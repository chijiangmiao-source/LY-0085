import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection
from utils.payment_utils import (
    calculate_payment_status,
    calculate_due_date,
)


def validate_purchase_payment(data: Dict) -> Tuple[bool, str]:
    if not data.get("purchase_id"):
        return False, "请选择采购记录"
    if not data.get("supplier_id"):
        return False, "请选择供应商"
    payable = data.get("payable_amount", 0)
    if payable <= 0:
        return False, "应付金额必须大于 0"
    paid = data.get("paid_amount", 0)
    if paid < 0:
        return False, "已付金额不能小于 0"
    if paid > payable + 0.01:
        return False, f"已付金额({paid})不能超过应付金额({payable})"
    status = data.get("payment_status", "未付款")
    if status not in ("未付款", "部分付款", "已付款", "逾期"):
        return False, "无效的付款状态"
    return True, ""


def validate_payment_record(data: Dict) -> Tuple[bool, str]:
    if not data.get("purchase_id"):
        return False, "请选择采购记录"
    if not data.get("supplier_id"):
        return False, "请选择供应商"
    amount = data.get("payment_amount", 0)
    if amount <= 0:
        return False, "付款金额必须大于 0"
    if not data.get("payment_date"):
        return False, "付款日期不能为空"
    return True, ""


def add_purchase_payment(data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_purchase_payment(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM purchase_payments WHERE purchase_id=?", (data["purchase_id"],))
        if cursor.fetchone()[0] > 0:
            return True, "付款汇总记录已存在，可通过新增付款流水进行分期付款登记"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = data.get("payment_status", "未付款")
        cursor.execute(
            """INSERT INTO purchase_payments (purchase_id, supplier_id, payable_amount, paid_amount,
               payment_date, payment_status, remark, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["purchase_id"],
                data["supplier_id"],
                data["payable_amount"],
                data.get("paid_amount", 0),
                data.get("payment_date") or None,
                status,
                data.get("remark", ""),
                now,
                now,
            ),
        )
        conn.commit()
        return True, "付款汇总记录创建成功，可通过新增付款流水进行分期付款登记"
    except Exception as e:
        return False, f"添加失败: {e}"
    finally:
        conn.close()


def update_purchase_payment(payment_id: int, data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_purchase_payment(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        status = data.get("payment_status", "未付款")
        cursor.execute(
            """UPDATE purchase_payments SET supplier_id=?, payable_amount=?, paid_amount=?,
               payment_date=?, payment_status=?, remark=?, updated_at=? WHERE id=?""",
            (
                data["supplier_id"],
                data["payable_amount"],
                data.get("paid_amount", 0),
                data.get("payment_date") or None,
                status,
                data.get("remark", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                payment_id,
            ),
        )
        conn.commit()
        return True, "更新成功"
    except Exception as e:
        return False, f"更新失败: {e}"
    finally:
        conn.close()


def delete_purchase_payment(payment_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM purchase_payments WHERE id=?", (payment_id,))
        conn.commit()
        return True, "删除成功"
    finally:
        conn.close()


def get_purchase_payments(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    supplier_id: Optional[int] = None,
    status: str = "",
) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT pp.*, sp.purchase_date, sp.purchase_quantity, sp.unit_price, sp.total_amount,
               m.material_code, m.material_name,
               s.supplier_code, s.supplier_name, s.payment_days
        FROM purchase_payments pp
        LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
        LEFT JOIN materials m ON sp.material_id = m.id
        LEFT JOIN suppliers s ON pp.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND sp.purchase_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sp.purchase_date <= ?"
        params.append(end_date)
    if keyword:
        query += " AND (s.supplier_name LIKE ? OR s.supplier_code LIKE ? OR m.material_name LIKE ? OR m.material_code LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    if supplier_id:
        query += " AND pp.supplier_id = ?"
        params.append(supplier_id)
    if status and status != "全部":
        query += " AND pp.payment_status = ?"
        params.append(status)
    query += " ORDER BY sp.purchase_date DESC, pp.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_purchase_payment_by_id(payment_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.*, sp.purchase_date, sp.total_amount, s.supplier_name
        FROM purchase_payments pp
        LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
        LEFT JOIN suppliers s ON pp.supplier_id = s.id
        WHERE pp.id=?
    """, (payment_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_purchase_payment_by_purchase_id(purchase_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.*, sp.purchase_date, sp.total_amount, sp.purchase_quantity, sp.unit_price,
               s.supplier_name, s.supplier_code, s.payment_days, s.contact_person, s.contact_phone,
               m.material_code, m.material_name, m.material_spec
        FROM purchase_payments pp
        LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
        LEFT JOIN suppliers s ON pp.supplier_id = s.id
        LEFT JOIN materials m ON sp.material_id = m.id
        WHERE pp.purchase_id = ?
    """, (purchase_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_unpaid_purchases(supplier_id: Optional[int] = None) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT sp.*, m.material_code, m.material_name, s.supplier_code, s.supplier_name, s.payment_days,
               pp.payable_amount, pp.paid_amount, pp.payment_status, pp.id as payment_id
        FROM stock_purchases sp
        LEFT JOIN materials m ON sp.material_id = m.id
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        LEFT JOIN purchase_payments pp ON sp.id = pp.purchase_id
        WHERE pp.payment_status IS NULL OR pp.payment_status IN ('未付款', '部分付款', '逾期')
    """
    params = []
    if supplier_id:
        query += " AND sp.supplier_id = ?"
        params.append(supplier_id)
    query += " ORDER BY sp.purchase_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_payment_record(data: Dict, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    valid, msg = validate_payment_record(data)
    if not valid:
        return False, msg

    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, payable_amount FROM purchase_payments WHERE purchase_id = ?",
                       (data["purchase_id"],))
        pp_row = cursor.fetchone()
        if not pp_row:
            return False, "未找到对应的付款汇总记录，请先创建付款登记"

        cursor.execute("""
            SELECT SUM(payment_amount) as total_paid
            FROM payment_records
            WHERE purchase_id = ?
        """, (data["purchase_id"],))
        sum_row = cursor.fetchone()
        current_paid = sum_row["total_paid"] or 0 if sum_row else 0
        new_paid = current_paid + data["payment_amount"]
        if new_paid > pp_row["payable_amount"] + 0.01:
            return False, f"累计付款金额({new_paid:.2f})不能超过应付金额({pp_row['payable_amount']:.2f})"

        cursor.execute(
            """INSERT INTO payment_records (purchase_id, supplier_id, payment_amount,
               payment_date, payment_method, payment_account, handler, voucher_no, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["purchase_id"],
                data["supplier_id"],
                data["payment_amount"],
                data.get("payment_date"),
                data.get("payment_method", ""),
                data.get("payment_account", ""),
                data.get("handler", ""),
                data.get("voucher_no", ""),
                data.get("remark", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        if should_close:
            conn.commit()
        return True, "付款登记成功"
    except Exception as e:
        if should_close:
            conn.rollback()
        return False, f"登记失败: {e}"
    finally:
        if should_close:
            conn.close()


def update_payment_record(record_id: int, data: Dict, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    valid, msg = validate_payment_record(data)
    if not valid:
        return False, msg

    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT purchase_id, payment_amount FROM payment_records WHERE id = ?", (record_id,))
        old_row = cursor.fetchone()
        if not old_row:
            return False, "付款记录不存在"

        cursor.execute("SELECT payable_amount FROM purchase_payments WHERE purchase_id = ?",
                       (old_row["purchase_id"],))
        pp_row = cursor.fetchone()
        if not pp_row:
            return False, "未找到对应的付款汇总记录"

        cursor.execute("""
            SELECT SUM(payment_amount) as total_paid
            FROM payment_records
            WHERE purchase_id = ? AND id != ?
        """, (old_row["purchase_id"], record_id))
        sum_row = cursor.fetchone()
        other_paid = sum_row["total_paid"] or 0 if sum_row else 0
        new_total = other_paid + data["payment_amount"]
        if new_total > pp_row["payable_amount"] + 0.01:
            return False, f"累计付款金额({new_total:.2f})不能超过应付金额({pp_row['payable_amount']:.2f})"

        cursor.execute(
            """UPDATE payment_records SET payment_amount=?, payment_date=?, payment_method=?,
               payment_account=?, handler=?, voucher_no=?, remark=? WHERE id=?""",
            (
                data["payment_amount"],
                data.get("payment_date"),
                data.get("payment_method", ""),
                data.get("payment_account", ""),
                data.get("handler", ""),
                data.get("voucher_no", ""),
                data.get("remark", ""),
                record_id,
            ),
        )

        if should_close:
            conn.commit()
        return True, "更新成功"
    except Exception as e:
        if should_close:
            conn.rollback()
        return False, f"更新失败: {e}"
    finally:
        if should_close:
            conn.close()


def delete_payment_record(record_id: int, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT purchase_id FROM payment_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            return False, "记录不存在"
        purchase_id = row["purchase_id"]

        cursor.execute("DELETE FROM payment_records WHERE id = ?", (record_id,))

        if should_close:
            conn.commit()
        return True, "删除成功"
    except Exception as e:
        if should_close:
            conn.rollback()
        return False, f"删除失败: {e}"
    finally:
        if should_close:
            conn.close()


def get_payment_records(
    purchase_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    payment_method: str = "",
) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT pr.*, sp.purchase_date, sp.total_amount,
               m.material_code, m.material_name,
               s.supplier_code, s.supplier_name
        FROM payment_records pr
        LEFT JOIN stock_purchases sp ON pr.purchase_id = sp.id
        LEFT JOIN materials m ON sp.material_id = m.id
        LEFT JOIN suppliers s ON pr.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if purchase_id:
        query += " AND pr.purchase_id = ?"
        params.append(purchase_id)
    if supplier_id:
        query += " AND pr.supplier_id = ?"
        params.append(supplier_id)
    if start_date:
        query += " AND pr.payment_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND pr.payment_date <= ?"
        params.append(end_date)
    if keyword:
        query += " AND (s.supplier_name LIKE ? OR s.supplier_code LIKE ? OR m.material_name LIKE ? OR pr.voucher_no LIKE ? OR pr.handler LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like, like])
    if payment_method and payment_method != "全部":
        query += " AND pr.payment_method = ?"
        params.append(payment_method)
    query += " ORDER BY pr.payment_date DESC, pr.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_payment_records_by_purchase(purchase_id: int) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, s.supplier_code, s.supplier_name,
               m.material_code, m.material_name
        FROM payment_records pr
        LEFT JOIN suppliers s ON pr.supplier_id = s.id
        LEFT JOIN stock_purchases sp ON pr.purchase_id = sp.id
        LEFT JOIN materials m ON sp.material_id = m.id
        WHERE pr.purchase_id = ?
        ORDER BY pr.payment_date DESC, pr.id DESC
    """, (purchase_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_payment_record_by_id(record_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, sp.purchase_date, sp.total_amount, sp.purchase_quantity, sp.unit_price,
               m.material_code, m.material_name, m.material_spec,
               s.supplier_code, s.supplier_name, s.payment_days
        FROM payment_records pr
        LEFT JOIN stock_purchases sp ON pr.purchase_id = sp.id
        LEFT JOIN materials m ON sp.material_id = m.id
        LEFT JOIN suppliers s ON pr.supplier_id = s.id
        WHERE pr.id = ?
    """, (record_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_total_paid_by_purchase(purchase_id: int, conn: Optional[sqlite3.Connection] = None) -> float:
    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT SUM(payment_amount) as total_paid
            FROM payment_records
            WHERE purchase_id = ?
        """, (purchase_id,))
        row = cursor.fetchone()
        total_paid = row["total_paid"] or 0 if row else 0
        return round(total_paid, 2)
    finally:
        if should_close:
            conn.close()


def get_last_pay_date_by_purchase(purchase_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT MAX(payment_date) as last_pay_date
            FROM payment_records
            WHERE purchase_id = ?
        """, (purchase_id,))
        row = cursor.fetchone()
        return row["last_pay_date"] if row else None
    finally:
        if should_close:
            conn.close()


def update_purchase_payment_summary(purchase_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        total_paid = get_total_paid_by_purchase(purchase_id, conn)

        cursor.execute("""
            SELECT pp.payable_amount, sp.purchase_date, s.payment_days
            FROM purchase_payments pp
            LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
            LEFT JOIN suppliers s ON pp.supplier_id = s.id
            WHERE pp.purchase_id = ?
        """, (purchase_id,))
        pp_row = cursor.fetchone()
        if not pp_row:
            return

        payable = pp_row["payable_amount"] or 0
        purchase_date = pp_row["purchase_date"] or ""
        payment_days = pp_row["payment_days"] or 30
        due_date = calculate_due_date(purchase_date, payment_days) or ""

        status = calculate_payment_status(payable, total_paid, due_date)
        last_pay_date = get_last_pay_date_by_purchase(purchase_id, conn)

        cursor.execute("""
            UPDATE purchase_payments
            SET paid_amount = ?, payment_status = ?, payment_date = ?, updated_at = ?
            WHERE purchase_id = ?
        """, (
            total_paid,
            status,
            last_pay_date,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            purchase_id,
        ))

        if should_close:
            conn.commit()
    finally:
        if should_close:
            conn.close()


def get_payment_records_with_cumulative(
    supplier_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    payment_method: str = "",
) -> List[Dict]:
    records = get_payment_records(
        supplier_id=supplier_id,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        payment_method=payment_method,
    )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cumulative_map = {}
        purchase_payable_map = {}

        for r in records:
            pid = r["purchase_id"]
            if pid not in cumulative_map:
                cursor.execute("""
                    SELECT SUM(payment_amount) as total_paid
                    FROM payment_records
                    WHERE purchase_id = ? AND payment_date <= ?
                """, (pid, r["payment_date"]))
                row = cursor.fetchone()
                cumulative_map[pid] = row["total_paid"] or 0 if row else 0

                cursor.execute("""
                    SELECT payable_amount FROM purchase_payments WHERE purchase_id = ?
                """, (pid,))
                pp_row = cursor.fetchone()
                purchase_payable_map[pid] = pp_row["payable_amount"] if pp_row else 0

        result = []
        for r in records:
            pid = r["purchase_id"]
            result.append({
                "id": r["id"],
                "purchase_id": pid,
                "supplier_id": r["supplier_id"],
                "supplier_code": r["supplier_code"],
                "supplier_name": r["supplier_name"],
                "material_code": r["material_code"],
                "material_name": r["material_name"],
                "purchase_date": r["purchase_date"],
                "payment_amount": r["payment_amount"],
                "payment_date": r["payment_date"],
                "payment_method": r["payment_method"],
                "payment_account": r["payment_account"],
                "handler": r["handler"],
                "voucher_no": r["voucher_no"],
                "remark": r["remark"],
                "created_at": r["created_at"],
                "cumulative_paid": cumulative_map.get(pid, 0),
                "payable_amount": purchase_payable_map.get(pid, 0),
            })
        return result
    finally:
        conn.close()


def batch_update_overdue_status() -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT pp.id, pp.payable_amount, pp.paid_amount, pp.payment_status,
                   sp.purchase_date, s.payment_days
            FROM purchase_payments pp
            LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
            LEFT JOIN suppliers s ON pp.supplier_id = s.id
            WHERE pp.payment_status IN ('未付款', '部分付款', '逾期')
        """)
        rows = cursor.fetchall()

        updated_count = 0
        for row in rows:
            payable = row["payable_amount"] or 0
            paid = row["paid_amount"] or 0
            purchase_date = row["purchase_date"] or ""
            payment_days = row["payment_days"] or 30
            due_date = calculate_due_date(purchase_date, payment_days) or ""

            new_status = calculate_payment_status(payable, paid, due_date)
            if new_status != row["payment_status"]:
                cursor.execute("""
                    UPDATE purchase_payments
                    SET payment_status = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    new_status,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    row["id"],
                ))
                updated_count += 1

        conn.commit()
        return {
            "total_checked": len(rows),
            "updated_count": updated_count,
        }
    finally:
        conn.close()


def get_payment_summary_stats(start_date: str = "", end_date: str = "") -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                COUNT(*) as total_records,
                SUM(payable_amount) as total_payable,
                SUM(paid_amount) as total_paid,
                SUM(CASE WHEN payment_status = '已付款' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN payment_status = '部分付款' THEN 1 ELSE 0 END) as partial_count,
                SUM(CASE WHEN payment_status = '未付款' THEN 1 ELSE 0 END) as unpaid_count,
                SUM(CASE WHEN payment_status = '逾期' THEN 1 ELSE 0 END) as overdue_count
            FROM purchase_payments pp
            LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
            WHERE 1=1
        """ + (" AND sp.purchase_date >= ?" if start_date else "") +
          (" AND sp.purchase_date <= ?" if end_date else ""),
          ([start_date] if start_date else []) + ([end_date] if end_date else []))
        row = cursor.fetchone()

        total_payable = row["total_payable"] or 0
        total_paid = row["total_paid"] or 0

        return {
            "total_records": row["total_records"] or 0,
            "total_payable": round(total_payable, 2),
            "total_paid": round(total_paid, 2),
            "total_unpaid": round(total_payable - total_paid, 2),
            "paid_count": row["paid_count"] or 0,
            "partial_count": row["partial_count"] or 0,
            "unpaid_count": row["unpaid_count"] or 0,
            "overdue_count": row["overdue_count"] or 0,
        }
    finally:
        conn.close()
