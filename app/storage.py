"""JSON形式での永続化レイヤ。トークンはFernetで暗号化保存。"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .config import DATA_DIR, get_settings


def _fernet() -> Fernet:
    """APP_SECRET_KEYから32バイトのFernet鍵を導出する。"""
    raw = get_settings().app_secret_key.encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


# ============================================================
# トークン管理（暗号化）
# ============================================================

TOKENS_FILE = DATA_DIR / "tokens.json"


def save_tokens(tokens: dict[str, Any]) -> None:
    """トークン情報を暗号化して保存。"""
    plaintext = json.dumps(tokens, ensure_ascii=False).encode("utf-8")
    ciphertext = _fernet().encrypt(plaintext)
    TOKENS_FILE.write_bytes(ciphertext)


def load_tokens() -> dict[str, Any] | None:
    """暗号化されたトークン情報を復号して取得。"""
    if not TOKENS_FILE.exists():
        return None
    try:
        ciphertext = TOKENS_FILE.read_bytes()
        plaintext = _fernet().decrypt(ciphertext)
        return json.loads(plaintext.decode("utf-8"))
    except Exception:
        # APP_SECRET_KEYが変わったなどで復号できない場合
        return None


def clear_tokens() -> None:
    if TOKENS_FILE.exists():
        TOKENS_FILE.unlink()


# ============================================================
# 設定・調整値（平文JSON）
# ============================================================

SETTINGS_FILE = DATA_DIR / "settings.json"
ADJUSTMENTS_FILE = DATA_DIR / "adjustments.json"
LOANS_FILE = DATA_DIR / "loans.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---- forecast settings ----

DEFAULT_SETTINGS = {
    # 売上発生→入金までの月数（売掛サイト）
    "receivable_months": 1,
    # 仕入・経費発生→支払までの月数（買掛サイト）
    "payable_months": 2,
    # 給与の支払サイト（月内末締め→翌月支払等）。0=当月、1=翌月
    "salary_payment_offset_months": 0,
    # 期首現預金残高（手元キャッシュ）。空ならAPI/Mockの口座残高合計を使う
    "opening_cash_balance": None,
    # シナリオパラメータ
    "scenarios": {
        "optimistic": {"revenue_multiplier": 1.10, "cost_multiplier": 0.95},
        "neutral": {"revenue_multiplier": 1.00, "cost_multiplier": 1.00},
        "pessimistic": {"revenue_multiplier": 0.85, "cost_multiplier": 1.05},
    },
}


def load_settings() -> dict:
    saved = _read_json(SETTINGS_FILE, {})
    # マージ
    merged = {**DEFAULT_SETTINGS, **saved}
    # scenariosは深いマージ
    if "scenarios" in saved:
        merged["scenarios"] = {**DEFAULT_SETTINGS["scenarios"], **saved["scenarios"]}
    return merged


def save_settings(data: dict) -> None:
    _write_json(SETTINGS_FILE, data)


# ---- manual adjustments ----
# 形式: { "2026-06": [{ "category": "賞与", "amount": -3000000, "type": "operating" }, ...], ... }

def load_adjustments() -> dict[str, list[dict]]:
    return _read_json(ADJUSTMENTS_FILE, {})


def save_adjustments(data: dict[str, list[dict]]) -> None:
    _write_json(ADJUSTMENTS_FILE, data)


# ---- loans ----
# 形式: [{ "name": "..", "principal": 30000000, "annual_rate": 0.015, "term_months": 60,
#          "start_year_month": "2025-04", "method": "equal_principal" or "equal_payment" }, ...]

# ---- forecast overrides (入金/支払予測の編集内容) ----

FORECAST_OVERRIDES_FILE = DATA_DIR / "forecast_overrides.json"


def load_forecast_overrides() -> dict:
    """{ "income": { partner_name: {...override...}, ... },
         "expense": { ... },
         "extra_items": [ ... ] }"""
    return _read_json(FORECAST_OVERRIDES_FILE, {"income": {}, "expense": {}, "extra_items": []})


def save_forecast_overrides(data: dict) -> None:
    _write_json(FORECAST_OVERRIDES_FILE, data)


def load_loans() -> list[dict]:
    return _read_json(LOANS_FILE, [])


def save_loans(data: list[dict]) -> None:
    _write_json(LOANS_FILE, data)


# ---- employee overrides (従業員の手動上書き) ----
# 形式: { "<emp_id>": { "monthly_salary": int, "commute_allowance": int,
#                       "fixed_overtime": int, "department": str, "position": str,
#                       "category": "exec" | "employee" | "engineer" }, ... }

EMPLOYEE_OVERRIDES_FILE = DATA_DIR / "employee_overrides.json"


def load_employee_overrides() -> dict:
    return _read_json(EMPLOYEE_OVERRIDES_FILE, {})


def save_employee_overrides(data: dict) -> None:
    _write_json(EMPLOYEE_OVERRIDES_FILE, data)


# ---- employee detail overrides (詳細情報の手動上書き: 面談履歴/入社手続き等) ----
EMPLOYEE_DETAILS_FILE = DATA_DIR / "employee_details.json"


def load_employee_details() -> dict:
    """{ "<emp_id>": { merged detail dict } }"""
    return _read_json(EMPLOYEE_DETAILS_FILE, {})


def save_employee_details(data: dict) -> None:
    _write_json(EMPLOYEE_DETAILS_FILE, data)
