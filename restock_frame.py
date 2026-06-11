import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, date
from typing import Optional, Callable
import database as db


class RestockDialog(ctk.CTkToplevel):
    def __init__(self, master, restock_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.restock_id = restock_id
        self.on_save = on_save
        self.title("编辑补货记录" if restock_id else "新增补货登记")
        self.geometry("520x620")
        self.resizable(False, False)
        self.grab_set()

        self._material_map = {}
        self._supplier_map = {}
        self._build_ui()
        self._load_materials()
        self._load_suppliers()
        if restock_id:
            self._load_data()

    def _load_materials(self):
        rows = db.get_materials()
        values = []
        for r in rows:
            if r["material_status"] == "正常":
                label = f"{r['material_code']} - {r['material_name']} (库存:{r['current_stock']})"
                self._material_map[label] = r["id"]
                values.append(label)
        self.combo_material.configure(values=values)

    def _load_suppliers(self):
        rows = db.get_suppliers()
        values = []
        for r in rows:
            if r["supplier_status"] == "正常":
                label = f"{r['supplier_code']} - {r['supplier_name']}"
                self._supplier_map[label] = r["id"]
                values.append(label)
        self.combo_supplier.configure(values=values)

    def _build_ui(self):
        pad = {"padx": 15, "pady": 8}
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="采购日期 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.date_entry = DateEntry(
            frm,
            width=25,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
            font=("Arial", 11),
        )
        self.date_entry.grid(row=0, column=1, **pad, sticky="w")

        ctk.CTkLabel(frm, text="材料 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.combo_material = ctk.CTkComboBox(frm, values=[], width=280)
        self.combo_material.grid(row=1, column=1, **pad)

        ctk.CTkLabel(frm, text="供应商 *", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.combo_supplier = ctk.CTkComboBox(frm, values=[], width=280)
        self.combo_supplier.grid(row=2, column=1, **pad)

        ctk.CTkLabel(frm, text="采购数量 *", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_qty = ctk.CTkEntry(frm, width=280)
        self.entry_qty.grid(row=3, column=1, **pad)
        self.entry_qty.insert(0, "1")

        ctk.CTkLabel(frm, text="单价 (元) *", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.entry_price = ctk.CTkEntry(frm, width=280)
        self.entry_price.grid(row=4, column=1, **pad)
        self.entry_price.insert(0, "0.00")

        ctk.CTkLabel(frm, text="总金额 (元) *", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self.entry_total = ctk.CTkEntry(frm, width=280)
        self.entry_total.grid(row=5, column=1, **pad)
        self.entry_total.insert(0, "0.00")

        ctk.CTkLabel(frm, text="备注", anchor="w").grid(row=6, column=0, sticky="nw", **pad)
        self.text_remark = ctk.CTkTextbox(frm, width=280, height=60)
        self.text_remark.grid(row=6, column=1, **pad)

        self.lbl_auto = ctk.CTkLabel(frm, text="💡 输入数量和单价后自动计算总金额", text_color="gray", font=("Arial", 10))
        self.lbl_auto.grid(row=7, column=0, columnspan=2, pady=(0, 5))

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=8, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frm, text="自动计算", width=100, command=self._calc_total).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=5)

        self.entry_qty.bind("<KeyRelease>", lambda e: self._auto_calc())
        self.entry_price.bind("<KeyRelease>", lambda e: self._auto_calc())

    def _auto_calc(self):
        try:
            qty = int(self.entry_qty.get().strip() or "0")
            price = float(self.entry_price.get().strip() or "0")
            total = round(qty * price, 2)
            current_total = self.entry_total.get().strip()
            try:
                current_val = float(current_total) if current_total else 0.0
                if abs(current_val - total) > 0.01:
                    self.lbl_auto.configure(
                        text=f"⚠ 总金额不匹配，计算值为: ¥{total:.2f}",
                        text_color="#e74c3c"
                    )
                else:
                    self.lbl_auto.configure(
                        text=f"✓ 总金额匹配: ¥{total:.2f}",
                        text_color="#27ae60"
                    )
            except ValueError:
                pass
            self.entry_total.delete(0, "end")
            self.entry_total.insert(0, f"{total:.2f}")
        except ValueError:
            self.lbl_auto.configure(
                text="💡 输入数量和单价后自动计算总金额",
                text_color="gray"
            )

    def _calc_total(self):
        try:
            qty = int(self.entry_qty.get().strip() or "0")
            price = float(self.entry_price.get().strip() or "0")
            total = round(qty * price, 2)
            self.entry_total.delete(0, "end")
            self.entry_total.insert(0, f"{total:.2f}")
            self.lbl_auto.configure(
                text=f"✓ 总金额已自动计算为: ¥{total:.2f}",
                text_color="#27ae60"
            )
            messagebox.showinfo("提示", f"总金额已自动计算为: ¥{total:.2f} 元", parent=self)
        except ValueError:
            messagebox.showwarning("警告", "请先输入有效的采购数量和单价", parent=self)

    def _load_data(self):
        records = db.get_stock_purchases()
        record = None
        for r in records:
            if r["id"] == self.restock_id:
                record = r
                break
        if not record:
            return

        try:
            dt = datetime.strptime(record["purchase_date"], "%Y-%m-%d")
            self.date_entry.set_date(dt)
        except Exception:
            pass

        supplier_label = None
        if record.get("supplier_id"):
            for label, sid in self._supplier_map.items():
                if sid == record["supplier_id"]:
                    supplier_label = label
                    break
        if not supplier_label and record["supplier"]:
            all_suppliers = db.get_suppliers()
            for s in all_suppliers:
                if s["supplier_name"] == record["supplier"] or record["supplier"].endswith(s["supplier_name"]):
                    supplier_label = f"{s['supplier_code']} - {s['supplier_name']}"
                    self._supplier_map[supplier_label] = s["id"]
                    current_values = list(self.combo_supplier.cget("values"))
                    if supplier_label not in current_values:
                        current_values.append(supplier_label)
                        self.combo_supplier.configure(values=current_values)
                    break
        if supplier_label:
            self.combo_supplier.set(supplier_label)
        self.entry_qty.delete(0, "end")
        self.entry_qty.insert(0, str(record["purchase_quantity"]))
        self.entry_price.delete(0, "end")
        self.entry_price.insert(0, f"{record['unit_price']:.2f}")
        self.entry_total.delete(0, "end")
        self.entry_total.insert(0, f"{record['total_amount']:.2f}")
        if record["remark"]:
            self.text_remark.insert("1.0", record["remark"])

        mat_label = None
        for label, mid in self._material_map.items():
            if mid == record["material_id"]:
                mat_label = label
                break
        if not mat_label:
            mat = db.get_material_by_id(record["material_id"])
            if mat:
                mat_label = f"{mat['material_code']} - {mat['material_name']} (库存:{mat['current_stock']})"
                self._material_map[mat_label] = mat["id"]
                current_values = list(self.combo_material.cget("values"))
                if mat_label not in current_values:
                    current_values.append(mat_label)
                    self.combo_material.configure(values=current_values)
        if mat_label:
            self.combo_material.set(mat_label)

    def _on_save(self):
        mat_label = self.combo_material.get().strip()
        if mat_label not in self._material_map:
            messagebox.showerror("错误", "请选择材料", parent=self)
            return
        material_id = self._material_map[mat_label]

        sup_label = self.combo_supplier.get().strip()
        if sup_label not in self._supplier_map:
            messagebox.showerror("错误", "请选择供应商（从供应商档案中选择）", parent=self)
            return
        supplier_id = self._supplier_map[sup_label]
        sup_name = sup_label.split(" - ", 1)[1] if " - " in sup_label else sup_label

        try:
            purchase_qty = int(self.entry_qty.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "采购数量必须是整数", parent=self)
            return
        try:
            unit_price = float(self.entry_price.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "单价必须是数字", parent=self)
            return
        try:
            total_amount = float(self.entry_total.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "总金额必须是数字", parent=self)
            return

        calc_total = round(purchase_qty * unit_price, 2)
        if abs(total_amount - calc_total) > 0.01:
            result = messagebox.askyesnocancel(
                "金额校验",
                f"总金额与计算结果不匹配！\n\n"
                f"采购数量: {purchase_qty}\n"
                f"单　　价: ¥{unit_price:.2f}\n"
                f"计算总价: ¥{calc_total:.2f}\n"
                f"输入总价: ¥{total_amount:.2f}\n\n"
                f"是否使用自动计算的金额 ¥{calc_total:.2f} 保存？\n"
                f"（是=使用计算值 / 否=继续使用输入值 / 取消=返回修改）",
                parent=self
            )
            if result is None:
                return
            elif result:
                total_amount = calc_total
                self.entry_total.delete(0, "end")
                self.entry_total.insert(0, f"{total_amount:.2f}")
                self.lbl_auto.configure(
                    text=f"✓ 已使用计算金额: ¥{total_amount:.2f}",
                    text_color="#27ae60"
                )

        purchase_date = self.date_entry.get_date().strftime("%Y-%m-%d")
        remark = self.text_remark.get("1.0", "end").strip()

        data = {
            "purchase_date": purchase_date,
            "material_id": material_id,
            "supplier": sup_name,
            "supplier_id": supplier_id,
            "purchase_quantity": purchase_qty,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "remark": remark,
        }

        if self.restock_id:
            ok, msg = db.update_stock_purchase(self.restock_id, data)
        else:
            ok, msg = db.add_stock_purchase(data)

        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self)


class RestockFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._material_map = {}
        self._build_ui()
        self._load_materials()
        self.refresh()

    def _load_materials(self):
        self._material_map = {}
        rows = db.get_materials()
        for r in rows:
            self._material_map[r["id"]] = f"{r['material_code']} - {r['material_name']}"

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top, text="开始日期:").pack(side="left")
        self.date_start = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_start.pack(side="left", padx=5)
        self.date_start.set_date(date(2000, 1, 1))

        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="关键词:").pack(side="left", padx=(15, 0))
        self.entry_search = ctk.CTkEntry(top, width=180, placeholder_text="供应商/材料")
        self.entry_search.pack(side="left", padx=5)

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset).pack(side="left", padx=5)

        ctk.CTkButton(top, text="新增补货", width=100, command=self._add).pack(side="right", padx=5)
        ctk.CTkButton(top, text="编辑", width=80, command=self._edit).pack(side="right", padx=5)
        ctk.CTkButton(top, text="删除", width=80, fg_color="#d9534f", command=self._delete).pack(side="right", padx=5)

        stat_frm = ctk.CTkFrame(self, fg_color="transparent")
        stat_frm.pack(fill="x", padx=15, pady=(0, 5))

        self.lbl_total_amount = ctk.CTkLabel(stat_frm, text="总采购金额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#27ae60")
        self.lbl_total_amount.pack(side="left", padx=10)
        self.lbl_total_qty = ctk.CTkLabel(stat_frm, text="总采购数量: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2980b9")
        self.lbl_total_qty.pack(side="left", padx=10)
        self.lbl_record_count = ctk.CTkLabel(stat_frm, text="记录数: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#8e44ad")
        self.lbl_record_count.pack(side="left", padx=10)

        tree_frm = ctk.CTkFrame(self)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("date", "material", "supplier", "qty", "price", "total", "remark")
        self.tree = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree.heading("date", text="采购日期")
        self.tree.heading("material", text="材料")
        self.tree.heading("supplier", text="供应商")
        self.tree.heading("qty", text="采购数量")
        self.tree.heading("price", text="单价")
        self.tree.heading("total", text="总金额")
        self.tree.heading("remark", text="备注")

        self.tree.column("date", width=100, anchor="center")
        self.tree.column("material", width=180, anchor="w")
        self.tree.column("supplier", width=120, anchor="w")
        self.tree.column("qty", width=80, anchor="center")
        self.tree.column("price", width=80, anchor="e")
        self.tree.column("total", width=100, anchor="e")
        self.tree.column("remark", width=200, anchor="w")

        self.tree.tag_configure("high", background="#f8d7da")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _reset(self):
        self.date_start.set_date(date(2000, 1, 1))
        self.date_end.set_date(date.today())
        self.entry_search.delete(0, "end")
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        start_date = self.date_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_end.get_date().strftime("%Y-%m-%d")
        keyword = self.entry_search.get().strip()

        rows = db.get_stock_purchases(start_date, end_date, keyword)

        total_amount = 0.0
        total_qty = 0
        for r in rows:
            total_amount += r["total_amount"]
            total_qty += r["purchase_quantity"]
            mat_display = f"{r['material_code']} - {r['material_name']}"
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["purchase_date"],
                    mat_display,
                    r["supplier"],
                    r["purchase_quantity"],
                    f"¥{r['unit_price']:.2f}",
                    f"¥{r['total_amount']:.2f}",
                    (r["remark"] or "")[:40],
                ),
            )

        self.lbl_total_amount.configure(text=f"总采购金额: ¥{total_amount:.2f}")
        self.lbl_total_qty.configure(text=f"总采购数量: {total_qty}")
        self.lbl_record_count.configure(text=f"记录数: {len(rows)}")

    def _get_selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条记录", parent=self)
            return None
        return int(sel[0])

    def _add(self):
        RestockDialog(self, on_save=self._on_change)

    def _edit(self):
        rid = self._get_selected_id()
        if rid:
            RestockDialog(self, restock_id=rid, on_save=self._on_change)

    def _delete(self):
        rid = self._get_selected_id()
        if rid and messagebox.askyesno("确认", "确定要删除该补货记录吗?\n删除后库存将自动回退。", parent=self):
            ok, msg = db.delete_stock_purchase(rid)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self._on_change()
            else:
                messagebox.showerror("错误", msg, parent=self)

    def _on_change(self):
        self._load_materials()
        self.refresh()
