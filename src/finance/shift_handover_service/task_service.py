# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: task_service。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from domain import NotFoundError

# 同包 cross-import
from finance.shift_handover_service._common import _log, _mask_name
from infra.i18n import t
from models import (
    Channel,
    Deposit,
    DepositLedgerEntry,
    FinanceReport,
    Guest,
    GuestTag,
    Order,
    Payment,
    Reservation,
    Room,
    ServiceRequest,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    Supply,
    TagDefinition,
    User,
)


def _guest_situations(db: Session, hotel_id: int) -> list[dict]:
    out: list[dict] = []
    today = date.today()
    vip_tag = db.query(TagDefinition).filter(TagDefinition.code == "high_value").first()
    checked = (
        db.query(Order, Guest, Room, Reservation)
        .outerjoin(Guest, Guest.id == Order.guest_id)
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .outerjoin(Room, Room.id == Reservation.room_id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .limit(12)
        .all()
    )
    for order, guest, room, _res in checked:
        room_no = room.room_no if room else "—"
        gname = _mask_name(guest.name if guest else order.note or t("客人"))
        gid = guest.id if guest else None
        oid = order.id
        if guest and vip_tag:
            has_vip = db.query(GuestTag).filter_by(guest_id=guest.id, tag_id=vip_tag.id).first()
            if has_vip:
                content = (order.note or "").strip()
                if not content:
                    continue
                out.append(
                    {
                        "type": "vip",
                        "type_label": t("VIP 在店"),
                        "room_no": room_no,
                        "guest_token": gname,
                        "guest_id": gid,
                        "order_id": oid,
                        "title": (
                            t("{guest} · {room} 房 · VIP", guest=gname, room=room_no)
                            if room_no not in (None, "", "—")
                            else t("{guest} · VIP 在店", guest=gname)
                        ),
                        "content": content[:120],
                    }
                )
                continue
        note = (order.note or "").lower()
        if any(k in note for k in ("素食", "过敏", "轮椅", "婴儿", "宠物", "庆生", "宗教")):
            out.append(
                {
                    "type": "special",
                    "type_label": t("特殊需求"),
                    "room_no": room_no,
                    "guest_token": gname,
                    "guest_id": gid,
                    "order_id": oid,
                    "title": t("{guest} · {room} 房 · 特殊需求", guest=gname, room=room_no),
                    "content": (order.note or "")[:120],
                }
            )
    open_sr = (
        db.query(ServiceRequest, Room)
        .outerjoin(Room, Room.id == ServiceRequest.room_id)
        .filter(ServiceRequest.hotel_id == hotel_id, ServiceRequest.status.in_(("open", "assigned", "in_progress")))
        .order_by(ServiceRequest.priority.asc())
        .limit(6)
        .all()
    )
    for sr, rm in open_sr:
        content = sr.content or ""
        room_no = rm.room_no if rm else "—"
        is_complaint = sr.priority and sr.priority <= 1 or any(k in content for k in ("投诉", "客诉", "不满"))
        out.append(
            {
                "type": "complaint" if is_complaint else "special",
                "type_label": t("客诉进行中") if is_complaint else t("在店客需"),
                "room_no": room_no,
                "guest_token": t("在住客人"),
                "title": t("{room} 房 · {need}", room=room_no, need=(content[:16] or t("客需"))),
                "content": content[:120],
            }
        )
    inbound = (
        db.query(Order, Guest)
        .outerjoin(Guest, Guest.id == Order.guest_id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("confirmed", "pending")),
            Order.check_in >= today,
            Order.check_in <= today + timedelta(days=1),
        )
        .order_by(Order.check_in.asc())
        .limit(4)
        .all()
    )
    for order, guest in inbound:
        gname = _mask_name(guest.name if guest else t("客人"))
        arr = order.arrival_time or "14:00"
        note = (order.note or "").strip()
        item: dict = {
            "type": "inbound",
            "type_label": t("即将到店"),
            "room_no": "—",
            "guest_token": gname,
            "guest_id": guest.id if guest else None,
            "order_id": order.id,
            "title": t("{guest} · {date} 到店 · {time}", guest=gname, date=order.check_in, time=arr),
        }
        if note:
            item["content"] = note[:120]
        out.append(item)
    return out[:8]


def _build_tasks(db: Session, hotel_id: int, shift_no: int) -> list[dict]:
    tasks: list[dict] = []
    open_sr = (
        db.query(ServiceRequest, Room)
        .outerjoin(Room, Room.id == ServiceRequest.room_id)
        .filter(ServiceRequest.hotel_id == hotel_id, ServiceRequest.status.in_(("open", "assigned", "in_progress")))
        .order_by(ServiceRequest.priority.asc())
        .limit(5)
        .all()
    )
    for sr, rm in open_sr:
        pri = "P0" if (sr.priority or 9) <= 1 else "P1" if (sr.priority or 9) <= 2 else "P2"
        owner_name = "—"
        if sr.assignee_id:
            u = db.get(User, sr.assignee_id)
            if u:
                owner_name = u.full_name or u.username or owner_name
        due_at = sr.created_at.isoformat(timespec="minutes") if sr.created_at else None
        tasks.append(
            {
                "priority": pri,
                "content": t(
                    "{room} 房 · {need}",
                    room=(rm.room_no if rm else "—"),
                    need=(sr.content or t("客需"))[:40],
                ),
                "owner_name": owner_name,
                "due_at": due_at,
                "status": "open",
                "linked_order_id": sr.order_id,
                "can_escalate": pri == "P0",
            }
        )
    from finance.ar_ap_service import list_ar_ap_todos

    for td in list_ar_ap_todos(db, hotel_id)[:2]:
        tasks.append(
            {
                "priority": "P1",
                "content": td.get("title") or td.get("detail") or t("应收跟进"),
                "owner_name": t("财务"),
                "due_at": td.get("created_at"),
                "status": "open",
                "linked_order_id": td.get("ar_id"),
                "can_escalate": False,
            }
        )
    late = (
        db.query(Order, Room, Reservation)
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .outerjoin(Room, Room.id == Reservation.room_id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in", Order.check_out <= date.today())
        .limit(3)
        .all()
    )
    for order, room, _ in late:
        due_at = None
        if order.check_out:
            due_at = datetime.combine(order.check_out, datetime.min.time().replace(hour=12)).isoformat(
                timespec="minutes"
            )
        tasks.append(
            {
                "priority": "P1",
                "content": t("{room} 延迟退房跟进", room=(room.room_no if room else "—")),
                "owner_name": t("前台主管"),
                "due_at": due_at,
                "status": "open",
                "linked_order_id": order.id,
                "can_escalate": False,
            }
        )
    return tasks


def _carryover_tasks(db: Session, hotel_id: int, current_id: int | None) -> list[dict]:
    q = (
        db.query(ShiftHandoverTask, ShiftHandover)
        .join(ShiftHandover, ShiftHandover.id == ShiftHandoverTask.handover_id)
        .filter(ShiftHandover.hotel_id == hotel_id, ShiftHandoverTask.status != "done")
    )
    if current_id:
        q = q.filter(ShiftHandoverTask.handover_id != current_id)
    rows = q.order_by(ShiftHandoverTask.id.desc()).limit(8).all()
    out = []
    now = datetime.now()
    for r, ho in rows:
        created = r.created_at or now
        hours = max(0, int((now - created).total_seconds() // 3600))
        st = r.status or "open"
        out.append(
            {
                "id": r.id,
                "priority": r.priority or "P2",
                "content": r.content or "",
                "owner_name": r.owner_name or "—",
                "due_at": r.due_at.isoformat(timespec="minutes") if r.due_at else None,
                "status": st,
                "linked_order_id": r.linked_order_id,
                "can_escalate": False,
                "carryover": True,
                "pending": st not in ("done",),
                "shift_no": r.source_shift_no or ho.shift_no,
                "hours_ago": hours,
            }
        )
    return out


def escalate_task(
    db: Session,
    hotel_id: int,
    handover_id: int,
    task_index: int,
    *,
    operator_id: int | None = None,
    operator_name: str = "",
) -> dict:
    """把本班 P0 待办升级给店长；写审计并要求店长审核。"""
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError(t("交班记录不存在"))

    tasks = tasks_for_display(db, hotel_id, row)
    if task_index < 0 or task_index >= len(tasks):
        raise NotFoundError(t("待办不存在"))
    item = tasks[task_index]
    now = datetime.now()
    content = (item.get("content") or "").strip() or t("P0 待办")

    existing = (
        db.query(ShiftHandoverTask)
        .filter_by(handover_id=handover_id, hotel_id=hotel_id, content=content)
        .order_by(ShiftHandoverTask.id.desc())
        .first()
    )
    if existing:
        existing.status = "escalated"
        existing.escalated_at = now
        existing.priority = existing.priority or "P0"
        existing.owner_name = t("店长")
    else:
        db.add(
            ShiftHandoverTask(
                handover_id=handover_id,
                hotel_id=hotel_id,
                priority=item.get("priority") or "P0",
                content=content,
                owner_name=t("店长"),
                due_at=now + timedelta(minutes=10),
                status="escalated",
                linked_order_id=item.get("linked_order_id"),
                source_shift_no=row.shift_no,
                escalated_at=now,
                created_by="manual",
            )
        )

    claims: dict = {}
    if row.task_claims:
        try:
            parsed = json.loads(row.task_claims)
            if isinstance(parsed, dict):
                claims = parsed
        except Exception:
            claims = {}
    claims[str(task_index)] = "escalated"
    row.task_claims = json.dumps(claims, ensure_ascii=False)
    row.manager_required = True
    _log(
        db,
        handover_id,
        hotel_id,
        "escalate_task",
        operator_id,
        operator_name,
        {"task_index": task_index, "content": content[:80]},
    )
    db.commit()
    return {"ok": True, "task_index": task_index, "manager_required": True}


def _jload_snapshot(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except Exception:
        return default
    return parsed if parsed else default


def _stable_situation_key(s: dict, idx: int) -> str:
    gid = s.get("guest_id")
    oid = s.get("order_id")
    if gid:
        return f"{s.get('type')}:{gid}"
    if oid:
        return f"{s.get('type')}:o{oid}"
    return f"{s.get('type')}:{idx}"


def guest_situations_for_display(db: Session, hotel_id: int, handover: ShiftHandover) -> list[dict]:
    """优先已确认快照，否则规则聚合；不依赖商业包 / LLM。"""
    snap = _jload_snapshot(handover.guest_situations_snapshot, None)
    if isinstance(snap, list) and snap:
        return [
            {**s, "key": s.get("key") or _stable_situation_key(s, i), "ai_generated": True} for i, s in enumerate(snap)
        ]
    raw = _guest_situations(db, hotel_id)
    return [{**s, "key": _stable_situation_key(s, i), "ai_generated": False} for i, s in enumerate(raw)]


def tasks_for_display(db: Session, hotel_id: int, handover: ShiftHandover) -> list[dict]:
    """持久化待办 + 规则动态待办合并（去重）；不依赖商业包。"""
    persisted = (
        db.query(ShiftHandoverTask)
        .filter_by(handover_id=handover.id, status="open")
        .order_by(ShiftHandoverTask.id.asc())
        .all()
    )
    out: list[dict] = []
    seen: set[str] = set()
    for t in persisted:
        key = (t.content or "")[:40]
        seen.add(key)
        out.append(
            {
                "priority": t.priority,
                "content": t.content,
                "owner_name": t.owner_name or "—",
                "due_at": t.due_at.isoformat(timespec="minutes") if t.due_at else None,
                "status": t.status,
                "linked_order_id": t.linked_order_id,
                "can_escalate": t.priority == "P0",
                "ai_generated": t.created_by == "ai_agent",
                "task_type": t.task_type or "normal",
                "source": t.source,
            }
        )
    for t in _build_tasks(db, hotel_id, handover.shift_no or 1):
        key = (t.get("content") or "")[:40]
        if key in seen:
            continue
        out.append({**t, "ai_generated": False, "task_type": "normal"})
    return out
