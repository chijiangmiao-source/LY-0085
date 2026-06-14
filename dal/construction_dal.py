import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection
from dal.material_dal import get_material_by_id


def validate_construction_record(data: Dict, material_id: int, record_id: Optional[int] = None) -> Tuple[bool, str]:
    if not data.get("construction_date"):
        return False, "施工日期不能为空"
    if not data.get("order_no"):
        return False, "订单编号不能为空"
    used_qty = data.get("used_quantity", 0)
    if used_qty <= 0:
        return False, "使用数量必须大于 0"
    rework_count = data.get("rework_count", 0)
    if rework_count < 0 or not isinstance(rework_count, int):
        return False, "返工次数必须为 0 或正整数"
    if rework_count >= 2 and not data.get("exception_note"):
        return False, "返工次数 >= 2 时，异常说明不能为空"

    material = get_material_by_id(material_id)
    if not material:
        return False, "材料不存在"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT COUNT(*) FROM construction_records WHERE construction_date=? AND order_no=? AND material_id=?"
        params = [data["construction_date"], data["order_no"], material_id]
        if record_id:
            query += " AND id != ?"
            params.append(record_id)
        cursor.execute(query, params)
        if cursor.fetchone()[0] > 0:
            return False, "同一订单编号在同一天不能重复登记同一种材料"

        current_stock = material["current_stock"]
        if record_id:
            cursor.execute("SELECT used_quantity FROM construction_records WHERE id=?", (record_id,))
            old_row = cursor.fetchone()
            if old_row:
                current_stock += old_row["used_quantity"]
        if used_qty > current_stock:
            return False, f"使用数量不能超过当前库存 ({current_stock})"
    finally:
        conn.close()

    return True, ""


def add_construction_record(data: Dict) -> Tuple[bool, str]:
    material_id = data.get("material_id")
    valid, msg = validate_construction_record(data, material_id)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO construction_records (construction_date, order_no, material_id, used_quantity, rework_count, operator, exception_note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["construction_date"],
                data["order_no"],
                material_id,
                data["used_quantity"],
                data.get("rework_count", 0),
                data.get("operator", ""),
                data.get("exception_note", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
            (data["used_quantity"], material_id),
        )
        conn.commit()
        return True, "添加成功"
    except sqlite3.IntegrityError as e:
        return False, f"登记失败: {e}"
    finally:
        conn.close()


def update_construction_record(record_id: int, data: Dict) -> Tuple[bool, str]:
    material_id = data.get("material_id")
    valid, msg = validate_construction_record(data, material_id, record_id)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT used_quantity, material_id FROM construction_records WHERE id=?", (record_id,))
        old_row = cursor.fetchone()
        if not old_row:
            return False, "记录不存在"

        old_qty = old_row["used_quantity"]
        old_material_id = old_row["material_id"]
        new_qty = data["used_quantity"]
        new_material_id = material_id

        if old_material_id != new_material_id:
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                (old_qty, old_material_id),
            )
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
                (new_qty, new_material_id),
            )
        else:
            diff = new_qty - old_qty
            if diff != 0:
                cursor.execute(
                    "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
                    (diff, new_material_id),
                )

        cursor.execute(
            "UPDATE construction_records SET construction_date=?, order_no=?, material_id=?, used_quantity=?, rework_count=?, operator=?, exception_note=? WHERE id=?",
            (
                data["construction_date"],
                data["order_no"],
                new_material_id,
                new_qty,
                data.get("rework_count", 0),
                data.get("operator", ""),
                data.get("exception_note", ""),
                record_id,
            ),
        )
        conn.commit()
        return True, "更新成功"
    finally:
        conn.close()


def delete_construction_record(record_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT used_quantity, material_id FROM construction_records WHERE id=?", (record_id,))
        row = cursor.fetchone()
        if not row:
            return False, "记录不存在"
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
            (row["used_quantity"], row["material_id"]),
        )
        cursor.execute("DELETE FROM construction_records WHERE id=?", (record_id,))
        conn.commit()
        return True, "删除成功"
    finally:
        conn.close()


def get_construction_records(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    material_id: Optional[int] = None,
) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT cr.*, m.material_code, m.material_name, m.material_spec
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
    if keyword:
        query += " AND (cr.order_no LIKE ? OR cr.operator LIKE ? OR m.material_name LIKE ? OR m.material_code LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    if material_id:
        query += " AND cr.material_id = ?"
        params.append(material_id)
    query += " ORDER BY cr.construction_date DESC, cr.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows
