import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from typing import Optional, Callable
import database as db


class RecordDialog(ctk.CTkToplevel):
    def __init__(self, master, record_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.record_id = record_id
        self.on_save = on_save
        self.title("编辑施工记录" if record_id else "新增施工记录")
        self.geometry("500x580")
        self.resizable(False, False)
        self.grab_set()

        self._material_map = {}
        self._build_ui()
        self._load_materials()
        if record_id:
            self._load_data()

    def _load_materials(self):
        rows = db.get_materials()
        values = []
        for r in rows:
            if self.record_id:
                label = f"{r['material_code']} - {r['material_name']} [{r['material_status']}] (库存:{r['current_stock']})"
                self._material_map[label] = r["id"]
                values.append(label)
            else:
                if r["material_status"] == "正常":
                    label = f"{r['material_code']} - {r['material_name']} (库存:{r['current_stock']})"
                    self._material_map[label] = r["id"]
                    values.append(label)
        self.combo_material.configure(values=values)

    def _build_ui(self):
        pad = {"padx": 15, "pady": 8}
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="施工日期 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
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

        ctk.CTkLabel(frm, text="订单编号 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.entry_order = ctk.CTkEntry(frm, width=280)
        self.entry_order.grid(row=1, column=1, **pad)

        ctk.CTkLabel(frm, text="材料 *", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.combo_material = ctk.CTkComboBox(frm, values=[], width=280)
        self.combo_material.grid(row=2, column=1, **pad)

        ctk.CTkLabel(frm, text="使用数量 *", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_qty = ctk.CTkEntry(frm, width=280)
        self.entry_qty.grid(row=3, column=1, **pad)
        self.entry_qty.insert(0, "1")

        ctk.CTkLabel(frm, text="返工次数 *", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.entry_rework = ctk.CTkEntry(frm, width=280)
        self.entry_rework.grid(row=4, column=1, **pad)
        self.entry_rework.insert(0, "0")

        ctk.CTkLabel(frm, text="操作人", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self.entry_operator = ctk.CTkEntry(frm, width=280)
        self.entry_operator.grid(row=5, column=1, **pad)

        ctk.CTkLabel(frm, text="异常说明", anchor="w").grid(row=6, column=0, sticky="nw", **pad)
        self.text_note = ctk.CTkTextbox(frm, width=280, height=80)
        self.text_note.grid(row=6, column=1, **pad)

        self.lbl_hint = ctk.CTkLabel(frm, text="返工次数 ≥ 2 时，异常说明不能为空", text_color="orange")
        self.lbl_hint.grid(row=7, column=0, columnspan=2, pady=(0, 5))

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=8, column=0, columnspan=2, pady=10)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=10)

    def _load_data(self):
        records = db.get_construction_records()
        record = None
        for r in records:
            if r["id"] == self.record_id:
                record = r
                break
        if not record:
            return

        from datetime import datetime
        try:
            dt = datetime.strptime(record["construction_date"], "%Y-%m-%d")
            self.date_entry.set_date(dt)
        except Exception:
            pass
        self.entry_order.insert(0, record["order_no"])
        self.entry_qty.delete(0, "end")
        self.entry_qty.insert(0, str(record["used_quantity"]))
        self.entry_rework.delete(0, "end")
        self.entry_rework.insert(0, str(record["rework_count"]))
        self.entry_operator.insert(0, record["operator"] or "")
        if record["exception_note"]:
            self.text_note.insert("1.0", record["exception_note"])

        mat_label = None
        for label, mid in self._material_map.items():
            if mid == record["material_id"]:
                mat_label = label
                break
        if not mat_label:
            mat = db.get_material_by_id(record["material_id"])
            if mat:
                mat_label = f"{mat['material_code']} - {mat['material_name']} [{mat['material_status']}] (库存:{mat['current_stock']})"
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

        try:
            used_qty = int(self.entry_qty.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "使用数量必须是整数", parent=self)
            return
        try:
            rework_count = int(self.entry_rework.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "返工次数必须是整数", parent=self)
            return

        construction_date = self.date_entry.get_date().strftime("%Y-%m-%d")
        exception_note = self.text_note.get("1.0", "end").strip()

        data = {
            "construction_date": construction_date,
            "order_no": self.entry_order.get().strip(),
            "material_id": material_id,
            "used_quantity": used_qty,
            "rework_count": rework_count,
            "operator": self.entry_operator.get().strip(),
            "exception_note": exception_note,
        }

        if self.record_id:
            ok, msg = db.update_construction_record(self.record_id, data)
        else:
            ok, msg = db.add_construction_record(data)

        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self)


class RecordFrame(ctk.CTkFrame):
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
        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="关键词:").pack(side="left", padx=(15, 0))
        self.entry_search = ctk.CTkEntry(top, width=180, placeholder_text="订单/操作人/材料")
        self.entry_search.pack(side="left", padx=5)

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset).pack(side="left", padx=5)

        ctk.CTkButton(top, text="新增记录", width=100, command=self._add).pack(side="right", padx=5)
        ctk.CTkButton(top, text="编辑", width=80, command=self._edit).pack(side="right", padx=5)
        ctk.CTkButton(top, text="删除", width=80, fg_color="#d9534f", command=self._delete).pack(side="right", padx=5)

        tree_frm = ctk.CTkFrame(self)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("date", "order", "material", "qty", "rework", "operator", "note")
        self.tree = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree.heading("date", text="施工日期")
        self.tree.heading("order", text="订单编号")
        self.tree.heading("material", text="材料")
        self.tree.heading("qty", text="使用数量")
        self.tree.heading("rework", text="返工次数")
        self.tree.heading("operator", text="操作人")
        self.tree.heading("note", text="异常说明")

        self.tree.column("date", width=100, anchor="center")
        self.tree.column("order", width=100, anchor="center")
        self.tree.column("material", width=180, anchor="w")
        self.tree.column("qty", width=80, anchor="center")
        self.tree.column("rework", width=80, anchor="center")
        self.tree.column("operator", width=90, anchor="center")
        self.tree.column("note", width=250, anchor="w")

        self.tree.tag_configure("rework", background="#fff3cd")
        self.tree.tag_configure("abnormal", background="#f8d7da")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        from datetime import date
        self.date_start.set_date(date(2000, 1, 1))
        self.date_end.set_date(date.today())

    def _reset(self):
        from datetime import date
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

        rows = db.get_construction_records(start_date, end_date, keyword)

        for r in rows:
            tag = ""
            if r["rework_count"] >= 2:
                tag = "abnormal"
            elif r["rework_count"] > 0:
                tag = "rework"

            mat_display = f"{r['material_code']} - {r['material_name']}"
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["construction_date"],
                    r["order_no"],
                    mat_display,
                    r["used_quantity"],
                    r["rework_count"],
                    r["operator"] or "",
                    (r["exception_note"] or "")[:50],
                ),
                tags=(tag,),
            )

    def _get_selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条记录", parent=self)
            return None
        return int(sel[0])

    def _add(self):
        RecordDialog(self, on_save=self._on_change)

    def _edit(self):
        rid = self._get_selected_id()
        if rid:
            RecordDialog(self, record_id=rid, on_save=self._on_change)

    def _delete(self):
        rid = self._get_selected_id()
        if rid and messagebox.askyesno("确认", "确定要删除该记录吗?", parent=self):
            ok, msg = db.delete_construction_record(rid)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self._on_change()
            else:
                messagebox.showerror("错误", msg, parent=self)

    def _on_change(self):
        self._load_materials()
        self.refresh()
