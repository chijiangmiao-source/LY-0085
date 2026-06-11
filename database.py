import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shoe_repair.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_code TEXT UNIQUE NOT NULL,
            material_name TEXT NOT NULL,
            material_spec TEXT,
            current_stock INTEGER NOT NULL DEFAULT 0,
            safety_stock INTEGER NOT NULL DEFAULT 0,
            applicable_shoe_type TEXT,
            material_status TEXT NOT NULL DEFAULT '正常'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS construction_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            construction_date TEXT NOT NULL,
            order_no TEXT NOT NULL,
            material_id INTEGER NOT NULL,
            used_quantity INTEGER NOT NULL,
            rework_count INTEGER NOT NULL DEFAULT 0,
            operator TEXT,
            exception_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materials(id),
            UNIQUE (construction_date, order_no, material_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'rework_rate_threshold'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("rework_rate_threshold", "0.15")
        )

    conn.commit()
    conn.close()


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
