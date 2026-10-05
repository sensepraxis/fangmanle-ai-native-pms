# SPDX-License-Identifier: Apache-2.0
# hk.housekeeping_service.task_service — auto-split by AST

"""
房务工单流：与房态分离。

INT-01 退房 → 建清洁单（房态已是 VD）
HK-02/03 开始/完成清洁 → pending_inspect（房态仍 VD）
HK-04 查房通过 → VD→VC
HK-05 不通过 → rework
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException  # noqa: F401  (except 分支用)
from sqlalchemy.orm import Session

import models as _models
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from models import HousekeepingTask, Room, User

globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})
from rooms.room_status import OCC, OOO, VC, VD, normalize, transition

HK_TYPE_CN = {
    "clean": "退房清扫",
    "inspect": "查房质检",
    "turn": "住中整理",
    "daily": "日常清洁",
    "repair": "维修",
    "service": "客需服务",
}
HK_ICON = {
    "clean": "cleaning_services",
    "inspect": "fact_check",
    "turn": "hotel",
    "daily": "mop",
    "repair": "build",
    "service": "room_service",
}

# ---- 模块级常量（在原文件中位于 def 之后但属于模块层）----
HK_TASK_TYPES = {
    "clean": "退房清洁",
    "turn": "住中整理",
    "daily": "日常清洁",
    "repair": "维修",
    "service": "客中服务",
    "inspect": "查房验收",
}
HK_AI_DISPATCH_SYSTEM = '你是单体酒店客房主管的派工助手。酒店规模小（通常 1–2 层、每层约 12 间），不要按百间酒店的编制来估人力。\n\n目标：根据「系统现状」、MCP 工具结果和人员负荷，给出可立刻执行的派工方案，并筛选待建保洁任务。\n\n硬约束：\n1. 只能使用输入里出现的 task_id、staff id、room_id，禁止编造人员、房号或楼层。\n2. 休息（status=rest）的人不能派工。\n3. 优先：同楼层就近 → 空闲/低负荷 → VIP/高优（priority 数字越小越急）。\n4. 每人最多派 4 单；本轮最多派 8 单。不要把全部开放任务塞给一个人。\n5. 缺口人数 = max(0, 待分配任务数 − 可派工人数)，两层小楼缺口通常是 0–2。\n6. new_tasks 只能从 MCP 工具 `draft_housekeeping_tasks` 返回的草稿里挑选，最多 6 条；不要给已有未完成工单的房间再建一张。\n7. 只输出一个 JSON 对象，不要 markdown、不要解释性前后文。\n\nJSON 格式：\n{\n  "summary": "不超过 80 字：先结论后理由",\n  "mode": "smart",\n  "focus_floor": 1,\n  "gap": 0,\n  "assignments": [\n    {"task_id": 12, "assignee_id": 5, "reason": "同层且空闲"}\n  ],\n  "new_tasks": [\n    {"room_id": 3, "task_type": "clean", "priority": 2, "assignee_id": null, "reason": "空脏无工单"}\n  ]\n}\n'
from hk.hk_status import HK_OPENISH_ACTIVE as HK_OPENISH

HK_TYPE_ALIASES = {
    "checkout": "clean",
    "checkout_clean": "clean",
    "清扫": "clean",
    "退房": "clean",
    "退房清洁": "clean",
    "退房清扫": "clean",
    "daily_clean": "daily",
    "日常": "daily",
    "日常清洁": "daily",
    "turn_down": "turn",
    "turndown": "turn",
    "住中": "turn",
    "住中整理": "turn",
    "maint": "repair",
    "maintenance": "repair",
    "维修": "repair",
    "客需": "service",
    "客中": "service",
    "客中服务": "service",
    "客需服务": "service",
    "查房": "inspect",
    "质检": "inspect",
    "查房验收": "inspect",
    "查房质检": "inspect",
}

# 跨子模块 helper：模块别名访问（避开循环 import）
from hk.housekeeping_service import dispatch_service as _hk_dispatch_service
from hk.housekeeping_service import repair_service as _hk_repair_service
from hk.housekeeping_service import task_service as _hk_task_service


def start_task(
    db: Session,
    task_id: int,
    *,
    operator_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    assignee_name: Optional[str] = None,
) -> HousekeepingTask:
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    t.mark_in_progress()
    try:
        from hk.hk_live_cache import cache_invalidate

        cache_invalidate(f"hk_heat:{t.hotel_id}:")
    except Exception:
        pass
    aid = _hk_dispatch_service._resolve_assignee_id(
        db, t.hotel_id, assignee_id=assignee_id, assignee_name=assignee_name
    )
    if aid:
        t.assignee_id = aid
    elif operator_id and (not t.assignee_id):
        t.assignee_id = operator_id
    elif not t.assignee_id:
        t.assignee_id = _hk_dispatch_service._pick_attendant(db, t.hotel_id, t.room_id)
    db.flush()
    return t


def assign_task(
    db: Session, task_id: int, *, assignee_id: Optional[int] = None, assignee_name: Optional[str] = None
) -> HousekeepingTask:
    """换执行人 / 指派：写回 assignee_id；开放单变为 assigned。"""
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    if t.is_terminal():
        raise InvalidStateError(f"当前状态「{t.status}」不可改派")
    aid = _hk_dispatch_service._resolve_assignee_id(
        db, t.hotel_id, assignee_id=assignee_id, assignee_name=assignee_name
    )
    if not aid:
        raise InvalidStateError("请指定执行人")
    t.assignee_id = aid
    if t.status in ("open", "rework"):
        t.mark_assigned()
    db.flush()
    from events import emit

    emit(
        "hk.task_assigned",
        {
            "hotel_id": t.hotel_id,
            "task_id": t.id,
            "room_id": t.room_id,
            "assignee_id": t.assignee_id,
            "status": t.status,
        },
    )
    return t


def ignore_task(db: Session, task_id: int, *, reason: str = "", operator_id: Optional[int] = None) -> HousekeepingTask:
    """忽略待分配任务：标记 ignored，不再出现在作业台开放列表。"""
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    if not t.can_start():
        raise InvalidStateError(f"当前状态「{t.status}」不可忽略（仅待处理任务可忽略）")
    t.mark_ignored()
    note = (reason or "主管忽略").strip()
    if hasattr(t, "fail_reason"):
        prefix = f"忽略：{note}"
        if operator_id:
            prefix = f"忽略(uid={operator_id})：{note}"
        t.fail_reason = prefix[:200]
    db.flush()
    return t


def urge_task(db: Session, task_id: int) -> HousekeepingTask:
    """催办：提升优先级并收紧截止时间。"""
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    if t.status in ("done", "ignored", "closed", "pending_inspect"):
        raise InvalidStateError(f"当前状态「{t.status}」不可催办")
    t.priority = 1
    soon = datetime.now().replace(second=0, microsecond=0)
    from datetime import timedelta

    t.due_at = soon + timedelta(minutes=30)
    db.flush()
    return t


def finish_clean(
    db: Session, task_id: int, *, to_status: str = VC, operator_id: Optional[int] = None
) -> HousekeepingTask:
    """清洁完成 → 待查房；维修单则关单并解除 OOO。"""
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    if not t.can_finish_clean():
        raise InvalidStateError(f"当前状态「{t.status}」不可完成清洁")
    if (t.task_type or "") == "repair":
        _hk_repair_service.complete_repair_and_clear_ooo(db, t, to_status=to_status or VC, operator_id=operator_id)
        return t
    t.mark_pending_inspect()
    db.flush()
    return t


def inspect_task(
    db: Session,
    task_id: int,
    *,
    passed: bool,
    inspector_id: Optional[int] = None,
    fail_reason: str = "",
    fail_items: Optional[list] = None,
) -> dict:
    t = db.get(HousekeepingTask, task_id)
    if not t:
        raise NotFoundError("任务不存在")
    if not t.can_inspect():
        raise InvalidStateError(f"当前状态「{t.status}」不可查房")
    if passed:
        t.mark_done()
        t.done_at = datetime.now()
        if hasattr(t, "inspect_by"):
            t.inspect_by = inspector_id
        if hasattr(t, "inspect_at"):
            t.inspect_at = datetime.now()
        if hasattr(t, "fail_reason"):
            t.fail_reason = None
        room_out = None
        if t.room_id:
            rm = db.get(Room, t.room_id)
            if rm and normalize(rm.status) == VD:
                transition(db, rm, VC, reason="查房验收通过", operator_id=inspector_id)
                room_out = rm.status
        db.flush()
        from events import emit

        emit(
            "hk.task_completed",
            {
                "hotel_id": t.hotel_id,
                "task_id": t.id,
                "room_id": t.room_id,
                "task_type": t.task_type,
                "inspector_id": inspector_id,
            },
        )
        return {"task": t, "passed": True, "room_status": room_out}
    bits = [str(x).strip() for x in fail_items or [] if str(x).strip()]
    reason = (fail_reason or "").strip()
    if bits and reason:
        reason = f"{'、'.join(bits)}；{reason}"
    elif bits:
        reason = "、".join(bits)
    if not reason:
        reason = "查房不通过"
    t.mark_rework()
    if hasattr(t, "fail_reason"):
        t.fail_reason = reason[:200]
    if hasattr(t, "fail_count"):
        t.fail_count = int(getattr(t, "fail_count", 0) or 0) + 1
    if hasattr(t, "inspect_by"):
        t.inspect_by = inspector_id
    if hasattr(t, "inspect_at"):
        t.inspect_at = datetime.now()
    db.flush()
    fail_n = int(getattr(t, "fail_count", 0) or 0)
    escalate = fail_n >= 2
    return {
        "task": t,
        "passed": False,
        "escalate": escalate,
        "fail_count": fail_n,
        "fail_reason": t.fail_reason if hasattr(t, "fail_reason") else reason,
    }


def task_public_dict(t: HousekeepingTask, room: Optional[Room] = None) -> dict:
    d = {
        "id": t.id,
        "hotel_id": t.hotel_id,
        "room_id": t.room_id,
        "task_type": t.task_type,
        "assignee_id": t.assignee_id,
        "priority": t.priority,
        "status": t.status,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "done_at": t.done_at.isoformat() if t.done_at else None,
        "inspect_by": getattr(t, "inspect_by", None),
        "inspect_at": getattr(t, "inspect_at", None).isoformat() if getattr(t, "inspect_at", None) else None,
        "fail_reason": getattr(t, "fail_reason", None),
        "fail_count": getattr(t, "fail_count", 0) or 0,
        "escalate": int(getattr(t, "fail_count", 0) or 0) >= 2,
        "note": getattr(t, "fail_reason", None),
    }
    if room:
        d["room_no"] = room.room_no
        d["room_status"] = normalize(room.status)
    return d


def _norm_task_type(raw: str) -> str:
    s = (raw or "clean").strip().lower()
    s = HK_TYPE_ALIASES.get(s, s)
    if s not in HK_TASK_TYPES:
        raise InvalidStateError(f"不支持的任务类型「{raw}」")
    return s


def _serialize_hk_task(db: Session, t: HousekeepingTask, *, created: Optional[bool] = None) -> dict:
    rm = db.get(Room, t.room_id) if t.room_id else None
    u = db.get(User, t.assignee_id) if t.assignee_id else None
    tt = t.task_type or "clean"
    row = {
        "id": t.id,
        "room_id": t.room_id,
        "room_no": rm.room_no if rm else "—",
        "floor": int(rm.floor) if rm and rm.floor else None,
        "task_type": tt,
        "title": HK_TASK_TYPES.get(tt, tt),
        "assignee_id": t.assignee_id,
        "assignee": u.full_name or u.username if u else "待分配",
        "priority": t.priority or 3,
        "status": t.status,
    }
    if created is not None:
        row["created"] = created
    return row


def create_housekeeping_task(
    db: Session,
    hotel_id: int,
    *,
    room_id: int,
    task_type: str = "clean",
    assignee_id: Optional[int] = None,
    assignee_name: Optional[str] = None,
    priority: Optional[int] = 3,
    reason: str = "",
) -> tuple[HousekeepingTask, bool]:
    """新建保洁工单。同房同类型未完成单幂等返回已有记录。维修单会联动置 OOO。"""
    from rooms.room_ops import set_out_of_order

    tt = _hk_task_service._norm_task_type(task_type)
    rm = db.get(Room, int(room_id))
    if not rm or rm.hotel_id != hotel_id:
        raise InvalidStateError("房间不存在或不属于本店")
    existing = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.room_id == rm.id,
            HousekeepingTask.task_type == tt,
            HousekeepingTask.status.in_(HK_OPENISH),
        )
        .order_by(HousekeepingTask.id.desc())
        .first()
    )
    if existing:
        return (existing, False)
    aid = None
    if assignee_id or assignee_name:
        try:
            aid = _hk_dispatch_service._resolve_assignee_id(
                db, hotel_id, assignee_id=assignee_id, assignee_name=assignee_name
            )
        except HTTPException:
            aid = None
    if not aid:
        aid = _hk_dispatch_service._pick_attendant(db, hotel_id, rm.id)
    pri = int(priority) if priority is not None else 3
    pri = max(1, min(5, pri))
    note = (reason or "").strip()
    t = HousekeepingTask(
        hotel_id=hotel_id,
        room_id=rm.id,
        task_type=tt,
        assignee_id=aid,
        priority=pri,
        status="assigned" if aid else "open",
        created_at=datetime.now(),
        due_at=datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        if datetime.now().hour < 14
        else datetime.now(),
        fail_reason=f"报修：{note}"[:200] if tt == "repair" and note else note[:200] or None,
    )
    db.add(t)
    db.flush()
    if tt == "repair" and normalize(rm.status) != OOO:
        set_out_of_order(db, rm, reason=note or "报修工单", operator_id=None)
    return (t, True)


def create_housekeeping_tasks(db: Session, hotel_id: int, items: list[dict]) -> dict:
    """批量新建。返回 created / skipped / tasks。"""
    if not items:
        raise InvalidStateError("请提供要创建的任务")
    created, skipped, tasks = (0, 0, [])
    for raw in items[:40]:
        if not isinstance(raw, dict):
            continue
        try:
            rid = int(raw.get("room_id"))
        except (TypeError, ValueError):
            continue
        t, is_new = _hk_task_service.create_housekeeping_task(
            db,
            hotel_id,
            room_id=rid,
            task_type=str(raw.get("task_type") or raw.get("type") or "clean"),
            assignee_id=raw.get("assignee_id"),
            assignee_name=raw.get("assignee_name") or raw.get("assignee"),
            priority=raw.get("priority") or 3,
            reason=str(raw.get("reason") or raw.get("note") or raw.get("fail_reason") or ""),
        )
        created += int(is_new)
        skipped += int(not is_new)
        tasks.append(_serialize_hk_task(db, t, created=is_new))
    if not tasks:
        raise InvalidStateError("没有可创建的有效任务（请检查房号）")
    return {"created": created, "skipped": skipped, "count": len(tasks), "tasks": tasks}


def list_housekeeping_tasks(db: Session, hotel_id: int) -> list[dict]:
    """房务任务列表（轻量，供 /housekeeping）。"""
    from api_common import row_to_dict
    from hk.housekeeping_service.board_service import hk_ui_status

    rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(HousekeepingTask.hotel_id == hotel_id)
        .all()
    )
    users = {u.id: u for u in db.query(User).all()}
    out = []
    for t, rm in rows:
        u = users.get(t.assignee_id) if t.assignee_id else None
        tt = t.task_type or "clean"
        out.append(
            dict(
                row_to_dict(t),
                room_no=rm.room_no if rm else None,
                floor=rm.floor if rm else None,
                assignee=(u.full_name or u.username) if u else "待分配",
                title=HK_TYPE_CN.get(tt, tt),
                icon=HK_ICON.get(tt, "cleaning_services"),
                priority_flag=(t.priority or 5) <= 2,
                ui_status=hk_ui_status(t.status),
            )
        )
    return out
