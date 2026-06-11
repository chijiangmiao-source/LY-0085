import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date, timedelta
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database as db


class StatsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()
        self._check_warnings()
        self.refresh_stats()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=10)

        ctk.CTkLabel(top, text="开始日期:").pack(side="left")
        self.date_start = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_start.set_date(date.today() - timedelta(days=30))
        self.date_start.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="趋势天数:").pack(side="left", padx=(15, 0))
        self.combo_days = ctk.CTkComboBox(top, values=["7", "14", "30", "60", "90"], width=60)
        self.combo_days.set("30")
        self.combo_days.pack(side="left", padx=5)

        ctk.CTkButton(top, text="刷新", width=80, command=self.refresh_all).pack(side="left", padx=10)

        ctk.CTkLabel(top, text="返工率阈值:").pack(side="right")
        self.entry_threshold = ctk.CTkEntry(top, width=60)
        current = db.get_rework_rate_threshold()
        self.entry_threshold.insert(0, str(current))
        self.entry_threshold.pack(side="right", padx=5)
        ctk.CTkLabel(top, text="(0~1)").pack(side="right")
        ctk.CTkButton(top, text="保存阈值", width=90, command=self._save_threshold).pack(side="right", padx=5)

        warn_box = ctk.CTkFrame(self, corner_radius=8)
        warn_box.grid(row=1, column=1, sticky="nsew", padx=(5, 15), pady=5)
        ctk.CTkLabel(warn_box, text="⚠ 返工预警（近7天）", font=ctk.CTkFont(size=14, weight="bold"), text_color="#d9534f").pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_warn_count = ctk.CTkLabel(warn_box, text="", font=ctk.CTkFont(size=12))
        self.lbl_warn_count.pack(anchor="w", padx=10)
        self.text_warn = ctk.CTkTextbox(warn_box, height=180)
        self.text_warn.pack(fill="both", expand=True, padx=10, pady=10)

        low_box = ctk.CTkFrame(self, corner_radius=8)
        low_box.grid(row=2, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        ctk.CTkLabel(low_box, text="📦 低库存预警", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e67e22").pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_low_count = ctk.CTkLabel(low_box, text="", font=ctk.CTkFont(size=12))
        self.lbl_low_count.pack(anchor="w", padx=10)
        self.text_low = ctk.CTkTextbox(low_box, height=150)
        self.text_low.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(15, 5), pady=5)
        left.grid_rowconfigure(1, weight=1)
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        chart_frm = ctk.CTkFrame(left, corner_radius=8)
        chart_frm.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        chart_frm.grid_columnconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(0, weight=1)
        self.fig_trend = Figure(figsize=(6, 2.5), dpi=100)
        self.canvas_trend = FigureCanvasTkAgg(self.fig_trend, master=chart_frm)
        self.canvas_trend.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        chart2_frm = ctk.CTkFrame(left, corner_radius=8)
        chart2_frm.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        chart2_frm.grid_columnconfigure(0, weight=1)
        chart2_frm.grid_rowconfigure(0, weight=1)
        self.fig_usage = Figure(figsize=(6, 2.5), dpi=100)
        self.canvas_usage = FigureCanvasTkAgg(self.fig_usage, master=chart2_frm)
        self.canvas_usage.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        table_frm = ctk.CTkFrame(left, corner_radius=8)
        table_frm.grid(row=2, column=0, sticky="nsew")
        table_frm.grid_columnconfigure(0, weight=1)
        table_frm.grid_rowconfigure(0, weight=1)

        cols = ("code", "name", "used", "rework", "abnormal", "rate", "stock", "safety")
        self.tree = ttk.Treeview(table_frm, columns=cols, show="headings", height=10)
        self.tree.heading("code", text="材料编号")
        self.tree.heading("name", text="材料名称")
        self.tree.heading("used", text="总用量")
        self.tree.heading("rework", text="返工次数")
        self.tree.heading("abnormal", text="异常数")
        self.tree.heading("rate", text="返工率")
        self.tree.heading("stock", text="当前库存")
        self.tree.heading("safety", text="安全库存")

        self.tree.column("code", width=80, anchor="center")
        self.tree.column("name", width=120, anchor="w")
        self.tree.column("used", width=70, anchor="center")
        self.tree.column("rework", width=70, anchor="center")
        self.tree.column("abnormal", width=70, anchor="center")
        self.tree.column("rate", width=70, anchor="center")
        self.tree.column("stock", width=80, anchor="center")
        self.tree.column("safety", width=80, anchor="center")

        self.tree.tag_configure("high", background="#f8d7da")
        self.tree.tag_configure("warn", background="#fff3cd")

        vsb = ttk.Scrollbar(table_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        vsb.grid(row=0, column=1, sticky="ns", pady=5)

    def _save_threshold(self):
        try:
            val = float(self.entry_threshold.get().strip())
        except ValueError:
            messagebox.showerror("错误", "阈值必须是数字", parent=self)
            return
        ok, msg = db.set_rework_rate_threshold(val)
        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            self.refresh_all()
        else:
            messagebox.showerror("错误", msg, parent=self)

    def _check_warnings(self):
        warnings = db.get_7day_rework_warnings()
        threshold = db.get_rework_rate_threshold()
        self.text_warn.delete("1.0", "end")
        if warnings:
            self.lbl_warn_count.configure(text=f"共 {len(warnings)} 项材料超过阈值 ({threshold*100:.0f}%)", text_color="#d9534f")
            for w in warnings:
                line = (
                    f"[{w['material_code']}] {w['material_name']}\n"
                    f"  返工率: {w['rework_rate']*100:.1f}% (记录:{w['total_records']} 返工:{w['rework_records']} 总返工:{w['total_reworks']})\n\n"
                )
                self.text_warn.insert("end", line)
        else:
            self.lbl_warn_count.configure(text="无预警，所有材料正常 ✓", text_color="#28a745")
            self.text_warn.insert("end", "近7天所有材料返工率均在阈值以下。")

        lows = db.get_low_stock_materials()
        self.text_low.delete("1.0", "end")
        if lows:
            self.lbl_low_count.configure(text=f"共 {len(lows)} 项材料库存不足", text_color="#e67e22")
            for m in lows:
                line = (
                    f"[{m['material_code']}] {m['material_name']}\n"
                    f"  当前库存: {m['current_stock']} / 安全库存: {m['safety_stock']}\n\n"
                )
                self.text_low.insert("end", line)
        else:
            self.lbl_low_count.configure(text="库存充足 ✓", text_color="#28a745")
            self.text_low.insert("end", "所有材料库存均在安全线以上。")

    def refresh_stats(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        start_date = self.date_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_end.get_date().strftime("%Y-%m-%d")
        threshold = db.get_rework_rate_threshold()
        stats = db.get_material_usage_stats(start_date, end_date)

        for s in stats:
            tag = ""
            if s["rework_rate"] > threshold:
                tag = "high"
            elif s["current_stock"] <= s["safety_stock"]:
                tag = "warn"
            self.tree.insert(
                "",
                "end",
                values=(
                    s["material_code"],
                    s["material_name"],
                    s["total_used"],
                    s["total_reworks"],
                    s["abnormal_count"],
                    f"{s['rework_rate']*100:.1f}%",
                    s["current_stock"],
                    s["safety_stock"],
                ),
                tags=(tag,),
            )

    def _draw_trend(self):
        days = int(self.combo_days.get())
        data = db.get_daily_usage_trend(days)
        self.fig_trend.clear()
        ax = self.fig_trend.add_subplot(111)
        if data:
            df = pd.DataFrame(data)
            ax.plot(df["construction_date"], df["total_used"], marker="o", label="使用量", linewidth=2, color="#3498db")
            ax.plot(df["construction_date"], df["total_reworks"], marker="s", label="返工次数", linewidth=2, color="#e74c3c")
            ax.set_title(f"近 {days} 天用量与返工趋势")
            ax.set_xlabel("日期")
            ax.set_ylabel("数量")
            ax.legend()
            ax.grid(True, alpha=0.3)
            for tick in ax.get_xticklabels():
                tick.set_rotation(45)
                tick.set_fontsize(8)
        else:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=14)
            ax.set_title(f"近 {days} 天用量与返工趋势")
        self.fig_trend.tight_layout()
        self.canvas_trend.draw()

    def _draw_usage(self):
        start_date = self.date_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_end.get_date().strftime("%Y-%m-%d")
        stats = db.get_material_usage_stats(start_date, end_date)
        self.fig_usage.clear()
        ax = self.fig_usage.add_subplot(111)
        valid = [s for s in stats if s["total_used"] > 0][:10]
        if valid:
            labels = [f"{s['material_code']}" for s in valid]
            values = [s["total_used"] for s in valid]
            reworks = [s["total_reworks"] for s in valid]
            import numpy as np
            x = np.arange(len(labels))
            width = 0.35
            ax.bar(x - width / 2, values, width, label="使用量", color="#3498db")
            ax.bar(x + width / 2, reworks, width, label="返工次数", color="#e74c3c")
            ax.set_xticks(x)
            ax.set_xticklabels(labels, fontsize=8)
            ax.set_title(f"材料用量 Top {len(valid)} ({start_date} ~ {end_date})")
            ax.set_xlabel("材料")
            ax.set_ylabel("数量")
            ax.legend()
            ax.grid(True, alpha=0.3, axis="y")
        else:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=14)
            ax.set_title("材料用量统计")
        self.fig_usage.tight_layout()
        self.canvas_usage.draw()

    def refresh_all(self):
        self.refresh_stats()
        self._draw_trend()
        self._draw_usage()
        self._check_warnings()
