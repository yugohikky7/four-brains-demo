"""APIレスポンスの簡易メモリキャッシュ。
freee API は呼び出しが遅いため、同一プロセス内で短時間 (デフォルト5分) 結果を保持する。
編集系操作 (PUT/POST) が走ったら関連プレフィックスを invalidate する。
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable

_DEFAULT_TTL = 300  # 秒（5分）

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def get_or_set(key: str, factory: Callable[[], Any], ttl: int = _DEFAULT_TTL) -> Any:
    """key のキャッシュがあれば返し、なければ factory を呼んで保存する。"""
    now = time.time()
    with _lock:
        if key in _store:
            ts, val = _store[key]
            if now - ts < ttl:
                return val
    val = factory()
    with _lock:
        _store[key] = (now, val)
    return val


def invalidate(prefix: str = "") -> int:
    """prefix で始まるキーをすべて無効化。prefix="" なら全消去。"""
    with _lock:
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            del _store[k]
        return len(keys)


def stats() -> dict:
    with _lock:
        return {
            "entries": len(_store),
            "keys": sorted(_store.keys()),
        }
