# SPDX-License-Identifier: Apache-2.0
"""Shared JSON/date helpers for mkt services (avoids circular imports)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional


def _jloads(raw: Any, default=None):
    if default is None:
        default = {}
    if not raw:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def _jdumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _dt(v: Any) -> Optional[datetime]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip().replace("Z", "")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None
