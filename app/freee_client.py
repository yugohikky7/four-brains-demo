"""freee accounting / HR API client (sync version, read-only)."""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .auth import get_valid_access_token
from .config import get_settings


class FreeeAPIError(Exception):
    pass


def _get(path: str, params: Optional[dict] = None, hr: bool = False,
         api_version: Optional[str] = "2020-06-15",
         base_url_override: Optional[str] = None) -> dict:
    token = get_valid_access_token()
    if not token:
        raise FreeeAPIError("Not connected. Please connect to freee first.")

    s = get_settings()
    if base_url_override:
        base = base_url_override
    else:
        base = s.freee_hr_base if hr else s.freee_accounting_base
    url = f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if api_version:
        headers["X-Api-Version"] = api_version

    with httpx.Client(timeout=60) as client:
        resp = client.get(url, params=params, headers=headers)

    if resp.status_code == 401:
        raise FreeeAPIError("Auth error (invalid token). Please reconnect to freee.")
    if resp.status_code >= 400:
        raise FreeeAPIError(f"API error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


# ============================================================
# 会計: 事業所・口座・取引
# ============================================================

def get_companies() -> List[dict]:
    data = _get("/api/1/companies")
    return data.get("companies", [])


def get_default_company_id() -> Optional[int]:
    companies = get_companies()
    return companies[0]["id"] if companies else None


def get_company_detail(company_id: int) -> dict:
    """事業所詳細（決算月など）"""
    data = _get(f"/api/1/companies/{company_id}", params={"details": "true"})
    return data.get("company", data)


def get_walletables(company_id: int) -> List[dict]:
    data = _get(
        "/api/1/walletables",
        params={"company_id": company_id, "with_balance": "true"},
    )
    return data.get("walletables", [])


def get_trial_pl(company_id: int, fiscal_year: int = None,
                 start_month: int = None, end_month: int = None) -> dict:
    """損益計算書 (試算表) を取得"""
    params: Dict[str, Any] = {"company_id": company_id}
    if fiscal_year is not None:
        params["fiscal_year"] = fiscal_year
    if start_month is not None:
        params["start_month"] = start_month
    if end_month is not None:
        params["end_month"] = end_month
    data = _get("/api/1/reports/trial_pl", params=params)
    return data.get("trial_pl", data)


def get_trial_pl_monthly(company_id: int, months: int = 12) -> list:
    """直近 months ヶ月分の月次P/Lを取得 (3月決算想定)。
    各月個別に /reports/trial_pl?start_month=N&end_month=N を叩く。
    戻り値: [{"year_month": "2025-06", "balances": [...]}, ...] (古→新)
    """
    from datetime import date as _date
    today = _date.today()
    ym_list = []
    cy, cm = today.year, today.month
    for _ in range(months):
        ym_list.append((cy, cm))
        cm -= 1
        if cm < 1:
            cm = 12; cy -= 1
    ym_list.reverse()

    result = []
    for y, m in ym_list:
        # 3月決算: 4月以降は当年度、1〜3月は前年度
        fy = y if m >= 4 else y - 1
        try:
            d = get_trial_pl(company_id, fiscal_year=fy, start_month=m, end_month=m)
            balances = d.get("balances") or []
        except FreeeAPIError:
            balances = []
        result.append({"year_month": f"{y}-{m:02d}", "balances": balances})
    return result


def get_trial_bs(company_id: int, fiscal_year: int = None,
                 start_month: int = None, end_month: int = None) -> dict:
    """貸借対照表 (試算表) を取得"""
    params: Dict[str, Any] = {"company_id": company_id}
    if fiscal_year is not None:
        params["fiscal_year"] = fiscal_year
    if start_month is not None:
        params["start_month"] = start_month
    if end_month is not None:
        params["end_month"] = end_month
    data = _get("/api/1/reports/trial_bs", params=params)
    return data.get("trial_bs", data)


def get_account_items(company_id: int) -> List[dict]:
    """勘定科目マスタ取得"""
    data = _get("/api/1/account_items", params={"company_id": company_id})
    return data.get("account_items", [])


def get_partners(company_id: int) -> List[dict]:
    """全取引先取得（id→名称マップ用）"""
    all_p: List[dict] = []
    offset = 0
    limit = 100
    while True:
        try:
            data = _get(
                "/api/1/partners",
                params={"company_id": company_id, "offset": offset, "limit": limit},
            )
        except FreeeAPIError:
            break
        partners = data.get("partners", [])
        all_p.extend(partners)
        if len(partners) < limit:
            break
        offset += limit
        if offset > 3000:
            break
    return all_p


def get_deals(
    company_id: int,
    start: date,
    end: date,
    deal_type: Optional[str] = None,
) -> List[dict]:
    """取引一覧 (発行日ベース)"""
    all_deals: List[dict] = []
    offset = 0
    limit = 100
    while True:
        params: Dict[str, Any] = {
            "company_id": company_id,
            "start_issue_date": start.isoformat(),
            "end_issue_date": end.isoformat(),
            "offset": offset,
            "limit": limit,
            "accruals": "with",
        }
        if deal_type:
            params["type"] = deal_type
        data = _get("/api/1/deals", params=params)
        deals = data.get("deals", [])
        all_deals.extend(deals)
        if len(deals) < limit:
            break
        offset += limit
        if offset > 5000:
            break
    return all_deals


def get_deals_by_due(
    company_id: int,
    start: date,
    end: date,
    deal_type: Optional[str] = None,
) -> List[dict]:
    """取引一覧 (期日ベース)"""
    all_deals: List[dict] = []
    offset = 0
    limit = 100
    while True:
        params: Dict[str, Any] = {
            "company_id": company_id,
            "start_due_date": start.isoformat(),
            "end_due_date": end.isoformat(),
            "offset": offset,
            "limit": limit,
            "accruals": "with",
        }
        if deal_type:
            params["type"] = deal_type
        try:
            data = _get("/api/1/deals", params=params)
        except FreeeAPIError:
            break
        deals = data.get("deals", [])
        all_deals.extend(deals)
        if len(deals) < limit:
            break
        offset += limit
        if offset > 5000:
            break
    return all_deals


# ============================================================
# 入金・支払予測 (過去パターンから予測)
# ============================================================

def _mode(values):
    """最頻値。同率なら最初の出現順を保持。"""
    if not values:
        return None
    from collections import Counter
    c = Counter(values)
    return c.most_common(1)[0][0]


def _median(values):
    if not values:
        return 0
    sorted_v = sorted(values)
    n = len(sorted_v)
    if n % 2:
        return sorted_v[n // 2]
    return (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2


def _is_month_end(d: date) -> bool:
    """その日付が月末か判定"""
    next_d = d + timedelta(days=1)
    return next_d.month != d.month


def _analyze_partner_pattern(deals_by_partner: dict, months_ahead: int = 12) -> List[dict]:
    """取引先別に発生パターンを分析し、将来N月分を予測 (mode/median使用)"""
    today = date.today()
    results = []
    for partner_name, deals in deals_by_partner.items():
        if not deals:
            continue
        deals_sorted = sorted(deals, key=lambda d: d.get("issue_date", ""))
        dates = []
        amounts = []
        terms = []
        for d in deals_sorted:
            try:
                idate = date.fromisoformat(d["issue_date"])
                ddate = date.fromisoformat(d.get("due_date") or d["issue_date"])
                dates.append(idate)
                amounts.append(int(d.get("amount", 0) or 0))
                terms.append((ddate - idate).days)
            except Exception:
                continue
        if not dates:
            continue

        # 金額は中央値（外れ値に強い）
        avg_amount = int(_median(amounts))
        # サイト日数も中央値
        avg_term_days = int(_median(terms)) if terms else 30

        first = dates[0]
        last = dates[-1]
        span_days = (last - first).days
        if len(dates) == 1:
            frequency_months = 12
        elif span_days <= 0:
            frequency_months = 1
        else:
            avg_gap_days = span_days / (len(dates) - 1)
            frequency_months = max(1, round(avg_gap_days / 30))
            if frequency_months > 12:
                frequency_months = 12

        # 締め日: 末日比率が50%以上なら 末日(31)、それ以外は最頻日
        month_end_ratio = sum(1 for d in dates if _is_month_end(d)) / len(dates)
        if month_end_ratio >= 0.5:
            close_day = 31  # 末日
        else:
            # 最頻日を使う
            mode_day = _mode([d.day for d in dates])
            close_day = mode_day if mode_day else int(_median([d.day for d in dates]))

        pay_day_offset = avg_term_days

        # 過去明細（詳細表示用）
        past_items = []
        for i, d in enumerate(dates):
            past_items.append({
                "issue_date": d.isoformat(),
                "due_date": (d + timedelta(days=terms[i] if i < len(terms) else avg_term_days)).isoformat(),
                "amount": amounts[i] if i < len(amounts) else 0,
            })

        # 次の発生予測 (last + frequency_months months)
        next_issue = last
        future = []
        end_date = today + timedelta(days=30 * months_ahead)
        for _ in range(20):  # safety cap
            # 次の発行日
            y = next_issue.year
            m = next_issue.month + frequency_months
            while m > 12:
                m -= 12
                y += 1
            try:
                if close_day >= 31:
                    # 末日: 翌月1日 - 1日
                    ny2 = y; nm2 = m + 1
                    if nm2 > 12: nm2 = 1; ny2 += 1
                    next_issue = date(ny2, nm2, 1) - timedelta(days=1)
                else:
                    next_issue = date(y, m, min(close_day, 28))
            except ValueError:
                next_issue = date(y, m, 28)
            if next_issue > end_date:
                break
            if next_issue <= today:
                continue
            next_due = next_issue + timedelta(days=pay_day_offset)
            future.append({
                "issue_date": next_issue.isoformat(),
                "due_date": next_due.isoformat(),
                "amount": avg_amount,
            })

        results.append({
            "partner": partner_name,
            "past_count": len(dates),
            "past_total": sum(amounts),
            "avg_amount": avg_amount,
            "frequency_months": frequency_months,
            "close_day": close_day,
            "payment_term_days": avg_term_days,
            "tax_rate": 10,  # 消費税率(%) デフォルト10%
            "last_issue_date": last.isoformat(),
            "last_due_date": (last + timedelta(days=avg_term_days)).isoformat(),
            "past_items": past_items,
            "future": future,
            "future_count": len(future),
            "future_total": sum(f["amount"] for f in future),
        })
    return sorted(results, key=lambda x: x["future_total"], reverse=True)


def _apply_overrides(patterns: list, overrides: dict, deal_type: str,
                     months_ahead: int = 12) -> list:
    """ユーザー編集内容(頻度・締め日・サイト・金額・月別カスタム・削除)を適用"""
    today = date.today()
    overrides_map = overrides.get(deal_type, {}) if overrides else {}
    result = []
    for p in patterns:
        ov = overrides_map.get(p["partner"], {})
        if ov.get("deleted"):
            continue
        # 基本パラメータ上書き
        if "frequency_months" in ov:
            p["frequency_months"] = int(ov["frequency_months"])
        if "close_day" in ov:
            p["close_day"] = int(ov["close_day"])
        if "payment_term_days" in ov:
            p["payment_term_days"] = int(ov["payment_term_days"])
        # 構造化サイト（月オフセット + 支払日）— 末日計算を正確に
        if "payment_offset_months" in ov:
            try:
                p["payment_offset_months"] = int(ov["payment_offset_months"])
            except (TypeError, ValueError):
                pass
        if "payment_day" in ov:
            try:
                p["payment_day"] = int(ov["payment_day"])
            except (TypeError, ValueError):
                pass
        if "avg_amount" in ov:
            p["avg_amount"] = int(ov["avg_amount"])
        if "tax_rate" in ov:
            try:
                p["tax_rate"] = float(ov["tax_rate"])
            except (TypeError, ValueError):
                pass
        if "tax_rate" not in p:
            p["tax_rate"] = 10
        # 月別カスタム
        monthly_overrides = ov.get("monthly_overrides") or {}
        # ★ 過去月は freee の実績で自動上書き（手動値があっても、実績があれば実績優先）
        # past_items から月別に集計
        past_by_month: dict[str, int] = {}
        for it in p.get("past_items") or []:
            try:
                ym = it.get("issue_date", "")[:7]
                if ym:
                    past_by_month[ym] = past_by_month.get(ym, 0) + int(it.get("amount", 0) or 0)
            except Exception:
                continue
        # past_by_month は実績ベース。それぞれの ym について、その月末が今日より前なら override を実績で更新
        today_ym = today.strftime("%Y-%m")
        new_monthly: dict[str, int] = dict(monthly_overrides)  # コピー
        auto_updated_months: list[str] = []
        # 既存 override の過去月を実績で上書き
        for ym in list(new_monthly.keys()):
            if ym < today_ym:
                actual = past_by_month.get(ym, 0)
                if actual > 0 and actual != int(new_monthly[ym]):
                    new_monthly[ym] = actual
                    auto_updated_months.append(ym)
        # 過去月で override が無くても実績があれば追加（記録用）
        for ym, actual in past_by_month.items():
            if ym < today_ym and ym not in new_monthly and actual > 0:
                new_monthly[ym] = actual
        monthly_overrides = new_monthly
        is_custom = bool(monthly_overrides)
        if is_custom:
            p["is_custom"] = True
        if auto_updated_months:
            p["auto_updated_months"] = sorted(auto_updated_months)
        # 保存用 overrides を更新（過去月の自動更新を永続化）
        if monthly_overrides != (ov.get("monthly_overrides") or {}):
            if "_persisted_changes" not in p:
                p["_persisted_changes"] = {}
            p["_persisted_changes"]["monthly_overrides"] = monthly_overrides
        # 将来予測を再生成（編集後の頻度・締め日・サイト・金額で）
        last = date.fromisoformat(p["last_issue_date"])
        future = []
        end_date = today + timedelta(days=30 * months_ahead)
        # 締め日: 31以上は「末日」扱い
        close_day_raw = p["close_day"]
        use_structured = "payment_offset_months" in p and "payment_day" in p
        next_issue = last
        for _ in range(months_ahead + 3):
            ny = next_issue.year
            nm = next_issue.month + max(1, p["frequency_months"])
            while nm > 12:
                nm -= 12
                ny += 1
            try:
                if close_day_raw >= 31:
                    # 末日
                    nm2 = nm + 1; ny2 = ny
                    if nm2 > 12:
                        nm2 = 1; ny2 += 1
                    next_issue = date(ny2, nm2, 1) - timedelta(days=1)
                else:
                    next_issue = date(ny, nm, min(close_day_raw, 28))
            except ValueError:
                next_issue = date(ny, nm, 28)
            if next_issue > end_date:
                break
            if next_issue <= today:
                continue
            # 支払予定日: 構造化フィールドがあればそれを使う（末日計算を正確に）
            if use_structured:
                offset = int(p["payment_offset_months"])
                pay_day = int(p["payment_day"])
                due_y = next_issue.year
                due_m = next_issue.month + offset
                while due_m > 12:
                    due_m -= 12; due_y += 1
                if pay_day >= 31:
                    # 末日: その月の最終日
                    nm3 = due_m + 1; ny3 = due_y
                    if nm3 > 12:
                        nm3 = 1; ny3 += 1
                    next_due = date(ny3, nm3, 1) - timedelta(days=1)
                else:
                    try:
                        next_due = date(due_y, due_m, pay_day)
                    except ValueError:
                        next_due = date(due_y, due_m, 28)
            else:
                next_due = next_issue + timedelta(days=p["payment_term_days"])
            ym_key = next_issue.strftime("%Y-%m")
            amount = monthly_overrides.get(ym_key, p["avg_amount"])
            future.append({
                "issue_date": next_issue.isoformat(),
                "due_date": next_due.isoformat(),
                "amount": int(amount),
                "is_override": ym_key in monthly_overrides,
            })
        p["future"] = future
        p["future_count"] = len(future)
        p["future_total"] = sum(f["amount"] for f in future)
        result.append(p)
    return result


def fetch_payment_forecast(company_id: int, deal_type: str = "income",
                            months_ahead: int = 12,
                            overrides: dict = None) -> dict:
    """取引先別の入出金予測を生成 (overridesで編集内容を適用)"""
    today = date.today()
    start = today - timedelta(days=365)
    try:
        partners = get_partners(company_id)
        partner_map = {p["id"]: p.get("name", "") for p in partners}
    except FreeeAPIError:
        partner_map = {}

    deals = get_deals(company_id, start, today, deal_type=deal_type)
    by_partner = {}
    for d in deals:
        pid = d.get("partner_id")
        name = d.get("partner_name") or partner_map.get(pid, "（取引先不明）")
        by_partner.setdefault(name, []).append(d)

    patterns = _analyze_partner_pattern(by_partner, months_ahead=months_ahead)
    if overrides:
        patterns = _apply_overrides(patterns, overrides, deal_type, months_ahead)

    # 追加項目（手動登録：給与など）
    extra_items = (overrides or {}).get("extra_items", []) if overrides else []
    # ★ extras も ov[deal_type][name] からの上書きを受ける
    overrides_map_for_extras = overrides.get(deal_type, {}) if overrides else {}
    for item in extra_items:
        if item.get("type") != deal_type:
            continue
        # ★ extras 用上書き取得 (partner_name = item.name)
        item_name = item.get("name", "(無名)")
        row_ov = overrides_map_for_extras.get(item_name, {}) if isinstance(overrides_map_for_extras, dict) else {}
        # extras 自体の値 + row_ov で上書き
        def _pick(key, default=None):
            if key in row_ov and row_ov[key] not in (None, ""):
                return row_ov[key]
            if key in item and item[key] not in (None, ""):
                return item[key]
            return default
        avg_amount = int(_pick("avg_amount", 0) or 0)
        freq = int(_pick("frequency_months", 1) or 1)
        close_day = int(_pick("close_day", 25) or 25)
        term_days = int(_pick("payment_term_days", 0) or 0)
        offset_months = _pick("payment_offset_months", None)
        pay_day = _pick("payment_day", None)
        try:
            offset_months = int(offset_months) if offset_months is not None else None
        except (TypeError, ValueError):
            offset_months = None
        try:
            pay_day = int(pay_day) if pay_day is not None else None
        except (TypeError, ValueError):
            pay_day = None
        use_structured = offset_months is not None and pay_day is not None
        # 月別override
        monthly_overrides = _pick("monthly_overrides", {}) or {}

        last = date.today()
        future = []
        end_date = today + timedelta(days=30 * months_ahead)
        next_issue = last
        for _ in range(months_ahead + 3):
            ny = next_issue.year
            nm = next_issue.month + max(1, freq)
            while nm > 12:
                nm -= 12; ny += 1
            try:
                if close_day >= 31:
                    nm2 = nm + 1; ny2 = ny
                    if nm2 > 12: nm2 = 1; ny2 += 1
                    next_issue = date(ny2, nm2, 1) - timedelta(days=1)
                else:
                    next_issue = date(ny, nm, min(close_day, 28))
            except ValueError:
                next_issue = date(ny, nm, 28)
            if next_issue > end_date:
                break
            if next_issue <= today:
                continue
            if use_structured:
                ofs = int(offset_months); pd = int(pay_day)
                due_y = next_issue.year; due_m = next_issue.month + ofs
                while due_m > 12:
                    due_m -= 12; due_y += 1
                if pd >= 31:
                    nm3 = due_m + 1; ny3 = due_y
                    if nm3 > 12: nm3 = 1; ny3 += 1
                    next_due = date(ny3, nm3, 1) - timedelta(days=1)
                else:
                    try:
                        next_due = date(due_y, due_m, pd)
                    except ValueError:
                        next_due = date(due_y, due_m, 28)
            else:
                next_due = next_issue + timedelta(days=term_days)
            # 月別 override: issue_date の YM をキーとして amount を上書き
            ym_key = next_issue.strftime("%Y-%m")
            amount_use = avg_amount
            is_ov = False
            if monthly_overrides and ym_key in monthly_overrides:
                try:
                    amount_use = int(monthly_overrides[ym_key])
                    is_ov = True
                except (TypeError, ValueError):
                    pass
            future.append({
                "issue_date": next_issue.isoformat(),
                "due_date": next_due.isoformat(),
                "amount": amount_use,
                "is_override": is_ov,
            })
        try:
            tax_rate = float(item.get("tax_rate", 10))
        except (TypeError, ValueError):
            tax_rate = 10
        patterns.append({
            "partner": item.get("name", "(無名)"),
            "is_extra": True,
            "is_custom": bool(monthly_overrides),
            "past_count": 0,
            "past_total": 0,
            "avg_amount": avg_amount,
            "frequency_months": freq,
            "close_day": close_day,
            "payment_term_days": term_days,
            "payment_offset_months": offset_months,
            "payment_day": pay_day,
            "tax_rate": tax_rate,
            "last_issue_date": last.isoformat(),
            "last_due_date": (last + timedelta(days=term_days)).isoformat(),
            "future": future,
            "future_count": len(future),
            "future_total": sum(f["amount"] for f in future),
        })

    return {
        "deal_type": deal_type,
        "based_on_days": 365,
        "months_ahead": months_ahead,
        "patterns": sorted(patterns, key=lambda x: x["future_total"], reverse=True),
    }


# ============================================================
# 会計集計の高レベル関数
# ============================================================

def fetch_monthly_history(company_id: int, months_back: int = 12) -> dict:
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months_back - 1):
        start = (start - timedelta(days=1)).replace(day=1)
    end_prev_month = today.replace(day=1) - timedelta(days=1)

    try:
        walletables = get_walletables(company_id)
        opening = sum(w.get("walletable_balance", 0) or 0 for w in walletables)
    except FreeeAPIError:
        opening = 0

    deals = get_deals(company_id, start, end_prev_month)

    monthly: Dict[str, Dict[str, Any]] = {}
    cursor = start
    while cursor <= end_prev_month:
        ym = cursor.strftime("%Y-%m")
        monthly[ym] = {"year_month": ym, "revenue": 0, "expense": 0, "salary": 0}
        next_m = cursor.replace(day=28) + timedelta(days=4)
        cursor = next_m.replace(day=1)

    for deal in deals:
        issue_date = deal.get("issue_date") or deal.get("date")
        if not issue_date:
            continue
        ym = issue_date[:7]
        if ym not in monthly:
            continue
        amount = deal.get("amount", 0) or 0
        dtype = deal.get("type")
        if dtype == "income":
            monthly[ym]["revenue"] += amount
        elif dtype == "expense":
            monthly[ym]["expense"] += amount

    try:
        hr_companies = hr_get_companies()
        hr_company_id = hr_companies[0]["id"] if hr_companies else None
    except FreeeAPIError:
        hr_company_id = None

    if hr_company_id:
        for ym, row in monthly.items():
            y, m = ym.split("-")
            try:
                row["salary"] = hr_get_payroll_total(hr_company_id, int(y), int(m))
            except FreeeAPIError:
                row["salary"] = 0

    return {
        "company_id": company_id,
        "opening_cash_balance": opening,
        "monthly": [monthly[k] for k in sorted(monthly.keys())],
    }


def fetch_ar_schedule(company_id: int) -> List[dict]:
    """売掛金スケジュール: 取引(type=income, 期日ベース)から構築"""
    today = date.today()
    start = today - timedelta(days=60)
    end = today + timedelta(days=120)
    deals = get_deals_by_due(company_id, start, end, deal_type="income")
    if not deals:
        # フォールバック: 発行日ベース
        deals = get_deals(company_id, start, end, deal_type="income")

    # 取引先名のマップ
    try:
        partners = get_partners(company_id)
        partner_map = {p["id"]: p.get("name", "") for p in partners}
    except FreeeAPIError:
        partner_map = {}

    items = []
    for d in deals:
        issue = d.get("issue_date", "")
        due = d.get("due_date") or d.get("issue_date", "")
        amount = d.get("amount", 0) or 0
        if amount <= 0:
            continue
        partner_id = d.get("partner_id")
        partner_name = d.get("partner_name") or partner_map.get(partner_id, "（取引先不明）")
        # 入金済かどうか
        payments = d.get("payments", []) or []
        paid = sum(p.get("amount", 0) for p in payments)
        status = "paid" if paid >= amount else "scheduled"
        # サイト日数（発行→期日）
        try:
            term = (date.fromisoformat(due) - date.fromisoformat(issue)).days
        except Exception:
            term = 0
        items.append({
            "invoice_no": d.get("ref_number") or f"DEAL-{d.get('id', '')}",
            "customer": partner_name,
            "issue_date": issue,
            "due_date": due,
            "amount": amount,
            "status": status,
            "payment_term_days": max(0, term),
        })
    return sorted(items, key=lambda x: x["due_date"])


def fetch_ap_schedule(company_id: int) -> List[dict]:
    """買掛金スケジュール: 取引(type=expense, 期日ベース)から構築"""
    today = date.today()
    start = today - timedelta(days=30)
    end = today + timedelta(days=120)
    deals = get_deals_by_due(company_id, start, end, deal_type="expense")
    if not deals:
        deals = get_deals(company_id, start, end, deal_type="expense")

    try:
        partners = get_partners(company_id)
        partner_map = {p["id"]: p.get("name", "") for p in partners}
    except FreeeAPIError:
        partner_map = {}

    items = []
    for d in deals:
        issue = d.get("issue_date", "")
        due = d.get("due_date") or d.get("issue_date", "")
        amount = d.get("amount", 0) or 0
        if amount <= 0:
            continue
        partner_id = d.get("partner_id")
        partner_name = d.get("partner_name") or partner_map.get(partner_id, "（取引先不明）")
        payments = d.get("payments", []) or []
        paid = sum(p.get("amount", 0) for p in payments)
        status = "paid" if paid >= amount else "scheduled"
        # カテゴリ（最初の明細の勘定科目）
        details = d.get("details", []) or []
        category = details[0].get("account_item_name", "") if details else "経費"
        items.append({
            "bill_no": d.get("ref_number") or f"DEAL-{d.get('id', '')}",
            "vendor": partner_name,
            "category": category,
            "issue_date": issue,
            "due_date": due,
            "amount": amount,
            "status": status,
        })
    return sorted(items, key=lambda x: x["due_date"])


# ============================================================
# 人事労務: 事業所・従業員・給与
# ============================================================

def hr_get_companies() -> List[dict]:
    """人事労務のcompany一覧。/api/v1/companies は存在しないため /users/me から取得。"""
    data = _get("/api/v1/users/me", hr=True)
    # レスポンスは { id, companies: [{ id, name, role, employee_id, ... }] }
    companies = data.get("companies") or []
    # 形式を会計と揃える: id, display_name, name
    result = []
    for c in companies:
        result.append({
            "id": c.get("id"),
            "name": c.get("name", ""),
            "display_name": c.get("name", ""),
            "role": c.get("role", ""),
            "employee_id": c.get("employee_id"),
            "external_cid": c.get("external_cid", ""),
        })
    return result


def hr_get_default_company_id() -> Optional[int]:
    companies = hr_get_companies()
    return companies[0]["id"] if companies else None


def hr_get_employees_all(company_id: int) -> List[dict]:
    """全従業員一覧（削除済を除く）"""
    data = _get(f"/api/v1/companies/{company_id}/employees", hr=True)
    if isinstance(data, list):
        return data
    return data.get("employees", [])


def hr_get_sections(company_id: int) -> List[dict]:
    """部門マスタ。複数のURLパターンを試す。"""
    candidates = [
        (f"/api/v1/companies/{company_id}/sections", None),
        ("/api/v1/sections", {"company_id": company_id}),
    ]
    for path, params in candidates:
        try:
            d = _get(path, params=params, hr=True)
            if isinstance(d, list):
                return d
            if isinstance(d, dict):
                items = d.get("sections") or d.get("data") or []
                if items:
                    return items
        except FreeeAPIError:
            continue
    return []


def hr_get_positions(company_id: int) -> List[dict]:
    """役職マスタ。/api/v1/positions が確認済み(company_id無し可)。"""
    candidates = [
        ("/api/v1/positions", None),  # 確認済: company_id 不要
        ("/api/v1/positions", {"company_id": company_id}),
        (f"/api/v1/companies/{company_id}/positions", None),
    ]
    for path, params in candidates:
        try:
            d = _get(path, params=params, hr=True)
            if isinstance(d, list):
                return d
            if isinstance(d, dict):
                items = d.get("positions") or d.get("data") or []
                if items:
                    return items
        except FreeeAPIError:
            continue
    return []


def hr_get_employee_position(company_id: int, emp_id: int, year: int, month: int) -> Optional[int]:
    """従業員の役職ID。複数のURLパターンを試して position_id を返す。"""
    candidates = [
        (f"/api/v1/employees/{emp_id}/position", {"company_id": company_id, "year": year, "month": month}),
        (f"/api/v1/employees/{emp_id}/positions", {"company_id": company_id, "year": year, "month": month}),
        (f"/api/v1/employee_positions/{emp_id}", {"company_id": company_id, "year": year, "month": month}),
    ]
    for path, params in candidates:
        try:
            d = _get(path, params=params, hr=True)
        except FreeeAPIError:
            continue
        if isinstance(d, dict):
            # トップレベルまたはコンテナ内
            for key in ("position_id", "employee_position", "position"):
                v = d.get(key)
                if isinstance(v, int):
                    return v
                if isinstance(v, dict):
                    pid = v.get("id") or v.get("position_id")
                    if pid is not None:
                        return pid
    return None


def hr_get_employees(company_id: int, year: int, month: int) -> List[dict]:
    data = _get(
        "/api/v1/employees",
        params={"company_id": company_id, "year": year, "month": month, "limit": 100},
        hr=True,
    )
    if isinstance(data, list):
        return data
    return data.get("employees", [])


def hr_get_employee_detail(company_id: int, emp_id: int, year: int, month: int) -> dict:
    data = _get(
        f"/api/v1/employees/{emp_id}",
        params={"company_id": company_id, "year": year, "month": month},
        hr=True,
    )
    return data.get("employee", data) if isinstance(data, dict) else {}


def hr_get_payroll_statements_month(company_id: int, year: int, month: int) -> List[dict]:
    """月内の全従業員給与明細を一括取得 (確認済みエンドポイント)"""
    try:
        data = _get(
            "/api/v1/salaries/employee_payroll_statements",
            params={"company_id": company_id, "year": year, "month": month, "limit": 100},
            hr=True,
        )
        return data.get("employee_payroll_statements", [])
    except FreeeAPIError:
        return []


def hr_get_payroll_statement_detail(payroll_id: int, company_id: int) -> dict:
    """個別給与明細の詳細を id で取得"""
    try:
        data = _get(
            f"/api/v1/salaries/employee_payroll_statements/{payroll_id}",
            params={"company_id": company_id},
            hr=True,
        )
        return data.get("employee_payroll_statement", data)
    except FreeeAPIError:
        return {}


def hr_get_payroll_statement(company_id: int, emp_id: int, year: int, month: int) -> dict:
    """個人別給与明細 (詳細フェッチ込み)"""
    statements = hr_get_payroll_statements_month(company_id, year, month)
    for st in statements:
        if st.get("employee_id") == emp_id:
            pid = st.get("id")
            if pid:
                detail = hr_get_payroll_statement_detail(pid, company_id)
                if detail:
                    return detail
            return st
    return {}


def _to_int(v) -> int:
    """freeeは金額を '100000.0' のような文字列で返すことあり"""
    if v is None:
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def hr_get_payroll_total(company_id: int, year: int, month: int) -> int:
    """月次の給与総支給額を集計 (詳細フェッチで正確に)"""
    statements = hr_get_payroll_statements_month(company_id, year, month)
    total = 0
    for st in statements:
        # バルクから取れる場合 (gross_payment_amount が正)
        amount = (
            st.get("gross_payment_amount") or
            st.get("total_payment_amount") or
            st.get("payment_amount") or 0
        )
        if not amount:
            # 詳細フェッチ
            pid = st.get("id")
            if pid:
                detail = hr_get_payroll_statement_detail(pid, company_id)
                amount = (
                    detail.get("gross_payment_amount") or
                    detail.get("total_payment_amount") or
                    detail.get("payment_amount") or 0
                )
        total += _to_int(amount)
    return total


def _extract_monthly_pay(detail: dict) -> int:
    """employee detail から月給を抽出 (基本給 + 固定残業代 + 役職手当等)"""
    if not isinstance(detail, dict):
        return 0
    base = 0
    fixed_overtime = 0
    other_allowances = 0

    # 基本給候補
    base_candidates = [
        detail.get("monthly_pay"),
        detail.get("basic_pay_amount"),
        detail.get("monthly_base_pay_amount"),
        detail.get("base_pay_amount"),
        detail.get("salary"),
    ]
    # 固定残業代候補
    overtime_candidates = [
        detail.get("fixed_overtime_pay"),
        detail.get("fixed_overtime_pay_amount"),
        detail.get("fixed_overtime_amount"),
        detail.get("deemed_overtime_pay"),
    ]

    # payment_rule の中
    for rule_key in ("payment_rule", "basic_pay_rule", "salary_rule",
                     "monthly_payment_rule", "pay_rule"):
        rule = detail.get(rule_key)
        if isinstance(rule, dict):
            base_candidates.extend([
                rule.get("monthly_pay"),
                rule.get("basic_pay_amount"),
                rule.get("base_pay_amount"),
                rule.get("amount"),
                rule.get("pay_amount"),
                rule.get("monthly_base_pay_amount"),
            ])
            overtime_candidates.extend([
                rule.get("fixed_overtime_pay"),
                rule.get("fixed_overtime_pay_amount"),
                rule.get("deemed_overtime_pay"),
            ])
            # 手当配列
            allowances = rule.get("allowances") or rule.get("monthly_allowances")
            if isinstance(allowances, list):
                for a in allowances:
                    if isinstance(a, dict):
                        amt = _to_int(a.get("amount") or a.get("monthly_amount"))
                        name = (a.get("name") or "").lower()
                        # 通勤手当は別カウントなので除外
                        if "通勤" in name or "commut" in name:
                            continue
                        other_allowances += amt

    # トップレベル allowances 配列
    for arr_key in ("allowances", "monthly_allowances", "salary_allowances"):
        arr = detail.get(arr_key)
        if isinstance(arr, list):
            for a in arr:
                if isinstance(a, dict):
                    amt = _to_int(a.get("amount") or a.get("monthly_amount"))
                    name = (a.get("name") or "").lower()
                    if "通勤" in name or "commut" in name:
                        continue
                    if "固定残業" in name or "deemed" in name or "fixed_overtime" in name:
                        fixed_overtime += amt
                    else:
                        other_allowances += amt

    for v in base_candidates:
        n = _to_int(v)
        if n > 0:
            base = n
            break
    for v in overtime_candidates:
        n = _to_int(v)
        if n > 0:
            fixed_overtime = max(fixed_overtime, n)
            break

    return base + fixed_overtime + other_allowances


def _extract_commute_allowance(detail: dict) -> int:
    """通勤手当を月額換算で抽出"""
    if not isinstance(detail, dict):
        return 0
    # 直接フィールド (複数の名前を試す)
    for k in ("commuting_allowance", "commute_allowance", "commute_fee",
              "transport_allowance", "commuting_amount", "commute_amount"):
        v = detail.get(k)
        n = _to_int(v)
        if n > 0:
            return n
    # payment_rule や allowances 配列の中で「通勤」を探す
    for rule_key in ("payment_rule", "basic_pay_rule", "salary_rule",
                     "monthly_payment_rule", "pay_rule"):
        rule = detail.get(rule_key)
        if isinstance(rule, dict):
            for arr_key in ("allowances", "monthly_allowances"):
                arr = rule.get(arr_key)
                if isinstance(arr, list):
                    for a in arr:
                        if isinstance(a, dict):
                            name = (a.get("name") or "").lower()
                            if "通勤" in name or "commut" in name or "transport" in name:
                                return _to_int(a.get("amount") or a.get("monthly_amount"))
    # トップレベル allowances 配列で通勤手当を探す
    for arr_key in ("allowances", "monthly_allowances", "salary_allowances"):
        arr = detail.get(arr_key)
        if isinstance(arr, list):
            for a in arr:
                if isinstance(a, dict):
                    name = (a.get("name") or "").lower()
                    if "通勤" in name or "commut" in name or "transport" in name:
                        return _to_int(a.get("amount") or a.get("monthly_amount"))
    # commute_allowances 配列 (期間別の定期券)
    allowances = (
        detail.get("commute_allowances") or
        detail.get("commuting_allowances") or
        detail.get("transportation_allowances") or []
    )
    if isinstance(allowances, list):
        total = 0
        for a in allowances:
            if not isinstance(a, dict):
                continue
            amount = _to_int(
                a.get("single_amount") or a.get("amount") or
                a.get("monthly_amount") or a.get("total_amount") or 0
            )
            period = (a.get("period") or a.get("term") or "").lower()
            # 6ヶ月定期等を月割
            if "six" in period or "半年" in period or "6" in period:
                amount = amount // 6
            elif "three" in period or "四半期" in period or "3" in period:
                amount = amount // 3
            elif "year" in period or "年" in period or "12" in period:
                amount = amount // 12
            total += amount
        return total
    return 0


def hr_fetch_employees() -> List[dict]:
    """従業員リストを画面用形式で取得（詳細情報含む）。
    月給は employee detail から取得（給与明細は月中入社で日割になるため使わない）"""
    import time
    _t_start = time.time()
    _api_calls = {"count": 0}
    print(f"[hr_fetch_employees] START at {time.strftime('%H:%M:%S')}")
    try:
        cid = hr_get_default_company_id()
        if not cid:
            return []
        raw = hr_get_employees_all(cid)
        print(f"[hr_fetch_employees] +{time.time()-_t_start:.1f}s: 全従業員LIST取得 ({len(raw)}名)")
    except FreeeAPIError:
        return []

    # ★ 退職済みは除外 (retire_date が既に過去日付の場合)
    today = date.today()
    raw_filtered = []
    for e in raw:
        rd_str = e.get("retire_date") or ""
        if rd_str:
            try:
                rd = date.fromisoformat(rd_str)
                if rd < today:
                    continue  # 退職済みはスキップ
            except Exception:
                pass
        raw_filtered.append(e)
    raw = raw_filtered
    print(f"[hr_fetch_employees] 退職者除外後: {len(raw)}名")

    # 詳細情報を取得する基準月（先月、給与が確定している可能性が高い）
    last_m_end = today.replace(day=1) - timedelta(days=1)
    y, m = last_m_end.year, last_m_end.month

    # 部門・役職マスタを引いて id→name 辞書を構築
    section_name_by_id: Dict[Any, str] = {}
    position_name_by_id: Dict[Any, str] = {}
    try:
        for s in hr_get_sections(cid):
            sid = s.get("id")
            nm = s.get("name") or s.get("section_name") or ""
            if sid is not None and nm:
                section_name_by_id[sid] = nm
    except Exception:
        pass
    try:
        for p in hr_get_positions(cid):
            pid = p.get("id")
            nm = p.get("name") or p.get("position_name") or ""
            if pid is not None and nm:
                position_name_by_id[pid] = nm
    except Exception:
        pass

    # 各従業員の基準月を決定:
    # - 過去入社/当月入社 → 先月 (y, m)
    # - 未来入社 → entry_date の月 (freeeに既に登録されている前提)
    today_y, today_m = today.year, today.month
    ref_month_for_emp: Dict[Any, tuple] = {}
    for e in raw:
        eid = e.get("id")
        if eid is None:
            continue
        entry_str = e.get("entry_date") or ""
        try:
            ed = date.fromisoformat(entry_str) if entry_str else None
        except Exception:
            ed = None
        if ed and (ed.year, ed.month) > (today_y, today_m):
            # 未来入社 → 入社月を基準
            ref_month_for_emp[eid] = (ed.year, ed.month)
        else:
            ref_month_for_emp[eid] = (y, m)

    # ユニーク基準月で年月別LISTを取得しマージ
    ym_emp_map: Dict[Any, dict] = {}
    unique_months = sorted(set(ref_month_for_emp.values()))
    for (ry, rm) in unique_months:
        try:
            ym_emps = hr_get_employees(cid, ry, rm)
            for em in ym_emps:
                eid2 = em.get("id")
                if eid2 is not None and eid2 not in ym_emp_map:
                    ym_emp_map[eid2] = em
        except FreeeAPIError:
            continue

    # ★★ ユーザー要望: 給与明細を使わない → プリフェッチ不要 ★★
    payroll_by_month: Dict[tuple, List[dict]] = {}
    print(f"[hr_fetch_employees] +{time.time()-_t_start:.1f}s: 給与明細スキップ (従業員情報のみ使用)")

    _fallback_count = 0
    result = []
    for e in raw:
        emp_id = e.get("id")
        # その従業員の基準月（過去入社者は先月、未来入社者は入社月）
        ref_y, ref_m = ref_month_for_emp.get(emp_id, (y, m))
        # 従業員番号 (num が一般的、無ければ emp_code, code)
        emp_num = e.get("num") or e.get("emp_code") or e.get("code") or ""
        # 未来日入社判定
        is_future_entry = False
        entry_str = e.get("entry_date") or ""
        try:
            if entry_str:
                ed_chk = date.fromisoformat(entry_str)
                if ed_chk > today:
                    is_future_entry = True
        except Exception:
            pass
        item = {
            "id": emp_id,
            "employee_number": str(emp_num) if emp_num != "" else "",
            "name": e.get("display_name") or e.get("name") or e.get("real_name", "（氏名不明）"),
            "position": "",
            "department": "",
            "monthly_salary": 0,
            "commute_allowance": 0,
            "annual_salary": 0,
            "hire_date": e.get("entry_date", ""),
            "employment_type": "正社員",
            "remaining_paid_leave": 0,
            "overtime_hours_last_month": 0,
            "is_future_entry": is_future_entry,
        }
        if emp_id:
            # ★ 年月別LIST から profile_rule と basic_pay_rule を直接取得 (個別フェッチ廃止)
            ym_emp = ym_emp_map.get(emp_id, {}) if ym_emp_map else {}
            prof = ym_emp.get("profile_rule") if isinstance(ym_emp.get("profile_rule"), dict) else {}
            # 雇用形態
            emp_type_raw = (
                ym_emp.get("employment_type")
                or prof.get("employment_type")
                or ""
            )
            etype_map = {
                "board-member": "役員",
                "board_member": "役員",
                "regular": "正社員",
                "permanent": "正社員",
                "part-time": "パート",
                "part_time": "パート",
                "contract": "契約社員",
                "outsourcing": "業務委託",
            }
            item["employment_type"] = etype_map.get(emp_type_raw, emp_type_raw or "正社員")
            # 役職・部門
            pos_name = (
                prof.get("title") or
                prof.get("position_name") or
                ym_emp.get("position_name") or ""
            )
            dept_name = (
                prof.get("section_name") or
                ym_emp.get("section_name") or
                ym_emp.get("department_name") or ""
            )
            sec_id = prof.get("section_id") or ym_emp.get("section_id")
            pos_id = prof.get("position_id") or ym_emp.get("position_id")
            if not dept_name and sec_id is not None:
                dept_name = section_name_by_id.get(sec_id, "")
            if not pos_name and pos_id is not None:
                pos_name = position_name_by_id.get(pos_id, "")
            item["position"] = pos_name or ""
            item["department"] = dept_name or ""

            # ★★ ユーザー要望: 月給・通勤費は自動取得を一切しない (混乱を避ける) ★★
            # 全員 0 で初期化。値が必要なら「編集」ボタンで手動入力
            item["monthly_salary"] = 0
            item["annual_salary"] = 0
            item["commute_allowance"] = 0
            item["_payment_names"] = []  # 後方互換
            item["_source_month"] = None
            item["_data_source"] = "手入力のみ (自動取得無し)"

        result.append(item)

    print(f"[hr_fetch_employees] DONE +{time.time()-_t_start:.1f}s: 全{len(result)}名処理完了")
    return result


def hr_fetch_employee_payroll_summary(
    fiscal_year: int,
    payment_offset_months: int = 1,
) -> Dict[int, Dict[str, int]]:
    """期(4月-翌3月)の労働対価の従業員別累計を返す。
    payment_offset_months: 給与の支払サイト (1=翌月末払、0=当月払)
      例: 月末締翌月末払い → payment_offset_months=1
          4月稼働の給与は5月末支払 → freee記録月は「5月」
    なので、4月稼働の給与を取得するには query month = (4 + offset) = 5月で叩く

    戻り値: { employee_id: { gross_salary, social_insurance_employer, commute, board_pay } }
    """
    try:
        cid = hr_get_default_company_id()
        if not cid:
            return {}
    except FreeeAPIError:
        return {}

    today = date.today()
    summary: Dict[int, Dict[str, int]] = {}

    # 4月-翌3月の各「稼働月」について、対応する「支払月」をクエリ
    for offset in range(12):
        # 稼働月
        work_y = fiscal_year + (0 if (4 + offset) <= 12 else 1)
        work_m = ((4 + offset - 1) % 12) + 1
        # 支払月 = 稼働月 + payment_offset_months
        pay_y, pay_m = work_y, work_m + payment_offset_months
        while pay_m > 12:
            pay_m -= 12; pay_y += 1
        # 支払月が「未来」のみスキップ。今月支給分は freee で確定済の為含める
        if (pay_y, pay_m) > (today.year, today.month):
            continue
        try:
            statements = hr_get_payroll_statements_month(cid, pay_y, pay_m)
        except Exception:
            statements = []
        for st in statements:
            eid = st.get("employee_id")
            if not eid:
                continue
            entry = summary.setdefault(eid, {
                "gross_salary": 0, "social_insurance_employer": 0,
                "commute": 0, "board_pay": 0,
            })
            # 総支給額 (通勤手当含む)
            gross = _to_int(st.get("gross_payment_amount") or st.get("total_payment_amount") or 0)
            # ★ 通勤手当を先に算出 (この明細分)
            commute_this = 0
            for pmt in (st.get("payments") or []):
                if not isinstance(pmt, dict):
                    continue
                nm = pmt.get("name") or ""
                if "通勤" in nm or "交通" in nm:
                    commute_this += _to_int(pmt.get("amount") or 0)
            # 月給 = 総支給額 − 通勤手当 (二重計上を防ぐ)
            entry["gross_salary"] += max(0, gross - commute_this)
            entry["commute"] += commute_this
            # 会社負担社保
            emp_si = _to_int(st.get("total_deduction_employer_share") or 0)
            if emp_si == 0:
                emp_si = int(gross * 0.165)
            entry["social_insurance_employer"] += emp_si
            # 役員報酬
            board = _to_int(st.get("board_member_remuneration_amount") or 0)
            entry["board_pay"] += board
    return summary


def hr_fetch_payroll_history(months_back: int = 12) -> List[dict]:
    """過去N月分の月次給与集計 (一括APIで高速化)"""
    try:
        cid = hr_get_default_company_id()
        if not cid:
            return []
    except FreeeAPIError:
        return []

    today = date.today()
    cursor = today.replace(day=1)
    for _ in range(months_back):
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    rows = []
    for _ in range(months_back):
        y, m = cursor.year, cursor.month
        ym = cursor.strftime("%Y-%m")
        total_gross = 0
        total_social_emp = 0
        total_withholding = 0
        total_employer_si = 0
        emp_count = 0

        statements = hr_get_payroll_statements_month(cid, y, m)
        for st in statements:
            # まずバルクから、無ければ詳細フェッチ
            gross_v = st.get("gross_payment_amount") or st.get("total_payment_amount")
            sie_v = st.get("total_deduction_amount") or st.get("social_insurance")
            wh_v = st.get("income_tax") or st.get("withholding_tax")
            employer_si_v = st.get("total_deduction_employer_share")
            if not gross_v:
                pid = st.get("id")
                if pid:
                    detail = hr_get_payroll_statement_detail(pid, cid)
                    gross_v = detail.get("gross_payment_amount") or detail.get("total_payment_amount")
                    sie_v = detail.get("total_deduction_amount") or detail.get("social_insurance")
                    wh_v = detail.get("income_tax") or detail.get("withholding_tax")
                    employer_si_v = detail.get("total_deduction_employer_share")
            gross = _to_int(gross_v)
            si = _to_int(sie_v)
            wh = _to_int(wh_v)
            employer_si = _to_int(employer_si_v)
            total_gross += gross
            total_social_emp += si
            total_withholding += wh
            total_employer_si += employer_si
            if gross > 0:
                emp_count += 1

        is_bonus = m in (6, 12) and total_gross > 0
        # 実値があればそれを優先、なければ概算
        if total_employer_si > 0:
            social_emp_employer = total_employer_si
        else:
            social_emp_employer = int(total_gross * 0.165)
        resident_tax = int(total_gross * 0.06) if total_gross and not is_bonus else 0
        net_payment = total_gross - total_social_emp - total_withholding - resident_tax

        rows.append({
            "year_month": ym,
            "is_bonus_month": is_bonus,
            "gross_salary": total_gross,
            "social_insurance_employee": total_social_emp,
            "social_insurance_employer": social_emp_employer,
            "withholding_tax": total_withholding,
            "resident_tax": resident_tax,
            "net_payment": net_payment,
            "employer_total_cost": total_gross + social_emp_employer,
            "employee_count": emp_count,
        })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return rows
