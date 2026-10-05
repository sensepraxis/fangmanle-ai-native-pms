# SPDX-License-Identifier: Apache-2.0
"""Facade module for hk domain.

生成器可产出上方透传包装；文末 ``# --- orchestrated ---`` 为手写编排，勿覆盖。

职责：
  - 调 service 函数 + 透传 BusinessError
  - 写路径编排：事务边界（commit）在此层
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
from infra.commercial_pack import bind as _cbind

_confirm_plan = _cbind("commercial.hk.hk_ai_harness", "confirm_plan")
_generate_plan = _cbind("commercial.hk.hk_ai_harness", "generate_plan")

from hk.housekeeping_service import (
    _on_duty_staff as __on_duty_staff,
)
from hk.housekeeping_service import (
    ai_suggest_dispatch as _ai_suggest_dispatch,
)
from hk.housekeeping_service import (
    assign_task as _assign_task,
)
from hk.housekeeping_service import (
    batch_dispatch as _batch_dispatch,
)
from hk.housekeeping_service import (
    build_housekeeping_ai_assistant as _build_housekeeping_ai_assistant,
)
from hk.housekeeping_service import (
    build_housekeeping_board as _build_housekeeping_board,
)
from hk.housekeeping_service import (
    create_guest_request as _create_guest_request,
)
from hk.housekeeping_service import (
    create_housekeeping_tasks as _create_housekeeping_tasks,
)
from hk.housekeeping_service import (
    finish_clean as _finish_clean,
)
from hk.housekeeping_service import (
    hk_ui_status as _hk_ui_status,
)
from hk.housekeeping_service import (
    ignore_task as _ignore_task,
)
from hk.housekeeping_service import (
    inspect_task as _inspect_task,
)
from hk.housekeeping_service import (
    list_housekeeping_tasks as _list_housekeeping_tasks,
)
from hk.housekeeping_service import (
    list_service_requests as _list_service_requests,
)
from hk.housekeeping_service import (
    start_task as _start_task,
)
from hk.housekeeping_service import (
    task_public_dict as _task_public_dict,
)
from hk.housekeeping_service import (
    urge_task as _urge_task,
)

_narrate_staffing_ai = _cbind("commercial.hk.staffing_ai", "narrate_staffing_ai")

from hk.staffing_service import (
    apply_ai_adjustments as _apply_ai_adjustments,
)
from hk.staffing_service import (
    staffing_board as _staffing_board,
)


def confirm_plan(*args, **kwargs):
    return _confirm_plan(*args, **kwargs)


def generate_plan(*args, **kwargs):
    return _generate_plan(*args, **kwargs)


def _on_duty_staff(*args, **kwargs):
    return __on_duty_staff(*args, **kwargs)


def ai_suggest_dispatch(*args, **kwargs):
    return _ai_suggest_dispatch(*args, **kwargs)


def build_housekeeping_ai_assistant(*args, **kwargs):
    return _build_housekeeping_ai_assistant(*args, **kwargs)


def build_housekeeping_board(*args, **kwargs):
    return _build_housekeeping_board(*args, **kwargs)


def create_guest_request(*args, **kwargs):
    return _create_guest_request(*args, **kwargs)


def create_housekeeping_tasks(*args, **kwargs):
    return _create_housekeeping_tasks(*args, **kwargs)


def hk_ui_status(*args, **kwargs):
    return _hk_ui_status(*args, **kwargs)


def narrate_staffing_ai(*args, **kwargs):
    return _narrate_staffing_ai(*args, **kwargs)


def apply_ai_adjustments(*args, **kwargs):
    return _apply_ai_adjustments(*args, **kwargs)


def staffing_board(*args, **kwargs):
    return _staffing_board(*args, **kwargs)


def staffing_board_tx(*args, **kwargs):
    """排班看板可能副作用写库，统一在此 commit。"""
    db = args[0]
    try:
        data = _staffing_board(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


# --- orchestrated ---
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import Room, User


def _task_view(db: Session, t) -> dict:
    rm = db.get(Room, t.room_id) if t.room_id else None
    d = _task_public_dict(t, rm)
    if t.assignee_id:
        u = db.get(User, t.assignee_id)
        d["assignee"] = (u.full_name or u.username) if u else d.get("assignee")
    if rm:
        d["room_status"] = rm.status
    return d


def start_hk_task(
    db: Session,
    tid: int,
    *,
    operator_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    assignee_name: Optional[str] = None,
) -> dict:
    if tid <= 0:
        raise ValidationError("无效任务，无法写回")
    try:
        t = _start_task(
            db,
            tid,
            operator_id=operator_id,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
        )
        db.commit()
        return _task_view(db, t)
    except Exception:
        db.rollback()
        raise


def assign_hk_task(
    db: Session,
    tid: int,
    *,
    assignee_id: Optional[int] = None,
    assignee_name: Optional[str] = None,
) -> dict:
    if tid <= 0:
        raise ValidationError("无效任务，无法写回")
    try:
        t = _assign_task(db, tid, assignee_id=assignee_id, assignee_name=assignee_name)
        db.commit()
        return _task_view(db, t)
    except Exception:
        db.rollback()
        raise


def ignore_hk_task(
    db: Session,
    tid: int,
    *,
    reason: str = "",
    operator_id: Optional[int] = None,
) -> dict:
    if tid <= 0:
        raise ValidationError("无效任务，无法写回")
    try:
        t = _ignore_task(db, tid, reason=reason, operator_id=operator_id)
        db.commit()
        return _task_view(db, t)
    except Exception:
        db.rollback()
        raise


def urge_hk_task(db: Session, tid: int) -> dict:
    if tid <= 0:
        raise ValidationError("无效任务，无法写回")
    try:
        t = _urge_task(db, tid)
        db.commit()
        return _task_view(db, t)
    except Exception:
        db.rollback()
        raise


def finish_hk_task(
    db: Session,
    tid: int,
    *,
    to_status: str = "VC",
    operator_id: Optional[int] = None,
) -> dict:
    if tid <= 0:
        raise ValidationError("合成任务无法写回，请刷新作业台获取真实任务")
    try:
        t = _finish_clean(db, tid, to_status=to_status, operator_id=operator_id)
        db.commit()
        return _task_view(db, t)
    except Exception:
        db.rollback()
        raise


def inspect_hk_task(
    db: Session,
    tid: int,
    *,
    passed: bool = True,
    inspector_id: Optional[int] = None,
    fail_reason: str = "",
    fail_items: Optional[list] = None,
) -> dict:
    try:
        result = _inspect_task(
            db,
            tid,
            passed=passed,
            inspector_id=inspector_id,
            fail_reason=fail_reason,
            fail_items=fail_items or [],
        )
        db.commit()
        t = result["task"]
        out = _task_view(db, t)
        out["passed"] = result.get("passed")
        out["escalate"] = result.get("escalate", False)
        out["fail_count"] = result.get("fail_count")
        out["fail_reason"] = result.get("fail_reason") or out.get("fail_reason")
        out["room_status"] = result.get("room_status") or out.get("room_status")
        return out
    except Exception:
        db.rollback()
        raise


def batch_dispatch_hk(
    db: Session,
    hotel_id: int,
    task_ids: list,
    *,
    mode: str = "single",
    assignee_id: Any = None,
    preview: bool = False,
    operator_id: Optional[int] = None,
    notify: bool = True,
) -> dict:
    try:
        result = _batch_dispatch(
            db,
            hotel_id,
            task_ids,
            mode=mode,
            assignee_id=assignee_id,
            preview=preview,
            operator_id=operator_id,
            notify=notify and not preview,
        )
        if not preview:
            db.commit()
        result["staff"] = __on_duty_staff(db, hotel_id)
        return result
    except Exception:
        db.rollback()
        raise


def create_hk_tasks(db: Session, hotel_id: int, items: list) -> Any:
    try:
        data = _create_housekeeping_tasks(db, hotel_id, items)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def create_guest_request_tx(*args, **kwargs):
    db = args[0]
    try:
        data = _create_guest_request(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def confirm_plan_tx(*args, **kwargs):
    db = args[0]
    try:
        data = _confirm_plan(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def apply_ai_adjustments_tx(*args, **kwargs):
    db = args[0]
    try:
        data = _apply_ai_adjustments(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def ai_suggest_dispatch_tx(*args, **kwargs):
    db = args[0]
    try:
        data = _ai_suggest_dispatch(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def upsert_staffing_shift(
    db: Session,
    hotel_id: int,
    *,
    user_id: int,
    shift_date: date,
    shift: str = "morning",
    view: str = "week",
    start: Optional[date] = None,
) -> dict:
    from hk.staffing_service import staffing_board, upsert_shift

    try:
        upsert_shift(
            db,
            hotel_id,
            user_id=user_id,
            shift_date=shift_date,
            shift=shift,
            note="[手改]",
            source="manual",
        )
        db.commit()
        return staffing_board(db, hotel_id, view=view, start=start)
    except Exception:
        db.rollback()
        raise


def copy_staffing_week(
    db: Session,
    hotel_id: int,
    *,
    week_start: date,
    view: str = "week",
) -> dict:
    from hk.staffing_service import copy_prev_week, staffing_board

    try:
        result = copy_prev_week(db, hotel_id, week_start)
        db.commit()
        board = staffing_board(db, hotel_id, view=view, start=week_start)
        board["copy"] = result
        return board
    except Exception:
        db.rollback()
        raise


def save_staffing_template(
    db: Session,
    hotel_id: int,
    *,
    week_start: date,
    name: str = "默认周模板",
) -> Any:
    from hk.staffing_service import save_week_template

    try:
        data = save_week_template(db, hotel_id, week_start, name)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def add_staffing_member(
    db: Session,
    hotel_id: int,
    *,
    user_id: int,
    range_start: date,
    range_end: date,
    view: str = "week",
) -> dict:
    from hk.staffing_service import add_staff_to_roster, staffing_board

    try:
        add_staff_to_roster(db, hotel_id, user_id, range_start, range_end)
        db.commit()
        return staffing_board(db, hotel_id, view=view, start=range_start)
    except Exception:
        db.rollback()
        raise


def decide_shift_request(
    db: Session,
    hotel_id: int,
    rid: int,
    *,
    approved: bool,
    view: str = "week",
    start: Optional[date] = None,
) -> dict:
    from hk.staffing_service import decide_shift_request as _decide
    from hk.staffing_service import staffing_board

    try:
        _decide(db, hotel_id, rid, approved=approved)
        db.commit()
        return staffing_board(db, hotel_id, view=view, start=start)
    except Exception:
        db.rollback()
        raise


def list_housekeeping_tasks(db: Session, hotel_id: int):
    return _list_housekeeping_tasks(db, hotel_id)


def list_service_requests(db: Session, hotel_id: int):
    return _list_service_requests(db, hotel_id)
