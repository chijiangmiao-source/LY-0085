import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection


def validate_supplier(data: Dict) -> Tuple[bool, str]:
    if not data.get("supplier_code"):
        return False, "供应商编号不能为空"
    if not data.get("supplier_name"):
        return False, "供应商名称不能为空"
    credit_limit = data.get("credit_limit", 0)
    if credit_limit < 0:
        return False, "信用额度必须大于等于 0"
    payment_days = data.get("payment_days", 30)
    if payment_days < 0:
        return False, "账期天数必须大于等于 0"
    return True, ""


def add_supplier(data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_supplier(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO suppliers (supplier_code, supplier_name, contact_person, contact_phone,
               address, bank_account, tax_number, credit_limit, payment_days, supplier_status, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["supplier_code"],
                data["supplier_name"],
                data.get("contact_person", ""),
                data.get("contact_phone", ""),
                data.get("address", ""),
                data.get("bank_account", ""),
                data.get("tax_number", ""),
                data.get("credit_limit", 0),
                data.get("payment_days", 30),
                data.get("supplier_status", "正常"),
                data.get("remark", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True, "添加成功"
    except sqlite3.IntegrityError:
        return False, "供应商编号已存在，不能重复"
    finally:
        conn.close()


def update_supplier(supplier_id: int, data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_supplier(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE suppliers SET supplier_code=?, supplier_name=?, contact_person=?, contact_phone=?,
               address=?, bank_account=?, tax_number=?, credit_limit=?, payment_days=?, supplier_status=?, remark=?
               WHERE id=?""",
            (
                data["supplier_code"],
                data["supplier_name"],
                data.get("contact_person", ""),
                data.get("contact_phone", ""),
                data.get("address", ""),
                data.get("bank_account", ""),
                data.get("tax_number", ""),
                data.get("credit_limit", 0),
                data.get("payment_days", 30),
                data.get("supplier_status", "正常"),
                data.get("remark", ""),
                supplier_id,
            ),
        )
        conn.commit()
        return True, "更新成功"
    except sqlite3.IntegrityError:
        return False, "供应商编号已存在，不能重复"
    finally:
        conn.close()


def delete_supplier(supplier_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM purchase_payments WHERE supplier_id=?", (supplier_id,))
        if cursor.fetchone()[0] > 0:
            return False, "该供应商存在付款记录，无法删除"
        cursor.execute("SELECT COUNT(*) FROM stock_purchases WHERE supplier_id=?", (supplier_id,))
        if cursor.fetchone()[0] > 0:
            return False, "该供应商存在采购记录，无法删除"
        cursor.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
        conn.commit()
        return True, "删除成功"
    finally:
        conn.close()


def get_suppliers(keyword: str = "", status: str = "") -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if keyword:
        query += " AND (supplier_code LIKE ? OR supplier_name LIKE ? OR contact_person LIKE ? OR contact_phone LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    if status and status != "全部":
        query += " AND supplier_status = ?"
        params.append(status)
    query += " ORDER BY supplier_code"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_supplier_by_id(supplier_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_supplier_by_code(code: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_code=?", (code,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_supplier_debt_summary(start_date: str = "", end_date: str = "") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            s.id as supplier_id,
            s.supplier_code,
            s.supplier_name,
            s.contact_person,
            s.contact_phone,
            s.credit_limit,
            COUNT(pp.id) as payment_count,
            SUM(pp.payable_amount) as total_payable,
            SUM(pp.paid_amount) as total_paid,
            SUM(CASE WHEN pp.payment_status IN ('未付款', '部分付款', '逾期') THEN 1 ELSE 0 END) as unpaid_count
        FROM suppliers s
        LEFT JOIN purchase_payments pp ON s.id = pp.supplier_id
        LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND sp.purchase_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sp.purchase_date <= ?"
        params.append(end_date)
    query += " GROUP BY s.id ORDER BY (SUM(pp.payable_amount) - SUM(pp.paid_amount)) DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        total_payable = row["total_payable"] or 0
        total_paid = row["total_paid"] or 0
        unpaid = round(total_payable - total_paid, 2)
        result.append({
            "supplier_id": row["supplier_id"],
            "supplier_code": row["supplier_code"],
            "supplier_name": row["supplier_name"],
            "contact_person": row["contact_person"] or "",
            "contact_phone": row["contact_phone"] or "",
            "credit_limit": row["credit_limit"] or 0,
            "payment_count": row["payment_count"] or 0,
            "total_payable": round(total_payable, 2),
            "total_paid": round(total_paid, 2),
            "unpaid_amount": unpaid,
            "unpaid_count": row["unpaid_count"] or 0,
            "credit_usage": round((unpaid / (row["credit_limit"] or 1) * 100), 2) if row["credit_limit"] else 0,
        })
    return result
