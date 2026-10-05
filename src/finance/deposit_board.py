# SPDX-License-Identifier: Apache-2.0
"""押金看板与异常检测（从 deposit_service 绞杀抽出）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from finance.deposit_common import serialize_deposit, yuan
from finance.deposit_status import ABNORMAL, FORMS, IN_HOLD, STATUS_LABEL, TERMINAL
from models import Deposit


def detect_anomalies(db: Session, hotel_id: int) -> list[dict[str, Any]]:
    from infra.i18n import t

    now = datetime.now()
    rows = db.query(Deposit).filter(Deposit.hotel_id == hotel_id, Deposit.status.in_(list(IN_HOLD))).all()
    out: list[dict[str, Any]] = []
    for d in rows:
        room = d.room_no or ""
        guest = d.guest_name or ""
        who = f"{room} {guest}".strip()
        if d.status == "EXPIRED" or (d.auth_expire_at and d.auth_expire_at < now and d.status == "FROZEN"):
            exp = (d.auth_expire_at or now).strftime("%m/%d")
            out.append(
                {
                    "type": "auth_expired",
                    "title": t("预授权过期"),
                    "level": "warn",
                    "deposit_id": d.deposit_id,
                    "room_no": d.room_no,
                    "guest_name": d.guest_name,
                    "detail": t("{who} · 授权已于 {date} 过期", who=who, date=exp),
                }
            )
        elif d.auth_expire_at and 0 < (d.auth_expire_at - now).total_seconds() < 3 * 86400 and d.status == "FROZEN":
            exp = d.auth_expire_at.strftime("%m/%d")
            out.append(
                {
                    "type": "auth_expiring",
                    "title": t("预授权临期"),
                    "level": "warn",
                    "deposit_id": d.deposit_id,
                    "room_no": d.room_no,
                    "guest_name": d.guest_name,
                    "detail": t("{who} · {date} 到期，建议重授权", who=who, date=exp),
                }
            )
        if d.status == "DISPUTED":
            age_h = 0
            if d.updated_at:
                age_h = int((now - d.updated_at).total_seconds() / 3600)
            out.append(
                {
                    "type": "disputed",
                    "title": t("争议未结"),
                    "level": "danger" if age_h >= 18 else "warn",
                    "deposit_id": d.deposit_id,
                    "room_no": d.room_no,
                    "guest_name": d.guest_name,
                    "detail": t("{who} · 金额不符，已挂 {hours}h", who=who, hours=age_h),
                }
            )
        if d.form == "CASH" and not d.receipt_no:
            out.append(
                {
                    "type": "cash_no_receipt",
                    "title": t("现金无收据"),
                    "level": "danger",
                    "deposit_id": d.deposit_id,
                    "room_no": d.room_no,
                    "guest_name": d.guest_name,
                    "detail": t("{who} · 现金押金 ¥{amt} 缺收据号", who=who, amt=f"{yuan(d.original_amount):.0f}"),
                }
            )
        if d.status in ("FROZEN", "PARTIAL_CAPTURE") and d.remaining_refund < 20000 and d.original_amount > 0:
            out.append(
                {
                    "type": "insufficient",
                    "title": t("在押不足"),
                    "level": "warn",
                    "deposit_id": d.deposit_id,
                    "room_no": d.room_no,
                    "guest_name": d.guest_name,
                    "detail": t("{who} · 剩余 ¥{amt}，预估杂费不足", who=who, amt=f"{yuan(d.remaining_refund):.0f}"),
                }
            )
    # 去重同 deposit 同类
    seen = set()
    uniq = []
    for a in out:
        key = (a["deposit_id"], a["type"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq


def board(
    db: Session,
    hotel_id: int,
    *,
    status: str | None = None,
    form: str | None = None,
    q: str | None = None,
    bucket: str | None = None,
) -> dict[str, Any]:
    query = db.query(Deposit).filter(Deposit.hotel_id == hotel_id)
    if status:
        query = query.filter(Deposit.status == status)
    if form:
        query = query.filter(Deposit.form == form)
    if bucket == "holding":
        query = query.filter(Deposit.status.in_(list(IN_HOLD - ABNORMAL)))
    elif bucket == "pending_release":
        query = query.filter(Deposit.status.in_(["FROZEN", "PARTIAL_CAPTURE"]))
    elif bucket == "abnormal":
        query = query.filter(Deposit.status.in_(list(ABNORMAL)))
    elif bucket == "cash":
        query = query.filter(Deposit.form == "CASH")
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Deposit.room_no.ilike(like))
            | (Deposit.order_no.ilike(like))
            | (Deposit.guest_name.ilike(like))
            | (Deposit.deposit_id.ilike(like))
        )
    rows = query.order_by(Deposit.updated_at.desc()).limit(200).all()

    all_rows = db.query(Deposit).filter(Deposit.hotel_id == hotel_id).all()
    held = sum(d.remaining_refund for d in all_rows if d.status in IN_HOLD)
    held_count = sum(1 for d in all_rows if d.status in IN_HOLD)
    today = datetime.now().date()
    today_refund = sum(
        d.original_amount - d.captured_amount
        for d in all_rows
        if d.status in TERMINAL and d.released_at and d.released_at.date() == today
    )
    anomalies = detect_anomalies(db, hotel_id)

    return {
        "summary": {
            "held_yuan": yuan(held),
            "held_cents": held,
            "count": held_count,
            "today_refund_yuan": yuan(today_refund),
            "anomaly_count": len(anomalies),
        },
        "anomalies": anomalies,
        "deposits": [serialize_deposit(d) for d in rows],
        "forms": [{"code": k, "label": v} for k, v in FORMS.items()],
        "statuses": [{"code": k, "label": v} for k, v in STATUS_LABEL.items()],
    }
