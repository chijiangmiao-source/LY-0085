import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, date, timedelta
from typing import Optional, Callable
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
import database as db
from restock_frame import RestockFrame


class SupplierDialog(ctk.CTkToplevel):
    def __init__(self, master, supplier_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.supplier_id = supplier_id
        self.on_save = on_save
        self.title("编辑供应商" if supplier_id else "新增供应商")
        self.geometry("500x640")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        if supplier_id:
            self._load_data()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 7}
        frm = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="供应商编号 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.entry_code = ctk.CTkEntry(frm, width=280)
        self.entry_code.grid(row=0, column=1, **pad)

        ctk.CTkLabel(frm, text="供应商名称 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.entry_name = ctk.CTkEntry(frm, width=280)
        self.entry_name.grid(row=1, column=1, **pad)

        ctk.CTkLabel(frm, text="联系人", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.entry_contact = ctk.CTkEntry(frm, width=280)
        self.entry_contact.grid(row=2, column=1, **pad)

        ctk.CTkLabel(frm, text="联系电话", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_phone = ctk.CTkEntry(frm, width=280)
        self.entry_phone.grid(row=3, column=1, **pad)

        ctk.CTkLabel(frm, text="地址", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.entry_address = ctk.CTkEntry(frm, width=280)
        self.entry_address.grid(row=4, column=1, **pad)

        ctk.CTkLabel(frm, text="银行账户", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self.entry_bank = ctk.CTkEntry(frm, width=280)
        self.entry_bank.grid(row=5, column=1, **pad)

        ctk.CTkLabel(frm, text="税号", anchor="w").grid(row=6, column=0, sticky="w", **pad)
        self.entry_tax = ctk.CTkEntry(frm, width=280)
        self.entry_tax.grid(row=6, column=1, **pad)

        ctk.CTkLabel(frm, text="信用额度 (元)", anchor="w").grid(row=7, column=0, sticky="w", **pad)
        self.entry_credit = ctk.CTkEntry(frm, width=280)
        self.entry_credit.grid(row=7, column=1, **pad)
        self.entry_credit.insert(0, "0")

        ctk.CTkLabel(frm, text="账期天数", anchor="w").grid(row=8, column=0, sticky="w", **pad)
        self.entry_days = ctk.CTkEntry(frm, width=280)
        self.entry_days.grid(row=8, column=1, **pad)
        self.entry_days.insert(0, "30")

        ctk.CTkLabel(frm, text="供应商状态", anchor="w").grid(row=9, column=0, sticky="w", **pad)
        self.combo_status = ctk.CTkComboBox(frm, values=["正常", "停用", "黑名单"], width=280)
        self.combo_status.grid(row=9, column=1, **pad)
        self.combo_status.set("正常")

        ctk.CTkLabel(frm, text="备注", anchor="nw").grid(row=10, column=0, sticky="nw", **pad)
        self.text_remark = ctk.CTkTextbox(frm, width=280, height=60)
        self.text_remark.grid(row=10, column=1, **pad)

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=11, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=10)

    def _load_data(self):
        row = db.get_supplier_by_id(self.supplier_id)
        if row:
            self.entry_code.insert(0, row["supplier_code"])
            self.entry_name.insert(0, row["supplier_name"])
            self.entry_contact.insert(0, row["contact_person"] or "")
            self.entry_phone.insert(0, row["contact_phone"] or "")
            self.entry_address.insert(0, row["address"] or "")
            self.entry_bank.insert(0, row["bank_account"] or "")
            self.entry_tax.insert(0, row["tax_number"] or "")
            self.entry_credit.delete(0, "end")
            self.entry_credit.insert(0, str(row["credit_limit"] or 0))
            self.entry_days.delete(0, "end")
            self.entry_days.insert(0, str(row["payment_days"] or 30))
            self.combo_status.set(row["supplier_status"])
            if row["remark"]:
                self.text_remark.insert("1.0", row["remark"])

    def _on_save(self):
        try:
            credit_limit = float(self.entry_credit.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "信用额度必须是数字", parent=self)
            return
        try:
            payment_days = int(self.entry_days.get().strip() or "30")
        except ValueError:
            messagebox.showerror("错误", "账期天数必须是整数", parent=self)
            return

        data = {
            "supplier_code": self.entry_code.get().strip(),
            "supplier_name": self.entry_name.get().strip(),
            "contact_person": self.entry_contact.get().strip(),
            "contact_phone": self.entry_phone.get().strip(),
            "address": self.entry_address.get().strip(),
            "bank_account": self.entry_bank.get().strip(),
            "tax_number": self.entry_tax.get().strip(),
            "credit_limit": credit_limit,
            "payment_days": payment_days,
            "supplier_status": self.combo_status.get(),
            "remark": self.text_remark.get("1.0", "end").strip(),
        }

        if self.supplier_id:
            ok, msg = db.update_supplier(self.supplier_id, data)
        else:
            ok, msg = db.add_supplier(data)

        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self)


class PaymentDialog(ctk.CTkToplevel):
    def __init__(self, master, payment_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.payment_id = payment_id
        self.on_save = on_save
        self.title("编辑付款记录" if payment_id else "新增付款登记")
        self.geometry("560x640")
        self.resizable(False, False)
        self.grab_set()

        self._supplier_map = {}
        self._purchase_map = {}
        self._build_ui()
        self._load_suppliers()
        if payment_id:
            self._load_data()

    def _load_suppliers(self):
        rows = db.get_suppliers()
        values = []
        for r in rows:
            if r["supplier_status"] == "正常":
                label = f"{r['supplier_code']} - {r['supplier_name']}"
                self._supplier_map[label] = r["id"]
                values.append(label)
        self.combo_supplier.configure(values=values)
        self.combo_supplier.bind("<<ComboboxSelected>>", lambda e: self._load_purchases())

    def _load_purchases(self):
        supplier_label = self.combo_supplier.get().strip()
        supplier_id = self._supplier_map.get(supplier_label)
        self._purchase_map = {}
        values = []
        if supplier_id:
            rows = db.get_unpaid_purchases(supplier_id)
            for r in rows:
                label = f"[{r['purchase_date']}] {r['material_code']} - {r['material_name']} x{r['purchase_quantity']} = ¥{r['total_amount']:.2f}"
                self._purchase_map[label] = r["id"]
                values.append(label)
        self.combo_purchase.configure(values=values)
        if values:
            self.combo_purchase.set(values[0])
            self._auto_fill()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 7}
        frm = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="供应商 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.combo_supplier = ctk.CTkComboBox(frm, values=[], width=320)
        self.combo_supplier.grid(row=0, column=1, **pad)

        ctk.CTkLabel(frm, text="采购记录 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.combo_purchase = ctk.CTkComboBox(frm, values=[], width=320)
        self.combo_purchase.grid(row=1, column=1, **pad)
        self.combo_purchase.bind("<<ComboboxSelected>>", lambda e: self._auto_fill())

        ctk.CTkLabel(frm, text="应付金额 (元) *", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.entry_payable = ctk.CTkEntry(frm, width=320)
        self.entry_payable.grid(row=2, column=1, **pad)
        self.entry_payable.insert(0, "0.00")

        ctk.CTkLabel(frm, text="已付金额 (元)", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_paid = ctk.CTkEntry(frm, width=320)
        self.entry_paid.grid(row=3, column=1, **pad)
        self.entry_paid.insert(0, "0.00")

        ctk.CTkLabel(frm, text="付款日期", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.date_payment = DateEntry(
            frm,
            width=28,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
            font=("Arial", 11),
        )
        self.date_payment.grid(row=4, column=1, sticky="w", **pad)

        ctk.CTkLabel(frm, text="付款状态", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self.combo_status = ctk.CTkComboBox(
            frm, values=["未付款", "部分付款", "已付款", "逾期"], width=320
        )
        self.combo_status.grid(row=5, column=1, **pad)
        self.combo_status.set("未付款")

        ctk.CTkLabel(frm, text="备注", anchor="nw").grid(row=6, column=0, sticky="nw", **pad)
        self.text_remark = ctk.CTkTextbox(frm, width=320, height=80)
        self.text_remark.grid(row=6, column=1, **pad)

        self.lbl_hint = ctk.CTkLabel(frm, text="", text_color="gray", font=("Arial", 10))
        self.lbl_hint.grid(row=7, column=0, columnspan=2, pady=(0, 5))

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=8, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frm, text="自动计算状态", width=120, command=self._auto_status).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=5)

    def _auto_fill(self):
        purchase_label = self.combo_purchase.get().strip()
        purchase_id = self._purchase_map.get(purchase_label)
        if purchase_id:
            for r in db.get_unpaid_purchases():
                if r["id"] == purchase_id:
                    self.entry_payable.delete(0, "end")
                    self.entry_payable.insert(0, f"{r['total_amount']:.2f}")
                    self.lbl_hint.configure(
                        text=f"账期: {r['payment_days'] or 30}天 | 到期日需根据采购日期自动计算",
                        text_color="#2980b9",
                    )
                    break

    def _auto_status(self):
        try:
            payable = float(self.entry_payable.get().strip() or "0")
        except ValueError:
            payable = 0
        try:
            paid = float(self.entry_paid.get().strip() or "0")
        except ValueError:
            paid = 0

        purchase_label = self.combo_purchase.get().strip()
        purchase_id = self._purchase_map.get(purchase_label)
        due_date = ""
        if purchase_id:
            for r in db.get_unpaid_purchases():
                if r["id"] == purchase_id:
                    try:
                        pd = datetime.strptime(r["purchase_date"], "%Y-%m-%d")
                        days = r["payment_days"] or 30
                        due_date = (pd + timedelta(days=days)).strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    break

        status = db._calc_payment_status(payable, paid, due_date)
        self.combo_status.set(status)
        self.lbl_hint.configure(text=f"自动计算状态: {status}", text_color="#27ae60")

    def _load_data(self):
        row = db.get_purchase_payment_by_id(self.payment_id)
        if not row:
            return

        supplier_label = None
        for label, sid in self._supplier_map.items():
            if label.endswith(row["supplier_name"] or "") or " - " in label:
                pass
        all_suppliers = db.get_suppliers()
        for s in all_suppliers:
            label = f"{s['supplier_code']} - {s['supplier_name']}"
            if s["id"] == row["supplier_id"]:
                supplier_label = label
                self._supplier_map[label] = s["id"]
                break
        if supplier_label:
            if supplier_label not in self.combo_supplier.cget("values"):
                current = list(self.combo_supplier.cget("values"))
                current.append(supplier_label)
                self.combo_supplier.configure(values=current)
            self.combo_supplier.set(supplier_label)

        self.entry_payable.delete(0, "end")
        self.entry_payable.insert(0, f"{row['payable_amount']:.2f}")
        self.entry_paid.delete(0, "end")
        self.entry_paid.insert(0, f"{row['paid_amount']:.2f}")
        self.combo_status.set(row["payment_status"])
        if row["payment_date"]:
            try:
                dt = datetime.strptime(row["payment_date"], "%Y-%m-%d")
                self.date_payment.set_date(dt)
            except Exception:
                pass
        if row["remark"]:
            self.text_remark.insert("1.0", row["remark"])

        self.combo_purchase.configure(state="disabled")

    def _on_save(self):
        supplier_label = self.combo_supplier.get().strip()
        if supplier_label not in self._supplier_map:
            messagebox.showerror("错误", "请选择供应商", parent=self)
            return
        supplier_id = self._supplier_map[supplier_label]

        purchase_label = self.combo_purchase.get().strip()
        if self.payment_id:
            row = db.get_purchase_payment_by_id(self.payment_id)
            purchase_id = row["purchase_id"] if row else None
        else:
            purchase_id = self._purchase_map.get(purchase_label)
        if not purchase_id:
            messagebox.showerror("错误", "请选择采购记录", parent=self)
            return

        try:
            payable_amount = float(self.entry_payable.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "应付金额必须是数字", parent=self)
            return
        try:
            paid_amount = float(self.entry_paid.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "已付金额必须是数字", parent=self)
            return

        payment_date = self.date_payment.get_date().strftime("%Y-%m-%d") if paid_amount > 0 else None
        remark = self.text_remark.get("1.0", "end").strip()

        data = {
            "purchase_id": purchase_id,
            "supplier_id": supplier_id,
            "payable_amount": payable_amount,
            "paid_amount": paid_amount,
            "payment_date": payment_date,
            "payment_status": self.combo_status.get(),
            "remark": remark,
        }

        if self.payment_id:
            ok, msg = db.update_purchase_payment(self.payment_id, data)
        else:
            ok, msg = db.add_purchase_payment(data)

        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self)


class SupplierFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self):
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.pack(fill="x", padx=15, pady=(10, 5))

        self.btn_tab_supplier = ctk.CTkButton(tab_bar, text="🏢 供应商档案", width=130, height=36,
                                               fg_color="#347ab8", command=lambda: self._switch_tab("supplier"))
        self.btn_tab_supplier.pack(side="left", padx=3)

        self.btn_tab_payment = ctk.CTkButton(tab_bar, text="💳 采购对账", width=130, height=36,
                                              fg_color="#95a5a6", command=lambda: self._switch_tab("payment"))
        self.btn_tab_payment.pack(side="left", padx=3)

        self.btn_tab_stats = ctk.CTkButton(tab_bar, text="📊 统计报表", width=130, height=36,
                                            fg_color="#95a5a6", command=lambda: self._switch_tab("stats"))
        self.btn_tab_stats.pack(side="left", padx=3)

        self.btn_tab_warn = ctk.CTkButton(tab_bar, text="⚠ 逾期提醒", width=130, height=36,
                                           fg_color="#95a5a6", command=lambda: self._switch_tab("warn"))
        self.btn_tab_warn.pack(side="left", padx=3)

        self.btn_tab_restock = ctk.CTkButton(tab_bar, text="📦 采购补货", width=130, height=36,
                                              fg_color="#95a5a6", command=lambda: self._switch_tab("restock"))
        self.btn_tab_restock.pack(side="left", padx=3)

        self.supplier_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_supplier_ui()

        self.payment_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_payment_ui()

        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_stats_ui()

        self.warn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_warn_ui()

        self.restock_frame = RestockFrame(self)

        self._switch_tab("supplier")

    def _build_supplier_ui(self):
        top = ctk.CTkFrame(self.supplier_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(top, text="关键词:").pack(side="left")
        self.entry_s_search = ctk.CTkEntry(top, width=200, placeholder_text="编号/名称/联系人/电话")
        self.entry_s_search.pack(side="left", padx=8)

        ctk.CTkLabel(top, text="状态:").pack(side="left", padx=(15, 0))
        self.combo_s_status = ctk.CTkComboBox(top, values=["全部", "正常", "停用", "黑名单"], width=100)
        self.combo_s_status.pack(side="left", padx=8)
        self.combo_s_status.set("全部")

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh_suppliers).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset_supplier).pack(side="left", padx=5)

        ctk.CTkButton(top, text="新增供应商", width=100, command=self._add_supplier).pack(side="right", padx=5)
        ctk.CTkButton(top, text="编辑", width=80, command=self._edit_supplier).pack(side="right", padx=5)
        ctk.CTkButton(top, text="删除", width=80, fg_color="#d9534f", command=self._delete_supplier).pack(side="right", padx=5)

        tree_frm = ctk.CTkFrame(self.supplier_frame)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("code", "name", "contact", "phone", "credit", "days", "status", "remark")
        self.tree_supplier = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree_supplier.heading("code", text="供应商编号")
        self.tree_supplier.heading("name", text="供应商名称")
        self.tree_supplier.heading("contact", text="联系人")
        self.tree_supplier.heading("phone", text="联系电话")
        self.tree_supplier.heading("credit", text="信用额度")
        self.tree_supplier.heading("days", text="账期")
        self.tree_supplier.heading("status", text="状态")
        self.tree_supplier.heading("remark", text="备注")

        self.tree_supplier.column("code", width=100, anchor="center")
        self.tree_supplier.column("name", width=160, anchor="w")
        self.tree_supplier.column("contact", width=80, anchor="center")
        self.tree_supplier.column("phone", width=110, anchor="center")
        self.tree_supplier.column("credit", width=90, anchor="e")
        self.tree_supplier.column("days", width=60, anchor="center")
        self.tree_supplier.column("status", width=70, anchor="center")
        self.tree_supplier.column("remark", width=200, anchor="w")

        self.tree_supplier.tag_configure("bad", background="#f8d7da")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_supplier.yview)
        self.tree_supplier.configure(yscrollcommand=vsb.set)
        self.tree_supplier.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _build_payment_ui(self):
        top = ctk.CTkFrame(self.payment_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(top, text="开始日期:").pack(side="left")
        self.date_p_start = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_p_start.pack(side="left", padx=5)
        self.date_p_start.set_date(date(2000, 1, 1))

        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_p_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_p_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="关键词:").pack(side="left", padx=(15, 0))
        self.entry_p_search = ctk.CTkEntry(top, width=160, placeholder_text="供应商/材料")
        self.entry_p_search.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="状态:").pack(side="left", padx=(10, 0))
        self.combo_p_status = ctk.CTkComboBox(top, values=["全部", "未付款", "部分付款", "已付款", "逾期"], width=90)
        self.combo_p_status.pack(side="left", padx=5)
        self.combo_p_status.set("全部")

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh_payments).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset_payment).pack(side="left", padx=5)

        ctk.CTkButton(top, text="新增付款", width=100, command=self._add_payment).pack(side="right", padx=5)
        ctk.CTkButton(top, text="编辑", width=80, command=self._edit_payment).pack(side="right", padx=5)
        ctk.CTkButton(top, text="删除", width=80, fg_color="#d9534f", command=self._delete_payment).pack(side="right", padx=5)

        stat_frm = ctk.CTkFrame(self.payment_frame, fg_color="transparent")
        stat_frm.pack(fill="x", padx=15, pady=(0, 5))

        self.lbl_payable = ctk.CTkLabel(stat_frm, text="应付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e74c3c")
        self.lbl_payable.pack(side="left", padx=10)
        self.lbl_paid = ctk.CTkLabel(stat_frm, text="已付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#27ae60")
        self.lbl_paid.pack(side="left", padx=10)
        self.lbl_unpaid = ctk.CTkLabel(stat_frm, text="未付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22")
        self.lbl_unpaid.pack(side="left", padx=10)
        self.lbl_p_count = ctk.CTkLabel(stat_frm, text="记录数: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#8e44ad")
        self.lbl_p_count.pack(side="left", padx=10)

        tree_frm = ctk.CTkFrame(self.payment_frame)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("date", "supplier", "material", "qty", "payable", "paid", "unpaid", "status", "pay_date", "remark")
        self.tree_payment = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree_payment.heading("date", text="采购日期")
        self.tree_payment.heading("supplier", text="供应商")
        self.tree_payment.heading("material", text="材料")
        self.tree_payment.heading("qty", text="数量")
        self.tree_payment.heading("payable", text="应付")
        self.tree_payment.heading("paid", text="已付")
        self.tree_payment.heading("unpaid", text="未付")
        self.tree_payment.heading("status", text="状态")
        self.tree_payment.heading("pay_date", text="付款日期")
        self.tree_payment.heading("remark", text="备注")

        self.tree_payment.column("date", width=90, anchor="center")
        self.tree_payment.column("supplier", width=130, anchor="w")
        self.tree_payment.column("material", width=150, anchor="w")
        self.tree_payment.column("qty", width=60, anchor="center")
        self.tree_payment.column("payable", width=80, anchor="e")
        self.tree_payment.column("paid", width=80, anchor="e")
        self.tree_payment.column("unpaid", width=80, anchor="e")
        self.tree_payment.column("status", width=70, anchor="center")
        self.tree_payment.column("pay_date", width=90, anchor="center")
        self.tree_payment.column("remark", width=150, anchor="w")

        self.tree_payment.tag_configure("overdue", background="#f8d7da")
        self.tree_payment.tag_configure("partial", background="#fff3cd")
        self.tree_payment.tag_configure("paid", background="#d4edda")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_payment.yview)
        self.tree_payment.configure(yscrollcommand=vsb.set)
        self.tree_payment.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _build_stats_ui(self):
        top = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top, text="开始日期:").pack(side="left")
        self.date_st_start = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_st_start.pack(side="left", padx=5)
        self.date_st_start.set_date(date.today() - timedelta(days=90))

        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_st_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_st_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="趋势月数:").pack(side="left", padx=(15, 0))
        self.combo_months = ctk.CTkComboBox(top, values=["3", "6", "12", "24"], width=60)
        self.combo_months.set("12")
        self.combo_months.pack(side="left", padx=5)

        ctk.CTkButton(top, text="刷新统计", width=100, command=self.refresh_all_stats).pack(side="left", padx=10)

        self.stats_frame.grid_columnconfigure(0, weight=1)
        self.stats_frame.grid_columnconfigure(1, weight=1)
        self.stats_frame.grid_rowconfigure(2, weight=1)

        chart_frm = ctk.CTkFrame(self.stats_frame, corner_radius=8)
        chart_frm.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=15, pady=(5, 10))
        chart_frm.grid_columnconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(0, weight=1)
        self.fig_trend = Figure(figsize=(8, 2.8), dpi=100)
        self.canvas_trend = FigureCanvasTkAgg(self.fig_trend, master=chart_frm)
        self.canvas_trend.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        debt_box = ctk.CTkFrame(self.stats_frame, corner_radius=8)
        debt_box.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=(5, 15))
        debt_box.grid_columnconfigure(0, weight=1)
        debt_box.grid_rowconfigure(1, weight=1)

        debt_header = ctk.CTkFrame(debt_box, fg_color="transparent")
        debt_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(debt_header, text="💰 供应商欠款汇总", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e74c3c").pack(side="left")
        self.lbl_debt_summary = ctk.CTkLabel(debt_header, text="", font=ctk.CTkFont(size=12))
        self.lbl_debt_summary.pack(side="right")

        debt_cols = ("rank", "code", "name", "total_payable", "total_paid", "unpaid", "count", "credit_usage")
        self.tree_debt = ttk.Treeview(debt_box, columns=debt_cols, show="headings", height=12)
        self.tree_debt.heading("rank", text="#")
        self.tree_debt.heading("code", text="编号")
        self.tree_debt.heading("name", text="供应商名称")
        self.tree_debt.heading("total_payable", text="应付总额")
        self.tree_debt.heading("total_paid", text="已付总额")
        self.tree_debt.heading("unpaid", text="欠款金额")
        self.tree_debt.heading("count", text="未结笔数")
        self.tree_debt.heading("credit_usage", text="额度使用")

        self.tree_debt.column("rank", width=30, anchor="center")
        self.tree_debt.column("code", width=80, anchor="center")
        self.tree_debt.column("name", width=140, anchor="w")
        self.tree_debt.column("total_payable", width=85, anchor="e")
        self.tree_debt.column("total_paid", width=85, anchor="e")
        self.tree_debt.column("unpaid", width=85, anchor="e")
        self.tree_debt.column("count", width=65, anchor="center")
        self.tree_debt.column("credit_usage", width=75, anchor="center")

        self.tree_debt.tag_configure("high", background="#f8d7da")
        self.tree_debt.tag_configure("warn", background="#fff3cd")

        vsb_debt = ttk.Scrollbar(debt_box, orient="vertical", command=self.tree_debt.yview)
        self.tree_debt.configure(yscrollcommand=vsb_debt.set)
        self.tree_debt.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_debt.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

        rank_box = ctk.CTkFrame(self.stats_frame, corner_radius=8)
        rank_box.grid(row=2, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        rank_box.grid_columnconfigure(0, weight=1)
        rank_box.grid_rowconfigure(1, weight=1)

        rank_header = ctk.CTkFrame(rank_box, fg_color="transparent")
        rank_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(rank_header, text="🏆 材料采购金额排行", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2980b9").pack(side="left")
        self.lbl_rank_info = ctk.CTkLabel(rank_header, text="", font=ctk.CTkFont(size=12))
        self.lbl_rank_info.pack(side="right")

        rank_cols = ("rank", "code", "name", "spec", "total_qty", "total_amount", "count", "avg_price")
        self.tree_rank = ttk.Treeview(rank_box, columns=rank_cols, show="headings", height=12)
        self.tree_rank.heading("rank", text="#")
        self.tree_rank.heading("code", text="材料编号")
        self.tree_rank.heading("name", text="材料名称")
        self.tree_rank.heading("spec", text="规格")
        self.tree_rank.heading("total_qty", text="采购数量")
        self.tree_rank.heading("total_amount", text="采购金额")
        self.tree_rank.heading("count", text="采购次数")
        self.tree_rank.heading("avg_price", text="平均单价")

        self.tree_rank.column("rank", width=30, anchor="center")
        self.tree_rank.column("code", width=80, anchor="center")
        self.tree_rank.column("name", width=120, anchor="w")
        self.tree_rank.column("spec", width=70, anchor="w")
        self.tree_rank.column("total_qty", width=70, anchor="center")
        self.tree_rank.column("total_amount", width=85, anchor="e")
        self.tree_rank.column("count", width=65, anchor="center")
        self.tree_rank.column("avg_price", width=75, anchor="e")

        self.tree_rank.tag_configure("top3", background="#fdebd0")

        vsb_rank = ttk.Scrollbar(rank_box, orient="vertical", command=self.tree_rank.yview)
        self.tree_rank.configure(yscrollcommand=vsb_rank.set)
        self.tree_rank.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_rank.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

    def _build_warn_ui(self):
        top = ctk.CTkFrame(self.warn_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top, text="🔔 逾期未付款提醒", font=ctk.CTkFont(size=16, weight="bold"), text_color="#c0392b").pack(side="left")
        self.lbl_overdue_count = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self.lbl_overdue_count.pack(side="right")

        ctk.CTkButton(top, text="刷新", width=80, command=self.refresh_warnings).pack(side="right", padx=10)

        info_box = ctk.CTkFrame(self.warn_frame, fg_color="transparent")
        info_box.pack(fill="x", padx=15, pady=(0, 5))
        self.lbl_total_overdue = ctk.CTkLabel(info_box, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e74c3c")
        self.lbl_total_overdue.pack(side="left", padx=5)
        self.lbl_overdue_amount = ctk.CTkLabel(info_box, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22")
        self.lbl_overdue_amount.pack(side="left", padx=15)

        tree_frm = ctk.CTkFrame(self.warn_frame)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("overdue_days", "supplier", "purchase_date", "due_date", "material", "payable", "paid", "unpaid", "contact", "phone", "status", "remark")
        self.tree_warn = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree_warn.heading("overdue_days", text="逾期天数")
        self.tree_warn.heading("supplier", text="供应商")
        self.tree_warn.heading("purchase_date", text="采购日期")
        self.tree_warn.heading("due_date", text="到期日期")
        self.tree_warn.heading("material", text="材料")
        self.tree_warn.heading("payable", text="应付")
        self.tree_warn.heading("paid", text="已付")
        self.tree_warn.heading("unpaid", text="未付")
        self.tree_warn.heading("contact", text="联系人")
        self.tree_warn.heading("phone", text="联系电话")
        self.tree_warn.heading("status", text="状态")
        self.tree_warn.heading("remark", text="备注")

        self.tree_warn.column("overdue_days", width=80, anchor="center")
        self.tree_warn.column("supplier", width=130, anchor="w")
        self.tree_warn.column("purchase_date", width=90, anchor="center")
        self.tree_warn.column("due_date", width=90, anchor="center")
        self.tree_warn.column("material", width=150, anchor="w")
        self.tree_warn.column("payable", width=75, anchor="e")
        self.tree_warn.column("paid", width=75, anchor="e")
        self.tree_warn.column("unpaid", width=75, anchor="e")
        self.tree_warn.column("contact", width=70, anchor="center")
        self.tree_warn.column("phone", width=100, anchor="center")
        self.tree_warn.column("status", width=70, anchor="center")
        self.tree_warn.column("remark", width=150, anchor="w")

        self.tree_warn.tag_configure("overdue30", background="#f8d7da")
        self.tree_warn.tag_configure("overdue15", background="#fdebd0")
        self.tree_warn.tag_configure("overdue7", background="#fff3cd")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_warn.yview)
        self.tree_warn.configure(yscrollcommand=vsb.set)
        self.tree_warn.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _switch_tab(self, tab_name: str):
        self.supplier_frame.pack_forget()
        self.payment_frame.pack_forget()
        self.stats_frame.pack_forget()
        self.warn_frame.pack_forget()
        self.restock_frame.pack_forget()

        self.btn_tab_supplier.configure(fg_color="#95a5a6")
        self.btn_tab_payment.configure(fg_color="#95a5a6")
        self.btn_tab_stats.configure(fg_color="#95a5a6")
        self.btn_tab_warn.configure(fg_color="#95a5a6")
        self.btn_tab_restock.configure(fg_color="#95a5a6")

        if tab_name == "supplier":
            self.supplier_frame.pack(fill="both", expand=True)
            self.btn_tab_supplier.configure(fg_color="#347ab8")
            self.refresh_suppliers()
        elif tab_name == "payment":
            self.payment_frame.pack(fill="both", expand=True)
            self.btn_tab_payment.configure(fg_color="#347ab8")
            self.refresh_payments()
        elif tab_name == "stats":
            self.stats_frame.pack(fill="both", expand=True)
            self.btn_tab_stats.configure(fg_color="#347ab8")
            self.refresh_all_stats()
        elif tab_name == "warn":
            self.warn_frame.pack(fill="both", expand=True)
            self.btn_tab_warn.configure(fg_color="#347ab8")
            self.refresh_warnings()
        elif tab_name == "restock":
            self.restock_frame.pack(fill="both", expand=True)
            self.btn_tab_restock.configure(fg_color="#347ab8")
            self.restock_frame.refresh()

    def _reset_supplier(self):
        self.entry_s_search.delete(0, "end")
        self.combo_s_status.set("全部")
        self.refresh_suppliers()

    def _reset_payment(self):
        self.date_p_start.set_date(date(2000, 1, 1))
        self.date_p_end.set_date(date.today())
        self.entry_p_search.delete(0, "end")
        self.combo_p_status.set("全部")
        self.refresh_payments()

    def refresh_suppliers(self):
        for item in self.tree_supplier.get_children():
            self.tree_supplier.delete(item)

        keyword = self.entry_s_search.get().strip()
        status = self.combo_s_status.get()
        rows = db.get_suppliers(keyword, status)

        for r in rows:
            tag = ""
            if r["supplier_status"] in ("停用", "黑名单"):
                tag = "bad"
            self.tree_supplier.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["supplier_code"],
                    r["supplier_name"],
                    r["contact_person"] or "",
                    r["contact_phone"] or "",
                    f"¥{r['credit_limit']:.2f}",
                    f"{r['payment_days']}天",
                    r["supplier_status"],
                    (r["remark"] or "")[:30],
                ),
                tags=(tag,),
            )

    def refresh_payments(self):
        for item in self.tree_payment.get_children():
            self.tree_payment.delete(item)

        start_date = self.date_p_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_p_end.get_date().strftime("%Y-%m-%d")
        keyword = self.entry_p_search.get().strip()
        status = self.combo_p_status.get()
        rows = db.get_purchase_payments(start_date, end_date, keyword, None, status)

        total_payable = 0.0
        total_paid = 0.0
        for r in rows:
            payable = r["payable_amount"] or 0
            paid = r["paid_amount"] or 0
            unpaid = round(payable - paid, 2)
            total_payable += payable
            total_paid += paid

            tag = ""
            st = r["payment_status"]
            if st == "已付款":
                tag = "paid"
            elif st == "逾期":
                tag = "overdue"
            elif st == "部分付款":
                tag = "partial"

            sup_name = r["supplier_name"] or r["supplier"] or "未知供应商"
            mat_name = f"{r['material_code'] or ''} - {r['material_name'] or ''}"

            self.tree_payment.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["purchase_date"] or "",
                    sup_name,
                    mat_name,
                    r["purchase_quantity"] or 0,
                    f"¥{payable:.2f}",
                    f"¥{paid:.2f}",
                    f"¥{unpaid:.2f}",
                    st,
                    r["payment_date"] or "",
                    (r["remark"] or "")[:25],
                ),
                tags=(tag,),
            )

        self.lbl_payable.configure(text=f"应付总额: ¥{total_payable:.2f}")
        self.lbl_paid.configure(text=f"已付总额: ¥{total_paid:.2f}")
        self.lbl_unpaid.configure(text=f"未付总额: ¥{total_payable - total_paid:.2f}")
        self.lbl_p_count.configure(text=f"记录数: {len(rows)}")

    def refresh_all_stats(self):
        self.refresh_debt_summary()
        self.refresh_material_rank()
        self._draw_monthly_trend()

    def refresh_debt_summary(self):
        for item in self.tree_debt.get_children():
            self.tree_debt.delete(item)

        start_date = self.date_st_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_st_end.get_date().strftime("%Y-%m-%d")
        data = db.get_supplier_debt_summary(start_date, end_date)

        total_unpaid = 0.0
        total_payable = 0.0
        for idx, d in enumerate(data, 1):
            total_unpaid += d["unpaid_amount"]
            total_payable += d["total_payable"]

            tag = ""
            if d["unpaid_amount"] > 0:
                if d["credit_usage"] >= 80:
                    tag = "high"
                elif d["credit_usage"] >= 50:
                    tag = "warn"

            self.tree_debt.insert(
                "",
                "end",
                values=(
                    f"#{idx}",
                    d["supplier_code"],
                    d["supplier_name"],
                    f"¥{d['total_payable']:.2f}",
                    f"¥{d['total_paid']:.2f}",
                    f"¥{d['unpaid_amount']:.2f}",
                    d["unpaid_count"],
                    f"{d['credit_usage']:.1f}%",
                ),
                tags=(tag,),
            )

        self.lbl_debt_summary.configure(
            text=f"应付总额: ¥{total_payable:.2f} | 欠款总额: ¥{total_unpaid:.2f}"
        )

    def refresh_material_rank(self):
        for item in self.tree_rank.get_children():
            self.tree_rank.delete(item)

        start_date = self.date_st_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_st_end.get_date().strftime("%Y-%m-%d")
        data = db.get_material_purchase_rank(start_date, end_date, top_n=20)

        total_amount = sum(d["total_amount"] for d in data)
        for idx, d in enumerate(data, 1):
            tag = ""
            if idx <= 3:
                tag = "top3"
            self.tree_rank.insert(
                "",
                "end",
                values=(
                    f"#{idx}",
                    d["material_code"],
                    d["material_name"],
                    d["material_spec"] or "",
                    d["total_qty"],
                    f"¥{d['total_amount']:.2f}",
                    d["purchase_count"],
                    f"¥{d['avg_price']:.2f}",
                ),
                tags=(tag,),
            )

        self.lbl_rank_info.configure(text=f"Top {len(data)} | 总金额: ¥{total_amount:.2f}")

    def _draw_monthly_trend(self):
        months = int(self.combo_months.get())
        data = db.get_monthly_purchase_trend(months)
        self.fig_trend.clear()
        ax = self.fig_trend.add_subplot(111)
        if data:
            df = pd.DataFrame(data)
            ax.bar(df["month"], df["total_amount"], color="#3498db", alpha=0.8, label="采购金额(元)")
            ax2 = ax.twinx()
            ax2.plot(df["month"], df["purchase_count"], marker="o", color="#e74c3c", linewidth=2, label="采购次数")
            ax.set_title(f"近 {months} 个月采购支出趋势")
            ax.set_xlabel("月份")
            ax.set_ylabel("采购金额 (元)")
            ax2.set_ylabel("采购次数")
            ax.grid(True, alpha=0.3, axis="y")
            for tick in ax.get_xticklabels():
                tick.set_rotation(45)
                tick.set_fontsize(8)

            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        else:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=14)
            ax.set_title("月度采购支出趋势")
        self.fig_trend.tight_layout()
        self.canvas_trend.draw()

    def refresh_warnings(self):
        for item in self.tree_warn.get_children():
            self.tree_warn.delete(item)

        data = db.get_overdue_payments()
        overdue_list = [d for d in data if d["is_overdue"]]

        total_unpaid = sum(d["unpaid_amount"] for d in overdue_list)
        self.lbl_overdue_count.configure(text=f"共 {len(overdue_list)} 笔逾期付款")
        self.lbl_total_overdue.configure(text=f"逾期笔数: {len(overdue_list)}")
        self.lbl_overdue_amount.configure(text=f"逾期未付总额: ¥{total_unpaid:.2f}")

        for d in overdue_list:
            tag = ""
            if d["overdue_days"] >= 30:
                tag = "overdue30"
            elif d["overdue_days"] >= 15:
                tag = "overdue15"
            elif d["overdue_days"] >= 7:
                tag = "overdue7"

            mat_name = f"{d['material_code'] or ''} - {d['material_name'] or ''}"
            self.tree_warn.insert(
                "",
                "end",
                iid=str(d["payment_id"]),
                values=(
                    f"{d['overdue_days']}天",
                    d["supplier_name"] or "",
                    d["purchase_date"],
                    d["due_date"],
                    mat_name,
                    f"¥{d['payable_amount']:.2f}",
                    f"¥{d['paid_amount']:.2f}",
                    f"¥{d['unpaid_amount']:.2f}",
                    d["contact_person"] or "",
                    d["contact_phone"] or "",
                    d["payment_status"],
                    (d["remark"] or "")[:25],
                ),
                tags=(tag,),
            )

    def _get_selected_supplier_id(self) -> Optional[int]:
        sel = self.tree_supplier.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条供应商记录", parent=self)
            return None
        return int(sel[0])

    def _get_selected_payment_id(self) -> Optional[int]:
        sel = self.tree_payment.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条付款记录", parent=self)
            return None
        return int(sel[0])

    def _add_supplier(self):
        SupplierDialog(self, on_save=self.refresh_suppliers)

    def _edit_supplier(self):
        sid = self._get_selected_supplier_id()
        if sid:
            SupplierDialog(self, supplier_id=sid, on_save=self.refresh_suppliers)

    def _delete_supplier(self):
        sid = self._get_selected_supplier_id()
        if sid and messagebox.askyesno("确认", "确定要删除该供应商吗?", parent=self):
            ok, msg = db.delete_supplier(sid)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self.refresh_suppliers()
            else:
                messagebox.showerror("错误", msg, parent=self)

    def _add_payment(self):
        PaymentDialog(self, on_save=self._on_payment_change)

    def _edit_payment(self):
        pid = self._get_selected_payment_id()
        if pid:
            PaymentDialog(self, payment_id=pid, on_save=self._on_payment_change)

    def _delete_payment(self):
        pid = self._get_selected_payment_id()
        if pid and messagebox.askyesno("确认", "确定要删除该付款记录吗?", parent=self):
            ok, msg = db.delete_purchase_payment(pid)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self._on_payment_change()
            else:
                messagebox.showerror("错误", msg, parent=self)

    def _on_payment_change(self):
        self.refresh_payments()

    def refresh_all(self):
        self.refresh_suppliers()
        self.refresh_payments()
        self.refresh_all_stats()
        self.refresh_warnings()
