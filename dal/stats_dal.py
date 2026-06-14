import sqlite3
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection
from dal.purchase_dal import get_avg_unit_price
from dal.payment_dal import get_payment_records
from utils.payment_utils import (
    calculate_payment_status,
    calculate_due_date,
    calculate_days_until_due,
    calculate_overdue_days,
    calculate_payment_summary,
)


def get_rework_rate_threshold() -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='rework_rate_threshold'")
    row = cursor.fetchone()
    conn.close()
    return float(row["value"]) if row else 0.15


def set_rework_rate_threshold(value: float) -> Tuple[bool, str]:
    if value < 0 or value > 1:
        return False, "阈值必须在 0 到 1 之间"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("rework_rate_threshold", str(value)),
    )
    conn.commit()
    conn.close()
    return True, "保存成功"


def get_7day_rework_warnings() -> List[Dict]:
    threshold = get_rework_rate_threshold()
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.id as material_id,
            m.material_code,
            m.material_name,
            COUNT(cr.id) as total_records,
            SUM(CASE WHEN cr.rework_count > 0 THEN 1 ELSE 0 END) as rework_records,
            SUM(cr.rework_count) as total_reworks,
            SUM(cr.used_quantity) as total_used
        FROM materials m
        LEFT JOIN construction_records cr ON m.id = cr.material_id AND cr.construction_date >= ?
        GROUP BY m.id
        HAVING total_records > 0
    """, (seven_days_ago,))
    rows = cursor.fetchall()
    conn.close()

    warnings = []
    for row in rows:
        total = row["total_records"]
        rework_records = row["rework_records"] or 0
        if total > 0:
            rate = rework_records / total
            if rate > threshold:
                warnings.append({
                    "material_id": row["material_id"],
                    "material_code": row["material_code"],
                    "material_name": row["material_name"],
                    "total_records": total,
                    "rework_records": rework_records,
                    "total_reworks": row["total_reworks"] or 0,
                    "total_used": row["total_used"] or 0,
                    "rework_rate": rate,
                    "threshold": threshold,
                })
    return warnings


def get_material_usage_stats(start_date: str = "", end_date: str = "") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            m.id as material_id,
            m.material_code,
            m.material_name,
            m.material_spec,
            m.current_stock,
            m.safety_stock,
            COUNT(cr.id) as record_count,
            SUM(cr.used_quantity) as total_used,
            SUM(cr.rework_count) as total_reworks,
            SUM(CASE WHEN cr.rework_count >= 2 THEN 1 ELSE 0 END) as abnormal_count
        FROM materials m
        LEFT JOIN construction_records cr ON m.id = cr.material_id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND cr.construction_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND cr.construction_date <= ?"
        params.append(end_date)
    query += " GROUP BY m.id ORDER BY total_used DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        total_used = row["total_used"] or 0
        total_reworks = row["total_reworks"] or 0
        record_count = row["record_count"] or 0
        rework_rate = (total_reworks / record_count) if record_count > 0 else 0
        result.append({
            "material_id": row["material_id"],
            "material_code": row["material_code"],
            "material_name": row["material_name"],
            "material_spec": row["material_spec"],
            "current_stock": row["current_stock"],
            "safety_stock": row["safety_stock"],
            "record_count": record_count,
            "total_used": total_used,
            "total_reworks": total_reworks,
            "abnormal_count": row["abnormal_count"] or 0,
            "rework_rate": rework_rate,
        })
    return result


def get_daily_usage_trend(days: int = 30) -> List[Dict]:
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            construction_date,
            SUM(used_quantity) as total_used,
            SUM(rework_count) as total_reworks,
            COUNT(*) as record_count
        FROM construction_records
        WHERE construction_date >= ?
        GROUP BY construction_date
        ORDER BY construction_date
    """, (start_date,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unit_order_material_cost(start_date: str = "", end_date: str = "") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            cr.order_no,
            cr.construction_date,
            SUM(cr.used_quantity) as total_qty,
            SUM(cr.rework_count) as total_reworks,
            GROUP_CONCAT(DISTINCT m.material_name, ', ') as materials_used
        FROM construction_records cr
        LEFT JOIN materials m ON cr.material_id = m.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND cr.construction_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND cr.construction_date <= ?"
        params.append(end_date)
    query += " GROUP BY cr.order_no, cr.construction_date ORDER BY cr.construction_date DESC"
    cursor.execute(query, params)
    order_rows = cursor.fetchall()

    result = []
    for row in order_rows:
        order_no = row["order_no"]
        cursor.execute("""
            SELECT cr.material_id, cr.used_quantity, cr.rework_count
            FROM construction_records cr
            WHERE cr.order_no = ? AND cr.construction_date = ?
        """, (order_no, row["construction_date"]))
        items = cursor.fetchall()

        total_cost = 0.0
        total_loss_cost = 0.0
        for item in items:
            avg_price = get_avg_unit_price(item["material_id"])
            used_qty = item["used_quantity"]
            rework_count = item["rework_count"]
            total_cost += used_qty * avg_price
            if rework_count > 0:
                loss_qty = used_qty * (rework_count / (rework_count + 1))
                total_loss_cost += loss_qty * avg_price

        result.append({
            "order_no": order_no,
            "construction_date": row["construction_date"],
            "materials_used": row["materials_used"] or "",
            "total_qty": row["total_qty"] or 0,
            "total_reworks": row["total_reworks"] or 0,
            "total_cost": round(total_cost, 2),
            "loss_cost": round(total_loss_cost, 2),
            "unit_cost": round(total_cost / max(row["total_qty"], 1), 2),
        })
    conn.close()
    return result


def get_30day_material_loss_cost() -> Dict:
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            cr.material_id,
            m.material_code,
            m.material_name,
            SUM(cr.used_quantity) as total_used,
            SUM(cr.rework_count) as total_reworks,
            COUNT(*) as record_count
        FROM construction_records cr
        LEFT JOIN materials m ON cr.material_id = m.id
        WHERE cr.construction_date >= ? AND cr.construction_date <= ?
        GROUP BY cr.material_id
        HAVING total_used > 0
        ORDER BY total_used DESC
    """, (thirty_days_ago, today))
    rows = cursor.fetchall()

    total_purchase_cost = 0.0
    total_loss_cost = 0.0
    material_details = []

    for row in rows:
        avg_price = get_avg_unit_price(row["material_id"])
        used_cost = (row["total_used"] or 0) * avg_price
        reworks = row["total_reworks"] or 0
        records = row["record_count"] or 0

        if records > 0 and reworks > 0:
            loss_ratio = reworks / (records + reworks)
            loss_cost = used_cost * loss_ratio
        else:
            loss_cost = 0.0

        total_purchase_cost += used_cost
        total_loss_cost += loss_cost

        material_details.append({
            "material_id": row["material_id"],
            "material_code": row["material_code"],
            "material_name": row["material_name"],
            "total_used": row["total_used"] or 0,
            "total_reworks": reworks,
            "avg_price": round(avg_price, 2),
            "used_cost": round(used_cost, 2),
            "loss_cost": round(loss_cost, 2),
            "loss_ratio": round((loss_cost / used_cost * 100) if used_cost > 0 else 0, 2),
        })

    conn.close()
    return {
        "period_start": thirty_days_ago,
        "period_end": today,
        "total_purchase_cost": round(total_purchase_cost, 2),
        "total_loss_cost": round(total_loss_cost, 2),
        "loss_rate": round((total_loss_cost / total_purchase_cost * 100) if total_purchase_cost > 0 else 0, 2),
        "materials": material_details,
    }


def get_high_loss_high_cost_materials(start_date: str = "", end_date: str = "", top_n: int = 10) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            cr.material_id,
            m.material_code,
            m.material_name,
            m.material_spec,
            SUM(cr.used_quantity) as total_used,
            SUM(cr.rework_count) as total_reworks,
            COUNT(*) as record_count,
            SUM(CASE WHEN cr.rework_count >= 2 THEN 1 ELSE 0 END) as abnormal_count
        FROM construction_records cr
        LEFT JOIN materials m ON cr.material_id = m.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND cr.construction_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND cr.construction_date <= ?"
        params.append(end_date)
    query += " GROUP BY cr.material_id HAVING total_used > 0"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        avg_price = get_avg_unit_price(row["material_id"])
        total_used = row["total_used"] or 0
        total_reworks = row["total_reworks"] or 0
        records = row["record_count"] or 0
        abnormal_count = row["abnormal_count"] or 0

        total_cost = total_used * avg_price

        if records > 0 and total_reworks > 0:
            loss_ratio = total_reworks / (records + total_reworks)
            loss_cost = total_cost * loss_ratio
        else:
            loss_ratio = 0
            loss_cost = 0

        result.append({
            "material_id": row["material_id"],
            "material_code": row["material_code"],
            "material_name": row["material_name"],
            "material_spec": row["material_spec"] or "",
            "total_used": total_used,
            "total_reworks": total_reworks,
            "abnormal_count": abnormal_count,
            "avg_price": round(avg_price, 2),
            "total_cost": round(total_cost, 2),
            "loss_cost": round(loss_cost, 2),
            "loss_ratio": round(loss_ratio * 100, 2),
            "score": round(loss_cost + total_cost * 0.3, 2),
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return result[:top_n]


def get_purchase_payment_with_records(purchase_id: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.*, sp.purchase_date, sp.total_amount, sp.purchase_quantity, sp.unit_price,
               s.supplier_code, s.supplier_name, s.payment_days, s.contact_person, s.contact_phone,
               m.material_code, m.material_name, m.material_spec
        FROM purchase_payments pp
        LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
        LEFT JOIN suppliers s ON pp.supplier_id = s.id
        LEFT JOIN materials m ON sp.material_id = m.id
        WHERE pp.purchase_id = ?
    """, (purchase_id,))
    pp_row = cursor.fetchone()
    if not pp_row:
        conn.close()
        return None

    cursor.execute("""
        SELECT pr.*, s.supplier_code, s.supplier_name,
               m.material_code, m.material_name
        FROM payment_records pr
        LEFT JOIN suppliers s ON pr.supplier_id = s.id
        LEFT JOIN stock_purchases sp ON pr.purchase_id = sp.id
        LEFT JOIN materials m ON sp.material_id = m.id
        WHERE pr.purchase_id = ?
        ORDER BY pr.payment_date ASC, pr.id ASC
    """, (purchase_id,))
    records = cursor.fetchall()
    conn.close()

    record_list = []
    cumulative = 0.0
    for r in records:
        cumulative += r["payment_amount"] or 0
        record_list.append({
            "id": r["id"],
            "payment_amount": round(r["payment_amount"] or 0, 2),
            "cumulative_paid": round(cumulative, 2),
            "payment_date": r["payment_date"] or "",
            "payment_method": r["payment_method"] or "",
            "payment_account": r["payment_account"] or "",
            "handler": r["handler"] or "",
            "voucher_no": r["voucher_no"] or "",
            "remark": r["remark"] or "",
            "created_at": r["created_at"] or "",
        })

    payable = pp_row["payable_amount"] or 0
    paid = pp_row["paid_amount"] or 0

    return {
        "payment_id": pp_row["id"],
        "purchase_id": purchase_id,
        "supplier_id": pp_row["supplier_id"],
        "supplier_code": pp_row["supplier_code"] or "",
        "supplier_name": pp_row["supplier_name"] or "",
        "contact_person": pp_row["contact_person"] or "",
        "contact_phone": pp_row["contact_phone"] or "",
        "material_code": pp_row["material_code"] or "",
        "material_name": pp_row["material_name"] or "",
        "material_spec": pp_row["material_spec"] or "",
        "purchase_date": pp_row["purchase_date"] or "",
        "purchase_quantity": pp_row["purchase_quantity"] or 0,
        "unit_price": pp_row["unit_price"] or 0,
        "payable_amount": round(payable, 2),
        "paid_amount": round(paid, 2),
        "payment_status": pp_row["payment_status"] or "未付款",
        "last_pay_date": pp_row["payment_date"] or "",
        "installment_count": len(records),
        "records": record_list,
    }


def get_installment_summary_stats() -> Dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_purchases,
            SUM(payable_amount) as total_payable,
            SUM(paid_amount) as total_paid,
            SUM(CASE WHEN payment_status = '已付款' THEN 1 ELSE 0 END) as paid_count,
            SUM(CASE WHEN payment_status = '部分付款' THEN 1 ELSE 0 END) as partial_count,
            SUM(CASE WHEN payment_status = '未付款' THEN 1 ELSE 0 END) as unpaid_count,
            SUM(CASE WHEN payment_status = '逾期' THEN 1 ELSE 0 END) as overdue_count
        FROM purchase_payments
    """)
    pp_row = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*) as total_records,
            SUM(payment_amount) as total_payment_flow
        FROM payment_records
    """)
    pr_row = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(DISTINCT purchase_id) as purchases_with_installments
        FROM payment_records
    """)
    inst_row = cursor.fetchone()

    conn.close()

    total_payable = pp_row["total_payable"] or 0
    total_paid = pp_row["total_paid"] or 0
    total_unpaid = round(total_payable - total_paid, 2)

    return {
        "total_purchases": pp_row["total_purchases"] or 0,
        "total_payable": round(total_payable, 2),
        "total_paid": round(total_paid, 2),
        "total_unpaid": total_unpaid,
        "paid_count": pp_row["paid_count"] or 0,
        "partial_count": pp_row["partial_count"] or 0,
        "unpaid_count": pp_row["unpaid_count"] or 0,
        "overdue_count": pp_row["overdue_count"] or 0,
        "payment_flow_count": pr_row["total_records"] or 0,
        "payment_flow_total": round(pr_row["total_payment_flow"] or 0, 2),
        "purchases_with_installments": inst_row["purchases_with_installments"] or 0,
        "completion_rate": round((pp_row["paid_count"] or 0) / max(pp_row["total_purchases"] or 1, 1) * 100, 2),
    }


def get_supplier_payment_subtotals(
    start_date: str = "",
    end_date: str = "",
    supplier_id: Optional[int] = None,
) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            pr.supplier_id,
            s.supplier_code,
            s.supplier_name,
            COUNT(pr.id) as record_count,
            SUM(pr.payment_amount) as total_amount,
            COUNT(DISTINCT pr.payment_method) as method_count
        FROM payment_records pr
        LEFT JOIN suppliers s ON pr.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND pr.payment_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND pr.payment_date <= ?"
        params.append(end_date)
    if supplier_id:
        query += " AND pr.supplier_id = ?"
        params.append(supplier_id)
    query += " GROUP BY pr.supplier_id ORDER BY total_amount DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "supplier_id": row["supplier_id"],
            "supplier_code": row["supplier_code"] or "",
            "supplier_name": row["supplier_name"] or "",
            "record_count": row["record_count"] or 0,
            "total_amount": round(row["total_amount"] or 0, 2),
            "method_count": row["method_count"] or 0,
        })
    return result


def get_payment_method_stats(start_date: str = "", end_date: str = "") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            COALESCE(NULLIF(pr.payment_method, ''), '未指定') as payment_method,
            COUNT(pr.id) as record_count,
            SUM(pr.payment_amount) as total_amount
        FROM payment_records pr
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND pr.payment_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND pr.payment_date <= ?"
        params.append(end_date)
    query += " GROUP BY payment_method ORDER BY total_amount DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    total = sum(r["total_amount"] or 0 for r in rows)
    result = []
    for row in rows:
        amount = row["total_amount"] or 0
        ratio = round((amount / total * 100), 2) if total > 0 else 0
        result.append({
            "payment_method": row["payment_method"] or "未指定",
            "record_count": row["record_count"] or 0,
            "total_amount": round(amount, 2),
            "ratio": ratio,
        })
    return result


def get_dashboard_payment_data() -> Dict:
    today = date.today()
    thirty_days_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    recent_payments = get_payment_records(start_date=thirty_days_ago, end_date=today_str)
    recent_total = sum(p["payment_amount"] or 0 for p in recent_payments)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                pp.payable_amount,
                pp.paid_amount,
                sp.purchase_date,
                s.payment_days
            FROM purchase_payments pp
            LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
            LEFT JOIN suppliers s ON pp.supplier_id = s.id
            WHERE pp.payment_status IN ('未付款', '部分付款', '逾期')
        """)
        rows = cursor.fetchall()

        overdue_count = 0
        upcoming_count = 0
        overdue_amount = 0.0
        upcoming_amount = 0.0

        for row in rows:
            payable = row["payable_amount"] or 0
            paid = row["paid_amount"] or 0
            unpaid = payable - paid
            if unpaid <= 0:
                continue

            purchase_date = row["purchase_date"] or ""
            payment_days = row["payment_days"] or 30
            due_date = calculate_due_date(purchase_date, payment_days)

            if not due_date:
                continue

            days_until = calculate_days_until_due(due_date)
            overdue_days = calculate_overdue_days(due_date)

            if overdue_days > 0:
                overdue_count += 1
                overdue_amount += unpaid
            elif days_until <= 30:
                upcoming_count += 1
                upcoming_amount += unpaid
    finally:
        conn.close()

    return {
        "recent_30day_payment_count": len(recent_payments),
        "recent_30day_payment_total": round(recent_total, 2),
        "overdue_count": overdue_count,
        "upcoming_count": upcoming_count,
        "overdue_amount": round(overdue_amount, 2),
        "upcoming_amount": round(upcoming_amount, 2),
    }
