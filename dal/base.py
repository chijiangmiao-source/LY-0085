import sqlite3
import os
from typing import Optional, List, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shoe_repair.db")


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
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_code TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            contact_person TEXT,
            contact_phone TEXT,
            address TEXT,
            bank_account TEXT,
            tax_number TEXT,
            credit_limit REAL NOT NULL DEFAULT 0,
            payment_days INTEGER NOT NULL DEFAULT 30,
            supplier_status TEXT NOT NULL DEFAULT '正常',
            remark TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL UNIQUE,
            supplier_id INTEGER NOT NULL,
            payable_amount REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            payment_date TEXT,
            payment_status TEXT NOT NULL DEFAULT '未付款',
            remark TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (purchase_id) REFERENCES stock_purchases(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            payment_amount REAL NOT NULL DEFAULT 0,
            payment_date TEXT,
            payment_method TEXT,
            payment_account TEXT,
            handler TEXT,
            voucher_no TEXT,
            remark TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (purchase_id) REFERENCES stock_purchases(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            material_id INTEGER NOT NULL,
            supplier TEXT NOT NULL,
            supplier_id INTEGER,
            purchase_quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            remark TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materials(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
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
