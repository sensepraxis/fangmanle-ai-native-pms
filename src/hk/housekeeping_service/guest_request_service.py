# SPDX-License-Identifier: Apache-2.0
# hk.housekeeping_service.guest_request_service — auto-split by AST

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
from hk.housekeeping_service import task_service as _hk_task_service


def create_guest_request(
    db: Session, hotel_id: int, *, room_id: int, content: str, assignee_id: Optional[int] = None, priority: int = 3
) -> dict:
    """客中请求一键录入：写 ServiceRequest，并同步一张 service 保洁单。"""
    from models import ServiceRequest

    text = (content or "").strip()
    if not text:
        raise InvalidStateError("请填写请求内容")
    rm = db.get(Room, int(room_id))
    if not rm or rm.hotel_id != hotel_id:
        raise InvalidStateError("房间不存在或不属于本店")
    aid = None
    if assignee_id:
        on_duty = {s["id"] for s in _hk_dispatch_service._on_duty_staff(db, hotel_id)}
        if int(assignee_id) not in on_duty:
            raise InvalidStateError("只能派给当日在班人员（休息不可派）")
        aid = int(assignee_id)
    pri = max(1, min(5, int(priority or 3)))
    sr = ServiceRequest(
        hotel_id=hotel_id,
        room_id=rm.id,
        content=text[:255],
        priority=pri,
        status="open",
        assignee_id=None,
        created_at=datetime.now(),
    )
    sr.assign(aid)
    db.add(sr)
    db.flush()
    task, task_new = _hk_task_service.create_housekeeping_task(
        db, hotel_id, room_id=rm.id, task_type="service", assignee_id=aid, priority=pri
    )
    u = db.get(User, aid) if aid else None
    return {
        "id": sr.id,
        "room_id": rm.id,
        "room_no": rm.room_no,
        "content": sr.content,
        "priority": pri,
        "status": sr.status,
        "assignee_id": aid,
        "assignee": u.full_name or u.username if u else "待分配",
        "task_id": task.id,
        "task_created": task_new,
    }


def list_service_requests(db: Session, hotel_id: int) -> list[dict]:
    """客需工单列表。"""
    from api_common import row_to_dict
    from models import ServiceRequest

    rows = (
        db.query(ServiceRequest, Room, User)
        .outerjoin(Room, ServiceRequest.room_id == Room.id)
        .outerjoin(User, ServiceRequest.assignee_id == User.id)
        .filter(ServiceRequest.hotel_id == hotel_id)
        .order_by(ServiceRequest.priority.asc(), ServiceRequest.id.desc())
        .all()
    )
    out = []
    for sr, rm, u in rows:
        d = row_to_dict(sr)
        d["room_no"] = rm.room_no if rm else None
        d["room"] = d["room_no"]
        d["assignee"] = (u.full_name or u.username) if u else "未分配"
        d["open"] = (sr.status or "") not in ("done", "closed", "resolved")
        d["msg"] = sr.content or ""
        d["time"] = sr.created_at.strftime("%H:%M") if sr.created_at else "—"
        d["channel"] = "微信" if (sr.id or 0) % 2 == 0 else "前台"
        out.append(d)
    return out
