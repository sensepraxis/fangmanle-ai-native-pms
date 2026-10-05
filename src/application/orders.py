# SPDX-License-Identifier: Apache-2.0
"""Facade module for orders domain.

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
from orders.order_insight_service import (
    build_orders_board as _build_orders_board,
)
from orders.order_insight_service import (
    build_orders_monitor as _build_orders_monitor,
)
from orders.order_insight_service import (
    compose_orders_attribution as _compose_orders_attribution,
)
from orders.order_insight_service import (
    compose_orders_channel_insight as _compose_orders_channel_insight,
)
from orders.order_service import (
    assign_group_line as _assign_group_line,
)
from orders.order_service import (
    checkin_group_line as _checkin_group_line,
)
from orders.order_service import (
    create_group_order as _create_group_order,
)
from orders.order_service import (
    list_orders_compat as _list_orders_compat,
)
from orders.order_service import (
    lookup_voucher as _lookup_voucher,
)
from orders.order_service import (
    order_detail_dict as _order_detail_dict,
)
from orders.order_service import (
    orders_work_summary as _orders_work_summary,
)
from orders.order_service import (
    sync_ota_order as _sync_ota_order,
)
from orders.order_service import (
    verify_voucher_and_order as _verify_voucher_and_order,
)
from orders.order_service import (
    walk_in_checkin as _walk_in_checkin,
)
from orders.pms_domain import (
    reveal_checkin_id_doc as _reveal_checkin_id_doc,
)
from orders.pms_ops import (
    add_folio_charge as _add_folio_charge,
)
from orders.pms_ops import (
    add_roommate as _add_roommate,
)
from orders.pms_ops import (
    assign_room_only as _assign_room_only,
)
from orders.pms_ops import (
    change_room as _change_room,
)
from orders.pms_ops import (
    collect_payment as _collect_payment,
)
from orders.pms_ops import (
    extend_stay as _extend_stay,
)
from orders.pms_ops import (
    list_order_checkins as _list_order_checkins,
)
from orders.pms_ops import (
    mark_no_show as _mark_no_show,
)
from orders.pms_ops import (
    post_longstay_monthly_rent as _post_longstay_monthly_rent,
)
from orders.pms_ops import (
    post_night_audit_room_charges as _post_night_audit_room_charges,
)
from orders.pms_ops import (
    rc_registration_card as _rc_registration_card,
)

_recommend_rooms = _cbind("commercial.orders.walkin_ai", "recommend_rooms")


def build_orders_board(*args, **kwargs):
    """薄包装 — 调 orders.order_insight_service.build_orders_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_orders_board(*args, **kwargs)


def build_orders_monitor(*args, **kwargs):
    """薄包装 — 调 orders.order_insight_service.build_orders_monitor。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_orders_monitor(*args, **kwargs)


def compose_orders_attribution(*args, **kwargs):
    """薄包装 — 调 orders.order_insight_service.compose_orders_attribution。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _compose_orders_attribution(*args, **kwargs)


def assign_group_line(*args, **kwargs):
    """编排：团体行预分房 → commit。"""
    db = args[0]
    try:
        data = _assign_group_line(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def checkin_group_line(*args, **kwargs):
    """编排：团体行入住 → commit。"""
    db = args[0]
    try:
        data = _checkin_group_line(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def create_group_order(*args, **kwargs):
    """编排：创建团体单 → commit。"""
    db = args[0]
    try:
        data = _create_group_order(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def list_orders_compat(*args, **kwargs):
    """薄包装 — 调 orders.order_service.list_orders_compat。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_orders_compat(*args, **kwargs)


def lookup_voucher(*args, **kwargs):
    """薄包装 — 调 orders.order_service.lookup_voucher。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_voucher(*args, **kwargs)


def order_detail_dict(*args, **kwargs):
    """薄包装 — 调 orders.order_service.order_detail_dict。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _order_detail_dict(*args, **kwargs)


def orders_work_summary(*args, **kwargs):
    """薄包装 — 调 orders.order_service.orders_work_summary。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _orders_work_summary(*args, **kwargs)


def sync_ota_order(*args, **kwargs):
    """编排：OTA 同步建单 → commit。"""
    db = args[0]
    try:
        data = _sync_ota_order(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def verify_voucher_and_order(*args, **kwargs):
    """编排：券核销建单 → commit。"""
    db = args[0]
    try:
        data = _verify_voucher_and_order(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def walk_in_checkin(*args, **kwargs):
    """编排：散客即时入住 → commit。"""
    db = args[0]
    try:
        data = _walk_in_checkin(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def reveal_checkin_id_doc(*args, **kwargs):
    """编排：揭密证件（审计由调用方/领域完成）→ commit。"""
    db = args[0]
    try:
        data = _reveal_checkin_id_doc(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def add_folio_charge(*args, **kwargs):
    """编排：住中加收 → commit。"""
    db = args[0]
    try:
        data = _add_folio_charge(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def add_roommate(*args, **kwargs):
    """编排：添加同住人 → commit。"""
    db = args[0]
    try:
        data = _add_roommate(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def assign_room_only(*args, **kwargs):
    """编排：预分房 → commit。"""
    db = args[0]
    try:
        data = _assign_room_only(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def change_room(*args, **kwargs):
    """编排：换房 → commit。"""
    db = args[0]
    try:
        data = _change_room(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def collect_payment(*args, **kwargs):
    """编排：住中收款 → commit。"""
    db = args[0]
    try:
        data = _collect_payment(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def extend_stay(*args, **kwargs):
    """编排：续住 → commit。"""
    db = args[0]
    try:
        data = _extend_stay(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def list_order_checkins(*args, **kwargs):
    """薄包装 — 调 orders.pms_ops.list_order_checkins。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_order_checkins(*args, **kwargs)


def mark_no_show(*args, **kwargs):
    """编排：标记 No-show → commit。"""
    db = args[0]
    try:
        data = _mark_no_show(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def post_longstay_monthly_rent(*args, **kwargs):
    """编排：长住月租入账 → commit。"""
    db = args[0]
    try:
        data = _post_longstay_monthly_rent(*args, **kwargs)
        db.commit()
        return data
    except Exception:
        db.rollback()
        raise


def post_night_audit_room_charges(*args, **kwargs):
    """薄包装 — 调 orders.pms_ops.post_night_audit_room_charges。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _post_night_audit_room_charges(*args, **kwargs)


def rc_registration_card(*args, **kwargs):
    """薄包装 — 调 orders.pms_ops.rc_registration_card。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _rc_registration_card(*args, **kwargs)


def recommend_rooms(*args, **kwargs):
    """薄包装 — 调 orders.walkin_ai.recommend_rooms。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _recommend_rooms(*args, **kwargs)


def compose_orders_channel_insight(*args, **kwargs):
    """薄包装 — 调 orders.order_insight_service.compose_orders_channel_insight。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _compose_orders_channel_insight(*args, **kwargs)


# --- orchestrated ---
# Hand-maintained write paths: domain service → commit → response dict.
# Lifecycle emit stays in domain services (order.created / guest.checked_*).

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from orders.order_service import (
    cancel_order as _cancel_order_record,
)
from orders.order_service import (
    checkin_order as _checkin_order_record,
)
from orders.order_service import (
    checkout_order as _checkout_order_record,
)
from orders.order_service import (
    create_order_record as _create_order_record,
)
from orders.order_service import (
    row_to_dict as _order_row_dict,
)


def create_order(
    db: Session,
    *,
    hotel_id: int,
    guest_name: str,
    phone: Optional[str],
    room_type_id: int,
    channel_id: Optional[int],
    check_in: date,
    check_out: date,
    rooms: int = 1,
    adults: int = 1,
    children: int = 0,
    note: str = "",
    external_order_no: Optional[str] = None,
    voucher_code: Optional[str] = None,
    payment_status: Optional[str] = None,
    status: str = "confirmed",
    created_by: Optional[int] = None,
) -> dict:
    """开单编排：建单 → commit → 返回序列化订单。"""
    try:
        o = _create_order_record(
            db,
            hotel_id=hotel_id,
            guest_name=guest_name,
            phone=phone,
            room_type_id=room_type_id,
            channel_id=channel_id,
            check_in=check_in,
            check_out=check_out,
            rooms=rooms,
            adults=adults,
            children=children,
            note=note,
            external_order_no=external_order_no,
            voucher_code=voucher_code,
            payment_status=payment_status,
            status=status,
            created_by=created_by,
        )
        db.commit()
        return _order_row_dict(db, o)
    except Exception:
        db.rollback()
        raise


def checkin(
    db: Session,
    order_id: int,
    room_id: Optional[int] = None,
    *,
    guest_name: Optional[str] = None,
    id_doc_type: Optional[str] = None,
    id_doc_no: Optional[str] = None,
) -> dict:
    """入住编排：checkin_order → commit → 订单详情。"""
    try:
        o = _checkin_order_record(
            db,
            order_id,
            room_id,
            guest_name=guest_name,
            id_doc_type=id_doc_type,
            id_doc_no=id_doc_no,
        )
        db.commit()
        return _order_detail_dict(db, o)
    except Exception:
        db.rollback()
        raise


def checkout(
    db: Session,
    order_id: int,
    *,
    payment_mode: str = "auto",
    method: str = "wechat",
    pos_slip_no: Optional[str] = None,
) -> dict:
    """离店编排：checkout_order → commit → 订单详情。"""
    try:
        o = _checkout_order_record(
            db,
            order_id,
            payment_mode=payment_mode,
            method=method,
            pos_slip_no=pos_slip_no,
        )
        db.commit()
        return _order_detail_dict(db, o)
    except Exception:
        db.rollback()
        raise


def cancel_order(db: Session, order_id: int, reason: str = "") -> dict:
    """取消编排：cancel_order → commit → 序列化订单。"""
    try:
        o = _cancel_order_record(db, order_id, reason)
        db.commit()
        return _order_row_dict(db, o)
    except Exception:
        db.rollback()
        raise


def purge_expired_id_docs(
    db: Session,
    *,
    hotel_id: int,
    operator_id: Optional[int],
    retain_years: int,
) -> dict:
    """合规：匿名化过期证件密文 + 审计 → commit。"""
    from infra.compliance import purge_expired_id_docs as _purge
    from infra.compliance import write_id_doc_audit

    try:
        n = _purge(db, retain_years=retain_years)
        write_id_doc_audit(
            db,
            hotel_id=hotel_id,
            checkin_id=None,
            order_id=None,
            operator_id=operator_id,
            action="purge",
            reason=f"匿名化离店超 {retain_years} 年证件密文，共 {n} 条",
        )
        db.commit()
        return {"purged": n, "retain_years": retain_years}
    except Exception:
        db.rollback()
        raise


def rc_registration_card_revealed(
    db: Session,
    order_id: int,
    *,
    hotel_id: int,
    operator_id: Optional[int],
    reason: str,
) -> dict:
    """RC 揭密：写审计 → commit → 返回含明文证件的登记单。"""
    from infra.compliance import write_id_doc_audit

    try:
        write_id_doc_audit(
            db,
            hotel_id=hotel_id,
            checkin_id=None,
            order_id=order_id,
            operator_id=operator_id,
            action="reveal",
            reason=reason or "打印登记单核验",
        )
        db.commit()
        return _rc_registration_card(db, order_id, reveal=True)
    except Exception:
        db.rollback()
        raise
