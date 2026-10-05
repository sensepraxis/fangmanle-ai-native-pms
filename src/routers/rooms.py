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
from models import Room, RoomType

router = APIRouter(tags=["rooms"])


@router.get("/rooms")
def list_rooms(
    hotel_id: int = Depends(hotel_scope),
    on_date: Optional[str] = Query(None, description="业务日 YYYY-MM-DD；缺省=今日；不可选历史"),
    db: Session = Depends(get_db),
):
    """房态列表：附带在住客人、房价、开放清扫/客需提示（减少前端 HardCode）。"""
    from application.rooms import build_rooms_list

    return ok(build_rooms_list(db, hotel_id, on_date=on_date))


@router.post("/rooms/ai-recommend")
def rooms_ai_recommend(payload: dict, db: Session = Depends(get_db), hotel_id: int = Depends(hotel_scope)):
    """散客入住 AI 推房：自然语言诉求 → 可售空净房排序推荐（优先 LLM，失败走规则）。"""
    from application.orders import recommend_rooms

    need = str(payload.get("need") or payload.get("query") or "").strip()
    if not need:
        raise HTTPException(400, "请填写客人房间诉求")
    hid = int(payload.get("hotel_id") or hotel_id)
    limit = int(payload.get("limit") or 8)
    return ok(recommend_rooms(db, hid, need, limit=limit))


@router.post("/rooms/{room_id}/status")
def set_room_status(
    room_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """房态变更：按目标状态走用例语义（维修/锁房/预离等）。"""
    from application.rooms import set_room_status

    return ok(set_room_status(db, room_id=room_id, payload=payload, ctx=ctx))


@router.post("/rooms/{room_id}/mark-due-out")
def mark_due_out_api(
    room_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.rooms import mark_due_out_room
    from models import Room

    r = db.get(Room, room_id)
    if not r:
        raise HTTPException(404, "room not found")
    assert_hotel_access(r.hotel_id)
    return ok(
        mark_due_out_room(
            db,
            room_id,
            reason=str(payload.get("reason") or "前台标记预离"),
            operator_id=ctx.user_id,
        )
    )


@router.get("/rooms/oversell")
def rooms_oversell(
    hotel_id: int = Depends(hotel_scope),
    days: int = 7,
    db: Session = Depends(get_db),
):
    """房态-12 超售与房量不足预警。"""
    from application.rooms import oversell_snapshot

    return ok(oversell_snapshot(db, hotel_id, days=max(1, min(int(days or 7), 30))))


@router.get("/rooms/status-history")
def rooms_status_history_api(
    hotel_id: int = Depends(hotel_scope),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    room_no: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """经营分析 · 房态历史查询（变更流水）。"""
    from application.rooms import room_status_history

    def _parse(s: Optional[str]):
        if not s:
            return None
        try:
            return date.fromisoformat(str(s)[:10])
        except Exception:
            raise HTTPException(400, "日期须为 YYYY-MM-DD")

    return ok(
        room_status_history(
            db,
            hotel_id,
            date_from=_parse(date_from),
            date_to=_parse(date_to),
            room_no=room_no,
            limit=limit,
        )
    )


@router.post("/rooms/{room_id}/transition")
def room_transition_api(
    room_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.rooms import transition_room
    from models import Room

    r = db.get(Room, room_id)
    if not r:
        raise HTTPException(404, "room not found")
    assert_hotel_access(r.hotel_id)
    return ok(
        transition_room(
            db,
            room_id,
            to_status=str(payload.get("to") or payload.get("status") or ""),
            reason=str(payload.get("reason") or ""),
            operator_id=ctx.user_id,
            force=bool(payload.get("force")),
        )
    )


# ---------------- 房间档案 ----------------
@router.get("/rooms/master")
def list_room_master(
    hotel_id: int = Depends(hotel_scope),
    room_type_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="搜索房号或门锁ID"),
    db: Session = Depends(get_db),
):
    """物理房间档案列表（系统配置用，不含实时房态投影）。"""
    from application.rooms import list_room_masters

    return ok(list_room_masters(db, hotel_id, room_type_id=room_type_id, q=q))


@router.post("/rooms/master")
def create_room_master(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """新增物理房间档案。"""
    from application.rooms import create_room_master as create_room_master_uc

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    return ok(create_room_master_uc(db, hotel_id, payload))


@router.put("/rooms/master/{room_id}")
def update_room_master(
    room_id: int, payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    """更新物理房间档案（房型绑定、楼层等，不改实时房态）。"""
    from application.rooms import update_room_master as update_room_master_uc

    r = db.get(Room, room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    assert_hotel_access(r.hotel_id)
    return ok(update_room_master_uc(db, room_id, payload))


@router.delete("/rooms/master/{room_id}")
def delete_room_master(room_id: int, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """删除物理房间档案（有在住/预订占用时拒绝）。"""
    from application.rooms import delete_room_master as delete_room_master_uc

    r = db.get(Room, room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    assert_hotel_access(r.hotel_id)
    return ok(delete_room_master_uc(db, room_id))


@router.get("/rooms/master/{room_id}/maintenance")
def room_master_maintenance(room_id: int, db: Session = Depends(get_db)):
    """房间档案 · 维修日志（按规范化房号匹配设备维保）。"""
    from application.rooms import list_room_maintenance_bundle

    r = db.get(Room, room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    assert_hotel_access(r.hotel_id)
    return ok(list_room_maintenance_bundle(db, r.hotel_id, r))


@router.post("/rooms/master/{room_id}/ai-maintain-advice")
def room_master_ai_maintain_advice(
    room_id: int,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """调用系统配置的 LLM（可切换本地/云端）结合维保记录生成维护建议。"""
    from application.rooms import build_room_maintain_advice

    return ok(build_room_maintain_advice(db, room_id=room_id, ctx=ctx))


@router.get("/rooms/{room_id}")
def room_detail(room_id: int, db: Session = Depends(get_db)):
    from application.rooms import room_detail_bundle

    return ok(room_detail_bundle(db, room_id))


# ---------------- 收益价格助手 ----------------
@router.get("/room-types")
def list_room_types(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """房型台账：面积/配置读库；关联房间数来自 rooms 计数（非房型写死字段）。"""
    from application.rooms import list_room_types as list_room_types_uc

    return ok(list_room_types_uc(db, hotel_id))


@router.post("/room-types")
def create_room_type(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """新增房型并落库。"""
    from application.rooms import create_room_type as create_room_type_uc

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    return ok(create_room_type_uc(db, hotel_id, payload))


@router.put("/room-types/{type_id}")
def update_room_type(
    type_id: int, payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    """更新房型字段并落库。"""
    from application.rooms import update_room_type as update_room_type_uc

    rt = db.get(RoomType, type_id)
    if not rt:
        raise HTTPException(404, "房型不存在")
    assert_hotel_access(rt.hotel_id)
    return ok(update_room_type_uc(db, type_id, payload))


@router.delete("/room-types/{type_id}")
def delete_room_type(type_id: int, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """删除房型：若仍有关联物理房间则拒绝。"""
    from application.rooms import delete_room_type as delete_room_type_uc

    rt = db.get(RoomType, type_id)
    if not rt:
        raise HTTPException(404, "房型不存在")
    assert_hotel_access(rt.hotel_id)
    return ok(delete_room_type_uc(db, type_id))


@router.get("/inventory/forecast")
def inventory_forecast(
    hotel_id: int = Depends(hotel_scope),
    days: int = 30,
    start_date: str | None = None,
    db: Session = Depends(get_db),
):
    """未来窗口入住压力热力：锚点日起 N 天；已订率来自 room_night_inventory，预测来自 demand_forecast。"""
    from application.rooms import build_inventory_forecast

    return ok(build_inventory_forecast(db, hotel_id, days=days, start_date=start_date))


@router.get("/inventory/forecast/day-detail")
def inventory_forecast_day_detail(
    hotel_id: int = Depends(hotel_scope),
    biz_date: str = "",
    db: Session = Depends(get_db),
):
    """高压日下钻：房型 × 日 已售/可售明细。"""
    from application.rooms import build_inventory_forecast_day_detail

    return ok(build_inventory_forecast_day_detail(db, hotel_id, biz_date=biz_date))


@router.get("/inventory/calendar")
def inventory_calendar(
    hotel_id: int = Depends(hotel_scope),
    days: int = 14,
    rebuild: bool = False,
    db: Session = Depends(get_db),
):
    """按日库存面板：优先读 room_night_inventory（按日×房间），缺数据时从订单/房态物化。"""
    from application.rooms import build_inventory_calendar

    return ok(build_inventory_calendar(db, hotel_id, days=days, rebuild=rebuild))


@router.post("/inventory/calendar/rebuild")
def inventory_calendar_rebuild(hotel_id: int = Depends(hotel_scope), days: int = 14, db: Session = Depends(get_db)):
    """强制按订单/房态重建按日房间库存。"""
    from bootstrap.ensure_room_inventory import rebuild_room_night_inventory

    n = rebuild_room_night_inventory(db, hotel_id, days)
    return ok({"rebuilt": n, "hotel_id": hotel_id, "days": days})
