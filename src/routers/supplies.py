# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)

router = APIRouter(tags=["supplies"])


@router.get("/supplies")
def list_supplies(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.assets import list_supplies as list_supplies_uc

    return ok(list_supplies_uc(db, hotel_id))


@router.post("/supplies/restock-orders/{oid}/approve")
def approve_restock(oid: int, db: Session = Depends(get_db)):
    from application.assets import approve_restock_order

    return ok(approve_restock_order(db, oid))


@router.post("/supplies/damage-tickets")
def create_damage(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """资产/物资报损登记：承接详情页表单。"""
    from application.assets import create_damage_ticket

    hotel_id = assert_hotel_access(payload.get("hotel_id") if payload else None)
    operator = getattr(ctx, "full_name", None) or ctx.username or "前台"
    return ok(create_damage_ticket(db, payload or {}, hotel_id=hotel_id, operator=operator))


@router.post("/supplies/damage-tickets/{tid}/resolve")
def resolve_damage(tid: int, db: Session = Depends(get_db)):
    from application.assets import resolve_damage_ticket

    return ok(resolve_damage_ticket(db, tid))


@router.get("/supplies/board")
def supplies_board(hotel_id: int = Depends(hotel_scope), line: Optional[str] = None, db: Session = Depends(get_db)):
    """⑧ 物资双线聚合：布草周转 / 易耗库存·补货·领用·报损。"""
    from application.assets import build_supplies_board

    return ok(build_supplies_board(db, hotel_id, line=line))
