# SPDX-License-Identifier: Apache-2.0
"""营收 / KPI 聚合口径。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from finance.reports.period import _compare_range, _delta_pct, _dt_range, _money, _pct
from models import FinanceTaxConfig, NightAuditLog, Order, Payment, ProfitInsight, Room

REV_STATUSES = ("checked_in", "checked_out", "reserved", "confirmed")


def _sum_payments(db: Session, hotel_id: int, d0: date, d1: date) -> float:
    start, end = _dt_range(d0, d1)
    try:
        rows = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start, Payment.paid_at < end)
            .scalar()
        )
        return _money(rows)
    except Exception:
        return 0.0


def _orders_in_period(db: Session, hotel_id: int, d0: date, d1: date) -> list[Order]:
    """入住日落在期间内的订单（收入明细/到店口径）。"""
    return (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(list(REV_STATUSES)),
            Order.check_in >= d0,
            Order.check_in <= d1,
        )
        .all()
    )


def _orders_overlapping(db: Session, hotel_id: int, d0: date, d1: date) -> list[Order]:
    """与期间有入住重叠的订单（ADR/OCC/RevPAR 口径）。"""
    return (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(list(REV_STATUSES)),
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= d1,
            Order.check_out > d0,
        )
        .all()
    )


def _overlap_room_nights(o: Order, d0: date, d1: date) -> int:
    if not o.check_in or not o.check_out:
        return 0
    start = max(o.check_in, d0)
    end = min(o.check_out - timedelta(days=1), d1)
    if end < start:
        return 0
    days = (end - start).days + 1
    return days * max(1, int(o.rooms or 1))


def _sum_orders_rev(db: Session, hotel_id: int, d0: date, d1: date) -> float:
    return _money(sum(float(o.total_amount or 0) for o in _orders_in_period(db, hotel_id, d0, d1)))


def _sum_orders_other(db: Session, hotel_id: int, d0: date, d1: date) -> float:
    return _money(sum(float(o.other_amount or 0) for o in _orders_in_period(db, hotel_id, d0, d1)))


def _sum_night_audit_rev(db: Session, hotel_id: int, d0: date, d1: date) -> float:
    val = (
        db.query(func.coalesce(func.sum(NightAuditLog.revenue), 0))
        .filter(NightAuditLog.hotel_id == hotel_id, NightAuditLog.biz_date >= d0, NightAuditLog.biz_date <= d1)
        .scalar()
    )
    return _money(val)


def _sum_night_audit_nights(db: Session, hotel_id: int, d0: date, d1: date) -> int:
    val = (
        db.query(func.coalesce(func.sum(NightAuditLog.room_nights), 0))
        .filter(NightAuditLog.hotel_id == hotel_id, NightAuditLog.biz_date >= d0, NightAuditLog.biz_date <= d1)
        .scalar()
    )
    return int(val or 0)


def period_revenue(db: Session, hotel_id: int, d0: date, d1: date) -> dict[str, Any]:
    """营收口径：夜审合计 → 订单合计 → 收款合计；绝不造假。"""
    audit = _sum_night_audit_rev(db, hotel_id, d0, d1)
    if audit > 0:
        return {"amount": audit, "source": "night_audit"}
    orders = _sum_orders_rev(db, hotel_id, d0, d1)
    if orders > 0:
        return {"amount": orders, "source": "orders"}
    pays = _sum_payments(db, hotel_id, d0, d1)
    if pays > 0:
        return {"amount": pays, "source": "payments"}
    return {"amount": 0.0, "source": "empty"}


def _room_count(db: Session, hotel_id: int) -> int:
    return db.query(Room).filter_by(hotel_id=hotel_id).count()


def _order_nights(orders: list[Order]) -> int:
    total = 0
    for o in orders:
        if not o.check_in or not o.check_out:
            continue
        days = max(1, (o.check_out - o.check_in).days)
        total += days * int(o.rooms or 1)
    return total


def _order_room_amount(o: Order) -> float:
    """单笔客房收入 = 订单总额 − 非房 other_amount（餐饮/会议等）。"""
    return max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))


def _order_other_amount(o: Order) -> float:
    return max(0.0, float(o.other_amount or 0))


def _sum_orders_room_rev(orders: list[Order]) -> float:
    return _money(sum(_order_room_amount(o) for o in orders))


def _sum_orders_other_rev(orders: list[Order]) -> float:
    return _money(sum(_order_other_amount(o) for o in orders))


def period_room_revenue(db: Session, hotel_id: int, d0: date, d1: date) -> dict[str, Any]:
    """客房收入口径（用于 ADR/RevPAR）：按与期间重叠的间夜分摊房费。

    分子 = Σ (总额 − other_amount) × (重叠间夜 / 整单间夜)；绝不把 payments 或 other 算进 ADR。
    """
    orders = _orders_overlapping(db, hotel_id, d0, d1)
    room = 0.0
    other = 0.0
    nights = 0
    for o in orders:
        n = _overlap_room_nights(o, d0, d1)
        if n <= 0:
            continue
        stay = max(1, (o.check_out - o.check_in).days) * max(1, int(o.rooms or 1))
        frac = n / stay
        room += _order_room_amount(o) * frac
        other += _order_other_amount(o) * frac
        nights += n
    room = _money(room)
    other = _money(other)
    if room > 0 or other > 0 or nights > 0:
        return {
            "amount": room,
            "other": other,
            "nights": nights,
            "source": "orders",
        }
    audit_n = _sum_night_audit_nights(db, hotel_id, d0, d1)
    audit_r = _sum_night_audit_rev(db, hotel_id, d0, d1)
    if audit_n > 0 and audit_r > 0:
        # 夜审表未拆非房：仅作无订单时的客房代理，调用方应在备注中说明
        return {
            "amount": audit_r,
            "other": 0.0,
            "nights": audit_n,
            "source": "night_audit_proxy",
        }
    return {"amount": 0.0, "other": 0.0, "nights": 0, "source": "empty"}


def period_ops_kpis(db: Session, hotel_id: int, d0: date, d1: date) -> dict[str, Any]:
    """营运 KPI：ADR/OCC/RevPAR 一律基于客房收入与已售间夜（同源，保证 RevPAR≈ADR×OCC）。"""
    rooms_n = max(0, _room_count(db, hotel_id))
    days = max(1, (d1 - d0).days + 1)
    capacity = max(1, rooms_n * days) if rooms_n else 0
    rr = period_room_revenue(db, hotel_id, d0, d1)
    room_rev = float(rr["amount"] or 0)
    sold = int(rr["nights"] or 0)
    adr = _money(room_rev / sold) if sold > 0 and room_rev > 0 else 0.0
    # 不强制封顶 100%：日用房/超售时 OCC 可>100%，才能与 RevPAR≈ADR×OCC 对齐
    occ_pct = _pct(sold / capacity * 100) if capacity and sold > 0 else 0.0
    revpar = _money(room_rev / capacity) if capacity and room_rev > 0 else 0.0
    return {
        "room_revenue": _money(room_rev),
        "other_revenue": _money(rr.get("other") or 0),
        "sold_nights": sold,
        "rooms": rooms_n,
        "days": days,
        "capacity": capacity,
        "occ_pct": occ_pct,
        "adr": adr,
        "revpar": revpar,
        "source": rr.get("source") or "empty",
    }


def _tax_rate(db: Session, hotel_id: int) -> float:
    row = (
        db.query(FinanceTaxConfig)
        .filter_by(hotel_id=hotel_id, status="active")
        .order_by(FinanceTaxConfig.id.desc())
        .first()
    )
    if row and row.main_rate is not None:
        return float(row.main_rate)
    from finance.tax.registry import get_tax_provider

    return float(get_tax_provider().tax_rate)


def build_kpis(
    db: Session, hotel_id: int, d0: date, d1: date, compare: str = "yoy", period: str = "month"
) -> list[dict]:
    from infra.i18n import t

    cur = period_revenue(db, hotel_id, d0, d1)
    rev = cur["amount"]

    cmp = _compare_range(d0, d1, compare)
    prev_rev = 0.0
    cmp_label = t("同比")
    if cmp:
        p0, p1, cmp_label = cmp
        prev_rev = period_revenue(db, hotel_id, p0, p1)["amount"]
    d_rev = _delta_pct(rev, prev_rev, cmp_label) if cmp and prev_rev > 0 else {"label": "—", "tone": "flat"}

    period_label = {
        "today": t("今日"),
        "week": t("本周"),
        "month": t("本月"),
        "year": t("本年"),
        "custom": t("本期"),
    }.get((period or "month").lower(), t("本期"))

    # AR：真实单据余额 / 0-30 账龄
    try:
        from finance.ar_ap_service import list_workspace

        ws = list_workspace(db, hotel_id)
        ar_amt = float(ws.get("aging", {}).get("d0_30") or 0) or float(ws.get("kpi", {}).get("ar_balance") or 0)
        ar_week = float(ws.get("kpi", {}).get("ar_week_receipts") or 0)
    except Exception:
        ar_amt = 0.0
        ar_week = 0.0

    if compare == "none":
        ar_delta = {"label": "—", "tone": "flat"}
    elif ar_week > 0:
        ar_delta = {"label": t("近 7 日回款 ¥{amt}", amt=f"{ar_week:,.0f}"), "tone": "flat"}
    else:
        ar_delta = {"label": "—", "tone": "flat"}

    # 异常线索：仅 ProfitInsight
    insights = (
        db.query(ProfitInsight)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(ProfitInsight.id.desc())
        .limit(5)
        .all()
    )
    insight_amt = _money(sum(float(i.impact_amount or 0) for i in insights))
    clues = [t(str(i.title)) for i in insights if i.title]
    if insights:
        clue_text = " · ".join(clues[:3]) if clues else t("{n} 条待处理", n=len(insights))
        anomaly_delta = {"label": f"📌 {clue_text}", "tone": "ai"}
    else:
        clue_text = ""
        anomaly_delta = {"label": t("暂无开放线索"), "tone": "flat"}

    return [
        {
            "key": "revenue",
            "label": t("{period}营收", period=period_label),
            "value": rev,
            "value_fmt": f"¥{rev:,.0f}",
            "delta": d_rev["label"],
            "tone": d_rev["tone"],
            "ai": False,
            "source": cur["source"],
        },
        {
            "key": "gop",
            "label": t("{period} GOP（毛利）", period=period_label),
            "value": 0,
            "value_fmt": "—",
            "delta": t("成本科目未接入，无法计算"),
            "tone": "flat",
            "ai": False,
        },
        {
            "key": "ar",
            "label": t("应收余额（账龄 0-30）"),
            "value": ar_amt,
            "value_fmt": f"¥{ar_amt:,.0f}",
            "delta": ar_delta["label"],
            "tone": ar_delta["tone"],
            "ai": False,
        },
        {
            "key": "anomaly",
            "label": t("{period}异常线索", period=period_label),
            "value": insight_amt,
            "value_fmt": f"¥{insight_amt:,.0f}" if insights else "—",
            "delta": anomaly_delta["label"],
            "tone": anomaly_delta["tone"],
            "ai": bool(insights),
        },
    ]
