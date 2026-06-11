import customtkinter as ctk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import database as db


class MaterialDialog(ctk.CTkToplevel):
    def __init__(self, master, material_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.material_id = material_id
        self.on_save = on_save
        self.title("编辑材料" if material_id else "新增材料")
        self.geometry("450x520")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        if material_id:
            self._load_data()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 8}
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="材料编号 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.entry_code = ctk.CTkEntry(frm, width=280)
        self.entry_code.grid(row=0, column=1, **pad)

        ctk.CTkLabel(frm, text="材料名称 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.entry_name = ctk.CTkEntry(frm, width=280)
        self.entry_name.grid(row=1, column=1, **pad)

        ctk.CTkLabel(frm, text="材料规格", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.entry_spec = ctk.CTkEntry(frm, width=280)
        self.entry_spec.grid(row=2, column=1, **pad)

        ctk.CTkLabel(frm, text="当前库存 *", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_stock = ctk.CTkEntry(frm, width=280)
        self.entry_stock.grid(row=3, column=1, **pad)
        self.entry_stock.insert(0, "0")

        ctk.CTkLabel(frm, text="安全库存", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.entry_safety = ctk.CTkEntry(frm, width=280)
        self.entry_safety.grid(row=4, column=1, **pad)
        self.entry_safety.insert(0, "0")

        ctk.CTkLabel(frm, text="适用鞋型", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self.entry_shoe = ctk.CTkEntry(frm, width=280)
        self.entry_shoe.grid(row=5, column=1, **pad)

        ctk.CTkLabel(frm, text="材料状态", anchor="w").grid(row=6, column=0, sticky="w", **pad)
        self.combo_status = ctk.CTkComboBox(frm, values=["正常", "停用", "缺货"], width=280)
        self.combo_status.grid(row=6, column=1, **pad)
        self.combo_status.set("正常")

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=7, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=10)

    def _load_data(self):
        row = db.get_material_by_id(self.material_id)
        if row:
            self.entry_code.insert(0, row["material_code"])
            self.entry_name.insert(0, row["material_name"])
            self.entry_spec.insert(0, row["material_spec"] or "")
            self.entry_stock.delete(0, "end")
            self.entry_stock.insert(0, str(row["current_stock"]))
            self.entry_safety.delete(0, "end")
            self.entry_safety.insert(0, str(row["safety_stock"]))
            self.entry_shoe.insert(0, row["applicable_shoe_type"] or "")
            self.combo_status.set(row["material_status"])

    def _on_save(self):
        try:
            current_stock = int(self.entry_stock.get().strip() or "0")
            safety_stock = int(self.entry_safety.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "库存必须是整数", parent=self)
            return

        data = {
            "material_code": self.entry_code.get().strip(),
            "material_name": self.entry_name.get().strip(),
            "material_spec": self.entry_spec.get().strip(),
            "current_stock": current_stock,
            "safety_stock": safety_stock,
            "applicable_shoe_type": self.entry_shoe.get().strip(),
            "material_status": self.combo_status.get(),
        }

        if self.material_id:
            ok, msg = db.update_material(self.material_id, data)
        else:
            ok, msg = db.add_material(data)

        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self)


class MaterialFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top, text="关键词:").pack(side="left")
        self.entry_search = ctk.CTkEntry(top, width=200, placeholder_text="编号/名称/鞋型")
        self.entry_search.pack(side="left", padx=8)

        ctk.CTkLabel(top, text="状态:").pack(side="left", padx=(15, 0))
        self.combo_status = ctk.CTkComboBox(top, values=["全部", "正常", "停用", "缺货"], width=100)
        self.combo_status.pack(side="left", padx=8)
        self.combo_status.set("全部")

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset).pack(side="left", padx=5)

        ctk.CTkButton(top, text="新增材料", width=100, command=self._add).pack(side="right", padx=5)
        ctk.CTkButton(top, text="编辑", width=80, command=self._edit).pack(side="right", padx=5)
        ctk.CTkButton(top, text="删除", width=80, fg_color="#d9534f", command=self._delete).pack(side="right", padx=5)

        tree_frm = ctk.CTkFrame(self)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("code", "name", "spec", "stock", "safety", "shoe", "status")
        self.tree = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree.heading("code", text="材料编号")
        self.tree.heading("name", text="材料名称")
        self.tree.heading("spec", text="规格")
        self.tree.heading("stock", text="当前库存")
        self.tree.heading("safety", text="安全库存")
        self.tree.heading("shoe", text="适用鞋型")
        self.tree.heading("status", text="状态")

        self.tree.column("code", width=100, anchor="center")
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("spec", width=100, anchor="w")
        self.tree.column("stock", width=80, anchor="center")
        self.tree.column("safety", width=80, anchor="center")
        self.tree.column("shoe", width=120, anchor="w")
        self.tree.column("status", width=80, anchor="center")

        self.tree.tag_configure("low", background="#fff3cd")
        self.tree.tag_configure("out", background="#f8d7da")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _reset(self):
        self.entry_search.delete(0, "end")
        self.combo_status.set("全部")
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        keyword = self.entry_search.get().strip()
        status = self.combo_status.get()
        rows = db.get_materials(keyword, status)

        for r in rows:
            tag = ""
            if r["current_stock"] == 0:
                tag = "out"
            elif r["current_stock"] <= r["safety_stock"]:
                tag = "low"
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["material_code"],
                    r["material_name"],
                    r["material_spec"] or "",
                    r["current_stock"],
                    r["safety_stock"],
                    r["applicable_shoe_type"] or "",
                    r["material_status"],
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
        MaterialDialog(self, on_save=self.refresh)

    def _edit(self):
        mid = self._get_selected_id()
        if mid:
            MaterialDialog(self, material_id=mid, on_save=self.refresh)

    def _delete(self):
        mid = self._get_selected_id()
        if mid and messagebox.askyesno("确认", "确定要删除该材料吗?", parent=self):
            ok, msg = db.delete_material(mid)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self.refresh()
            else:
                messagebox.showerror("错误", msg, parent=self)
