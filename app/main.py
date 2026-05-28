"""Flask entry. OAuth + data fetch + forecast APIs. Pure Python, no Pydantic."""
from datetime import date, timedelta

from flask import Flask, jsonify, request, redirect, Response

from . import auth, freee_client, forecast, mock_data, storage, cache
from . import loans as loans_module
from .config import STATIC_DIR, get_settings

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)


def _real_freee() -> bool:
    """True if we should use real freee data (not Mock and connected)."""
    s = get_settings()
    return (not s.mock_mode) and auth.is_connected()


def _wrap(data, source: str, warning: str = None):
    """Wrap response with metadata about source."""
    return {"source": source, "warning": warning, "data": data}


@app.route("/")
def index():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return Response(html, mimetype="text/html; charset=utf-8")


# ---------- Status ----------

@app.route("/api/status", methods=["GET"])
def get_status():
    s = get_settings()
    return jsonify({
        "mock_mode": s.mock_mode,
        "has_credentials": s.has_freee_credentials,
        "connected": auth.is_connected(),
        "redirect_uri": s.freee_redirect_uri,
    })


# ---------- OAuth ----------

@app.route("/oauth/start", methods=["GET"])
def oauth_start():
    s = get_settings()
    if not s.has_freee_credentials:
        return Response(
            "<h2>Setting error</h2><p>Set FREEE_CLIENT_ID / FREEE_CLIENT_SECRET in .env.</p><p><a href='/'>Back</a></p>",
            status=400, mimetype="text/html; charset=utf-8",
        )
    url, _state = auth.build_authorization_url()
    return redirect(url)


@app.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    if error:
        return Response(
            f"<h2>Authorization error</h2><p>{error}</p><p><a href='/'>Back</a></p>",
            status=400, mimetype="text/html; charset=utf-8",
        )
    if not code or not state:
        return Response("code/state missing", status=400)
    if not auth.verify_state(state):
        return Response("state mismatch (CSRF risk)", status=400)
    try:
        auth.exchange_code_for_tokens(code)
    except Exception as e:
        return Response(
            f"<h2>Token fetch failed</h2><pre>{e}</pre><p><a href='/'>Back</a></p>",
            status=500, mimetype="text/html; charset=utf-8",
        )
    return Response(
        "<html><head><meta charset='utf-8'><title>Connected</title></head>"
        "<body style='font-family: sans-serif; padding: 40px;'>"
        "<h2>freee connection completed</h2>"
        "<p>Returning to dashboard in 3 seconds...</p>"
        "<p><a href='/'>Return now</a></p>"
        "<script>setTimeout(function(){location.href='/'}, 3000);</script>"
        "</body></html>",
        mimetype="text/html; charset=utf-8",
    )


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    auth.disconnect()
    return jsonify({"ok": True})


# ---------- Forecast ----------

def _load_history():
    s = get_settings()
    if s.mock_mode or not auth.is_connected():
        return mock_data.generate_mock_history()
    try:
        company_id = freee_client.get_default_company_id()
        if not company_id:
            return mock_data.generate_mock_history()
        history = freee_client.fetch_monthly_history(company_id, months_back=12)
        # 期首残高を再計算: 負債系口座を除外
        try:
            walletables = freee_client.get_walletables(company_id)
            opening = sum(
                (w.get("walletable_balance", 0) or 0)
                for w in walletables
                if not _is_excluded_wallet(w.get("name", ""))
            )
            history["opening_cash_balance"] = opening
        except freee_client.FreeeAPIError:
            pass
        companies = freee_client.get_companies()
        if companies:
            history["company_name"] = companies[0].get("display_name") or companies[0].get("name", "")
        return history
    except freee_client.FreeeAPIError as e:
        result = mock_data.generate_mock_history()
        result["_warning"] = f"freee API取得失敗のためMock使用: {e}"
        return result


@app.route("/api/forecast", methods=["GET"])
def api_forecast():
    scenario = request.args.get("scenario")
    history = _load_history()
    settings = storage.load_settings()
    loans = storage.load_loans()
    if not loans and get_settings().mock_mode:
        loans = mock_data.generate_mock_loans()
    adjustments = storage.load_adjustments()

    if scenario:
        result = forecast.build_forecast(history, settings, loans, adjustments, scenario)
        return jsonify({
            "company_name": history.get("company_name", ""),
            "warning": history.get("_warning"),
            "result": result,
        })
    all_scenarios = forecast.build_all_scenarios(history, settings, loans, adjustments)
    return jsonify({
        "company_name": history.get("company_name", ""),
        "warning": history.get("_warning"),
        "scenarios": all_scenarios,
        "history": history["monthly"],
        "opening_balance": history.get("opening_cash_balance", 0),
    })


# ---------- Settings ----------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(storage.load_settings())


@app.route("/api/settings", methods=["PUT"])
def api_put_settings():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400
    current = storage.load_settings()
    for key in ("receivable_months", "payable_months", "salary_payment_offset_months"):
        if key in payload and payload[key] is not None:
            try:
                current[key] = int(payload[key])
            except (TypeError, ValueError):
                return jsonify({"error": f"{key} must be int"}), 400
    if "opening_cash_balance" in payload:
        v = payload["opening_cash_balance"]
        if v is None or v == "":
            current["opening_cash_balance"] = None
        else:
            try:
                current["opening_cash_balance"] = int(v)
            except (TypeError, ValueError):
                return jsonify({"error": "opening_cash_balance must be int or null"}), 400
    if "scenarios" in payload and isinstance(payload["scenarios"], dict):
        merged = current.get("scenarios", {})
        for k, v in payload["scenarios"].items():
            if isinstance(v, dict):
                merged[k] = {
                    "revenue_multiplier": float(v.get("revenue_multiplier", 1.0)),
                    "cost_multiplier": float(v.get("cost_multiplier", 1.0)),
                }
        current["scenarios"] = merged
    storage.save_settings(current)
    return jsonify(current)


# ---------- Loans ----------

@app.route("/api/loans", methods=["GET"])
def api_get_loans():
    loans = storage.load_loans()
    if not loans and get_settings().mock_mode:
        return jsonify(mock_data.generate_mock_loans())
    return jsonify(loans)


@app.route("/api/loans", methods=["PUT"])
def api_put_loans():
    payload = request.get_json(silent=True) or []
    if not isinstance(payload, list):
        return jsonify({"error": "payload must be an array"}), 400
    cleaned = []
    for loan in payload:
        if not isinstance(loan, dict):
            continue
        try:
            principal = loan.get("principal")
            cleaned.append({
                "name": str(loan.get("name", "")),
                "outstanding": int(loan.get("outstanding", 0)),
                "annual_rate": float(loan.get("annual_rate", 0)),
                "remaining_months": int(loan.get("remaining_months", 0)),
                "grace_months": int(loan.get("grace_months", 0) or 0),
                "repayment_day": int(loan.get("repayment_day", 31) or 31),
                "method": str(loan.get("method", "equal_principal")),
                "start_year_month": loan.get("start_year_month"),
                "principal": int(principal) if principal not in (None, "") else None,
            })
        except (TypeError, ValueError) as e:
            return jsonify({"error": f"invalid loan: {e}"}), 400
    storage.save_loans(cleaned)
    # 借入は税金カレンダー・PL Plan・日次CFに影響
    cache.invalidate("tax_calendar")
    cache.invalidate("pl_plan")
    cache.invalidate("daily_forecast")
    return jsonify(cleaned)


# ---------- Adjustments ----------

@app.route("/api/adjustments", methods=["GET"])
def api_get_adjustments():
    return jsonify(storage.load_adjustments())


@app.route("/api/adjustments", methods=["PUT"])
def api_put_adjustments():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400
    cleaned = {}
    for ym, items in payload.items():
        if not isinstance(items, list):
            continue
        row_list = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                row_list.append({
                    "category": str(item.get("category", "")),
                    "amount": int(item.get("amount", 0)),
                    "type": str(item.get("type", "operating")),
                })
            except (TypeError, ValueError):
                continue
        if row_list:
            cleaned[ym] = row_list
    storage.save_adjustments(cleaned)
    return jsonify(cleaned)


# ============================================================
# NEW with freee real-data integration
# ============================================================

# 現預金から除外する口座名のキーワード（負債/預り系）
EXCLUDED_WALLET_KEYWORDS = ["借入金", "預り金", "未払", "クレジット", "ローン"]


def _is_excluded_wallet(name: str) -> bool:
    if not name:
        return False
    return any(kw in name for kw in EXCLUDED_WALLET_KEYWORDS)


@app.route("/api/bank-accounts", methods=["GET"])
def api_bank_accounts():
    if _real_freee():
        try:
            cid = freee_client.get_default_company_id()
            if cid:
                w = freee_client.get_walletables(cid)
                type_map = {"bank_account": "current", "credit_card": "credit",
                            "wallet": "cash", "private_account_item": "other"}
                included = []
                excluded = []
                for x in w:
                    name = x.get("name") or "（口座名なし）"
                    # walletable_balance（freeeの「現在残高」）を優先
                    bal = x.get("walletable_balance")
                    if bal is None:
                        bal = x.get("last_balance", 0)
                    item = {
                        "id": x.get("id"),
                        "name": name,
                        "type": type_map.get(x.get("type"), x.get("type", "")),
                        "balance": int(bal or 0),
                        "bank_code": x.get("bank_id", "") or "",
                        "branch": str(x.get("branch_id", "") or ""),
                        "raw_walletable_balance": x.get("walletable_balance"),
                        "raw_last_balance": x.get("last_balance"),
                    }
                    if _is_excluded_wallet(name):
                        item["excluded_reason"] = "負債/預り金扱い（現預金から除外）"
                        excluded.append(item)
                    else:
                        included.append(item)
                return jsonify({
                    "source": "freee",
                    "data": included,
                    "excluded": excluded,
                })
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee取得失敗: {e}",
                            "data": mock_data.generate_mock_bank_accounts()})
    return jsonify({"source": "mock", "data": mock_data.generate_mock_bank_accounts()})


@app.route("/api/ar-schedule", methods=["GET"])
def api_ar_schedule():
    if _real_freee():
        try:
            cid = freee_client.get_default_company_id()
            if cid:
                data = freee_client.fetch_ar_schedule(cid)
                if data:
                    return jsonify({"source": "freee", "data": data})
                return jsonify({"source": "freee",
                                "warning": "freeeに該当期間の売上取引がありません",
                                "data": []})
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee取得失敗: {e}",
                            "data": mock_data.generate_mock_ar_schedule()})
    return jsonify({"source": "mock", "data": mock_data.generate_mock_ar_schedule()})


@app.route("/api/ap-schedule", methods=["GET"])
def api_ap_schedule():
    if _real_freee():
        try:
            cid = freee_client.get_default_company_id()
            if cid:
                data = freee_client.fetch_ap_schedule(cid)
                if data:
                    return jsonify({"source": "freee", "data": data})
                return jsonify({"source": "freee",
                                "warning": "freeeに該当期間の経費取引がありません",
                                "data": []})
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee取得失敗: {e}",
                            "data": mock_data.generate_mock_ap_schedule()})
    return jsonify({"source": "mock", "data": mock_data.generate_mock_ap_schedule()})


def _last_day_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def _build_tax_calendar_from_plan() -> list:
    """事業計画P/L から税金支払予定を生成する。
    3月決算法人を想定。
    - 法人税等: 期末翌2ヶ月以内 (5月末)。中間納付(上期実績半分)を11月末
    - 消費税: 期末翌2ヶ月以内 (5月末)。中間納付を11月末 (前年実績の半分)
    - 源泉所得税: 当月給与 × 概算0.05 → 翌月10日
    - 住民税(特別徴収): 当月給与 × 概算0.06 → 翌月10日
    - 社会保険料(会社負担分): 既存の支払予測に含まれている想定 → 重複回避でカレンダーには出さない
    """
    plan = _build_plan_pl(months_ahead=12)
    rows = plan.get("months", [])
    today = date.today()
    events = []

    # ---- 法人税等 ----
    # 3月決算: 4月開始 → 翌3月末
    # 当期の月別 pretax_profit を fiscal年度ごとに合計し、5月末に年税
    by_fy_pretax: dict[int, int] = {}
    by_fy_h1_pretax: dict[int, int] = {}  # 上期 (4-9月) 累積
    for r in rows:
        try:
            y, m = (int(x) for x in r["year_month"].split("-"))
        except Exception:
            continue
        fy = y if m >= 4 else y - 1
        by_fy_pretax[fy] = by_fy_pretax.get(fy, 0) + int(r.get("pretax_profit", 0))
        if 4 <= m <= 9:
            by_fy_h1_pretax[fy] = by_fy_h1_pretax.get(fy, 0) + int(r.get("pretax_profit", 0))

    for fy, total in by_fy_pretax.items():
        # 年税確定 (期末翌5月末)
        annual_tax = int(max(0, total) * 0.30)
        due = date(fy + 1, 5, 31)
        if due >= today:
            events.append({
                "name": "法人税等(確定)",
                "due_date": due.isoformat(),
                "amount": annual_tax,
                "note": f"FY{fy} (4月-翌3月) 税引前利益 ¥{total:,} × 30%概算",
            })

    for fy, h1_total in by_fy_h1_pretax.items():
        # 中間納付: 11月末 (上期実績 × 50%)
        midyear_tax = int(max(0, h1_total) * 0.30 * 0.5)
        if midyear_tax > 0:
            due = date(fy, 11, 30)
            if due >= today:
                events.append({
                    "name": "法人税等(中間納付)",
                    "due_date": due.isoformat(),
                    "amount": midyear_tax,
                    "note": f"FY{fy} 上期(4-9月)実績ベース概算",
                })

    # ---- 消費税 ----
    by_fy_ctax_net: dict[int, int] = {}
    by_fy_h1_ctax_net: dict[int, int] = {}
    for r in rows:
        try:
            y, m = (int(x) for x in r["year_month"].split("-"))
        except Exception:
            continue
        fy = y if m >= 4 else y - 1
        net = int(r.get("consumption_tax_received", 0)) - int(r.get("consumption_tax_paid", 0))
        by_fy_ctax_net[fy] = by_fy_ctax_net.get(fy, 0) + net
        if 4 <= m <= 9:
            by_fy_h1_ctax_net[fy] = by_fy_h1_ctax_net.get(fy, 0) + net

    for fy, net in by_fy_ctax_net.items():
        if net > 0:
            due = date(fy + 1, 5, 31)
            if due >= today:
                events.append({
                    "name": "消費税(確定)",
                    "due_date": due.isoformat(),
                    "amount": net,
                    "note": f"FY{fy} 仮受 − 仮払 = ¥{net:,}",
                })

    for fy, h1net in by_fy_h1_ctax_net.items():
        if h1net > 0:
            mid = int(h1net * 0.5)
            due = date(fy, 11, 30)
            if due >= today:
                events.append({
                    "name": "消費税(中間納付)",
                    "due_date": due.isoformat(),
                    "amount": mid,
                    "note": f"FY{fy} 上期実績 × 50%概算",
                })

    # ---- 源泉所得税・住民税(特別徴収) 各月10日 ----
    for r in rows:
        try:
            y, m = (int(x) for x in r["year_month"].split("-"))
        except Exception:
            continue
        salary = int(r.get("salary", 0))
        if salary <= 0:
            continue
        # 翌月
        ny = y; nm = m + 1
        if nm > 12:
            nm = 1; ny += 1
        try:
            due = date(ny, nm, 10)
        except Exception:
            continue
        if due < today:
            continue
        wh = int(salary * 0.05)
        rt = int(salary * 0.06)
        events.append({
            "name": "源泉所得税(納期特例なし)",
            "due_date": due.isoformat(),
            "amount": wh,
            "note": f"{y}/{m} 給与支給 ¥{salary:,} × 概算5%",
        })
        events.append({
            "name": "住民税(特別徴収)",
            "due_date": due.isoformat(),
            "amount": rt,
            "note": f"{y}/{m} 給与支給ベース概算6%",
        })

    events.sort(key=lambda x: x["due_date"])
    return events


@app.route("/api/tax-calendar", methods=["GET"])
def api_tax_calendar():
    """税金カレンダー: 事業計画P/Lを元に法人税・消費税・源泉/住民税を算出"""
    try:
        events = cache.get_or_set("tax_calendar", _build_tax_calendar_from_plan, ttl=600)
        if not events:
            return jsonify({
                "source": "empty",
                "warning": "事業計画P/Lから算出可能な税金が見つかりませんでした（入金/支払予測が空の可能性）",
                "data": []
            })
        return jsonify({
            "source": "freee" if _real_freee() else "template",
            "warning": "事業計画P/L(税抜会計)からの概算。実効税率30%・消費税10%・源泉5%・住民税6%を仮定",
            "data": events,
        })
    except Exception as e:
        return jsonify({"source": "empty", "warning": f"算出失敗: {e}", "data": []})


@app.route("/api/daily-forecast", methods=["GET"])
def api_daily_forecast():
    """日次CF予測: 連携時はAR/AP/tax/walletablesから生成、それ以外はMock"""
    try:
        days = int(request.args.get("days", "30"))
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(days, 90))

    if _real_freee():
        try:
            cid = freee_client.get_default_company_id()
            if cid:
                # 期首残高: 負債系口座を除外
                w = freee_client.get_walletables(cid)
                opening = sum(
                    (x.get("walletable_balance", 0) or 0)
                    for x in w
                    if not _is_excluded_wallet(x.get("name", ""))
                )
                ar = freee_client.fetch_ar_schedule(cid)
                ap = freee_client.fetch_ap_schedule(cid)
                # 予測項目も追加（過去パターン+編集内容から将来予測）
                try:
                    overrides = storage.load_forecast_overrides()
                    pf_income = freee_client.fetch_payment_forecast(cid, deal_type="income", months_ahead=3, overrides=overrides)
                    pf_expense = freee_client.fetch_payment_forecast(cid, deal_type="expense", months_ahead=3, overrides=_ensure_social_insurance_in_overrides(_ensure_salary_in_overrides(overrides)))
                    # 将来日付の予測項目を AR/AP に追加
                    for pat in pf_income.get("patterns", []):
                        for f in pat.get("future", []):
                            ar.append({
                                "invoice_no": f"PRED-{pat['partner']}",
                                "customer": pat["partner"] + "（予測）",
                                "issue_date": f["issue_date"],
                                "due_date": f["due_date"],
                                "amount": f["amount"],
                                "status": "scheduled",
                                "payment_term_days": pat.get("payment_term_days", 30),
                            })
                    for pat in pf_expense.get("patterns", []):
                        for f in pat.get("future", []):
                            ap.append({
                                "bill_no": f"PRED-{pat['partner']}",
                                "vendor": pat["partner"] + "（予測）",
                                "category": "予測",
                                "issue_date": f["issue_date"],
                                "due_date": f["due_date"],
                                "amount": f["amount"],
                                "status": "scheduled",
                            })
                except Exception:
                    pass
                # build daily
                today = date.today()
                daily = {}
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
                # 税金はfreee連携時はテンプレートを混ぜない（手動調整で登録）
                # 必要なら、手動調整から拾われる
                rows = sorted(daily.values(), key=lambda x: x["date"])
                bal = opening
                for row in rows:
                    row["net"] = row["inflow"] - row["outflow"]
                    bal += row["net"]
                    row["ending_balance"] = bal
                return jsonify({"source": "freee", "data": rows})
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee取得失敗: {e}",
                            "data": mock_data.generate_mock_daily_forecast(days=days)})
    return jsonify({"source": "mock", "data": mock_data.generate_mock_daily_forecast(days=days)})


def _infer_default_category(emp: dict) -> str:
    """雇用形態と部門/役職から、カテゴリ(exec/employee/engineer)を推測する。"""
    et = emp.get("employment_type") or ""
    pos = emp.get("position") or ""
    dept = emp.get("department") or ""
    if "役員" in et:
        return "exec"
    if "エンジニア" in pos or "エンジニア" in dept or "開発" in pos or "開発" in dept:
        return "engineer"
    return "employee"


def _apply_employee_overrides(emps: list) -> list:
    """employee_overrides.json の手動上書きを emps にマージ。
    上書きで指定された値は freee 由来の値より優先される。category 未指定はデフォルト推測。"""
    overrides = storage.load_employee_overrides() or {}
    out = []
    for e in emps:
        eid = str(e.get("id") or "")
        ov = overrides.get(eid, {}) if isinstance(overrides, dict) else {}
        merged = dict(e)
        for key in ("monthly_salary", "commute_allowance", "annual_salary",
                    "department", "position", "employment_type"):
            v = ov.get(key)
            if v is not None and v != "" and v != 0:
                # 数値型は0でない時のみ上書き、文字列は空でない時のみ
                merged[key] = v
        # 固定残業代の単独上書き
        if "fixed_overtime" in ov and ov.get("fixed_overtime"):
            base = int(merged.get("monthly_salary") or 0)
            # 月給に既に含まれていない可能性もあるので additive ではなく既存値が低ければ書き換える
            merged["fixed_overtime_override"] = int(ov.get("fixed_overtime"))
        # カテゴリ
        cat = ov.get("category") or _infer_default_category(merged)
        merged["category"] = cat
        # annual_salary が未上書きで monthly_salary が変わっていたら再計算
        if "monthly_salary" in ov and "annual_salary" not in ov:
            merged["annual_salary"] = int(merged["monthly_salary"]) * 12
        # 上書きフラグ
        merged["has_override"] = bool(ov)
        out.append(merged)
    return out


@app.route("/api/employees", methods=["GET"])
def api_employees():
    if _real_freee():
        try:
            emps = cache.get_or_set("employees", freee_client.hr_fetch_employees, ttl=600)
            if emps:
                merged = _apply_employee_overrides(emps)
                return jsonify({"source": "freee", "data": merged})
            return jsonify({"source": "mock",
                            "warning": "freee人事労務から従業員が取得できませんでした",
                            "data": _apply_employee_overrides(mock_data.generate_mock_employees())})
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee人事労務取得失敗: {e}",
                            "data": _apply_employee_overrides(mock_data.generate_mock_employees())})
    return jsonify({"source": "mock", "data": _apply_employee_overrides(mock_data.generate_mock_employees())})


@app.route("/api/org-chart", methods=["GET"])
def api_org_chart():
    """組織図 (freee人事労務の組織マスタ＋従業員所属を統合表示)。
    返却形式: 階層化されたツリー (root: 会社) + 各部門の所属メンバー一覧。
    """
    # 従業員データを取得 (freee/mock両対応)
    try:
        if _real_freee():
            emps = cache.get_or_set("employees", freee_client.hr_fetch_employees, ttl=600) or []
        else:
            emps = mock_data.generate_mock_employees()
    except Exception:
        emps = mock_data.generate_mock_employees()
    emps = _apply_employee_overrides(emps)

    # 役職の序列
    POS_RANK = {
        "代表取締役": 1, "取締役": 2, "執行役員": 3,
        "部長": 4, "マネージャー": 5, "チーフ": 6,
        "リーダー": 7, "メンバー": 8, "アソシエイト": 9,
    }

    def emp_brief(e):
        return {
            "id": e.get("id"),
            "name": e.get("name", ""),
            "position": e.get("position", ""),
            "employee_number": e.get("employee_number", ""),
            "department": e.get("department", ""),
            "monthly_salary": e.get("monthly_salary", 0),
            "hire_date": e.get("hire_date", ""),
            "employment_type": e.get("employment_type", ""),
            "pos_rank": POS_RANK.get(e.get("position", ""), 99),
        }

    # 経営層 (役員) と部門の二段構造
    executives = sorted(
        [emp_brief(e) for e in emps if e.get("position") in ("代表取締役", "取締役", "執行役員")],
        key=lambda x: (x["pos_rank"], x["employee_number"]),
    )

    # 部門ごとに集計
    dept_map = {}
    for e in emps:
        # 役員はトップに、その他は部門に
        if e.get("position") in ("代表取締役", "取締役"):
            continue
        dept = e.get("department") or "未配属"
        if dept not in dept_map:
            dept_map[dept] = []
        dept_map[dept].append(emp_brief(e))

    departments = []
    for dept_name, members in sorted(dept_map.items()):
        members_sorted = sorted(members, key=lambda x: (x["pos_rank"], x["employee_number"]))
        # 部長を部門責任者として
        manager = next((m for m in members_sorted if m["position"] == "部長"), None)
        departments.append({
            "name": dept_name,
            "manager": manager,
            "member_count": len(members_sorted),
            "members": members_sorted,
            "avg_salary": int(sum(m["monthly_salary"] for m in members_sorted) / len(members_sorted)) if members_sorted else 0,
            "total_salary": sum(m["monthly_salary"] for m in members_sorted),
        })

    return jsonify({
        "source": "freee" if _real_freee() else "mock",
        "company_name": mock_data.DEMO_COMPANY_NAME if not _real_freee() else "貴社",
        "total_members": len(emps),
        "executives": executives,
        "departments": departments,
    })


def _calc_employee_sales(cid: int, fiscal_year: int, employees: list) -> dict:
    """期(4月-翌3月)の従業員別売上(税抜)を計算 (明細単位集計)。
    - 勘定科目が「売上系」のみ集計、「旅費交通費」など費用系は除外（経費精算が誤計上されない）
    - 各明細行の (amount - vat) で 税抜金額 を従業員別に集計
    - 行の description に従業員氏名があれば紐付け、無ければ取引全体の摘要で紐付け
    """
    from datetime import date as _date
    start = _date(fiscal_year, 4, 1)
    end = _date(fiscal_year + 1, 3, 31)
    today = _date.today()
    if end > today:
        end = today

    # 勘定科目マスタ取得: 売上系の account_item_id を特定
    revenue_account_ids: set = set()
    excluded_account_ids: set = set()  # 旅費交通費など費用系
    try:
        items = freee_client.get_account_items(cid)
        for it in items:
            cat = (it.get("account_category") or it.get("category") or "") or ""
            cat_name = (it.get("account_category_name") or "") or ""
            name = (it.get("name") or "") or ""
            iid = it.get("id")
            if iid is None:
                continue
            # 売上系: account_category が「売上高」「営業収益」を含む
            if ("売上" in cat or "売上" in cat_name or "営業収益" in cat
                or "営業収益" in cat_name or "sales" in cat.lower()):
                revenue_account_ids.add(iid)
                continue
            # 売上高に類する科目名 (sales, revenue)
            if "売上高" in name or "売上" in name and "原価" not in name:
                revenue_account_ids.add(iid)
                continue
            # 旅費交通費・経費系は除外対象に
            if ("旅費" in name or "交通費" in name or "立替" in name
                or "費" in name or "原価" in name or "経費" in name):
                excluded_account_ids.add(iid)
    except Exception:
        # 取得失敗時はキーワードフォールバック
        pass

    # 名前マップを構築。長い文字列から優先マッチ
    name_entries: list = []
    for e in employees:
        eid = e.get("id")
        if not eid:
            continue
        nm = (e.get("name") or "").replace("　", " ").strip()
        if not nm:
            continue
        name_entries.append((nm, eid, 0))
        joined = nm.replace(" ", "")
        if joined != nm:
            name_entries.append((joined, eid, 0))
        parts = nm.split()
        for p in parts:
            if len(p) >= 2:
                name_entries.append((p, eid, 1))
    name_entries.sort(key=lambda x: (x[2], -len(x[0])))

    sales_by_eid: dict = {eid: 0 for eid in (e.get("id") for e in employees) if eid}
    unmatched_total = 0
    unmatched_count = 0
    excluded_total = 0  # 経費精算で除外された金額

    try:
        deals = freee_client.get_deals(cid, start, end, deal_type="income")
    except Exception:
        deals = []

    def _line_is_revenue(det):
        """明細行が売上系か判定"""
        aid = det.get("account_item_id")
        if aid is not None:
            if aid in revenue_account_ids:
                return True
            if aid in excluded_account_ids:
                return False
        # account_item_id が無いor未分類: descriptionキーワードで判定
        desc = det.get("description") or ""
        if "旅費" in desc or "交通費" in desc:
            return False
        return True  # デフォルトは売上扱い

    for d in deals:
        details = d.get("details") or []
        deal_text = " ".join([
            d.get("ref_number") or "",
            d.get("description") or "",
            d.get("partner_name") or "",
            d.get("memo") or "",
        ])

        if not details:
            continue  # 明細無しはスキップ (税抜計算不可)

        any_line_matched = False
        for det in details:
            if not isinstance(det, dict):
                continue
            # 売上系かどうかでフィルタ
            if not _line_is_revenue(det):
                # 経費精算等を除外
                excl_amt = int(det.get("amount", 0) or 0)
                if excl_amt > 0:
                    excluded_total += excl_amt
                continue
            det_amt = int(det.get("amount", 0) or 0)
            det_vat = int(det.get("vat", 0) or 0)
            # 税抜金額
            det_amt_excl = det_amt - det_vat
            if det_amt_excl <= 0:
                continue
            det_desc = det.get("description") or ""
            # 行descriptionで従業員マッチ
            matched_eid = None
            for nm, eid, _pri in name_entries:
                if nm in det_desc:
                    matched_eid = eid
                    break
            # 行で見つからなければ deal_text にフォールバック
            if not matched_eid:
                combined = det_desc + " " + deal_text
                for nm, eid, _pri in name_entries:
                    if nm in combined:
                        matched_eid = eid
                        break
            if matched_eid:
                sales_by_eid[matched_eid] = sales_by_eid.get(matched_eid, 0) + det_amt_excl
                any_line_matched = True
            else:
                unmatched_total += det_amt_excl
                unmatched_count += 1

    sales_by_eid["__unmatched__"] = {"amount": unmatched_total, "count": unmatched_count}
    sales_by_eid["__excluded__"] = {"amount": excluded_total}
    sales_by_eid["__revenue_account_count__"] = len(revenue_account_ids)
    sales_by_eid["__excluded_account_count__"] = len(excluded_account_ids)
    return sales_by_eid


@app.route("/api/employee-gross-profit", methods=["GET"])
def api_employee_gross_profit():
    """従業員別の粗利を計算。
    クエリ: ?fiscal_year=2026 (4月-翌3月) [&nocache=1 でキャッシュ無視]
    """
    try:
        fy = int(request.args.get("fiscal_year") or "0")
    except (TypeError, ValueError):
        fy = 0
    today = date.today()
    if fy <= 0:
        # 3月決算: 4月以降は当年度、1〜3月は前年度
        fy = today.year if today.month >= 4 else today.year - 1

    # ?nocache=1 が指定されたらキャッシュ無効化
    if request.args.get("nocache"):
        cache.invalidate("payroll_summary_")
        cache.invalidate("emp_sales_")

    if not _real_freee():
        return jsonify({"source": "empty",
                        "warning": "freee連携時のみ取得可能",
                        "data": None})

    try:
        # 従業員(手動上書きマージ後)
        emps = cache.get_or_set("employees",
                                freee_client.hr_fetch_employees,
                                ttl=600)
        emps = _apply_employee_overrides(emps or [])
        # 給与累計 (支払サイト考慮: 月末締翌月末払なら offset=1)
        settings = storage.load_settings()
        pay_offset = int(settings.get("salary_payment_offset_months", 1) or 1)
        cache_key_payroll = f"payroll_summary_{fy}_off{pay_offset}"
        payroll = cache.get_or_set(
            cache_key_payroll,
            lambda: freee_client.hr_fetch_employee_payroll_summary(fy, payment_offset_months=pay_offset),
            ttl=600,
        )
        # 売上累計
        cid = freee_client.get_default_company_id()
        cache_key_sales = f"emp_sales_{fy}"
        sales_by_eid = cache.get_or_set(
            cache_key_sales,
            lambda: _calc_employee_sales(cid, fy, emps),
            ttl=600,
        )

        rows = []
        sum_salary = 0; sum_si = 0; sum_commute = 0; sum_sales = 0; sum_gp = 0
        unmatched = sales_by_eid.pop("__unmatched__", {"amount": 0, "count": 0})
        excluded = sales_by_eid.pop("__excluded__", {"amount": 0})
        rev_acc_count = sales_by_eid.pop("__revenue_account_count__", 0)
        exc_acc_count = sales_by_eid.pop("__excluded_account_count__", 0)
        for e in emps:
            eid = e.get("id")
            pay = payroll.get(eid, {}) if eid else {}
            sal = int(pay.get("gross_salary", 0))
            si = int(pay.get("social_insurance_employer", 0))
            commute = int(pay.get("commute", 0))
            sales = int(sales_by_eid.get(eid, 0))
            cost = sal + si + commute
            gp = sales - cost
            rows.append({
                "id": eid,
                "employee_number": e.get("employee_number") or "",
                "name": e.get("name") or "",
                "monthly_salary_total": sal,
                "social_insurance_total": si,
                "commute_total": commute,
                "labor_cost_total": cost,
                "sales_total": sales,
                "gross_profit": gp,
                "gross_profit_ratio": round(gp / sales * 100, 2) if sales else 0,
            })
            sum_salary += sal; sum_si += si; sum_commute += commute
            sum_sales += sales; sum_gp += gp

        return jsonify({
            "source": "freee",
            "data": {
                "fiscal_year": fy,
                "period_label": f"{fy}年度 ({fy}年4月〜{fy+1}年3月)",
                "rows": rows,
                "summary": {
                    "total_salary": sum_salary,
                    "total_social_insurance": sum_si,
                    "total_commute": sum_commute,
                    "total_labor_cost": sum_salary + sum_si + sum_commute,
                    "total_sales": sum_sales,
                    "total_gross_profit": sum_gp,
                    "gross_profit_ratio": round(sum_gp / sum_sales * 100, 2) if sum_sales else 0,
                    "unmatched_sales": int(unmatched.get("amount", 0)),
                    "unmatched_count": int(unmatched.get("count", 0)),
                    "excluded_amount": int(excluded.get("amount", 0)),
                    "revenue_account_count": rev_acc_count,
                    "excluded_account_count": exc_acc_count,
                    "salary_payment_offset_months": pay_offset,
                },
            },
        })
    except Exception as e:
        return jsonify({"source": "empty", "warning": f"計算失敗: {e}", "data": None})


@app.route("/api/employee-detail/<int:emp_id>", methods=["GET"])
def api_get_employee_detail(emp_id):
    """1名分の詳細を取得 (mock + 手動上書きをマージ)"""
    # 全従業員から該当者を取得
    emps_raw = []
    if _real_freee():
        try:
            emps_raw = cache.get_or_set("employees", freee_client.hr_fetch_employees, ttl=600) or []
        except Exception:
            emps_raw = []
    if not emps_raw:
        emps_raw = mock_data.generate_mock_employees()
    target = next((e for e in emps_raw if e.get("id") == emp_id), None)
    if not target:
        return jsonify({"error": "not found"}), 404
    # 詳細上書きをマージ
    details_ov = storage.load_employee_details() or {}
    saved = details_ov.get(str(emp_id), {})
    merged_detail = dict(target.get("detail") or {})
    for k, v in saved.items():
        merged_detail[k] = v
    target["detail"] = merged_detail
    return jsonify({"data": target})


@app.route("/api/employee-detail/<int:emp_id>", methods=["PUT"])
def api_put_employee_detail(emp_id):
    """1名分の詳細を上書き保存"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be object"}), 400
    all_details = storage.load_employee_details() or {}
    all_details[str(emp_id)] = payload
    storage.save_employee_details(all_details)
    return jsonify({"ok": True, "saved": payload})


@app.route("/api/employee-overrides", methods=["GET"])
def api_get_employee_overrides():
    """従業員手動上書きを取得"""
    return jsonify(storage.load_employee_overrides())


@app.route("/api/employee-overrides", methods=["DELETE"])
def api_clear_all_employee_overrides():
    """全員の手動上書きをクリア（freee 自動読込に戻す）"""
    storage.save_employee_overrides({})
    # 従業員一覧キャッシュも無効化
    cache.invalidate("employees")
    return jsonify({"ok": True, "cleared_all": True})


@app.route("/api/employee-overrides", methods=["PUT"])
def api_put_employee_overrides():
    """従業員手動上書きを保存（全置換）"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400
    # 構造を整える
    cleaned: dict = {}
    for eid, ov in payload.items():
        if not isinstance(ov, dict):
            continue
        rec: dict = {}
        for key in ("monthly_salary", "commute_allowance", "fixed_overtime", "annual_salary"):
            v = ov.get(key)
            if v in (None, ""):
                continue
            try:
                rec[key] = int(v)
            except (TypeError, ValueError):
                continue
        for key in ("department", "position", "category", "employment_type"):
            v = ov.get(key)
            if v not in (None, ""):
                rec[key] = str(v)
        if rec:
            cleaned[str(eid)] = rec
    storage.save_employee_overrides(cleaned)
    # 従業員一覧キャッシュは生 freee 結果なので無効化不要。再フェッチ時に再マージされる
    return jsonify(cleaned)


@app.route("/api/payroll-history", methods=["GET"])
def api_payroll_history():
    if _real_freee():
        try:
            rows = cache.get_or_set("payroll_history_12",
                                    lambda: freee_client.hr_fetch_payroll_history(months_back=12),
                                    ttl=600)
            # 全月0なら取得できなかったとみなす
            if rows and any(r["gross_salary"] > 0 for r in rows):
                return jsonify({"source": "freee", "data": rows})
            return jsonify({"source": "mock",
                            "warning": "freee人事労務に給与明細が登録されていません",
                            "data": mock_data.generate_mock_payroll_history()})
        except freee_client.FreeeAPIError as e:
            return jsonify({"source": "mock",
                            "warning": f"freee人事労務取得失敗: {e}",
                            "data": mock_data.generate_mock_payroll_history()})
    return jsonify({"source": "mock", "data": mock_data.generate_mock_payroll_history()})


@app.route("/api/bonus-calendar", methods=["GET"])
def api_bonus_calendar():
    """賞与カレンダー: freee連携時は空、未連携時はテンプレート"""
    if _real_freee():
        return jsonify({
            "source": "empty",
            "warning": "freee連携時は架空データを混ぜません。実際の賞与予定は「手動調整」ページで登録してください。",
            "data": []
        })
    return jsonify({
        "source": "template",
        "warning": "賞与予定は7月・12月のテンプレート",
        "data": mock_data.generate_mock_bonus_calendar()
    })


def _aggregate_labor_costs(balances):
    """trial_pl balances から労務関連科目を「売上原価」「販管費」セクション別に集計。
    freee の prl_pl の科目は parent_account_category_name で区分される。"""
    cogs = {"salary": 0, "social_insurance": 0, "travel": 0}
    sga = {"salary": 0, "social_insurance": 0}
    for b in balances:
        name = b.get("account_item_name") or ""
        cat = (
            b.get("parent_account_category_name")
            or b.get("account_category_name")
            or ""
        )
        amt = int(b.get("closing_balance", 0) or 0)
        is_cogs = "売上原価" in cat or cat == "原価"
        is_sga = (
            "販売管理費" in cat
            or "販管費" in cat
            or "販売費" in cat
            or "一般管理" in cat
        )
        if not (is_cogs or is_sga):
            continue
        # 科目分類: 名称マッチ
        if any(kw in name for kw in ["給料", "給与", "賃金", "役員報酬", "雑給"]):
            (cogs if is_cogs else sga)["salary"] += amt
        elif "法定福利" in name:
            (cogs if is_cogs else sga)["social_insurance"] += amt
        elif "旅費" in name or "通勤" in name:
            # 旅費交通費は売上原価のときのみ「現場交通費」として人件費含めて扱う
            if is_cogs:
                cogs["travel"] += amt
            # 販管費の旅費交通費は人件費に含めない
    return cogs, sga


@app.route("/api/labor-analysis", methods=["GET"])
def api_labor_analysis():
    """人件費分析: P/L月次から売上高・売上原価人件費・販管費人件費を集計。
    人件費(売上原価) = 給料手当(原) + 法定福利費(原) + 旅費交通費(原)
    人件費(全体)     = 上記 + 給料手当(販) + 法定福利費(販)
    """
    if not _real_freee():
        return jsonify({"source": "mock", "data": mock_data.generate_mock_labor_analysis()})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        raw = cache.get_or_set(
            f"pl_monthly_{cid}_12",
            lambda: freee_client.get_trial_pl_monthly(cid, months=12),
            ttl=600,
        )
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "mock", "warning": f"freee取得失敗: {e}",
                        "data": mock_data.generate_mock_labor_analysis()})

    # 従業員数: 給与明細件数 (実支給者数)
    try:
        payroll = cache.get_or_set(
            "payroll_history_12",
            lambda: freee_client.hr_fetch_payroll_history(months_back=12),
            ttl=600,
        )
    except Exception:
        payroll = []
    pay_map = {r["year_month"]: r for r in payroll}

    monthly = []
    sum_rev = 0
    sum_cogs_sal = 0
    sum_cogs_si = 0
    sum_cogs_tr = 0
    sum_sga_sal = 0
    sum_sga_si = 0
    emp_max = 0

    for m in raw:
        ym = m["year_month"]
        balances = m.get("balances") or []
        summary = _summarize_pl_balances(balances)
        rev = int(summary.get("revenue") or 0)
        cogs, sga = _aggregate_labor_costs(balances)
        cogs_labor = cogs["salary"] + cogs["social_insurance"] + cogs["travel"]
        sga_labor = sga["salary"] + sga["social_insurance"]
        total = cogs_labor + sga_labor
        emp = int(pay_map.get(ym, {}).get("employee_count", 0))
        monthly.append({
            "year_month": ym,
            "revenue": rev,
            "cogs_salary": cogs["salary"],
            "cogs_social_insurance": cogs["social_insurance"],
            "cogs_travel": cogs["travel"],
            "cogs_labor_total": cogs_labor,
            "sga_salary": sga["salary"],
            "sga_social_insurance": sga["social_insurance"],
            "sga_labor_total": sga_labor,
            "labor_total": total,
            "cogs_labor_to_revenue_ratio": round(cogs_labor / rev * 100, 2) if rev else 0,
            "labor_to_revenue_ratio": round(total / rev * 100, 2) if rev else 0,
            "revenue_per_employee": int(rev / max(1, emp)) if emp else 0,
            "employee_count": emp,
        })
        sum_rev += rev
        sum_cogs_sal += cogs["salary"]
        sum_cogs_si += cogs["social_insurance"]
        sum_cogs_tr += cogs["travel"]
        sum_sga_sal += sga["salary"]
        sum_sga_si += sga["social_insurance"]
        emp_max = max(emp_max, emp)

    cogs_labor_total = sum_cogs_sal + sum_cogs_si + sum_cogs_tr
    sga_labor_total = sum_sga_sal + sum_sga_si
    total_labor = cogs_labor_total + sga_labor_total

    return jsonify({"source": "freee", "data": {
        "annual_revenue": sum_rev,
        "annual_cogs_salary": sum_cogs_sal,
        "annual_cogs_social_insurance": sum_cogs_si,
        "annual_cogs_travel": sum_cogs_tr,
        "annual_cogs_labor_total": cogs_labor_total,
        "annual_sga_salary": sum_sga_sal,
        "annual_sga_social_insurance": sum_sga_si,
        "annual_sga_labor_total": sga_labor_total,
        "annual_total_labor_cost": total_labor,
        "cogs_labor_to_revenue_ratio": round(cogs_labor_total / sum_rev * 100, 2) if sum_rev else 0,
        "labor_to_revenue_ratio": round(total_labor / sum_rev * 100, 2) if sum_rev else 0,
        "revenue_per_employee_annual": int(sum_rev / max(1, emp_max)) if emp_max else 0,
        "labor_cost_per_employee_monthly": int(total_labor / 12 / max(1, emp_max)) if emp_max else 0,
        "employee_count": emp_max,
        "monthly_breakdown": monthly,
    }})


@app.route("/api/raw/<path:subpath>", methods=["GET"])
def api_raw(subpath):
    """Return raw freee API response for a given path. For debugging only."""
    if not auth.is_connected():
        return jsonify({"error": "not connected"}), 400
    hr = request.args.get("hr", "").lower() in ("1", "true", "yes")
    params = {k: v for k, v in request.args.items() if k != "hr"}
    if "company_id" not in params and not hr:
        try:
            cid = freee_client.get_default_company_id()
            if cid:
                params["company_id"] = cid
        except Exception:
            pass
    try:
        data = freee_client._get("/" + subpath, params=params, hr=hr)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/trial-pl", methods=["GET"])
def api_trial_pl():
    """損益計算書"""
    if not _real_freee():
        # Mock: 月次PLを年間累計に変換して balances 形式で返す
        m_rows = mock_data.generate_mock_pl_monthly()
        total_rev = sum(r["revenue"] for r in m_rows)
        total_cogs = sum(r["cogs"] for r in m_rows)
        total_sga = sum(r["sga"] for r in m_rows)
        total_op = total_rev - total_cogs - total_sga
        balances = [
            {"account_item_name": "売上高", "account_category_name": "売上高", "closing_balance": total_rev, "hierarchy_level": 1},
            {"account_item_name": "売上原価", "account_category_name": "売上原価", "closing_balance": total_cogs, "hierarchy_level": 1},
            {"account_item_name": "売上総利益", "account_category_name": "売上総利益", "closing_balance": total_rev - total_cogs, "hierarchy_level": 0, "total_line": True},
            {"account_item_name": "販売管理費", "account_category_name": "販売管理費", "closing_balance": total_sga, "hierarchy_level": 1},
            {"account_item_name": "営業利益", "account_category_name": "営業利益", "closing_balance": total_op, "hierarchy_level": 0, "total_line": True},
        ]
        return jsonify({"source": "mock", "data": {"balances": balances, "fiscal_year": date.today().year, "start_month": 4, "end_month": 3}})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        fy = request.args.get("fiscal_year")
        kwargs = {}
        if fy:
            kwargs["fiscal_year"] = int(fy)
        sm = request.args.get("start_month")
        em = request.args.get("end_month")
        if sm: kwargs["start_month"] = int(sm)
        if em: kwargs["end_month"] = int(em)
        data = freee_client.get_trial_pl(cid, **kwargs)
        return jsonify({"source": "freee", "data": data})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": f"取得失敗: {e}", "data": None})


def _pick_balance(balances, keywords):
    """parent_account_category_name / account_category_name / account_item_name に
    指定キーワードのいずれかが含まれる closing_balance を合計する。
    合計行(total_line=True または name に「合計」を含む)が同名で複数存在する場合は重複を避ける。"""
    total = 0
    seen_total_for_kw = set()
    for b in balances:
        for src_field in ("account_category_name", "parent_account_category_name", "account_item_name"):
            name = b.get(src_field) or ""
            for kw in keywords:
                if kw and kw in name:
                    # 合計行ならキーワードごとに1回だけ採用
                    is_total = bool(b.get("total_line")) or ("合計" in name)
                    sig = (kw, name) if is_total else (kw, id(b))
                    if sig in seen_total_for_kw:
                        continue
                    seen_total_for_kw.add(sig)
                    total += int(b.get("closing_balance", 0) or 0)
                    break
    return total


def _summarize_pl_balances(balances):
    """P/L balances から主要科目を抽出。
    freee の trial_pl は account_category_name に「売上高」「売上原価」「販売管理費」等の集計行を含む。
    集計行を優先し、無ければ親カテゴリで合算する。"""
    def _by_cat(keywords, exact=False):
        total = 0
        for b in balances:
            name = b.get("account_category_name") or b.get("parent_account_category_name") or ""
            for kw in keywords:
                if exact:
                    if name == kw:
                        total += int(b.get("closing_balance", 0) or 0)
                        break
                else:
                    if kw and kw in name:
                        total += int(b.get("closing_balance", 0) or 0)
                        break
        return total

    # まず集計行 (hierarchy 高い行) を試す
    def _category_total(cat_name):
        for b in balances:
            n = b.get("account_category_name") or b.get("parent_account_category_name") or ""
            if n == cat_name and b.get("closing_balance") is not None:
                return int(b.get("closing_balance") or 0)
        return None

    revenue = _category_total("売上高")
    if revenue is None:
        revenue = _by_cat(["売上高", "営業収益"])

    cogs = _category_total("売上原価")
    if cogs is None:
        cogs = _by_cat(["売上原価", "原価"])

    sga = _category_total("販売管理費")
    if sga is None:
        sga = _by_cat(["販管費", "販売管理費", "販売費及び一般管理費", "販売費"])

    non_op_rev = _category_total("営業外収益") or _by_cat(["営業外収益"])
    non_op_exp = _category_total("営業外費用") or _by_cat(["営業外費用"])
    extra_rev = _category_total("特別利益") or _by_cat(["特別利益"])
    extra_exp = _category_total("特別損失") or _by_cat(["特別損失"])
    corp_tax = _by_cat(["法人税"])

    gross = revenue - cogs
    op = gross - sga
    ord_ = op + non_op_rev - non_op_exp
    pretax = ord_ + extra_rev - extra_exp
    net = pretax - corp_tax
    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross,
        "sga": sga,
        "operating_profit": op,
        "non_operating_income": non_op_rev,
        "non_operating_expense": non_op_exp,
        "ordinary_profit": ord_,
        "extraordinary_income": extra_rev,
        "extraordinary_loss": extra_exp,
        "pretax_profit": pretax,
        "corporate_tax": corp_tax,
        "net_profit": net,
    }


@app.route("/api/pl-monthly", methods=["GET"])
def api_pl_monthly():
    """月次P/L (直近12ヶ月分)"""
    if not _real_freee():
        return jsonify({"source": "mock", "data": mock_data.generate_mock_pl_monthly()})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        months = int(request.args.get("months", "12"))
        raw = cache.get_or_set(
            f"pl_monthly_{cid}_{months}",
            lambda: freee_client.get_trial_pl_monthly(cid, months=months),
            ttl=600,
        )
        rows = []
        for m in raw:
            summary = _summarize_pl_balances(m.get("balances") or [])
            summary["year_month"] = m["year_month"]
            rows.append(summary)
        return jsonify({"source": "freee", "data": rows})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": f"取得失敗: {e}", "data": None})


# ========================================================
# P/L 事業計画（CF逆算）
# ========================================================

def _build_plan_pl(months_ahead: int = 12) -> dict:
    """入金/支払予測 + 借入金 + 給与から、税抜会計で月次P/L事業計画を逆算する。

    考え方:
      - 入金予測の future アイテム: issue_date(発生月=売上計上月) に税抜売上として計上
      - 支払予測の future アイテム: issue_date を発生月として計上
        - extra item で name に「給与」を含めば「給与」科目、それ以外は「販管費・原価」
      - 借入金: 各月の利息 → 営業外費用、元金返済はP/Lには影響しない
      - 法人税等: 営業利益(暫定) × 30% を概算
    """
    today = date.today()
    # 月リスト (今月から months_ahead 月分)
    months_list = []
    cy, cm = today.year, today.month
    for _ in range(months_ahead):
        months_list.append(f"{cy}-{cm:02d}")
        cm += 1
        if cm > 12:
            cm = 1; cy += 1

    # 初期化
    init = lambda: {ym: 0 for ym in months_list}
    revenue_excl = init()           # 売上高(税抜)
    revenue_tax = init()             # 仮受消費税
    sga_excl = init()                # 販管費(税抜、給与除く)
    sga_tax = init()                 # 仮払消費税
    salary = init()                  # 給与
    interest = init()                # 支払利息

    cid = None
    if _real_freee():
        try:
            cid = freee_client.get_default_company_id()
        except Exception:
            cid = None

    overrides = storage.load_forecast_overrides()
    expense_overrides = _ensure_social_insurance_in_overrides(_ensure_salary_in_overrides(overrides))

    # 入金予測
    income_patterns = []
    if cid:
        try:
            inc = freee_client.fetch_payment_forecast(cid, deal_type="income",
                                                      months_ahead=months_ahead,
                                                      overrides=overrides)
            income_patterns = inc.get("patterns", [])
        except freee_client.FreeeAPIError:
            pass
    for p in income_patterns:
        rate = float(p.get("tax_rate", 10)) / 100.0
        for f in p.get("future", []):
            try:
                d = date.fromisoformat(f["issue_date"])
            except Exception:
                continue
            ym = d.strftime("%Y-%m")
            if ym not in revenue_excl:
                continue
            amt = int(f.get("amount", 0))
            excl = int(round(amt / (1 + rate))) if rate > 0 else amt
            tax_part = amt - excl
            revenue_excl[ym] += excl
            revenue_tax[ym] += tax_part

    # 支払予測
    expense_patterns = []
    if cid:
        try:
            exp = freee_client.fetch_payment_forecast(cid, deal_type="expense",
                                                      months_ahead=months_ahead,
                                                      overrides=expense_overrides)
            expense_patterns = exp.get("patterns", [])
        except freee_client.FreeeAPIError:
            pass
    for p in expense_patterns:
        rate = float(p.get("tax_rate", 10)) / 100.0
        is_salary = ("給与" in (p.get("partner") or "")) or ("給料" in (p.get("partner") or ""))
        for f in p.get("future", []):
            try:
                d = date.fromisoformat(f["issue_date"])
            except Exception:
                continue
            ym = d.strftime("%Y-%m")
            if ym not in sga_excl:
                continue
            amt = int(f.get("amount", 0))
            if is_salary:
                # 給与は消費税対象外
                salary[ym] += amt
            else:
                excl = int(round(amt / (1 + rate))) if rate > 0 else amt
                tax_part = amt - excl
                sga_excl[ym] += excl
                sga_tax[ym] += tax_part

    # 借入金利息
    try:
        loans = storage.load_loans()
        loan_sched = loans_module.aggregate_loans(loans, months_list)
        for ym, v in loan_sched.items():
            interest[ym] += int(v.get("interest", 0))
    except Exception:
        pass

    # 月次集計と税金概算
    rows = []
    cum_op_profit = 0
    cum_revenue_tax = 0
    cum_sga_tax = 0
    for ym in months_list:
        rev = revenue_excl[ym]
        sga = sga_excl[ym]
        sal = salary[ym]
        intr = interest[ym]
        op = rev - sga - sal
        ord_ = op - intr
        pretax = ord_
        corp_tax = int(max(0, pretax) * 0.30)  # 実効税率約30%概算
        net = pretax - corp_tax
        cum_op_profit += op
        cum_revenue_tax += revenue_tax[ym]
        cum_sga_tax += sga_tax[ym]
        rows.append({
            "year_month": ym,
            "revenue": rev,
            "sga": sga,
            "salary": sal,
            "operating_profit": op,
            "interest": intr,
            "ordinary_profit": ord_,
            "pretax_profit": pretax,
            "corporate_tax_estimate": corp_tax,
            "net_profit": net,
            "consumption_tax_received": revenue_tax[ym],
            "consumption_tax_paid": sga_tax[ym],
        })

    return {
        "months": rows,
        "summary": {
            "total_revenue": sum(r["revenue"] for r in rows),
            "total_sga": sum(r["sga"] for r in rows),
            "total_salary": sum(r["salary"] for r in rows),
            "total_operating_profit": sum(r["operating_profit"] for r in rows),
            "total_ordinary_profit": sum(r["ordinary_profit"] for r in rows),
            "total_pretax_profit": sum(r["pretax_profit"] for r in rows),
            "total_corporate_tax_estimate": sum(r["corporate_tax_estimate"] for r in rows),
            "total_net_profit": sum(r["net_profit"] for r in rows),
            "total_consumption_tax_received": cum_revenue_tax,
            "total_consumption_tax_paid": cum_sga_tax,
            "net_consumption_tax": cum_revenue_tax - cum_sga_tax,
        },
    }


@app.route("/api/pl-plan", methods=["GET"])
def api_pl_plan():
    """事業計画P/L (CF逆算)"""
    try:
        months = int(request.args.get("months", "12"))
    except (TypeError, ValueError):
        months = 12
    data = cache.get_or_set(
        f"pl_plan_{months}",
        lambda: _build_plan_pl(months_ahead=months),
        ttl=600,
    )
    src = "freee" if _real_freee() else "empty"
    return jsonify({"source": src, "data": data})


@app.route("/api/trial-bs", methods=["GET"])
def api_trial_bs():
    """貸借対照表"""
    if not _real_freee():
        bs = mock_data.generate_mock_bs_summary()
        balances = [
            {"account_item_name": "現預金", "account_category_name": "流動資産", "closing_balance": bs["cash"], "hierarchy_level": 2},
            {"account_item_name": "売掛金", "account_category_name": "流動資産", "closing_balance": bs["accounts_receivable"], "hierarchy_level": 2},
            {"account_item_name": "棚卸資産", "account_category_name": "流動資産", "closing_balance": bs["inventory"], "hierarchy_level": 2},
            {"account_item_name": "その他流動資産", "account_category_name": "流動資産", "closing_balance": bs["other_current_assets"], "hierarchy_level": 2},
            {"account_item_name": "流動資産合計", "account_category_name": "流動資産", "closing_balance": bs["current_assets"], "hierarchy_level": 1, "total_line": True},
            {"account_item_name": "有形固定資産", "account_category_name": "固定資産", "closing_balance": bs["tangible_assets"], "hierarchy_level": 2},
            {"account_item_name": "無形固定資産", "account_category_name": "固定資産", "closing_balance": bs["intangible_assets"], "hierarchy_level": 2},
            {"account_item_name": "投資その他", "account_category_name": "固定資産", "closing_balance": bs["investments"], "hierarchy_level": 2},
            {"account_item_name": "固定資産合計", "account_category_name": "固定資産", "closing_balance": bs["fixed_assets"], "hierarchy_level": 1, "total_line": True},
            {"account_item_name": "資産合計", "account_category_name": "資産", "closing_balance": bs["total_assets"], "hierarchy_level": 0, "total_line": True},
            {"account_item_name": "買掛金", "account_category_name": "流動負債", "closing_balance": bs["accounts_payable"], "hierarchy_level": 2},
            {"account_item_name": "短期借入金", "account_category_name": "流動負債", "closing_balance": bs["short_term_loan"], "hierarchy_level": 2},
            {"account_item_name": "その他流動負債", "account_category_name": "流動負債", "closing_balance": bs["other_current_liabilities"], "hierarchy_level": 2},
            {"account_item_name": "流動負債合計", "account_category_name": "流動負債", "closing_balance": bs["current_liabilities"], "hierarchy_level": 1, "total_line": True},
            {"account_item_name": "長期借入金", "account_category_name": "固定負債", "closing_balance": bs["long_term_loan"], "hierarchy_level": 2},
            {"account_item_name": "その他固定負債", "account_category_name": "固定負債", "closing_balance": bs["other_fixed_liabilities"], "hierarchy_level": 2},
            {"account_item_name": "固定負債合計", "account_category_name": "固定負債", "closing_balance": bs["fixed_liabilities"], "hierarchy_level": 1, "total_line": True},
            {"account_item_name": "負債合計", "account_category_name": "負債", "closing_balance": bs["total_liabilities"], "hierarchy_level": 0, "total_line": True},
            {"account_item_name": "資本金", "account_category_name": "純資産", "closing_balance": bs["capital"], "hierarchy_level": 2},
            {"account_item_name": "資本剰余金", "account_category_name": "純資産", "closing_balance": bs["capital_surplus"], "hierarchy_level": 2},
            {"account_item_name": "利益剰余金", "account_category_name": "純資産", "closing_balance": bs["retained_earnings"], "hierarchy_level": 2},
            {"account_item_name": "純資産合計", "account_category_name": "純資産", "closing_balance": bs["net_assets"], "hierarchy_level": 0, "total_line": True},
        ]
        return jsonify({"source": "mock", "data": {"balances": balances, "fiscal_year": date.today().year, "end_month": 3}})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        fy = request.args.get("fiscal_year")
        kwargs = {}
        if fy:
            kwargs["fiscal_year"] = int(fy)
        em = request.args.get("end_month")
        if em: kwargs["end_month"] = int(em)
        data = freee_client.get_trial_bs(cid, **kwargs)
        return jsonify({"source": "freee", "data": data})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": f"取得失敗: {e}", "data": None})


@app.route("/api/company-info", methods=["GET"])
def api_company_info():
    """事業所詳細 (決算月、社名など)"""
    if not _real_freee():
        return jsonify({"source": "mock", "data": {
            "id": mock_data.DEMO_COMPANY_ID,
            "name": mock_data.DEMO_COMPANY_NAME,
            "display_name": mock_data.DEMO_COMPANY_NAME,
            "fiscal_year_start_month": 4,
        }})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        info = freee_client.get_company_detail(cid)
        return jsonify({"source": "freee", "data": info})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": str(e), "data": None})


@app.route("/api/forecast-overrides", methods=["GET"])
def api_get_forecast_overrides():
    """予測編集内容を取得"""
    return jsonify(storage.load_forecast_overrides())


@app.route("/api/forecast-overrides", methods=["PUT"])
def api_put_forecast_overrides():
    """予測編集内容を保存"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400
    # 構造を整える
    cleaned = {
        "income": payload.get("income", {}) if isinstance(payload.get("income"), dict) else {},
        "expense": payload.get("expense", {}) if isinstance(payload.get("expense"), dict) else {},
        "extra_items": payload.get("extra_items", []) if isinstance(payload.get("extra_items"), list) else [],
    }
    storage.save_forecast_overrides(cleaned)
    # 予測関連キャッシュを無効化
    cache.invalidate("income_forecast_")
    cache.invalidate("expense_forecast_")
    cache.invalidate("daily_forecast")
    cache.invalidate("tax_calendar")
    cache.invalidate("pl_plan")
    return jsonify(cleaned)


def _ensure_salary_in_overrides(overrides: dict) -> dict:
    """支払予測に給与項目を自動追加（無ければ）"""
    extras = overrides.get("extra_items", [])
    has_salary = any(item.get("name", "").startswith("給与") and item.get("type") == "expense" for item in extras)
    if not has_salary and _real_freee():
        try:
            # 直近月の給与から自動推定
            rows = freee_client.hr_fetch_payroll_history(months_back=3)
            recent = [r for r in rows if r.get("gross_salary", 0) > 0 and not r.get("is_bonus_month")]
            if recent:
                avg = sum(r["gross_salary"] for r in recent) // len(recent)
                extras = list(extras) + [{
                    "id": "salary_auto",
                    "name": "給与（自動推定）",
                    "type": "expense",
                    "frequency_months": 1,
                    "close_day": 31,
                    "payment_term_days": 0,
                    # ★ デフォルトサイト: 翌月末 (御社の支払サイトに合わせる)
                    "payment_offset_months": 1,
                    "payment_day": 31,
                    "avg_amount": avg,
                }]
                overrides = {**overrides, "extra_items": extras}
        except Exception:
            pass
    return overrides


def _ensure_social_insurance_in_overrides(overrides: dict) -> dict:
    """支払予測に「社会保険料（会社負担・確定）」項目を自動追加。
    過去の給与明細から確定済の会社負担社保を月別に取得し、monthly_overrides に設定。
    例: 4月稼働分の社保(¥XX,XXX) が確定 → 5月末払い予測に確定値として表示。
    """
    extras = overrides.get("extra_items", [])
    has_si = any(item.get("name", "").startswith("社会保険料") and item.get("type") == "expense"
                 for item in extras)
    if not has_si and _real_freee():
        try:
            rows = freee_client.hr_fetch_payroll_history(months_back=12)
            # 確定月の会社負担社保を {対象月YM: 金額} で集約
            # 注意: rows[i].year_month = 給与の対象月 (稼働月)
            #       社保納付月 = 稼働月 + 1ヶ月 (翌月末)
            si_by_work_month: dict = {}
            for r in rows:
                if r.get("is_bonus_month"):
                    continue
                ym = r.get("year_month")
                si = int(r.get("social_insurance_employer", 0) or 0)
                if ym and si > 0:
                    si_by_work_month[ym] = si
            if not si_by_work_month:
                return overrides
            # 平均(将来月のデフォルト値)
            avg = sum(si_by_work_month.values()) // max(1, len(si_by_work_month))
            # monthly_overrides は issue_date のYMをキーとする
            # 稼働月の月末を issue_date とし、翌月末を支払日とすれば
            # issue_date YM = 稼働月YM そのまま使える
            monthly_overrides = dict(si_by_work_month)
            extras = list(extras) + [{
                "id": "social_insurance_auto",
                "name": "社会保険料（会社負担・確定）",
                "type": "expense",
                "frequency_months": 1,
                "close_day": 31,         # 月末締め
                "payment_term_days": 30,  # 翌月末払い (旧式)
                "payment_offset_months": 1,  # 翌月
                "payment_day": 31,        # 末日
                "avg_amount": avg,
                "monthly_overrides": monthly_overrides,
                "tax_rate": 0,  # 社保は消費税対象外
            }]
            overrides = {**overrides, "extra_items": extras}
        except Exception:
            pass
    return overrides


@app.route("/api/payment-forecast", methods=["GET"])
def api_payment_forecast():
    """入金予測（売掛先別・パターン分析・編集適用）"""
    if not _real_freee():
        months = int(request.args.get("months", "12"))
        return jsonify({"source": "mock",
                        "data": mock_data.generate_mock_payment_forecast("income", months)})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        months = int(request.args.get("months", "12"))
        overrides = storage.load_forecast_overrides()
        # キャッシュキーは overrides の中身も含めてハッシュ
        import hashlib, json as _json
        ov_hash = hashlib.md5(_json.dumps(overrides, sort_keys=True).encode()).hexdigest()[:8]
        data = cache.get_or_set(
            f"income_forecast_{cid}_{months}_{ov_hash}",
            lambda: freee_client.fetch_payment_forecast(cid, deal_type="income", months_ahead=months, overrides=overrides),
            ttl=600,
        )
        return jsonify({"source": "freee", "data": data})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": f"取得失敗: {e}", "data": None})


@app.route("/api/expense-forecast", methods=["GET"])
def api_expense_forecast():
    """支払予測（買掛先別・パターン分析・給与組込・編集適用）"""
    if not _real_freee():
        months = int(request.args.get("months", "12"))
        return jsonify({"source": "mock",
                        "data": mock_data.generate_mock_payment_forecast("expense", months)})
    try:
        cid = freee_client.get_default_company_id()
        if not cid:
            return jsonify({"source": "empty", "data": None})
        months = int(request.args.get("months", "12"))
        overrides = storage.load_forecast_overrides()
        overrides = _ensure_social_insurance_in_overrides(_ensure_salary_in_overrides(overrides))
        import hashlib, json as _json
        ov_hash = hashlib.md5(_json.dumps(overrides, sort_keys=True).encode()).hexdigest()[:8]
        data = cache.get_or_set(
            f"expense_forecast_{cid}_{months}_{ov_hash}",
            lambda: freee_client.fetch_payment_forecast(cid, deal_type="expense", months_ahead=months, overrides=overrides),
            ttl=600,
        )
        return jsonify({"source": "freee", "data": data})
    except freee_client.FreeeAPIError as e:
        return jsonify({"source": "empty", "warning": f"取得失敗: {e}", "data": None})


# ---------- Diagnostics ----------

def api_diagnostics_OLD_DISABLED():
    """旧版診断: 大量API呼出で激遅のため無効化。下に新版あり。"""
    from datetime import date as _date
    results = []

    def _check(label: str, fn):
        try:
            v = fn()
            return {"label": label, "ok": True, "detail": str(v)[:200]}
        except freee_client.FreeeAPIError as e:
            return {"label": label, "ok": False, "detail": str(e)[:300]}
        except Exception as e:
            return {"label": label, "ok": False, "detail": f"{type(e).__name__}: {str(e)[:200]}"}

    s = get_settings()
    results.append({"label": "MOCK_MODE", "ok": True, "detail": str(s.mock_mode)})
    results.append({"label": ".envに認証情報あり", "ok": s.has_freee_credentials, "detail": "Client ID/Secretが設定済み" if s.has_freee_credentials else "Client ID/Secretが未設定"})
    results.append({"label": "freee連携トークン保存済み", "ok": auth.is_connected(), "detail": "保存済み" if auth.is_connected() else "未保存(freeeと連携してください)"})

    if not auth.is_connected():
        return jsonify({"results": results})

    # --- 会計API
    results.append(_check("会計: /api/1/companies (事業所一覧)",
                          lambda: f"{len(freee_client.get_companies())}件"))

    cid = None
    try:
        cid = freee_client.get_default_company_id()
    except Exception:
        pass

    if cid:
        results.append({"label": "会計: company_id", "ok": True, "detail": str(cid)})
        results.append(_check("会計: /api/1/walletables (口座)",
                              lambda: f"{len(freee_client.get_walletables(cid))}口座"))
        today = _date.today()
        start = today.replace(day=1)
        for _ in range(2):
            start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
        results.append(_check(f"会計: /api/1/deals (取引, 過去2ヶ月)",
                              lambda: f"{len(freee_client.get_deals(cid, start, today))}件"))
        results.append(_check("会計: /api/1/partners (取引先)",
                              lambda: f"{len(freee_client.get_partners(cid))}件"))

    # --- 人事労務API: 複数エンドポイントで疎通テスト
    results.append(_check("人事労務: /api/v1/users/me (ログインユーザー)",
                          lambda: f"OK ({len(freee_client._get('/api/v1/users/me', hr=True).get('companies', []))} companies)"))
    results.append(_check("人事労務: hr_get_companies (users/me 経由)",
                          lambda: f"{len(freee_client.hr_get_companies())}件"))

    hr_cid = None
    try:
        hr_cid = freee_client.hr_get_default_company_id()
    except Exception:
        pass

    if hr_cid:
        results.append({"label": "人事労務: company_id", "ok": True, "detail": str(hr_cid)})
        # 全従業員: /api/v1/companies/{id}/employees
        results.append(_check(f"人事労務: /companies/{hr_cid}/employees (全従業員)",
                              lambda: f"{len(freee_client.hr_get_employees_all(hr_cid))}名"))
        today = _date.today()
        # 先月で試す
        last_m_end = today.replace(day=1) - timedelta(days=1)
        y, m = last_m_end.year, last_m_end.month
        results.append(_check(f"人事労務: /employees?company_id={hr_cid}&year={y}&month={m}",
                              lambda: f"{len(freee_client.hr_get_employees(hr_cid, y, m))}名"))
        # 給与明細: 複数のURLパターンを試行
        try:
            emps = freee_client.hr_get_employees(hr_cid, y, m)
            if emps:
                first_id = emps[0].get("id")
                # 確認済みエンドポイント
                statements = freee_client.hr_get_payroll_statements_month(hr_cid, y, m)
                results.append({"label": f"人事労務: /salaries/employee_payroll_statements ({y}/{m})",
                                "ok": True, "detail": f"{len(statements)}件取得"})

                # 1件目の完全JSON
                if statements:
                    first = statements[0]
                    import json as _json
                    pid = first.get("id")
                    eid = first.get("employee_id")
                    if pid:
                        try:
                            detail = freee_client.hr_get_payroll_statement_detail(pid, hr_cid)
                            results.append({"label": f"[診断用] 給与明細詳細 (id={pid}) の全フィールド",
                                            "ok": True,
                                            "detail": _json.dumps(detail, ensure_ascii=False)[:5000]})
                        except Exception as e:
                            results.append({"label": "給与明細詳細失敗", "ok": False, "detail": str(e)[:200]})
                    if eid:
                        # 従業員詳細 (基本給・固定残業・通勤手当を探す)
                        try:
                            emp_detail = freee_client._get(
                                f"/api/v1/employees/{eid}",
                                params={"company_id": hr_cid, "year": y, "month": m},
                                hr=True)
                            results.append({"label": f"[診断用] 従業員詳細 (id={eid}) の全フィールド",
                                            "ok": True,
                                            "detail": _json.dumps(emp_detail, ensure_ascii=False)[:5000]})
                        except Exception as e:
                            results.append({"label": "従業員詳細失敗", "ok": False, "detail": str(e)[:200]})
                        # 専用エンドポイント: basic_pay_rule (月給) と allowances (固定残業・手当)
                        for path in [
                            f"/api/v1/employees/{eid}/basic_pay_rule",
                            f"/api/v1/employees/{eid}/allowances",
                            f"/api/v1/employees/{eid}/commute_allowance",
                            f"/api/v1/employees/{eid}/commute_allowances",
                            f"/api/v1/employees/{eid}/commute_pay_rule",
                            f"/api/v1/employees/{eid}/work_record_rule",
                        ]:
                            try:
                                d = freee_client._get(path, params={"company_id": hr_cid, "year": y, "month": m}, hr=True)
                                results.append({"label": f"HR専用 {path}", "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:3000]})
                            except Exception as e:
                                results.append({"label": f"HR専用 {path}", "ok": False,
                                                "detail": str(e)[:200]})

                # ★ 部門/役職マスタの疎通テスト
                for path, params in [
                    (f"/api/v1/companies/{hr_cid}/sections", None),
                    ("/api/v1/sections", {"company_id": hr_cid}),
                    (f"/api/v1/companies/{hr_cid}/positions", None),
                    ("/api/v1/positions", {"company_id": hr_cid}),
                ]:
                    try:
                        d = freee_client._get(path, params=params, hr=True)
                        results.append({"label": f"マスタ {path}", "ok": True,
                                        "detail": _json.dumps(d, ensure_ascii=False)[:2000]})
                    except Exception as e:
                        results.append({"label": f"マスタ {path}", "ok": False,
                                        "detail": str(e)[:200]})

                # ★ 全従業員(LIST)の最初の1名の全フィールド
                all_emps = []
                try:
                    all_emps = freee_client.hr_get_employees_all(hr_cid)
                    if all_emps:
                        first_full = all_emps[0]
                        results.append({"label": f"[診断] 全従業員LIST 1名目の全フィールド",
                                        "ok": True,
                                        "detail": _json.dumps(first_full, ensure_ascii=False)[:3000]})
                except Exception as e:
                    results.append({"label": "全従業員LIST取得失敗", "ok": False, "detail": str(e)[:200]})

                # ★★ 重要: 複数従業員の basic_pay_rule 全フィールドを比較
                # (役員/正社員/新入社員で field set が違う可能性を確認)
                try:
                    targets = all_emps[:5] if all_emps else []
                    for emp_obj in targets:
                        eid2 = emp_obj.get("id")
                        nm2 = emp_obj.get("display_name") or emp_obj.get("num")
                        entry2 = emp_obj.get("entry_date", "")
                        if not eid2:
                            continue
                        # 基準月: 入社月か先月の遅い方
                        ref_y, ref_m = y, m
                        try:
                            ed2 = _date.fromisoformat(entry2) if entry2 else None
                            if ed2 and (ed2.year, ed2.month) > (y, m):
                                ref_y, ref_m = ed2.year, ed2.month
                        except Exception:
                            pass
                        try:
                            bp = freee_client._get(
                                f"/api/v1/employees/{eid2}/basic_pay_rule",
                                params={"company_id": hr_cid, "year": ref_y, "month": ref_m},
                                hr=True,
                            )
                            results.append({
                                "label": f"★ basic_pay_rule [{nm2}] (基準月{ref_y}/{ref_m}) 全フィールド",
                                "ok": True,
                                "detail": _json.dumps(bp, ensure_ascii=False)[:2500],
                            })
                        except Exception as e:
                            results.append({"label": f"basic_pay_rule [{nm2}] 失敗",
                                            "ok": False, "detail": str(e)[:200]})
                except Exception as e:
                    results.append({"label": "複数従業員 basic_pay_rule 診断失敗",
                                    "ok": False, "detail": str(e)[:200]})

                # ★★ 通勤手当エンドポイント候補を網羅試行 (正社員1名で試す)
                try:
                    # ★ 役員以外を正しく選ぶ: employment_type は profile_rule の中
                    # 年月別 LIST を一回だけ取得して使い回す
                    test_emp = None
                    try:
                        ym_emps_t = freee_client.hr_get_employees(hr_cid, y, m)
                    except Exception:
                        ym_emps_t = []
                    ym_data_by_id = {em.get("id"): em for em in ym_emps_t if em.get("id")}
                    for emp_obj in (all_emps or []):
                        eid_t = emp_obj.get("id")
                        ym_data = ym_data_by_id.get(eid_t, {})
                        prof = ym_data.get("profile_rule") if isinstance(ym_data.get("profile_rule"), dict) else {}
                        et = prof.get("employment_type") or ym_data.get("employment_type") or ""
                        # 役員以外を選択
                        if et not in ("board-member", "board_member"):
                            test_emp = emp_obj
                            break
                    if test_emp:
                        eid_t = test_emp.get("id")
                        nm_t = test_emp.get("display_name") or test_emp.get("num")
                        entry_t = test_emp.get("entry_date", "")
                        # テスト対象の雇用形態を確認用に出力
                        test_ym = ym_data_by_id.get(eid_t, {})
                        test_prof = test_ym.get("profile_rule") if isinstance(test_ym.get("profile_rule"), dict) else {}
                        test_et = test_prof.get("employment_type") or "?"
                        results.append({
                            "label": f"★★★ 通勤/残業候補のテスト対象",
                            "ok": True,
                            "detail": f"氏名={nm_t} / 雇用形態={test_et} / employee_id={eid_t} / 入社日={entry_t}",
                        })
                        ref_y, ref_m = y, m
                        try:
                            ed3 = _date.fromisoformat(entry_t) if entry_t else None
                            if ed3 and (ed3.year, ed3.month) > (y, m):
                                ref_y, ref_m = ed3.year, ed3.month
                        except Exception:
                            pass
                        commute_endpoints = [
                            f"/api/v1/employees/{eid_t}/commute_pay_rule",
                            f"/api/v1/employees/{eid_t}/commute_allowance",
                            f"/api/v1/employees/{eid_t}/commute_allowances",
                            f"/api/v1/employees/{eid_t}/commute_pay_rules",
                            f"/api/v1/employees/{eid_t}/employee_commute_allowance",
                            f"/api/v1/employees/{eid_t}/employee_commute_allowances",
                            f"/api/v1/employees/{eid_t}/employee_commute_pay_rule",
                            f"/api/v1/employees/{eid_t}/transportation_allowance",
                            f"/api/v1/employees/{eid_t}/transportation_pay_rule",
                            f"/api/v1/employee_commute_allowances/{eid_t}",
                            f"/api/v1/employee_commute_pay_rules/{eid_t}",
                        ]
                        for path in commute_endpoints:
                            try:
                                d = freee_client._get(path, params={"company_id": hr_cid, "year": ref_y, "month": ref_m}, hr=True)
                                results.append({"label": f"★通勤候補 {path} [{nm_t}]",
                                                "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:1500]})
                            except Exception as e:
                                results.append({"label": f"通勤候補 {path}",
                                                "ok": False,
                                                "detail": str(e)[:150]})
                        # 固定残業代の追加候補
                        overtime_endpoints = [
                            f"/api/v1/employees/{eid_t}/overtime_pay_rule",
                            f"/api/v1/employees/{eid_t}/fixed_overtime_pay_rule",
                            f"/api/v1/employees/{eid_t}/employee_overtime_pay_rule",
                            f"/api/v1/employees/{eid_t}/allowances",
                            f"/api/v1/employees/{eid_t}/employee_allowances",
                        ]
                        for path in overtime_endpoints:
                            try:
                                d = freee_client._get(path, params={"company_id": hr_cid, "year": ref_y, "month": ref_m}, hr=True)
                                results.append({"label": f"★残業/手当候補 {path} [{nm_t}]",
                                                "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:1500]})
                            except Exception as e:
                                results.append({"label": f"残業/手当候補 {path}",
                                                "ok": False,
                                                "detail": str(e)[:150]})

                        # ★★★ 追加: 未試行URLパターン (employee_settings系/payment_rule系)
                        extra_endpoints = [
                            # 設定・ルール系
                            f"/api/v1/employees/{eid_t}/payment_settings",
                            f"/api/v1/employees/{eid_t}/payment_rule",
                            f"/api/v1/employees/{eid_t}/payment_rules",
                            f"/api/v1/employees/{eid_t}/pay_setting",
                            f"/api/v1/employees/{eid_t}/payroll",
                            f"/api/v1/employees/{eid_t}/payroll_rules",
                            f"/api/v1/employees/{eid_t}/salary",
                            f"/api/v1/employees/{eid_t}/salary_rule",
                            f"/api/v1/employees/{eid_t}/salary_settings",
                            # 手当系の別パターン
                            f"/api/v1/employees/{eid_t}/extra_pay",
                            f"/api/v1/employees/{eid_t}/extra_pays",
                            f"/api/v1/employees/{eid_t}/extra_allowances",
                            f"/api/v1/employees/{eid_t}/employee_extra_pay_rules",
                            f"/api/v1/employees/{eid_t}/standard_pays",
                            # 給与情報の総合エンドポイント
                            f"/api/v1/employees/{eid_t}/employee_payment_info",
                            f"/api/v1/employees/{eid_t}/payment_info",
                            f"/api/v1/employees/{eid_t}/work_record_summaries",
                            # company配下
                            f"/api/v1/companies/{hr_cid}/employees/{eid_t}/basic_pay_rule",
                            f"/api/v1/companies/{hr_cid}/employees/{eid_t}/allowances",
                            f"/api/v1/companies/{hr_cid}/employees/{eid_t}/commute_allowance",
                        ]
                        for path in extra_endpoints:
                            try:
                                d = freee_client._get(path, params={"company_id": hr_cid, "year": ref_y, "month": ref_m}, hr=True)
                                results.append({"label": f"★★追加URL候補 {path} [{nm_t}]",
                                                "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:1500]})
                            except Exception as e:
                                results.append({"label": f"追加URL候補 {path}",
                                                "ok": False,
                                                "detail": str(e)[:80]})

                        # ★★ basic_pay_rule をパラメータ無し/異なる組合せで再試行
                        param_variants = [
                            ("基本: company_idのみ", {"company_id": hr_cid}),
                            ("基本: パラメータ無し", None),
                            ("基本: include=allowances", {"company_id": hr_cid, "include": "allowances"}),
                            ("基本: with=full", {"company_id": hr_cid, "with": "full"}),
                            ("基本: with_allowances=true", {"company_id": hr_cid, "with_allowances": "true"}),
                            ("基本: expand=*", {"company_id": hr_cid, "expand": "*"}),
                        ]
                        for label, params in param_variants:
                            try:
                                d = freee_client._get(
                                    f"/api/v1/employees/{eid_t}/basic_pay_rule",
                                    params=params, hr=True,
                                )
                                results.append({
                                    "label": f"★ basic_pay_rule {label} [{nm_t}]",
                                    "ok": True,
                                    "detail": _json.dumps(d, ensure_ascii=False)[:1500],
                                })
                            except Exception as e:
                                results.append({"label": f"basic_pay_rule {label}", "ok": False,
                                                "detail": str(e)[:80]})

                        # ★★★★ 第3弾: リソース型/通勤定期/会社設定/v2系 まだ未試行のURL
                        third_wave_endpoints = [
                            # 通勤関連の追加パターン
                            f"/api/v1/employees/{eid_t}/commute_path",
                            f"/api/v1/employees/{eid_t}/commute_paths",
                            f"/api/v1/employees/{eid_t}/commute_pass",
                            f"/api/v1/employees/{eid_t}/commute_passes",
                            f"/api/v1/employees/{eid_t}/commute_route",
                            f"/api/v1/employees/{eid_t}/commute_routes",
                            f"/api/v1/employees/{eid_t}/transportation_expense",
                            f"/api/v1/employees/{eid_t}/transportation_expenses",
                            f"/api/v1/employees/{eid_t}/transit_pass",
                            # 標準給与・割増賃金関連
                            f"/api/v1/employees/{eid_t}/standard_pay",
                            f"/api/v1/employees/{eid_t}/standard_pay_rule",
                            f"/api/v1/employees/{eid_t}/standard_remuneration",
                            f"/api/v1/employees/{eid_t}/overtime_rate",
                            f"/api/v1/employees/{eid_t}/overtime_rates",
                            f"/api/v1/employees/{eid_t}/work_time_rule",
                            f"/api/v1/employees/{eid_t}/attendance_rule",
                            f"/api/v1/employees/{eid_t}/job_role",
                            f"/api/v1/employees/{eid_t}/job_title",
                            f"/api/v1/employees/{eid_t}/employee_pay_settings",
                            f"/api/v1/employees/{eid_t}/employee_payment_settings",
                            # OpenAPI/Swagger 探索
                            "/api/v1",
                            "/api/v1/swagger.json",
                            "/api/v1/openapi.json",
                            # 会社レベル設定
                            f"/api/v1/companies/{hr_cid}/overtime_settings",
                            f"/api/v1/companies/{hr_cid}/allowance_settings",
                            f"/api/v1/companies/{hr_cid}/payment_settings",
                            f"/api/v1/companies/{hr_cid}/payroll_settings",
                            f"/api/v1/companies/{hr_cid}/work_record_summaries",
                            f"/api/v1/companies/{hr_cid}/employee_payment_periods",
                            # v2/v3 系
                            f"/api/v2/employees/{eid_t}/basic_pay_rule",
                            f"/api/v2/employees/{eid_t}",
                            # 単数形 (id埋め込み・複数形)
                            f"/api/v1/commute_pay_rules",
                            f"/api/v1/fixed_overtime_pays",
                            f"/api/v1/employee_commute_paths",
                            f"/api/v1/employee_overtime_pay_rates",
                            f"/api/v1/employee_allowance_rules",
                            f"/api/v1/employee_standard_pays",
                        ]
                        for path in third_wave_endpoints:
                            try:
                                # company_id だけ付ける（year/month はやめる）
                                p = {"company_id": hr_cid} if "v1" in path and "employees" not in path[-20:] else \
                                    {"company_id": hr_cid, "employee_id": eid_t} if "employees" not in path else \
                                    {"company_id": hr_cid, "year": ref_y, "month": ref_m}
                                d = freee_client._get(path, params=p, hr=True)
                                results.append({"label": f"★★★第3弾 {path} [{nm_t}]",
                                                "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:1500]})
                            except Exception as e:
                                results.append({"label": f"第3弾 {path}",
                                                "ok": False, "detail": str(e)[:80]})

                        # ★★★★★ 第4弾: X-Api-Version を変えて再試行
                        # 古いバージョン(2020-06-15)では公開されていないが、
                        # 新版では公開されているフィールドがある可能性
                        api_versions = [
                            None,           # ヘッダ無し
                            "2022-09-01",
                            "2023-01-01",
                            "2024-01-01",
                            "2025-01-01",
                        ]
                        for ver in api_versions:
                            ver_label = ver or "(無し)"
                            # basic_pay_rule を各バージョンで取得
                            try:
                                d = freee_client._get(
                                    f"/api/v1/employees/{eid_t}/basic_pay_rule",
                                    params={"company_id": hr_cid, "year": ref_y, "month": ref_m},
                                    hr=True, api_version=ver,
                                )
                                results.append({
                                    "label": f"★第4弾 X-Api-Version={ver_label} basic_pay_rule [{nm_t}]",
                                    "ok": True,
                                    "detail": _json.dumps(d, ensure_ascii=False)[:1500],
                                })
                            except Exception as e:
                                results.append({"label": f"第4弾 X-Api-Version={ver_label} basic_pay_rule",
                                                "ok": False, "detail": str(e)[:80]})
                            # 年月別LIST も各バージョンで取得 (basic_pay_rule の中身が変わるか)
                            try:
                                d = freee_client._get(
                                    "/api/v1/employees",
                                    params={"company_id": hr_cid, "year": ref_y, "month": ref_m, "limit": 1},
                                    hr=True, api_version=ver,
                                )
                                items = d.get("employees", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                                first_keys = sorted(items[0].keys()) if items else []
                                results.append({
                                    "label": f"★第4弾 X-Api-Version={ver_label} 年月別LIST 1名目キー",
                                    "ok": True,
                                    "detail": ", ".join(first_keys) if first_keys else "(空)",
                                })
                            except Exception as e:
                                results.append({"label": f"第4弾 X-Api-Version={ver_label} 年月別LIST",
                                                "ok": False, "detail": str(e)[:80]})
                            # commute_pay_rule も各バージョンで再試行
                            try:
                                d = freee_client._get(
                                    f"/api/v1/employees/{eid_t}/commute_pay_rule",
                                    params={"company_id": hr_cid, "year": ref_y, "month": ref_m},
                                    hr=True, api_version=ver,
                                )
                                results.append({
                                    "label": f"★第4弾 X-Api-Version={ver_label} commute_pay_rule [{nm_t}]",
                                    "ok": True,
                                    "detail": _json.dumps(d, ensure_ascii=False)[:1500],
                                })
                            except Exception as e:
                                results.append({"label": f"第4弾 X-Api-Version={ver_label} commute_pay_rule",
                                                "ok": False, "detail": str(e)[:60]})
                except Exception as e:
                    results.append({"label": "通勤/残業 候補診断失敗",
                                    "ok": False, "detail": str(e)[:200]})

                # ★ 年月別 LIST の最初の1名の全フィールド
                try:
                    ym_emps_full = freee_client.hr_get_employees(hr_cid, y, m)
                    if ym_emps_full:
                        results.append({"label": f"[診断] 年月別LIST({y}/{m}) 1名目の全フィールド",
                                        "ok": True,
                                        "detail": _json.dumps(ym_emps_full[0], ensure_ascii=False)[:5000]})
                        # キー一覧 (position_id/section_id 等が含まれるか確認用)
                        all_keys = sorted({k for em in ym_emps_full for k in em.keys()})
                        results.append({"label": "[診断] 年月別LIST に含まれる全キー",
                                        "ok": True,
                                        "detail": ", ".join(all_keys)})
                        # ★★ 年月別LIST 内の basic_pay_rule を全名分ダンプ
                        # → 個別フェッチとの差を確認
                        for em in ym_emps_full[:5]:
                            bpr = em.get("basic_pay_rule")
                            nm_x = em.get("display_name") or em.get("num") or "?"
                            results.append({
                                "label": f"★ 年月別LIST内 basic_pay_rule [{nm_x}]",
                                "ok": True,
                                "detail": _json.dumps(bpr, ensure_ascii=False)[:1500] if bpr is not None else "(null - データ無し)",
                            })
                except Exception as e:
                    results.append({"label": "年月別LIST取得失敗", "ok": False, "detail": str(e)[:200]})

                # ★ 役職紐付けエンドポイントの疎通
                try:
                    if ym_emps_full and ym_emps_full[0].get("id"):
                        eid_test = ym_emps_full[0]["id"]
                        for path in [
                            f"/api/v1/employees/{eid_test}/position",
                            f"/api/v1/employees/{eid_test}/positions",
                            f"/api/v1/employee_positions/{eid_test}",
                        ]:
                            try:
                                d = freee_client._get(path, params={"company_id": hr_cid, "year": y, "month": m}, hr=True)
                                results.append({"label": f"役職紐付け {path}", "ok": True,
                                                "detail": _json.dumps(d, ensure_ascii=False)[:1500]})
                            except Exception as e:
                                results.append({"label": f"役職紐付け {path}", "ok": False,
                                                "detail": str(e)[:200]})
                except Exception:
                    pass

                # ★ 全従業員の payments name 一覧（手当キーワード調整用）
                try:
                    name_counter: dict[str, int] = {}
                    sample_per_name: dict[str, str] = {}
                    for st in statements:
                        for pmt in (st.get("payments") or []):
                            if not isinstance(pmt, dict):
                                continue
                            nm = pmt.get("name") or ""
                            if not nm:
                                continue
                            amt = pmt.get("amount") or 0
                            name_counter[nm] = name_counter.get(nm, 0) + 1
                            if nm not in sample_per_name:
                                sample_per_name[nm] = f"{amt}"
                    sorted_names = sorted(name_counter.items(), key=lambda x: -x[1])
                    summary_lines = [f"{nm} ×{cnt} (例 ¥{sample_per_name.get(nm, '?')})" for nm, cnt in sorted_names]
                    results.append({
                        "label": f"★ payments の name 一覧 ({y}/{m}, 全{len(statements)}名分)",
                        "ok": True,
                        "detail": " / ".join(summary_lines) if summary_lines else "（payments が空）"
                    })
                except Exception as e:
                    results.append({"label": "payments name 集計失敗", "ok": False, "detail": str(e)[:200]})
            else:
                results.append({"label": "給与明細テスト", "ok": False, "detail": "在籍従業員0名"})
        except Exception as e:
            results.append({"label": "給与明細テスト", "ok": False, "detail": str(e)[:200]})

    return jsonify({"results": results})


# ---------- Diagnostics (slim parallel version) ----------

@app.route("/api/diagnostics", methods=["GET"])
def api_diagnostics_v2():
    """並列化＋スリム化版の診断。重要APIだけを最大10並列で実行。"""
    from datetime import date as _date
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import json as _json

    results = []
    s = get_settings()
    results.append({"label": "MOCK_MODE", "ok": True, "detail": str(s.mock_mode)})
    results.append({"label": ".envに認証情報あり", "ok": s.has_freee_credentials,
                    "detail": "OK" if s.has_freee_credentials else "未設定"})
    results.append({"label": "freee連携トークン保存済み", "ok": auth.is_connected(),
                    "detail": "OK" if auth.is_connected() else "未保存"})

    if not auth.is_connected():
        return jsonify({"results": results})

    # 基準月
    today = _date.today()
    last_m_end = today.replace(day=1) - timedelta(days=1)
    y, m = last_m_end.year, last_m_end.month

    # ---- 直列で実行 (依存あり): cid 取得 / 従業員一覧 / 年月別LIST ----
    cid = None
    hr_cid = None
    try:
        cid = freee_client.get_default_company_id()
    except Exception:
        pass
    try:
        hr_cid = freee_client.hr_get_default_company_id()
    except Exception:
        pass
    results.append({"label": "会計 company_id", "ok": cid is not None, "detail": str(cid)})
    results.append({"label": "人事労務 company_id", "ok": hr_cid is not None, "detail": str(hr_cid)})

    if not hr_cid:
        return jsonify({"results": results})

    # 全従業員 + 年月別LIST
    all_emps = []
    ym_emps = []
    try:
        all_emps = freee_client.hr_get_employees_all(hr_cid)
    except Exception as e:
        results.append({"label": "全従業員LIST", "ok": False, "detail": str(e)[:200]})
    try:
        ym_emps = freee_client.hr_get_employees(hr_cid, y, m)
    except Exception as e:
        results.append({"label": "年月別LIST", "ok": False, "detail": str(e)[:200]})

    results.append({"label": f"全従業員LIST", "ok": True, "detail": f"{len(all_emps)}名"})
    results.append({"label": f"年月別LIST({y}/{m})", "ok": True, "detail": f"{len(ym_emps)}名"})

    # ★★ 3種類のテスト対象を選定: 役員 / 正社員既存 / 正社員新入社員(未来日入社)
    ym_by_id = {em.get("id"): em for em in ym_emps if em.get("id")}
    test_targets: list = []  # [(emp, ref_y, ref_m, kind_label), ...]

    def _et_of(emp):
        eid = emp.get("id")
        if not eid:
            return ""
        ym = ym_by_id.get(eid, {})
        prof = ym.get("profile_rule") if isinstance(ym.get("profile_rule"), dict) else {}
        return prof.get("employment_type") or ""

    def _ref_of(emp):
        entry = emp.get("entry_date") or ""
        try:
            ed = _date.fromisoformat(entry) if entry else None
            if ed and (ed.year, ed.month) > (y, m):
                return (ed.year, ed.month)
        except Exception:
            pass
        return (y, m)

    # 役員1名
    for emp in all_emps:
        if _et_of(emp) in ("board-member", "board_member"):
            test_targets.append((emp, *_ref_of(emp), "役員"))
            break
    # 正社員既存(過去入社) 1名
    for emp in all_emps:
        et = _et_of(emp)
        if et and et not in ("board-member", "board_member"):
            entry = emp.get("entry_date") or ""
            try:
                ed = _date.fromisoformat(entry) if entry else None
                if ed and (ed.year, ed.month) <= (y, m):
                    test_targets.append((emp, *_ref_of(emp), "正社員(既存)"))
                    break
            except Exception:
                pass
    # 新入社員(未来入社含む) 1名
    for emp in all_emps:
        et = _et_of(emp)
        if et and et not in ("board-member", "board_member"):
            entry = emp.get("entry_date") or ""
            try:
                ed = _date.fromisoformat(entry) if entry else None
                if ed and (ed.year, ed.month) > (y, m - 2 if m > 2 else 1):
                    # 最近入社
                    test_targets.append((emp, *_ref_of(emp), "正社員(新入社員)"))
                    break
            except Exception:
                pass

    if not test_targets and all_emps:
        emp = all_emps[0]
        test_targets.append((emp, *_ref_of(emp), "fallback"))

    if not test_targets:
        results.append({"label": "テスト対象選定失敗", "ok": False, "detail": "従業員0名"})
        return jsonify({"results": results})

    # テスト対象一覧を表示
    for emp, ry, rm, kind in test_targets:
        results.append({
            "label": f"★★★ テスト対象 [{kind}]",
            "ok": True,
            "detail": f"氏名={emp.get('display_name') or emp.get('num')} / 雇用形態={_et_of(emp) or '?'} / id={emp.get('id')} / 入社日={emp.get('entry_date','')} / 基準月={ry}/{rm}",
        })

    # 1名目をデフォルトのテスト対象に
    test_emp, ref_y, ref_m, _kind = test_targets[0] if test_targets else (None, y, m, "")
    eid_t = test_emp.get("id") if test_emp else None
    nm_t = (test_emp.get("display_name") or test_emp.get("num") or "?") if test_emp else "?"
    test_et = _et_of(test_emp) if test_emp else "?"

    # 年月別LIST の全キー
    if ym_emps:
        all_keys = sorted({k for em in ym_emps for k in em.keys()})
        results.append({"label": "年月別LIST 全キー", "ok": True, "detail": ", ".join(all_keys)})

    # ---- 並列実行: 重要エンドポイントだけに絞る ----
    # 通勤手当 + 固定残業代 + 基本給 のテスト
    candidates = [
        ("基本給(従業員情報)", f"/api/v1/employees/{eid_t}/basic_pay_rule"),
        ("通勤手当(commute_pay_rule)", f"/api/v1/employees/{eid_t}/commute_pay_rule"),
        ("通勤手当(commute_allowance)", f"/api/v1/employees/{eid_t}/commute_allowance"),
        ("通勤手当(commute_allowances)", f"/api/v1/employees/{eid_t}/commute_allowances"),
        ("通勤手当(commute_pass)", f"/api/v1/employees/{eid_t}/commute_pass"),
        ("通勤手当(transportation)", f"/api/v1/employees/{eid_t}/transportation_allowance"),
        ("固定残業(overtime_pay_rule)", f"/api/v1/employees/{eid_t}/overtime_pay_rule"),
        ("固定残業(fixed_overtime)", f"/api/v1/employees/{eid_t}/fixed_overtime_pay_rule"),
        ("固定残業(allowances)", f"/api/v1/employees/{eid_t}/allowances"),
        ("勤怠ルール(work_record_rule)", f"/api/v1/employees/{eid_t}/work_record_rule"),
        ("雇用保険(employment_insurance)", f"/api/v1/employees/{eid_t}/employment_insurance_rule"),
        ("所得税(income_tax)", f"/api/v1/employees/{eid_t}/income_tax_rule"),
        ("住民税(resident_tax)", f"/api/v1/employees/{eid_t}/resident_tax_rule"),
        ("従業員詳細", f"/api/v1/employees/{eid_t}"),
    ]

    def _do_call(label_path):
        label, path = label_path
        try:
            d = freee_client._get(path,
                params={"company_id": hr_cid, "year": ref_y, "month": ref_m},
                hr=True)
            return {"label": f"★ {label} [{nm_t}]", "ok": True,
                    "detail": _json.dumps(d, ensure_ascii=False)[:1500]}
        except Exception as e:
            return {"label": f"{label} [{nm_t}]", "ok": False, "detail": str(e)[:120]}

    # 最大10並列でテスト (1名目のみ - 後段で他の名前もテスト)
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(_do_call, c) for c in candidates]
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"label": "並列実行失敗", "ok": False, "detail": str(e)[:200]})

    # ※ 探索系URL試行(3名テスト/権限ベース/代替URL/完全ダンプ)は確定済みのため削除
    # 通勤手当・固定残業代は freee 公開API では取得不可能と確定 (40+ URL/5バージョン全試行)
    # ----
    # 従業員詳細 (`/api/v1/employees/{eid}`) の完全ダンプ＋全フィールドスキャン (確認用に残す)
    # 通勤・残業・手当関連フィールドが隠れていないか徹底的に探す
    try:
        full_detail = freee_client._get(
            f"/api/v1/employees/{eid_t}",
            params={"company_id": hr_cid, "year": ref_y, "month": ref_m},
            hr=True,
        )
        # 完全ダンプ (truncation なし)
        full_json = _json.dumps(full_detail, ensure_ascii=False)
        results.append({
            "label": f"★★ 従業員詳細 [{nm_t}] (完全ダンプ) — 全{len(full_json):,}文字",
            "ok": True,
            "detail": full_json,
        })

        # 関連フィールドスキャン: 全パスを再帰的に walk
        found_paths: list = []
        keywords = ["commute", "transport", "overtime", "allow",
                    "通勤", "交通", "残業", "時間外", "手当", "pay_amount",
                    "monthly_amount", "base_pay", "extra"]

        def _walk(node, path=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    new_path = f"{path}.{k}" if path else k
                    # キー名にキーワードを含むかチェック
                    k_lc = k.lower()
                    for kw in keywords:
                        if kw.lower() in k_lc:
                            val_repr = str(v)[:80] if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>"
                            found_paths.append(f"{new_path} = {val_repr}")
                            break
                    _walk(v, new_path)
            elif isinstance(node, list):
                for i, it in enumerate(node):
                    _walk(it, f"{path}[{i}]")

        _walk(full_detail)
        if found_paths:
            results.append({
                "label": f"★★★ 通勤/残業/手当 関連フィールド検出 ({len(found_paths)}件)",
                "ok": True,
                "detail": " | ".join(found_paths[:100]),
            })
        else:
            results.append({
                "label": "★★★ 通勤/残業/手当 関連フィールド検出",
                "ok": False,
                "detail": "従業員詳細の全フィールドを再帰スキャンしましたが、commute/transport/overtime/通勤/残業/手当/allow を含むフィールドは1つも見つかりませんでした",
            })
    except Exception as e:
        results.append({"label": "従業員詳細完全ダンプ失敗", "ok": False, "detail": str(e)[:300]})

    # 給与明細
    try:
        statements = freee_client.hr_get_payroll_statements_month(hr_cid, y, m)
        results.append({"label": f"給与明細({y}/{m})", "ok": True, "detail": f"{len(statements)}件"})
        # payments name 集計
        name_counter: dict = {}
        for st in statements:
            for pmt in (st.get("payments") or []):
                if not isinstance(pmt, dict):
                    continue
                nm = pmt.get("name") or ""
                if nm:
                    name_counter[nm] = name_counter.get(nm, 0) + 1
        if name_counter:
            results.append({"label": "★ payments name 一覧",
                            "ok": True,
                            "detail": ", ".join(f"{k}×{v}" for k, v in sorted(name_counter.items(), key=lambda x: -x[1]))})
    except Exception as e:
        results.append({"label": "給与明細", "ok": False, "detail": str(e)[:200]})

    return jsonify({"results": results})


# ---------- Entry point ----------

def run():
    s = get_settings()
    print(f" * Starting freee Cashflow Dashboard on http://127.0.0.1:{s.app_port}")
    print(f" * Mock mode: {s.mock_mode}")
    print(f" * Connected to freee: {auth.is_connected()}")
    app.run(host="127.0.0.1", port=s.app_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run()
