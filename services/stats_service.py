from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from dal.purchase_dal import (
    get_avg_unit_price,
    get_material_purchase_rank,
    get_monthly_purchase_trend,
)
from dal.material_dal import get_low_stock_materials
from dal.stats_dal import (
    get_material_usage_stats,
    get_daily_usage_trend,
    get_7day_rework_warnings,
    get_unit_order_material_cost,
    get_30day_material_loss_cost,
    get_high_loss_high_cost_materials,
    get_rework_rate_threshold,
    set_rework_rate_threshold,
    get_purchase_payment_with_records,
    get_installment_summary_stats,
    get_supplier_payment_subtotals,
    get_payment_method_stats,
    get_dashboard_payment_data,
)
from services.payment_service import PaymentService


class StatsService:

    @staticmethod
    def get_rework_rate_threshold() -> float:
        return get_rework_rate_threshold()

    @staticmethod
    def set_rework_rate_threshold(value: float) -> Tuple[bool, str]:
        return set_rework_rate_threshold(value)

    @staticmethod
    def get_material_usage_stats(start_date: str = "", end_date: str = "") -> List[Dict]:
        return get_material_usage_stats(start_date, end_date)

    @staticmethod
    def get_daily_usage_trend(days: int = 30) -> List[Dict]:
        return get_daily_usage_trend(days)

    @staticmethod
    def get_7day_rework_warnings() -> List[Dict]:
        return get_7day_rework_warnings()

    @staticmethod
    def get_low_stock_materials() -> List:
        return get_low_stock_materials()

    @staticmethod
    def get_unit_order_material_cost(start_date: str = "", end_date: str = "") -> List[Dict]:
        return get_unit_order_material_cost(start_date, end_date)

    @staticmethod
    def get_30day_material_loss_cost() -> Dict:
        return get_30day_material_loss_cost()

    @staticmethod
    def get_high_loss_high_cost_materials(start_date: str = "", end_date: str = "", top_n: int = 10) -> List[Dict]:
        return get_high_loss_high_cost_materials(start_date, end_date, top_n)

    @staticmethod
    def get_purchase_payment_with_records(purchase_id: int) -> Optional[Dict]:
        return get_purchase_payment_with_records(purchase_id)

    @staticmethod
    def get_installment_summary_stats() -> Dict:
        return get_installment_summary_stats()

    @staticmethod
    def get_supplier_payment_subtotals(
        start_date: str = "",
        end_date: str = "",
        supplier_id: Optional[int] = None,
    ) -> List[Dict]:
        return get_supplier_payment_subtotals(start_date, end_date, supplier_id)

    @staticmethod
    def get_payment_method_stats_summary(start_date: str = "", end_date: str = "") -> List[Dict]:
        return get_payment_method_stats(start_date, end_date)

    @staticmethod
    def get_dashboard_payment_data() -> Dict:
        return get_dashboard_payment_data()

    @staticmethod
    def get_avg_unit_price(material_id: int) -> float:
        return get_avg_unit_price(material_id)

    @staticmethod
    def get_material_purchase_rank(start_date: str = "", end_date: str = "", top_n: int = 20) -> List[Dict]:
        return get_material_purchase_rank(start_date, end_date, top_n)

    @staticmethod
    def get_monthly_purchase_trend(months: int = 12) -> List[Dict]:
        return get_monthly_purchase_trend(months)

    @staticmethod
    def get_monthly_payment_trend(months: int = 12) -> List[Dict]:
        return PaymentService.get_monthly_payment_trend(months)

    @staticmethod
    def get_monthly_payable_vs_paid(months: int = 12) -> List[Dict]:
        return PaymentService.get_monthly_payable_vs_paid(months)

    @staticmethod
    def get_payment_method_stats(start_date: str = "", end_date: str = "") -> Dict:
        records = PaymentService.get_payment_records(
            start_date=start_date, end_date=end_date
        )

        method_map = {}
        total_amount = 0.0
        for r in records:
            method = r["payment_method"] or "未指定"
            amt = r["payment_amount"] or 0
            total_amount += amt
            if method not in method_map:
                method_map[method] = {"count": 0, "amount": 0.0}
            method_map[method]["count"] += 1
            method_map[method]["amount"] += amt

        sorted_methods = sorted(method_map.items(), key=lambda x: x[1]["amount"], reverse=True)
        result = []
        for idx, (method, info) in enumerate(sorted_methods, 1):
            ratio = (info["amount"] / total_amount * 100) if total_amount > 0 else 0
            result.append({
                "rank": idx,
                "method": method,
                "count": info["count"],
                "amount": round(info["amount"], 2),
                "ratio": round(ratio, 1),
            })

        return {
            "total_records": len(records),
            "total_amount": round(total_amount, 2),
            "methods": result,
        }

    @staticmethod
    def get_supplier_payment_rank(start_date: str = "", end_date: str = "", top_n: int = 20) -> Dict:
        records = PaymentService.get_payment_records(
            start_date=start_date, end_date=end_date
        )

        sup_map = {}
        for r in records:
            key = (r["supplier_code"] or "", r["supplier_name"] or "未知供应商")
            amt = r["payment_amount"] or 0
            if key not in sup_map:
                sup_map[key] = {"count": 0, "amount": 0.0}
            sup_map[key]["count"] += 1
            sup_map[key]["amount"] += amt

        sorted_sups = sorted(sup_map.items(), key=lambda x: x[1]["amount"], reverse=True)
        total = 0.0
        result = []
        for idx, ((code, name), info) in enumerate(sorted_sups[:top_n], 1):
            total += info["amount"]
            result.append({
                "rank": idx,
                "code": code,
                "name": name,
                "count": info["count"],
                "amount": round(info["amount"], 2),
            })

        return {
            "total_suppliers": len(sorted_sups),
            "total_amount": round(total, 2),
            "rankings": result,
        }

    @staticmethod
    def get_installment_status_distribution(
        supplier_id: Optional[int] = None,
        status: str = "",
    ) -> Dict:
        data = PaymentService.get_installment_progress(
            supplier_id=supplier_id, status=status
        )

        status_counts = {"已付款": 0, "部分付款": 0, "未付款": 0, "逾期": 0}
        supplier_totals = {}
        total_payable = 0.0
        total_paid = 0.0
        paid_count = 0

        for d in data:
            st = d["payment_status"]
            if st in status_counts:
                status_counts[st] += 1
            else:
                status_counts[st] = 1

            sup_key = d["supplier_name"] or "未知供应商"
            if sup_key not in supplier_totals:
                supplier_totals[sup_key] = 0.0
            supplier_totals[sup_key] += d["paid_amount"] or 0

            total_payable += d["payable_amount"]
            total_paid += d["paid_amount"]
            if d["payment_status"] == "已付款":
                paid_count += 1

        completion_rate = (paid_count / len(data) * 100) if len(data) > 0 else 0

        return {
            "total_count": len(data),
            "total_payable": round(total_payable, 2),
            "total_paid": round(total_paid, 2),
            "total_unpaid": round(total_payable - total_paid, 2),
            "completion_rate": round(completion_rate, 1),
            "status_counts": status_counts,
            "supplier_totals": supplier_totals,
        }

    @staticmethod
    def get_due_payment_summary(days_ahead: int = 30) -> Dict:
        data = PaymentService.get_upcoming_due_payments(days_ahead=days_ahead)

        overdue_count = 0
        overdue_amount = 0.0
        upcoming_count = 0
        upcoming_amount = 0.0

        for d in data:
            if d["is_overdue"]:
                overdue_count += 1
                overdue_amount += d["unpaid_amount"]
            elif d["is_upcoming"]:
                upcoming_count += 1
                upcoming_amount += d["unpaid_amount"]

        return {
            "overdue_count": overdue_count,
            "overdue_amount": round(overdue_amount, 2),
            "upcoming_count": upcoming_count,
            "upcoming_amount": round(upcoming_amount, 2),
            "total_count": overdue_count + upcoming_count,
            "total_amount": round(overdue_amount + upcoming_amount, 2),
            "details": data,
        }
