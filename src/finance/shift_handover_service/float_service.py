# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: float_service。
"""

from __future__ import annotations

import json
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
from finance.doc_identity import present_diff_type_label

# 同包 cross-import（拆分后必须显式 import）
from finance.shift_handover_service._common import _log, _money
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

FLOAT_DENOMS = [(100, "100 元"), (50, "50 元"), (20, "20 元"), (10, "10 元"), (5, "5 元"), (1, "1 元（硬币）")]


def _float_expected(db: Session, hotel_id: int) -> float:
    """备用金底数：财务参数（active）→ 上一班归档实盘 → 0。"""
    from finance.finance_float_service import get_active_float_carry_amount

    amt = get_active_float_carry_amount(db, hotel_id)
    if amt > 0:
        return amt
    fr = (
        db.query(FinanceReport)
        .filter_by(hotel_id=hotel_id, metric="float_carry")
        .order_by(FinanceReport.id.desc())
        .first()
    )
    if fr and fr.value is not None:
        return float(fr.value)
    prev = (
        db.query(ShiftHandover)
        .filter(
            ShiftHandover.hotel_id == hotel_id,
            ShiftHandover.status == "archived",
            ShiftHandover.float_actual.isnot(None),
        )
        .order_by(ShiftHandover.id.desc())
        .first()
    )
    if prev and prev.float_actual is not None:
        return float(prev.float_actual)
    return 0.0


def _float_breakdown_expected(expected: float, db: Session | None = None, hotel_id: int | None = None) -> list[dict]:
    """按面额拆分应有数量（配比来自财务参数；实盘须前台录入）。"""
    ratios = None
    if db is not None and hotel_id is not None:
        from finance.finance_float_service import get_active_denom_ratios, suggest_denom_breakdown

        ratios = get_active_denom_ratios(db, hotel_id)
        if expected <= 0:
            return [{"denom": d["denom"], "label": d["label"], "expected_qty": 0, "actual_qty": 0} for d in ratios]
        return [{**d, "actual_qty": 0} for d in suggest_denom_breakdown(expected, ratios)]
    if expected <= 0:
        from infra.i18n import t as _t

        return [{"denom": d, "label": _t(lbl), "expected_qty": 0, "actual_qty": 0} for d, lbl in FLOAT_DENOMS]
    ratios_legacy = [0.8, 0.1, 0.06, 0.02, 0.01, 0.004, 0.004, 0.004]
    out = []
    from infra.i18n import t as _t

    for (denom, label), ratio in zip(FLOAT_DENOMS, ratios_legacy):
        sub = expected * ratio
        qty = int(sub / denom) if denom >= 1 else int(sub / denom)
        out.append({"denom": denom, "label": _t(label), "expected_qty": qty, "actual_qty": 0})
    return out


def _sync_float_breakdown(db: Session, handover: ShiftHandover) -> None:
    """未确认盘库前，按应有备用金刷新面额拆分；不覆盖已录入实盘。剔除散角面额。"""
    if handover.float_confirmed:
        return
    expected = float(handover.float_expected or 0)
    breakdown = _float_breakdown_expected(expected, db, handover.hotel_id)
    allowed = {float(item["denom"]) for item in breakdown}
    existing = {float(r.denom): r for r in db.query(ShiftFloatCount).filter_by(handover_id=handover.id).all()}
    for denom, row in list(existing.items()):
        if denom not in allowed:
            db.delete(row)
            existing.pop(denom, None)
    for item in breakdown:
        denom = float(item["denom"])
        row = existing.get(denom)
        if row:
            row.expected_qty = item["expected_qty"]
            row.label = item["label"]
            if not handover.float_confirmed:
                row.actual_qty = 0
        else:
            db.add(
                ShiftFloatCount(
                    handover_id=handover.id,
                    denom=_money(denom),
                    label=item["label"],
                    expected_qty=item["expected_qty"],
                    actual_qty=0,
                )
            )


def _float_history(db: Session, hotel_id: int, limit: int = 10) -> dict:
    rows = (
        db.query(ShiftHandover)
        .filter(
            ShiftHandover.hotel_id == hotel_id,
            ShiftHandover.float_diff.isnot(None),
            ShiftHandover.status.in_(("signed", "archived")),
        )
        .order_by(ShiftHandover.id.desc())
        .limit(limit)
        .all()
    )
    bars = []
    short_n = long_n = flat_n = 0
    max_diff = 0.0
    for r in reversed(rows):
        diff = float(r.float_diff or 0)
        if abs(diff) < 0.01:
            flat_n += 1
            kind = "zero"
        elif diff > 0:
            long_n += 1
            kind = "up"
        else:
            short_n += 1
            kind = "down"
        max_diff = max(max_diff, abs(diff))
        bars.append({"diff": diff, "kind": kind, "shift_no": r.shift_no})
    trend = "稳定" if short_n <= 1 else "关注"
    return {
        "bars": bars,
        "short_count": short_n,
        "long_count": long_n,
        "flat_count": flat_n,
        "max_diff": round(max_diff, 2),
        "trend": trend,
    }


def save_float_count(
    db: Session,
    hotel_id: int,
    handover_id: int,
    denominations: list[dict] | None = None,
    diff_reason: str = "",
    operator_id: int | None = None,
    operator_name: str = "",
    float_actual: float | None = None,
) -> dict:
    """交班人备用金盘库：以「实点总额」为主；面额明细选填（精细清点）。"""
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    if row.status in ("archived",):
        raise InvalidStateError("已归档交班不可修改")
    denominations = denominations or []
    float_rows = [
        r for r in db.query(ShiftFloatCount).filter_by(handover_id=handover_id).all() if float(r.denom or 0) >= 1
    ]
    for r in db.query(ShiftFloatCount).filter_by(handover_id=handover_id).all():
        if float(r.denom or 0) < 1:
            db.delete(r)
    detail_sum = None
    if denominations:
        by_denom = {float(d["denom"]): d for d in denominations if float(d.get("denom") or 0) >= 1}
        detail_sum = 0.0
        for r in float_rows:
            d = by_denom.get(float(r.denom))
            if d is not None:
                r.actual_qty = int(d.get("actual_qty") or 0)
            detail_sum += float(r.denom) * int(r.actual_qty or 0)
        detail_sum = round(detail_sum, 2)
    if float_actual is None:
        if detail_sum is None:
            raise InvalidStateError("请填写本班实点总额")
        actual = detail_sum
    else:
        actual = round(float(float_actual), 2)
        if detail_sum is not None and abs(detail_sum - actual) >= 0.01:
            raise InvalidStateError(f"明细合计 ¥{detail_sum:.2f} 与实点总额 ¥{actual:.2f} 不一致")
    expected = float(row.float_expected or 0)
    diff = round(actual - expected, 2)
    row.float_actual = _money(actual)
    row.float_diff = _money(diff)
    if abs(diff) < 0.01:
        row.diff_type = "flat"
        row.diff_reason = diff_reason or None
    else:
        row.diff_type = "long" if diff > 0 else "short"
        if not (diff_reason or "").strip():
            raise InvalidStateError("备用金有差异时必须填写原因")
        row.diff_reason = diff_reason.strip()
    row.float_confirmed = True
    row.manager_required = abs(diff) >= 5
    _log(
        db,
        handover_id,
        hotel_id,
        "float_count",
        operator_id,
        operator_name,
        {"diff": diff, "actual": actual, "has_detail": bool(denominations)},
    )
    db.commit()
    return {
        "float_actual": actual,
        "float_diff": diff,
        "diff_type": row.diff_type,
        "diff_type_label": present_diff_type_label(row.diff_type),
    }
