# SPDX-License-Identifier: Apache-2.0
"""Domain service extracted from thick API handlers."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException  # noqa: F401  (except 分支用)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models as _models
from api_common import row_to_dict
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.auth_local import assert_hotel_access
from models import Asset, Guest, HousekeepingTask, Order, PriceSuggestion, Reservation, Room, RoomType, User

# models.__all__ 未覆盖全部 ORM（如 SupplyAlert）；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})
from hk.housekeeping_service import HK_ICON, HK_TYPE_CN, hk_ui_status


def _parse_feature_tags(raw) -> list:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [x.strip() for x in str(raw).replace("，", ",").split(",") if x.strip()]


def _dump_feature_tags(tags) -> Optional[str]:
    cleaned = _parse_feature_tags(tags)
    return ",".join(cleaned) if cleaned else None


def _normalize_physical_status(v) -> str:
    s = str(v or "normal").strip().lower()
    alias = {
        "正常": "normal",
        "维修": "maintenance",
        "停用": "oos",
        "out_of_service": "oos",
        "ooo": "oos",
        "maint": "maintenance",
    }
    s = alias.get(s, s)
    if s not in ("normal", "maintenance", "oos"):
        return "normal"
    return s


def _room_feature_tags(r: Room) -> list:
    tags = _parse_feature_tags(r.features)
    smoke = "可吸烟" if r.smoking else "无烟"
    # 吸烟标签固定首位，避免重复
    tags = [t for t in tags if t not in ("无烟", "可吸烟")]
    return [smoke] + tags


def _find_lock_asset(db: Session, hotel_id: int, room_no: str, lock_id: Optional[str] = None):
    """优先按门锁 ID / 设备编号匹配，其次按房号 + 门锁类目。"""
    if lock_id:
        a = (
            db.query(Asset)
            .filter(
                Asset.hotel_id == hotel_id,
                (Asset.asset_no == lock_id) | (Asset.sn == lock_id),
            )
            .first()
        )
        if a:
            return a
    if room_no:
        a = (
            db.query(Asset)
            .filter(Asset.hotel_id == hotel_id, Asset.room_no == room_no)
            .filter((Asset.category.ilike("%门锁%")) | (Asset.name.ilike("%门锁%")) | (Asset.category.ilike("%安防%")))
            .first()
        )
        if a:
            return a
        # 回退：该房任意设备
        return (
            db.query(Asset)
            .filter(Asset.hotel_id == hotel_id, Asset.room_no == room_no)
            .order_by(Asset.id.asc())
            .first()
        )
    return None


def _room_master_dict(db: Session, r: Room, rt: Optional[RoomType] = None) -> dict:
    if rt is None and r.room_type_id:
        rt = db.get(RoomType, r.room_type_id)
    d = row_to_dict(r)
    d["room_type_name"] = rt.name if rt else ""
    d["room_type_code"] = rt.code if rt else ""
    d["feature_tags"] = _room_feature_tags(r)
    d["physical_status"] = _normalize_physical_status(getattr(r, "physical_status", None) or "normal")
    d["lock_id"] = (r.lock_id or "").strip() or None
    lock = _find_lock_asset(db, r.hotel_id, r.room_no, r.lock_id)
    d["lock_asset_id"] = lock.id if lock else None
    d["lock_asset_name"] = lock.name if lock else None
    return d


def build_rooms_list(db: Session, hotel_id: int, on_date: Optional[str] = None):
    """房态列表：附带在住客人、房价、开放清扫/客需提示（减少前端 HardCode）。"""
    from rooms.room_status import BLK, DO, EA, OCC, OOO, VD, label, normalize, public_room_dict

    today = date.today()
    view = today
    if on_date:
        try:
            view = date.fromisoformat(str(on_date)[:10])
        except Exception:
            raise InvalidStateError("on_date 须为 YYYY-MM-DD")
    if view < today:
        raise InvalidStateError("历史房态请前往经营分析 · 房态历史查询")
    if view > today + timedelta(days=90):
        raise InvalidStateError("仅支持查看未来 90 天内房态")
    if view > today:
        from rooms.room_ops import project_board_for_date

        return project_board_for_date(db, hotel_id, view)

    rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id)
        .all()
    )

    # 在住：reservation → checked_in order → guest
    stay_by_room: dict = {}
    stay_rows = (
        db.query(Reservation, Order, Guest)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .all()
    )
    for res, od, g in stay_rows:
        if res.room_id:
            stay_by_room[res.room_id] = (od, g)

    # 预抵：已分房未入住
    ea_by_room: dict = {}
    ea_rows = (
        db.query(Reservation, Order, Guest)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed")),
            Reservation.room_id.isnot(None),
        )
        .all()
    )
    for res, od, g in ea_rows:
        if res.room_id:
            ea_by_room[res.room_id] = (od, g)

    # 开放清扫任务（按房）
    users = {u.id: u for u in db.query(User).filter((User.hotel_id == hotel_id) | (User.hotel_id.is_(None))).all()}
    open_hk: dict = {}
    for t in (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned", "in_progress", "pending_inspect", "rework")),
        )
        .order_by(HousekeepingTask.priority.asc(), HousekeepingTask.id.desc())
        .all()
    ):
        if t.room_id and t.room_id not in open_hk:
            u = users.get(t.assignee_id) if t.assignee_id else None
            open_hk[t.room_id] = {
                "title": HK_TYPE_CN.get(t.task_type or "clean", t.task_type or "清扫"),
                "assignee": (u.full_name or u.username) if u else "待分配",
                "priority": t.priority or 5,
                "status": t.status,
            }

    # 开放客需（按房）
    from hk.queries import OpenServiceRequestsQuery

    open_sr: dict = {}
    for row in OpenServiceRequestsQuery(hotel_id=hotel_id, limit=200, order_desc=True).as_dicts(db):
        rid = row.get("room_id")
        if rid and rid not in open_sr:
            open_sr[rid] = (row.get("content") or "住中客需")[:40]

    # 今日房价建议（按房型）
    price_by_type: dict = {}
    for p in (
        db.query(PriceSuggestion)
        .filter(PriceSuggestion.hotel_id == hotel_id, PriceSuggestion.biz_date == date.today())
        .all()
    ):
        price_by_type[p.room_type_id] = float(p.suggested_price or p.current_price or 0)

    out = []
    for r, rt in rows:
        d = public_room_dict(r)
        d["room_type_name"] = rt.name if rt else ""
        base = float(rt.base_price) if rt and rt.base_price is not None else None
        d["base_price"] = base
        ai = price_by_type.get(r.room_type_id)
        d["ai_price"] = ai if ai else base
        d["view_date"] = view.isoformat()
        d["projected"] = False
        st = normalize(r.status)

        od, g = stay_by_room.get(r.id, (None, None))
        if od and g:
            d["guest_name"] = g.name
            d["guest_id"] = g.id
            d["order_id"] = od.id
            d["vip_level"] = g.vip_level
            d["check_out"] = od.check_out.strftime("%m-%d") if od.check_out else None
            d["check_in"] = od.check_in.strftime("%m-%d") if od.check_in else None
            if od.check_in and od.check_out:
                d["nights"] = max(1, (od.check_out - od.check_in).days)
            else:
                d["nights"] = od.nights or 1
            # 今日预离：库内已是 DO 则保留；OCC 且今日离店则派生展示
            if st == DO or (od.check_out == date.today() and st == OCC):
                d["status"] = DO
                d["status_label"] = label(DO)
                d["status_legacy"] = "occupied"
        elif st == EA or r.id in ea_by_room:
            eod, eg = ea_by_room.get(r.id, (None, None))
            if st != EA and eod:
                # 已分房但房态未翻到 EA 时，展示层纠正提示（写库由预分接口负责）
                d["status"] = EA
                d["status_label"] = label(EA)
            d["guest_name"] = eg.name if eg else (eod and "预抵客人")
            d["guest_id"] = eg.id if eg else None
            d["order_id"] = eod.id if eod else None
            d["check_in"] = eod.check_in.strftime("%m-%d") if eod and eod.check_in else None
            d["check_out"] = eod.check_out.strftime("%m-%d") if eod and eod.check_out else None
            d["nights"] = eod.nights if eod else None
            if eod and not d.get("ai_tip"):
                d["ai_tip"] = f"预抵订单 #{eod.id}"
        elif st in (OCC, DO):
            d["guest_name"] = None
            d["check_out"] = None
            d["nights"] = 1
        else:
            d["guest_name"] = None
            d["check_out"] = None
            d["nights"] = None

        if d.get("status_note") and not d.get("ai_tip"):
            until = d.get("status_until")
            d["ai_tip"] = d["status_note"] + (f" · 预计 {until}" if until else "")

        hk = open_hk.get(r.id)
        sr_tip = open_sr.get(r.id)
        d["open_hk"] = hk
        d["open_request"] = sr_tip
        # 维修/锁房原因优先展示（勿被通用 ai_tip 覆盖）
        note = (d.get("status_note") or "").strip()
        if hk:
            d["ai_tip"] = f"派单给 {hk['assignee']}（{hk['title']} · {hk.get('status')}）"
        elif sr_tip:
            d["ai_tip"] = f"未结客需：{sr_tip}"
        elif st in (OOO, BLK):
            until = d.get("status_until")
            if note:
                d["ai_tip"] = note + (f" · 预计 {until}" if until else "")
            else:
                d["ai_tip"] = "停用/锁房中，不可售"
        elif st in (OCC, DO) and d.get("check_out"):
            d["ai_tip"] = f"预计退房 {d['check_out']}，可提前安排夜床/送物"
        elif st == VD:
            d["ai_tip"] = "空脏待清洁，须查房通过后才可售"
        elif d.get("ai_price") and base and d["ai_price"] != base:
            delta = int(d["ai_price"] - base)
            d["ai_tip"] = f"AI 建议售价 ¥{int(d['ai_price'])}（相对基价 {delta:+d}）"
        else:
            d["ai_tip"] = "空净可售"
        out.append(d)

    out.sort(key=lambda x: x["room_no"])
    return out


# --- 库存看板已绞杀至 rooms.room_inventory_board ---
from rooms.room_inventory_board import (  # noqa: E402
    build_inventory_calendar,
    build_inventory_forecast,
    build_inventory_forecast_day_detail,
)


def build_room_maintain_advice(db: Session, room_id: int, ctx: Any = None):
    """调用系统配置的 LLM（可切换本地/云端）结合维保记录生成维护建议。"""
    import json
    import re

    from bootstrap.ensure_room_types import parse_amenities
    from extensions.llm.facade import chat as llm_chat
    from extensions.llm.facade import llm_identity, load_llm_config
    from rooms.maintenance_bundle import list_room_maintenance_bundle

    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("房间不存在")
    assert_hotel_access(r.hotel_id)
    rt = db.get(RoomType, r.room_type_id) if r.room_type_id else None
    bundle = list_room_maintenance_bundle(db, r.hotel_id, r)

    context = {
        "room_no": r.room_no,
        "room_type": rt.name if rt else "",
        "building": r.building,
        "floor": r.floor,
        "physical_status": getattr(r, "physical_status", None) or "normal",
        "board_status": r.status,
        "lock_id": r.lock_id,
        "features": parse_amenities(r.features) if r.features else [],
        "smoking": bool(r.smoking),
        "assets": [
            {
                "name": a.get("name"),
                "category": a.get("category"),
                "health_score": a.get("health_score"),
                "insight": a.get("insight"),
                "status": a.get("status"),
                "next_maintain_date": str(a.get("next_maintain_date") or ""),
            }
            for a in (bundle.get("assets") or [])
        ],
        "maintenance_logs": [
            {
                "title": m.get("title"),
                "status": m.get("status"),
                "date": m.get("date"),
                "note": m.get("note"),
                "owner": m.get("owner"),
                "cost": float(m.get("cost") or 0),
            }
            for m in (bundle.get("maintenance") or [])[:12]
        ],
        "current_fault": bundle.get("current_fault"),
    }

    system = (
        "你是酒店工程维保顾问，服务国内中档商务酒店。根据给定房间档案、设备健康与维修记录，"
        "输出 2～3 条可执行的预防性维护建议。只输出 JSON 数组，不要 Markdown，不要解释。"
        "每项字段：icon(door_front|bed|ac_unit|build|plumbing|battery_alert)、"
        "title(≤20字)、desc(1～2句中文，含依据)、action(立即创建工单|排期巡检|评估置换|更换耗材)、"
        "danger(boolean，紧急为 true)。语气专业、具体，避免空话。"
    )
    user = "请基于以下 JSON 数据给出维护建议：\n" + json.dumps(context, ensure_ascii=False, default=str)

    try:
        resp = llm_chat(db, [{"role": "user", "content": user}], system)
        raw = (resp.get("content") or "").strip()
    except HTTPException:
        raise
    except Exception as e:
        raise BusinessError(f"LLM 调用失败：{e}") from e

    suggestions = []
    try:
        # 剥离 ```json ... ```
        text = raw
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("suggestions") or data.get("items") or []
        for item in data[:4]:
            if not isinstance(item, dict):
                continue
            suggestions.append(
                {
                    "icon": str(item.get("icon") or "build")[:40],
                    "title": str(item.get("title") or "维护建议")[:40],
                    "desc": str(item.get("desc") or item.get("recommendation") or "")[:200],
                    "action": str(item.get("action") or "排期巡检")[:20],
                    "danger": bool(item.get("danger")),
                }
            )
    except Exception:
        suggestions = []

    if not suggestions and raw:
        suggestions = [
            {
                "icon": "smart_toy",
                "title": "模型原始建议",
                "desc": raw[:280],
                "action": "排期巡检",
                "danger": False,
            }
        ]

    return {
        "room_id": r.id,
        "room_no": r.room_no,
        "suggestions": suggestions,
        "raw": raw if not suggestions or suggestions[0].get("title") == "模型原始建议" else None,
        **llm_identity(load_llm_config(db), resp if isinstance(resp, dict) else None),
    }


def set_room_status(db: Session, room_id: int, payload: dict, ctx: Any = None):
    """房态变更：按目标状态走用例语义（维修/锁房/预离等）。"""
    from datetime import datetime as _dt

    from rooms.room_ops import (
        clear_block,
        clear_due_out_to_occupied,
        clear_out_of_order,
        mark_due_out,
        set_block,
        set_out_of_order,
    )
    from rooms.room_status import BLK, DO, OCC, OOO, VC, VD, normalize, public_room_dict, transition

    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("room not found")
    assert_hotel_access(r.hotel_id)
    dest = normalize(str(payload.get("status") or ""))
    reason = str(payload.get("reason") or "")
    force = bool(payload.get("force"))
    eta_raw = payload.get("eta") or payload.get("status_until")
    eta = None
    if eta_raw:
        try:
            eta = _dt.strptime(str(eta_raw)[:10], "%Y-%m-%d").date()
        except Exception:
            eta = None

    cur = normalize(r.status)
    if dest == OOO:
        set_out_of_order(db, r, reason=reason or "设置维修房", eta=eta, operator_id=ctx.user_id)
    elif cur == OOO and dest in (VC, VD):
        clear_out_of_order(db, r, to_status=dest, reason=reason or "解除维修房", operator_id=ctx.user_id)
    elif dest == BLK:
        set_block(db, r, reason=reason or "锁房", operator_id=ctx.user_id)
    elif cur == BLK and dest == VC:
        clear_block(db, r, reason=reason or "解锁", operator_id=ctx.user_id)
    elif dest == DO:
        mark_due_out(db, r, reason=reason or "标记预离", operator_id=ctx.user_id)
    elif cur == DO and dest == OCC:
        clear_due_out_to_occupied(db, r, reason=reason or "续住清除预离", operator_id=ctx.user_id)
    else:
        transition(
            db,
            r,
            dest,
            reason=reason,
            operator_id=ctx.user_id,
            force=force,
        )
        if reason and hasattr(r, "status_note") and dest in (OOO, BLK):
            r.status_note = reason[:200]
    db.commit()
    return public_room_dict(r)
