"""キャッシュフロー予測エンジン。

過去12ヶ月の実績と各種設定（売掛/買掛サイト、シナリオ倍率、借入、手動調整）から
向こう12ヶ月分の月次キャッシュフロー予測を生成する。
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from .loans import aggregate_loans


def _next_month_str(ym: str) -> str:
    y, m = ym.split("-")
    y, m = int(y), int(m)
    if m == 12:
        return f"{y + 1}-01"
    return f"{y}-{m + 1:02d}"


def _shift_ym(ym: str, months: int) -> str:
    """ym（YYYY-MM）をmonths月だけシフト。"""
    y, m = ym.split("-")
    y, m = int(y), int(m)
    total = y * 12 + (m - 1) + months
    ny = total // 12
    nm = total % 12 + 1
    return f"{ny}-{nm:02d}"


def _forecast_months(count: int = 12) -> list[str]:
    """今月から数えてcount月分のYYYY-MMリスト。"""
    today = date.today().replace(day=1)
    months: list[str] = []
    cursor = today
    for _ in range(count):
        months.append(cursor.strftime("%Y-%m"))
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def _project_baseline(history: list[dict], forecast_months: list[str]) -> list[dict]:
    """過去実績から、向こう12ヶ月の売上・経費・給与の予測ベースラインを作る。

    手法：直近12ヶ月の同月平均（年次性を反映）。
        同月実績が無ければ12ヶ月平均で補う。直近の3ヶ月トレンドを軽く適用。
    """
    by_month = {row["year_month"]: row for row in history}

    # 月別の平均（複数年の同月平均）
    rev_avg = mean(r["revenue"] for r in history) if history else 0
    exp_avg = mean(r["expense"] for r in history) if history else 0
    sal_avg = mean(r["salary"] for r in history) if history else 0

    # 同月（去年の同じ月）を優先
    projection = []
    for fm in forecast_months:
        _, mm = fm.split("-")
        same_month_rows = [r for r in history if r["year_month"].endswith(f"-{mm}")]
        if same_month_rows:
            rev = int(mean(r["revenue"] for r in same_month_rows))
            exp = int(mean(r["expense"] for r in same_month_rows))
            sal = int(mean(r["salary"] for r in same_month_rows))
        else:
            rev = int(rev_avg)
            exp = int(exp_avg)
            sal = int(sal_avg)
        projection.append({
            "year_month": fm,
            "revenue_projected": rev,
            "expense_projected": exp,
            "salary_projected": sal,
        })
    return projection


def _apply_payment_timing(
    projection: list[dict],
    history: list[dict],
    receivable_months: int,
    payable_months: int,
    salary_offset: int,
) -> list[dict]:
    """売上・経費・給与の「発生」を、サイトに応じて「入出金」に変換。

    予測対象月の入金 = (予測対象月 - 売掛サイト月) の売上発生額
    予測対象月の支払 = (予測対象月 - 買掛サイト月) の経費発生額
    予測対象月の給与支払 = (予測対象月 - 給与オフセット) の給与発生額

    過去分は実績から、未来分は予測ベースラインから引く。
    """
    # 発生額を一元化（実績優先、無ければ予測）
    occurrence: dict[str, dict] = {}
    for row in history:
        occurrence[row["year_month"]] = {
            "revenue": row["revenue"],
            "expense": row["expense"],
            "salary": row["salary"],
        }
    for row in projection:
        ym = row["year_month"]
        # 予測月の発生額を入れる（実績にあれば上書きしない）
        if ym not in occurrence:
            occurrence[ym] = {
                "revenue": row["revenue_projected"],
                "expense": row["expense_projected"],
                "salary": row["salary_projected"],
            }
        else:
            # 既に履歴あり（発生済み）— そのまま使う
            pass

    # 発生額のうち、現実的に該当月の発生額が不明な場合は予測値で代用
    # 予測対象月のサイト先源泉月が history にも projection にもない場合は0扱い

    result = []
    for row in projection:
        target_ym = row["year_month"]
        # ソース月（売上発生月 = 予測対象月 - receivable_months）
        rev_source = _shift_ym(target_ym, -receivable_months)
        exp_source = _shift_ym(target_ym, -payable_months)
        sal_source = _shift_ym(target_ym, -salary_offset)

        # 売上ソース月の発生額 → 当月の入金
        rev_in = 0
        if rev_source in occurrence:
            rev_in = occurrence[rev_source]["revenue"]
        elif any(r["year_month"] == rev_source for r in projection):
            for r in projection:
                if r["year_month"] == rev_source:
                    rev_in = r["revenue_projected"]
                    break

        exp_out = 0
        if exp_source in occurrence:
            exp_out = occurrence[exp_source]["expense"]
        elif any(r["year_month"] == exp_source for r in projection):
            for r in projection:
                if r["year_month"] == exp_source:
                    exp_out = r["expense_projected"]
                    break

        sal_out = 0
        if sal_source in occurrence:
            sal_out = occurrence[sal_source]["salary"]
        elif any(r["year_month"] == sal_source for r in projection):
            for r in projection:
                if r["year_month"] == sal_source:
                    sal_out = r["salary_projected"]
                    break

        result.append({
            **row,
            "cash_in_sales": rev_in,
            "cash_out_purchase": exp_out,
            "cash_out_salary": sal_out,
        })
    return result


def _apply_scenario(rows: list[dict], scenario: dict) -> list[dict]:
    """シナリオ倍率を適用。"""
    rev_mult = float(scenario.get("revenue_multiplier", 1.0))
    cost_mult = float(scenario.get("cost_multiplier", 1.0))
    out = []
    for row in rows:
        out.append({
            **row,
            "cash_in_sales": int(row["cash_in_sales"] * rev_mult),
            "cash_out_purchase": int(row["cash_out_purchase"] * cost_mult),
            # 給与は通常シナリオの影響を受けにくいので変えない
        })
    return out


def _apply_loans_and_adjustments(
    rows: list[dict],
    loan_sched: dict[str, dict],
    adjustments: dict[str, list[dict]],
) -> list[dict]:
    """借入返済・手動調整を反映してCFを完成させる。"""
    out = []
    for row in rows:
        ym = row["year_month"]
        loan = loan_sched.get(ym, {"principal": 0, "interest": 0})

        # 手動調整を分類別に集計
        adj_rows = adjustments.get(ym, [])
        adj_operating = sum(
            int(a.get("amount", 0)) for a in adj_rows
            if a.get("type", "operating") == "operating"
        )
        adj_investing = sum(
            int(a.get("amount", 0)) for a in adj_rows
            if a.get("type") == "investing"
        )
        adj_financing = sum(
            int(a.get("amount", 0)) for a in adj_rows
            if a.get("type") == "financing"
        )

        # 営業CF
        operating_cf = (
            row["cash_in_sales"]
            - row["cash_out_purchase"]
            - row["cash_out_salary"]
            - loan["interest"]  # 利息は営業CFに含めるのが一般的
            + adj_operating
        )
        # 投資CF
        investing_cf = adj_investing
        # 財務CF
        financing_cf = -loan["principal"] + adj_financing

        net_cf = operating_cf + investing_cf + financing_cf

        out.append({
            **row,
            "loan_principal": loan["principal"],
            "loan_interest": loan["interest"],
            "adjustment_operating": adj_operating,
            "adjustment_investing": adj_investing,
            "adjustment_financing": adj_financing,
            "operating_cf": operating_cf,
            "investing_cf": investing_cf,
            "financing_cf": financing_cf,
            "net_cf": net_cf,
        })
    return out


def _compute_running_balance(
    rows: list[dict], opening_balance: int
) -> list[dict]:
    """期首残高から積み上げて月末残高を計算。"""
    balance = opening_balance
    out = []
    for row in rows:
        balance += row["net_cf"]
        out.append({**row, "ending_balance": balance})
    return out


def build_forecast(
    history: dict,
    settings: dict,
    loans: list[dict],
    adjustments: dict[str, list[dict]],
    scenario_key: str = "neutral",
) -> dict:
    """エントリーポイント。完成形のCF予測を返す。

    Args:
        history: { opening_cash_balance, monthly: [...] }
        settings: storage.load_settings() の戻り値
        loans:  storage.load_loans()
        adjustments: storage.load_adjustments()
        scenario_key: "optimistic" | "neutral" | "pessimistic"

    Returns:
        {
            "scenario": str,
            "opening_balance": int,
            "forecast_months": [YYYY-MM, ...],
            "rows": [完成行...],
            "totals": {...}
        }
    """
    months = _forecast_months(12)
    baseline = _project_baseline(history["monthly"], months)
    timed = _apply_payment_timing(
        baseline,
        history["monthly"],
        receivable_months=int(settings.get("receivable_months", 1)),
        payable_months=int(settings.get("payable_months", 2)),
        salary_offset=int(settings.get("salary_payment_offset_months", 0)),
    )
    scenario_params = settings["scenarios"].get(
        scenario_key, settings["scenarios"]["neutral"]
    )
    scenarioed = _apply_scenario(timed, scenario_params)
    loan_sched = aggregate_loans(loans, months)
    enriched = _apply_loans_and_adjustments(scenarioed, loan_sched, adjustments)

    opening = settings.get("opening_cash_balance")
    if opening is None:
        opening = history.get("opening_cash_balance", 0)
    opening = int(opening)

    rows = _compute_running_balance(enriched, opening)

    totals = {
        "operating_cf": sum(r["operating_cf"] for r in rows),
        "investing_cf": sum(r["investing_cf"] for r in rows),
        "financing_cf": sum(r["financing_cf"] for r in rows),
        "net_cf": sum(r["net_cf"] for r in rows),
        "ending_balance": rows[-1]["ending_balance"] if rows else opening,
        "min_balance": min((r["ending_balance"] for r in rows), default=opening),
        "min_balance_month": min(
            rows, key=lambda r: r["ending_balance"]
        )["year_month"] if rows else None,
    }

    return {
        "scenario": scenario_key,
        "scenario_params": scenario_params,
        "opening_balance": opening,
        "forecast_months": months,
        "rows": rows,
        "totals": totals,
    }


def build_all_scenarios(
    history: dict,
    settings: dict,
    loans: list[dict],
    adjustments: dict[str, list[dict]],
) -> dict[str, dict]:
    """3シナリオすべてを計算して返す。"""
    return {
        key: build_forecast(history, settings, loans, adjustments, key)
        for key in ("optimistic", "neutral", "pessimistic")
    }
