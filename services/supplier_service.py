from typing import List, Dict, Optional, Tuple
import sqlite3

from dal.supplier_dal import (
    validate_supplier,
    add_supplier,
    update_supplier,
    delete_supplier,
    get_suppliers,
    get_supplier_by_id,
    get_supplier_by_code,
    get_supplier_debt_summary,
)


class SupplierService:

    @staticmethod
    def add_supplier(data: Dict) -> Tuple[bool, str]:
        return add_supplier(data)

    @staticmethod
    def update_supplier(supplier_id: int, data: Dict) -> Tuple[bool, str]:
        return update_supplier(supplier_id, data)

    @staticmethod
    def delete_supplier(supplier_id: int) -> Tuple[bool, str]:
        return delete_supplier(supplier_id)

    @staticmethod
    def get_suppliers(keyword: str = "", status: str = "") -> List[sqlite3.Row]:
        return get_suppliers(keyword, status)

    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[sqlite3.Row]:
        return get_supplier_by_id(supplier_id)

    @staticmethod
    def get_supplier_by_code(code: str) -> Optional[sqlite3.Row]:
        return get_supplier_by_code(code)

    @staticmethod
    def get_supplier_debt_summary(start_date: str = "", end_date: str = "") -> List[Dict]:
        return get_supplier_debt_summary(start_date, end_date)

    @staticmethod
    def get_active_suppliers() -> List[sqlite3.Row]:
        rows = get_suppliers(status="正常")
        return rows

    @staticmethod
    def get_supplier_map() -> Dict[str, int]:
        rows = get_active_suppliers()
        supplier_map = {}
        for r in rows:
            label = f"{r['supplier_code']} - {r['supplier_name']}"
            supplier_map[label] = r["id"]
        return supplier_map

    @staticmethod
    def validate_supplier_data(data: Dict) -> Tuple[bool, str]:
        return validate_supplier(data)
