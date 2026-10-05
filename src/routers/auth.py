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

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login", response_model=None)
def login(payload: LoginBody, db: Session = Depends(get_db)):
    ctx = authenticate_user(db, payload.username, payload.password)
    token = issue_token(
        user_id=ctx.user_id,
        hotel_id=ctx.hotel_id,
        username=ctx.username,
        role=ctx.role,
    )
    return ok(
        {
            "access_token": token,
            "token_type": "bearer",
            "hotel_id": ctx.hotel_id,
            "hotel_name": ctx.hotel_name,
            "user": {
                "id": ctx.user_id,
                "username": ctx.username,
                "name": ctx.full_name,
                "role": ctx.role,
            },
            "menus": sorted(ctx.menus),
            "scopes": sorted(ctx.scopes),
            "issued_at": datetime.now().isoformat(),
        }
    )


@router.get("/auth/me")
def auth_me(ctx: AppContext = Depends(get_current_user), db: Session = Depends(get_db)):
    # 每次 /me 从 DB 刷新（权限改完立刻生效）
    from infra.rbac_service import get_role_permission_sets

    menus, scopes = get_role_permission_sets(db, ctx.role)
    return ok(
        {
            "user_id": ctx.user_id,
            "username": ctx.username,
            "name": ctx.full_name,
            "role": ctx.role,
            "hotel_id": ctx.hotel_id,
            "hotel_name": ctx.hotel_name,
            "menus": sorted(menus),
            "scopes": sorted(scopes),
        }
    )
