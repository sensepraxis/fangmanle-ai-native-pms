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

router = APIRouter(tags=["assets"])


class AssetRegisterPayload(BaseModel):
    reason: str = "new"  # new | replace | expand
    category: str = "客房电器"
    asset_no: Optional[str] = None
    name: str
    spec: Optional[str] = None
    qty: int = 1
    budget: Optional[str] = None
    room: Optional[str] = None
    supplier: Optional[str] = None
    note: Optional[str] = None
    replace_asset_id: Optional[int] = None


@router.post("/assets")
def asset_register(
    payload: AssetRegisterPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """登记新资产：写入 assets 表并记录生命周期事件。"""
    from application.assets import register_asset

    return ok(register_asset(db, hotel_id, payload=payload))


@router.get("/assets/{asset_id}/maintenance")
def asset_maintenance_list(
    asset_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """单设备关联维保/维修工单（含历史与待办，不限条数）。"""
    from application.assets import list_asset_maintenance

    return ok(list_asset_maintenance(db, hotel_id, asset_id=asset_id))


def _maint_status_label(st: str) -> str:
    from infra.i18n import t as _t

    return {
        "done": _t("已完成"),
        "overdue": _t("逾期"),
        "doing": _t("处理中"),
        "scheduled": _t("计划中"),
    }.get(st or "scheduled", _t("计划中"))


def _maint_progress_step(st: str) -> int:
    return {"scheduled": 1, "overdue": 1, "doing": 3, "done": 4}.get(st or "scheduled", 1)


@router.get("/assets/{asset_id}/maintenance/{maint_id}")
def asset_maintenance_detail(
    asset_id: int,
    maint_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """单条维保/维修工单详情（含设备上下文与进度时间轴）。"""
    from application.assets import get_asset_maintenance_detail

    return ok(get_asset_maintenance_detail(db, hotel_id, asset_id=asset_id, maint_id=maint_id))


@router.get("/assets/loss-attribution/cache")
def asset_loss_attribution_cache(
    period: str = "12",
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """报损页：按输入数据指纹查询归因缓存。"""
    from application.assets import loss_attribution_cache

    return ok(loss_attribution_cache(db, hotel_id, period))


@router.post("/assets/loss-attribution/analyze")
def asset_loss_attribution_analyze(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """报损页：高频损坏 LLM 归因（非流式）。"""
    from application.assets import generate_loss_attribution

    period = str((payload or {}).get("period") or "12")
    force = bool((payload or {}).get("force"))
    return ok(generate_loss_attribution(db, hotel_id, period, force=force))


@router.post("/assets/loss-attribution/analyze/stream")
def asset_loss_attribution_stream(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """报损页：高频损坏 LLM 归因（SSE 流式）。"""
    from application.assets import stream_loss_attribution

    period = str((payload or {}).get("period") or "12")
    force = bool((payload or {}).get("force"))

    def event_gen():
        for evt in stream_loss_attribution(db, hotel_id, period, force=force):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/assets/{asset_id}/ai-next-action")
def asset_ai_next_action(
    asset_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """结合资产台账/告警/工单，由 LLM 生成下一步行动建议。"""
    from application.assets import generate_asset_next_action

    return ok(generate_asset_next_action(db, hotel_id, asset_id))


@router.post("/assets/{asset_id}/ai-next-action/stream")
def asset_ai_next_action_stream(
    asset_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """流式生成资产下一步行动建议（SSE）。"""
    from application.assets import stream_asset_next_action

    def event_gen():
        for evt in stream_asset_next_action(db, hotel_id, asset_id):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------- LLM 可配置模块 ----------------


@router.get("/assets/board")
def assets_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """设备设施聚合：台账 / 告警 / 洞察 / 维保 / 盘点 / 生命周期事件。"""
    from application.assets import build_assets_board

    return ok(build_assets_board(db, hotel_id))
