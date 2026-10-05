# SPDX-License-Identifier: Apache-2.0
"""Shared API helpers — safe for routers/services to import (no FastAPI app)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from infra.auth_local import AppContext, assert_hotel_access, get_current_user


def row_to_dict(o):
    d = {}
    for c in o.__table__.columns:
        v = getattr(o, c.name)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        elif isinstance(v, Decimal):
            v = float(v)
        d[c.name] = v
    return d


def ok(data):
    return {"ok": True, "data": data}


def hotel_scope(
    hotel_id: Optional[int] = Query(None),
    ctx: AppContext = Depends(get_current_user),
) -> int:
    """单体部署：返回本店 hotel_id（兼容旧 query 参数）。"""
    return assert_hotel_access(hotel_id)
