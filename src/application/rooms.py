# SPDX-License-Identifier: Apache-2.0
"""Facade module for rooms domain.

生成器可产出上方透传包装；文末 ``# --- orchestrated ---`` 为手写编排，勿覆盖。
"""

from __future__ import annotations

# 业务异常（透传用）
from domain import (  # noqa: F401
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from rooms.maintenance_bundle import (
    list_room_maintenance_bundle as _list_room_maintenance_bundle,
)
from rooms.room_board_service import (
    build_inventory_calendar as _build_inventory_calendar,
)
from rooms.room_board_service import (
    build_inventory_forecast as _build_inventory_forecast,
)
from rooms.room_board_service import (
    build_inventory_forecast_day_detail as _build_inventory_forecast_day_detail,
)
from rooms.room_board_service import (
    build_room_maintain_advice as _build_room_maintain_advice,
)
from rooms.room_board_service import (
    build_rooms_list as _build_rooms_list,
)
from rooms.room_board_service import (
    set_room_status as _set_room_status,
)
from rooms.room_ops import (
    mark_due_out as _mark_due_out,
)
from rooms.room_ops import (
    night_audit_room_flip as _night_audit_room_flip,
)
from rooms.room_ops import (
    oversell_snapshot as _oversell_snapshot,
)
from rooms.room_ops import (
    room_status_history as _room_status_history,
)
from rooms.room_status import (
    public_room_dict as _public_room_dict,
)


def list_room_maintenance_bundle(*args, **kwargs):
    """薄包装 — 调 rooms.maintenance_bundle.list_room_maintenance_bundle。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_room_maintenance_bundle(*args, **kwargs)


def build_inventory_calendar(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.build_inventory_calendar。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_inventory_calendar(*args, **kwargs)


def build_inventory_forecast(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.build_inventory_forecast。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_inventory_forecast(*args, **kwargs)


def build_inventory_forecast_day_detail(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.build_inventory_forecast_day_detail。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_inventory_forecast_day_detail(*args, **kwargs)


def build_room_maintain_advice(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.build_room_maintain_advice。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_room_maintain_advice(*args, **kwargs)


def build_rooms_list(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.build_rooms_list。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_rooms_list(*args, **kwargs)


def set_room_status(*args, **kwargs):
    """薄包装 — 调 rooms.room_board_service.set_room_status。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _set_room_status(*args, **kwargs)


def mark_due_out(*args, **kwargs):
    """薄包装 — 调 rooms.room_ops.mark_due_out。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _mark_due_out(*args, **kwargs)


def night_audit_room_flip(*args, **kwargs):
    """薄包装 — 调 rooms.room_ops.night_audit_room_flip。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _night_audit_room_flip(*args, **kwargs)


def oversell_snapshot(*args, **kwargs):
    """薄包装 — 调 rooms.room_ops.oversell_snapshot。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _oversell_snapshot(*args, **kwargs)


def room_status_history(*args, **kwargs):
    """薄包装 — 调 rooms.room_ops.room_status_history。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _room_status_history(*args, **kwargs)


def public_room_dict(*args, **kwargs):
    """薄包装 — 调 rooms.room_status.public_room_dict。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _public_room_dict(*args, **kwargs)


# --- orchestrated ---
from typing import Optional

from sqlalchemy.orm import Session

from models import Room


def mark_due_out_room(
    db: Session,
    room_id: int,
    *,
    reason: str = "前台标记预离",
    operator_id: Optional[int] = None,
) -> dict:
    """标记预离 → commit → 公开房态。"""
    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("room not found")
    try:
        _mark_due_out(db, r, reason=reason, operator_id=operator_id)
        db.commit()
        return _public_room_dict(r)
    except Exception:
        db.rollback()
        raise


def transition_room(
    db: Session,
    room_id: int,
    *,
    to_status: str,
    reason: str = "",
    operator_id: Optional[int] = None,
    force: bool = False,
) -> dict:
    """通用房态跳转 → commit → 公开房态。"""
    from rooms.room_status import transition

    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("room not found")
    try:
        transition(
            db,
            r,
            to_status,
            reason=reason,
            operator_id=operator_id,
            force=force,
        )
        db.commit()
        return _public_room_dict(r)
    except Exception:
        db.rollback()
        raise


# --- 房间档案 / 房型台账（写路径 commit 在此）---
from rooms.room_master_service import (
    create_room_master as _create_room_master,
)
from rooms.room_master_service import (
    create_room_type as _create_room_type,
)
from rooms.room_master_service import (
    delete_room_master as _delete_room_master,
)
from rooms.room_master_service import (
    delete_room_type as _delete_room_type,
)
from rooms.room_master_service import (
    list_room_masters as _list_room_masters,
)
from rooms.room_master_service import (
    list_room_types as _list_room_types,
)
from rooms.room_master_service import (
    room_detail_bundle as _room_detail_bundle,
)
from rooms.room_master_service import (
    update_room_master as _update_room_master,
)
from rooms.room_master_service import (
    update_room_type as _update_room_type,
)


def list_room_masters(db: Session, hotel_id: int, *, room_type_id=None, q=None) -> list:
    return _list_room_masters(db, hotel_id, room_type_id=room_type_id, q=q)


def create_room_master(db: Session, hotel_id: int, payload: dict) -> dict:
    try:
        out = _create_room_master(db, hotel_id, payload)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def update_room_master(db: Session, room_id: int, payload: dict) -> dict:
    try:
        out = _update_room_master(db, room_id, payload)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def delete_room_master(db: Session, room_id: int) -> dict:
    try:
        out = _delete_room_master(db, room_id)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def room_detail_bundle(db: Session, room_id: int) -> dict:
    return _room_detail_bundle(db, room_id)


def list_room_types(db: Session, hotel_id: int) -> list:
    """列表；缺字段回填时一并 commit。"""
    try:
        out = _list_room_types(db, hotel_id)
        if db.new or db.dirty or db.deleted:
            db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def create_room_type(db: Session, hotel_id: int, payload: dict) -> dict:
    try:
        out = _create_room_type(db, hotel_id, payload)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def update_room_type(db: Session, type_id: int, payload: dict) -> dict:
    try:
        out = _update_room_type(db, type_id, payload)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def delete_room_type(db: Session, type_id: int) -> dict:
    try:
        out = _delete_room_type(db, type_id)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise
