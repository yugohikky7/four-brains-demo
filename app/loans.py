"""借入返済スケジューラ。元金均等・元利均等の両方式に対応。"""
from __future__ import annotations

from datetime import date, timedelta


def _next_month(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def _parse_ym(ym: str) -> date:
    y, m = ym.split("-")
    return date(int(y), int(m), 1)


def schedule_loan(loan: dict, forecast_months: list[str]) -> dict[str, dict]:
    """1本の借入について、forecast_monthsの各月の元金返済・利息を返す。

    Args:
        loan: {
            name, outstanding, annual_rate, remaining_months,
            method: "equal_principal" | "equal_payment",
            start_year_month,
            grace_months: int (元金返済据置期間。この期間は利息のみ),
        }
    """
    result = {ym: {"principal": 0, "interest": 0} for ym in forecast_months}

    outstanding = float(loan.get("outstanding", loan.get("principal", 0)))
    annual_rate = float(loan.get("annual_rate", 0))
    monthly_rate = annual_rate / 12
    remaining = int(loan.get("remaining_months", loan.get("term_months", 0)))
    grace = max(0, int(loan.get("grace_months", 0) or 0))
    method = loan.get("method", "equal_principal")

    if remaining <= 0 or outstanding <= 0:
        return result

    # 元金返済が始まる月数 = max(0, 残月数 - 据置月数)
    # 例: 残月数60、据置12 → 据置後48ヶ月で元金返済
    repayment_months = max(1, remaining - grace)

    # 元利均等の月額（元金返済期間のみで計算）
    if method == "equal_payment" and monthly_rate > 0:
        payment = outstanding * monthly_rate / (
            1 - (1 + monthly_rate) ** (-repayment_months)
        )
    elif method == "equal_payment":
        payment = outstanding / repayment_months
    else:
        payment = None

    if method == "equal_principal":
        principal_per_month = outstanding / repayment_months

    today = date.today().replace(day=1)
    cursor = today
    months_iterated = 0
    bal = outstanding

    while months_iterated < remaining and bal > 0:
        ym = cursor.strftime("%Y-%m")
        interest = bal * monthly_rate

        # 据置期間中は利息のみ、元金返済なし
        if months_iterated < grace:
            principal_pay = 0
        else:
            if method == "equal_payment" and payment is not None:
                principal_pay = payment - interest
                if principal_pay > bal:
                    principal_pay = bal
                if principal_pay < 0:
                    principal_pay = 0
            else:
                principal_pay = min(principal_per_month, bal)

        bal -= principal_pay

        if ym in result:
            result[ym]["principal"] += int(round(principal_pay))
            result[ym]["interest"] += int(round(interest))

        cursor = _next_month(cursor)
        months_iterated += 1

    return result


def aggregate_loans(loans: list[dict], forecast_months: list[str]) -> dict[str, dict]:
    """複数の借入を合算して月次の元金・利息を返す。"""
    totals = {ym: {"principal": 0, "interest": 0} for ym in forecast_months}
    for loan in loans:
        sched = schedule_loan(loan, forecast_months)
        for ym, v in sched.items():
            totals[ym]["principal"] += v["principal"]
            totals[ym]["interest"] += v["interest"]
    return totals
