# SPDX-License-Identifier: Apache-2.0
"""AR/AP 从订单物化同步（从 ar_ap_service 绞杀抽出）。

公开 API：normalize_agreement_orders / purge_non_real_ar_ap / sync_ar_ap_from_orders
``ar_ap_service`` 仍 re-export，调用方可不改。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from finance.doc_identity import (
    encode_commission_doc,
    encode_note_doc,
    encode_order_doc,
    encode_ota_doc,
)
from models import (
    ApInvoice,
    ArInvoice,
    Channel,
    CorpAccount,
    Order,
    OtaSettlement,
    PmsArEntry,
    PmsArLedger,
)

OTA_CODES = {
    "ctrip",
    "meituan",
    "fliggy",
    "douyin",
    "xiaohongshu",
    "meituan_voucher",
    "ota_ctrip",
    "ota_meituan",
    "ota_fliggy",
    "ota_douyin",
    "ota_tongcheng",
    "ota_elong",
    "ota_agoda",
    "jd",
}
AR_TYPE_LABEL = {
    "corp_on_account": "企业挂账",
    "ota_settlement": "OTA结算",
    "meeting": "会议",
    "longstay": "长包房",
    "member_prepaid": "会员预付",
}
AP_TYPE_LABEL = {
    "ota_commission": "OTA佣金",
    "supplier": "供应商",
    "outsource": "外包服务",
    "rent": "房租",
}
SETTLE_DAYS = {"weekly": 7, "monthly": 30, "periody": 15}


def _f(v) -> float:
    return float(v or 0)


def _money(v: float | Decimal) -> Decimal:
    return Decimal(str(round(float(v), 2)))


def _term_days(corp: Optional[CorpAccount]) -> int:
    if not corp:
        return 30
    return SETTLE_DAYS.get((corp.settle_cycle or "monthly").lower(), 30)


def _due_from_base(base: date, days: int) -> date:
    return base + timedelta(days=max(1, days))


def _ar_status(amount: Decimal, paid: Decimal, due: Optional[date], today: date) -> str:
    bal = amount - paid
    if bal <= 0:
        return "settled"
    if paid > 0:
        st = "partial"
    else:
        st = "open"
    if due and due < today and bal > 0:
        return "overdue"
    return st


def _ap_status(amount: Decimal, paid: Decimal, ap_type: str, due: Optional[date], today: date) -> str:
    bal = amount - paid
    if bal <= 0:
        return "settled"
    if ap_type == "ota_commission" and paid <= 0:
        return "pending_deduct"
    if paid > 0:
        return "partial"
    if due and due < today:
        return "open"
    return "open"


def normalize_agreement_orders(db: Session, hotel_id: int) -> dict[str, int]:
    """未退房且无挂账明细的订单不应标 on_account（与真实 AR 入账一致）。"""
    charged = {e.order_id for e in db.query(PmsArEntry).filter_by(entry_type="charge").all() if e.order_id}
    fixed = 0
    for o in db.query(Order).filter_by(hotel_id=hotel_id, payment_status="on_account"):
        if o.id in charged:
            continue
        if o.status != "checked_out":
            o.payment_status = "unpaid"
            fixed += 1
    if fixed:
        db.flush()
    return {"orders_payment_normalized": fixed}


def purge_non_real_ar_ap(db: Session, hotel_id: int) -> dict[str, int]:
    """删除无订单/挂账明细支撑的 AR/AP（含历史种子）。"""
    ap_del = (
        db.query(ApInvoice)
        .filter(
            ApInvoice.hotel_id == hotel_id,
            ApInvoice.ap_type != "ota_commission",
        )
        .delete(synchronize_session=False)
    )
    entry_ids = {
        e.id
        for e in (
            db.query(PmsArEntry)
            .join(PmsArLedger, PmsArLedger.id == PmsArEntry.ar_ledger_id)
            .filter(PmsArLedger.hotel_id == hotel_id, PmsArEntry.entry_type == "charge")
            .all()
        )
    }
    corp_types = ("corp_on_account", "longstay", "meeting", "member_prepaid")
    corp_rows = (
        db.query(ArInvoice)
        .filter(
            ArInvoice.hotel_id == hotel_id,
            ArInvoice.ar_type.in_(corp_types),
        )
        .all()
    )
    ar_corp_del = 0
    for row in corp_rows:
        if not row.pms_ar_entry_id or row.pms_ar_entry_id not in entry_ids:
            db.delete(row)
            ar_corp_del += 1
    db.flush()
    return {"ap_fake_removed": ap_del, "ar_corp_orphan_removed": ar_corp_del}


def sync_ar_ap_from_orders(db: Session, hotel_id: int) -> dict[str, int]:
    """从挂账订单、PmsArEntry、OTA 渠道订单重建/补齐 AR/AP 单据。"""
    from finance.ota_commission_service import resolve_commission_rate

    today = date.today()
    channels = {c.id: c for c in db.query(Channel).all()}
    corps = {c.id: c for c in db.query(CorpAccount).filter_by(hotel_id=hotel_id).all()}
    ar_n = ap_n = ota_n = 0
    valid_entry_ids: set[int] = set()

    # ① 协议挂账：仅以 PmsArEntry.charge 为准（须对应库内挂账明细）
    entries = (
        db.query(PmsArEntry)
        .join(PmsArLedger, PmsArLedger.id == PmsArEntry.ar_ledger_id)
        .filter(PmsArLedger.hotel_id == hotel_id, PmsArEntry.entry_type == "charge")
        .all()
    )
    for e in entries:
        valid_entry_ids.add(e.id)
        inv_no = f"AR-{e.id:04d}"
        row = db.query(ArInvoice).filter_by(hotel_id=hotel_id, invoice_no=inv_no).first()
        corp = corps.get(db.get(PmsArLedger, e.ar_ledger_id).corp_id) if e.ar_ledger_id else None
        order = db.get(Order, e.order_id) if e.order_id else None
        corp_id = corp.id if corp else (order.agreement_id if order else None)
        if corp_id and not corp:
            corp = corps.get(corp_id) or db.get(CorpAccount, corp_id)

        ar_type = "corp_on_account"
        if order:
            if order.order_type == 4:
                ar_type = "longstay"
            elif order.order_type == 5:
                ar_type = "meeting"

        cust = corp.name if corp else "协议客户"
        doc = encode_order_doc(order.order_no) if order else encode_note_doc(e.note)
        base_date = order.check_out if order and order.check_out else (e.created_at.date() if e.created_at else today)
        due = _due_from_base(base_date, _term_days(corp))
        amt = _money(e.amount or 0)
        paid = _money(row.paid_amount or 0) if row else Decimal("0")
        st = _ar_status(amt, paid, due, today)

        if not row:
            row = ArInvoice(
                hotel_id=hotel_id,
                invoice_no=inv_no,
                ar_type=ar_type,
                customer_name=cust,
                corp_id=corp_id,
                order_id=e.order_id,
                pms_ar_entry_id=e.id,
                doc_label=doc,
                amount=amt,
                paid_amount=paid,
                due_date=due,
                status=st,
                credit_limit_snapshot=corp.credit_limit if corp else None,
            )
            db.add(row)
            ar_n += 1
        else:
            row.customer_name = cust
            row.corp_id = corp_id
            row.order_id = e.order_id
            row.pms_ar_entry_id = e.id
            row.doc_label = doc
            row.amount = amt
            row.due_date = due
            row.status = st
            row.credit_limit_snapshot = corp.credit_limit if corp else row.credit_limit_snapshot

    # ② OTA 按月聚合 → OtaSettlement + AR(净额) + AP(佣金)
    ota_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.channel_id.isnot(None),
            Order.status.in_(["confirmed", "checked_in", "checked_out", "partial_extend"]),
        )
        .all()
    )
    month_buckets: dict[tuple[int, str], list[Order]] = defaultdict(list)
    for o in ota_orders:
        ch = channels.get(o.channel_id)
        if not ch or (ch.code or "").lower() not in OTA_CODES:
            continue
        period = (o.check_in or today).strftime("%Y-%m")
        month_buckets[(ch.id, period)].append(o)

    for (ch_id, period), orders in month_buckets.items():
        ch = channels[ch_id]
        gross = 0.0
        commission = 0.0
        for o in orders:
            amt = _f(o.total_amount)
            if amt <= 0:
                continue
            gross += amt
            code = (ch.code or "").strip()
            rate = (
                resolve_commission_rate(
                    db,
                    hotel_id,
                    code,
                    room_type_id=o.room_type_id,
                    on_date=o.check_in,
                )
                if code
                else 0.0
            )
            commission += round(amt * rate, 2)
        if gross <= 0:
            continue
        commission = round(commission, 2)
        net = round(gross - commission, 2)
        # 加权平均费率（展示用）
        avg_rate = (commission / gross) if gross else 0.0

        settle = db.query(OtaSettlement).filter_by(hotel_id=hotel_id, channel_id=ch_id, period=period).first()
        y, m = map(int, period.split("-"))
        due = date(y, m, 28) + timedelta(days=7)
        if not settle:
            settle = OtaSettlement(
                hotel_id=hotel_id,
                channel_id=ch_id,
                platform=(ch.code or "ota").lower(),
                period=period,
                gross_amount=_money(gross),
                commission_amount=_money(commission),
                net_amount=_money(net),
                due_date=due,
            )
            db.add(settle)
            db.flush()
            ota_n += 1
        else:
            settle.gross_amount = _money(gross)
            settle.commission_amount = _money(commission)
            settle.net_amount = _money(net)
            settle.due_date = due

        _ = avg_rate  # 加权率已体现在 commission/gross，calc_process 用结算表反推
        ar_no = f"AR-OTA-{ch.code.upper()}-{period.replace('-', '')}"
        ar_row = db.query(ArInvoice).filter_by(hotel_id=hotel_id, invoice_no=ar_no).first()
        paid_net = _money(settle.paid_net or 0)
        ar_st = _ar_status(_money(net), paid_net, due, today)
        pill = "已结算" if ar_st == "settled" else None
        ch_name = ch.name or ch.code or ""
        doc = encode_ota_doc(period, (ch.code or "ota"), len(orders))
        if not ar_row:
            ar_row = ArInvoice(
                hotel_id=hotel_id,
                invoice_no=ar_no,
                ar_type="ota_settlement",
                customer_name=ch.name or ch.code,
                channel_id=ch_id,
                ota_settlement_id=settle.id,
                doc_label=doc,
                amount=_money(net),
                paid_amount=paid_net,
                due_date=due,
                status=ar_st,
                pill_note=pill,
            )
            db.add(ar_row)
            ar_n += 1
        else:
            ar_row.amount = _money(net)
            ar_row.paid_amount = paid_net
            ar_row.status = ar_st
            ar_row.doc_label = doc
            ar_row.pill_note = pill
            ar_row.ota_settlement_id = settle.id

        ap_no = f"AP-OTA-{ch.code.upper()}-{period.replace('-', '')}"
        ap_row = db.query(ApInvoice).filter_by(hotel_id=hotel_id, invoice_no=ap_no).first()
        ap_paid = _money(commission) if ar_st == "settled" else Decimal("0")
        ap_st = "settled" if ar_st == "settled" else "pending_deduct"
        if not ap_row:
            ap_row = ApInvoice(
                hotel_id=hotel_id,
                invoice_no=ap_no,
                ap_type="ota_commission",
                vendor_name=ch.name or ch.code,
                channel_id=ch_id,
                ota_settlement_id=settle.id,
                doc_label=encode_commission_doc(period),
                amount=_money(commission),
                paid_amount=ap_paid,
                due_date=due,
                status=ap_st,
                note="结算时扣减",
            )
            db.add(ap_row)
            ap_n += 1
        else:
            ap_row.amount = _money(commission)
            ap_row.paid_amount = ap_paid
            ap_row.status = ap_st
            ap_row.ota_settlement_id = settle.id
            ap_row.doc_label = encode_commission_doc(period)
            ap_row.note = ap_row.note or "结算时扣减"

    # ③ 清除已无订单支撑的 OTA 批次与单据
    active_ota_keys = set(month_buckets.keys())
    ota_removed = 0
    for settle in db.query(OtaSettlement).filter_by(hotel_id=hotel_id).all():
        key = (settle.channel_id, settle.period)
        if key in active_ota_keys:
            continue
        db.query(ArInvoice).filter_by(hotel_id=hotel_id, ota_settlement_id=settle.id).delete(synchronize_session=False)
        db.query(ApInvoice).filter_by(hotel_id=hotel_id, ota_settlement_id=settle.id).delete(synchronize_session=False)
        db.delete(settle)
        ota_removed += 1

    # ④ 清除无挂账明细支撑的企业 AR
    for row in (
        db.query(ArInvoice)
        .filter(
            ArInvoice.hotel_id == hotel_id,
            ArInvoice.ar_type.in_(("corp_on_account", "longstay", "meeting")),
        )
        .all()
    ):
        if row.pms_ar_entry_id not in valid_entry_ids:
            db.delete(row)

    db.flush()
    return {
        "ar_synced": ar_n,
        "ap_synced": ap_n,
        "ota_settlements": ota_n,
        "ota_stale_removed": ota_removed,
    }
