# SPDX-License-Identifier: Apache-2.0
"""
房态状态机入口（VC/VD/OCC/EA/DO/OOO/BLK）。

规则事实源：``rooms.room_status_machine``（Enum + ALLOWED_TRANSITIONS）。
本模块保留常量/兼容 API，并提供唯一写库入口 ``transition``（写日志 + emit）。
"""

from __future__ import annotations

from typing import Optional, Set

from sqlalchemy.orm import Session

from domain import InvalidStateError
from models import Room, RoomStatusLog
from rooms.room_status_machine import (
    ALLOWED_TRANSITIONS,
    RoomStatus,
)
from rooms.room_status_machine import (
    CHECKIN_OK as _CHECKIN_OK_ENUM,
)
from rooms.room_status_machine import (
    LEGACY_MAP as _MACHINE_LEGACY,
)
from rooms.room_status_machine import (
    SELLABLE as _SELLABLE_ENUM,
)
from rooms.room_status_machine import (
    STATUS_CN as _MACHINE_STATUS_CN,
)
from rooms.room_status_machine import (
    can_checkin as _machine_can_checkin,
)
from rooms.room_status_machine import (
    can_transition as _machine_can_transition,
)
from rooms.room_status_machine import (
    is_sellable as _machine_is_sellable,
)
from rooms.room_status_machine import (
    label as _machine_label,
)
from rooms.room_status_machine import (
    normalize as _machine_normalize,
)

# 标准码（字符串常量，兼容历史 import）
VC, VD, OCC, EA, DO, OOO, BLK = "VC", "VD", "OCC", "EA", "DO", "OOO", "BLK"

CANONICAL = frozenset({e.value for e in RoomStatus})

LEGACY_MAP = dict(_MACHINE_LEGACY)
STATUS_CN = dict(_MACHINE_STATUS_CN)

# 合法转换：由 machine 生成 str→set[str]，兼容旧代码
ALLOWED: dict[str, Set[str]] = {src.value: {dst.value for dst in dsts} for src, dsts in ALLOWED_TRANSITIONS.items()}

SELLABLE = frozenset(s.value for s in _SELLABLE_ENUM)
CHECKIN_OK = frozenset(s.value for s in _CHECKIN_OK_ENUM)


def can_checkin(status: Optional[str]) -> bool:
    return _machine_can_checkin(status)


def is_physically_unavailable(status: Optional[str]) -> bool:
    return normalize(status) in (OOO, BLK)


def normalize(status: Optional[str]) -> str:
    return _machine_normalize(status)


def is_sellable(status: Optional[str]) -> bool:
    return _machine_is_sellable(status)


def label(status: Optional[str]) -> str:
    return _machine_label(status)


def public_room_dict(room: Room) -> dict:
    st = normalize(room.status)
    d = {
        "id": room.id,
        "hotel_id": room.hotel_id,
        "room_type_id": room.room_type_id,
        "room_no": room.room_no,
        "building": room.building,
        "floor": room.floor,
        "status": st,
        "status_label": label(st),
        "sellable": st in SELLABLE,
        "status_note": getattr(room, "status_note", None),
        "status_until": (room.status_until.isoformat() if getattr(room, "status_until", None) else None),
        # 兼容旧前端筛选
        "status_legacy": {
            VC: "vacant",
            VD: "dirty",
            OCC: "occupied",
            EA: "occupied",
            DO: "occupied",
            OOO: "ooo",
            BLK: "ooo",
        }.get(st, "vacant"),
    }
    return d


def transition(
    db: Session,
    room: Room,
    to_status: str,
    *,
    reason: str = "",
    operator_id: Optional[int] = None,
    force: bool = False,
) -> Room:
    """唯一合法房态变更入口（写 RoomStatusLog + emit）。模型上的 ``Room.transition_to`` 仅改字段。"""
    dest = normalize(to_status)
    if dest not in CANONICAL:
        raise InvalidStateError(f"未知房态「{to_status}」")
    cur = normalize(room.status)
    if cur == dest and not force:
        room.status = dest  # 顺带纠正遗留写法
        return room
    if not force and not _machine_can_transition(RoomStatus(cur), RoomStatus(dest)):
        raise InvalidStateError(
            f"房态不可从 {label(cur)}({cur}) 直接变为 {label(dest)}({dest})",
        )
    prev = room.status
    room.status = dest
    db.add(
        RoomStatusLog(
            room_id=room.id,
            from_status=prev,
            to_status=dest,
            operator_id=operator_id,
            reason=(reason or "")[:120],
        )
    )
    db.flush()
    if normalize(prev) != dest or force:
        from events import emit

        emit(
            "room.status_changed",
            {
                "hotel_id": room.hotel_id,
                "room_id": room.id,
                "from_status": prev,
                "to_status": dest,
                "reason": reason or "",
                "operator_id": operator_id,
            },
        )
    return room


def migrate_room_statuses(db: Session, hotel_id: Optional[int] = None) -> int:
    """把遗留英文状态批量映射为标准码。"""
    q = db.query(Room)
    if hotel_id:
        q = q.filter_by(hotel_id=hotel_id)
    n = 0
    for r in q.all():
        canon = normalize(r.status)
        if r.status != canon:
            r.status = canon
            n += 1
    if n:
        db.flush()
    return n
