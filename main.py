import customtkinter as ctk
from tkinter import ttk
import database as db
from material_frame import MaterialFrame
from record_frame import RecordFrame
from stats_frame import StatsFrame
from supplier_frame import SupplierFrame


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("修鞋铺鞋底材料损耗核对台")
        self.geometry("1200x780")
        self.minsize(1100, 700)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._build_style()
        self._build_ui()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            font=("Microsoft YaHei", 10),
            rowheight=28,
            background="white",
            fieldbackground="white",
        )
        style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei", 10, "bold"),
            background="#e8eef5",
            foreground="#333",
            padding=5,
        )
        style.map(
            "Treeview",
            background=[("selected", "#347ab8")],
            foreground=[("selected", "white")],
        )

    def _build_ui(self):
        header = ctk.CTkFrame(self, height=60, fg_color="#2c3e50")
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="👟 修鞋铺鞋底材料损耗核对台",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20)

        self.lbl_info = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=12), text_color="#ecf0f1")
        self.lbl_info.pack(side="right", padx=20)
        self._update_header_info()

        tab_frm = ctk.CTkFrame(self, fg_color="transparent")
        tab_frm.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_stats = ctk.CTkButton(tab_frm, text="📊 统计分析", width=140, height=38,
                                        fg_color="#347ab8", command=lambda: self._switch_tab("stats"))
        self.btn_stats.pack(side="left", padx=3)

        self.btn_material = ctk.CTkButton(tab_frm, text="📦 材料管理", width=140, height=38,
                                           fg_color="#95a5a6", command=lambda: self._switch_tab("material"))
        self.btn_material.pack(side="left", padx=3)

        self.btn_record = ctk.CTkButton(tab_frm, text="📝 施工记录", width=140, height=38,
                                         fg_color="#95a5a6", command=lambda: self._switch_tab("record"))
        self.btn_record.pack(side="left", padx=3)

        self.btn_supplier = ctk.CTkButton(tab_frm, text="🏢 采购与供应商", width=140, height=38,
                                           fg_color="#95a5a6", command=lambda: self._switch_tab("supplier"))
        self.btn_supplier.pack(side="left", padx=3)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=5, pady=5)

        self.stats_frame = StatsFrame(self.content)
        self.material_frame = MaterialFrame(self.content)
        self.record_frame = RecordFrame(self.content)
        self.supplier_frame = SupplierFrame(self.content)

        self._switch_tab("stats")

    def _update_header_info(self):
        warnings = db.get_7day_rework_warnings()
        lows = db.get_low_stock_materials()
        parts = []
        if warnings:
            parts.append(f"⚠ 返工预警: {len(warnings)}")
        if lows:
            parts.append(f"📦 低库存: {len(lows)}")
        if not parts:
            parts.append("✓ 一切正常")
        self.lbl_info.configure(text="   |   ".join(parts))

    def _switch_tab(self, name: str):
        self.stats_frame.pack_forget()
        self.material_frame.pack_forget()
        self.record_frame.pack_forget()
        self.supplier_frame.pack_forget()

        self.btn_stats.configure(fg_color="#95a5a6")
        self.btn_material.configure(fg_color="#95a5a6")
        self.btn_record.configure(fg_color="#95a5a6")
        self.btn_supplier.configure(fg_color="#95a5a6")

        if name == "stats":
            self.stats_frame.pack(fill="both", expand=True)
            self.btn_stats.configure(fg_color="#347ab8")
            self.stats_frame.refresh_all()
        elif name == "material":
            self.material_frame.pack(fill="both", expand=True)
            self.btn_material.configure(fg_color="#347ab8")
            self.material_frame.refresh()
        elif name == "record":
            self.record_frame.pack(fill="both", expand=True)
            self.btn_record.configure(fg_color="#347ab8")
            self.record_frame.refresh()
        elif name == "supplier":
            self.supplier_frame.pack(fill="both", expand=True)
            self.btn_supplier.configure(fg_color="#347ab8")
            self.supplier_frame.refresh_all()

        self._update_header_info()


def main():
    db.init_db()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
