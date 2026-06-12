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


class PaymentRecordDialog(ctk.CTkToplevel):
    def __init__(self, master, purchase_id: Optional[int] = None, supplier_id: Optional[int] = None,
                 record_id: Optional[int] = None, on_save: Optional[Callable] = None):
        super().__init__(master)
        self.purchase_id = purchase_id
        self.supplier_id = supplier_id
        self.record_id = record_id
        self.on_save = on_save
        self.title("编辑付款流水" if record_id else "新增付款登记")
        self.geometry("520x620")
        self.resizable(False, False)
        self.grab_set()

        self._supplier_map = {}
        self._purchase_map = {}
        self._build_ui()
        self._load_suppliers()
        if record_id:
            self._load_data()
        elif purchase_id and supplier_id:
            self._auto_fill_purchase()

    def _load_suppliers(self):
        rows = db.get_suppliers()
        values = []
        for r in rows:
            if r["supplier_status"] == "正常":
                label = f"{r['supplier_code']} - {r['supplier_name']}"
                self._supplier_map[label] = r["id"]
                values.append(label)
        self.combo_supplier.configure(values=values)
        if self.supplier_id:
            for label, sid in self._supplier_map.items():
                if sid == self.supplier_id:
                    self.combo_supplier.set(label)
                    self._load_purchases()
                    break
        self.combo_supplier.bind("<<ComboboxSelected>>", lambda e: self._load_purchases())

    def _load_purchases(self):
        supplier_label = self.combo_supplier.get().strip()
        supplier_id = self._supplier_map.get(supplier_label)
        self._purchase_map = {}
        values = []
        if supplier_id:
            rows = db.get_unpaid_purchases(supplier_id)
            for r in rows:
                paid = r["paid_amount"] or 0
                total = r["total_amount"] or 0
                remaining = round(total - paid, 2)
                label = f"[{r['purchase_date']}] {r['material_code']} - {r['material_name']} x{r['purchase_quantity']} = ¥{total:.2f} (剩余: ¥{remaining:.2f})"
                self._purchase_map[label] = r["id"]
                values.append(label)
        self.combo_purchase.configure(values=values)
        if self.purchase_id:
            for label, pid in self._purchase_map.items():
                if pid == self.purchase_id:
                    self.combo_purchase.set(label)
                    self._auto_fill_purchase()
                    break
        elif values and not self.record_id:
            self.combo_purchase.set(values[0])
            self._auto_fill_purchase()
        self.combo_purchase.bind("<<ComboboxSelected>>", lambda e: self._auto_fill_purchase())

    def _auto_fill_purchase(self):
        purchase_label = self.combo_purchase.get().strip()
        purchase_id = self._purchase_map.get(purchase_label)
        if purchase_id:
            rows = db.get_unpaid_purchases()
            for r in rows:
                if r["id"] == purchase_id:
                    paid = r["paid_amount"] or 0
                    total = r["total_amount"] or 0
                    remaining = round(total - paid, 2)
                    self.entry_payable.delete(0, "end")
                    self.entry_payable.insert(0, f"{total:.2f}")
                    self.entry_paid.delete(0, "end")
                    self.entry_paid.insert(0, f"{paid:.2f}")
                    self.entry_remaining.delete(0, "end")
                    self.entry_remaining.insert(0, f"{remaining:.2f}")
                    self.entry_amount.delete(0, "end")
                    self.entry_amount.insert(0, f"{remaining:.2f}")
                    try:
                        pd = datetime.strptime(r["purchase_date"], "%Y-%m-%d")
                        days = r["payment_days"] or 30
                        due_date = (pd + timedelta(days=days)).strftime("%Y-%m-%d")
                        self.lbl_hint.configure(
                            text=f"账期: {days}天 | 到期日: {due_date}",
                            text_color="#2980b9",
                        )
                    except Exception:
                        self.lbl_hint.configure(text="", text_color="gray")
                    break

    def _build_ui(self):
        pad = {"padx": 15, "pady": 7}
        frm = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="供应商 *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.combo_supplier = ctk.CTkComboBox(frm, values=[], width=300)
        self.combo_supplier.grid(row=0, column=1, **pad)

        ctk.CTkLabel(frm, text="采购记录 *", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.combo_purchase = ctk.CTkComboBox(frm, values=[], width=300)
        self.combo_purchase.grid(row=1, column=1, **pad)

        ctk.CTkLabel(frm, text="应付总额 (元)", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.entry_payable = ctk.CTkEntry(frm, width=300)
        self.entry_payable.grid(row=2, column=1, **pad)
        self.entry_payable.insert(0, "0.00")
        self.entry_payable.configure(state="readonly")

        ctk.CTkLabel(frm, text="累计已付 (元)", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.entry_paid = ctk.CTkEntry(frm, width=300)
        self.entry_paid.grid(row=3, column=1, **pad)
        self.entry_paid.insert(0, "0.00")
        self.entry_paid.configure(state="readonly")

        ctk.CTkLabel(frm, text="剩余未付 (元)", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self.entry_remaining = ctk.CTkEntry(frm, width=300)
        self.entry_remaining.grid(row=4, column=1, **pad)
        self.entry_remaining.insert(0, "0.00")
        self.entry_remaining.configure(state="readonly")

        ctk.CTkLabel(frm, text="本次付款金额 (元) *", anchor="w", text_color="#e74c3c").grid(row=5, column=0, sticky="w", **pad)
        self.entry_amount = ctk.CTkEntry(frm, width=300)
        self.entry_amount.grid(row=5, column=1, **pad)
        self.entry_amount.insert(0, "0.00")

        ctk.CTkLabel(frm, text="付款日期 *", anchor="w").grid(row=6, column=0, sticky="w", **pad)
        self.date_payment = DateEntry(
            frm,
            width=26,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
            font=("Arial", 11),
        )
        self.date_payment.grid(row=6, column=1, sticky="w", **pad)

        ctk.CTkLabel(frm, text="付款方式", anchor="w").grid(row=7, column=0, sticky="w", **pad)
        self.combo_method = ctk.CTkComboBox(
            frm,
            values=["现金", "银行转账", "支票", "承兑汇票", "支付宝", "微信支付", "其他"],
            width=300
        )
        self.combo_method.grid(row=7, column=1, **pad)
        self.combo_method.set("银行转账")

        ctk.CTkLabel(frm, text="付款账户", anchor="w").grid(row=8, column=0, sticky="w", **pad)
        self.entry_account = ctk.CTkEntry(frm, width=300, placeholder_text="如：工商银行6222****")
        self.entry_account.grid(row=8, column=1, **pad)

        ctk.CTkLabel(frm, text="经手人", anchor="w").grid(row=9, column=0, sticky="w", **pad)
        self.entry_handler = ctk.CTkEntry(frm, width=300)
        self.entry_handler.grid(row=9, column=1, **pad)

        ctk.CTkLabel(frm, text="凭证号", anchor="w").grid(row=10, column=0, sticky="w", **pad)
        self.entry_voucher = ctk.CTkEntry(frm, width=300, placeholder_text="发票号/收据号等")
        self.entry_voucher.grid(row=10, column=1, **pad)

        ctk.CTkLabel(frm, text="备注", anchor="nw").grid(row=11, column=0, sticky="nw", **pad)
        self.text_remark = ctk.CTkTextbox(frm, width=300, height=60)
        self.text_remark.grid(row=11, column=1, **pad)

        self.lbl_hint = ctk.CTkLabel(frm, text="", text_color="gray", font=("Arial", 10))
        self.lbl_hint.grid(row=12, column=0, columnspan=2, pady=(0, 5))

        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=13, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frm, text="保存", width=100, command=self._on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frm, text="取消", width=100, fg_color="gray", command=self.destroy).pack(side="left", padx=10)

    def _load_data(self):
        row = db.get_payment_record_by_id(self.record_id)
        if not row:
            return

        supplier_label = None
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

        self._load_purchases()

        purchase_label = None
        for label, pid in self._purchase_map.items():
            if pid == row["purchase_id"]:
                purchase_label = label
                break
        if not purchase_label:
            p = db.get_purchase_payment_by_purchase_id(row["purchase_id"])
            if p:
                paid = p["paid_amount"] or 0
                total = p["total_amount"] or 0
                remaining = round(total - paid, 2)
                purchase_label = f"[{p['purchase_date']}] {p['material_code']} - {p['material_name']} x{p['purchase_quantity']} = ¥{total:.2f} (剩余: ¥{remaining:.2f})"
                self._purchase_map[purchase_label] = row["purchase_id"]
                current = list(self.combo_purchase.cget("values"))
                current.append(purchase_label)
                self.combo_purchase.configure(values=current)
        if purchase_label:
            self.combo_purchase.set(purchase_label)
            self._auto_fill_purchase()

        self.entry_payable.configure(state="normal")
        self.entry_paid.configure(state="normal")
        self.entry_remaining.configure(state="normal")

        pp = db.get_purchase_payment_by_purchase_id(row["purchase_id"])
        if pp:
            self.entry_payable.delete(0, "end")
            self.entry_payable.insert(0, f"{pp['payable_amount']:.2f}")
            self.entry_paid.delete(0, "end")
            self.entry_paid.insert(0, f"{pp['paid_amount']:.2f}")
            remaining = round(pp['payable_amount'] - pp['paid_amount'], 2)
            self.entry_remaining.delete(0, "end")
            self.entry_remaining.insert(0, f"{remaining:.2f}")

        self.entry_amount.delete(0, "end")
        self.entry_amount.insert(0, f"{row['payment_amount']:.2f}")

        if row["payment_date"]:
            try:
                dt = datetime.strptime(row["payment_date"], "%Y-%m-%d")
                self.date_payment.set_date(dt)
            except Exception:
                pass

        if row["payment_method"]:
            self.combo_method.set(row["payment_method"])

        self.entry_account.insert(0, row["payment_account"] or "")
        self.entry_handler.insert(0, row["handler"] or "")
        self.entry_voucher.insert(0, row["voucher_no"] or "")

        if row["remark"]:
            self.text_remark.insert("1.0", row["remark"])

        self.combo_supplier.configure(state="disabled")
        self.combo_purchase.configure(state="disabled")
        self.entry_payable.configure(state="readonly")
        self.entry_paid.configure(state="readonly")
        self.entry_remaining.configure(state="readonly")

    def _on_save(self):
        supplier_label = self.combo_supplier.get().strip()
        if supplier_label not in self._supplier_map:
            messagebox.showerror("错误", "请选择供应商", parent=self)
            return
        supplier_id = self._supplier_map[supplier_label]

        purchase_label = self.combo_purchase.get().strip()
        purchase_id = self._purchase_map.get(purchase_label)
        if not purchase_id:
            messagebox.showerror("错误", "请选择采购记录", parent=self)
            return

        try:
            payment_amount = float(self.entry_amount.get().strip() or "0")
        except ValueError:
            messagebox.showerror("错误", "付款金额必须是数字", parent=self)
            return
        if payment_amount <= 0:
            messagebox.showerror("错误", "付款金额必须大于0", parent=self)
            return

        try:
            remaining = float(self.entry_remaining.get().strip() or "0")
        except ValueError:
            remaining = 0

        if self.record_id:
            pp = db.get_purchase_payment_by_purchase_id(purchase_id)
            if pp:
                other_paid = (pp["paid_amount"] or 0) - payment_amount
                old_rec = db.get_payment_record_by_id(self.record_id)
                if old_rec:
                    other_paid = (pp["paid_amount"] or 0) - old_rec["payment_amount"]
                if other_paid + payment_amount > (pp["payable_amount"] or 0) + 0.01:
                    messagebox.showerror("错误", f"累计付款不能超过应付金额", parent=self)
                    return
        else:
            if payment_amount > remaining + 0.01:
                messagebox.showerror("错误", f"付款金额({payment_amount:.2f})不能超过剩余未付金额({remaining:.2f})", parent=self)
                return

        pp = db.get_purchase_payment_by_purchase_id(purchase_id)
        if not pp:
            sp = db.get_stock_purchases(keyword="")
            purchase_data = None
            for p in sp:
                if p["id"] == purchase_id:
                    purchase_data = p
                    break
            if purchase_data:
                data = {
                    "purchase_id": purchase_id,
                    "supplier_id": supplier_id,
                    "payable_amount": purchase_data["total_amount"],
                    "paid_amount": 0,
                    "payment_date": None,
                    "payment_status": "未付款",
                    "remark": "",
                }
                ok, msg = db.add_purchase_payment(data)
                if not ok:
                    messagebox.showerror("错误", msg, parent=self)
                    return

        payment_date = self.date_payment.get_date().strftime("%Y-%m-%d")
        remark = self.text_remark.get("1.0", "end").strip()

        data = {
            "purchase_id": purchase_id,
            "supplier_id": supplier_id,
            "payment_amount": payment_amount,
            "payment_date": payment_date,
            "payment_method": self.combo_method.get().strip(),
            "payment_account": self.entry_account.get().strip(),
            "handler": self.entry_handler.get().strip(),
            "voucher_no": self.entry_voucher.get().strip(),
            "remark": remark,
        }

        if self.record_id:
            ok, msg = db.update_payment_record(self.record_id, data)
        else:
            ok, msg = db.add_payment_record(data)

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
        self.title("付款详情 - 分期付款管理")
        self.geometry("900x700")
        self.resizable(True, True)
        self.grab_set()

        self._supplier_map = {}
        self._purchase_map = {}
        self._current_purchase_id = None
        self._build_ui()
        if payment_id:
            self._load_data()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        info_frm = ctk.CTkFrame(self, corner_radius=8)
        info_frm.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(info_frm, text="📋 采购单基本信息", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2c3e50").grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(info_frm, text="供应商:", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.lbl_supplier = ctk.CTkLabel(info_frm, text="-", font=ctk.CTkFont(weight="bold"))
        self.lbl_supplier.grid(row=1, column=1, sticky="w", **pad)

        ctk.CTkLabel(info_frm, text="材料:", anchor="w").grid(row=1, column=2, sticky="w", **pad)
        self.lbl_material = ctk.CTkLabel(info_frm, text="-", font=ctk.CTkFont(weight="bold"))
        self.lbl_material.grid(row=1, column=3, sticky="w", **pad)

        ctk.CTkLabel(info_frm, text="采购日期:", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.lbl_purchase_date = ctk.CTkLabel(info_frm, text="-")
        self.lbl_purchase_date.grid(row=2, column=1, sticky="w", **pad)

        ctk.CTkLabel(info_frm, text="到期日期:", anchor="w").grid(row=2, column=2, sticky="w", **pad)
        self.lbl_due_date = ctk.CTkLabel(info_frm, text="-")
        self.lbl_due_date.grid(row=2, column=3, sticky="w", **pad)

        ctk.CTkLabel(info_frm, text="采购数量:", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self.lbl_quantity = ctk.CTkLabel(info_frm, text="-")
        self.lbl_quantity.grid(row=3, column=1, sticky="w", **pad)

        ctk.CTkLabel(info_frm, text="单价:", anchor="w").grid(row=3, column=2, sticky="w", **pad)
        self.lbl_unit_price = ctk.CTkLabel(info_frm, text="-")
        self.lbl_unit_price.grid(row=3, column=3, sticky="w", **pad)

        summary_frm = ctk.CTkFrame(self, corner_radius=8)
        summary_frm.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(summary_frm, text="💰 付款状态汇总", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2c3e50").grid(row=0, column=0, columnspan=6, sticky="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(summary_frm, text="应付总额:", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.lbl_total_payable = ctk.CTkLabel(summary_frm, text="¥0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e74c3c")
        self.lbl_total_payable.grid(row=1, column=1, sticky="w", **pad)

        ctk.CTkLabel(summary_frm, text="累计已付:", anchor="w").grid(row=1, column=2, sticky="w", **pad)
        self.lbl_total_paid = ctk.CTkLabel(summary_frm, text="¥0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color="#27ae60")
        self.lbl_total_paid.grid(row=1, column=3, sticky="w", **pad)

        ctk.CTkLabel(summary_frm, text="剩余未付:", anchor="w").grid(row=1, column=4, sticky="w", **pad)
        self.lbl_remaining = ctk.CTkLabel(summary_frm, text="¥0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e67e22")
        self.lbl_remaining.grid(row=1, column=5, sticky="w", **pad)

        ctk.CTkLabel(summary_frm, text="付款状态:", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self.lbl_status = ctk.CTkLabel(summary_frm, text="-", font=ctk.CTkFont(weight="bold"))
        self.lbl_status.grid(row=2, column=1, sticky="w", **pad)

        ctk.CTkLabel(summary_frm, text="分期付款次数:", anchor="w").grid(row=2, column=2, sticky="w", **pad)
        self.lbl_installment_count = ctk.CTkLabel(summary_frm, text="0次", font=ctk.CTkFont(weight="bold"))
        self.lbl_installment_count.grid(row=2, column=3, sticky="w", **pad)

        ctk.CTkLabel(summary_frm, text="付款进度:", anchor="w").grid(row=2, column=4, sticky="w", **pad)
        self.progress_bar = ctk.CTkProgressBar(summary_frm, width=150, height=20)
        self.progress_bar.grid(row=2, column=5, sticky="w", **pad)
        self.progress_bar.set(0)
        self.lbl_progress = ctk.CTkLabel(summary_frm, text="0%")
        self.lbl_progress.grid(row=2, column=5, sticky="e", **pad)

        btn_frm = ctk.CTkFrame(self, fg_color="transparent")
        btn_frm.pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(btn_frm, text="➕ 新增付款", width=120, fg_color="#27ae60", command=self._add_payment_record).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="✏️ 编辑选中", width=120, command=self._edit_payment_record).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="🗑️ 删除选中", width=120, fg_color="#e74c3c", command=self._delete_payment_record).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="🔄 刷新", width=100, command=self._refresh_records).pack(side="left", padx=5)
        ctk.CTkButton(btn_frm, text="关闭", width=100, fg_color="gray", command=self.destroy).pack(side="right", padx=5)

        records_frm = ctk.CTkFrame(self, corner_radius=8)
        records_frm.pack(fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(records_frm, text="📝 付款流水明细", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2c3e50").pack(anchor="w", padx=15, pady=(10, 5))

        tree_frm = ctk.CTkFrame(records_frm, fg_color="transparent")
        tree_frm.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("id", "date", "amount", "method", "account", "handler", "voucher", "remark", "created")
        self.tree_records = ttk.Treeview(tree_frm, columns=cols, show="headings", height=15)
        self.tree_records.heading("id", text="序号")
        self.tree_records.heading("date", text="付款日期")
        self.tree_records.heading("amount", text="付款金额")
        self.tree_records.heading("method", text="付款方式")
        self.tree_records.heading("account", text="付款账户")
        self.tree_records.heading("handler", text="经手人")
        self.tree_records.heading("voucher", text="凭证号")
        self.tree_records.heading("remark", text="备注")
        self.tree_records.heading("created", text="登记时间")

        self.tree_records.column("id", width=50, anchor="center")
        self.tree_records.column("date", width=100, anchor="center")
        self.tree_records.column("amount", width=100, anchor="e")
        self.tree_records.column("method", width=90, anchor="center")
        self.tree_records.column("account", width=150, anchor="w")
        self.tree_records.column("handler", width=80, anchor="center")
        self.tree_records.column("voucher", width=120, anchor="w")
        self.tree_records.column("remark", width=150, anchor="w")
        self.tree_records.column("created", width=140, anchor="center")

        self.tree_records.tag_configure("paid", background="#d4edda")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_records.yview)
        self.tree_records.configure(yscrollcommand=vsb.set)
        self.tree_records.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree_records.bind("<Double-1>", lambda e: self._edit_payment_record())

    def _load_data(self):
        row = db.get_purchase_payment_by_id(self.payment_id)
        if not row:
            return

        self._current_purchase_id = row["purchase_id"]

        detail = db.get_purchase_payment_by_purchase_id(self._current_purchase_id)
        if detail:
            self.lbl_supplier.configure(text=f"{detail['supplier_code']} - {detail['supplier_name']}")
            self.lbl_material.configure(text=f"{detail['material_code']} - {detail['material_name']}")
            self.lbl_purchase_date.configure(text=detail["purchase_date"] or "-")
            self.lbl_quantity.configure(text=f"{detail['purchase_quantity'] or 0}")
            self.lbl_unit_price.configure(text=f"¥{detail['unit_price'] or 0:.2f}")

            try:
                pd = datetime.strptime(detail["purchase_date"], "%Y-%m-%d")
                days = detail["payment_days"] or 30
                due_date = (pd + timedelta(days=days)).strftime("%Y-%m-%d")
                self.lbl_due_date.configure(text=due_date)
            except Exception:
                self.lbl_due_date.configure(text="-")

        self._refresh_summary()
        self._refresh_records()

    def _refresh_summary(self):
        if not self._current_purchase_id:
            return

        detail = db.get_purchase_payment_by_purchase_id(self._current_purchase_id)
        if detail:
            payable = detail["payable_amount"] or 0
            paid = detail["paid_amount"] or 0
            remaining = round(payable - paid, 2)
            progress = (paid / payable * 100) if payable > 0 else 0

            self.lbl_total_payable.configure(text=f"¥{payable:.2f}")
            self.lbl_total_paid.configure(text=f"¥{paid:.2f}")
            self.lbl_remaining.configure(text=f"¥{remaining:.2f}")

            status = detail["payment_status"] or "未付款"
            status_colors = {
                "已付款": "#27ae60",
                "部分付款": "#e67e22",
                "未付款": "#7f8c8d",
                "逾期": "#e74c3c",
            }
            self.lbl_status.configure(text=status, text_color=status_colors.get(status, "#333"))
            self.progress_bar.set(progress / 100)
            self.lbl_progress.configure(text=f"{progress:.1f}%")

        records = db.get_payment_records_by_purchase(self._current_purchase_id)
        self.lbl_installment_count.configure(text=f"{len(records)}次")

    def _refresh_records(self):
        for item in self.tree_records.get_children():
            self.tree_records.delete(item)

        if not self._current_purchase_id:
            return

        records = db.get_payment_records_by_purchase(self._current_purchase_id)
        for idx, r in enumerate(records, 1):
            self.tree_records.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    idx,
                    r["payment_date"] or "",
                    f"¥{r['payment_amount']:.2f}",
                    r["payment_method"] or "",
                    r["payment_account"] or "",
                    r["handler"] or "",
                    r["voucher_no"] or "",
                    (r["remark"] or "")[:20],
                    r["created_at"] or "",
                ),
                tags=("paid",),
            )

    def _get_selected_record_id(self) -> Optional[int]:
        sel = self.tree_records.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条付款流水记录", parent=self)
            return None
        return int(sel[0])

    def _add_payment_record(self):
        if not self._current_purchase_id:
            return
        detail = db.get_purchase_payment_by_purchase_id(self._current_purchase_id)
        if not detail:
            return
        PaymentRecordDialog(
            self,
            purchase_id=self._current_purchase_id,
            supplier_id=detail["supplier_id"],
            on_save=self._on_record_changed,
        )

    def _edit_payment_record(self):
        record_id = self._get_selected_record_id()
        if record_id:
            PaymentRecordDialog(
                self,
                record_id=record_id,
                on_save=self._on_record_changed,
            )

    def _delete_payment_record(self):
        record_id = self._get_selected_record_id()
        if record_id and messagebox.askyesno("确认", "确定要删除该付款流水记录吗?", parent=self):
            ok, msg = db.delete_payment_record(record_id)
            if ok:
                messagebox.showinfo("成功", msg, parent=self)
                self._on_record_changed()
            else:
                messagebox.showerror("错误", msg, parent=self)

    def _on_record_changed(self):
        self._refresh_summary()
        self._refresh_records()
        if self.on_save:
            self.on_save()

    def _load_suppliers(self):
        pass

    def _load_purchases(self):
        pass

    def _auto_fill(self):
        pass

    def _auto_status(self):
        pass

    def _on_save(self):
        pass


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

        self.btn_tab_installment = ctk.CTkButton(tab_bar, text="� 分期付款进度", width=140, height=36,
                                                  fg_color="#95a5a6", command=lambda: self._switch_tab("installment"))
        self.btn_tab_installment.pack(side="left", padx=3)

        self.btn_tab_flow = ctk.CTkButton(tab_bar, text="📋 付款流水明细", width=140, height=36,
                                           fg_color="#95a5a6", command=lambda: self._switch_tab("flow"))
        self.btn_tab_flow.pack(side="left", padx=3)

        self.btn_tab_trend = ctk.CTkButton(tab_bar, text="📊 付款支出趋势", width=140, height=36,
                                            fg_color="#95a5a6", command=lambda: self._switch_tab("trend"))
        self.btn_tab_trend.pack(side="left", padx=3)

        self.btn_tab_due = ctk.CTkButton(tab_bar, text="⏰ 应付款提醒", width=140, height=36,
                                          fg_color="#95a5a6", command=lambda: self._switch_tab("due"))
        self.btn_tab_due.pack(side="left", padx=3)

        self.btn_tab_restock = ctk.CTkButton(tab_bar, text="📦 采购补货", width=130, height=36,
                                              fg_color="#95a5a6", command=lambda: self._switch_tab("restock"))
        self.btn_tab_restock.pack(side="left", padx=3)

        self.supplier_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_supplier_ui()

        self.payment_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_payment_ui()

        self.installment_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_installment_ui()

        self.flow_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_flow_ui()

        self.trend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_trend_ui()

        self.due_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._build_due_ui()

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

    def _build_installment_ui(self):
        self.installment_frame.grid_columnconfigure(0, weight=2)
        self.installment_frame.grid_columnconfigure(1, weight=1)
        self.installment_frame.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self.installment_frame, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=5)

        ctk.CTkLabel(top, text="供应商:").pack(side="left")
        self.combo_inst_supplier = ctk.CTkComboBox(top, values=["全部"], width=200)
        self.combo_inst_supplier.pack(side="left", padx=5)
        self.combo_inst_supplier.set("全部")

        ctk.CTkLabel(top, text="付款状态:").pack(side="left", padx=(15, 0))
        self.combo_inst_status = ctk.CTkComboBox(top, values=["全部", "未付款", "部分付款", "已付款", "逾期"], width=100)
        self.combo_inst_status.pack(side="left", padx=5)
        self.combo_inst_status.set("全部")

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh_installment).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset_installment).pack(side="left", padx=5)
        ctk.CTkButton(top, text="新增付款", width=100, fg_color="#27ae60", command=self._add_installment_payment).pack(side="right", padx=5)
        ctk.CTkButton(top, text="查看详情", width=100, command=self._view_installment_detail).pack(side="right", padx=5)

        stat_frm = ctk.CTkFrame(self.installment_frame, fg_color="transparent")
        stat_frm.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5))

        self.lbl_inst_total = ctk.CTkLabel(stat_frm, text="采购单总数: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2980b9")
        self.lbl_inst_total.pack(side="left", padx=10)
        self.lbl_inst_payable = ctk.CTkLabel(stat_frm, text="应付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e74c3c")
        self.lbl_inst_payable.pack(side="left", padx=10)
        self.lbl_inst_paid = ctk.CTkLabel(stat_frm, text="已付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#27ae60")
        self.lbl_inst_paid.pack(side="left", padx=10)
        self.lbl_inst_unpaid = ctk.CTkLabel(stat_frm, text="未付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22")
        self.lbl_inst_unpaid.pack(side="left", padx=10)
        self.lbl_inst_completion = ctk.CTkLabel(stat_frm, text="完成率: 0%", font=ctk.CTkFont(size=12, weight="bold"), text_color="#8e44ad")
        self.lbl_inst_completion.pack(side="left", padx=10)

        chart_frm = ctk.CTkFrame(self.installment_frame, corner_radius=8)
        chart_frm.grid(row=2, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        chart_frm.grid_columnconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(2, weight=1)

        chart1_header = ctk.CTkFrame(chart_frm, fg_color="transparent")
        chart1_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        ctk.CTkLabel(chart1_header, text="📊 付款状态分布", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2c3e50").pack(side="left")
        self.fig_inst_status = Figure(figsize=(3.5, 2.2), dpi=100)
        self.canvas_inst_status = FigureCanvasTkAgg(self.fig_inst_status, master=chart_frm)
        self.canvas_inst_status.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        chart2_header = ctk.CTkFrame(chart_frm, fg_color="transparent")
        chart2_header.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 0))
        ctk.CTkLabel(chart2_header, text="🏆 供应商分期付款Top5", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2c3e50").pack(side="left")
        self.fig_inst_supplier = Figure(figsize=(3.5, 2.2), dpi=100)
        self.canvas_inst_supplier = FigureCanvasTkAgg(self.fig_inst_supplier, master=chart_frm)
        self.canvas_inst_supplier.get_tk_widget().grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

        tree_frm = ctk.CTkFrame(self.installment_frame)
        tree_frm.grid(row=2, column=0, sticky="nsew", padx=(15, 5), pady=(5, 15))

        cols = ("supplier", "material", "purchase_date", "due_date", "payable", "paid", "unpaid",
                "progress", "count", "last_pay", "status", "days_due")
        self.tree_installment = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree_installment.heading("supplier", text="供应商")
        self.tree_installment.heading("material", text="材料")
        self.tree_installment.heading("purchase_date", text="采购日期")
        self.tree_installment.heading("due_date", text="到期日期")
        self.tree_installment.heading("payable", text="应付金额")
        self.tree_installment.heading("paid", text="已付金额")
        self.tree_installment.heading("unpaid", text="未付金额")
        self.tree_installment.heading("progress", text="付款进度")
        self.tree_installment.heading("count", text="付款次数")
        self.tree_installment.heading("last_pay", text="最近付款")
        self.tree_installment.heading("status", text="状态")
        self.tree_installment.heading("days_due", text="距到期")

        self.tree_installment.column("supplier", width=120, anchor="w")
        self.tree_installment.column("material", width=130, anchor="w")
        self.tree_installment.column("purchase_date", width=85, anchor="center")
        self.tree_installment.column("due_date", width=85, anchor="center")
        self.tree_installment.column("payable", width=75, anchor="e")
        self.tree_installment.column("paid", width=75, anchor="e")
        self.tree_installment.column("unpaid", width=75, anchor="e")
        self.tree_installment.column("progress", width=75, anchor="center")
        self.tree_installment.column("count", width=65, anchor="center")
        self.tree_installment.column("last_pay", width=85, anchor="center")
        self.tree_installment.column("status", width=65, anchor="center")
        self.tree_installment.column("days_due", width=65, anchor="center")

        self.tree_installment.tag_configure("overdue", background="#f8d7da")
        self.tree_installment.tag_configure("partial", background="#fff3cd")
        self.tree_installment.tag_configure("paid", background="#d4edda")
        self.tree_installment.tag_configure("soon", background="#d6eaf8")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_installment.yview)
        self.tree_installment.configure(yscrollcommand=vsb.set)
        self.tree_installment.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree_installment.bind("<Double-1>", lambda e: self._view_installment_detail())

    def _build_flow_ui(self):
        top = ctk.CTkFrame(self.flow_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(top, text="开始日期:").pack(side="left")
        self.date_flow_start = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_flow_start.pack(side="left", padx=5)
        self.date_flow_start.set_date(date.today() - timedelta(days=90))

        ctk.CTkLabel(top, text="结束日期:").pack(side="left", padx=(10, 0))
        self.date_flow_end = DateEntry(
            top, width=12, background="darkblue", foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd", font=("Arial", 10),
        )
        self.date_flow_end.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="供应商:").pack(side="left", padx=(15, 0))
        self.combo_flow_supplier = ctk.CTkComboBox(top, values=["全部"], width=180)
        self.combo_flow_supplier.pack(side="left", padx=5)
        self.combo_flow_supplier.set("全部")

        ctk.CTkLabel(top, text="付款方式:").pack(side="left", padx=(15, 0))
        self.combo_flow_method = ctk.CTkComboBox(
            top,
            values=["全部", "现金", "银行转账", "支票", "承兑汇票", "支付宝", "微信支付", "其他"],
            width=100
        )
        self.combo_flow_method.pack(side="left", padx=5)
        self.combo_flow_method.set("全部")

        ctk.CTkLabel(top, text="关键词:").pack(side="left", padx=(10, 0))
        self.entry_flow_search = ctk.CTkEntry(top, width=160, placeholder_text="材料/凭证/经手人")
        self.entry_flow_search.pack(side="left", padx=5)

        ctk.CTkButton(top, text="搜索", width=80, command=self.refresh_flow).pack(side="left", padx=5)
        ctk.CTkButton(top, text="重置", width=80, fg_color="gray", command=self._reset_flow).pack(side="left", padx=5)
        ctk.CTkButton(top, text="新增付款", width=100, fg_color="#27ae60", command=self._add_flow_payment).pack(side="right", padx=5)
        ctk.CTkButton(top, text="导出Excel", width=100, fg_color="#2980b9", command=self._export_flow).pack(side="right", padx=5)

        stat_frm = ctk.CTkFrame(self.flow_frame, fg_color="transparent")
        stat_frm.pack(fill="x", padx=15, pady=(0, 5))

        self.lbl_flow_count = ctk.CTkLabel(stat_frm, text="付款笔数: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#8e44ad")
        self.lbl_flow_count.pack(side="left", padx=10)
        self.lbl_flow_total = ctk.CTkLabel(stat_frm, text="付款总金额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#27ae60")
        self.lbl_flow_total.pack(side="left", padx=10)
        self.lbl_flow_unpaid = ctk.CTkLabel(stat_frm, text="待付总额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22")
        self.lbl_flow_unpaid.pack(side="left", padx=10)

        tree_frm = ctk.CTkFrame(self.flow_frame)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("pay_date", "supplier", "material", "amount", "cumulative", "payable", "method", "account", "handler", "voucher", "purchase_date", "remark")
        self.tree_flow = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20)
        self.tree_flow.heading("pay_date", text="付款日期")
        self.tree_flow.heading("supplier", text="供应商")
        self.tree_flow.heading("material", text="对应材料")
        self.tree_flow.heading("amount", text="本次付款")
        self.tree_flow.heading("cumulative", text="累计已付")
        self.tree_flow.heading("payable", text="应付金额")
        self.tree_flow.heading("method", text="付款方式")
        self.tree_flow.heading("account", text="付款账户")
        self.tree_flow.heading("handler", text="经手人")
        self.tree_flow.heading("voucher", text="凭证号")
        self.tree_flow.heading("purchase_date", text="采购日期")
        self.tree_flow.heading("remark", text="备注")

        self.tree_flow.column("pay_date", width=95, anchor="center")
        self.tree_flow.column("supplier", width=130, anchor="w")
        self.tree_flow.column("material", width=120, anchor="w")
        self.tree_flow.column("amount", width=85, anchor="e")
        self.tree_flow.column("cumulative", width=85, anchor="e")
        self.tree_flow.column("payable", width=85, anchor="e")
        self.tree_flow.column("method", width=80, anchor="center")
        self.tree_flow.column("account", width=130, anchor="w")
        self.tree_flow.column("handler", width=70, anchor="center")
        self.tree_flow.column("voucher", width=100, anchor="w")
        self.tree_flow.column("purchase_date", width=90, anchor="center")
        self.tree_flow.column("remark", width=130, anchor="w")

        self.tree_flow.tag_configure("paid_full", background="#d4edda")
        self.tree_flow.tag_configure("paid_partial", background="#fff3cd")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_flow.yview)
        self.tree_flow.configure(yscrollcommand=vsb.set)
        self.tree_flow.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree_flow.bind("<Double-1>", lambda e: self._edit_flow_payment())

    def _build_trend_ui(self):
        top = ctk.CTkFrame(self.trend_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top, text="趋势月数:").pack(side="left")
        self.combo_trend_months = ctk.CTkComboBox(top, values=["3", "6", "12", "24"], width=60)
        self.combo_trend_months.set("12")
        self.combo_trend_months.pack(side="left", padx=5)

        ctk.CTkButton(top, text="刷新图表", width=100, command=self.refresh_trend).pack(side="left", padx=10)
        ctk.CTkButton(top, text="更新逾期状态", width=120, fg_color="#e74c3c", command=self._batch_update_overdue).pack(side="right", padx=5)
        ctk.CTkButton(top, text="导出趋势数据", width=120, fg_color="#27ae60", command=self._export_trend_data).pack(side="right", padx=5)

        self.trend_frame.grid_columnconfigure(0, weight=1)
        self.trend_frame.grid_columnconfigure(1, weight=1)
        self.trend_frame.grid_rowconfigure(1, weight=1)
        self.trend_frame.grid_rowconfigure(2, weight=1)
        self.trend_frame.grid_rowconfigure(3, weight=1)

        chart_frm = ctk.CTkFrame(self.trend_frame, corner_radius=8)
        chart_frm.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=15, pady=(5, 5))
        chart_frm.grid_columnconfigure(0, weight=1)
        chart_frm.grid_rowconfigure(0, weight=1)
        self.fig_pay_trend = Figure(figsize=(8, 2.6), dpi=100)
        self.canvas_pay_trend = FigureCanvasTkAgg(self.fig_pay_trend, master=chart_frm)
        self.canvas_pay_trend.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        compare_frm = ctk.CTkFrame(self.trend_frame, corner_radius=8)
        compare_frm.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=15, pady=(5, 5))
        compare_frm.grid_columnconfigure(0, weight=1)
        compare_frm.grid_rowconfigure(0, weight=1)
        self.fig_compare = Figure(figsize=(8, 2.4), dpi=100)
        self.canvas_compare = FigureCanvasTkAgg(self.fig_compare, master=compare_frm)
        self.canvas_compare.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        method_box = ctk.CTkFrame(self.trend_frame, corner_radius=8)
        method_box.grid(row=3, column=0, sticky="nsew", padx=(15, 5), pady=(5, 15))
        method_box.grid_columnconfigure(0, weight=1)
        method_box.grid_rowconfigure(1, weight=1)

        method_header = ctk.CTkFrame(method_box, fg_color="transparent")
        method_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(method_header, text="💳 付款方式分布", font=ctk.CTkFont(size=13, weight="bold"), text_color="#2980b9").pack(side="left")
        self.lbl_method_info = ctk.CTkLabel(method_header, text="", font=ctk.CTkFont(size=11))
        self.lbl_method_info.pack(side="right")

        method_cols = ("rank", "method", "count", "amount", "ratio")
        self.tree_method = ttk.Treeview(method_box, columns=method_cols, show="headings", height=8)
        self.tree_method.heading("rank", text="#")
        self.tree_method.heading("method", text="付款方式")
        self.tree_method.heading("count", text="笔数")
        self.tree_method.heading("amount", text="金额")
        self.tree_method.heading("ratio", text="占比")

        self.tree_method.column("rank", width=30, anchor="center")
        self.tree_method.column("method", width=100, anchor="w")
        self.tree_method.column("count", width=60, anchor="center")
        self.tree_method.column("amount", width=90, anchor="e")
        self.tree_method.column("ratio", width=60, anchor="center")

        vsb_method = ttk.Scrollbar(method_box, orient="vertical", command=self.tree_method.yview)
        self.tree_method.configure(yscrollcommand=vsb_method.set)
        self.tree_method.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_method.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

        supplier_box = ctk.CTkFrame(self.trend_frame, corner_radius=8)
        supplier_box.grid(row=3, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        supplier_box.grid_columnconfigure(0, weight=1)
        supplier_box.grid_rowconfigure(1, weight=1)

        supplier_header = ctk.CTkFrame(supplier_box, fg_color="transparent")
        supplier_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(supplier_header, text="🏢 供应商付款排行", font=ctk.CTkFont(size=13, weight="bold"), text_color="#8e44ad").pack(side="left")
        self.lbl_supplier_pay_info = ctk.CTkLabel(supplier_header, text="", font=ctk.CTkFont(size=11))
        self.lbl_supplier_pay_info.pack(side="right")

        sp_cols = ("rank", "code", "name", "count", "amount")
        self.tree_supplier_pay = ttk.Treeview(supplier_box, columns=sp_cols, show="headings", height=8)
        self.tree_supplier_pay.heading("rank", text="#")
        self.tree_supplier_pay.heading("code", text="编号")
        self.tree_supplier_pay.heading("name", text="供应商名称")
        self.tree_supplier_pay.heading("count", text="付款笔数")
        self.tree_supplier_pay.heading("amount", text="付款金额")

        self.tree_supplier_pay.column("rank", width=30, anchor="center")
        self.tree_supplier_pay.column("code", width=70, anchor="center")
        self.tree_supplier_pay.column("name", width=120, anchor="w")
        self.tree_supplier_pay.column("count", width=60, anchor="center")
        self.tree_supplier_pay.column("amount", width=90, anchor="e")

        self.tree_supplier_pay.tag_configure("top3", background="#fdebd0")

        vsb_sp = ttk.Scrollbar(supplier_box, orient="vertical", command=self.tree_supplier_pay.yview)
        self.tree_supplier_pay.configure(yscrollcommand=vsb_sp.set)
        self.tree_supplier_pay.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        vsb_sp.grid(row=1, column=1, sticky="ns", pady=5, padx=(0, 10))

    def _build_due_ui(self):
        top = ctk.CTkFrame(self.due_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(top, text="提前提醒天数:").pack(side="left")
        self.combo_due_days = ctk.CTkComboBox(top, values=["7", "15", "30", "60", "90"], width=60)
        self.combo_due_days.set("30")
        self.combo_due_days.pack(side="left", padx=5)

        ctk.CTkLabel(top, text="显示类型:").pack(side="left", padx=(15, 0))
        self.combo_due_type = ctk.CTkComboBox(top, values=["全部", "仅逾期", "仅即将到期"], width=110)
        self.combo_due_type.pack(side="left", padx=5)
        self.combo_due_type.set("全部")

        ctk.CTkButton(top, text="刷新", width=80, command=self.refresh_due).pack(side="left", padx=10)
        ctk.CTkButton(top, text="全选", width=60, command=self._select_all_due).pack(side="right", padx=3)
        ctk.CTkButton(top, text="取消全选", width=80, command=self._deselect_all_due).pack(side="right", padx=3)
        ctk.CTkButton(top, text="批量导出", width=80, fg_color="#2980b9", command=self._export_due_list).pack(side="right", padx=3)
        ctk.CTkButton(top, text="批量标记已处理", width=100, fg_color="#8e44ad", command=self._batch_mark_processed).pack(side="right", padx=3)
        ctk.CTkButton(top, text="快捷付款", width=100, fg_color="#27ae60", command=self._pay_from_due).pack(side="right", padx=3)

        info_box = ctk.CTkFrame(self.due_frame, fg_color="transparent")
        info_box.pack(fill="x", padx=15, pady=(0, 5))

        self.lbl_due_overdue_cnt = ctk.CTkLabel(info_box, text="逾期笔数: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e74c3c")
        self.lbl_due_overdue_cnt.pack(side="left", padx=5)
        self.lbl_due_overdue_amt = ctk.CTkLabel(info_box, text="逾期金额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#c0392b")
        self.lbl_due_overdue_amt.pack(side="left", padx=15)
        self.lbl_due_soon_cnt = ctk.CTkLabel(info_box, text="即将到期: 0笔", font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22")
        self.lbl_due_soon_cnt.pack(side="left", padx=5)
        self.lbl_due_soon_amt = ctk.CTkLabel(info_box, text="到期金额: ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#d35400")
        self.lbl_due_soon_amt.pack(side="left", padx=15)
        self.lbl_due_selected = ctk.CTkLabel(info_box, text="已选: 0笔 / ¥0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2980b9")
        self.lbl_due_selected.pack(side="right", padx=10)

        tree_frm = ctk.CTkFrame(self.due_frame)
        tree_frm.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        cols = ("select", "alert", "supplier", "purchase_date", "due_date", "material", "payable", "paid", "unpaid",
                "contact", "phone", "status", "remark")
        self.tree_due = ttk.Treeview(tree_frm, columns=cols, show="headings", height=20, selectmode="extended")
        self.tree_due.heading("select", text="☑")
        self.tree_due.heading("alert", text="提醒")
        self.tree_due.heading("supplier", text="供应商")
        self.tree_due.heading("purchase_date", text="采购日期")
        self.tree_due.heading("due_date", text="到期日期")
        self.tree_due.heading("material", text="材料")
        self.tree_due.heading("payable", text="应付")
        self.tree_due.heading("paid", text="已付")
        self.tree_due.heading("unpaid", text="未付")
        self.tree_due.heading("contact", text="联系人")
        self.tree_due.heading("phone", text="联系电话")
        self.tree_due.heading("status", text="状态")
        self.tree_due.heading("remark", text="备注")

        self.tree_due.column("select", width=35, anchor="center")
        self.tree_due.column("alert", width=90, anchor="center")
        self.tree_due.column("supplier", width=120, anchor="w")
        self.tree_due.column("purchase_date", width=85, anchor="center")
        self.tree_due.column("due_date", width=85, anchor="center")
        self.tree_due.column("material", width=130, anchor="w")
        self.tree_due.column("payable", width=70, anchor="e")
        self.tree_due.column("paid", width=70, anchor="e")
        self.tree_due.column("unpaid", width=70, anchor="e")
        self.tree_due.column("contact", width=65, anchor="center")
        self.tree_due.column("phone", width=95, anchor="center")
        self.tree_due.column("status", width=65, anchor="center")
        self.tree_due.column("remark", width=120, anchor="w")

        self.tree_due.tag_configure("overdue30", background="#f8d7da")
        self.tree_due.tag_configure("overdue15", background="#fadbd8")
        self.tree_due.tag_configure("overdue7", background="#fdebd0")
        self.tree_due.tag_configure("soon7", background="#fff3cd")
        self.tree_due.tag_configure("soon15", background="#d6eaf8")
        self.tree_due.tag_configure("soon30", background="#eaf2f8")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree_due.yview)
        self.tree_due.configure(yscrollcommand=vsb.set)
        self.tree_due.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree_due.bind("<Double-1>", lambda e: self._pay_from_due())
        self.tree_due.bind("<<TreeviewSelect>>", lambda e: self._update_selected_count())
        self.tree_due.bind("<Button-1>", self._on_tree_due_click)

    def _switch_tab(self, tab_name: str):
        self.supplier_frame.pack_forget()
        self.payment_frame.pack_forget()
        self.installment_frame.pack_forget()
        self.flow_frame.pack_forget()
        self.trend_frame.pack_forget()
        self.due_frame.pack_forget()
        self.restock_frame.pack_forget()

        self.btn_tab_supplier.configure(fg_color="#95a5a6")
        self.btn_tab_payment.configure(fg_color="#95a5a6")
        self.btn_tab_installment.configure(fg_color="#95a5a6")
        self.btn_tab_flow.configure(fg_color="#95a5a6")
        self.btn_tab_trend.configure(fg_color="#95a5a6")
        self.btn_tab_due.configure(fg_color="#95a5a6")
        self.btn_tab_restock.configure(fg_color="#95a5a6")

        if tab_name == "supplier":
            self.supplier_frame.pack(fill="both", expand=True)
            self.btn_tab_supplier.configure(fg_color="#347ab8")
            self.refresh_suppliers()
        elif tab_name == "payment":
            self.payment_frame.pack(fill="both", expand=True)
            self.btn_tab_payment.configure(fg_color="#347ab8")
            self.refresh_payments()
        elif tab_name == "installment":
            self.installment_frame.pack(fill="both", expand=True)
            self.btn_tab_installment.configure(fg_color="#347ab8")
            self._load_installment_suppliers()
            self.refresh_installment()
        elif tab_name == "flow":
            self.flow_frame.pack(fill="both", expand=True)
            self.btn_tab_flow.configure(fg_color="#347ab8")
            self._load_flow_suppliers()
            self.refresh_flow()
        elif tab_name == "trend":
            self.trend_frame.pack(fill="both", expand=True)
            self.btn_tab_trend.configure(fg_color="#347ab8")
            self.refresh_trend()
        elif tab_name == "due":
            self.due_frame.pack(fill="both", expand=True)
            self.btn_tab_due.configure(fg_color="#347ab8")
            self.refresh_due()
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

    def _load_installment_suppliers(self):
        rows = db.get_suppliers()
        values = ["全部"]
        for r in rows:
            if r["supplier_status"] == "正常":
                values.append(f"{r['supplier_code']} - {r['supplier_name']}")
        current = self.combo_inst_supplier.get()
        self.combo_inst_supplier.configure(values=values)
        if current in values:
            self.combo_inst_supplier.set(current)
        else:
            self.combo_inst_supplier.set("全部")

    def _reset_installment(self):
        self.combo_inst_supplier.set("全部")
        self.combo_inst_status.set("全部")
        self.refresh_installment()

    def refresh_installment(self):
        for item in self.tree_installment.get_children():
            self.tree_installment.delete(item)

        supplier_label = self.combo_inst_supplier.get().strip()
        supplier_id = None
        if supplier_label and supplier_label != "全部":
            all_suppliers = db.get_suppliers()
            for s in all_suppliers:
                if f"{s['supplier_code']} - {s['supplier_name']}" == supplier_label:
                    supplier_id = s["id"]
                    break

        status = self.combo_inst_status.get()
        data = db.get_installment_progress(supplier_id=supplier_id, status=status)

        total_payable = 0.0
        total_paid = 0.0
        total_unpaid = 0.0
        paid_count = 0
        for d in data:
            total_payable += d["payable_amount"]
            total_paid += d["paid_amount"]
            total_unpaid += d["unpaid_amount"]
            if d["payment_status"] == "已付款":
                paid_count += 1

            tag = ""
            st = d["payment_status"]
            if st == "已付款":
                tag = "paid"
            elif st == "逾期":
                tag = "overdue"
            elif st == "部分付款":
                tag = "partial"
            elif 0 <= d["days_until_due"] <= 7:
                tag = "soon"

            sup_name = f"{d['supplier_code'] or ''} - {d['supplier_name'] or ''}"
            mat_name = f"{d['material_code'] or ''} - {d['material_name'] or ''}"
            days_due_text = f"逾期{d['days_until_due'] * -1}天" if d['days_until_due'] < 0 else (f"{d['days_until_due']}天" if d['days_until_due'] <= 30 else "-")

            self.tree_installment.insert(
                "",
                "end",
                iid=str(d["payment_id"]),
                values=(
                    sup_name,
                    mat_name,
                    d["purchase_date"] or "",
                    d["due_date"] or "",
                    f"¥{d['payable_amount']:.2f}",
                    f"¥{d['paid_amount']:.2f}",
                    f"¥{d['unpaid_amount']:.2f}",
                    f"{d['progress_rate']:.1f}%",
                    f"{d['installment_count']}次",
                    d["last_pay_date"] or "",
                    st,
                    days_due_text,
                ),
                tags=(tag,),
            )

        completion_rate = (paid_count / len(data) * 100) if len(data) > 0 else 0

        self.lbl_inst_total.configure(text=f"采购单总数: {len(data)}")
        self.lbl_inst_payable.configure(text=f"应付总额: ¥{total_payable:.2f}")
        self.lbl_inst_paid.configure(text=f"已付总额: ¥{total_paid:.2f}")
        self.lbl_inst_unpaid.configure(text=f"未付总额: ¥{total_unpaid:.2f}")
        self.lbl_inst_completion.configure(text=f"完成率: {completion_rate:.1f}%")

        self._draw_installment_charts(data)

    def _draw_installment_charts(self, data):
        status_counts = {"已付款": 0, "部分付款": 0, "未付款": 0, "逾期": 0}
        supplier_totals = {}

        for d in data:
            st = d["payment_status"]
            if st in status_counts:
                status_counts[st] += 1
            else:
                status_counts[st] = 1

            sup_key = d["supplier_name"] or "未知供应商"
            if sup_key not in supplier_totals:
                supplier_totals[sup_key] = 0.0
            supplier_totals[sup_key] += d["paid_amount"] or 0

        self.fig_inst_status.clear()
        ax1 = self.fig_inst_status.add_subplot(111)
        labels = []
        sizes = []
        colors = {"已付款": "#27ae60", "部分付款": "#f39c12", "未付款": "#95a5a6", "逾期": "#e74c3c"}
        for status, count in status_counts.items():
            if count > 0:
                labels.append(f"{status}({count})")
                sizes.append(count)

        if sizes:
            pie_colors = [colors.get(l.split("(")[0], "#3498db") for l in labels]
            wedges, texts, autotexts = ax1.pie(
                sizes, labels=labels, colors=pie_colors, autopct="%1.0f%%",
                startangle=90, textprops={"fontsize": 8}
            )
            ax1.set_title("付款状态分布", fontsize=10, fontweight="bold")
        else:
            ax1.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=10, color="gray")
            ax1.set_title("付款状态分布", fontsize=10, fontweight="bold")
        self.fig_inst_status.tight_layout()
        self.canvas_inst_status.draw()

        self.fig_inst_supplier.clear()
        ax2 = self.fig_inst_supplier.add_subplot(111)
        sorted_suppliers = sorted(supplier_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        if sorted_suppliers:
            names = [s[0][:8] for s in sorted_suppliers]
            amounts = [s[1] for s in sorted_suppliers]
            bars = ax2.barh(names, amounts, color="#3498db", alpha=0.8)
            for bar in bars:
                width = bar.get_width()
                if width > 0:
                    ax2.text(width, bar.get_y() + bar.get_height() / 2,
                             f"¥{width:,.0f}", ha="left", va="center", fontsize=7)
            ax2.set_title("供应商分期付款Top5", fontsize=10, fontweight="bold")
            ax2.set_xlabel("已付金额(元)", fontsize=8)
            ax2.tick_params(axis="both", labelsize=7)
            ax2.invert_yaxis()
        else:
            ax2.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=10, color="gray")
            ax2.set_title("供应商分期付款Top5", fontsize=10, fontweight="bold")
        self.fig_inst_supplier.tight_layout()
        self.canvas_inst_supplier.draw()

    def _add_installment_payment(self):
        PaymentRecordDialog(self, on_save=self.refresh_installment)

    def _view_installment_detail(self):
        sel = self.tree_installment.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条分期付款记录")
            return
        payment_id = int(sel[0])
        PaymentDialog(self, payment_id=payment_id, on_save=self.refresh_installment)

    def _load_flow_suppliers(self):
        rows = db.get_suppliers()
        values = ["全部"]
        for r in rows:
            values.append(f"{r['supplier_code']} - {r['supplier_name']}")
        current = self.combo_flow_supplier.get()
        self.combo_flow_supplier.configure(values=values)
        if current in values:
            self.combo_flow_supplier.set(current)
        else:
            self.combo_flow_supplier.set("全部")

    def _reset_flow(self):
        self.date_flow_start.set_date(date.today() - timedelta(days=90))
        self.date_flow_end.set_date(date.today())
        self.combo_flow_supplier.set("全部")
        self.combo_flow_method.set("全部")
        self.entry_flow_search.delete(0, "end")
        self.refresh_flow()

    def refresh_flow(self):
        for item in self.tree_flow.get_children():
            self.tree_flow.delete(item)

        start_date = self.date_flow_start.get_date().strftime("%Y-%m-%d")
        end_date = self.date_flow_end.get_date().strftime("%Y-%m-%d")

        supplier_label = self.combo_flow_supplier.get().strip()
        supplier_id = None
        if supplier_label and supplier_label != "全部":
            all_suppliers = db.get_suppliers()
            for s in all_suppliers:
                if f"{s['supplier_code']} - {s['supplier_name']}" == supplier_label:
                    supplier_id = s["id"]
                    break

        keyword = self.entry_flow_search.get().strip()
        payment_method = self.combo_flow_method.get().strip()

        data = db.get_payment_records_with_cumulative(
            supplier_id=supplier_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            payment_method=payment_method,
        )

        total_amount = 0.0
        total_unpaid = 0.0
        for d in data:
            total_amount += d["payment_amount"] or 0
            sup_name = f"{d['supplier_code'] or ''} - {d['supplier_name'] or ''}"
            mat_name = f"{d['material_code'] or ''} - {d['material_name'] or ''}"

            tag = ""
            if d["cumulative_paid"] >= d["payable_amount"] - 0.01:
                tag = "paid_full"
            elif d["cumulative_paid"] > 0:
                tag = "paid_partial"

            self.tree_flow.insert(
                "",
                "end",
                iid=str(d["id"]),
                values=(
                    d["payment_date"] or "",
                    sup_name,
                    mat_name,
                    f"¥{d['payment_amount']:.2f}",
                    f"¥{d['cumulative_paid']:.2f}",
                    f"¥{d['payable_amount']:.2f}",
                    d["payment_method"] or "",
                    d["payment_account"] or "",
                    d["handler"] or "",
                    d["voucher_no"] or "",
                    d["purchase_date"] or "",
                    (d["remark"] or "")[:25],
                ),
                tags=(tag,),
            )

        stats = db.get_payment_summary_stats(start_date, end_date)
        self.lbl_flow_count.configure(text=f"付款笔数: {len(data)}")
        self.lbl_flow_total.configure(text=f"付款总金额: ¥{total_amount:.2f}")
        self.lbl_flow_unpaid.configure(text=f"待付总额: ¥{stats['total_unpaid']:.2f}")

    def _add_flow_payment(self):
        PaymentRecordDialog(self, on_save=self.refresh_flow)

    def _edit_flow_payment(self):
        sel = self.tree_flow.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一条付款流水记录")
            return
        record_id = int(sel[0])
        PaymentRecordDialog(self, record_id=record_id, on_save=self.refresh_flow)

    def _export_flow(self):
        rows = self.tree_flow.get_children()
        if not rows:
            messagebox.showwarning("提示", "没有可导出的数据")
            return
        try:
            export_data = []
            for item in rows:
                vals = self.tree_flow.item(item, "values")
                export_data.append({
                    "付款日期": vals[0],
                    "供应商": vals[1],
                    "对应材料": vals[2],
                    "本次付款": vals[3],
                    "累计已付": vals[4],
                    "应付金额": vals[5],
                    "付款方式": vals[6],
                    "付款账户": vals[7],
                    "经手人": vals[8],
                    "凭证号": vals[9],
                    "采购日期": vals[10],
                    "备注": vals[11],
                })
            df = pd.DataFrame(export_data)
            default_name = f"付款流水_{date.today().strftime('%Y%m%d')}.xlsx"
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile=default_name,
                title="导出付款流水",
            )
            if filepath:
                df.to_excel(filepath, index=False)
                messagebox.showinfo("成功", f"已导出到: {filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def refresh_trend(self):
        self._draw_payment_trend()
        self._draw_payable_vs_paid_chart()
        self._refresh_payment_method_stats()
        self._refresh_supplier_pay_rank()

    def _draw_payable_vs_paid_chart(self):
        months = int(self.combo_trend_months.get())
        data = db.get_monthly_payable_vs_paid(months)
        self.fig_compare.clear()
        ax = self.fig_compare.add_subplot(111)
        if data and (any(d["payable_amount"] > 0 for d in data) or any(d["paid_amount"] > 0 for d in data)):
            df = pd.DataFrame(data)
            x = range(len(df["month"]))
            width = 0.35
            bars1 = ax.bar([i - width/2 for i in x], df["payable_amount"], width,
                          label="应付金额(元)", color="#e74c3c", alpha=0.7)
            bars2 = ax.bar([i + width/2 for i in x], df["paid_amount"], width,
                          label="实付金额(元)", color="#27ae60", alpha=0.7)

            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f"{height:,.0f}", ha="center", va="bottom", fontsize=7, color="#c0392b")
            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f"{height:,.0f}", ha="center", va="bottom", fontsize=7, color="#1e8449")

            ax2 = ax.twinx()
            ax2.plot(x, df["unpaid_amount"], marker="o", color="#f39c12",
                    linewidth=2, label="未付余额(元)", markersize=5)
            for i, val in enumerate(df["unpaid_amount"]):
                if val > 0:
                    ax2.text(i, val, f"{val:,.0f}", ha="center", va="bottom", fontsize=7, color="#d68910")

            ax.set_xticks(x)
            ax.set_xticklabels(df["month"], fontsize=7, rotation=45)
            ax.set_title(f"近 {months} 个月应付 vs 实付对比", fontsize=11, fontweight="bold")
            ax.set_ylabel("金额 (元)")
            ax2.set_ylabel("未付余额 (元)")
            ax.grid(True, alpha=0.3, axis="y")

            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=7)
        else:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=12, color="gray")
            ax.set_title("应付 vs 实付对比", fontsize=11, fontweight="bold")
        self.fig_compare.tight_layout()
        self.canvas_compare.draw()

    def _batch_update_overdue(self):
        result = db.batch_update_overdue_status()
        messagebox.showinfo(
            "更新完成",
            f"共检查 {result['total_checked']} 条记录，\n更新逾期状态 {result['updated_count']} 条。"
        )
        self.refresh_trend()

    def _export_trend_data(self):
        months = int(self.combo_trend_months.get())
        data = db.get_monthly_payable_vs_paid(months)
        if not data:
            messagebox.showwarning("提示", "没有可导出的数据")
            return
        try:
            df = pd.DataFrame(data)
            df.columns = ["月份", "应付金额", "实付金额", "未付金额"]
            default_name = f"付款趋势_{date.today().strftime('%Y%m%d')}.xlsx"
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile=default_name,
                title="导出付款趋势数据",
            )
            if filepath:
                df.to_excel(filepath, index=False)
                messagebox.showinfo("成功", f"已导出到: {filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def _draw_payment_trend(self):
        months = int(self.combo_trend_months.get())
        data = db.get_monthly_payment_trend(months)
        self.fig_pay_trend.clear()
        ax = self.fig_pay_trend.add_subplot(111)
        if data and any(d["total_payment"] > 0 for d in data):
            df = pd.DataFrame(data)
            bars = ax.bar(df["month"], df["total_payment"], color="#27ae60", alpha=0.8, label="实际付款金额(元)")
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f"{height:,.0f}", ha="center", va="bottom", fontsize=8)
            ax2 = ax.twinx()
            ax2.plot(df["month"], df["payment_count"], marker="s", color="#e67e22",
                     linewidth=2, label="付款笔数", markersize=5)
            ax.set_title(f"近 {months} 个月实际付款支出趋势", fontsize=13, fontweight="bold")
            ax.set_xlabel("月份")
            ax.set_ylabel("付款金额 (元)")
            ax2.set_ylabel("付款笔数")
            ax.grid(True, alpha=0.3, axis="y")
            for tick in ax.get_xticklabels():
                tick.set_rotation(45)
                tick.set_fontsize(8)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        else:
            ax.text(0.5, 0.5, "暂无付款数据", ha="center", va="center", fontsize=14, color="gray")
            ax.set_title("月度实际付款支出趋势", fontsize=13, fontweight="bold")
        self.fig_pay_trend.tight_layout()
        self.canvas_pay_trend.draw()

    def _refresh_payment_method_stats(self):
        for item in self.tree_method.get_children():
            self.tree_method.delete(item)

        months = int(self.combo_trend_months.get())
        start_date = (date.today().replace(day=1) - timedelta(days=(months - 1) * 30)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        records = db.get_payment_records(start_date=start_date, end_date=end_date)

        method_map = {}
        total_amount = 0.0
        for r in records:
            method = r["payment_method"] or "未指定"
            amt = r["payment_amount"] or 0
            total_amount += amt
            if method not in method_map:
                method_map[method] = {"count": 0, "amount": 0.0}
            method_map[method]["count"] += 1
            method_map[method]["amount"] += amt

        sorted_methods = sorted(method_map.items(), key=lambda x: x[1]["amount"], reverse=True)
        for idx, (method, info) in enumerate(sorted_methods, 1):
            ratio = (info["amount"] / total_amount * 100) if total_amount > 0 else 0
            self.tree_method.insert(
                "",
                "end",
                values=(
                    f"#{idx}",
                    method,
                    info["count"],
                    f"¥{info['amount']:.2f}",
                    f"{ratio:.1f}%",
                ),
            )
        self.lbl_method_info.configure(text=f"共{len(records)}笔 | 总金额¥{total_amount:.2f}")

    def _refresh_supplier_pay_rank(self):
        for item in self.tree_supplier_pay.get_children():
            self.tree_supplier_pay.delete(item)

        months = int(self.combo_trend_months.get())
        start_date = (date.today().replace(day=1) - timedelta(days=(months - 1) * 30)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        records = db.get_payment_records(start_date=start_date, end_date=end_date)

        sup_map = {}
        for r in records:
            key = (r["supplier_code"] or "", r["supplier_name"] or "未知供应商")
            amt = r["payment_amount"] or 0
            if key not in sup_map:
                sup_map[key] = {"count": 0, "amount": 0.0}
            sup_map[key]["count"] += 1
            sup_map[key]["amount"] += amt

        sorted_sups = sorted(sup_map.items(), key=lambda x: x[1]["amount"], reverse=True)
        total = 0.0
        for idx, ((code, name), info) in enumerate(sorted_sups[:20], 1):
            total += info["amount"]
            tag = "top3" if idx <= 3 else ""
            self.tree_supplier_pay.insert(
                "",
                "end",
                values=(
                    f"#{idx}",
                    code,
                    name,
                    info["count"],
                    f"¥{info['amount']:.2f}",
                ),
                tags=(tag,),
            )
        self.lbl_supplier_pay_info.configure(text=f"Top{min(len(sorted_sups), 20)} | 合计¥{total:.2f}")

    def refresh_due(self):
        for item in self.tree_due.get_children():
            self.tree_due.delete(item)

        days_ahead = int(self.combo_due_days.get())
        due_type = self.combo_due_type.get()
        data = db.get_upcoming_due_payments(days_ahead=days_ahead)

        if due_type == "仅逾期":
            data = [d for d in data if d["is_overdue"]]
        elif due_type == "仅即将到期":
            data = [d for d in data if d["is_upcoming"]]

        overdue_list = [d for d in data if d["is_overdue"]]
        upcoming_list = [d for d in data if d["is_upcoming"]]

        overdue_amt = sum(d["unpaid_amount"] for d in overdue_list)
        upcoming_amt = sum(d["unpaid_amount"] for d in upcoming_list)

        self.lbl_due_overdue_cnt.configure(text=f"逾期笔数: {len(overdue_list)}")
        self.lbl_due_overdue_amt.configure(text=f"逾期金额: ¥{overdue_amt:.2f}")
        self.lbl_due_soon_cnt.configure(text=f"即将到期: {len(upcoming_list)}笔")
        self.lbl_due_soon_amt.configure(text=f"到期金额: ¥{upcoming_amt:.2f}")

        self._due_data_map = {}
        for d in data:
            tag = ""
            if d["is_overdue"]:
                if d["overdue_days"] >= 30:
                    tag = "overdue30"
                elif d["overdue_days"] >= 15:
                    tag = "overdue15"
                else:
                    tag = "overdue7"
                alert_text = f"🔴 逾期{d['overdue_days']}天"
            else:
                if d["days_until_due"] <= 7:
                    tag = "soon7"
                elif d["days_until_due"] <= 15:
                    tag = "soon15"
                else:
                    tag = "soon30"
                alert_text = f"🟡 {d['days_until_due']}天后到期"

            mat_name = f"{d['material_code'] or ''} - {d['material_name'] or ''}"
            self._due_data_map[str(d["payment_id"])] = d
            self.tree_due.insert(
                "",
                "end",
                iid=str(d["payment_id"]),
                values=(
                    "☐",
                    alert_text,
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
        self._update_selected_count()

    def _on_tree_due_click(self, event):
        region = self.tree_due.identify("region", event.x, event.y)
        column = self.tree_due.identify_column(event.x)
        row_id = self.tree_due.identify_row(event.y)
        if region == "cell" and column == "#1" and row_id:
            current_values = list(self.tree_due.item(row_id, "values"))
            if current_values[0] == "☐":
                current_values[0] = "☑"
            else:
                current_values[0] = "☐"
            self.tree_due.item(row_id, values=tuple(current_values))
            self._update_selected_count()
            return "break"

    def _update_selected_count(self):
        selected_count = 0
        selected_amount = 0.0
        for item_id in self.tree_due.get_children():
            values = self.tree_due.item(item_id, "values")
            if values and values[0] == "☑":
                selected_count += 1
                data = self._due_data_map.get(item_id)
                if data:
                    selected_amount += data["unpaid_amount"]
        self.lbl_due_selected.configure(text=f"已选: {selected_count}笔 / ¥{selected_amount:.2f}")

    def _select_all_due(self):
        for item_id in self.tree_due.get_children():
            values = list(self.tree_due.item(item_id, "values"))
            if values:
                values[0] = "☑"
                self.tree_due.item(item_id, values=tuple(values))
        self._update_selected_count()

    def _deselect_all_due(self):
        for item_id in self.tree_due.get_children():
            values = list(self.tree_due.item(item_id, "values"))
            if values:
                values[0] = "☐"
                self.tree_due.item(item_id, values=tuple(values))
        self._update_selected_count()

    def _get_checked_payment_ids(self):
        checked = []
        for item_id in self.tree_due.get_children():
            values = self.tree_due.item(item_id, "values")
            if values and values[0] == "☑":
                checked.append(int(item_id))
        return checked

    def _batch_mark_processed(self):
        checked = self._get_checked_payment_ids()
        if not checked:
            messagebox.showwarning("提示", "请先勾选要标记的记录")
            return
        if not messagebox.askyesno("确认", f"确定要标记 {len(checked)} 条记录为已处理吗？"):
            return
        success = 0
        for payment_id in checked:
            data = {"remark": "已标记处理"}
            result = db.update_purchase_payment(payment_id, data)
            if result["success"]:
                success += 1
        messagebox.showinfo("完成", f"成功标记 {success}/{len(checked)} 条记录")
        self.refresh_due()

    def _export_due_list(self):
        data_list = []
        for item_id in self.tree_due.get_children():
            values = self.tree_due.item(item_id, "values")
            data = self._due_data_map.get(item_id)
            if data:
                alert_text = values[1] if len(values) > 1 else ""
                data_list.append({
                    "提醒": alert_text,
                    "供应商": data.get("supplier_name", ""),
                    "采购日期": data.get("purchase_date", ""),
                    "到期日期": data.get("due_date", ""),
                    "材料名称": f"{data.get('material_code', '')} - {data.get('material_name', '')}",
                    "应付金额": data.get("payable_amount", 0),
                    "已付金额": data.get("paid_amount", 0),
                    "未付金额": data.get("unpaid_amount", 0),
                    "联系人": data.get("contact_person", ""),
                    "联系电话": data.get("contact_phone", ""),
                    "付款状态": data.get("payment_status", ""),
                    "备注": data.get("remark", ""),
                })
        if not data_list:
            messagebox.showwarning("提示", "没有可导出的数据")
            return
        try:
            df = pd.DataFrame(data_list)
            default_name = f"应付款提醒_{date.today().strftime('%Y%m%d')}.xlsx"
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile=default_name,
                title="导出应付款提醒列表",
            )
            if filepath:
                df.to_excel(filepath, index=False)
                messagebox.showinfo("成功", f"已导出到: {filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def _pay_from_due(self):
        checked = self._get_checked_payment_ids()
        if not checked:
            sel = self.tree_due.selection()
            if not sel:
                messagebox.showwarning("提示", "请先勾选或选择要付款的记录")
                return
            checked = [int(sel[0])]
        if len(checked) == 1:
            PaymentDialog(self, payment_id=checked[0], on_save=self.refresh_due)
        else:
            if not messagebox.askyesno("确认", f"确定要对 {len(checked)} 条记录进行批量快捷付款登记吗？"):
                return
            success = 0
            for payment_id in checked:
                pay_data = self._due_data_map.get(str(payment_id))
                if pay_data and pay_data["unpaid_amount"] > 0:
                    data = {
                        "purchase_id": pay_data["purchase_id"],
                        "payment_amount": pay_data["unpaid_amount"],
                        "payment_date": date.today().isoformat(),
                        "payment_method": "银行转账",
                        "payment_account": "",
                        "handler": "",
                        "voucher_no": "",
                        "remark": "批量快捷付款",
                    }
                    result = db.add_payment_record(data)
                    if result["success"]:
                        success += 1
            messagebox.showinfo("完成", f"成功登记 {success}/{len(checked)} 条付款记录")
            self.refresh_due()

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
        PaymentRecordDialog(self, on_save=self._on_payment_change)

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
