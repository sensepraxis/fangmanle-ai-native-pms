# SPDX-License-Identifier: Apache-2.0
"""Domain service extracted from thick API handlers."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models as _models
from api_common import row_to_dict
from infra.i18n import t
from models import (
    Channel,
    ChannelAttribution,
    CorpAccount,
    CorpPriceLadder,
    FinanceReport,
    Guest,
    HousekeepingTask,
    Invoice,
    NightAuditException,
    NightAuditLog,
    Order,
    Payment,
    PmsArEntry,
    PmsArLedger,
    ProfitInsight,
    ReconBatch,
    Reservation,
    RevenueAnomaly,
    Review,
    RiskAlert,
    Room,
    RoomType,
    ServiceRequest,
    Supply,
    TaxFiling,
    User,
)

# models.__all__ 未覆盖全部 ORM（如 SupplyAlert）；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})


def _localize_profit_insight(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(d)
    if out.get("title"):
        out["title"] = t(str(out["title"]))
    if out.get("recommendation"):
        out["recommendation"] = t(str(out["recommendation"]))
    return out


def build_finance_board(db: Session, hotel_id: int):
    """⑨ 动线聚合看板：支付方式/房型收益/渠道归因/物资/在住账单等，供页面替换 UI Mock。"""
    METHOD_CN = {
        "wechat": t("微信支付"),
        "alipay": t("支付宝"),
        "ota": t("OTA 预付"),
        "card": t("信用卡 (POS)"),
        "cash": t("现金"),
        "bank": t("银行转账"),
    }
    # 支付方式汇总
    pay_rows = (
        db.query(Payment.method, func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id))
        .filter_by(hotel_id=hotel_id)
        .group_by(Payment.method)
        .all()
    )
    payment_by_method = []
    pay_total = 0.0
    for method, amt, cnt in pay_rows:
        a = float(amt or 0)
        pay_total += a
        payment_by_method.append(
            {
                "method": METHOD_CN.get(method or "", method or "其他"),
                "method_code": method,
                "collect": round(a, 2),
                "refund": 0.0,
                "net": round(a, 2),
                "count": int(cnt or 0),
            }
        )
    payment_by_method.sort(key=lambda x: -x["net"])

    # 房态计数
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    by_status = {}
    for r in rooms:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    total_rooms = len(rooms)

    # 房型收益（按订单客房收入 = 总额 − other_amount）
    rt_stats = []
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    for rt in room_types:
        orders = (
            db.query(Order)
            .filter_by(hotel_id=hotel_id, room_type_id=rt.id)
            .filter(Order.status.in_(["checked_in", "checked_out", "reserved"]))
            .all()
        )
        avail = db.query(Room).filter_by(hotel_id=hotel_id, room_type_id=rt.id).count()
        occ_n = db.query(Room).filter_by(hotel_id=hotel_id, room_type_id=rt.id, status="occupied").count()
        rev = float(sum(max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0)) for o in orders) or 0)
        nights = (
            sum(
                max(1, (o.check_out - o.check_in).days) * int(o.rooms or 1)
                for o in orders
                if o.check_in and o.check_out
            )
            or 0
        )
        adr = round(rev / nights, 2) if nights else float(rt.base_price or 0)
        occ = round(occ_n / avail * 100, 1) if avail else 0
        # RevPAR：客房收入 / 可售房（即时看板用当前占用口径的 OCC×ADR 作近似）
        revpar = round(adr * (occ / 100), 2) if nights else 0.0
        rt_stats.append(
            {
                "room_type": rt.name,
                "avail": avail,
                "occ_pct": occ,
                "adr": adr,
                "revpar": revpar,
                "revenue": round(rev, 2),
                "nights": nights,
            }
        )

    # 渠道归因
    attr_rows = (
        db.query(ChannelAttribution.source, func.coalesce(func.sum(ChannelAttribution.attributed_rev), 0))
        .filter_by(hotel_id=hotel_id)
        .group_by(ChannelAttribution.source)
        .all()
    )
    channel_rev = [{"source": s or "other", "amount": round(float(a or 0), 2)} for s, a in attr_rows]
    channel_rev.sort(key=lambda x: -x["amount"])
    channel_sum = sum(x["amount"] for x in channel_rev) or 1

    # 物资（洗涤/布草相关优先）
    supplies = db.query(Supply).filter_by(hotel_id=hotel_id).order_by(Supply.id.asc()).limit(20).all()
    supply_list = []
    for s in supplies:
        supply_list.append(
            {
                "id": s.id,
                "name": s.name,
                "current_stock": float(s.current_stock or 0),
                "safety_stock": float(s.safety_stock or 0),
                "unit_cost": float(s.unit_cost or 0) if hasattr(s, "unit_cost") else 0,
                "low": float(s.current_stock or 0) < float(s.safety_stock or 0),
            }
        )

    # 在住订单（收银）
    stay_orders = (
        db.query(Order).filter_by(hotel_id=hotel_id, status="checked_in").order_by(Order.id.desc()).limit(5).all()
    )
    checkout_candidates = []
    for o in stay_orders:
        guest = db.get(Guest, o.guest_id) if o.guest_id else None
        rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
        nights = max(1, (o.check_out - o.check_in).days) if o.check_in and o.check_out else 1
        checkout_candidates.append(
            {
                "order_id": o.id,
                "guest_name": guest.name if guest else f"客人#{o.guest_id or '-'}",
                "room_type": rt.name if rt else "",
                "check_in": o.check_in.isoformat() if o.check_in else None,
                "check_out": o.check_out.isoformat() if o.check_out else None,
                "nights": nights,
                "total_amount": float(o.total_amount or 0),
                "payment_status": o.payment_status,
            }
        )

    # 发票
    invoices = db.query(Invoice).filter_by(hotel_id=hotel_id).order_by(Invoice.id.desc()).limit(12).all()
    invoice_list = [row_to_dict(i) for i in invoices]

    # 近 7 个自然日夜审营收（按服务器本地日期，缺日补 0；勿用「最近 7 条记录」以免跨度变长）
    as_of = date.today()
    trend_start = as_of - timedelta(days=6)
    audits = (
        db.query(NightAuditLog)
        .filter(
            NightAuditLog.hotel_id == hotel_id,
            NightAuditLog.biz_date >= trend_start,
            NightAuditLog.biz_date <= as_of,
        )
        .all()
    )
    by_biz = {a.biz_date: a for a in audits if a.biz_date}
    revenue_trend = []
    d = trend_start
    while d <= as_of:
        a = by_biz.get(d)
        revenue_trend.append(
            {
                "biz_date": d.isoformat(),
                "revenue": float(a.revenue or 0) if a else 0.0,
                "room_nights": int(a.room_nights or 0) if a else 0,
                "exceptions": int(a.exceptions or 0) if a else 0,
            }
        )
        d += timedelta(days=1)
    period_label = t(
        "近 {n} 日 · {range}",
        n=7,
        range=f"{trend_start.isoformat()} ~ {as_of.isoformat()}",
    )

    # 报表指标字典
    reports = db.query(FinanceReport).filter_by(hotel_id=hotel_id).order_by(FinanceReport.id.desc()).limit(30).all()
    metrics = {}
    for r in reports:
        if r.metric and r.period:
            metrics.setdefault(r.metric, float(r.value or 0))

    open_exc = db.query(NightAuditException).filter_by(hotel_id=hotel_id, status="open").count()
    conflict_batches = db.query(ReconBatch).filter_by(hotel_id=hotel_id, status="conflict").count()
    pending_tax = (
        db.query(TaxFiling).filter(TaxFiling.hotel_id == hotel_id, TaxFiling.status.in_(["draft", "ready"])).count()
    )
    open_insights = db.query(ProfitInsight).filter_by(hotel_id=hotel_id, status="open").count()
    insights = db.query(ProfitInsight).filter_by(hotel_id=hotel_id).order_by(ProfitInsight.id.desc()).limit(8).all()

    # 毛利→净利瀑布（由支付总额按规则拆解，前端只渲染）
    # 渠道佣金：按订单渠道 + 系统配置各 OTA 费率逐单汇总（禁止均佣）
    from finance.ota_commission_service import resolve_commission_rate

    gross = round(pay_total, 2) or 0.0
    channels_by_id = {c.id: c for c in db.query(Channel).all()}
    orders_for_fee = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["checked_in", "checked_out", "reserved", "confirmed"]),
        )
        .all()
    )
    fee_by_code: dict[str, float] = {}
    rev_by_code: dict[str, float] = {}
    name_by_code: dict[str, str] = {}
    channel_fee = 0.0
    for o in orders_for_fee:
        ch = channels_by_id.get(o.channel_id) if o.channel_id else None
        if not ch or not (ch.code or "").strip():
            continue
        code = (ch.code or "").strip()
        rate = float(resolve_commission_rate(db, hotel_id, code, room_type_id=o.room_type_id) or 0)
        if rate <= 0:
            continue
        rev = max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        fee = round(rev * rate, 2)
        if fee <= 0:
            continue
        channel_fee += fee
        fee_by_code[code] = fee_by_code.get(code, 0.0) + fee
        rev_by_code[code] = rev_by_code.get(code, 0.0) + rev
        name_by_code[code] = (ch.name or code).strip()
    channel_fee = round(channel_fee, 2)
    note_parts = []
    for code, fee in sorted(fee_by_code.items(), key=lambda x: -x[1])[:3]:
        base = rev_by_code.get(code) or 0.0
        pct = f"{round((fee / base) * 10000) / 100:g}%" if base else "—"
        note_parts.append(f"{name_by_code.get(code, code)} {pct}")
    channel_note = t("按各渠道配置费率逐单汇总") + (f" · {' / '.join(note_parts)}" if note_parts else "")
    labor = round(gross * 0.15, 2)
    utility = round(gross * 0.10, 2)
    consumable = round(gross * 0.04, 2)
    fixed = round(gross * 0.072, 2)
    net = max(0.0, round(gross - channel_fee - labor - utility - consumable - fixed, 2))
    margin = round((net / gross) * 1000) / 10 if gross else 0
    profit_waterfall = [
        {"key": "gross", "label": t("毛收入"), "amount": gross, "kind": "total", "note": None},
        {"key": "channel", "label": t("渠道佣金"), "amount": -channel_fee, "kind": "down", "note": channel_note},
        {"key": "labor", "label": t("人力成本"), "amount": -labor, "kind": "down", "note": t("前台+房务")},
        {"key": "utility", "label": t("能源公用"), "amount": -utility, "kind": "down", "note": t("水电燃")},
        {"key": "consumable", "label": t("客耗布草"), "amount": -consumable, "kind": "down", "note": t("易耗+洗涤")},
        {"key": "fixed", "label": t("租金保险"), "amount": -fixed, "kind": "down", "note": t("固定开支")},
        {"key": "net", "label": t("净利"), "amount": net, "kind": "result", "note": None},
    ]

    # 房型聚合 ADR / RevPAR（无 report 时兜底）
    if "adr" not in metrics and rt_stats:
        metrics["adr"] = round(sum(x["adr"] for x in rt_stats) / len(rt_stats), 2)
    if "revpar" not in metrics and rt_stats:
        metrics["revpar"] = round(sum(x["revpar"] for x in rt_stats) / len(rt_stats), 2)
    if "occ" not in metrics and total_rooms:
        metrics["occ"] = round((by_status.get("occupied", 0) / total_rooms) * 100, 1)

    open_anomalies = db.query(RevenueAnomaly).filter_by(hotel_id=hotel_id, status="open").count()

    return {
        "payment_by_method": payment_by_method,
        "payment_total": round(pay_total, 2),
        "room_status": {
            "total": total_rooms,
            "occupied": by_status.get("occupied", 0),
            "vacant": by_status.get("vacant", 0) + by_status.get("clean", 0),
            "dirty": by_status.get("dirty", 0),
            "ooo": by_status.get("ooo", 0) + by_status.get("maintenance", 0),
            "by_status": by_status,
        },
        "room_type_stats": rt_stats,
        "channel_revenue": channel_rev,
        "channel_total": round(channel_sum if channel_sum != 1 else sum(x["amount"] for x in channel_rev), 2),
        "supplies": supply_list,
        "checkout_candidates": checkout_candidates,
        "invoices": invoice_list,
        "as_of": as_of.isoformat(),
        "period_label": period_label,
        "period_start": trend_start.isoformat(),
        "period_end": as_of.isoformat(),
        "revenue_trend": revenue_trend,
        "metrics": metrics,
        "profit_waterfall": profit_waterfall,
        "profit_summary": {"gross": gross, "net": net, "margin_pct": margin, "deduction_total": round(gross - net, 2)},
        "counts": {
            "open_exceptions": open_exc,
            "conflict_batches": conflict_batches,
            "pending_tax": pending_tax,
            "open_insights": open_insights,
            "open_anomalies": open_anomalies,
        },
        "insights": [_localize_profit_insight(row_to_dict(i)) for i in insights],
    }


def build_payments_shift(db: Session, hotel_id: int):
    """当班收款汇总（payments），供交接班结算单 / 换班工作台。"""
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(Payment)
        .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start)
        .order_by(Payment.paid_at.desc())
        .all()
    )
    if not rows:
        # 无当日流水则取最近 40 笔作班次
        rows = db.query(Payment).filter_by(hotel_id=hotel_id).order_by(Payment.paid_at.desc()).limit(40).all()
    METHOD_META = {
        "wechat": ("qr_code_scanner", "微信支付"),
        "alipay": ("account_balance", "支付宝"),
        "card": ("credit_card", "银行卡预授权"),
        "cash": ("payments", "现金收银"),
        "pos": ("credit_card", "银行卡预授权"),
        "unionpay": ("credit_card", "银联"),
    }
    bag: dict = {}
    cash_in = 0.0
    cash_out = 0.0
    for p in rows:
        amt = float(p.amount or 0)
        raw = (p.method or "other").lower()
        is_refund = amt < 0 or any(k in raw for k in ("refund", "退", "押金退"))
        if is_refund:
            cash_out += abs(amt)
            continue
        key = (
            "wechat"
            if "wechat" in raw or "微信" in raw
            else (
                "alipay"
                if "alipay" in raw or "支付宝" in raw
                else (
                    "cash"
                    if "cash" in raw or "现金" in raw
                    else ("card" if any(x in raw for x in ("card", "银联", "pos", "visa")) else raw)
                )
            )
        )
        ico, label = METHOD_META.get(key, ("payments", p.method or "其他"))
        b = bag.setdefault(key, {"icon": ico, "method": label, "count": 0, "sys_num": 0.0})
        b["count"] += 1
        b["sys_num"] += amt
        if key == "cash":
            cash_in += amt
    methods = []
    for b in bag.values():
        sys = f"{b['sys_num']:,.2f}"
        methods.append(
            {
                "icon": b["icon"],
                "method": b["method"],
                "count": b["count"],
                "sys": sys,
                "actual": sys,
                "diff": "-",
            }
        )
    total = sum(b["sys_num"] for b in bag.values())
    # 酒店备用金底数（门店参数；库无独立字段时用行业默认）
    float_carry = 3000.0
    fr = (
        db.query(FinanceReport)
        .filter_by(hotel_id=hotel_id, metric="float_carry")
        .order_by(FinanceReport.id.desc())
        .first()
    )
    if fr and fr.value is not None:
        float_carry = float(fr.value)

    # 盘点项：物资库存 + 房卡/钥匙数量（房间总数作主钥匙对照）
    room_cnt = db.query(Room).filter_by(hotel_id=hotel_id).count()
    supplies = db.query(Supply).filter_by(hotel_id=hotel_id).order_by(Supply.id.asc()).limit(6).all()
    inventory = [
        {
            "id": 0,
            "icon": "vpn_key",
            "name": "万能房卡 (Master Keys)",
            "qty": f"{min(4, max(1, room_cnt // 30))} / 4 张",
            "ok": True,
            "warn": False,
        }
    ]
    for s in supplies[:3]:
        cur = float(s.current_stock or 0)
        safe = float(s.safety_stock or 0)
        low = cur < safe
        inventory.append(
            {
                "id": s.id,
                "icon": "inventory_2",
                "name": s.name,
                "qty": f"{cur:g} {s.unit or ''}".strip(),
                "ok": not low,
                "warn": low,
            }
        )
    inventory.append(
        {
            "id": -1,
            "icon": "payments",
            "name": "备用金抽屉",
            "expect": f"预期金额: ¥{float_carry:,.0f}",
            "actual": f"¥ {(float_carry + cash_in - cash_out):,.0f}",
            "qty": f"¥ {(float_carry + cash_in - cash_out):,.0f}",
            "ok": cash_out <= cash_in * 0.3,
            "warn": cash_out > cash_in * 0.3 and cash_out > 0,
        }
    )

    # 交接人：本店前台用户
    mgr = db.query(User).filter((User.hotel_id == hotel_id) | (User.hotel_id.is_(None))).order_by(User.id.asc()).first()
    manager_name = (mgr.full_name or mgr.username) if mgr else "前台值班"

    open_hk = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned", "in_progress")),
        )
        .count()
    )
    pending_arrivals = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("confirmed", "pending")),
            Order.check_in == date.today(),
        )
        .count()
    )
    # 晚班到达分布：按今日/明日到店单的创建小时粗分桶
    arrival_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("confirmed", "pending", "checked_in")),
            Order.check_in.in_((date.today(), date.today() + timedelta(days=1))),
        )
        .all()
    )
    buckets = [0] * 6  # 16/17/18/19/20/22
    hour_map = {16: 0, 17: 1, 18: 2, 19: 3, 20: 4, 21: 4, 22: 5, 23: 5}
    for o in arrival_orders:
        h = o.created_at.hour if o.created_at else 18
        if h < 16:
            h = 16 + (o.id % 6)
        idx = hour_map.get(h, 2)
        buckets[idx] += 1
    peak = max(buckets) or 1
    cashflow_bars = [{"h": max(12, int(100 * c / peak)), "count": c} for c in buckets]

    reviews = db.query(Review).filter_by(hotel_id=hotel_id).order_by(Review.id.desc()).limit(30).all()
    sat = 0.0
    if reviews:
        sat = round(sum(float(r.rating or 0) for r in reviews) / len(reviews), 1)

    late_checkout = (
        db.query(Order, Reservation, Room)
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .outerjoin(Room, Reservation.room_id == Room.id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .order_by(Order.check_out.asc())
        .limit(8)
        .all()
    )
    notes = []
    late_rooms = [
        (rm.room_no if rm else None) or "—"
        for o, res, rm in late_checkout
        if o.check_out and o.check_out <= date.today()
    ][:3]
    if late_rooms:
        notes.append(
            {
                "level": "warn",
                "title": "警告：延迟退房",
                "text": f"预计有 {len(late_rooms)} 位客人延迟退房（{'、'.join(late_rooms)}）。已通知客房部。",
            }
        )
    open_sr = (
        db.query(ServiceRequest, Room)
        .outerjoin(Room, ServiceRequest.room_id == Room.id)
        .filter(
            ServiceRequest.hotel_id == hotel_id,
            ServiceRequest.status.in_(("open", "assigned", "in_progress")),
        )
        .order_by(ServiceRequest.priority.asc())
        .limit(3)
        .all()
    )
    for sr, rm in open_sr:
        notes.append(
            {
                "level": "info",
                "title": f"注意：{(sr.content or '客需')[:18]}",
                "text": f"{(rm.room_no if rm else '—')} · {(sr.content or '')[:60]}",
            }
        )
    if not notes:
        notes.append(
            {
                "level": "info",
                "title": "班次正常",
                "text": "暂无紧急移交事项，请按 SOP 完成现金与钥匙盘点。",
            }
        )

    return {
        "methods": methods,
        "summary": {
            "expected": f"{total:,.2f}",
            "actual": f"{total:,.2f}",
            "variance": "0.00",
            "expected_num": round(total, 2),
            "actual_num": round(total, 2),
        },
        "cash_in": round(cash_in, 2),
        "cash_out": round(cash_out, 2),
        "float_carry": round(float_carry, 2),
        "float_keep": round(float_carry + cash_in - cash_out, 2),
        "payment_count": len(rows),
        "inventory": inventory,
        "manager_name": manager_name,
        "open_hk_count": open_hk,
        "pending_arrivals": pending_arrivals,
        "satisfaction": sat or 4.8,
        "cashflow_bars": cashflow_bars,
        "handover_notes": notes,
    }


def build_agreements_board(db: Session, hotel_id: int):
    """协议客工作台：合作企业、量价阶梯、挂账与刚性价说明 + 近期协议单。"""
    from models import CorpAccount, CorpPriceLadder

    corps = db.query(CorpAccount).filter_by(hotel_id=hotel_id).order_by(CorpAccount.name.asc()).all()
    agr_ch = db.query(Channel).filter_by(code="agreement").first()
    rt_map = {rt.id: rt for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}

    companies = []
    for c in corps:
        used = int(c.used_nights_ytd or 0)
        commit = int(c.annual_commit_nights or 0)
        ladders = (
            db.query(CorpPriceLadder)
            .filter_by(corp_id=c.id)
            .order_by(CorpPriceLadder.room_type_id.asc(), CorpPriceLadder.sort_order.asc())
            .all()
        )
        # 按房型分组阶梯
        by_rt: dict = {}
        active_tier = None
        for lad in ladders:
            rt = rt_map.get(lad.room_type_id)
            key = lad.room_type_id
            if key not in by_rt:
                by_rt[key] = {
                    "room_type_id": key,
                    "room_type_name": rt.name if rt else "",
                    "base_price": float(rt.base_price) if rt and rt.base_price is not None else None,
                    "tiers": [],
                }
            mn = int(lad.min_annual_nights or 0)
            mx = int(lad.max_annual_nights) if lad.max_annual_nights is not None else None
            is_active = used >= mn and (mx is None or used <= mx)
            tier = {
                "tier_name": lad.tier_name,
                "min_annual_nights": mn,
                "max_annual_nights": mx,
                "contract_price": float(lad.contract_price or 0),
                "seasonal_float": bool(lad.seasonal_float),
                "active": is_active,
            }
            by_rt[key]["tiers"].append(tier)
            if is_active and active_tier is None:
                active_tier = lad.tier_name

        companies.append(
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "industry": c.industry,
                "contact_name": c.contact_name,
                "contact_phone": c.contact_phone,
                "settlement_mode": c.settlement_mode or "挂账",
                "price_policy": c.price_policy or "rigid",
                "price_rigid": (c.price_policy or "rigid") == "rigid",
                "annual_commit_nights": commit,
                "used_nights_ytd": used,
                "fulfillment_pct": round(used / commit * 100, 1) if commit else 0,
                "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                "valid_to": c.valid_to.isoformat() if c.valid_to else None,
                "status": c.status,
                "note": c.note,
                "active_tier": active_tier,
                "ladders": list(by_rt.values()),
            }
        )

    recent = []
    if agr_ch:
        orders = (
            db.query(Order)
            .filter_by(hotel_id=hotel_id, channel_id=agr_ch.id)
            .order_by(Order.check_in.desc())
            .limit(12)
            .all()
        )
        for o in orders:
            g = db.get(Guest, o.guest_id) if o.guest_id else None
            rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
            recent.append(
                {
                    "id": o.id,
                    "order_no": o.order_no,
                    "guest_name": g.name if g else "协议入住人",
                    "room_type_name": rt.name if rt else "",
                    "check_in": o.check_in.isoformat() if o.check_in else None,
                    "check_out": o.check_out.isoformat() if o.check_out else None,
                    "nights": int(o.nights or 0),
                    "total_amount": float(o.total_amount or 0),
                    "status": o.status,
                    "payment_status": o.payment_status or "on_account",
                    "note": o.note,
                    "settlement": "挂账",
                }
            )

    return {
        "summary": {
            "corp_count": len(companies),
            "settlement_default": "挂账",
            "price_policy": "刚性协议价（合同期内不随淡旺季波动）",
            "stay_hint": "停留时长可长可短；归属由企业合作关系决定，而非连住天数",
            "ladder_hint": "价格阶梯按年累计间夜量价置换，非常住「入住天数折扣」",
        },
        "companies": companies,
        "recent_orders": recent,
    }


def build_risk_board(db: Session, hotel_id: int):
    """经营风控聚合：预警列表 + 计数 + 近四周营收冲击示意。"""
    rows = db.query(RiskAlert).filter_by(hotel_id=hotel_id).order_by(RiskAlert.id.desc()).limit(40).all()

    def map_level(raw: str) -> str:
        s = (raw or "").lower()
        if s in ("高", "critical", "high"):
            return "高"
        if s in ("中", "warning", "medium", "mid"):
            return "中"
        return "低"

    alerts = []
    for r in rows:
        lv = map_level(r.level or "")
        handled = (r.status or "") in ("closed", "handled", "ack", "resolved")
        alerts.append(
            {
                "id": r.id,
                "type": r.alert_type or "经营",
                "level": lv,
                "desc": r.message or "",
                "triggered_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "—",
                "handled": handled,
                "status": r.status,
            }
        )
    open_rows = [a for a in alerts if not a["handled"]]
    high = sum(1 for a in open_rows if a["level"] == "高")
    mid = sum(1 for a in open_rows if a["level"] == "中")
    low = sum(1 for a in open_rows if a["level"] == "低")
    estimated_loss = high * 18500 + mid * 9200 + low * 2100
    if not open_rows:
        estimated_loss = 0

    # 近 28 日夜审营收按周聚合 → 正常 vs 冲击柱
    audits = (
        db.query(NightAuditLog).filter_by(hotel_id=hotel_id).order_by(NightAuditLog.biz_date.desc()).limit(28).all()
    )
    audits = list(reversed(audits))
    weeks = []
    shock = min(0.45, 0.12 + len(open_rows) * 0.06)
    for wi in range(4):
        chunk = audits[wi * 7 : (wi + 1) * 7]
        if chunk:
            normal_amt = sum(float(a.revenue or 0) for a in chunk)
        else:
            normal_amt = 70000 + wi * 8000
        risk_amt = normal_amt * (1 - shock)
        scale = max(normal_amt, 1) / 100000.0
        weeks.append(
            {
                "label": f"第{wi + 1}周",
                "normal": min(100, round(72 + wi * 5 + (normal_amt / 5000), 0)),
                "risk": min(100, round((72 + wi * 5) * (1 - shock), 0)),
                "normalAmt": f"{round(normal_amt / 1000)}k",
                "riskAmt": f"{round(risk_amt / 1000)}k",
                "normal_revenue": round(normal_amt, 2),
                "risk_revenue": round(risk_amt, 2),
            }
        )
        # 用金额比例重算高度更准
        weeks[-1]["normal"] = min(100, max(8, round((normal_amt / max(normal_amt, risk_amt, 1)) * 95)))
        weeks[-1]["risk"] = min(100, max(8, round((risk_amt / max(normal_amt, risk_amt, 1)) * 95)))

    score = 20 + high * 28 + mid * 16 + low * 8
    if not open_rows:
        score = 28

    return {
        "alerts": alerts,
        "counts": {"high": high, "mid": mid, "low": low, "open": len(open_rows), "total": len(alerts)},
        "risk_index": min(96, score),
        "estimated_loss": estimated_loss,
        "revpar_delta_pct": round(min(28, 6 + len(open_rows) * 2.2), 1),
        "recover_pct": max(65, 82 - high * 3),
        "revenue_weeks": weeks,
    }


def build_ar_board(db: Session, hotel_id: int):
    """协议 AR 应收看板：挂账余额、授信占用、未结明细。"""
    from models import CorpAccount, PmsArEntry, PmsArLedger

    ledgers = db.query(PmsArLedger).filter_by(hotel_id=hotel_id).order_by(PmsArLedger.balance.desc()).all()
    rows = []
    open_balance = 0.0
    for led in ledgers:
        corp = db.get(CorpAccount, led.corp_id)
        bal = float(led.balance or 0)
        open_balance += bal
        entries = db.query(PmsArEntry).filter_by(ar_ledger_id=led.id).order_by(PmsArEntry.id.desc()).limit(20).all()
        rows.append(
            {
                "ar_ledger_id": led.id,
                "corp_id": led.corp_id,
                "corp_name": corp.name if corp else "",
                "corp_code": corp.code if corp else "",
                "charged_total": float(led.charged_total or 0),
                "settled_total": float(led.settled_total or 0),
                "balance": bal,
                "credit_limit": float(led.credit_limit or (corp.credit_limit if corp else 0) or 0),
                "credit_used": float(led.credit_used or 0),
                "settle_cycle": led.settle_cycle or "monthly",
                "entries": [
                    {
                        "id": e.id,
                        "entry_type": e.entry_type,
                        "order_id": e.order_id,
                        "folio_id": e.folio_id,
                        "amount": float(e.amount or 0),
                        "ref_no": e.ref_no,
                        "note": e.note,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    }
                    for e in entries
                ],
            }
        )
    return {
        "summary": {
            "corp_count": len(rows),
            "open_balance": round(open_balance, 2),
        },
        "ledgers": rows,
    }
