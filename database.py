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
        CREATE TABLE IF NOT EXISTS stock_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            material_id INTEGER NOT NULL,
            supplier TEXT NOT NULL,
            purchase_quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            remark TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materials(id)
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


def validate_stock_purchase(data: Dict) -> Tuple[bool, str]:
    if not data.get("purchase_date"):
        return False, "采购日期不能为空"
    if not data.get("material_id"):
        return False, "请选择材料"
    if not data.get("supplier"):
        return False, "供应商不能为空"
    qty = data.get("purchase_quantity", 0)
    if qty <= 0:
        return False, "采购数量必须大于 0"
    price = data.get("unit_price", 0)
    if price <= 0:
        return False, "单价必须大于 0"
    total = data.get("total_amount", 0)
    if total <= 0:
        return False, "总金额必须大于 0"
    return True, ""


def add_stock_purchase(data: Dict) -> Tuple[bool, str]:
    valid, msg = validate_stock_purchase(data)
    if not valid:
        return False, msg

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stock_purchases (purchase_date, material_id, supplier, purchase_quantity, unit_price, total_amount, remark, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["purchase_date"],
                data["material_id"],
                data["supplier"],
                data["purchase_quantity"],
                data["unit_price"],
                data["total_amount"],
                data.get("remark", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
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
        cursor.execute("SELECT purchase_quantity, material_id FROM stock_purchases WHERE id=?", (purchase_id,))
        old_row = cursor.fetchone()
        if not old_row:
            return False, "记录不存在"

        old_qty = old_row["purchase_quantity"]
        old_material_id = old_row["material_id"]
        new_qty = data["purchase_quantity"]
        new_material_id = data["material_id"]

        if old_material_id != new_material_id:
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
                (old_qty, old_material_id),
            )
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                (new_qty, new_material_id),
            )
        else:
            diff = new_qty - old_qty
            if diff != 0:
                cursor.execute(
                    "UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                    (diff, new_material_id),
                )

        cursor.execute(
            "UPDATE stock_purchases SET purchase_date=?, material_id=?, supplier=?, purchase_quantity=?, unit_price=?, total_amount=?, remark=? WHERE id=?",
            (
                data["purchase_date"],
                data["material_id"],
                data["supplier"],
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
        cursor.execute("SELECT purchase_quantity, material_id FROM stock_purchases WHERE id=?", (purchase_id,))
        row = cursor.fetchone()
        if not row:
            return False, "记录不存在"
        cursor.execute(
            "UPDATE materials SET current_stock = current_stock - ? WHERE id=?",
            (row["purchase_quantity"], row["material_id"]),
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
