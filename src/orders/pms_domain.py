# SPDX-License-Identifier: Apache-2.0
"""
PMS 核心域服务：入住登记 / Folio 账本 / 收款 / AR 挂账。
对齐设计文档：不对接支付网关，POS 小票人工录入对账。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    CorpAccount,
    Order,
    OrderItem,
    Payment,
    PmsArEntry,
    PmsArLedger,
    PmsCheckin,
    PmsFolio,
    PmsFolioEntry,
    Reservation,
    Room,
)

METHOD_ALIASES = {
    "wechat": "wechat_pos",
    "alipay": "alipay_pos",
    "wx": "wechat_pos",
    "cash": "cash",
    "card": "card",
    "bank": "card",
    "corp": "ar",
    "ar": "ar",
    "deposit": "deposit_offset",
}


def normalize_pay_method(method: str) -> str:
    m = (method or "cash").strip().lower()
    return METHOD_ALIASES.get(m, m)


def infer_order_type_from_source(source_group: str, channel_code: str | None, nights: int) -> int:
    if source_group == "group" or channel_code == "group":
        return 5
    if source_group == "agreement" or channel_code == "agreement":
        return 3
    if source_group == "longstay" or channel_code == "longstay" or nights >= 28:
        return 4
    if source_group == "ota" or (channel_code or "") in ("ota", "ctrip", "meituan", "fliggy"):
        return 2
    return 1


def apply_order_domain_defaults(o: Order, source_group: str, channel_code: str | None) -> None:
    """创建订单时写入类型 / 价策略 / OTA 预付 / 长住标记。"""
    nights = int(o.nights or 0)
    # 已显式标为团体则保留
    if int(getattr(o, "order_type", None) or 0) == 5 or getattr(o, "group_name", None):
        o.order_type = 5
        o.rate_strategy = o.rate_strategy or "daily"
        return
    ot = infer_order_type_from_source(source_group, channel_code, nights)
    o.order_type = ot
    if ot == 2:
        o.channel_prepaid = True
        o.rate_strategy = "daily"
    elif ot == 3:
        o.allow_on_account = True
        o.rate_strategy = "agreement"
    elif ot == 4:
        o.rate_strategy = "monthly"
        o.skip_daily_room_charge = True
        o.longstay_cycle = o.longstay_cycle or "monthly"
        o.monthly_rent = o.monthly_rent if o.monthly_rent is not None else o.total_amount
        o.longstay_start = o.longstay_start or o.check_in
        o.longstay_end = o.longstay_end or o.check_out
    elif ot == 5:
        o.rate_strategy = "daily"
    else:
        o.rate_strategy = o.rate_strategy or "daily"


def open_checkin_and_folio(
    db: Session,
    o: Order,
    *,
    room: Optional[Room] = None,
    reservation: Optional[Reservation] = None,
    guest_name: Optional[str] = None,
    id_doc_type: Optional[str] = None,
    id_doc_no: Optional[str] = None,
) -> tuple[PmsCheckin, PmsFolio]:
    """办理入住：写 pms_checkin + 开立 folio，并导入订单报价行。

    证件号仅写入本表（加密+脱敏），不写入 orders。
    """
    from infra.id_doc_crypto import pack_id_doc_fields
    from models import Guest

    is_group = int(getattr(o, "order_type", None) or 0) == 5 or bool(getattr(o, "group_name", None))
    existing = db.query(PmsCheckin).filter_by(order_id=o.id, status="inhouse").first()
    # 团体：允许多间同时在住，跳过「已有入住则复用」；非团体仍保持单入住
    if existing and not is_group:
        # 补登证件（散客页后填 / 续住复用前可更新）
        if id_doc_no and not existing.id_doc_cipher:
            packed = pack_id_doc_fields(id_doc_no, hotel_id=o.hotel_id)
            existing.id_doc_type = id_doc_type or existing.id_doc_type or "id_card"
            existing.id_doc_cipher = packed["id_doc_cipher"]
            existing.id_doc_mask = packed["id_doc_mask"]
            existing.id_doc_hash = packed["id_doc_hash"]
            existing.id_doc_no = None
        if guest_name and not existing.guest_name:
            existing.guest_name = guest_name
        folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
        if folio:
            return existing, folio

    g = db.get(Guest, o.guest_id) if o.guest_id else None
    name_snap = (guest_name or "").strip() or (g.name if g else None) or getattr(o, "guest_name", None)
    packed = pack_id_doc_fields(id_doc_no, hotel_id=o.hotel_id)

    ci = PmsCheckin(
        hotel_id=o.hotel_id,
        order_id=o.id,
        reservation_id=reservation.id if reservation else None,
        room_id=room.id if room else None,
        guest_id=o.guest_id,
        guest_name=name_snap,
        status="inhouse",
        actual_checkin_at=datetime.now(),
        id_doc_type=(id_doc_type or ("id_card" if packed["id_doc_cipher"] else None)),
        id_doc_cipher=packed["id_doc_cipher"],
        id_doc_mask=packed["id_doc_mask"],
        id_doc_hash=packed["id_doc_hash"],
        id_doc_no=None,
        floor=room.floor if room else None,
        room_no=room.room_no if room else None,
    )
    db.add(ci)
    db.flush()

    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    is_new_folio = folio is None
    if not folio:
        folio = PmsFolio(
            hotel_id=o.hotel_id,
            folio_no=f"F{o.id:08d}",
            order_id=o.id,
            checkin_id=ci.id,
            guest_id=o.guest_id,
            status="open",
            opened_at=datetime.now(),
        )
        db.add(folio)
        db.flush()
    else:
        folio.checkin_id = ci.id
        folio.open_folio()

    has_entries = db.query(PmsFolioEntry).filter_by(folio_id=folio.id).first() is not None
    if is_new_folio or not has_entries:
        # 导入预订行 → folio 分录（OTA 预付房费记 adjustment 冲减）
        items = db.query(OrderItem).filter_by(order_id=o.id).all()
        charge = Decimal("0")
        room_charge = Decimal("0")
        for it in items:
            et = "room_charge" if (it.item_type or "") == "room" else "misc"
            amt = Decimal(str(it.amount or 0))
            charge += amt
            if et == "room_charge":
                room_charge += amt
            db.add(
                PmsFolioEntry(
                    folio_id=folio.id,
                    entry_type=et,
                    biz_date=date.today(),
                    description=it.description or et,
                    amount=amt,
                    qty=it.qty or 1,
                    unit_price=it.unit_price,
                    source="system",
                )
            )
        if not items:
            amt = Decimal(str(o.total_amount or 0))
            charge = amt
            room_charge = amt
            db.add(
                PmsFolioEntry(
                    folio_id=folio.id,
                    entry_type="room_charge",
                    biz_date=date.today(),
                    description="房费",
                    amount=amt,
                    source="system",
                )
            )

        prepaid_offset = Decimal("0")
        if o.channel_prepaid and room_charge > 0:
            prepaid_offset = room_charge
            db.add(
                PmsFolioEntry(
                    folio_id=folio.id,
                    entry_type="adjustment",
                    biz_date=date.today(),
                    description="渠道已预付房费",
                    amount=-room_charge,
                    source="system",
                )
            )

        if o.deposit_amount and Decimal(str(o.deposit_amount)) > 0:
            dep = Decimal(str(o.deposit_amount))
            db.add(
                PmsFolioEntry(
                    folio_id=folio.id,
                    entry_type="deposit",
                    biz_date=date.today(),
                    description="入住押金",
                    amount=dep,
                    source="system",
                )
            )
            charge += dep

        folio.charge_total = charge
        folio.payment_total = Decimal("0")
        folio.balance = charge - prepaid_offset
    db.flush()
    return ci, folio


def recalc_folio(db: Session, folio: PmsFolio) -> PmsFolio:
    entries = db.query(PmsFolioEntry).filter_by(folio_id=folio.id).all()
    # deposit 计入应收；adjustment/refund 可为负；payment 不在 entries 里
    charge = sum(Decimal(str(e.amount or 0)) for e in entries)
    pays = db.query(Payment).filter_by(folio_id=folio.id).all()
    pay_total = sum(Decimal(str(p.received_amount or p.amount or 0)) for p in pays)
    folio.charge_total = charge
    folio.payment_total = pay_total
    folio.balance = charge - pay_total
    folio.sync_status_from_totals()
    return folio


def post_payment(
    db: Session,
    o: Order,
    *,
    amount: float | Decimal,
    method: str = "wechat_pos",
    pos_slip_no: Optional[str] = None,
    settle_type: str = "full",
    operator_id: Optional[int] = None,
    note: str = "",
) -> Payment:
    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    amt = Decimal(str(amount))
    p = Payment(
        hotel_id=o.hotel_id,
        order_id=o.id,
        folio_id=folio.id if folio else None,
        method=normalize_pay_method(method),
        amount=amt,
        received_amount=amt,
        pos_slip_no=pos_slip_no,
        settle_type=settle_type,
        operator_id=operator_id,
        note=note or None,
        paid_at=datetime.now(),
    )
    db.add(p)
    db.flush()
    if folio:
        recalc_folio(db, folio)
    return p


def post_ar_charge(
    db: Session,
    o: Order,
    *,
    amount: Optional[float | Decimal] = None,
    operator_id: Optional[int] = None,
) -> Optional[PmsArEntry]:
    """协议挂账：写入 AR 明细并占用授信。"""
    if not o.agreement_id:
        # 尝试绑定默认企业
        corp = db.query(CorpAccount).filter_by(hotel_id=o.hotel_id, status="active").first()
        if not corp:
            return None
        o.agreement_id = corp.id

    corp = db.get(CorpAccount, o.agreement_id)
    if not corp:
        return None

    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    amt = Decimal(str(amount if amount is not None else (folio.balance if folio else o.total_amount or 0)))
    if amt <= 0:
        amt = Decimal(str(o.total_amount or 0))

    from finance.ar_ap_service import assert_credit_for_charge, ensure_ar_invoice_from_entry

    assert_credit_for_charge(db, o.hotel_id, corp.id, float(amt))

    ledger = db.query(PmsArLedger).filter_by(hotel_id=o.hotel_id, corp_id=corp.id).first()
    if not ledger:
        ledger = PmsArLedger(
            hotel_id=o.hotel_id,
            corp_id=corp.id,
            credit_limit=corp.credit_limit or Decimal("200000"),
            settle_cycle=corp.settle_cycle or "monthly",
        )
        db.add(ledger)
        db.flush()

    entry = PmsArEntry(
        ar_ledger_id=ledger.id,
        entry_type="charge",
        order_id=o.id,
        folio_id=folio.id if folio else None,
        amount=amt,
        note="退房挂账",
        operator_id=operator_id,
    )
    db.add(entry)
    db.flush()
    ledger.charged_total = Decimal(str(ledger.charged_total or 0)) + amt
    ledger.balance = Decimal(str(ledger.balance or 0)) + amt
    ledger.credit_used = Decimal(str(ledger.credit_used or 0)) + amt
    corp.credit_used = Decimal(str(corp.credit_used or 0)) + amt
    o.credit_occupy = Decimal(str(o.credit_occupy or 0)) + amt
    o.allow_on_account = True

    if folio:
        db.add(
            PmsFolioEntry(
                folio_id=folio.id,
                entry_type="ar_charge",
                biz_date=date.today(),
                description=f"挂账 · {corp.name}",
                amount=0,  # 应收已在房费中；此处仅标记转 AR
                source="system",
                operator_id=operator_id,
            )
        )
        # 挂账视同结清客人账本余额
        db.add(
            PmsFolioEntry(
                folio_id=folio.id,
                entry_type="adjustment",
                biz_date=date.today(),
                description="转协议 AR 应收",
                amount=-amt,
                source="system",
                operator_id=operator_id,
            )
        )
        recalc_folio(db, folio)
        folio.close()

    ensure_ar_invoice_from_entry(db, o.hotel_id, entry, o)
    db.flush()
    return entry


def close_checkin(db: Session, o: Order) -> Optional[PmsCheckin]:
    rows = db.query(PmsCheckin).filter_by(order_id=o.id, status="inhouse").order_by(PmsCheckin.id.asc()).all()
    if not rows:
        # 兼容：无 inhouse 时取最近一条
        ci = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
        if not ci:
            return None
        rows = [ci]
    last = None
    for ci in rows:
        if ci.can_checkout():
            ci.checkout()
        elif str(ci.status or "") != "checked_out":
            # 兼容非 inhouse 兜底行（如 transferred）
            ci.status = "checked_out"
        ci.actual_checkout_at = datetime.now()
        last = ci
    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if folio and folio.balance <= 0:
        folio.close()
    return last


def checkin_public_dict(ci: Optional[PmsCheckin]) -> Optional[dict]:
    """对外默认视图：仅脱敏掩码，永不返回密文/明文。"""
    if not ci:
        return None
    return {
        "id": ci.id,
        "order_id": ci.order_id,
        "guest_id": ci.guest_id,
        "guest_name": ci.guest_name,
        "status": ci.status,
        "room_no": ci.room_no,
        "id_doc_type": ci.id_doc_type,
        "id_doc_mask": ci.id_doc_mask,
        "has_id_doc": bool(ci.id_doc_cipher or ci.id_doc_mask),
        "actual_checkin_at": ci.actual_checkin_at.isoformat() if ci.actual_checkin_at else None,
        "actual_checkout_at": ci.actual_checkout_at.isoformat() if ci.actual_checkout_at else None,
    }


def reveal_checkin_id_doc(
    db: Session,
    checkin_id: int,
    *,
    operator_id: Optional[int] = None,
    reason: str = "",
) -> dict:
    """高权限查看完整证件号，并写不可删审计。"""
    from infra.compliance import write_id_doc_audit
    from infra.id_doc_crypto import decrypt_id_doc

    ci = db.get(PmsCheckin, checkin_id)
    if not ci:
        raise ValueError("入住登记不存在")
    plain = decrypt_id_doc(ci.id_doc_cipher, hotel_id=ci.hotel_id)
    write_id_doc_audit(
        db,
        hotel_id=ci.hotel_id,
        checkin_id=ci.id,
        order_id=ci.order_id,
        operator_id=operator_id,
        action="reveal",
        reason=(reason or "前台核查")[:200],
    )
    return {
        "checkin_id": ci.id,
        "id_doc_type": ci.id_doc_type,
        "id_doc_no": plain,
        "id_doc_mask": ci.id_doc_mask,
    }


def folio_snapshot(db: Session, order_id: int) -> Optional[dict]:
    folio = db.query(PmsFolio).filter_by(order_id=order_id).first()
    if not folio:
        return None
    entries = db.query(PmsFolioEntry).filter_by(folio_id=folio.id).order_by(PmsFolioEntry.id.asc()).all()
    pays = db.query(Payment).filter_by(folio_id=folio.id).all()
    ci = db.get(PmsCheckin, folio.checkin_id) if folio.checkin_id else None
    return {
        "id": folio.id,
        "folio_no": folio.folio_no,
        "status": folio.status,
        "balance": float(folio.balance or 0),
        "charge_total": float(folio.charge_total or 0),
        "payment_total": float(folio.payment_total or 0),
        "checkin_id": folio.checkin_id,
        "room_no": ci.room_no if ci else None,
        "checkin": checkin_public_dict(ci) if ci else None,
        "entries": [
            {
                "id": e.id,
                "entry_type": e.entry_type,
                "biz_date": e.biz_date.isoformat() if e.biz_date else None,
                "description": e.description,
                "amount": float(e.amount or 0),
                "source": e.source,
            }
            for e in entries
        ],
        "payments": [
            {
                "id": p.id,
                "method": p.method,
                "amount": float(p.amount or 0),
                "received_amount": float(p.received_amount or p.amount or 0),
                "pos_slip_no": p.pos_slip_no,
                "settle_type": p.settle_type,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in pays
        ],
    }
