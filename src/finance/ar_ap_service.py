# SPDX-License-Identifier: Apache-2.0
"""应收应付中心：从订单/协议 AR/OTA 对账同步单据，并提供核销与授信校验。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
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
from finance.doc_identity import (
    encode_note_doc,
    encode_order_doc,
    present_doc_label,
    present_party_name,
    present_sys_note,
)
from infra.i18n import TranslatingMap, t
from models import (
    ApInvoice,
    ArApLog,
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
AR_TYPE_LABEL = TranslatingMap(
    {
        "corp_on_account": "企业挂账",
        "ota_settlement": "OTA结算",
        "meeting": "会议",
        "longstay": "长包房",
        "member_prepaid": "会员预付",
    }
)
AP_TYPE_LABEL = TranslatingMap(
    {
        "ota_commission": "OTA佣金",
        "supplier": "供应商",
        "outsource": "外包服务",
        "rent": "房租",
    }
)
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


def _log(
    db: Session,
    hotel_id: int,
    action: str,
    ref_type: str,
    ref_id: int,
    amount: float,
    operator: str,
    reason: str = "",
    meta: str = "",
):
    db.add(
        ArApLog(
            hotel_id=hotel_id,
            action=action,
            ref_type=ref_type,
            ref_id=ref_id,
            operator_name=operator,
            amount=_money(amount),
            reason=reason,
            meta=meta,
        )
    )


def _ensure_ledger(db: Session, hotel_id: int, corp_id: int) -> PmsArLedger:
    led = db.query(PmsArLedger).filter_by(hotel_id=hotel_id, corp_id=corp_id).first()
    if led:
        return led
    corp = db.get(CorpAccount, corp_id)
    led = PmsArLedger(
        hotel_id=hotel_id,
        corp_id=corp_id,
        credit_limit=corp.credit_limit if corp else Decimal("200000"),
        settle_cycle=corp.settle_cycle if corp else "monthly",
    )
    db.add(led)
    db.flush()
    return led


# --- sync 已绞杀至 finance.ar_ap_sync；保持兼容 re-export ---
from finance.ar_ap_sync import (  # noqa: E402
    normalize_agreement_orders,
    purge_non_real_ar_ap,
    sync_ar_ap_from_orders,
)


def check_credit(db: Session, hotel_id: int, corp_id: int, amount: float) -> dict[str, Any]:
    corp = db.get(CorpAccount, corp_id)
    if not corp or corp.hotel_id != hotel_id:
        raise NotFoundError("协议单位不存在")
    limit = _f(corp.credit_limit)
    used = _f(corp.credit_used)
    available = max(0.0, limit - used)
    blocked = amount > available + 0.001
    return {
        "corp_id": corp_id,
        "corp_name": corp.name,
        "credit_limit": limit,
        "credit_used": used,
        "credit_available": round(available, 2),
        "term_days": _term_days(corp),
        "blocked": blocked,
        "message": ("可用额度不足，请担保/现付/补缴保证金" if blocked else "额度充足，可挂账"),
    }


def assert_credit_for_charge(db: Session, hotel_id: int, corp_id: int, amount: float) -> None:
    """挂账前授信校验，超额则阻断。"""
    chk = check_credit(db, hotel_id, corp_id, amount)
    if chk["blocked"]:
        raise InvalidStateError(chk["message"])


def ensure_ar_invoice_from_entry(
    db: Session,
    hotel_id: int,
    entry: PmsArEntry,
    order: Optional[Order] = None,
) -> ArInvoice:
    """单笔挂账明细 → 应收单据（与收银台/退房挂账同源）。"""
    today = date.today()
    inv_no = f"AR-{entry.id:04d}"
    row = db.query(ArInvoice).filter_by(hotel_id=hotel_id, invoice_no=inv_no).first()
    corp = None
    if entry.ar_ledger_id:
        led = db.get(PmsArLedger, entry.ar_ledger_id)
        if led:
            corp = db.get(CorpAccount, led.corp_id)
    if order and order.agreement_id and not corp:
        corp = db.get(CorpAccount, order.agreement_id)
    corp_id = corp.id if corp else (order.agreement_id if order else None)

    ar_type = "corp_on_account"
    if order:
        if order.order_type == 4:
            ar_type = "longstay"
        elif order.order_type == 5:
            ar_type = "meeting"

    cust = corp.name if corp else "协议客户"
    doc = encode_order_doc(order.order_no) if order else encode_note_doc(entry.note)
    base_date = (
        order.check_out if order and order.check_out else (entry.created_at.date() if entry.created_at else today)
    )
    due = _due_from_base(base_date, _term_days(corp))
    amt = _money(entry.amount or 0)
    paid = _money(row.paid_amount or 0) if row else Decimal("0")
    st = _ar_status(amt, paid, due, today)

    if not row:
        row = ArInvoice(
            hotel_id=hotel_id,
            invoice_no=inv_no,
            ar_type=ar_type,
            customer_name=cust,
            corp_id=corp_id,
            order_id=entry.order_id or (order.id if order else None),
            pms_ar_entry_id=entry.id,
            doc_label=doc,
            amount=amt,
            paid_amount=paid,
            due_date=due,
            status=st,
            credit_limit_snapshot=corp.credit_limit if corp else None,
        )
        db.add(row)
    else:
        row.customer_name = cust
        row.corp_id = corp_id
        row.order_id = entry.order_id or (order.id if order else None)
        row.doc_label = doc
        row.amount = amt
        row.due_date = due
        row.status = st
        row.pms_ar_entry_id = entry.id
        row.credit_limit_snapshot = corp.credit_limit if corp else row.credit_limit_snapshot
    db.flush()
    return row


def _parse_meta(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _todo_dismissed_keys(db: Session, hotel_id: int) -> set[str]:
    keys: set[str] = set()
    rows = (
        db.query(ArApLog)
        .filter_by(hotel_id=hotel_id, action="todo_dismiss")
        .order_by(ArApLog.id.desc())
        .limit(200)
        .all()
    )
    for r in rows:
        meta = _parse_meta(r.meta)
        tid = meta.get("todo_id") or r.reason or ""
        if tid:
            keys.add(str(tid))
        if r.ref_id:
            keys.add(f"ar_{r.ref_id}")
            keys.add(f"log_{r.ref_id}")
            keys.add(f"corp_{r.ref_id}_credit")
    return keys


def list_ar_ap_todos(db: Session, hotel_id: int, *, ar_rows: Optional[list] = None) -> list[dict]:
    """催收/授信待办：AI 备忘 + 系统自动项（逾期/90+天/超额授信）。"""
    today = date.today()
    dismissed = _todo_dismissed_keys(db, hotel_id)
    todos: list[dict] = []
    seen_ar: set[int] = set()
    seen_corp: set[int] = set()

    if ar_rows is None:
        ar_rows = db.query(ArInvoice).filter_by(hotel_id=hotel_id).filter(ArInvoice.status != "bad_debt").all()

    ar_by_id = {r.id: r for r in ar_rows}

    ai_logs = (
        db.query(ArApLog)
        .filter(
            ArApLog.hotel_id == hotel_id,
            ArApLog.action.in_(["reminder", "credit_warn"]),
        )
        .order_by(ArApLog.created_at.desc())
        .limit(40)
        .all()
    )
    for log in ai_logs:
        meta = _parse_meta(log.meta)
        if meta.get("status") == "done":
            continue
        tid = f"log_{log.id}"
        if tid in dismissed:
            continue
        ar_id = log.ref_id if log.ref_type == "ar" and log.action == "reminder" else None
        corp_id = log.ref_id if log.action == "credit_warn" else None
        still_relevant = True
        title = log.reason or "待跟进"
        amount = _f(log.amount)
        todo_type = "overdue_collect" if log.action == "reminder" else "credit_warn"
        if ar_id and ar_id in ar_by_id:
            inv = ar_by_id[ar_id]
            if inv.status in ("settled", "bad_debt"):
                still_relevant = False
            else:
                amount = max(0, _f(inv.amount) - _f(inv.paid_amount))
                title = f"催收 · {inv.customer_name} · ¥{amount:.0f}"
                seen_ar.add(ar_id)
        elif corp_id:
            corp = db.get(CorpAccount, corp_id)
            if corp:
                limit = _f(corp.credit_limit)
                used = _f(corp.credit_used)
                rate = round(used / limit * 100, 1) if limit > 0 else 0
                if rate < 80:
                    still_relevant = False
                title = f"授信预警 · {corp.name} · 使用率 {rate}%"
                seen_corp.add(corp_id)
        if not still_relevant:
            continue
        todos.append(
            {
                "id": tid,
                "source": "ai",
                "type": todo_type,
                "title": title,
                "detail": log.reason or "",
                "amount": amount,
                "ar_id": ar_id,
                "corp_id": corp_id,
                "log_id": log.id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "priority": "high" if todo_type == "overdue_collect" else "medium",
            }
        )

    for inv in ar_rows:
        if inv.status != "overdue" or inv.id in seen_ar:
            continue
        tid = f"ar_{inv.id}"
        if tid in dismissed:
            continue
        bal = max(0, _f(inv.amount) - _f(inv.paid_amount))
        due = inv.due_date.isoformat() if inv.due_date else "—"
        overdue_days = (today - inv.due_date).days if inv.due_date else 0
        todos.append(
            {
                "id": tid,
                "source": "system",
                "type": "overdue_collect",
                "title": t("逾期应收 · {name} · ¥{amt}", name=inv.customer_name, amt=f"{bal:.0f}"),
                "detail": t(
                    "{doc} · 账期 {due} · 逾期 {n} 天",
                    doc=present_doc_label(inv.doc_label) or "—",
                    due=due,
                    n=overdue_days,
                ),
                "amount": bal,
                "ar_id": inv.id,
                "corp_id": inv.corp_id,
                "log_id": None,
                "created_at": None,
                "priority": "high" if overdue_days >= 30 else "medium",
            }
        )
        seen_ar.add(inv.id)

    for inv in ar_rows:
        if inv.status in ("settled", "bad_debt") or not inv.due_date:
            continue
        if (today - inv.due_date).days < 90:
            continue
        if inv.id in seen_ar:
            continue
        tid = f"aging_{inv.id}"
        if tid in dismissed:
            continue
        bal = max(0, _f(inv.amount) - _f(inv.paid_amount))
        if bal <= 0:
            continue
        todos.append(
            {
                "id": tid,
                "source": "system",
                "type": "aging_90",
                "title": t("90+ 天预警 · {name} · ¥{amt}", name=inv.customer_name, amt=f"{bal:.0f}"),
                "detail": t(
                    "{doc} · 建议人工评估是否坏账（AI 不自动核销）",
                    doc=present_doc_label(inv.doc_label) or "—",
                ),
                "amount": bal,
                "ar_id": inv.id,
                "corp_id": inv.corp_id,
                "log_id": None,
                "created_at": None,
                "priority": "high",
            }
        )
        seen_ar.add(inv.id)

    ledgers = db.query(PmsArLedger).filter_by(hotel_id=hotel_id).all()
    for led in ledgers:
        corp = db.get(CorpAccount, led.corp_id)
        if not corp or corp.id in seen_corp:
            continue
        limit = _f(corp.credit_limit or led.credit_limit)
        used = _f(corp.credit_used or led.credit_used)
        if limit <= 0:
            continue
        rate = used / limit * 100
        if rate < 80 and used < limit * 0.98:
            continue
        tid = f"corp_{corp.id}_credit"
        if tid in dismissed:
            continue
        todos.append(
            {
                "id": tid,
                "source": "system",
                "type": "credit_warn",
                "title": f"授信占用偏高 · {corp.name} · {rate:.0f}%",
                "detail": f"已用 ¥{used:.0f} / 授信 ¥{limit:.0f} · 挂账前请确认额度",
                "amount": used,
                "ar_id": None,
                "corp_id": corp.id,
                "log_id": None,
                "created_at": None,
                "priority": "high" if rate >= 95 or used >= limit * 0.98 else "medium",
            }
        )
        seen_corp.add(corp.id)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    todos.sort(key=lambda x: (priority_order.get(x["priority"], 9), x.get("created_at") or ""), reverse=False)
    return todos[:20]


def dismiss_ar_ap_todo(
    db: Session,
    hotel_id: int,
    todo_id: str,
    operator: str,
    note: str = "",
) -> dict[str, Any]:
    """标记待办已跟进/关闭（不写回款，仅留痕）。"""
    tid = (todo_id or "").strip()
    if not tid:
        raise InvalidStateError("缺少待办 ID")

    if tid.startswith("log_"):
        log_id = int(tid.replace("log_", "", 1))
        log = db.get(ArApLog, log_id)
        if not log or log.hotel_id != hotel_id:
            raise NotFoundError("待办不存在")
        meta = _parse_meta(log.meta)
        meta["status"] = "done"
        log.meta = json.dumps(meta, ensure_ascii=False)
    else:
        ref_id = None
        if tid.startswith("ar_") or tid.startswith("aging_"):
            ref_id = int(tid.split("_", 1)[1])
        elif tid.startswith("corp_"):
            ref_id = int(tid.split("_")[1])
        db.add(
            ArApLog(
                hotel_id=hotel_id,
                action="todo_dismiss",
                ref_type="ar",
                ref_id=ref_id,
                operator_name=operator,
                reason=note or "已跟进/关闭待办",
                meta=json.dumps({"todo_id": tid}, ensure_ascii=False),
            )
        )
    db.flush()
    return {"todo_id": tid, "status": "dismissed"}


def list_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    normalize_agreement_orders(db, hotel_id)
    purge_non_real_ar_ap(db, hotel_id)
    sync_ar_ap_from_orders(db, hotel_id)
    today = date.today()
    week_start = today - timedelta(days=7)

    ar_rows = (
        db.query(ArInvoice)
        .filter_by(hotel_id=hotel_id)
        .filter(ArInvoice.status != "bad_debt")
        .order_by(ArInvoice.due_date.asc().nullslast(), ArInvoice.id.desc())
        .all()
    )
    ap_rows = (
        db.query(ApInvoice)
        .filter_by(hotel_id=hotel_id)
        .order_by(ApInvoice.due_date.asc().nullslast(), ApInvoice.id.desc())
        .all()
    )

    ar_balance = sum(max(0, _f(r.amount) - _f(r.paid_amount)) for r in ar_rows if r.status != "bad_debt")
    overdue = sum(max(0, _f(r.amount) - _f(r.paid_amount)) for r in ar_rows if r.status == "overdue")
    aging_90 = sum(
        max(0, _f(r.amount) - _f(r.paid_amount))
        for r in ar_rows
        if r.due_date and (today - r.due_date).days >= 90 and r.status not in ("settled", "bad_debt")
    )
    week_receipts = (
        db.query(ArApLog)
        .filter(
            ArApLog.hotel_id == hotel_id,
            ArApLog.action == "receipt",
            ArApLog.created_at >= datetime.combine(week_start, datetime.min.time()),
        )
        .all()
    )
    week_receipt_sum = sum(_f(x.amount) for x in week_receipts)

    ap_balance = sum(max(0, _f(r.amount) - _f(r.paid_amount)) for r in ap_rows if r.status != "settled")
    ap_pending = sum(
        max(0, _f(r.amount) - _f(r.paid_amount)) for r in ap_rows if r.status in ("open", "partial", "pending_deduct")
    )
    next_due = min((r.due_date for r in ap_rows if r.due_date and r.status != "settled"), default=None)
    week_payments = (
        db.query(ArApLog)
        .filter(
            ArApLog.hotel_id == hotel_id,
            ArApLog.action == "payment",
            ArApLog.created_at >= datetime.combine(week_start, datetime.min.time()),
        )
        .all()
    )
    week_payment_sum = sum(_f(x.amount) for x in week_payments)

    aging = {"d0_30": 0.0, "d30_60": 0.0, "d60_90": 0.0, "d90_plus": 0.0}
    for r in ar_rows:
        if r.status in ("settled", "bad_debt"):
            continue
        bal = max(0, _f(r.amount) - _f(r.paid_amount))
        if bal <= 0 or not r.due_date:
            aging["d0_30"] += bal
            continue
        days = (today - r.due_date).days
        if days < 0:
            aging["d0_30"] += bal
        elif days < 30:
            aging["d0_30"] += bal
        elif days < 60:
            aging["d30_60"] += bal
        elif days < 90:
            aging["d60_90"] += bal
        else:
            aging["d90_plus"] += bal

    credit_cards = []
    ledgers = db.query(PmsArLedger).filter_by(hotel_id=hotel_id).all()
    for led in ledgers:
        corp = db.get(CorpAccount, led.corp_id)
        if not corp:
            continue
        limit = _f(corp.credit_limit or led.credit_limit)
        used = _f(corp.credit_used or led.credit_used)
        rate = round(used / limit * 100, 1) if limit > 0 else 0
        overdue_cnt = sum(1 for r in ar_rows if r.corp_id == corp.id and r.status == "overdue")
        blocked = limit > 0 and used >= limit * 0.98
        credit_cards.append(
            {
                "corp_id": corp.id,
                "name": t("{name}（协议单位）", name=present_party_name(corp.name)),
                "credit_limit": limit,
                "credit_used": used,
                "usage_rate": rate,
                "term_days": _term_days(corp),
                "overdue_count": overdue_cnt,
                "blocked": blocked,
                "status": ("blocked" if blocked else "overdue" if overdue_cnt else "normal"),
            }
        )

    def _ota_calc_process(
        settle: OtaSettlement | None,
        *,
        kind: str,
        channel_name: str = "",
    ) -> str:
        """单据旁展示：房费 × (1 − 渠道佣金 x%) 或 房费 × 佣金 x%。"""
        if not settle:
            return "—"
        gross = _f(settle.gross_amount)
        commission = _f(settle.commission_amount)
        net = _f(settle.net_amount)
        if gross <= 0:
            return "—"
        pct = round(commission / gross * 100, 2)
        # 去掉多余小数尾零：12.00 → 12；12.50 → 12.5
        pct_s = f"{pct:.2f}".rstrip("0").rstrip(".")
        name = t((channel_name or "").strip()) if (channel_name or "").strip() else t("渠道")
        g = f"¥{gross:,.2f}"
        if kind == "net":
            return t(
                "{g} × (1 - {name}佣金 {pct}%) = ¥{net}",
                g=g,
                name=name,
                pct=pct_s,
                net=f"{net:,.2f}",
            )
        return t(
            "{g} × {name}佣金 {pct}% = ¥{commission}",
            g=g,
            name=name,
            pct=pct_s,
            commission=f"{commission:,.2f}",
        )

    settle_ids = {r.ota_settlement_id for r in ar_rows + ap_rows if getattr(r, "ota_settlement_id", None)}
    settles = {
        s.id: s for s in (db.query(OtaSettlement).filter(OtaSettlement.id.in_(settle_ids)).all() if settle_ids else [])
    }
    ch_by_id = {c.id: c for c in db.query(Channel).all()}

    def _fmt_ar(r: ArInvoice) -> dict:
        ch = ch_by_id.get(r.channel_id) if r.channel_id else None
        ch_name = (ch.name if ch else r.customer_name) or ""
        calc = "—"
        if r.ar_type == "ota_settlement" and r.ota_settlement_id:
            settle = settles.get(r.ota_settlement_id)
            calc = _ota_calc_process(settle, kind="net", channel_name=ch_name)
        pill_raw = (r.pill_note or "").replace("−", "-").strip()
        return {
            "id": r.id,
            "invoice_no": r.invoice_no,
            "customer_name": present_party_name(r.customer_name),
            "type": AR_TYPE_LABEL.get(r.ar_type, r.ar_type),
            "type_code": r.ar_type,
            "doc_label": present_doc_label(r.doc_label, channel_name=ch_name),
            "calc_process": calc,
            "amount": _f(r.amount),
            "paid_amount": _f(r.paid_amount),
            "balance": round(max(0, _f(r.amount) - _f(r.paid_amount)), 2),
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "status": r.status,
            "pill_note": None if pill_raw in ("净额=房费-佣金",) else present_sys_note(r.pill_note),
            "order_id": r.order_id,
            "corp_id": r.corp_id,
        }

    def _fmt_ap(r: ApInvoice) -> dict:
        ch = ch_by_id.get(r.channel_id) if r.channel_id else None
        ch_name = (ch.name if ch else r.vendor_name) or ""
        calc = "—"
        if r.ap_type == "ota_commission" and r.ota_settlement_id:
            settle = settles.get(r.ota_settlement_id)
            calc = _ota_calc_process(settle, kind="commission", channel_name=ch_name)
        return {
            "id": r.id,
            "invoice_no": r.invoice_no,
            "vendor_name": present_party_name(r.vendor_name),
            "type": AP_TYPE_LABEL.get(r.ap_type, r.ap_type),
            "type_code": r.ap_type,
            "doc_label": present_doc_label(r.doc_label, channel_name=ch_name),
            "calc_process": calc,
            "amount": _f(r.amount),
            "paid_amount": _f(r.paid_amount),
            "balance": round(max(0, _f(r.amount) - _f(r.paid_amount)), 2),
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "status": r.status,
            "note": present_sys_note(r.note),
        }

    corps = db.query(CorpAccount).filter_by(hotel_id=hotel_id, status="active").order_by(CorpAccount.name.asc()).all()

    return {
        "as_of": today.isoformat(),
        "kpi": {
            "ar_balance": round(ar_balance, 2),
            "ar_overdue": round(overdue, 2),
            "ar_aging_90_plus": round(aging_90, 2),
            "ar_week_receipts": round(week_receipt_sum, 2),
            "ap_balance": round(ap_balance, 2),
            "ap_pending": round(ap_pending, 2),
            "ap_next_due": next_due.isoformat() if next_due else None,
            "ap_week_payments": round(week_payment_sum, 2),
        },
        "aging": {k: round(v, 2) for k, v in aging.items()},
        "credit_accounts": credit_cards,
        "corps": [
            {
                "id": c.id,
                "name": present_party_name(c.name),
                "credit_limit": _f(c.credit_limit),
                "credit_used": _f(c.credit_used),
                "credit_available": round(max(0, _f(c.credit_limit) - _f(c.credit_used)), 2),
                "term_days": _term_days(c),
            }
            for c in corps
        ],
        "ar_invoices": [_fmt_ar(r) for r in ar_rows],
        "ap_invoices": [_fmt_ap(r) for r in ap_rows],
        "todos": list_ar_ap_todos(db, hotel_id, ar_rows=ar_rows),
        "footnote": "",
    }


def apply_receipt(
    db: Session,
    hotel_id: int,
    ar_id: int,
    amount: float,
    channel: str,
    operator: str,
    ref_no: str = "",
) -> dict[str, Any]:
    row = db.get(ArInvoice, ar_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("应收单据不存在")
    if row.status in ("settled", "bad_debt"):
        raise InvalidStateError("该单据已结清或已核销坏账")
    bal = _f(row.amount) - _f(row.paid_amount)
    if amount <= 0 or amount > bal + 0.01:
        raise InvalidStateError(f"回款金额须在 0～{bal:.2f} 之间")

    row.paid_amount = _money(_f(row.paid_amount) + amount)
    today = date.today()
    row.status = _ar_status(_money(row.amount), _money(row.paid_amount), row.due_date, today)

    if row.ar_type == "corp_on_account" and row.corp_id:
        led = _ensure_ledger(db, hotel_id, row.corp_id)
        db.add(
            PmsArEntry(
                ar_ledger_id=led.id,
                entry_type="settle",
                order_id=row.order_id,
                amount=_money(amount),
                ref_no=ref_no or channel,
                note=f"回款核销 · {channel}",
            )
        )
        led.settled_total = _money(_f(led.settled_total) + amount)
        led.balance = _money(max(0, _f(led.balance) - amount))
        led.credit_used = _money(max(0, _f(led.credit_used) - amount))
        corp = db.get(CorpAccount, row.corp_id)
        if corp:
            corp.credit_used = _money(max(0, _f(corp.credit_used) - amount))

    if row.ar_type == "ota_settlement" and row.ota_settlement_id:
        settle = db.get(OtaSettlement, row.ota_settlement_id)
        if settle:
            settle.paid_net = _money(_f(settle.paid_net) + amount)
            if _f(settle.paid_net) >= _f(settle.net_amount):
                settle.status = "settled"
                ap = db.query(ApInvoice).filter_by(hotel_id=hotel_id, ota_settlement_id=settle.id).first()
                if ap:
                    ap.paid_amount = ap.amount
                    ap.status = "settled"

    _log(db, hotel_id, "receipt", "ar", ar_id, amount, operator, reason=channel, meta=ref_no)
    db.flush()
    return {"ar_id": ar_id, "paid_amount": _f(row.paid_amount), "status": row.status}


def apply_payment(
    db: Session,
    hotel_id: int,
    ap_id: int,
    amount: float,
    channel: str,
    operator: str,
    ref_no: str = "",
) -> dict[str, Any]:
    row = db.get(ApInvoice, ap_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("应付单据不存在")
    if row.status == "settled":
        raise InvalidStateError("该应付已结清")
    if row.ap_type == "ota_commission" and row.note == "结算时扣减":
        raise InvalidStateError("OTA 佣金由平台结算自动扣减，无需单独付款")
    bal = _f(row.amount) - _f(row.paid_amount)
    if amount <= 0 or amount > bal + 0.01:
        raise InvalidStateError(f"付款金额须在 0～{bal:.2f} 之间")

    row.paid_amount = _money(_f(row.paid_amount) + amount)
    today = date.today()
    row.status = _ap_status(_money(row.amount), _money(row.paid_amount), row.ap_type, row.due_date, today)
    _log(db, hotel_id, "payment", "ap", ap_id, amount, operator, reason=channel, meta=ref_no)
    db.flush()
    return {"ap_id": ap_id, "paid_amount": _f(row.paid_amount), "status": row.status}


def write_off_ar(
    db: Session,
    hotel_id: int,
    ar_id: int,
    reason: str,
    approver: str,
    operator: str,
) -> dict[str, Any]:
    row = db.get(ArInvoice, ar_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("应收单据不存在")
    if row.status in ("settled", "bad_debt"):
        raise InvalidStateError("该单据不可再核销坏账")
    if not approver.strip():
        raise InvalidStateError("须填写审批人（总经理）")
    if not reason.strip():
        raise InvalidStateError("须填写核销原因")

    bal = max(0, _f(row.amount) - _f(row.paid_amount))
    row.status = "bad_debt"
    row.paid_amount = row.amount

    if row.corp_id:
        led = _ensure_ledger(db, hotel_id, row.corp_id)
        db.add(
            PmsArEntry(
                ar_ledger_id=led.id,
                entry_type="write_off",
                order_id=row.order_id,
                amount=_money(bal),
                note=f"坏账核销 · {reason} · 审批:{approver}",
            )
        )
        led.balance = _money(max(0, _f(led.balance) - bal))
        led.credit_used = _money(max(0, _f(led.credit_used) - bal))
        corp = db.get(CorpAccount, row.corp_id)
        if corp:
            corp.credit_used = _money(max(0, _f(corp.credit_used) - bal))

    _log(
        db,
        hotel_id,
        "write_off",
        "ar",
        ar_id,
        bal,
        operator,
        reason=reason,
        meta=f"approver={approver}",
    )
    db.flush()
    return {"ar_id": ar_id, "status": "bad_debt", "amount_written": bal}


def create_corp_charge(
    db: Session,
    hotel_id: int,
    corp_id: int,
    amount: float,
    operator: str,
    note: str = "",
) -> dict[str, Any]:
    chk = check_credit(db, hotel_id, corp_id, amount)
    if chk["blocked"]:
        raise InvalidStateError(chk["message"])

    corp = db.get(CorpAccount, corp_id)
    led = _ensure_ledger(db, hotel_id, corp_id)
    amt = _money(amount)
    entry = PmsArEntry(
        ar_ledger_id=led.id,
        entry_type="charge",
        amount=amt,
        note=note or "手工企业挂账",
    )
    db.add(entry)
    db.flush()

    led.charged_total = _money(_f(led.charged_total) + amount)
    led.balance = _money(_f(led.balance) + amount)
    led.credit_used = _money(_f(led.credit_used) + amount)
    corp.credit_used = _money(_f(corp.credit_used) + amount)

    due = _due_from_base(date.today(), _term_days(corp))
    inv_no = f"AR-{entry.id:04d}"
    inv = ArInvoice(
        hotel_id=hotel_id,
        invoice_no=inv_no,
        ar_type="corp_on_account",
        customer_name=corp.name,
        corp_id=corp_id,
        pms_ar_entry_id=entry.id,
        doc_label=encode_note_doc(note),
        amount=amt,
        due_date=due,
        status="open",
        credit_limit_snapshot=corp.credit_limit,
    )
    db.add(inv)
    _log(db, hotel_id, "charge", "ar", entry.id, amount, operator, reason=note)
    db.flush()
    return {"ar_id": inv.id, "invoice_no": inv_no, "credit_check": chk}


def settle_ar_ledger(
    db: Session,
    ledger_id: int,
    *,
    hotel_id: int,
    amount: float | Decimal,
    ref_no: Optional[str] = None,
    note: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """对公回款核销：写 settle 分录并回写账本/授信（勿 commit，由 facade 提交）。"""
    led = db.get(PmsArLedger, ledger_id)
    if not led or led.hotel_id != hotel_id:
        raise NotFoundError("AR 账本不存在")
    amt = _money(amount)
    if amt <= 0:
        raise ValidationError("核销金额须大于 0")
    entry = PmsArEntry(
        ar_ledger_id=led.id,
        entry_type="settle",
        amount=amt,
        ref_no=ref_no,
        note=note or "对公回款核销",
        operator_id=operator_id,
    )
    db.add(entry)
    led.settled_total = _money(_f(led.settled_total) + float(amt))
    led.balance = _money(_f(led.balance) - float(amt))
    led.credit_used = max(Decimal("0"), _money(_f(led.credit_used) - float(amt)))
    corp = db.get(CorpAccount, led.corp_id)
    if corp:
        corp.credit_used = max(Decimal("0"), _money(_f(corp.credit_used) - float(amt)))
    db.flush()
    return {
        "ar_ledger_id": led.id,
        "balance": float(led.balance or 0),
        "settled_total": float(led.settled_total or 0),
        "entry_id": entry.id,
    }
