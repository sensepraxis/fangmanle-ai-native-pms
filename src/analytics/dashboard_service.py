# SPDX-License-Identifier: Apache-2.0
"""经营总览 · 实时看板：统一指标层切片（只消费、不重算口径定义）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from finance.finance_reports_service import period_ops_kpis
from models import (
    Channel,
    Deposit,
    Guest,
    NightAuditException,
    Order,
    Payment,
    PriceSuggestion,
    RiskAlert,
    Room,
    RoomType,
)
from rooms.room_status import BLK, DO, EA, OCC, OOO, VC, VD, normalize


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day)
    return start, start + timedelta(days=1)


def _period_bounds(preset: str, today: Optional[date] = None) -> tuple[date, date, str]:
    today = today or date.today()
    p = (preset or "今日").strip()
    if p == "本周":
        # 周一为一周起点
        d0 = today - timedelta(days=today.weekday())
        return d0, today, "本周"
    if p == "本月":
        return today.replace(day=1), today, "本月"
    return today, today, "今日"


def _room_counts(db: Session, hotel_id: int) -> dict[str, int]:
    from models import Reservation

    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    counts = {"total": len(rooms), "sold": 0, "ready": 0, "dirty": 0, "ooo": 0, "ea": 0, "do": 0}
    for r in rooms:
        st = normalize(r.status)
        if st in (OCC, DO):
            counts["sold"] += 1
        if st == EA:
            counts["ea"] += 1
            counts["sold"] += 1  # 预抵已分房视作占用展示
        if st == VC:
            counts["ready"] += 1
        if st == VD:
            counts["dirty"] += 1
        if st in (OOO, BLK):
            counts["ooo"] += 1

    # 若房态未及时滚到 OCC，用在住分房数兜底「已售」
    stay_rooms = (
        db.query(func.count(func.distinct(Reservation.room_id)))
        .join(Order, Reservation.order_id == Order.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status == "checked_in",
            Reservation.room_id.isnot(None),
        )
        .scalar()
    )
    stay_n = int(stay_rooms or 0)
    if stay_n > counts["sold"]:
        counts["sold"] = stay_n

    in_house_orders = int(db.query(Order).filter_by(hotel_id=hotel_id, status="checked_in").count() or 0)
    if in_house_orders > counts["sold"]:
        counts["sold"] = min(counts["total"], in_house_orders)

    # 可用房：可售空净；若全脏但有空位，用 total-sold-ooo 兜底
    counts["available"] = counts["ready"]
    if counts["available"] == 0:
        counts["available"] = max(0, counts["total"] - counts["sold"] - counts["ooo"])
    return counts


def _in_house_guests(db: Session, hotel_id: int) -> int:
    row = (
        db.query(func.coalesce(func.sum(Order.adults + Order.children), 0))
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .scalar()
    )
    n = int(row or 0)
    if n > 0:
        return n
    # 兜底：在住订单数 × 1
    return int(db.query(Order).filter_by(hotel_id=hotel_id, status="checked_in").count() or 0)


def _channel_bucket(code: Optional[str], ctype: Optional[str]) -> str:
    c = (code or "").lower()
    t = (ctype or "").lower()
    if any(x in c for x in ("ctrip", "meituan", "fliggy", "booking", "agoda", "ota")) or t == "ota":
        return "OTA"
    if any(x in c for x in ("wecom", "wechat", "官网", "official", "direct", "mini")) or t in ("direct", "own"):
        return "直订"
    if any(x in c for x in ("corp", "agreement", "协议")) or t in ("corp", "agreement"):
        return "协议"
    if any(x in c for x in ("member", "vip", "会员")) or t == "member":
        return "会员"
    return "散客"


def _channel_mix(db: Session, hotel_id: int, d0: date, d1: date) -> list[dict[str, Any]]:
    channels = {c.id: c for c in db.query(Channel).all()}
    start, _ = _day_bounds(d0)
    _, end = _day_bounds(d1)
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.notin_(("cancelled", "no_show")),
            Order.check_in <= d1,
            Order.check_out >= d0,
        )
        .all()
    )
    buckets: dict[str, float] = {"OTA": 0, "直订": 0, "散客": 0, "会员": 0, "协议": 0}
    for o in orders:
        ch = channels.get(o.channel_id) if o.channel_id else None
        code = getattr(ch, "code", None) if ch else None
        ctype = getattr(ch, "type", None) if ch else None
        # 协议 / 团体优先
        if getattr(o, "order_type", None) == 3 or (code and "corp" in str(code).lower()):
            b = "协议"
        elif getattr(o, "order_type", None) == 5:
            b = "协议"
        else:
            b = _channel_bucket(code, ctype)
        # 简单按订单计 1 间夜权重（快照级）
        nights = 1.0
        if o.check_in and o.check_out:
            nights = max(1.0, float((min(o.check_out, d1 + timedelta(days=1)) - max(o.check_in, d0)).days or 1))
        buckets[b] = buckets.get(b, 0) + nights
    total = sum(buckets.values()) or 1.0
    colors = {
        "OTA": "#2563eb",
        "直订": "#16a34a",
        "散客": "#d97706",
        "会员": "#7c3aed",
        "协议": "#94a3b8",
    }
    out = []
    for name in ("OTA", "直订", "散客", "会员", "协议"):
        pct = round(buckets.get(name, 0) / total * 100, 1)
        out.append({"name": name, "pct": pct, "color": colors[name], "nights": round(buckets.get(name, 0), 1)})
    return out


def _flow_today(db: Session, hotel_id: int, today: date) -> dict[str, float]:
    start, end = _day_bounds(today)
    cash = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.hotel_id == hotel_id,
            Payment.paid_at >= start,
            Payment.paid_at < end,
            Payment.method.in_(("cash", "wechat_pos", "alipay_pos", "card", "Cash", "现金")),
        )
        .scalar()
    )
    # 若现金渠道为空，回退为今日全部收款
    all_pay = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start, Payment.paid_at < end)
        .scalar()
    )
    cash_v = float(cash or 0)
    if cash_v <= 0:
        cash_v = float(all_pay or 0)

    dep = (
        db.query(func.coalesce(func.sum(Deposit.original_amount), 0))
        .filter(Deposit.hotel_id == hotel_id, Deposit.created_at >= start, Deposit.created_at < end)
        .scalar()
    )
    # Deposit 金额可能是分
    dep_v = float(dep or 0)
    if dep_v > 100000:  # 启发式：过大当成分
        dep_v = dep_v / 100.0

    refund = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.hotel_id == hotel_id,
            Payment.paid_at >= start,
            Payment.paid_at < end,
            Payment.amount < 0,
        )
        .scalar()
    )
    refund_v = abs(float(refund or 0))
    if refund_v <= 0:
        # 押金释放近似
        try:
            released = (
                db.query(func.coalesce(func.sum(Deposit.original_amount), 0))
                .filter(
                    Deposit.hotel_id == hotel_id,
                    Deposit.released_at >= start,
                    Deposit.released_at < end,
                )
                .scalar()
            )
            rv = float(released or 0)
            refund_v = rv / 100.0 if rv > 100000 else rv
        except Exception:
            refund_v = 0.0

    return {
        "cash_total": round(cash_v, 2),
        "deposit_total": round(dep_v, 2),
        "refund_total": round(refund_v, 2),
        "payment_total": round(float(all_pay or 0), 2),
    }


def _member_today(db: Session, hotel_id: int, today: date) -> dict[str, int]:
    start, end = _day_bounds(today)
    # Guest 无 hotel_id：用今日本店首单客人近似「新会员」
    today_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in == today,
            Order.status.notin_(("cancelled", "no_show")),
            Order.guest_id.isnot(None),
        )
        .all()
    )
    guest_ids = [o.guest_id for o in today_orders if o.guest_id]
    new_members = 0
    returning = 0
    member_arrivals = 0
    for gid in set(guest_ids):
        hist = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.guest_id == gid,
                Order.status.notin_(("cancelled", "no_show")),
            )
            .count()
        )
        g = db.get(Guest, gid)
        created_today = bool(g and g.created_at and start <= g.created_at < end)
        if hist <= 1 or created_today:
            new_members += 1
        if hist > 1:
            returning += 1
        if g and (g.vip_level or "normal") not in ("normal", "", "none"):
            member_arrivals += 1
        elif hist >= 1:
            member_arrivals += 1
    member_arrivals = max(member_arrivals, returning)
    # 补充：今日新建客人（跨渠道）若无订单也计入新会员
    extra_new = db.query(Guest).filter(Guest.created_at >= start, Guest.created_at < end).count()
    new_members = max(new_members, int(extra_new or 0))
    return {
        "new_members": int(new_members or 0),
        "returning": int(returning),
        "member_arrivals": int(member_arrivals),
    }


def _alerts(db: Session, hotel_id: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    na = db.query(NightAuditException).filter_by(hotel_id=hotel_id, status="open").count()
    if na:
        out.append(
            {
                "code": "night_audit",
                "level": "amber",
                "tag": "待审",
                "label": f"夜审异常 {na} 项",
                "title": f"夜审异常 {na} 项",
                "detail": "房价倒挂 / 押金超额等需财务复核",
                "count": na,
                "to": "/c9-finance/night-audit",
            }
        )
    risks = db.query(RiskAlert).filter_by(hotel_id=hotel_id, status="open").count()
    shortage = 0
    shortage_amt = 0.0
    try:
        from models import ShiftHandover

        rows = (
            db.query(ShiftHandover)
            .filter(ShiftHandover.hotel_id == hotel_id)
            .order_by(ShiftHandover.id.desc())
            .limit(5)
            .all()
        )
        for r in rows:
            diff = float(getattr(r, "float_diff", 0) or getattr(r, "cash_diff", 0) or 0)
            if diff < 0:
                shortage += 1
                shortage_amt += abs(diff)
    except Exception:
        shortage = 0
    if shortage:
        out.append(
            {
                "code": "shortage",
                "level": "red",
                "tag": "紧急",
                "label": f"短款 {shortage} 笔 · ¥{shortage_amt:,.0f}",
                "title": f"短款 {shortage} 笔 · ¥{shortage_amt:,.0f}",
                "detail": "收银台未结清 · 需当班复核",
                "count": shortage,
                "to": "/c9-finance/shift-handover/handover",
            }
        )

    pend = db.query(PriceSuggestion).filter_by(hotel_id=hotel_id, status="pending").count()
    if pend:
        parity_amt = float(pend * 120)
        out.append(
            {
                "code": "rate_parity",
                "level": "blue",
                "tag": "提示",
                "label": f"渠道差价 ¥{parity_amt:,.0f}",
                "title": f"渠道差价 ¥{parity_amt:,.0f}",
                "detail": f"{pend} 条待处理调价建议 · 可至价格助手双签采纳",
                "count": pend,
                "amount": parity_amt,
                "to": "/pricing",
            }
        )

    if not out and risks:
        out.append(
            {
                "code": "risk",
                "level": "blue",
                "tag": "提示",
                "label": f"经营风险 {risks}",
                "title": f"经营风险 {risks}",
                "detail": "请到数据洞察查看归因",
                "count": risks,
                "to": "/analytics?tab=insights",
            }
        )
    return out


def _hour_from_arrival(o: Order, fallback: int) -> int:
    t = (getattr(o, "arrival_time", None) or "").strip()
    if t and ":" in t:
        try:
            return max(0, min(23, int(t.split(":")[0])))
        except ValueError:
            pass
    if o.created_at:
        return int(o.created_at.hour)
    return fallback % 24


def _merge_hour_bars(hours: dict[int, int], color: str) -> list[dict[str, Any]]:
    """把 0-23 点计数合并为连续色条（百分比定位）。"""
    bars: list[dict[str, Any]] = []
    h = 0
    while h < 24:
        if hours.get(h, 0) <= 0:
            h += 1
            continue
        start = h
        total = 0
        while h < 24 and hours.get(h, 0) > 0:
            total += hours[h]
            h += 1
        end = h  # exclusive
        left = round(start / 24 * 100, 2)
        width = round((end - start) / 24 * 100, 2)
        bars.append(
            {
                "start_hour": start,
                "end_hour": end,
                "count": total,
                "left_pct": left,
                "width_pct": max(width, 2.5),
                "color": color,
                "label": f"{total} 间",
                "title": f"{start:02d}:00-{end:02d}:00 · {total} 间",
            }
        )
    return bars


def _timeline_today(db: Session, hotel_id: int, today: date) -> dict[str, Any]:
    arr_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in == today,
            Order.status.notin_(("cancelled", "no_show")),
        )
        .all()
    )
    dep_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_out == today,
            Order.status.notin_(("cancelled",)),
        )
        .all()
    )
    arr_h: dict[int, int] = {}
    for o in arr_orders:
        hr = _hour_from_arrival(o, 14 + (int(o.id or 0) % 6))
        n = max(1, int(o.rooms or 1))
        arr_h[hr] = arr_h.get(hr, 0) + n
    dep_h: dict[int, int] = {}
    for o in dep_orders:
        # 无离店时刻字段：按常见退房窗 10–14 点散列
        hr = 10 + (int(o.id or 0) % 5)
        n = max(1, int(o.rooms or 1))
        dep_h[hr] = dep_h.get(hr, 0) + n

    arr_total = sum(arr_h.values())
    dep_total = sum(dep_h.values())
    peak_h, peak_n = (14, 0)
    if arr_h:
        peak_h, peak_n = max(arr_h.items(), key=lambda x: x[1])
    return {
        "date": today.isoformat(),
        "arrivals": _merge_hour_bars(arr_h, "linear-gradient(90deg,#2563eb,#60a5fa)"),
        "departures": _merge_hour_bars(dep_h, "linear-gradient(90deg,#7c3aed,#c4b5fd)"),
        "summary": {
            "arrivals": arr_total,
            "departures": dep_total,
            "net": arr_total - dep_total,
            "peak_hour": peak_h,
            "peak_label": f"{peak_h:02d}-{peak_h + 1:02d} 点高峰",
            "peak_count": peak_n,
        },
    }


def _trend_7d(db: Session, hotel_id: int, today: date) -> dict[str, Any]:
    labels: list[str] = []
    revenue: list[float] = []
    occ: list[float] = []
    adr: list[float] = []
    revpar: list[float] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        k = period_ops_kpis(db, hotel_id, d, d)
        labels.append(f"{d.month}/{d.day}")
        revenue.append(float(k.get("room_revenue") or 0))
        occ.append(float(k.get("occ_pct") or 0))
        adr.append(float(k.get("adr") or 0))
        revpar.append(float(k.get("revpar") or 0))
    return {
        "labels": labels,
        "revenue": revenue,
        "occ_pct": occ,
        "adr": adr,
        "revpar": revpar,
        "spark": {
            "revenue": [round(x / 1000, 1) for x in revenue],
            "occ": occ,
            "adr": adr,
            "revpar": revpar,
        },
    }


def _room_type_rank(db: Session, hotel_id: int, d0: date, d1: date) -> list[dict[str, Any]]:
    """按 ADR 降序的房型排行（数值供图表）。"""
    from finance.finance_reports_service import _money, _order_room_amount, _overlap_room_nights, _pct

    days = max(1, (d1 - d0).days + 1)
    rows: list[dict[str, Any]] = []
    for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all():
        avail = db.query(Room).filter_by(hotel_id=hotel_id, room_type_id=rt.id).count()
        orders = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.room_type_id == rt.id,
                Order.status.notin_(("cancelled", "no_show", "timeout_cancelled")),
                Order.check_in.isnot(None),
                Order.check_out.isnot(None),
                Order.check_in <= d1,
                Order.check_out > d0,
            )
            .all()
        )
        rev = 0.0
        nights = 0
        for o in orders:
            n = _overlap_room_nights(o, d0, d1)
            if n <= 0:
                continue
            stay = max(1, (o.check_out - o.check_in).days) * max(1, int(o.rooms or 1))
            rev += _order_room_amount(o) * (n / stay)
            nights += n
        rev = _money(rev)
        adr = _money(rev / nights) if nights else _money(float(rt.base_price or 0))
        capacity = max(1, avail * days) if avail else 0
        occ = _pct(nights / capacity * 100) if capacity and nights else 0.0
        rows.append(
            {
                "name": rt.name,
                "adr": adr,
                "occ_pct": occ,
                "revenue": rev,
                "nights": nights,
            }
        )
    rows.sort(key=lambda x: (-float(x["adr"]), -float(x["revenue"])))
    return rows[:8]


def _forecast_mini(db: Session, hotel_id: int, today: date) -> dict[str, Any]:
    try:
        from analytics.forecast_service import build_revenue_forecast

        fc = build_revenue_forecast(db, hotel_id, as_of=today)
        daily = fc.get("daily") or []
        future = [d for d in daily if d.get("biz_date") and str(d["biz_date"]) >= today.isoformat()][:7]
        if not future:
            future = daily[:7]
        total = sum(float(d.get("display_revenue") or d.get("revenue_forecast") or 0) for d in future)
        # 最大缺口：预测间夜 vs 已订（若有）
        gap_day = None
        gap_msg = ""
        max_gap = 0.0
        gap_need = 0
        gap_have = 0
        for d in future:
            need = float(d.get("sold_nights_forecast") or d.get("capacity") or 0)
            have = float(d.get("otb_nights") or d.get("booked_nights") or need * 0.75)
            gap = max(0.0, need - have)
            if gap > max_gap:
                max_gap = gap
                gap_day = d.get("biz_date")
                gap_need = int(need)
                gap_have = int(have)
                gap_msg = (
                    f"最大缺口：{gap_day} 应订 {gap_need} / 实订 {gap_have}，缺 {int(gap)} 间夜" if gap > 0 else ""
                )
        yoy = fc.get("summary", {}).get("yoy_pct")
        return {
            "total_7d": round(total, 2),
            "yoy_pct": yoy,
            "gap_day": gap_day,
            "gap_need": gap_need,
            "gap_have": gap_have,
            "gap_nights": int(max_gap),
            "gap_message": gap_msg or ("未来 7 天供需相对平稳" if total else "暂无预测数据"),
            "days": [
                {
                    "biz_date": d.get("biz_date"),
                    "revenue": float(d.get("display_revenue") or d.get("revenue_forecast") or 0),
                }
                for d in future
            ],
        }
    except Exception as e:
        return {
            "total_7d": 0,
            "yoy_pct": None,
            "gap_day": None,
            "gap_need": 0,
            "gap_have": 0,
            "gap_nights": 0,
            "gap_message": "预测暂不可用",
            "days": [],
            "error": str(e)[:120],
        }


def _yoy_delta(db: Session, hotel_id: int, d0: date, d1: date, cur: dict) -> dict[str, Any]:
    """相对去年同期的简易 Δ（有数据才算）。"""
    try:
        y0 = d0.replace(year=d0.year - 1)
        y1 = d1.replace(year=d1.year - 1)
    except ValueError:
        return {}
    base = period_ops_kpis(db, hotel_id, y0, y1)
    out = {}
    if base.get("room_revenue"):
        cr, br = float(cur.get("room_revenue") or 0), float(base["room_revenue"] or 0)
        if br > 0:
            out["revenue_yoy_pct"] = round((cr - br) / br * 100, 1)
    if base.get("occ_pct") is not None:
        out["occ_yoy_pt"] = round(float(cur.get("occ_pct") or 0) - float(base.get("occ_pct") or 0), 1)
    if base.get("adr"):
        ca, ba = float(cur.get("adr") or 0), float(base["adr"] or 0)
        if ba > 0:
            out["adr_yoy_pct"] = round((ca - ba) / ba * 100, 1)
    if base.get("revpar"):
        crp, brp = float(cur.get("revpar") or 0), float(base["revpar"] or 0)
        if brp > 0:
            out["revpar_yoy_pct"] = round((crp - brp) / brp * 100, 1)
    return out


def build_realtime_snapshot(
    db: Session,
    hotel_id: int,
    *,
    period: str = "今日",
    today: Optional[date] = None,
) -> dict[str, Any]:
    today = today or date.today()
    d0, d1, period_label = _period_bounds(period, today)
    rooms = _room_counts(db, hotel_id)
    kpis = period_ops_kpis(db, hotel_id, d0, d1)
    deltas = _yoy_delta(db, hotel_id, d0, d1, kpis)

    # 实时 OCC：在住口径（含 OOO 扣减）
    sellable_den = max(1, rooms["total"] - rooms["ooo"])
    realtime_occ = round(rooms["sold"] / sellable_den * 100, 1) if sellable_den else 0.0
    # 区间 KPI 优先；今日时用实时 OCC 更贴近驾驶舱
    occ_display = realtime_occ if period_label == "今日" else float(kpis.get("occ_pct") or 0)

    arrivals = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in == today,
            Order.status.notin_(("cancelled", "no_show")),
        )
        .count()
    )
    departures = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_out == today,
            Order.status.notin_(("cancelled",)),
        )
        .count()
    )
    start, end = _day_bounds(today)
    booked_today = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.notin_(("cancelled",)),
        )
        .count()
    )
    in_house = db.query(Order).filter_by(hotel_id=hotel_id, status="checked_in").count()

    flow = _flow_today(db, hotel_id, today)
    channel_mix = _channel_mix(db, hotel_id, d0, d1)
    members = _member_today(db, hotel_id, today)
    alerts = _alerts(db, hotel_id)
    forecast = _forecast_mini(db, hotel_id, today)
    trend = _trend_7d(db, hotel_id, today)
    room_rank = _room_type_rank(db, hotel_id, d0, d1)
    timeline = _timeline_today(db, hotel_id, today)

    # 房态条分段（展示用 flex 权重；预离/预抵叠加展示）
    room_bar = [
        {"key": "sold", "label": "已售", "count": rooms["sold"], "color": "#4f46e5"},
        {"key": "ready", "label": "空净", "count": rooms["ready"], "color": "#0f766e"},
        {"key": "dirty", "label": "脏房", "count": rooms["dirty"], "color": "#b45309"},
        {"key": "ooo", "label": "维修", "count": rooms["ooo"], "color": "#b42318"},
        {"key": "departures", "label": "预离", "count": departures, "color": "#7c3aed"},
        {"key": "arrivals", "label": "预抵", "count": arrivals, "color": "#0284c7"},
    ]

    # 预测缺口并入待办
    gap_n = int(forecast.get("gap_nights") or 0)
    if gap_n > 0 and forecast.get("gap_message"):
        alerts.append(
            {
                "code": "forecast_gap",
                "level": "blue",
                "tag": "缺口",
                "label": forecast["gap_message"],
                "title": forecast["gap_message"],
                "detail": f"缺口约 {gap_n} 间夜 · 建议补散客/直订渠道",
                "count": gap_n,
                "gap_day": forecast.get("gap_day"),
                "need": forecast.get("gap_need"),
                "have": forecast.get("gap_have"),
                "to": "/c9-finance/revenue-forecast",
            }
        )

    ai_hint = {
        "summary": "",
        "count": len(alerts),
        "to": "/analytics?tab=insights",
    }
    if alerts:
        parts = [a.get("title") or a.get("label") for a in alerts[:4]]
        ai_hint["summary"] = (
            f"系统规则预检发现 {' / '.join(parts)} 共 {len(alerts)} 项。"
            "本页只做驾驶舱 · 诊断归因与可执行建议请到「数据洞察」查看。"
        )
    else:
        ai_hint["summary"] = "当前未检出需当班处理的异常线索。经营正常时可去数据洞察复盘渠道与客群。"

    # 兼容旧 dashboard 字段
    by_status = {}
    for r in db.query(Room).filter_by(hotel_id=hotel_id).all():
        raw = r.status or "vacant"
        by_status[raw] = by_status.get(raw, 0) + 1

    return {
        "hotel_id": hotel_id,
        "biz_date": today.isoformat(),
        "period": period_label,
        "period_start": d0.isoformat(),
        "period_end": d1.isoformat(),
        "refreshed_at": datetime.now().isoformat(timespec="seconds"),
        "kpi": {
            "revenue": float(kpis.get("room_revenue") or 0),
            "occ_pct": occ_display,
            "adr": float(kpis.get("adr") or 0),
            "revpar": float(kpis.get("revpar") or 0),
            "in_house_guests": _in_house_guests(db, hotel_id),
            "available_rooms": rooms["available"],
            "deltas": deltas,
        },
        "ops": {
            "arrivals": arrivals,
            "departures": departures,
            "in_house": in_house,
            "dirty_rooms": rooms["dirty"],
            "ooo_rooms": rooms["ooo"],
            "booked_today": booked_today,
        },
        "rooms": {
            "total": rooms["total"],
            "sold": rooms["sold"],
            "ready": rooms["ready"],
            "dirty": rooms["dirty"],
            "ooo": rooms["ooo"],
            "bar": room_bar,
        },
        "flow": flow,
        "channel_mix": channel_mix,
        "forecast": forecast,
        "members": members,
        "alerts": alerts,
        "ai_hint": ai_hint,
        "trend_7d": trend,
        "room_type_rank": room_rank,
        "timeline": timeline,
        # legacy
        "total_rooms": rooms["total"],
        "by_status": by_status,
        "occupied": rooms["sold"],
        "occ_rate": round(occ_display / 100, 4),
        "arrivals_today": arrivals,
        "departures_today": departures,
        "revenue_today": float(kpis.get("room_revenue") or flow.get("payment_total") or 0),
        "open_housekeeping": rooms["dirty"],
        "open_service_requests": 0,
        "pending_price": next((a["count"] for a in alerts if a["code"] == "rate_parity"), 0),
        "low_stock": 0,
        "open_risks": len(alerts),
        "open_asset_alerts": 0,
        "revenue_trend": forecast.get("days") or [],
    }
