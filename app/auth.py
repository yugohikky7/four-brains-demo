"""freee OAuth2 flow and token refresh (sync version)."""
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from .config import get_settings
from .storage import clear_tokens, load_tokens, save_tokens

_pending_states: Dict[str, float] = {}


def build_authorization_url() -> Tuple[str, str]:
    s = get_settings()
    state = secrets.token_urlsafe(24)
    _pending_states[state] = time.time()
    cutoff = time.time() - 600
    for k in [k for k, v in _pending_states.items() if v < cutoff]:
        _pending_states.pop(k, None)
    params = {
        "response_type": "code",
        "client_id": s.freee_client_id,
        "redirect_uri": s.freee_redirect_uri,
        "state": state,
        "prompt": "select_company",
    }
    return f"{s.freee_oauth_authorize_url}?{urlencode(params)}", state


def verify_state(state: str) -> bool:
    return _pending_states.pop(state, None) is not None


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    s = get_settings()
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            s.freee_oauth_token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "client_id": s.freee_client_id,
                "client_secret": s.freee_client_secret,
                "code": code,
                "redirect_uri": s.freee_redirect_uri,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    data["obtained_at"] = int(time.time())
    save_tokens(data)
    return data


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    s = get_settings()
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            s.freee_oauth_token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": s.freee_client_id,
                "client_secret": s.freee_client_secret,
                "refresh_token": refresh_token,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    data["obtained_at"] = int(time.time())
    save_tokens(data)
    return data


def get_valid_access_token() -> Optional[str]:
    tokens = load_tokens()
    if not tokens:
        return None
    obtained = tokens.get("obtained_at", 0)
    expires_in = tokens.get("expires_in", 21600)
    if time.time() > obtained + expires_in - 300:
        refresh = tokens.get("refresh_token")
        if not refresh:
            return None
        try:
            tokens = refresh_access_token(refresh)
        except httpx.HTTPError:
            clear_tokens()
            return None
    return tokens.get("access_token")


def is_connected() -> bool:
    return load_tokens() is not None


def disconnect() -> None:
    clear_tokens()
