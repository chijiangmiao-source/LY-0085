import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection


def validate_stock_purchase(data: Dict) -> Tuple[bool, str]:
    if not data.get("purchase_date"):
        return False, "采购日期不能为空"
    if not data.get("material_id"):
        return False, "请选择材料"
    if not data.get("supplier"):
        return False, "供应商不能为空"
    if not data.get("supplier_id"):
        return False, "请从供应商档案中选择供应商"
    qty = data.get("purchase_quantity", 0)
    if qty <= 0:
        return False, "采购数量必须大于 0"
    price = data.get("unit_price", 0)
    if price <= 0:
        return False, "单价必须大于 0"
    total = data.get("total_amount", 0)
    if total <= 0:
        return False, "总金额必须大于 0"
    calc_total = round(qty * price, 2)
    if abs(total - calc_total) > 0.01:
        return False, f"总金额不匹配：数量({qty}) × 单价({price}) = {calc_total}，当前输入为 {total}"
    return True, ""


def add_stock_purchase(data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_stock_purchase(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stock_purchases (purchase_date, material_id, supplier, supplier_id, purchase_quantity, unit_price, total_amount, remark, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["purchase_date"],
                data["material_id"],
                data["supplier"],
                data.get("supplier_id"),
                data["purchase_quantity"],
                data["unit_price"],
                data["total_amount"],
                data.get("remark", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        purchase_id = cursor.lastrowid
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
            (data["purchase_quantity"], data["material_id"]),
        )
        conn.commit()
        return True, "采购登记成功，库存已更新"
    except Exception as e:
        return False, f"登记失败: {e}"
    finally:
        conn.close()


def update_stock_purchase(purchase_id: int, data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_stock_purchase(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sp.purchase_quantity, sp.material_id, "
                       "m1.current_stock as old_stock, m1.material_name as old_name, "
                       "m2.current_stock as new_stock, m2.material_name as new_name "
                       "FROM stock_purchases sp "
                       "LEFT JOIN materials m1 ON sp.material_id = m1.id "
                       "LEFT JOIN materials m2 ON ? = m2.id "
                       "WHERE sp.id=?",
                       (data["material_id"], purchase_id))
        row = cursor.fetchone()
        if not row:
            return False, "记录不存在"

        old_qty = row["purchase_quantity"]
        old_material_id = row["material_id"]
        old_stock = row["old_stock"] or 0
        old_name = row["old_name"] or "未知材料"
        new_qty = data["purchase_quantity"]
        new_material_id = data["material_id"]

        if old_material_id != new_material_id:
            if old_stock < old_qty:
                return False, (f"库存不足，无法回退旧材料：材料[{old_name}]当前库存为 {old_stock}，"
                               f"需要回退 {old_qty}，回退后库存将为负数。\n"
                               f"请先调整库存或删除相关施工记录后再试。")
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
                (old_qty, old_material_id),
            )
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                (new_qty, new_material_id),
            )
        else:
            if new_qty < old_qty:
                rollback_qty = old_qty - new_qty
                if old_stock < rollback_qty:
                    return False, (f"库存不足，无法回退：材料[{old_name}]当前库存为 {old_stock}，"
                                   f"需要回退 {rollback_qty}（原 {old_qty} → 新 {new_qty}），回退后库存将为负数。\n"
                                   f"请先调整库存或删除相关施工记录后再试。")
            diff = new_qty - old_qty
            if diff != 0:
                cursor.execute(
                    "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                    (diff, new_material_id),
                )

        cursor.execute(
            "UPDATE stock_purchases SET purchase_date=?, material_id=?, supplier=?, supplier_id=?, purchase_quantity=?, unit_price=?, total_amount=?, remark=? WHERE id=?",
            (
                data["purchase_date"],
                data["material_id"],
                data["supplier"],
                data.get("supplier_id"),
                data["purchase_quantity"],
                data["unit_price"],
                data["total_amount"],
                data.get("remark", ""),
                purchase_id,
            ),
        )

        conn.commit()
        return True, "更新成功，库存已同步"
    except Exception as e:
        return False, f"更新失败: {e}"
    finally:
        conn.close()


def delete_stock_purchase(purchase_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sp.purchase_quantity, sp.material_id, m.current_stock, m.material_name "
                       "FROM stock_purchases sp LEFT JOIN materials m ON sp.material_id = m.id "
                       "WHERE sp.id=?", (purchase_id,))
        row = cursor.fetchone()
        if not row:
            return False, "记录不存在"
        old_qty = row["purchase_quantity"]
        current_stock = row["current_stock"]
        if current_stock < old_qty:
            return False, (f"库存不足，无法回退：材料[{row['material_name']}]当前库存为 {current_stock}，"
                           f"需要回退 {old_qty}，回退后库存将为负数。\n"
                           f"请先调整库存或删除相关施工记录后再试。")
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
            (old_qty, row["material_id"]),
        )
        cursor.execute("DELETE FROM stock_purchases WHERE id=?", (purchase_id,))
        conn.commit()
        return True, "删除成功，库存已回退"
    finally:
        conn.close()


def get_stock_purchases(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    material_id: Optional[int] = None,
) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT sp.*, m.material_code, m.material_name
        FROM stock_purchases sp
        LEFT JOIN materials m ON sp.material_id = m.id
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
        query += " AND (sp.supplier LIKE ? OR m.material_name LIKE ? OR m.material_code LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if material_id:
        query += " AND sp.material_id = ?"
        params.append(material_id)
    query += " ORDER BY sp.purchase_date DESC, sp.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_avg_unit_price(material_id: int) -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(unit_price) as avg_price
        FROM stock_purchases
        WHERE material_id = ?
    """, (material_id,))
    row = cursor.fetchone()
    conn.close()
    return float(row["avg_price"]) if row and row["avg_price"] else 0.0


def get_material_purchase_rank(start_date: str = "", end_date: str = "", top_n: int = 20) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            m.id as material_id,
            m.material_code,
            m.material_name,
            m.material_spec,
            SUM(sp.purchase_quantity) as total_qty,
            SUM(sp.total_amount) as total_amount,
            COUNT(sp.id) as purchase_count,
            AVG(sp.unit_price) as avg_price
        FROM materials m
        LEFT JOIN stock_purchases sp ON m.id = sp.material_id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND sp.purchase_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sp.purchase_date <= ?"
        params.append(end_date)
    query += " GROUP BY m.id HAVING total_amount > 0 ORDER BY total_amount DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "material_id": row["material_id"],
            "material_code": row["material_code"],
            "material_name": row["material_name"],
            "material_spec": row["material_spec"] or "",
            "total_qty": row["total_qty"] or 0,
            "total_amount": round(row["total_amount"] or 0, 2),
            "purchase_count": row["purchase_count"] or 0,
            "avg_price": round(row["avg_price"] or 0, 2),
        })
    return result[:top_n]


def get_monthly_purchase_trend(months: int = 12) -> List[Dict]:
    from datetime import date, timedelta
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            strftime('%Y-%m', purchase_date) as month,
            SUM(total_amount) as total_amount,
            COUNT(*) as purchase_count,
            SUM(purchase_quantity) as total_qty
        FROM stock_purchases
        WHERE purchase_date >= date('now', 'start of month', ?)
        GROUP BY strftime('%Y-%m', purchase_date)
        ORDER BY month ASC
    """, (f"-{months - 1} months",))
    rows = cursor.fetchall()
    conn.close()

    result = []
    data_map = {}
    for row in rows:
        data_map[row["month"]] = {
            "month": row["month"],
            "total_amount": round(row["total_amount"] or 0, 2),
            "purchase_count": row["purchase_count"] or 0,
            "total_qty": row["total_qty"] or 0,
        }

    today = date.today()
    for i in range(months - 1, -1, -1):
        m = today.replace(day=1) - timedelta(days=i * 30)
        month_key = m.strftime("%Y-%m")
        if month_key in data_map:
            result.append(data_map[month_key])
        else:
            result.append({
                "month": month_key,
                "total_amount": 0.0,
                "purchase_count": 0,
                "total_qty": 0,
            })
    return result
