# SPDX-License-Identifier: Apache-2.0
# hk.housekeeping_service.repair_service — auto-split by AST

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

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models as _models
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


def ensure_checkout_clean_task(db: Session, *, hotel_id: int, room_id: int, priority: int = 1) -> HousekeepingTask:
    """退房后确保有一条未完成的退房清洁单（幂等）；指派当日在岗人员。"""
    openish = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.room_id == room_id,
            HousekeepingTask.task_type.in_(("turn", "clean")),
            HousekeepingTask.status.in_(("open", "assigned", "in_progress", "pending_inspect", "rework")),
        )
        .first()
    )
    if openish:
        if not openish.assignee_id:
            aid = _hk_dispatch_service._pick_attendant(db, hotel_id, room_id)
            if aid:
                openish.assignee_id = aid
                openish.status = "assigned"
                db.flush()
        return openish
    aid = _hk_dispatch_service._pick_attendant(db, hotel_id, room_id)
    t = HousekeepingTask(
        hotel_id=hotel_id,
        room_id=room_id,
        task_type="turn",
        assignee_id=aid,
        priority=priority,
        created_at=datetime.now(),
    )
    t.status = "assigned" if t.assignee_id else "open"
    db.add(t)
    db.flush()
    return t


def ensure_repair_task(
    db: Session, *, hotel_id: int, room_id: int, reason: str = "", priority: int = 1
) -> HousekeepingTask:
    """维修房确保有一条未完成维修工单（幂等）。原因写入 fail_reason 供列表展示。"""
    openish_st = ("open", "assigned", "in_progress", "pending_inspect", "rework")
    openish = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.room_id == room_id,
            HousekeepingTask.task_type == "repair",
            HousekeepingTask.status.in_(openish_st),
        )
        .first()
    )
    note = (reason or "设备故障").strip()[:180]
    if openish:
        if hasattr(openish, "fail_reason") and note:
            openish.fail_reason = f"报修：{note}"[:200]
        if not openish.assignee_id:
            aid = _hk_dispatch_service._pick_attendant(db, hotel_id, room_id)
            if aid:
                openish.assignee_id = aid
                openish.status = "assigned"
        db.flush()
        return openish
    aid = _hk_dispatch_service._pick_attendant(db, hotel_id, room_id)
    t = HousekeepingTask(
        hotel_id=hotel_id,
        room_id=room_id,
        task_type="repair",
        assignee_id=aid,
        priority=priority,
        status="assigned" if aid else "open",
        created_at=datetime.now(),
        fail_reason=f"报修：{note}"[:200],
    )
    db.add(t)
    db.flush()
    return t


def close_repair_tasks_for_room(db: Session, *, hotel_id: int, room_id: int, note: str = "维修完成") -> int:
    """关闭该房未完成维修单。"""
    openish_st = ("open", "assigned", "in_progress", "pending_inspect", "rework")
    rows = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.room_id == room_id,
            HousekeepingTask.task_type == "repair",
            HousekeepingTask.status.in_(openish_st),
        )
        .all()
    )
    n = 0
    for t in rows:
        t.status = "done"
        t.done_at = datetime.now()
        if hasattr(t, "fail_reason") and note:
            prev = (t.fail_reason or "").strip()
            t.fail_reason = f"{prev} · {note}".strip(" ·")[:200] if prev else note[:200]
        n += 1
    if n:
        db.flush()
    return n


def complete_repair_and_clear_ooo(
    db: Session, task: HousekeepingTask, *, to_status: str = VC, operator_id: Optional[int] = None
) -> dict:
    """维修完成：关单 + 解除维修房。"""
    from rooms.room_ops import clear_out_of_order

    task.status = "done"
    task.done_at = datetime.now()
    room_out = None
    if task.room_id:
        rm = db.get(Room, task.room_id)
        if rm and normalize(rm.status) == OOO:
            dest = normalize(to_status) if to_status else VC
            if dest not in (VC, VD):
                dest = VC
            clear_out_of_order(db, rm, to_status=dest, reason="维修工单完成", operator_id=operator_id)
            room_out = rm.status
    db.flush()
    return {"task": task, "room_status": room_out}
