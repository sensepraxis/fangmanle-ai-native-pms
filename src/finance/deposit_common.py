# SPDX-License-Identifier: Apache-2.0
"""押金领域 · 公共工具（金额 / 序列化 / 台账 / 信用预览）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from finance.deposit_status import (
    ABNORMAL,
    FORMS,
    IN_HOLD,
    STATUS_LABEL,
    TERMINAL,
    TRANSITIONS,
    next_status,
)
from models import Deposit, DepositLedgerEntry, Guest, Order, PmsCheckin


def yuan(cents: int | None) -> float:
    return round((cents or 0) / 100.0, 2)


def deposits_for_order(db: Session, hotel_id: int, order_id: int) -> dict[str, Any]:
    """结账页用：本单押金笔数 / 在押金额 / 各单状态。"""
    rows = (
        db.query(Deposit)
        .filter(Deposit.hotel_id == hotel_id, Deposit.order_id == order_id)
        .order_by(Deposit.created_at.desc(), Deposit.deposit_id.desc())
        .all()
    )
    items = []
    held_cents = 0
    held_count = 0
    for d in rows:
        in_hold = d.status in IN_HOLD
        if in_hold:
            held_count += 1
            held_cents += int(d.remaining_refund or 0)
        items.append(
            {
                "deposit_id": d.deposit_id,
                "form": d.form,
                "form_label": FORMS.get(d.form or "", d.form),
                "status": d.status,
                "status_label": STATUS_LABEL.get(d.status or "", d.status),
                "in_hold": in_hold,
                "original_yuan": yuan(d.original_amount),
                "captured_yuan": yuan(d.captured_amount),
                "remaining_yuan": yuan(d.remaining_refund),
                "room_no": d.room_no,
                "auth_expire_at": d.auth_expire_at.isoformat() if d.auth_expire_at else None,
            }
        )
    return {
        "count": len(items),
        "held_count": held_count,
        "held_yuan": yuan(held_cents),
        "all_cleared": held_count == 0,
        "items": items,
    }


def to_cents(amount: Any) -> int:
    """入参可为「分」int，或「元」float/str。"""
    if amount is None:
        return 0
    if isinstance(amount, int):
        # 约定：>= 1000 且无小数时按分；小整数按元（友好）
        # 实际写接口用 original_amount_yuan 或明确 unit
        return amount
    try:
        return int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return 0


def _next_deposit_id(db: Session, hotel_id: int) -> str:
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"DPS-{day}-"
    last = (
        db.query(Deposit)
        .filter(Deposit.hotel_id == hotel_id, Deposit.deposit_id.like(f"{prefix}%"))
        .order_by(Deposit.deposit_id.desc())
        .first()
    )
    seq = 1
    if last and last.deposit_id:
        try:
            seq = int(last.deposit_id.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def _write_ledger(
    db: Session,
    *,
    deposit_id: str,
    event: str,
    from_status: str | None,
    to_status: str,
    amount_delta: int,
    operator_id: str,
    channel_ref: str | None = None,
    memo: str | None = None,
) -> DepositLedgerEntry:
    row = DepositLedgerEntry(
        deposit_id=deposit_id,
        event=event,
        from_status=from_status,
        to_status=to_status,
        amount_delta=amount_delta,
        operator_id=operator_id,
        channel_ref=channel_ref,
        memo=memo,
    )
    db.add(row)
    return row


def credit_preview(
    db: Session,
    *,
    hotel_id: int,
    customer_id: str | None = None,
    guest_id: int | None = None,
    nights: int = 1,
) -> dict[str, Any]:
    """§8 信用策略试算（建议金额，人工确认）。"""
    guest: Guest | None = None
    if guest_id:
        guest = db.get(Guest, guest_id)
    elif customer_id:
        guest = db.query(Guest).filter_by(one_id=customer_id).first()

    nights = max(1, int(nights or 1))
    vip = (guest.vip_level or "normal").lower() if guest else "normal"
    stay_freq = 0
    if guest:
        stay_freq = (
            db.query(Order)
            .filter(Order.hotel_id == hotel_id, Order.guest_id == guest.id, Order.status == "checked_out")
            .count()
        )
    # 信用分：VIP / 忠诚抬升
    score = 60
    if vip in ("vip3", "gold", "diamond") or "3" in vip:
        score = 88
    elif vip in ("vip2", "silver") or "2" in vip:
        score = 82
    elif vip in ("vip1", "bronze") or "1" in vip:
        score = 72
    if stay_freq >= 5:
        score = max(score, 80)
    if guest and guest.churn_risk and float(guest.churn_risk) > 0.7:
        score = min(score, 45)

    risk_tags: list[str] = []
    if guest and guest.churn_risk and float(guest.churn_risk) > 0.7:
        risk_tags.append("高流失风险")

    if score < 40:
        return {
            "suggested_amount": 100000,
            "suggested_amount_yuan": 1000.0,
            "form_hint": "CASH",
            "waived": False,
            "rule": "BLACKLIST_BLOCK",
            "credit_score": score,
            "risk_tags": risk_tags + ["需现金定金"],
            "guest_name": guest.name if guest else None,
            "vip_level": vip,
            "stay_frequency": stay_freq,
        }
    if score >= 80:
        return {
            "suggested_amount": 0,
            "suggested_amount_yuan": 0.0,
            "form_hint": "AR",
            "waived": True,
            "rule": "CREDIT_WAIVE",
            "credit_score": score,
            "risk_tags": risk_tags or ["无风险"],
            "guest_name": guest.name if guest else None,
            "vip_level": vip,
            "stay_frequency": stay_freq,
        }
    if stay_freq >= 5:
        return {
            "suggested_amount": 20000,
            "suggested_amount_yuan": 200.0,
            "form_hint": "WECHAT_DEPOSIT",
            "waived": False,
            "rule": "LOYAL_DISCOUNT",
            "credit_score": score,
            "risk_tags": risk_tags,
            "guest_name": guest.name if guest else None,
            "vip_level": vip,
            "stay_frequency": stay_freq,
        }
    amt = 50000 * nights
    return {
        "suggested_amount": amt,
        "suggested_amount_yuan": yuan(amt),
        "form_hint": "WECHAT_DEPOSIT",
        "waived": False,
        "rule": "DEFAULT_500_PER_NIGHT",
        "credit_score": score,
        "risk_tags": risk_tags,
        "guest_name": guest.name if guest else None,
        "vip_level": vip,
        "stay_frequency": stay_freq,
    }


def serialize_deposit(d: Deposit, ledger: list[DepositLedgerEntry] | None = None) -> dict[str, Any]:
    return {
        "deposit_id": d.deposit_id,
        "hotel_id": d.hotel_id,
        "order_id": d.order_id,
        "order_no": d.order_no,
        "customer_id": d.customer_id,
        "guest_id": d.guest_id,
        "guest_name": d.guest_name,
        "room_no": d.room_no,
        "form": d.form,
        "form_label": FORMS.get(d.form, d.form),
        "original_amount": d.original_amount,
        "captured_amount": d.captured_amount,
        "remaining_refund": d.remaining_refund,
        "original_yuan": yuan(d.original_amount),
        "captured_yuan": yuan(d.captured_amount),
        "remaining_yuan": yuan(d.remaining_refund),
        "status": d.status,
        "status_label": STATUS_LABEL.get(d.status, d.status),
        "auth_code": d.auth_code,
        "auth_expire_at": d.auth_expire_at.isoformat() if d.auth_expire_at else None,
        "receipt_no": d.receipt_no,
        "ar_account_id": d.ar_account_id,
        "operator_id": d.operator_id,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "released_at": d.released_at.isoformat() if d.released_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        "ledger": [
            {
                "id": e.id,
                "event": e.event,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "amount_delta": e.amount_delta,
                "amount_delta_yuan": yuan(e.amount_delta),
                "operator_id": e.operator_id,
                "channel_ref": e.channel_ref,
                "memo": e.memo,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in (ledger or [])
        ],
    }


VALID_ORDER_STATUSES = {"confirmed", "pending", "checked_in", "partial_extend"}


def _mask_guest_name(name: str | None) -> str:
    n = (name or "客人").strip()
    if len(n) <= 1:
        return n + "**"
    return n[0] + "**"


def _digits(s: str | None) -> str:
    import re

    return re.sub(r"\D+", "", str(s or ""))


def _serialize_order_for_collect(db: Session, hotel_id: int, o: Order) -> dict[str, Any]:
    from models import Channel, RoomType

    has_hold = db.query(Deposit).filter(Deposit.order_id == o.id, Deposit.status.in_(list(IN_HOLD))).first()
    g = db.get(Guest, o.guest_id) if o.guest_id else None
    ck = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
    room_no = (ck.room_no if ck else None) or "待排房"
    rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
    ch = db.get(Channel, o.channel_id) if o.channel_id else None
    preview = credit_preview(
        db,
        hotel_id=hotel_id,
        guest_id=o.guest_id,
        nights=int(o.nights or 1),
    )
    if has_hold:
        dep_st = "collected"
        dep_label = "已收押"
        if has_hold.status in ("PARTIAL_CAPTURE",) or (
            has_hold.remaining_refund < 20000 and has_hold.original_amount > 0
        ):
            dep_st = "need_topup"
            dep_label = "需追加"
    else:
        dep_st = "uncollected"
        dep_label = "未收押"

    return {
        "order_id": o.id,
        "order_no": o.order_no,
        "status": o.status,
        "status_label": {
            "pending": "待确认",
            "confirmed": "已确认/待入住",
            "checked_in": "在住",
            "partial_extend": "续住中",
        }.get(o.status or "", o.status),
        "guest_name": g.name if g else (o.guest_phone or "客人"),
        "customer_id": g.one_id if g else None,
        "guest_id": o.guest_id,
        "room_no": room_no,
        "room_type_id": o.room_type_id,
        "room_type_name": (rt.name if rt else None) or "—",
        "channel_name": (ch.name if ch else None) or "直销/其他",
        "check_in": o.check_in.isoformat() if o.check_in else None,
        "check_out": o.check_out.isoformat() if o.check_out else None,
        "nights": o.nights,
        "has_active_deposit": bool(has_hold),
        "deposit_status": dep_st,
        "deposit_status_label": dep_label,
        "preview": preview,
    }
