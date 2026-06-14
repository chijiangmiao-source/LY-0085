import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dal.base import get_connection


def validate_material(data: Dict) -> Tuple[bool, str]:
    if not data.get("material_code"):
        return False, "材料编号不能为空"
    if not data.get("material_name"):
        return False, "材料名称不能为空"
    current_stock = data.get("current_stock", 0)
    if current_stock < 0:
        return False, "当前库存必须大于等于 0"
    safety_stock = data.get("safety_stock", 0)
    if safety_stock < 0:
        return False, "安全库存必须大于等于 0"
    return True, ""


def add_material(data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_material(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO materials (material_code, material_name, material_spec, current_stock, safety_stock, applicable_shoe_type, material_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data["material_code"],
                data["material_name"],
                data.get("material_spec", ""),
                data.get("current_stock", 0),
                data.get("safety_stock", 0),
                data.get("applicable_shoe_type", ""),
                data.get("material_status", "正常"),
            ),
        )
        conn.commit()
        return True, "添加成功"
    except sqlite3.IntegrityError:
        return False, "材料编号已存在，不能重复"
    finally:
        conn.close()


def update_material(material_id: int, data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_material(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE materials SET material_code=?, material_name=?, material_spec=?, current_stock=?, safety_stock=?, applicable_shoe_type=?, material_status=? WHERE id=?",
            (
                data["material_code"],
                data["material_name"],
                data.get("material_spec", ""),
                data.get("current_stock", 0),
                data.get("safety_stock", 0),
                data.get("applicable_shoe_type", ""),
                data.get("material_status", "正常"),
                material_id,
            ),
        )
        conn.commit()
        return True, "更新成功"
    except sqlite3.IntegrityError:
        return False, "材料编号已存在，不能重复"
    finally:
        conn.close()


def delete_material(material_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM construction_records WHERE material_id=?", (material_id,))
        if cursor.fetchone()[0] > 0:
            return False, "该材料存在施工记录，无法删除"
        cursor.execute("DELETE FROM materials WHERE id=?", (material_id,))
        conn.commit()
        return True, "删除成功"
    finally:
        conn.close()


def get_materials(keyword: str = "", status: str = "") -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM materials WHERE 1=1"
    params = []
    if keyword:
        query += " AND (material_code LIKE ? OR material_name LIKE ? OR applicable_shoe_type LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if status and status != "全部":
        query += " AND material_status = ?"
        params.append(status)
    query += " ORDER BY material_code"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_material_by_id(material_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materials WHERE id=?", (material_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_material_by_code(code: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materials WHERE material_code=?", (code,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_low_stock_materials() -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM materials
        WHERE current_stock <= safety_stock
        ORDER BY current_stock ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_material_stock(material_id: int, quantity: int, conn: Optional[sqlite3.Connection] = None) -> None:
    should_close = conn is None
    conn = conn or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
            (quantity, material_id),
        )
        if should_close:
            conn.commit()
    finally:
        if should_close:
            conn.close()
