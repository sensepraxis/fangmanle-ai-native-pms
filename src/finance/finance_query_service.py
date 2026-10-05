# SPDX-License-Identifier: Apache-2.0
"""财务读查询（Query Object）：从 Fat Router 下沉的只读聚合。

约定：本模块只读、不 commit；router 经 ``application.finance`` 调用。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from api_common import row_to_dict
from models import (
    FinanceReport,
    LedgerEntry,
    NightAuditException,
    NightAuditLog,
    ProfitInsight,
    ReconBatch,
    ReconItem,
    RevenueAnomaly,
    RiskAlert,
    TaxFiling,
)


def finance_flow_summary(db: Session, hotel_id: int) -> dict[str, Any]:
    """动线总览：最近夜审 + 异常/对账/报税/利润计数。"""
    latest = db.query(NightAuditLog).filter_by(hotel_id=hotel_id).order_by(NightAuditLog.biz_date.desc()).first()
    open_exc = db.query(NightAuditException).filter_by(hotel_id=hotel_id, status="open").count()
    conflict_batches = db.query(ReconBatch).filter_by(hotel_id=hotel_id, status="conflict").count()
    pending_tax = (
        db.query(TaxFiling).filter(TaxFiling.hotel_id == hotel_id, TaxFiling.status.in_(["draft", "ready"])).count()
    )
    open_insights = db.query(ProfitInsight).filter_by(hotel_id=hotel_id, status="open").count()
    reports = db.query(FinanceReport).filter_by(hotel_id=hotel_id).order_by(FinanceReport.id.desc()).limit(12).all()
    return {
        "latest_audit": row_to_dict(latest) if latest else None,
        "open_exceptions": open_exc,
        "conflict_batches": conflict_batches,
        "pending_tax": pending_tax,
        "open_insights": open_insights,
        "reports": [row_to_dict(r) for r in reports],
    }


def list_ledger_entries(db: Session, hotel_id: int, *, limit: int = 40) -> dict[str, Any]:
    """账务流水（ledger_entries），供常住账务页。"""
    limit = max(5, min(100, int(limit or 40)))
    rows = (
        db.query(LedgerEntry)
        .filter_by(hotel_id=hotel_id)
        .order_by(LedgerEntry.biz_date.desc(), LedgerEntry.id.desc())
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for e in rows:
        debit = float(e.debit or 0)
        credit = float(e.credit or 0)
        amt = debit if debit else credit
        paid = credit > 0 and debit <= 0
        acct = e.account or "账务"
        icon = "home"
        if any(k in acct for k in ("电", "水", "燃", "能源")):
            icon = "bolt"
        elif any(k in acct for k in ("洗衣", "干洗", "客需")):
            icon = "local_laundry_service"
        elif "押" in acct:
            icon = "account_balance_wallet"
        out.append(
            {
                "id": e.id,
                "date": e.biz_date.isoformat() if e.biz_date else None,
                "icon": icon,
                "iconCls": "" if paid else "text-primary",
                "desc": acct,
                "amount": f"{amt:,.2f}",
                "amount_num": amt,
                "paid": paid,
                "debit": debit,
                "credit": credit,
                "ref_type": e.ref_type,
            }
        )
    billed = sum(float(e.debit or 0) for e in rows)
    settled = sum(float(e.credit or 0) for e in rows)
    return {
        "entries": out,
        "summary": {
            "billed": f"{billed:,.0f}",
            "deposits": f"{max(0, settled * 0.2):,.0f}",
            "outstanding": f"{max(0, billed - settled):,.0f}",
            "utility": f"{sum(x['amount_num'] for x in out if x['icon'] == 'bolt'):,.0f}",
        },
    }


def list_risk_alerts(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(RiskAlert).filter(RiskAlert.hotel_id == hotel_id).all()
    return [row_to_dict(r) for r in rows]


def list_audit_exceptions(
    db: Session,
    hotel_id: int,
    *,
    biz_date: Optional[str] = None,
) -> list[dict]:
    from domain import ValidationError

    q = db.query(NightAuditException).filter_by(hotel_id=hotel_id)
    if biz_date:
        try:
            d = datetime.strptime(biz_date, "%Y-%m-%d").date()
            q = q.filter_by(biz_date=d)
        except Exception as e:
            raise ValidationError("biz_date must be YYYY-MM-DD") from e
    rows = q.order_by(NightAuditException.id.desc()).limit(50).all()
    return [row_to_dict(r) for r in rows]


def list_recon_conflicts(db: Session, hotel_id: int) -> list[dict]:
    """冲突明细（供审计冲突下钻页）。"""
    from finance.recon_service import serialize_recon_batch

    rows = (
        db.query(ReconItem)
        .filter_by(hotel_id=hotel_id, match_status="conflict")
        .order_by(ReconItem.id.desc())
        .limit(40)
        .all()
    )
    out: list[dict] = []
    for it in rows:
        d = row_to_dict(it)
        batch = db.get(ReconBatch, it.batch_id)
        if batch:
            d["batch"] = serialize_recon_batch(db, batch)
        else:
            d["batch"] = None
        out.append(d)
    return out


def list_tax_filings(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(TaxFiling)
        .filter_by(hotel_id=hotel_id)
        .order_by(TaxFiling.period.desc(), TaxFiling.id.desc())
        .limit(30)
        .all()
    )
    return [row_to_dict(r) for r in rows]


def list_profit_insights(db: Session, hotel_id: int) -> list[dict]:
    from infra.i18n import t as _t

    rows = db.query(ProfitInsight).filter_by(hotel_id=hotel_id).order_by(ProfitInsight.id.desc()).limit(30).all()
    out = []
    for r in rows:
        d = row_to_dict(r)
        if d.get("title"):
            d["title"] = _t(str(d["title"]))
        if d.get("recommendation"):
            d["recommendation"] = _t(str(d["recommendation"]))
        out.append(d)
    return out


def list_revenue_anomalies(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(RevenueAnomaly)
        .filter_by(hotel_id=hotel_id)
        .order_by(RevenueAnomaly.score.desc(), RevenueAnomaly.id.desc())
        .all()
    )
    out: list[dict] = []
    for r in rows:
        d = row_to_dict(r)
        try:
            d["timeline"] = json.loads(r.timeline_json or "[]")
        except Exception:
            d["timeline"] = []
        out.append(d)
    return out


__all__ = [
    "finance_flow_summary",
    "list_ledger_entries",
    "list_risk_alerts",
    "list_audit_exceptions",
    "list_recon_conflicts",
    "list_tax_filings",
    "list_profit_insights",
    "list_revenue_anomalies",
]
