from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import sqlite3

from dal.payment_dal import (
    add_purchase_payment,
    update_purchase_payment,
    delete_purchase_payment,
    get_purchase_payments,
    get_purchase_payment_by_id,
    get_purchase_payment_by_purchase_id,
    get_unpaid_purchases,
    add_payment_record,
    update_payment_record,
    delete_payment_record,
    get_payment_records,
    get_payment_records_by_purchase,
    get_payment_record_by_id,
    get_payment_records_with_cumulative,
    batch_update_overdue_status as dal_batch_update_overdue,
    get_payment_summary_stats,
    update_purchase_payment_summary,
)
from dal.base import get_connection
from utils.payment_utils import (
    calculate_payment_status,
    calculate_due_date,
    calculate_days_until_due,
    calculate_overdue_days,
    calculate_payment_summary,
)


class PaymentService:

    @staticmethod
    def calculate_payment_status(payable: float, paid: float, due_date: str = "") -> str:
        return calculate_payment_status(payable, paid, due_date)

    @staticmethod
    def calculate_due_date(purchase_date: str, payment_days: int = 30) -> Optional[str]:
        return calculate_due_date(purchase_date, payment_days)

    @staticmethod
    def calculate_days_until_due(due_date: str) -> int:
        return calculate_days_until_due(due_date)

    @staticmethod
    def calculate_overdue_days(due_date: str) -> int:
        return calculate_overdue_days(due_date)

    @staticmethod
    def calculate_payment_summary(payable: float, paid: float) -> Dict:
        return calculate_payment_summary(payable, paid)

    @staticmethod
    def _enrich_payment_data(row: sqlite3.Row) -> Dict:
        data = dict(row)
        purchase_date = data.get("purchase_date", "")
        payment_days = data.get("payment_days") or 30
        due_date = calculate_due_date(purchase_date, payment_days)
        payable = data.get("payable_amount") or 0
        paid = data.get("paid_amount") or 0

        summary = calculate_payment_summary(payable, paid)
        data.update(summary)

        if due_date:
            data["due_date"] = due_date
            data["days_until_due"] = calculate_days_until_due(due_date)
            data["overdue_days"] = calculate_overdue_days(due_date)
        else:
            data["due_date"] = ""
            data["days_until_due"] = 999
            data["overdue_days"] = 0

        return data

    @staticmethod
    def add_payment_record_with_summary(data: Dict) -> Tuple[bool, str]:
        conn = get_connection()
        try:
            ok, msg = add_payment_record(data, conn)
            if not ok:
                conn.rollback()
                return False, msg

            update_purchase_payment_summary(data["purchase_id"], conn)
            conn.commit()
            return True, msg
        except Exception as e:
            conn.rollback()
            return False, f"登记失败: {e}"
        finally:
            conn.close()

    @staticmethod
    def update_payment_record_with_summary(record_id: int, data: Dict) -> Tuple[bool, str]:
        conn = get_connection()
        try:
            old_row = get_payment_record_by_id(record_id)
            if not old_row:
                return False, "付款记录不存在"

            ok, msg = update_payment_record(record_id, data, conn)
            if not ok:
                conn.rollback()
                return False, msg

            update_purchase_payment_summary(data["purchase_id"], conn)
            if old_row["purchase_id"] != data["purchase_id"]:
                update_purchase_payment_summary(old_row["purchase_id"], conn)

            conn.commit()
            return True, msg
        except Exception as e:
            conn.rollback()
            return False, f"更新失败: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete_payment_record_with_summary(record_id: int) -> Tuple[bool, str]:
        conn = get_connection()
        try:
            row = get_payment_record_by_id(record_id)
            if not row:
                return False, "记录不存在"
            purchase_id = row["purchase_id"]

            ok, msg = delete_payment_record(record_id, conn)
            if not ok:
                conn.rollback()
                return False, msg

            update_purchase_payment_summary(purchase_id, conn)
            conn.commit()
            return True, msg
        except Exception as e:
            conn.rollback()
            return False, f"删除失败: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_purchase_payments_enriched(
        start_date: str = "",
        end_date: str = "",
        keyword: str = "",
        supplier_id: Optional[int] = None,
        status: str = "",
    ) -> List[Dict]:
        rows = get_purchase_payments(start_date, end_date, keyword, supplier_id, status)
        return [PaymentService._enrich_payment_data(row) for row in rows]

    @staticmethod
    def get_installment_progress(
        supplier_id: Optional[int] = None,
        status: str = "",
    ) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    pp.id as payment_id,
                    pp.purchase_id,
                    pp.supplier_id,
                    pp.payable_amount,
                    pp.paid_amount,
                    pp.payment_status,
                    pp.payment_date as last_pay_date,
                    pp.remark,
                    sp.purchase_date,
                    sp.purchase_quantity,
                    sp.unit_price,
                    sp.total_amount as purchase_total,
                    m.material_code,
                    m.material_name,
                    m.material_spec,
                    s.supplier_code,
                    s.supplier_name,
                    s.payment_days,
                    s.contact_person,
                    s.contact_phone,
                    COUNT(pr.id) as installment_count
                FROM purchase_payments pp
                LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
                LEFT JOIN materials m ON sp.material_id = m.id
                LEFT JOIN suppliers s ON pp.supplier_id = s.id
                LEFT JOIN payment_records pr ON pp.purchase_id = pr.purchase_id
                WHERE 1=1
            """
            params = []
            if supplier_id:
                query += " AND pp.supplier_id = ?"
                params.append(supplier_id)
            if status and status != "全部":
                query += " AND pp.payment_status = ?"
                params.append(status)
            query += " GROUP BY pp.id ORDER BY sp.purchase_date DESC, pp.id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                data = PaymentService._enrich_payment_data(row)
                data["installment_count"] = row["installment_count"] or 0
                data["last_pay_date"] = row["last_pay_date"] or ""
                data["purchase_quantity"] = row["purchase_quantity"] or 0
                data["unit_price"] = row["unit_price"] or 0
                data["payment_id"] = row["payment_id"]
                data["purchase_id"] = row["purchase_id"]
                data["supplier_id"] = row["supplier_id"]
                data["supplier_code"] = row["supplier_code"]
                data["supplier_name"] = row["supplier_name"]
                data["contact_person"] = row["contact_person"] or ""
                data["contact_phone"] = row["contact_phone"] or ""
                data["material_code"] = row["material_code"]
                data["material_name"] = row["material_name"]
                data["material_spec"] = row["material_spec"] or ""
                data["purchase_date"] = row["purchase_date"]
                data["payment_status"] = row["payment_status"]
                data["remark"] = row["remark"] or ""
                result.append(data)
            return result
        finally:
            conn.close()

    @staticmethod
    def get_upcoming_due_payments(days_ahead: int = 30) -> List[Dict]:
        today = date.today()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    pp.id as payment_id,
                    pp.purchase_id,
                    pp.supplier_id,
                    pp.payable_amount,
                    pp.paid_amount,
                    pp.payment_status,
                    pp.remark,
                    sp.purchase_date,
                    sp.total_amount,
                    m.material_code,
                    m.material_name,
                    s.supplier_code,
                    s.supplier_name,
                    s.contact_person,
                    s.contact_phone,
                    s.payment_days
                FROM purchase_payments pp
                LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
                LEFT JOIN materials m ON sp.material_id = m.id
                LEFT JOIN suppliers s ON pp.supplier_id = s.id
                WHERE pp.payment_status IN ('未付款', '部分付款', '逾期')
                ORDER BY sp.purchase_date ASC
            """)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                data = PaymentService._enrich_payment_data(row)

                due_date_str = data.get("due_date", "")
                days_until_due = data.get("days_until_due", 999)
                overdue_days = data.get("overdue_days", 0)
                unpaid = data.get("unpaid_amount", 0)

                is_overdue = due_date_str and today > datetime.strptime(due_date_str, "%Y-%m-%d").date() and unpaid > 0
                is_upcoming = (not is_overdue) and days_until_due <= days_ahead and unpaid > 0

                if is_overdue or is_upcoming:
                    data.update({
                        "payment_id": row["payment_id"],
                        "purchase_id": row["purchase_id"],
                        "supplier_id": row["supplier_id"],
                        "supplier_code": row["supplier_code"],
                        "supplier_name": row["supplier_name"],
                        "contact_person": row["contact_person"] or "",
                        "contact_phone": row["contact_phone"] or "",
                        "material_code": row["material_code"],
                        "material_name": row["material_name"],
                        "purchase_date": row["purchase_date"],
                        "payable_amount": data["payable_amount"],
                        "paid_amount": data["paid_amount"],
                        "unpaid_amount": unpaid,
                        "payment_status": row["payment_status"],
                        "is_overdue": is_overdue,
                        "is_upcoming": is_upcoming,
                        "remark": row["remark"] or "",
                    })
                    result.append(data)

            result_overdue = sorted([r for r in result if r["is_overdue"]], key=lambda x: x["overdue_days"], reverse=True)
            result_upcoming = sorted([r for r in result if r["is_upcoming"]], key=lambda x: x["days_until_due"])
            return result_overdue + result_upcoming
        finally:
            conn.close()

    @staticmethod
    def get_overdue_payments() -> List[Dict]:
        all_due = PaymentService.get_upcoming_due_payments(days_ahead=0)
        return [r for r in all_due if r["is_overdue"]]

    @staticmethod
    def get_supplier_payment_flow(
        supplier_id: Optional[int] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        records = get_payment_records(
            supplier_id=supplier_id,
            start_date=start_date,
            end_date=end_date,
        )
        result = []
        for row in records:
            result.append({
                "record_id": row["id"],
                "purchase_id": row["purchase_id"],
                "supplier_id": row["supplier_id"],
                "supplier_code": row["supplier_code"],
                "supplier_name": row["supplier_name"],
                "material_code": row["material_code"],
                "material_name": row["material_name"],
                "purchase_date": row["purchase_date"],
                "purchase_total": row["total_amount"] or 0,
                "payment_amount": round(row["payment_amount"] or 0, 2),
                "payment_date": row["payment_date"] or "",
                "payment_method": row["payment_method"] or "",
                "payment_account": row["payment_account"] or "",
                "handler": row["handler"] or "",
                "voucher_no": row["voucher_no"] or "",
                "remark": row["remark"] or "",
            })
        return result

    @staticmethod
    def get_monthly_payment_trend(months: int = 12) -> List[Dict]:
        from datetime import date as _date, timedelta
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    strftime('%Y-%m', payment_date) as month,
                    SUM(payment_amount) as total_payment,
                    COUNT(*) as payment_count
                FROM payment_records
                WHERE payment_date >= date('now', 'start of month', ?)
                GROUP BY strftime('%Y-%m', payment_date)
                ORDER BY month ASC
            """, (f"-{months - 1} months",))
            rows = cursor.fetchall()

            result = []
            data_map = {}
            for row in rows:
                data_map[row["month"]] = {
                    "month": row["month"],
                    "total_payment": round(row["total_payment"] or 0, 2),
                    "payment_count": row["payment_count"] or 0,
                }

            today = _date.today()
            for i in range(months - 1, -1, -1):
                m = today.replace(day=1) - timedelta(days=i * 30)
                month_key = m.strftime("%Y-%m")
                if month_key in data_map:
                    result.append(data_map[month_key])
                else:
                    result.append({
                        "month": month_key,
                        "total_payment": 0.0,
                        "payment_count": 0,
                    })
            return result
        finally:
            conn.close()

    @staticmethod
    def get_monthly_payable_vs_paid(months: int = 12) -> List[Dict]:
        from datetime import date as _date, timedelta
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    strftime('%Y-%m', sp.purchase_date) as month,
                    SUM(pp.payable_amount) as payable_amount,
                    SUM(pp.paid_amount) as paid_amount
                FROM purchase_payments pp
                LEFT JOIN stock_purchases sp ON pp.purchase_id = sp.id
                WHERE sp.purchase_date >= date('now', 'start of month', ?)
                GROUP BY strftime('%Y-%m', sp.purchase_date)
                ORDER BY month ASC
            """, (f"-{months - 1} months",))
            rows = cursor.fetchall()

            result = []
            data_map = {}
            for row in rows:
                payable = row["payable_amount"] or 0
                paid = row["paid_amount"] or 0
                data_map[row["month"]] = {
                    "month": row["month"],
                    "payable_amount": round(payable, 2),
                    "paid_amount": round(paid, 2),
                    "unpaid_amount": round(payable - paid, 2),
                }

            today = _date.today()
            for i in range(months - 1, -1, -1):
                m = today.replace(day=1) - timedelta(days=i * 30)
                month_key = m.strftime("%Y-%m")
                if month_key in data_map:
                    result.append(data_map[month_key])
                else:
                    result.append({
                        "month": month_key,
                        "payable_amount": 0.0,
                        "paid_amount": 0.0,
                        "unpaid_amount": 0.0,
                    })
            return result
        finally:
            conn.close()

    @staticmethod
    def batch_update_overdue_status() -> Dict:
        return dal_batch_update_overdue()

    @staticmethod
    def get_payment_summary(start_date: str = "", end_date: str = "") -> Dict:
        return get_payment_summary_stats(start_date, end_date)

    @staticmethod
    def get_payment_records_with_cumulative(
        supplier_id: Optional[int] = None,
        start_date: str = "",
        end_date: str = "",
        keyword: str = "",
        payment_method: str = "",
    ) -> List[Dict]:
        return get_payment_records_with_cumulative(
            supplier_id, start_date, end_date, keyword, payment_method
        )

    @staticmethod
    def add_purchase_payment(data: Dict) -> Tuple[bool, str]:
        return add_purchase_payment(data)

    @staticmethod
    def update_purchase_payment(payment_id: int, data: Dict) -> Tuple[bool, str]:
        return update_purchase_payment(payment_id, data)

    @staticmethod
    def delete_purchase_payment(payment_id: int) -> Tuple[bool, str]:
        return delete_purchase_payment(payment_id)

    @staticmethod
    def get_purchase_payment_by_id(payment_id: int) -> Optional[sqlite3.Row]:
        return get_purchase_payment_by_id(payment_id)

    @staticmethod
    def get_purchase_payment_by_purchase_id(purchase_id: int) -> Optional[sqlite3.Row]:
        return get_purchase_payment_by_purchase_id(purchase_id)

    @staticmethod
    def get_unpaid_purchases(supplier_id: Optional[int] = None) -> List[sqlite3.Row]:
        return get_unpaid_purchases(supplier_id)

    @staticmethod
    def get_payment_records(
        purchase_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        start_date: str = "",
        end_date: str = "",
        keyword: str = "",
        payment_method: str = "",
    ) -> List[sqlite3.Row]:
        return get_payment_records(
            purchase_id, supplier_id, start_date, end_date, keyword, payment_method
        )

    @staticmethod
    def get_payment_records_by_purchase(purchase_id: int) -> List[sqlite3.Row]:
        return get_payment_records_by_purchase(purchase_id)

    @staticmethod
    def get_payment_record_by_id(record_id: int) -> Optional[sqlite3.Row]:
        return get_payment_record_by_id(record_id)
