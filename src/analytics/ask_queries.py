# SPDX-License-Identifier: Apache-2.0
"""AI 问数 · 确定性查询（开发者 SQL/聚合，模型永不写 SQL）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from analytics.ask_catalog import PERIOD_LABELS
from analytics.ask_snapshot import _channel_bucket, _mix_from_orders, _nights_in_window, _segment_bucket
from finance.finance_reports_service import period_ops_kpis, resolve_period
from models import Channel, Order, Review

DIRECT_CODES = {"direct", "official", "wecom", "wechat", "mini", "官网", "企微"}


def _pct_text(rate: float) -> str:
    pct = round(float(rate or 0) * 100, 2)
    return f"{pct:.2f}".rstrip("0").rstrip(".")


def _channel_commission_rate(db: Session, ch: Channel | None) -> float:
    if not ch:
        return 0.0
    try:
        from finance.ota_commission_service import rate_for_channel

        return float(rate_for_channel(db, ch) or 0)
    except Exception:
        return float(ch.commission_rate or 0)


def resolve_ask_period(
    period_label: str,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[date, date, str, str]:
    """返回 d0,d1,label,period_key。支持本周/本月/本季/自定义。"""
    raw = (period_label or "本月").strip()
    key_map = {
        "本周": "week",
        "本月": "month",
        "本季": "quarter",
        "自定义": "custom",
        "week": "week",
        "month": "month",
        "quarter": "quarter",
        "custom": "custom",
    }
    key = key_map.get(raw, "month")
    today = date.today()
    if key == "week":
        d0, d1, lab = resolve_period("week")
    elif key == "quarter":
        q = (today.month - 1) // 3
        d0 = date(today.year, q * 3 + 1, 1)
        d1 = today
        lab = f"{d0.isoformat()} ~ {d1.isoformat()}"
    elif key == "custom":
        d0, d1, lab = resolve_period("custom", start=start, end=end)
    else:
        d0, d1, lab = resolve_period("month")
    return d0, d1, lab, key


def _compare_range(d0: date, d1: date, baseline: str) -> tuple[date, date]:
    days = (d1 - d0).days + 1
    if (baseline or "同比").strip() in ("环比", "mom"):
        c1 = d0 - timedelta(days=1)
        c0 = c1 - timedelta(days=days - 1)
        return c0, c1
    try:
        return date(d0.year - 1, d0.month, d0.day), date(d1.year - 1, d1.month, d1.day)
    except ValueError:
        return d0 - timedelta(days=365), d1 - timedelta(days=365)


def _row(label: str, value: Any, note: str = "", tone: str = "neutral") -> dict:
    from infra.i18n import t

    return {"label": t(str(label)), "value": value, "note": t(str(note)) if note else "", "tone": tone}


def _pack(title: str, unit: str, rows: list[dict], metrics: dict | None = None, empty: bool = False) -> dict:
    from infra.i18n import t

    unit_disp = t(str(unit)) if unit else unit
    # 未走 _row 的行（客人明细等）补一层 label/note 翻译
    out_rows: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            out_rows.append(r)
            continue
        rr = dict(r)
        if rr.get("label") is not None:
            rr["label"] = t(str(rr["label"]))
        if rr.get("note"):
            rr["note"] = t(str(rr["note"]))
        out_rows.append(rr)
    return {
        "title": t(str(title)),
        "unit": unit_disp,
        "columns": [t("维度"), t("数值({unit})", unit=unit_disp), t("说明")],
        "rows": out_rows,
        "metrics": metrics or {},
        "empty": empty or not out_rows,
    }


def _orders_window(db: Session, hotel_id: int, d0: date, d1: date) -> list[Order]:
    return (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= d1,
            Order.check_out > d0,
            Order.status.in_(["reserved", "confirmed", "checked_in", "checked_out", "pending"]),
        )
        .all()
    )


def q_channel_profit_loss(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    from infra.i18n import t as _t

    channels = {c.id: c for c in db.query(Channel).all()}
    buckets: dict[str, dict[str, float]] = {}
    for o in _orders_window(db, hotel_id, d0, d1):
        n = _nights_in_window(o, d0, d1)
        if n <= 0:
            continue
        stay = max(1, (o.check_out - o.check_in).days)
        room = max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        rev = room * (n / stay)
        ch = channels.get(o.channel_id)
        name = (ch.name if ch else None) or _t("未标注")
        code = ch.code if ch else None
        ctype = ch.type if ch else None
        bucket = _channel_bucket(code, ctype)
        # 按渠道读 OTA 佣金配置（不再写死 12%）
        try:
            from finance.ota_commission_service import resolve_commission_rate

            if ch and ch.code:
                commission = float(
                    resolve_commission_rate(
                        db,
                        hotel_id,
                        ch.code,
                        room_type_id=o.room_type_id,
                        on_date=o.check_in,
                    )
                    or 0
                )
            else:
                commission = 0.0
        except Exception:
            commission = _channel_commission_rate(db, ch) if bucket == "ota" else 0.0
            if bucket != "ota":
                commission = 0.0
        # 直销桶强制 0；OTA/其他按配置
        if bucket in ("direct", "wechat", "offline"):
            commission = 0.0
        net = rev * (1 - commission)
        row = buckets.setdefault(
            name,
            {"rev": 0.0, "net": 0.0, "nights": 0.0, "bucket": bucket, "rate": commission},
        )
        row["rev"] += rev
        row["net"] += net
        row["nights"] += n
        row["rate"] = commission
    rows = []
    for name, v in sorted(buckets.items(), key=lambda x: x[1]["net"]):
        net = round(v["net"], 0)
        rev = round(v["rev"], 0)
        rate = float(v.get("rate") or 0)
        pct = _pct_text(rate)
        if rate > 0:
            note = _t(
                "净收益 = ¥{rev} × (1 - {name}佣金 {pct}%)",
                rev=f"{rev:,.0f}",
                name=name,
                pct=pct,
            )
        else:
            note = _t("净收益为负") if net < 0 else (_t("零佣/直订") if v["bucket"] != "ota" else _t("健康"))
        if net < 0 and rate > 0:
            note = _t("净收益为负 · {note}", note=note)
        elif net < 0:
            note = _t("净收益为负")
        tone = "neg" if net < 0 else "pos"
        rows.append(_row(name, int(net), note, tone))
    losing = [r for r in rows if isinstance(r["value"], (int, float)) and r["value"] < 0]
    return _pack(
        _t("各渠道净收益（{d0}~{d1}）", d0=d0, d1=d1),
        "元",
        rows,
        {"losing_count": len(losing), "losing": [r["label"] for r in losing]},
        empty=not rows,
    )


def q_ota_share_ratio(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    ch, _ = _mix_from_orders(db, hotel_id, d0, d1)
    ota = float(ch.get("ota_pct") or 0) * 100
    direct = float(ch.get("direct_pct") or 0) * 100
    corp = float(ch.get("corp_pct") or 0) * 100
    mem = float(ch.get("member_pct") or 0) * 100
    warn = ota >= 55
    rows = [
        _row("OTA 合计", round(ota, 1), ">55% 阈值，偏高" if warn else "未超警戒线", "warn" if warn else "pos"),
        _row("直订", round(direct, 1), "直订健康" if direct >= 20 else "直订偏弱", "pos" if direct >= 20 else "warn"),
        _row("协议/企业", round(corp, 1), "待拓展" if corp < 15 else "尚可"),
        _row("会员", round(mem, 1), "偏低" if mem < 10 else "尚可", "warn" if mem < 10 else "neutral"),
    ]
    return _pack("渠道间夜占比", "%", rows, {"ota_pct": round(ota, 1), "threshold": 55, "over": warn})


def q_direct_book_rate(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "同比", **_) -> dict:
    from infra.i18n import t as _t

    ch, _ = _mix_from_orders(db, hotel_id, d0, d1)
    cur = float(ch.get("direct_pct") or 0) * 100
    c0, c1 = _compare_range(d0, d1, baseline)
    ch_b, _ = _mix_from_orders(db, hotel_id, c0, c1)
    base = float(ch_b.get("direct_pct") or 0) * 100
    delta = round(cur - base, 1)
    rows = [
        _row("本期直订占比", round(cur, 1), "官网/企微/直销口径"),
        _row(_t("对比期（{baseline}）", baseline=_t(str(baseline or "同比"))), round(base, 1), f"{c0}~{c1}"),
        _row("变化", delta, "百分点", "pos" if delta >= 0 else "neg"),
    ]
    return _pack("直订率", "%", rows, {"direct_pct": round(cur, 1), "delta_pt": delta})


def q_business_churn(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "同比", **_) -> dict:
    _, seg = _mix_from_orders(db, hotel_id, d0, d1)
    cur = float(seg.get("business_pct") or 0) * 100
    c0, c1 = _compare_range(d0, d1, baseline)
    _, seg_b = _mix_from_orders(db, hotel_id, c0, c1)
    base = float(seg_b.get("business_pct") or 0) * 100
    delta = round(cur - base, 1)
    from infra.i18n import t as _t

    churn = delta < -3
    rows = [
        _row("本期商务客占比", round(cur, 1), "间夜口径"),
        _row(_t("对比期（{baseline}）", baseline=_t(str(baseline or "同比"))), round(base, 1), f"{c0}~{c1}"),
        _row("变化", delta, "百分点", "neg" if churn else "pos"),
    ]
    return _pack("商务客占比", "%", rows, {"business_pct": round(cur, 1), "delta_pt": delta, "churn": churn})


def q_member_repurchase(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    # 复购代理：会员渠道/客群间夜占比 vs 上期（环比）
    _, seg = _mix_from_orders(db, hotel_id, d0, d1)
    ch, _ = _mix_from_orders(db, hotel_id, d0, d1)
    cur = max(float(seg.get("member_pct") or 0), float(ch.get("member_pct") or 0)) * 100
    c0, c1 = _compare_range(d0, d1, "环比")
    _, seg_b = _mix_from_orders(db, hotel_id, c0, c1)
    ch_b, _ = _mix_from_orders(db, hotel_id, c0, c1)
    base = max(float(seg_b.get("member_pct") or 0), float(ch_b.get("member_pct") or 0)) * 100
    delta = round(cur - base, 1)
    worse = delta < -3
    rows = [
        _row("本期会员占比（复购代理）", round(cur, 1), "会员客群/渠道间夜"),
        _row("上期（环比）", round(base, 1), f"{c0}~{c1}"),
        _row("变化", delta, "百分点", "neg" if worse else "pos"),
    ]
    return _pack("会员复购代理", "%", rows, {"member_pct": round(cur, 1), "delta_pt": delta, "worse": worse})


def q_segment_mix(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    _, seg = _mix_from_orders(db, hotel_id, d0, d1)
    labels = {"leisure_pct": "休闲客", "business_pct": "商务客", "group_pct": "团队", "member_pct": "会员"}
    rows = [_row(lab, round(float(seg.get(k) or 0) * 100, 1), "间夜占比") for k, lab in labels.items()]
    return _pack("客群结构", "%", rows, {k: round(float(seg.get(k) or 0) * 100, 1) for k in labels})


def q_revpar_trend(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "同比", **_) -> dict:
    from infra.i18n import t as _t

    cur = period_ops_kpis(db, hotel_id, d0, d1)
    c0, c1 = _compare_range(d0, d1, baseline)
    base = period_ops_kpis(db, hotel_id, c0, c1)

    def delta(a, b):
        if not b:
            return None
        return round((a - b) / abs(b) * 100, 1) if b else None

    rows = [
        _row("OCC", f"{cur['occ_pct']}%", _t("对比期 {v}%", v=base["occ_pct"])),
        _row("ADR", cur["adr"], _t("对比期 ¥{v}", v=base["adr"]), "neutral"),
        _row("RevPAR", cur["revpar"], _t("对比期 ¥{v}", v=base["revpar"]), "neutral"),
        _row("客房收入", cur["room_revenue"], "总额−other_amount"),
    ]
    d_rp = delta(cur["revpar"], base["revpar"])
    if d_rp is not None:
        rows.append(_row("RevPAR 涨跌", f"{d_rp}%", _t(str(baseline or "同比")), "pos" if d_rp >= 0 else "neg"))
    return _pack(
        "营收 KPI",
        "元",
        rows,
        {"adr": cur["adr"], "occ_pct": cur["occ_pct"], "revpar": cur["revpar"], "revpar_delta_pct": d_rp},
    )


def _kpi_compare_pack(
    title: str,
    metric_key: str,
    unit: str,
    cur: dict,
    base: dict,
    baseline: str,
    *,
    as_pct: bool = False,
) -> dict:
    cv = float(cur.get(metric_key) or 0)
    bv = float(base.get(metric_key) or 0)
    delta_pt = round(cv - bv, 1)
    delta_pct = round((cv - bv) / abs(bv) * 100, 1) if bv else None
    from infra.i18n import t as _t

    tone = "pos" if delta_pt >= 0 else "neg"
    baseline_lab = _t(str(baseline or "同比"))
    if as_pct:
        rows = [
            _row("本期", f"{cv}%", ""),
            _row("对比期", f"{bv}%", baseline_lab),
            _row("变化", f"{delta_pt} pt", baseline_lab, tone),
        ]
        if delta_pct is not None:
            rows.append(_row("相对变化", f"{delta_pct}%", baseline_lab, tone))
        metrics = {
            metric_key: cv,
            f"{metric_key}_base": bv,
            "delta_pt": delta_pt,
            "delta_pct": delta_pct,
            "baseline": baseline,
            "improved": delta_pt >= 0,
        }
    else:
        rows = [
            _row("本期", cv, "元" if unit == "元" else unit),
            _row("对比期", bv, baseline_lab),
            _row("变化", delta_pt if unit != "元" else round(cv - bv, 2), baseline_lab, tone),
        ]
        if delta_pct is not None:
            rows.append(_row("相对变化", f"{delta_pct}%", baseline_lab, tone))
        metrics = {
            metric_key: cv,
            f"{metric_key}_base": bv,
            "delta": round(cv - bv, 2),
            "delta_pct": delta_pct,
            "baseline": baseline,
            "improved": (cv - bv) >= 0,
        }
    return _pack(title, unit, rows, metrics)


def q_occupancy_kpi(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "环比", **_) -> dict:
    cur = period_ops_kpis(db, hotel_id, d0, d1)
    c0, c1 = _compare_range(d0, d1, baseline)
    base = period_ops_kpis(db, hotel_id, c0, c1)
    return _kpi_compare_pack("入住率对比", "occ_pct", "%", cur, base, baseline, as_pct=True)


def q_adr_kpi(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "同比", **_) -> dict:
    cur = period_ops_kpis(db, hotel_id, d0, d1)
    c0, c1 = _compare_range(d0, d1, baseline)
    base = period_ops_kpis(db, hotel_id, c0, c1)
    return _kpi_compare_pack("ADR 对比", "adr", "元", cur, base, baseline, as_pct=False)


def q_revpar_kpi(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "同比", **_) -> dict:
    cur = period_ops_kpis(db, hotel_id, d0, d1)
    c0, c1 = _compare_range(d0, d1, baseline)
    base = period_ops_kpis(db, hotel_id, c0, c1)
    return _kpi_compare_pack("RevPAR 对比", "revpar", "元", cur, base, baseline, as_pct=False)


def q_room_revenue_kpi(db: Session, hotel_id: int, d0: date, d1: date, baseline: str = "环比", **_) -> dict:
    cur = period_ops_kpis(db, hotel_id, d0, d1)
    c0, c1 = _compare_range(d0, d1, baseline)
    base = period_ops_kpis(db, hotel_id, c0, c1)
    return _kpi_compare_pack("客房收入对比", "room_revenue", "元", cur, base, baseline, as_pct=False)


def q_weekday_occ(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    from analytics.insight_service import build_olap

    olap = build_olap(db, hotel_id, d0, d1, dim="weekday")
    rows = []
    from infra.i18n import t as _t

    for s in olap.get("series") or []:
        rows.append(
            _row(
                s.get("label") or "—",
                s.get("nights") or 0,
                _t("营收占比 {pct}%", pct=s.get("rev_share_pct")),
            )
        )
    return _pack("平日/周末间夜", "间夜", rows, {"total_nights": olap.get("total_nights")}, empty=not rows)


def q_review_topics(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    start_dt = datetime.combine(d0, datetime.min.time())
    end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())
    reviews = (
        db.query(Review)
        .filter(Review.hotel_id == hotel_id, Review.created_at >= start_dt, Review.created_at < end_dt)
        .all()
    )
    if not reviews:
        return _pack("投诉主题", "单", [], empty=True)
    # 简易关键词桶
    topics = {"清洁": 0, "噪音/空调": 0, "前台/排队": 0, "早餐/餐饮": 0, "其他": 0}
    for r in reviews:
        text = f"{r.content or ''}".lower()
        hit = False
        if any(k in text for k in ("脏", "清洁", "卫生", "毛发")):
            topics["清洁"] += 1
            hit = True
        if any(k in text for k in ("噪", "空调", "吵", "异响")):
            topics["噪音/空调"] += 1
            hit = True
        if any(k in text for k in ("排队", "前台", "退房", "慢")):
            topics["前台/排队"] += 1
            hit = True
        if any(k in text for k in ("早餐", "餐", "味道")):
            topics["早餐/餐饮"] += 1
            hit = True
        if not hit:
            topics["其他"] += 1
    rows = [
        _row(k, v, "提及次数", "warn" if v >= 3 else "neutral")
        for k, v in sorted(topics.items(), key=lambda x: -x[1])
        if v > 0
    ]
    avg = round(sum(float(r.rating or 0) for r in reviews if r.rating is not None) / max(1, len(reviews)), 2)
    return _pack("投诉主题 Top", "单", rows, {"review_count": len(reviews), "avg_rating": avg}, empty=not rows)


def q_nps_trend(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    start_dt = datetime.combine(d0, datetime.min.time())
    end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())
    reviews = (
        db.query(Review)
        .filter(Review.hotel_id == hotel_id, Review.created_at >= start_dt, Review.created_at < end_dt)
        .all()
    )
    ratings = [float(r.rating or 0) for r in reviews if r.rating is not None]
    if not ratings:
        return _pack("NPS / 评分", "分", [], empty=True)
    avg = round(sum(ratings) / len(ratings), 2)
    promoters = sum(1 for x in ratings if x >= 4)
    detractors = sum(1 for x in ratings if x <= 2)
    nps = round((promoters - detractors) / len(ratings) * 100)
    replied = sum(1 for r in reviews if getattr(r, "replied", False))
    reply_rate = round(replied / len(reviews) * 100, 1) if reviews else 0
    rows = [
        _row("点评条数", len(reviews), ""),
        _row("均分", avg, "1–5"),
        _row("NPS 代理", nps, "≥4 推荐 / ≤2 贬损", "warn" if nps < 40 else "pos"),
        _row("回复率", f"{reply_rate}%", ""),
    ]
    return _pack("口碑指标", "—", rows, {"avg_rating": avg, "nps": nps, "count": len(reviews)})


def q_pickup_gap(db: Session, hotel_id: int, d0: date, d1: date, horizon: int = 7, **_) -> dict:
    from analytics.forecast_service import build_revenue_forecast

    board = build_revenue_forecast(db, hotel_id, growth_factor=1.0)
    pickup = board.get("pickup") or []
    target = None
    for p in pickup:
        days = int(p.get("window_days") or p.get("days") or p.get("horizon") or 0)
        if days == int(horizon):
            target = p
            break
    if not target and pickup:
        target = min(
            pickup,
            key=lambda x: abs(int(x.get("window_days") or x.get("days") or x.get("horizon") or 0) - int(horizon)),
        )
    from infra.i18n import t as _t

    title = _t("未来 {horizon} 天预订进度", horizon=horizon)
    if not target:
        return _pack(title, "间夜", [], empty=True)
    booked = int(target.get("booked") or target.get("booked_nights") or 0)
    expected = int(target.get("expected") or target.get("baseline") or 0)
    gap = int(target.get("gap") or max(0, expected - booked))
    gap_pct = float(target.get("gap_pct") or (round(gap / expected * 100, 1) if expected else 0))
    rows = [
        _row("已订", booked, "实际"),
        _row("应有", expected, "历史基线"),
        _row("缺口", gap, _t("缺口 {pct}%", pct=gap_pct), "warn" if gap_pct > 15 else "neutral"),
    ]
    return _pack(
        title,
        "间夜",
        rows,
        {"booked": booked, "expected": expected, "gap": gap, "gap_pct": gap_pct},
    )


def _guest_spend_stats(db: Session, hotel_id: int) -> list[dict[str, Any]]:
    """全生命周期：按客人汇总实付与入住次数（ignore_period）。"""
    from models import Guest

    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.guest_id.isnot(None),
            Order.status.in_(["reserved", "confirmed", "checked_in", "checked_out", "pending"]),
        )
        .all()
    )
    agg: dict[int, dict[str, Any]] = {}
    for o in orders:
        gid = int(o.guest_id)
        bucket = agg.setdefault(gid, {"spend": 0.0, "stays": 0, "last_out": None})
        bucket["spend"] += float(o.total_amount or 0)
        bucket["stays"] += 1
        cout = o.check_out.date() if o.check_out and hasattr(o.check_out, "date") else o.check_out
        if cout and (bucket["last_out"] is None or cout > bucket["last_out"]):
            bucket["last_out"] = cout

    if not agg:
        return []
    guests = {g.id: g for g in db.query(Guest).filter(Guest.id.in_(list(agg.keys()))).all()}
    rows = []
    for gid, st in agg.items():
        g = guests.get(gid)
        if not g or getattr(g, "merged_into_guest_id", None):
            continue
        stays = int(st["stays"] or 0)
        spend = round(float(st["spend"] or 0), 2)
        aov = round(spend / stays, 2) if stays else 0.0
        last_out = st["last_out"]
        idle_days = (date.today() - last_out).days if last_out else None
        rows.append(
            {
                "guest_id": gid,
                "guest_name": g.name,
                "name": g.name,
                "gender": g.gender,
                "phone": None,
                "spend": spend,
                "stays": stays,
                "aov": aov,
                "last_out": last_out.isoformat() if last_out else None,
                "idle_days": idle_days,
                "ltv": float(g.ltv or spend),
            }
        )
    return rows


def q_guest_top_cumulative(db: Session, hotel_id: int, d0: date, d1: date, top_n: int = 5, **_) -> dict:
    from infra.i18n import t as _t

    stats = _guest_spend_stats(db, hotel_id)
    stats.sort(key=lambda x: -x["spend"])
    top = stats[: max(1, int(top_n or 5))]
    rows = [
        {
            "label": s["guest_name"],
            "value": s["spend"],
            "note": _t("到店 {n} 次", n=s["stays"]),
            "tone": "pos",
            "guest_id": s["guest_id"],
            "guest_name": s["guest_name"],
            "gender": s.get("gender"),
            "stays": s["stays"],
        }
        for s in top
    ]
    return _pack(
        _t("累计消费 Top{n}", n=len(rows)),
        "元",
        rows,
        {"top_n": len(rows), "ignore_period": True, "metric": "cumulative_payment"},
        empty=not rows,
    )


def q_guest_top_stay_count(db: Session, hotel_id: int, d0: date, d1: date, top_n: int = 5, **_) -> dict:
    from infra.i18n import t as _t

    stats = _guest_spend_stats(db, hotel_id)
    stats.sort(key=lambda x: (-x["stays"], -x["spend"]))
    top = stats[: max(1, int(top_n or 5))]
    rows = [
        {
            "label": s["guest_name"],
            "value": s["stays"],
            "note": _t("累计 ¥{amount}", amount=s["spend"]),
            "tone": "pos",
            "guest_id": s["guest_id"],
            "guest_name": s["guest_name"],
            "gender": s.get("gender"),
            "spend": s["spend"],
        }
        for s in top
    ]
    return _pack(
        _t("到店次数 Top{n}", n=len(rows)),
        "次",
        rows,
        {"top_n": len(rows), "ignore_period": True, "metric": "stay_count"},
        empty=not rows,
    )


def q_guest_aov_distribution(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    stats = _guest_spend_stats(db, hotel_id)
    buckets = {"<300": 0, "300–599": 0, "600–999": 0, "≥1000": 0}
    for s in stats:
        a = float(s["aov"] or 0)
        if a < 300:
            buckets["<300"] += 1
        elif a < 600:
            buckets["300–599"] += 1
        elif a < 1000:
            buckets["600–999"] += 1
        else:
            buckets["≥1000"] += 1
    rows = [_row(k, v, "客户数") for k, v in buckets.items()]
    return _pack("客单价分布", "人", rows, {"guest_count": len(stats), "ignore_period": True}, empty=not stats)


def q_guest_churn_warning(db: Session, hotel_id: int, d0: date, d1: date, idle_days: int = 90, **_) -> dict:
    from infra.i18n import t as _t

    stats = _guest_spend_stats(db, hotel_id)
    sleepy = [s for s in stats if s.get("idle_days") is not None and s["idle_days"] >= int(idle_days)]
    sleepy.sort(key=lambda x: -int(x["idle_days"] or 0))
    top = sleepy[:10]
    rows = [
        {
            "label": s["guest_name"],
            "value": s["idle_days"],
            "note": _t("累计 ¥{amount} · 到店 {n} 次", amount=s["spend"], n=s["stays"]),
            "tone": "warn",
            "guest_id": s["guest_id"],
            "guest_name": s["guest_name"],
            "gender": s.get("gender"),
        }
        for s in top
    ]
    return _pack(
        _t("沉睡客户（≥{days} 天未住）", days=idle_days),
        "天",
        rows,
        {"count": len(sleepy), "threshold_days": idle_days, "ignore_period": True},
        empty=not rows,
    )


def q_guest_segment_by_tag(db: Session, hotel_id: int, d0: date, d1: date, **_) -> dict:
    from sqlalchemy import func as sa_func

    from models import GuestTag, TagDefinition

    guest_ids = [
        r[0]
        for r in db.query(Order.guest_id)
        .filter(Order.hotel_id == hotel_id, Order.guest_id.isnot(None))
        .distinct()
        .all()
    ]
    if not guest_ids:
        return _pack("标签客户分布", "人", [], empty=True)
    rows_q = (
        db.query(TagDefinition.name, sa_func.count(GuestTag.id))
        .join(GuestTag, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id.in_(guest_ids), TagDefinition.is_active.is_(True))
        .group_by(TagDefinition.id)
        .order_by(sa_func.count(GuestTag.id).desc())
        .limit(12)
        .all()
    )
    rows = [_row(str(name), int(cnt), "客户数") for name, cnt in rows_q]
    return _pack("按标签分群客户数", "人", rows, {"tag_count": len(rows), "ignore_period": True}, empty=not rows)


QUERY_REGISTRY = {
    "q_channel_profit_loss": q_channel_profit_loss,
    "q_ota_share_ratio": q_ota_share_ratio,
    "q_direct_book_rate": q_direct_book_rate,
    "q_business_churn": q_business_churn,
    "q_member_repurchase": q_member_repurchase,
    "q_segment_mix": q_segment_mix,
    "q_revpar_trend": q_revpar_trend,
    "q_occupancy_kpi": q_occupancy_kpi,
    "q_adr_kpi": q_adr_kpi,
    "q_revpar_kpi": q_revpar_kpi,
    "q_room_revenue_kpi": q_room_revenue_kpi,
    "q_weekday_occ": q_weekday_occ,
    "q_review_topics": q_review_topics,
    "q_nps_trend": q_nps_trend,
    "q_pickup_gap": q_pickup_gap,
    "q_guest_top_cumulative": q_guest_top_cumulative,
    "q_guest_top_stay_count": q_guest_top_stay_count,
    "q_guest_aov_distribution": q_guest_aov_distribution,
    "q_guest_churn_warning": q_guest_churn_warning,
    "q_guest_segment_by_tag": q_guest_segment_by_tag,
}


def register_query(query_ref: str, fn) -> None:
    """插件可追加确定性查询（模型只引用 query_ref，永不写 SQL）。"""
    key = (query_ref or "").strip()
    if not key:
        raise ValueError("query_ref required")
    QUERY_REGISTRY[key] = fn


def run_query(
    db: Session,
    hotel_id: int,
    query_ref: str,
    *,
    period_label: str = "本月",
    baseline: str = "同比",
    horizon: int = 7,
    top_n: int = 5,
    start: Optional[str] = None,
    end: Optional[str] = None,
    ignore_period: bool = False,
) -> dict[str, Any]:
    fn = QUERY_REGISTRY.get(query_ref)
    if not fn:
        return _pack("未知查询", "—", [], empty=True)
    d0, d1, lab, _ = resolve_ask_period(period_label, start=start, end=end)
    return fn(
        db,
        hotel_id,
        d0,
        d1,
        baseline=baseline,
        horizon=int(horizon or 7),
        top_n=int(top_n or 5),
        period_label=PERIOD_LABELS.get(period_label, period_label),
        range_label=lab,
        ignore_period=ignore_period,
    )
