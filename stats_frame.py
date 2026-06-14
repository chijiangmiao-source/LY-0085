import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date, timedelta
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import platform
import os

system = platform.system()
if system == "Windows":
    font_candidates = ["Microsoft YaHei", "SimHei", "SimSun", "KaiTi"]
elif system == "Darwin":
    font_candidates = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
else:
    font_candidates = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Source Han Sans SC"]

available_fonts = {f.name for f in font_manager.fontManager.ttflist}
for fname in font_candidates:
    if fname in available_fonts:
        plt.rcParams["font.sans-serif"] = [fname]
        break

plt.rcParams["axes.unicode_minus"] = False

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from services.stats_service import StatsService
from services.payment_service import PaymentService


class StatsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()
        self._check_warnings()
        self.refresh_stats()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)

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
        current = StatsService.get_rework_rate_threshold()
        self.entry_threshold.insert(0, str(current))
        self.entry_threshold.pack(side="right", padx=5)
        ctk.CTkLabel(top, text="(0~1)").pack(side="right")
        ctk.CTkButton(top, text="保存阈值", width=90, command=self._save_threshold).pack(side="right", padx=5)

        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5))

        self.btn_tab_usage = ctk.CTkButton(tab_bar, text="📊 用量统计", width=120, height=32,
                                           fg_color="#347ab8", command=lambda: self._switch_tab("usage"))
        self.btn_tab_usage.pack(side="left", padx=3)

        self.btn_tab_cost = ctk.CTkButton(tab_bar, text="💰 成本分析", width=120, height=32,
                                          fg_color="#95a5a6", command=lambda: self._switch_tab("cost"))
        self.btn_tab_cost.pack(side="left", padx=3)

        self.usage_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.usage_frame.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=5)
        self.usage_frame.grid_rowconfigure(1, weight=1)
        self.usage_frame.grid_rowconfigure(3, weight=1)
        self.usage_frame.grid_columnconfigure(0, weight=1)

        chart_frm = ctk.CTkFrame(self.usage_frame, corner_radius=8)
        chart_frm.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        chart_frm.grid_columnconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(0, weight=1)
        self.fig_trend = Figure(figsize=(6, 2.5), dpi=100)
        self.canvas_trend = FigureCanvasTkAgg(self.fig_trend, master=chart_frm)
        self.canvas_trend.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        chart2_frm = ctk.CTkFrame(self.usage_frame, corner_radius=8)
        chart2_frm.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        chart2_frm.grid_columnconfigure(0, weight=1)
        chart2_frm.grid_rowconfigure(0, weight=1)
        self.fig_usage = Figure(figsize=(6, 2.5), dpi=100)
        self.canvas_usage = FigureCanvasTkAgg(self.fig_usage, master=chart2_frm)
        self.canvas_usage.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        table_frm = ctk.CTkFrame(self.usage_frame, corner_radius=8)
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

        self.cost_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cost_frame.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=5)
        self.cost_frame.grid_rowconfigure(1, weight=1)
        self.cost_frame.grid_rowconfigure(2, weight=1)
        self.cost_frame.grid_columnconfigure(0, weight=1)

        loss30_box = ctk.CTkFrame(self.cost_frame, corner_radius=8)
        loss30_box.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        loss30_box.grid_columnconfigure(0, weight=1)
        loss30_box.grid_rowconfigure(1, weight=1)

        loss30_header = ctk.CTkFrame(loss30_box, fg_color="transparent")
        loss30_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(loss30_header, text="📉 近30天材料损耗成本", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e74c3c").pack(side="left")
        self.lbl_loss30_summary = ctk.CTkLabel(loss30_header, text="", font=ctk.CTkFont(size=12))
        self.lbl_loss30_summary.pack(side="right")

        loss30_cols = ("mat_code", "mat_name", "total_used", "avg_price", "used_cost", "loss_cost", "loss_ratio")
        self.tree_loss30 = ttk.Treeview(loss30_box, columns=loss30_cols, show="headings", height=6)
        self.tree_loss30.heading("mat_code", text="材料编号")
        self.tree_loss30.heading("mat_name", text="材料名称")
        self.tree_loss30.heading("total_used", text="总用量")
        self.tree_loss30.heading("avg_price", text="平均单价")
        self.tree_loss30.heading("used_cost", text="使用成本")
        self.tree_loss30.heading("loss_cost", text="损耗成本")
        self.tree_loss30.heading("loss_ratio", text="损耗率")

        self.tree_loss30.column("mat_code", width=80, anchor="center")
        self.tree_loss30.column("mat_name", width=120, anchor="w")
        self.tree_loss30.column("total_used", width=70, anchor="center")
        self.tree_loss30.column("avg_price", width=80, anchor="e")
        self.tree_loss30.column("used_cost", width=90, anchor="e")
        self.tree_loss30.column("loss_cost", width=90, anchor="e")
        self.tree_loss30.column("loss_ratio", width=70, anchor="center")

        self.tree_loss30.tag_configure("high", background="#f8d7da")
        vsb_loss30 = ttk.Scrollbar(loss30_box, orient="vertical", command=self.tree_loss30.yview)
        self.tree_loss30.configure(yscrollcommand=vsb_loss30.set)
        self.tree_loss30.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_loss30.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

        order_box = ctk.CTkFrame(self.cost_frame, corner_radius=8)
        order_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        order_box.grid_columnconfigure(0, weight=1)
        order_box.grid_rowconfigure(1, weight=1)

        order_header = ctk.CTkFrame(order_box, fg_color="transparent")
        order_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(order_header, text="📋 单位订单材料成本", font=ctk.CTkFont(size=14, weight="bold"), text_color="#3498db").pack(side="left")
        self.lbl_order_count = ctk.CTkLabel(order_header, text="", font=ctk.CTkFont(size=12))
        self.lbl_order_count.pack(side="right")

        order_cols = ("order_no", "date", "materials", "total_qty", "reworks", "total_cost", "loss_cost", "unit_cost")
        self.tree_order = ttk.Treeview(order_box, columns=order_cols, show="headings", height=8)
        self.tree_order.heading("order_no", text="订单编号")
        self.tree_order.heading("date", text="施工日期")
        self.tree_order.heading("materials", text="使用材料")
        self.tree_order.heading("total_qty", text="总用量")
        self.tree_order.heading("reworks", text="返工数")
        self.tree_order.heading("total_cost", text="材料总成本")
        self.tree_order.heading("loss_cost", text="损耗成本")
        self.tree_order.heading("unit_cost", text="单位成本")

        self.tree_order.column("order_no", width=90, anchor="center")
        self.tree_order.column("date", width=90, anchor="center")
        self.tree_order.column("materials", width=150, anchor="w")
        self.tree_order.column("total_qty", width=60, anchor="center")
        self.tree_order.column("reworks", width=60, anchor="center")
        self.tree_order.column("total_cost", width=90, anchor="e")
        self.tree_order.column("loss_cost", width=90, anchor="e")
        self.tree_order.column("unit_cost", width=80, anchor="e")

        self.tree_order.tag_configure("high_loss", background="#f8d7da")
        vsb_order = ttk.Scrollbar(order_box, orient="vertical", command=self.tree_order.yview)
        self.tree_order.configure(yscrollcommand=vsb_order.set)
        self.tree_order.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_order.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

        rank_box = ctk.CTkFrame(self.cost_frame, corner_radius=8)
        rank_box.grid(row=2, column=0, sticky="nsew")
        rank_box.grid_columnconfigure(0, weight=1)
        rank_box.grid_rowconfigure(1, weight=1)

        rank_header = ctk.CTkFrame(rank_box, fg_color="transparent")
        rank_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(rank_header, text="🏆 高损耗高成本材料排行 (Top 10)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").pack(side="left")
        self.lbl_rank_info = ctk.CTkLabel(rank_header, text="按综合成本评分排序", font=ctk.CTkFont(size=12), text_color="gray")
        self.lbl_rank_info.pack(side="right")

        rank_cols = ("rank", "mat_code", "mat_name", "spec", "total_used", "reworks", "abnormal", "avg_price", "total_cost", "loss_cost", "loss_ratio")
        self.tree_rank = ttk.Treeview(rank_box, columns=rank_cols, show="headings", height=8)
        self.tree_rank.heading("rank", text="排名")
        self.tree_rank.heading("mat_code", text="材料编号")
        self.tree_rank.heading("mat_name", text="材料名称")
        self.tree_rank.heading("spec", text="规格")
        self.tree_rank.heading("total_used", text="总用量")
        self.tree_rank.heading("reworks", text="返工数")
        self.tree_rank.heading("abnormal", text="异常数")
        self.tree_rank.heading("avg_price", text="平均单价")
        self.tree_rank.heading("total_cost", text="总成本")
        self.tree_rank.heading("loss_cost", text="损耗成本")
        self.tree_rank.heading("loss_ratio", text="损耗率")

        self.tree_rank.column("rank", width=50, anchor="center")
        self.tree_rank.column("mat_code", width=80, anchor="center")
        self.tree_rank.column("mat_name", width=110, anchor="w")
        self.tree_rank.column("spec", width=80, anchor="w")
        self.tree_rank.column("total_used", width=60, anchor="center")
        self.tree_rank.column("reworks", width=60, anchor="center")
        self.tree_rank.column("abnormal", width=60, anchor="center")
        self.tree_rank.column("avg_price", width=80, anchor="e")
        self.tree_rank.column("total_cost", width=80, anchor="e")
        self.tree_rank.column("loss_cost", width=80, anchor="e")
        self.tree_rank.column("loss_ratio", width=70, anchor="center")

        self.tree_rank.tag_configure("top3", background="#fdebd0")
        self.tree_rank.tag_configure("high", background="#f8d7da")
        vsb_rank = ttk.Scrollbar(rank_box, orient="vertical", command=self.tree_rank.yview)
        self.tree_rank.configure(yscrollcommand=vsb_rank.set)
        self.tree_rank.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_rank.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

        warn_box = ctk.CTkFrame(self, corner_radius=8)
        warn_box.grid(row=2, column=1, sticky="nsew", padx=(5, 15), pady=5)
        ctk.CTkLabel(warn_box, text="⚠ 返工预警（近7天）", font=ctk.CTkFont(size=14, weight="bold"), text_color="#d9534f").pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_warn_count = ctk.CTkLabel(warn_box, text="", font=ctk.CTkFont(size=12))
        self.lbl_warn_count.pack(anchor="w", padx=10)
        self.text_warn = ctk.CTkTextbox(warn_box, height=180)
        self.text_warn.pack(fill="both", expand=True, padx=10, pady=10)

        low_box = ctk.CTkFrame(self, corner_radius=8)
        low_box.grid(row=2, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        low_box.grid_remove()
        ctk.CTkLabel(low_box, text="📦 低库存预警", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e67e22").pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_low_count = ctk.CTkLabel(low_box, text="", font=ctk.CTkFont(size=12))
        self.lbl_low_count.pack(anchor="w", padx=10)
        self.text_low = ctk.CTkTextbox(low_box, height=150)
        self.text_low.pack(fill="both", expand=True, padx=10, pady=10)

        self._switch_tab("usage")

    def _save_threshold(self):
        try:
            val = float(self.entry_threshold.get().strip())
        except ValueError:
            messagebox.showerror("错误", "阈值必须是数字", parent=self)
            return
        ok, msg = StatsService.set_rework_rate_threshold(val)
        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            self.refresh_all()
        else:
            messagebox.showerror("错误", msg, parent=self)

    def _check_warnings(self):
        warnings = StatsService.get_7day_rework_warnings()
        threshold = StatsService.get_rework_rate_threshold()
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

        lows = StatsService.get_low_stock_materials()
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
        threshold = StatsService.get_rework_rate_threshold()
        stats = StatsService.get_material_usage_stats(start_date, end_date)

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
        data = StatsService.get_daily_usage_trend(days)
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
        stats = StatsService.get_material_usage_stats(start_date, end_date)
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

    def _switch_tab(self, tab_name: str):
        self.usage_frame.grid_remove()
        self.cost_frame.grid_remove()
        self.btn_tab_usage.configure(fg_color="#95a5a6")
        self.btn_tab_cost.configure(fg_color="#95a5a6")

        if tab_name == "usage":
            self.usage_frame.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=5)
            self.btn_tab_usage.configure(fg_color="#347ab8")
        elif tab_name == "cost":
            self.cost_frame.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=5)
            self.btn_tab_cost.configure(fg_color="#347ab8")
            self.refresh_cost_stats()

    def refresh_cost_stats(self):
        self.refresh_30day_loss()
        self.refresh_order_cost()
        self.refresh_high_loss_rank()

    def refresh_30day_loss(self):
        for item in self.tree_loss30.get_children():
            self.tree_loss30.delete(item)

        loss_data = StatsService.get_30day_material_loss_cost()
        materials = loss_data.get("materials", [])

        self.lbl_loss30_summary.configure(
            text=f"总采购成本: ¥{loss_data['total_purchase_cost']:.2f} | "
                 f"总损耗成本: ¥{loss_data['total_loss_cost']:.2f} | "
                 f"损耗率: {loss_data['loss_rate']:.2f}%"
        )

        for m in materials:
            tag = ""
            if m["loss_ratio"] >= 15:
                tag = "high"
            self.tree_loss30.insert(
                "",
                "end",
                values=(
                    m["material_code"],
                    m["material_name"],
                    m["total_used"],
                    f"¥{m['avg_price']:.2f}",
                    f"¥{m['used_cost']:.2f}",
                    f"¥{m['loss_cost']:.2f}",
                    f"{m['loss_ratio']:.2f}%",
                ),
                tags=(tag,),
            )

    def refresh_order_cost(self):
        for item in self.tree_order.get_children():
            self.tree_order.delete(item)

        start_date = self.date_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_end.get_date().strftime("%Y-%m-%d")
        order_data = StatsService.get_unit_order_material_cost(start_date, end_date)

        self.lbl_order_count.configure(text=f"共 {len(order_data)} 个订单")

        for o in order_data:
            tag = ""
            if o["loss_cost"] > 0 and o["loss_cost"] / o["total_cost"] >= 0.15:
                tag = "high_loss"
            self.tree_order.insert(
                "",
                "end",
                values=(
                    o["order_no"],
                    o["construction_date"],
                    (o["materials_used"] or "")[:20],
                    o["total_qty"],
                    o["total_reworks"],
                    f"¥{o['total_cost']:.2f}",
                    f"¥{o['loss_cost']:.2f}",
                    f"¥{o['unit_cost']:.2f}",
                ),
                tags=(tag,),
            )

    def refresh_high_loss_rank(self):
        for item in self.tree_rank.get_children():
            self.tree_rank.delete(item)

        start_date = self.date_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_end.get_date().strftime("%Y-%m-%d")
        rank_data = StatsService.get_high_loss_high_cost_materials(start_date, end_date, top_n=10)

        for idx, r in enumerate(rank_data, 1):
            tag = ""
            if idx <= 3:
                tag = "top3"
            elif r["loss_ratio"] >= 15:
                tag = "high"
            self.tree_rank.insert(
                "",
                "end",
                values=(
                    f"#{idx}",
                    r["material_code"],
                    r["material_name"],
                    r["material_spec"] or "",
                    r["total_used"],
                    r["total_reworks"],
                    r["abnormal_count"],
                    f"¥{r['avg_price']:.2f}",
                    f"¥{r['total_cost']:.2f}",
                    f"¥{r['loss_cost']:.2f}",
                    f"{r['loss_ratio']:.2f}%",
                ),
                tags=(tag,),
            )

    def refresh_all(self):
        self.refresh_stats()
        self._draw_trend()
        self._draw_usage()
        self._check_warnings()
        if self.cost_frame.winfo_ismapped():
            self.refresh_cost_stats()
