# SPDX-License-Identifier: Apache-2.0
"""Facade module for guests domain.

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
from guests.crm_defaults import (
    match_rule_extended as _match_rule_extended,
)
from guests.guest_service import (
    build_guest_360 as _build_guest_360,
)
from guests.guest_service import (
    build_guest_arrival_calendar as _build_guest_arrival_calendar,
)
from guests.guest_service import (
    build_guest_oneid_audit as _build_guest_oneid_audit,
)
from guests.guest_service import (
    build_guests_list as _build_guests_list,
)
from guests.guest_service import (
    build_oneid_board as _build_oneid_board,
)
from guests.guest_service import (
    build_segments_list as _build_segments_list,
)
from guests.guest_service import (
    compare_guest_segments as _compare_guest_segments,
)
from guests.guest_service import (
    create_crm_tasks as _create_crm_tasks,
)
from guests.guest_service import (
    create_guest_segment as _create_guest_segment,
)
from guests.guest_service import (
    export_guest_segment as _export_guest_segment,
)
from guests.guest_service import (
    merge_oneid_guests as _merge_oneid_guests,
)
from guests.guest_service import (
    post_guest_event as _post_guest_event,
)
from guests.nl_filter import (
    query_nl_guests as _query_nl_guests,
)
from guests.oneid_case import (
    get_guest_asset_summary as _get_guest_asset_summary,
)
from guests.oneid_case import (
    get_oneid_merge_case as _get_oneid_merge_case,
)
from guests.oneid_case import (
    list_duplicate_phone_groups as _list_duplicate_phone_groups,
)


def match_rule_extended(*args, **kwargs):
    """薄包装 — 调 guests.crm_defaults.match_rule_extended。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _match_rule_extended(*args, **kwargs)


def build_guest_360(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_guest_360。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_guest_360(*args, **kwargs)


def build_guest_arrival_calendar(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_guest_arrival_calendar。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_guest_arrival_calendar(*args, **kwargs)


def build_guest_oneid_audit(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_guest_oneid_audit。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_guest_oneid_audit(*args, **kwargs)


def build_guests_list(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_guests_list。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_guests_list(*args, **kwargs)


def build_oneid_board(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_oneid_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_oneid_board(*args, **kwargs)


def build_segments_list(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.build_segments_list。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_segments_list(*args, **kwargs)


def compare_guest_segments(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.compare_guest_segments。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _compare_guest_segments(*args, **kwargs)


def create_crm_tasks(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.create_crm_tasks。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _create_crm_tasks(*args, **kwargs)


def create_guest_segment(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.create_guest_segment。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _create_guest_segment(*args, **kwargs)


def export_guest_segment(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.export_guest_segment。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _export_guest_segment(*args, **kwargs)


def merge_oneid_guests(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.merge_oneid_guests。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _merge_oneid_guests(*args, **kwargs)


def post_guest_event(*args, **kwargs):
    """薄包装 — 调 guests.guest_service.post_guest_event。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _post_guest_event(*args, **kwargs)


def query_nl_guests(*args, **kwargs):
    """薄包装 — 调 guests.nl_filter.query_nl_guests。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _query_nl_guests(*args, **kwargs)


def get_guest_asset_summary(*args, **kwargs):
    """薄包装 — 调 guests.oneid_case.get_guest_asset_summary。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_guest_asset_summary(*args, **kwargs)


def get_oneid_merge_case(*args, **kwargs):
    """薄包装 — 调 guests.oneid_case.get_oneid_merge_case。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_oneid_merge_case(*args, **kwargs)


def list_duplicate_phone_groups(*args, **kwargs):
    """薄包装 — 调 guests.oneid_case.list_duplicate_phone_groups。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_duplicate_phone_groups(*args, **kwargs)


# --- orchestrated ---
from typing import Optional

from sqlalchemy.orm import Session

from guests.crm_write_service import (
    apply_tag_to_hotel_guests as _apply_tag_to_hotel_guests,
)
from guests.crm_write_service import (
    complete_crm_task as _complete_crm_task,
)
from guests.crm_write_service import (
    create_tag_definition as _create_tag_definition,
)
from guests.crm_write_service import (
    delete_guest_segment as _delete_guest_segment,
)
from guests.crm_write_service import (
    update_tag_definition as _update_tag_definition,
)


def delete_guest_segment(db: Session, hotel_id: int, segment_id: int) -> dict:
    try:
        out = _delete_guest_segment(db, hotel_id, segment_id)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def complete_crm_task(db: Session, hotel_id: int, task_id: int) -> dict:
    try:
        out = _complete_crm_task(db, hotel_id, task_id)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def create_tag_definition(
    db: Session,
    *,
    name: str,
    code: Optional[str] = None,
    category: Optional[str] = None,
    rule_expr: Optional[str] = None,
    is_active: bool = True,
) -> dict:
    try:
        out = _create_tag_definition(
            db,
            name=name,
            code=code,
            category=category,
            rule_expr=rule_expr,
            is_active=is_active,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def update_tag_definition(
    db: Session,
    tag_id: int,
    *,
    name: str,
    category: Optional[str] = None,
    rule_expr: Optional[str] = None,
    is_active: bool = True,
) -> dict:
    try:
        out = _update_tag_definition(
            db,
            tag_id,
            name=name,
            category=category,
            rule_expr=rule_expr,
            is_active=is_active,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def apply_tag_to_hotel_guests(db: Session, hotel_id: int, tag_id: int) -> dict:
    try:
        out = _apply_tag_to_hotel_guests(db, hotel_id, tag_id)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def list_reviews(db: Session, hotel_id: int):
    from guests.review_service import list_reviews as _list_reviews

    return _list_reviews(db, hotel_id)


def patch_review(
    db: Session,
    hotel_id: int,
    review_id: int,
    *,
    replied: bool = True,
    reply_content: Optional[str] = None,
) -> dict:
    from guests.review_service import patch_review as _patch_review

    try:
        out = _patch_review(
            db,
            hotel_id,
            review_id,
            replied=replied,
            reply_content=reply_content,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


# --- read queries ---


def list_oneid(db: Session):
    from guests.guest_query_service import list_oneid_identities

    return list_oneid_identities(db)


def list_tags(db: Session):
    from guests.guest_query_service import list_tags_with_coverage

    return list_tags_with_coverage(db)


def list_crm_tasks(db: Session, hotel_id: int, *, status: Optional[str] = None):
    from guests.guest_query_service import list_crm_tasks as _list_crm_tasks

    return _list_crm_tasks(db, hotel_id, status=status)
