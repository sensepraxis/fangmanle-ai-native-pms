# SPDX-License-Identifier: Apache-2.0
"""夜审编排与查询 — 从 Fat Controller 下沉。

职责：
  - run_night_audit：日租入账 → 房态翻转 → 证件清理 → 汇总写 NightAuditLog
  - list / detail：只读查询组装
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import NotFoundError, ValidationError
from events import emit
from models import Invoice, NightAuditLog, Order, Payment, PriceSuggestion


def run_night_audit(
    db: Session,
    hotel_id: int,
    biz_date: date,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """执行夜审并提交事务（Template Method：``NightAuditPipeline``）。"""
    from finance.night_audit_pipeline import run_night_audit_pipeline

    return run_night_audit_pipeline(db, hotel_id, biz_date, force=force)


def list_night_audits(db: Session, hotel_id: int, *, limit: int = 30) -> list[dict]:
    rows = (
        db.query(NightAuditLog).filter_by(hotel_id=hotel_id).order_by(NightAuditLog.biz_date.desc()).limit(limit).all()
    )
    return [row_to_dict(r) for r in rows]


def get_night_audit_detail(db: Session, hotel_id: int, biz_date: date | str) -> dict[str, Any]:
    """夜审详情：当日营收/间夜/异常 + 订单与支付明细。"""
    if isinstance(biz_date, str):
        try:
            d = datetime.strptime(biz_date, "%Y-%m-%d").date()
        except Exception as e:
            raise ValidationError("biz_date must be YYYY-MM-DD") from e
    else:
        d = biz_date

    log = db.query(NightAuditLog).filter_by(hotel_id=hotel_id, biz_date=d).first()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    payments = (
        db.query(Payment)
        .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start, Payment.paid_at < end)
        .order_by(Payment.id.desc())
        .all()
    )
    orders_checked_out = db.query(Order).filter(Order.hotel_id == hotel_id, Order.check_out == d).all()
    no_show = db.query(Order).filter_by(hotel_id=hotel_id, status="no_show").count()
    blocked_pricing = (
        db.query(PriceSuggestion)
        .filter_by(hotel_id=hotel_id, status="blocked")
        .filter(PriceSuggestion.biz_date >= start, PriceSuggestion.biz_date < end)
        .all()
    )
    invoices = (
        db.query(Invoice)
        .filter(Invoice.hotel_id == hotel_id, Invoice.issued_at >= start, Invoice.issued_at < end)
        .all()
    )
    return {
        "log": row_to_dict(log) if log else None,
        "biz_date": d.isoformat(),
        "payments": [row_to_dict(p) for p in payments],
        "checked_out_orders": [row_to_dict(o) for o in orders_checked_out],
        "blocked_pricing": [row_to_dict(p) for p in blocked_pricing],
        "invoices": [row_to_dict(i) for i in invoices],
        "exceptions": no_show,
    }


def fix_audit_exception(db: Session, eid: int) -> dict:
    from models import NightAuditException

    row = db.get(NightAuditException, eid)
    if not row:
        raise NotFoundError("exception not found")
    row.status = "fixed"
    row.fixed_at = datetime.now()
    db.flush()
    return row_to_dict(row)
