# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: revenue_service。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    Channel,
    Deposit,
    DepositLedgerEntry,
    FinanceReport,
    Guest,
    GuestTag,
    Order,
    Payment,
    Reservation,
    Room,
    ServiceRequest,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    Supply,
    TagDefinition,
    User,
)


def _revenue_target(db: Session, hotel_id: int, shift_date: date) -> float | None:
    """班次营收目标：仅读取 finance_reports，无则返回 None。"""
    period = shift_date.strftime("%Y-%m-%d")
    for metric in ("shift_revenue_target", "daily_revenue_target", "revenue_target"):
        row = (
            db.query(FinanceReport)
            .filter_by(hotel_id=hotel_id, metric=metric, period=period)
            .order_by(FinanceReport.id.desc())
            .first()
        )
        if row and row.value is not None and (float(row.value) > 0):
            return float(row.value)
    row = (
        db.query(FinanceReport)
        .filter_by(hotel_id=hotel_id, metric="shift_revenue_target")
        .order_by(FinanceReport.id.desc())
        .first()
    )
    if row and row.value is not None and (float(row.value) > 0):
        return float(row.value)
    return None


def _channel_revenue(db: Session, hotel_id: int, start: datetime, end: datetime) -> list[dict]:
    rows = (
        db.query(Payment, Order, Channel)
        .outerjoin(Order, Order.id == Payment.order_id)
        .outerjoin(Channel, Channel.id == Order.channel_id)
        .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start, Payment.paid_at < end, Payment.amount > 0)
        .all()
    )
    bag: dict[str, dict] = {}
    for pay, order, ch in rows:
        amt = float(pay.amount or 0)
        method = (pay.method or "").lower()
        if "cash" in method or "现金" in method:
            key, name = ("cash", "现场现付")
        elif ch and ch.name:
            key, name = (f"ch_{ch.id}", ch.name)
        elif order and order.channel_id:
            key, name = (f"ch_{order.channel_id}", "其他渠道")
        else:
            key, name = ("other", "其他")
        b = bag.setdefault(key, {"channel": name, "count": 0, "amount": 0.0})
        b["count"] += 1
        b["amount"] += amt
    items = sorted(bag.values(), key=lambda x: -x["amount"])
    total = sum(x["amount"] for x in items) or 1.0
    return [
        {
            "channel": x["channel"],
            "count": x["count"],
            "amount": round(x["amount"], 2),
            "share_pct": round(100 * x["amount"] / total, 1),
        }
        for x in items
    ]


def _merge_yesterday(channels: list[dict], yesterday: list[dict]) -> list[dict]:
    ymap = {c["channel"]: c["amount"] for c in yesterday}
    out = []
    for c in channels:
        y = ymap.get(c["channel"], 0)
        diff_pct = round(100 * (c["amount"] - y) / y, 1) if y else None
        out.append({**c, "yesterday_amount": y, "diff_pct": diff_pct})
    return out


def _deposit_handover(db: Session, hotel_id: int, start: datetime, end: datetime) -> dict:
    collected = refunded = 0.0
    c_cnt = r_cnt = 0
    deps = db.query(Deposit).filter_by(hotel_id=hotel_id).all()
    for d in deps:
        created = d.created_at
        if created and start <= created < end:
            collected += float(d.original_amount or 0) / 100
            c_cnt += 1
        if d.released_at and start <= d.released_at < end:
            refunded += float(d.captured_amount or d.original_amount or 0) / 100
            r_cnt += 1
        else:
            led = (
                db.query(DepositLedgerEntry)
                .filter_by(deposit_id=d.deposit_id)
                .filter(DepositLedgerEntry.created_at >= start, DepositLedgerEntry.created_at < end)
                .all()
            )
            for e in led:
                if (e.event or "").lower() in ("refund", "release", "退"):
                    refunded += abs(float(e.amount_delta or 0)) / 100
                    r_cnt += 1
    net = round(collected - refunded, 2)
    pending_refund = (
        db.query(Deposit)
        .filter(Deposit.hotel_id == hotel_id, Deposit.status.in_(("FROZEN", "CAPTURED", "HELD", "ACTIVE")))
        .count()
    )
    return {
        "collected": round(collected, 2),
        "collected_count": c_cnt,
        "refunded": round(refunded, 2),
        "refunded_count": r_cnt,
        "net": net,
        "pending_refund_count": pending_refund,
        "hint": f"接班人需承接 ¥{net:,.2f} 退押压力（含 {pending_refund} 笔待离店退押）。跨班退押须在投款信封上注明退负金额。"
        if net > 0
        else "",
    }
