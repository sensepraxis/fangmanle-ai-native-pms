# SPDX-License-Identifier: Apache-2.0
"""押金收 / 扣 / 释 / 再授权 / 争议（从 deposit_service 绞杀抽出）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from finance.deposit_common import (
    _next_deposit_id,
    _serialize_order_for_collect,
    _write_ledger,
    credit_preview,
    serialize_deposit,
    to_cents,
    yuan,
)
from finance.deposit_status import FORMS, next_status
from models import Deposit, DepositLedgerEntry, Guest, Order, PmsCheckin


def get_detail(db: Session, hotel_id: int, deposit_id: str) -> dict[str, Any]:
    d = db.get(Deposit, deposit_id)
    if not d or d.hotel_id != hotel_id:
        raise NotFoundError("押金单不存在")
    ledger = db.query(DepositLedgerEntry).filter_by(deposit_id=deposit_id).order_by(DepositLedgerEntry.id.asc()).all()
    data = serialize_deposit(d, ledger)
    preview = credit_preview(db, hotel_id=hotel_id, customer_id=d.customer_id, guest_id=d.guest_id)
    data["guest_profile"] = preview
    return data


def collect(db: Session, hotel_id: int, payload: dict, operator_id: str) -> dict[str, Any]:
    idem = (payload.get("idempotency_key") or "").strip()
    if not idem:
        raise InvalidStateError("缺少 idempotency_key")
    existed = db.query(Deposit).filter_by(idempotency_key=idem).first()
    if existed:
        return serialize_deposit(existed)

    order_id = payload.get("order_id")
    if not order_id:
        raise InvalidStateError("押金必须关联订单 order_id")
    order: Order | None = db.get(Order, int(order_id))
    if not order or order.hotel_id != hotel_id:
        raise NotFoundError("关联订单不存在")

    form = (payload.get("form") or "WECHAT_DEPOSIT").upper()
    if form not in FORMS:
        raise InvalidStateError(f"不支持的押金形态: {form}")

    # 金额：优先 original_amount_yuan，其次 original_amount（分）
    if payload.get("original_amount_yuan") is not None:
        original = to_cents(payload.get("original_amount_yuan"))
    else:
        raw = payload.get("original_amount")
        if isinstance(raw, (int, float)) and float(raw) < 10000 and "." in str(raw):
            original = to_cents(raw)
        elif isinstance(raw, (int, float)) and float(raw) > 0 and float(raw) < 500 and float(raw) == int(float(raw)):
            # 小整数按「元」理解
            original = int(float(raw) * 100)
        else:
            original = int(raw or 0)

    waived = bool(payload.get("waived")) or original == 0
    if not waived and original <= 0:
        raise InvalidStateError("收押金额须大于 0（免押请传 waived=true）")

    auth_code = payload.get("auth_code")
    receipt_no = payload.get("receipt_no")
    if form in ("PREAUTH_CARD", "WECHAT_DEPOSIT", "ALIPAY_DEPOSIT") and not waived and not auth_code:
        auth_code = f"{form[:2]}AUTH-{datetime.now().strftime('%H%M%S')}"
    if form == "CASH" and not receipt_no and not waived:
        raise InvalidStateError("现金押金必须填写收据号 receipt_no")

    room_no = payload.get("room_no") or ""
    guest_name = payload.get("guest_name")
    customer_id = payload.get("customer_id")
    guest_id = payload.get("guest_id")
    order_no = payload.get("order_no")
    nights = int(payload.get("nights") or (order.nights if order else 1) or 1)

    if order:
        order_no = order.order_no
        guest_id = guest_id or order.guest_id
        if order.guest_id:
            g = db.get(Guest, order.guest_id)
            if g:
                customer_id = customer_id or g.one_id
                guest_name = guest_name or g.name
        if not room_no:
            ck = db.query(PmsCheckin).filter_by(order_id=order.id).order_by(PmsCheckin.id.desc()).first()
            if ck and ck.room_no:
                room_no = ck.room_no
        if not room_no:
            room_no = "——"

    if not customer_id:
        customer_id = f"C-DEMO-{hotel_id}"
    if not room_no:
        raise InvalidStateError("缺少房号 room_no")

    auth_expire_at = None
    if payload.get("auth_expire_at"):
        try:
            auth_expire_at = datetime.fromisoformat(str(payload["auth_expire_at"]).replace("Z", ""))
        except ValueError:
            auth_expire_at = datetime.now() + timedelta(days=30)
    elif form in ("PREAUTH_CARD", "WECHAT_DEPOSIT", "ALIPAY_DEPOSIT"):
        auth_expire_at = datetime.now() + timedelta(days=30)

    deposit_id = _next_deposit_id(db, hotel_id)
    status = "FROZEN"
    d = Deposit(
        deposit_id=deposit_id,
        hotel_id=hotel_id,
        order_id=int(order_id),
        customer_id=customer_id,
        guest_id=int(guest_id) if guest_id else None,
        room_no=str(room_no)[:8],
        form=form,
        original_amount=original,
        captured_amount=0,
        remaining_refund=original,
        status=status,
        auth_code=None if waived else auth_code,
        auth_expire_at=None if waived else auth_expire_at,
        ar_account_id=payload.get("ar_account_id"),
        receipt_no=receipt_no,
        operator_id=str(operator_id),
        idempotency_key=idem,
        guest_name=guest_name,
        order_no=order_no,
    )
    if waived:
        d.status = "RELEASED"
        d.released_at = datetime.now()
        d.remaining_refund = 0
        d.form = form if form == "AR" else "AR"

    db.add(d)
    _write_ledger(
        db,
        deposit_id=deposit_id,
        event="COLLECT",
        from_status="CREATED",
        to_status=d.status,
        amount_delta=original,
        operator_id=str(operator_id),
        channel_ref=auth_code,
        memo="免押确认" if waived else "收押成功",
    )
    if order and original > 0:
        from decimal import Decimal

        order.deposit_amount = Decimal(str(order.deposit_amount or 0)) + Decimal(str(original / 100.0))
    db.flush()
    db.refresh(d)
    from events import emit

    emit(
        "deposit.created",
        {
            "hotel_id": hotel_id,
            "deposit_id": d.deposit_id,
            "order_id": d.order_id,
            "guest_id": d.guest_id,
            "status": d.status,
            "original_amount": d.original_amount,
            "form": d.form,
        },
    )
    return serialize_deposit(d)


def _require_transition(d: Deposit, event: str) -> str:
    return next_status(d.status, event)


def capture(db: Session, hotel_id: int, deposit_id: str, payload: dict, operator_id: str) -> dict[str, Any]:
    d = db.get(Deposit, deposit_id)
    if not d or d.hotel_id != hotel_id:
        raise NotFoundError("押金单不存在")
    if payload.get("original_amount_yuan") is not None or "capture_amount_yuan" in payload:
        amt = to_cents(payload.get("capture_amount_yuan") or payload.get("capture_amount"))
    else:
        raw = payload.get("capture_amount")
        amt = int(raw) if isinstance(raw, int) and raw >= 100 else to_cents(raw)
    if amt <= 0:
        raise InvalidStateError("扣减金额须大于 0")
    if amt > d.remaining_refund:
        raise InvalidStateError("扣减金额超过剩余可退")
    from_st = d.status
    d.captured_amount += amt
    d.remaining_refund = d.original_amount - d.captured_amount
    full = d.captured_amount >= d.original_amount
    if full:
        d.remaining_refund = 0
    d.apply_event("CAPTURE", full_capture=full)
    _write_ledger(
        db,
        deposit_id=d.deposit_id,
        event="CAPTURE",
        from_status=from_st,
        to_status=d.status,
        amount_delta=-amt,
        operator_id=str(operator_id),
        memo=payload.get("memo") or "部分扣减",
    )
    db.flush()
    from events import emit

    emit(
        "deposit.captured",
        {
            "hotel_id": hotel_id,
            "deposit_id": d.deposit_id,
            "order_id": d.order_id,
            "amount_cents": amt,
            "status": d.status,
            "operator_id": operator_id,
        },
    )
    return get_detail(db, hotel_id, deposit_id)


def release(db: Session, hotel_id: int, deposit_id: str, payload: dict, operator_id: str) -> dict[str, Any]:
    d = db.get(Deposit, deposit_id)
    if not d or d.hotel_id != hotel_id:
        raise NotFoundError("押金单不存在")
    if d.form == "CASH" and not d.receipt_no:
        raise InvalidStateError("现金押金无收据号，禁止释放")
    from_st = d.status
    refund = d.remaining_refund
    if from_st == "DISPUTED":
        # SETTLE / RELEASE 均收口到 RELEASED
        try:
            d.apply_event("RELEASE")
        except InvalidStateError:
            d.apply_event("SETTLE")
    else:
        d.apply_event("RELEASE")
    d.remaining_refund = 0
    d.released_at = datetime.now()
    method = payload.get("refund_method") or "ORIGINAL"
    _write_ledger(
        db,
        deposit_id=d.deposit_id,
        event="RELEASE",
        from_status=from_st,
        to_status=d.status,
        amount_delta=-refund,
        operator_id=str(operator_id),
        channel_ref=f"REFUND-{method}",
        memo=payload.get("memo") or f"退押({method})",
    )
    db.flush()
    from events import emit

    emit(
        "deposit.released",
        {
            "hotel_id": hotel_id,
            "deposit_id": d.deposit_id,
            "order_id": d.order_id,
            "status": d.status,
            "refund_cents": refund,
            "operator_id": operator_id,
        },
    )
    return {
        **get_detail(db, hotel_id, deposit_id),
        "refund_amount": refund,
        "refund_amount_yuan": yuan(refund),
    }


def reauthorize(db: Session, hotel_id: int, deposit_id: str, payload: dict, operator_id: str) -> dict[str, Any]:
    d = db.get(Deposit, deposit_id)
    if not d or d.hotel_id != hotel_id:
        raise NotFoundError("押金单不存在")
    from_st = d.status
    if from_st not in ("EXPIRED", "DISPUTED"):
        raise InvalidStateError("仅失效/争议单可重授权")
    d.auth_code = payload.get("auth_code") or f"REAUTH-{datetime.now().strftime('%H%M%S')}"
    d.auth_expire_at = datetime.now() + timedelta(days=30)
    if payload.get("auth_expire_at"):
        try:
            d.auth_expire_at = datetime.fromisoformat(str(payload["auth_expire_at"]).replace("Z", ""))
        except ValueError:
            pass
    d.apply_event("REAUTHORIZE")
    _write_ledger(
        db,
        deposit_id=d.deposit_id,
        event="REAUTHORIZE",
        from_status=from_st,
        to_status=d.status,
        amount_delta=0,
        operator_id=str(operator_id),
        channel_ref=d.auth_code,
        memo="重授权",
    )
    db.flush()
    return get_detail(db, hotel_id, deposit_id)


def dispute(db: Session, hotel_id: int, deposit_id: str, payload: dict, operator_id: str) -> dict[str, Any]:
    d = db.get(Deposit, deposit_id)
    if not d or d.hotel_id != hotel_id:
        raise NotFoundError("押金单不存在")
    from_st = d.status
    if from_st not in ("FROZEN", "PARTIAL_CAPTURE"):
        raise InvalidStateError("当前状态不可登记争议")
    if from_st == "PARTIAL_CAPTURE":
        # 状态机仅定义 FROZEN→DISPUTE；部分扣减争议直接落 DISPUTED
        d.status = "DISPUTED"
    else:
        d.apply_event("DISPUTE")
    _write_ledger(
        db,
        deposit_id=d.deposit_id,
        event="DISPUTE",
        from_status=from_st,
        to_status=d.status,
        amount_delta=0,
        operator_id=str(operator_id),
        memo=payload.get("memo") or "争议登记",
    )
    db.flush()
    return get_detail(db, hotel_id, deposit_id)


def list_collectable_orders(db: Session, hotel_id: int, limit: int = 30) -> list[dict[str, Any]]:
    """收押向导：可选订单（已确认/在住，优先无在押单）。"""
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["confirmed", "checked_in", "pending"]),
        )
        .order_by(Order.id.desc())
        .limit(80)
        .all()
    )
    out = []
    for o in orders:
        row = _serialize_order_for_collect(db, hotel_id, o)
        out.append(row)
        if len(out) >= limit:
            break
    return out
