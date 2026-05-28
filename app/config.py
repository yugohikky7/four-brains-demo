"""環境変数とアプリ設定を一元管理する。"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# プロジェクトルート
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static"

# .env を読み込む
load_dotenv(ROOT_DIR / ".env")


class Settings:
    """環境変数から取得した設定値。"""

    def __init__(self) -> None:
        self.mock_mode: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
        self.freee_client_id: str = os.getenv("FREEE_CLIENT_ID", "")
        self.freee_client_secret: str = os.getenv("FREEE_CLIENT_SECRET", "")
        self.freee_redirect_uri: str = os.getenv(
            "FREEE_REDIRECT_URI", "http://localhost:8765/oauth/callback"
        )
        self.app_secret_key: str = os.getenv(
            "APP_SECRET_KEY",
            "default-insecure-key-please-change-in-production-32chars",
        )
        self.app_port: int = int(os.getenv("APP_PORT", "8765"))

        # freee API のエンドポイント
        self.freee_oauth_authorize_url = (
            "https://accounts.secure.freee.co.jp/public_api/authorize"
        )
        self.freee_oauth_token_url = (
            "https://accounts.secure.freee.co.jp/public_api/token"
        )
        self.freee_accounting_base = "https://api.freee.co.jp"
        self.freee_hr_base = "https://api.freee.co.jp/hr"

        # データディレクトリを作成
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def has_freee_credentials(self) -> bool:
        return bool(self.freee_client_id and self.freee_client_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
