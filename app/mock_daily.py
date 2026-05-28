"""日次CF予測モジュール (mock_data.py のサイズ制限回避のため切出)。"""
from datetime import date, timedelta
from typing import Any, Dict, List

from . import mock_data as M


def generate_mock_daily_forecast(opening_balance: int = None, days: int = 30) -> List[Dict[str, Any]]:
    """日次CF予測 (統一CFモデル準拠)。"""
    if opening_balance is None:
        opening_balance = M.CASH_BALANCE
    today = date.today()
    ar = M.generate_mock_ar_schedule()
    ap = M.generate_mock_ap_schedule()
    tax = M.generate_mock_tax_calendar()
    bonus = M.generate_mock_bonus_calendar()

    daily: Dict[str, Dict[str, Any]] = {}
    for offset in range(days):
        d = today + timedelta(days=offset)
        ds = d.isoformat()
        daily[ds] = {
            "date": ds,
            "weekday": ["月", "火", "水", "木", "金", "土", "日"][d.weekday()],
            "is_weekend": d.weekday() >= 5,
            "inflow": 0, "outflow": 0,
            "inflow_items": [], "outflow_items": [],
        }

    for inv in ar:
        ds = inv["due_date"]
        if ds in daily and inv["status"] == "scheduled":
            daily[ds]["inflow"] += inv["amount"]
            daily[ds]["inflow_items"].append({"label": inv["customer"], "amount": inv["amount"]})
    for bill in ap:
        ds = bill["due_date"]
        if ds in daily and bill["status"] == "scheduled":
            daily[ds]["outflow"] += bill["amount"]
            daily[ds]["outflow_items"].append({"label": f"{bill['vendor']} ({bill['category']})", "amount": bill["amount"]})
    for t in tax:
        ds = t["due_date"]
        if ds in daily:
            daily[ds]["outflow"] += t["amount"]
            daily[ds]["outflow_items"].append({"label": f"税金: {t['name']}", "amount": t["amount"]})
    for b in bonus:
        ds = b["pay_date"]
        if ds in daily:
            daily[ds]["outflow"] += b["amount"]
            daily[ds]["outflow_items"].append({"label": f"賞与: {b['name']}", "amount": b["amount"]})

    monthly_salary = M.ANNUAL_SALARY_GROSS // 12
    monthly_principal = M.ANNUAL_LOAN_PRINCIPAL_REPAY // 12
    monthly_interest = M.ANNUAL_LOAN_INTEREST // 12
    cursor = today.replace(day=1)
    for _ in range(3):
        last_day = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        ds = last_day.isoformat()
        if ds in daily:
            daily[ds]["outflow"] += monthly_salary
            daily[ds]["outflow_items"].append({
                "label": f"給与支払 ({M.DEMO_EMPLOYEE_COUNT}名分)",
                "amount": monthly_salary,
            })
            daily[ds]["outflow"] += monthly_principal + monthly_interest
            daily[ds]["outflow_items"].append({
                "label": "借入金返済 (元利金)",
                "amount": monthly_principal + monthly_interest,
            })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    rows = sorted(daily.values(), key=lambda x: x["date"])
    balance = opening_balance
    for row in rows:
        row["net"] = row["inflow"] - row["outflow"]
        balance += row["net"]
        row["ending_balance"] = balance
    return rows
