# SPDX-License-Identifier: Apache-2.0
"""今日运营实时指标轻量缓存（进程内 TTL，环境替代 Redis）。"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, Any]] = {}

DEFAULT_TTL = 30.0


def cache_get(key: str) -> Optional[Any]:
    now = time.monotonic()
    with _LOCK:
        row = _STORE.get(key)
        if not row:
            return None
        exp, val = row
        if exp < now:
            _STORE.pop(key, None)
            return None
        return val


def cache_set(key: str, value: Any, ttl: float = DEFAULT_TTL) -> None:
    with _LOCK:
        _STORE[key] = (time.monotonic() + max(1.0, float(ttl)), value)


def cache_invalidate(prefix: str = "") -> None:
    with _LOCK:
        if not prefix:
            _STORE.clear()
            return
        for k in list(_STORE.keys()):
            if k.startswith(prefix):
                _STORE.pop(k, None)
