from datetime import datetime, date, timedelta
from typing import Dict, Optional


def calculate_payment_status(payable: float, paid: float, due_date: str = "") -> str:
    if abs(paid - payable) <= 0.01 and paid > 0:
        return "已付款"
    if paid > 0:
        return "部分付款"
    if due_date:
        try:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            if due < date.today():
                return "逾期"
        except Exception:
            pass
    return "未付款"


def calculate_due_date(purchase_date: str, payment_days: int = 30) -> Optional[str]:
    try:
        pd = datetime.strptime(purchase_date, "%Y-%m-%d")
        due_date = (pd + timedelta(days=payment_days)).strftime("%Y-%m-%d")
        return due_date
    except Exception:
        return None


def calculate_days_until_due(due_date: str) -> int:
    try:
        due_dt = datetime.strptime(due_date, "%Y-%m-%d").date()
        return (due_dt - date.today()).days
    except Exception:
        return 999


def calculate_overdue_days(due_date: str) -> int:
    try:
        due_dt = datetime.strptime(due_date, "%Y-%m-%d").date()
        days = (date.today() - due_dt).days
        return max(days, 0)
    except Exception:
        return 0


def calculate_payment_summary(payable: float, paid: float) -> Dict:
    payable = round(payable or 0, 2)
    paid = round(paid or 0, 2)
    unpaid = round(payable - paid, 2)
    progress = round((paid / payable * 100), 2) if payable > 0 else 0
    return {
        "payable_amount": payable,
        "paid_amount": paid,
        "unpaid_amount": unpaid,
        "payment_progress": progress,
    }
