import sqlite3
import os
from datetime import datetime, timedelta, date
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


from dal import (
    validate_material as _dal_validate_material,
    add_material as _dal_add_material,
    update_material as _dal_update_material,
    delete_material as _dal_delete_material,
    get_materials as _dal_get_materials,
    get_material_by_id as _dal_get_material_by_id,
    get_material_by_code as _dal_get_material_by_code,
    get_low_stock_materials as _dal_get_low_stock_materials,
    validate_construction_record as _dal_validate_construction_record,
    add_construction_record as _dal_add_construction_record,
    update_construction_record as _dal_update_construction_record,
    delete_construction_record as _dal_delete_construction_record,
    get_construction_records as _dal_get_construction_records,
    validate_supplier as _dal_validate_supplier,
    add_supplier as _dal_add_supplier,
    update_supplier as _dal_update_supplier,
    delete_supplier as _dal_delete_supplier,
    get_suppliers as _dal_get_suppliers,
    get_supplier_by_id as _dal_get_supplier_by_id,
    get_supplier_by_code as _dal_get_supplier_by_code,
    get_supplier_debt_summary as _dal_get_supplier_debt_summary,
    validate_stock_purchase as _dal_validate_stock_purchase,
    add_stock_purchase as _dal_add_stock_purchase,
    update_stock_purchase as _dal_update_stock_purchase,
    delete_stock_purchase as _dal_delete_stock_purchase,
    get_stock_purchases as _dal_get_stock_purchases,
    get_avg_unit_price as _dal_get_avg_unit_price,
    get_material_purchase_rank as _dal_get_material_purchase_rank,
    get_monthly_purchase_trend as _dal_get_monthly_purchase_trend,
    validate_purchase_payment as _dal_validate_purchase_payment,
    validate_payment_record as _dal_validate_payment_record,
    add_purchase_payment as _dal_add_purchase_payment,
    update_purchase_payment as _dal_update_purchase_payment,
    delete_purchase_payment as _dal_delete_purchase_payment,
    get_purchase_payments as _dal_get_purchase_payments,
    get_purchase_payment_by_id as _dal_get_purchase_payment_by_id,
    get_purchase_payment_by_purchase_id as _dal_get_purchase_payment_by_purchase_id,
    get_unpaid_purchases as _dal_get_unpaid_purchases,
    get_payment_records_by_purchase as _dal_get_payment_records_by_purchase,
    add_payment_record as _dal_add_payment_record,
    update_payment_record as _dal_update_payment_record,
    delete_payment_record as _dal_delete_payment_record,
    get_payment_records as _dal_get_payment_records,
    get_payment_record_by_id as _dal_get_payment_record_by_id,
    get_payment_records_with_cumulative as _dal_get_payment_records_with_cumulative,
    batch_update_overdue_status as _dal_batch_update_overdue_status,
    get_payment_summary_stats as _dal_get_payment_summary_stats,
    get_rework_rate_threshold as _dal_get_rework_rate_threshold,
    set_rework_rate_threshold as _dal_set_rework_rate_threshold,
    get_7day_rework_warnings as _dal_get_7day_rework_warnings,
    get_material_usage_stats as _dal_get_material_usage_stats,
    get_daily_usage_trend as _dal_get_daily_usage_trend,
    get_unit_order_material_cost as _dal_get_unit_order_material_cost,
    get_30day_material_loss_cost as _dal_get_30day_material_loss_cost,
    get_high_loss_high_cost_materials as _dal_get_high_loss_high_cost_materials,
    get_purchase_payment_with_records as _dal_get_purchase_payment_with_records,
    get_installment_summary_stats as _dal_get_installment_summary_stats,
    get_supplier_payment_subtotals as _dal_get_supplier_payment_subtotals,
    get_payment_method_stats as _dal_get_payment_method_stats,
    get_dashboard_payment_data as _dal_get_dashboard_payment_data,
)

from services.payment_service import PaymentService
from services.stats_service import StatsService
from utils.payment_utils import calculate_payment_status as _calc_payment_status


def _calc_payment_status(payable: float, paid: float, due_date: str = "") -> str:
    return _calc_payment_status(payable, paid, due_date)


def validate_material(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_material(data)


def add_material(data: Dict) -> Tuple[bool, str]:
    return _dal_add_material(data)


def update_material(material_id: int, data: Dict) -> Tuple[bool, str]:
    return _dal_update_material(material_id, data)


def delete_material(material_id: int) -> Tuple[bool, str]:
    return _dal_delete_material(material_id)


def get_materials(keyword: str = "", status: str = "") -> List[sqlite3.Row]:
    return _dal_get_materials(keyword, status)


def get_material_by_id(material_id: int) -> Optional[sqlite3.Row]:
    return _dal_get_material_by_id(material_id)


def get_material_by_code(code: str) -> Optional[sqlite3.Row]:
    return _dal_get_material_by_code(code)


def validate_construction_record(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_construction_record(data)


def add_construction_record(data: Dict) -> Tuple[bool, str]:
    return _dal_add_construction_record(data)


def update_construction_record(record_id: int, data: Dict) -> Tuple[bool, str]:
    return _dal_update_construction_record(record_id, data)


def delete_construction_record(record_id: int) -> Tuple[bool, str]:
    return _dal_delete_construction_record(record_id)


def get_construction_records(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    material_id: Optional[int] = None,
) -> List[sqlite3.Row]:
    return _dal_get_construction_records(start_date, end_date, keyword, material_id)


def get_rework_rate_threshold() -> float:
    return _dal_get_rework_rate_threshold()


def set_rework_rate_threshold(value: float) -> Tuple[bool, str]:
    return _dal_set_rework_rate_threshold(value)


def get_7day_rework_warnings() -> List[Dict]:
    return _dal_get_7day_rework_warnings()


def get_material_usage_stats(start_date: str = "", end_date: str = "") -> List[Dict]:
    return _dal_get_material_usage_stats(start_date, end_date)


def get_daily_usage_trend(days: int = 30) -> List[Dict]:
    return _dal_get_daily_usage_trend(days)


def get_low_stock_materials() -> List[sqlite3.Row]:
    return _dal_get_low_stock_materials()


def validate_stock_purchase(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_stock_purchase(data)


def add_stock_purchase(data: Dict) -> Tuple[bool, str]:
    return _dal_add_stock_purchase(data)


def update_stock_purchase(purchase_id: int, data: Dict) -> Tuple[bool, str]:
    return _dal_update_stock_purchase(purchase_id, data)


def delete_stock_purchase(purchase_id: int) -> Tuple[bool, str]:
    return _dal_delete_stock_purchase(purchase_id)


def get_stock_purchases(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    material_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
) -> List[sqlite3.Row]:
    return _dal_get_stock_purchases(start_date, end_date, keyword, material_id, supplier_id)


def get_avg_unit_price(material_id: int) -> float:
    return _dal_get_avg_unit_price(material_id)


def get_unit_order_material_cost(start_date: str = "", end_date: str = "") -> List[Dict]:
    return _dal_get_unit_order_material_cost(start_date, end_date)


def get_30day_material_loss_cost() -> Dict:
    return _dal_get_30day_material_loss_cost()


def get_high_loss_high_cost_materials(start_date: str = "", end_date: str = "", top_n: int = 10) -> List[Dict]:
    return _dal_get_high_loss_high_cost_materials(start_date, end_date, top_n)


def validate_supplier(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_supplier(data)


def add_supplier(data: Dict) -> Tuple[bool, str]:
    return _dal_add_supplier(data)


def update_supplier(supplier_id: int, data: Dict) -> Tuple[bool, str]:
    return _dal_update_supplier(supplier_id, data)


def delete_supplier(supplier_id: int) -> Tuple[bool, str]:
    return _dal_delete_supplier(supplier_id)


def get_suppliers(keyword: str = "", status: str = "") -> List[sqlite3.Row]:
    return _dal_get_suppliers(keyword, status)


def get_supplier_by_id(supplier_id: int) -> Optional[sqlite3.Row]:
    return _dal_get_supplier_by_id(supplier_id)


def get_supplier_by_code(code: str) -> Optional[sqlite3.Row]:
    return _dal_get_supplier_by_code(code)


def validate_purchase_payment(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_purchase_payment(data)


def add_purchase_payment(data: Dict) -> Tuple[bool, str]:
    return _dal_add_purchase_payment(data)


def update_purchase_payment(payment_id: int, data: Dict) -> Tuple[bool, str]:
    return _dal_update_purchase_payment(payment_id, data)


def delete_purchase_payment(payment_id: int) -> Tuple[bool, str]:
    return _dal_delete_purchase_payment(payment_id)


def get_purchase_payments(
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    supplier_id: Optional[int] = None,
    status: str = "",
) -> List[sqlite3.Row]:
    return _dal_get_purchase_payments(start_date, end_date, keyword, supplier_id, status)


def get_purchase_payment_by_id(payment_id: int) -> Optional[sqlite3.Row]:
    return _dal_get_purchase_payment_by_id(payment_id)


def get_unpaid_purchases(supplier_id: Optional[int] = None) -> List[sqlite3.Row]:
    return _dal_get_unpaid_purchases(supplier_id)


def get_purchase_payment_by_purchase_id(purchase_id: int) -> Optional[sqlite3.Row]:
    return _dal_get_purchase_payment_by_purchase_id(purchase_id)


def get_payment_records_by_purchase(purchase_id: int) -> List[sqlite3.Row]:
    return _dal_get_payment_records_by_purchase(purchase_id)


def get_supplier_debt_summary(start_date: str = "", end_date: str = "") -> List[Dict]:
    return _dal_get_supplier_debt_summary(start_date, end_date)


def get_material_purchase_rank(start_date: str = "", end_date: str = "", top_n: int = 20) -> List[Dict]:
    return _dal_get_material_purchase_rank(start_date, end_date, top_n)


def get_overdue_payments() -> List[Dict]:
    return PaymentService.get_overdue_payments()


def get_monthly_purchase_trend(months: int = 12) -> List[Dict]:
    return _dal_get_monthly_purchase_trend(months)


def validate_payment_record(data: Dict) -> Tuple[bool, str]:
    return _dal_validate_payment_record(data)


def _update_purchase_payment_summary(purchase_id: int, conn: sqlite3.Connection):
    from dal.payment_dal import update_purchase_payment_summary as _dal_update_purchase_payment_summary
    _dal_update_purchase_payment_summary(purchase_id, conn)


def add_payment_record(data: Dict) -> Tuple[bool, str]:
    return PaymentService.add_payment_record_with_summary(data)


def update_payment_record(record_id: int, data: Dict) -> Tuple[bool, str]:
    return PaymentService.update_payment_record_with_summary(record_id, data)


def delete_payment_record(record_id: int) -> Tuple[bool, str]:
    return PaymentService.delete_payment_record_with_summary(record_id)


def get_payment_records(
    purchase_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    payment_method: str = "",
) -> List[sqlite3.Row]:
    return _dal_get_payment_records(purchase_id, supplier_id, start_date, end_date, keyword, payment_method)


def get_payment_record_by_id(record_id: int) -> Optional[sqlite3.Row]:
    return _dal_get_payment_record_by_id(record_id)


def get_installment_progress(
    supplier_id: Optional[int] = None,
    status: str = "",
) -> List[Dict]:
    return PaymentService.get_installment_progress(supplier_id=supplier_id, status=status)


def get_supplier_payment_flow(
    supplier_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
) -> List[Dict]:
    return PaymentService.get_supplier_payment_flow(supplier_id, start_date, end_date)


def get_monthly_payment_trend(months: int = 12) -> List[Dict]:
    return PaymentService.get_monthly_payment_trend(months)


def get_upcoming_due_payments(days_ahead: int = 30) -> List[Dict]:
    return PaymentService.get_upcoming_due_payments(days_ahead=days_ahead)


def get_payment_summary_stats(start_date: str = "", end_date: str = "") -> Dict:
    return _dal_get_payment_summary_stats(start_date, end_date)


def get_payment_records_with_cumulative(
    supplier_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    payment_method: str = "",
) -> List[Dict]:
    return _dal_get_payment_records_with_cumulative(supplier_id, start_date, end_date, keyword, payment_method)


def batch_update_overdue_status() -> Dict:
    return _dal_batch_update_overdue_status()


def get_monthly_payable_vs_paid(months: int = 12) -> List[Dict]:
    return PaymentService.get_monthly_payable_vs_paid(months)


def get_supplier_payment_subtotals(
    start_date: str = "",
    end_date: str = "",
    supplier_id: Optional[int] = None,
) -> List[Dict]:
    return _dal_get_supplier_payment_subtotals(start_date, end_date, supplier_id)


def get_purchase_payment_with_records(purchase_id: int) -> Optional[Dict]:
    return _dal_get_purchase_payment_with_records(purchase_id)


def get_payment_method_stats(start_date: str = "", end_date: str = "") -> List[Dict]:
    return _dal_get_payment_method_stats(start_date, end_date)


def get_installment_summary_stats() -> Dict:
    return _dal_get_installment_summary_stats()


def get_dashboard_payment_data() -> Dict:
    return _dal_get_dashboard_payment_data()


def update_material_stock(material_id: int, quantity_change: int) -> Tuple[bool, str]:
    from dal.material_dal import update_material_stock as _dal_update_material_stock
    return _dal_update_material_stock(material_id, quantity_change)
