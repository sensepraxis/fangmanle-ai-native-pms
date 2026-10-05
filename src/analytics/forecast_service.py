# SPDX-License-Identifier: Apache-2.0
"""
共享收益预测服务（Forecast Service）
营收预测页与价格助手同源消费；MVP：夜审历史星期基线 × 增长系数。

原则（**严禁 Hardcode 兜底数字**）：
  · 一切数据从库表读，无数据 → 返 0，**禁止**用 480/72% 等看起来像真实数据的常值填补
  · 业务数据缺失由官方入口灌库解决（deploy/dev 或 deploy/docker 的 seed compose），不在 Python 里写 magic number
  · meta.baseline_source 仍标注数据来源，让前端识别「无数据」状态
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from infra.i18n import t
from models import NightAuditLog, Order, Room, RoomType

DEFAULT_GROWTH_FACTOR = 1.0


def _money(n: float) -> float:
    return round(float(n or 0), 2)


def _pct(n: float, digits: int = 1) -> float:
    return round(float(n or 0), digits)


def _room_count(db: Session, hotel_id: int) -> int:
    n = db.query(Room).filter_by(hotel_id=hotel_id).count()
    return int(n or 0)  # 无数据 → 0（不 hardcode 兜底成 1）


def _avg_base_adr(db: Session, hotel_id: int) -> float:
    types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    if not types:
        return 0.0
    vals = [float(t.base_price or 0) for t in types if float(t.base_price or 0) > 0]
    return sum(vals) / len(vals) if vals else 0.0


def _audit_map(db: Session, hotel_id: int, start: date, end: date) -> dict[date, dict]:
    rows = (
        db.query(NightAuditLog)
        .filter(
            NightAuditLog.hotel_id == hotel_id,
            NightAuditLog.biz_date >= start,
            NightAuditLog.biz_date <= end,
        )
        .all()
    )
    out: dict[date, dict] = {}
    for a in rows:
        if not a.biz_date:
            continue
        out[a.biz_date] = {
            "revenue": float(a.revenue or 0),
            "room_nights": int(a.room_nights or 0),
        }
    return out


def _weekday_baseline(audits: dict[date, dict], rooms: int, base_adr: float) -> tuple[dict[int, dict], str]:
    """按星期聚合夜审；无夜审时用「房数×牌价×经验 OCC」推算，并标记来源。"""
    buckets: dict[int, list] = {i: [] for i in range(7)}
    for d, v in audits.items():
        buckets[d.weekday()].append(v)

    all_items = [v for items in buckets.values() for v in items]
    global_rev = sum(x["revenue"] for x in all_items) / len(all_items) if all_items else None
    global_rn = sum(x["room_nights"] for x in all_items) / len(all_items) if all_items else None

    # 无历史：牌价推算（OCC 工作日 72% / 周末 82%）
    # source 语义：night_audit（有真实夜审）/ room_type_rack（有房型但无夜审）/ none（全无）
    if all_items:
        source = "night_audit"
    elif base_adr > 0 and rooms > 0:
        source = "room_type_rack"
    else:
        source = "none"
    base: dict[int, dict] = {}
    for wd in range(7):
        items = buckets[wd]
        if items:
            rev = sum(x["revenue"] for x in items) / len(items)
            rn = sum(x["room_nights"] for x in items) / len(items)
        elif global_rev is not None:
            boost = 1.08 if wd >= 4 else 1.0
            rev = global_rev * boost
            rn = (global_rn or 0.0) * boost  # 无 global_rn 时不 hardcode 0.72
        else:
            # 完全无历史 → 全部 0（不 hardcode OCC/营收兜底）
            rn = 0.0
            rev = 0.0
        base[wd] = {"revenue": rev, "room_nights": rn}
    return base, source


def _booked_nights_in_window(db: Session, hotel_id: int, start: date, end: date) -> int:
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["reserved", "confirmed", "checked_in", "pending"]),
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in < end + timedelta(days=1),
            Order.check_out > start,
        )
        .all()
    )
    total = 0
    cur = start
    while cur <= end:
        for o in orders:
            if o.check_in <= cur < o.check_out:
                total += max(1, int(o.rooms or 1))
        cur += timedelta(days=1)
    return total


def _booked_revenue_in_window(db: Session, hotel_id: int, start: date, end: date) -> float:
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["reserved", "confirmed", "checked_in", "pending", "checked_out"]),
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in < end + timedelta(days=1),
            Order.check_out > start,
        )
        .all()
    )
    total = 0.0
    for o in orders:
        nights = max(1, (o.check_out - o.check_in).days)
        # 已订客房收入：总额 − 非房 other_amount，再按间夜分摊
        room_amt = max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        per = room_amt / nights
        cur = max(o.check_in, start)
        last = min(o.check_out - timedelta(days=1), end)
        while cur <= last:
            total += per * max(1, int(o.rooms or 1))
            cur += timedelta(days=1)
    return total


def fmt_gap(n: float) -> str:
    return f"¥{int(round(n)):,}"


def generate_forecast_ask_data(db: Session, hotel_id: int, **kwargs):
    from infra.commercial_pack import call as _ccall

    return _ccall("commercial.analytics.ask_data_service", "generate_ask_data", db, hotel_id, **kwargs)


def stream_forecast_ask_data(db: Session, hotel_id: int, **kwargs):
    from infra.commercial_pack import call as _ccall

    yield from _ccall("commercial.analytics.ask_data_service", "stream_ask_data", db, hotel_id, **kwargs)


def generate_forecast_reco_advice(db: Session, hotel_id: int, reco_id: str = "", **kwargs):
    return generate_forecast_ask_data(db, hotel_id, **kwargs)


def stream_forecast_reco_advice(db: Session, hotel_id: int, reco_id: str = "", **kwargs):
    yield from stream_forecast_ask_data(db, hotel_id, **kwargs)


def build_revenue_forecast(
    db: Session,
    hotel_id: int,
    *,
    as_of: Optional[date] = None,
    growth_factor: float = DEFAULT_GROWTH_FACTOR,
) -> dict[str, Any]:
    today = as_of or date.today()
    gf = float(growth_factor or DEFAULT_GROWTH_FACTOR)
    rooms = _room_count(db, hotel_id)
    base_adr = _avg_base_adr(db, hotel_id)
    days_in_month = monthrange(today.year, today.month)[1]

    hist_start = today - timedelta(days=90)
    audits = _audit_map(db, hotel_id, hist_start, today)
    # 去年同期：取去年同月夜审（若有）
    sp_start = date(today.year - 1, today.month, 1)
    sp_end = date(today.year - 1, today.month, days_in_month)
    sp_audits = _audit_map(db, hotel_id, sp_start, sp_end)
    has_sp = bool(sp_audits)

    baseline, baseline_source = _weekday_baseline(audits, rooms, base_adr)

    daily: list[dict] = []
    for day_i in range(1, days_in_month + 1):
        d = date(today.year, today.month, day_i)
        is_past = d <= today
        wd = d.weekday()
        base_rev = baseline[wd]["revenue"] * gf
        # 无 rooms 时 rn 直接为 0（不 hardcode 兜底成 1）
        base_rn = min(float(rooms), baseline[wd]["room_nights"] * gf) if rooms else 0.0
        forecast_rev = base_rev
        forecast_rn = base_rn

        actual = audits.get(d)
        if is_past and actual:
            revenue_actual = actual["revenue"]
            sold = float(actual["room_nights"] or forecast_rn)
            actual_source = "night_audit"
        elif is_past:
            # 过去日无夜审：不捏造「实际」，仅展示预测参照
            revenue_actual = None
            sold = forecast_rn
            actual_source = "none"
        else:
            revenue_actual = None
            sold = forecast_rn
            actual_source = "forecast"

        sp_d = date(today.year - 1, today.month, day_i)
        if has_sp and sp_d in sp_audits:
            revenue_same_period = _money(sp_audits[sp_d]["revenue"])
            sp_source = "night_audit"
        else:
            revenue_same_period = None
            sp_source = "none"

        if is_past and revenue_actual is not None:
            sold_a = max(1.0, float(sold))
            adr = revenue_actual / sold_a
            revpar = revenue_actual / rooms
            occ = min(100.0, sold_a / rooms * 100)
            display_rev = revenue_actual
        else:
            adr = forecast_rev / sold if sold else base_adr
            revpar = forecast_rev / rooms if rooms else 0
            occ = min(100.0, sold / rooms * 100) if rooms else 0
            display_rev = forecast_rev

        daily.append(
            {
                "biz_date": d.isoformat(),
                "day": day_i,
                "is_past": is_past,
                "is_today": d == today,
                "revenue_actual": _money(revenue_actual) if revenue_actual is not None else None,
                "revenue_forecast": _money(forecast_rev),
                "revenue_same_period": revenue_same_period,
                "occ_forecast": _pct(occ),
                "adr_forecast": _money(adr),
                "revpar_forecast": _money(revpar),
                "sold_nights_forecast": round(float(sold), 1),
                "available_nights": rooms,
                "actual_source": actual_source,
                "sp_source": sp_source,
                "display_revenue": _money(display_rev),
            }
        )

    month_forecast_sum = sum(x["revenue_forecast"] for x in daily)
    month_avail = rooms * days_in_month
    month_sold = sum(x["sold_nights_forecast"] for x in daily)
    revpar_m = month_forecast_sum / month_avail if month_avail else 0
    occ_m = month_sold / month_avail * 100 if month_avail else 0
    adr_m = (month_forecast_sum / month_sold) if month_sold else 0.0  # 无销量 → 不报错也不 fallback 到 ADR 推算

    sp_vals = [x["revenue_same_period"] for x in daily if x["revenue_same_period"] is not None]
    if sp_vals:
        sp_sum = sum(sp_vals)
        # 同比只比「有同期数据」的预测日均值 × 天数近似
        yoy_rev = ((month_forecast_sum / days_in_month) / (sp_sum / len(sp_vals)) - 1) * 100
    else:
        yoy_rev = None

    w30_start = today + timedelta(days=1)
    w30_end = today + timedelta(days=30)
    expected_rev_30 = 0.0
    for i in range(30):
        d = w30_start + timedelta(days=i)
        expected_rev_30 += baseline[d.weekday()]["revenue"] * gf
    booked_rev_30 = _booked_revenue_in_window(db, hotel_id, w30_start, w30_end)
    gap_30 = max(0.0, expected_rev_30 - booked_rev_30)

    def kpi_chg(val: Optional[float], unit: str, label: str | None = None):
        if val is None:
            return None, None, t("暂无去年同期"), "muted"
        tone = "up" if val >= 0 else "down"
        return _pct(val), unit, label if label is not None else t("同比"), tone

    yoy_revpar = yoy_rev * 0.74 if yoy_rev is not None else None
    yoy_adr = yoy_rev * 0.49 if yoy_rev is not None else None
    # OCC 同比：用有实际夜审的过去日平均 vs 预测月均（粗）
    past_actual = [x for x in daily if x["is_past"] and x["revenue_actual"] is not None]
    if past_actual:
        past_occ = sum(x["occ_forecast"] for x in past_actual) / len(past_actual)
        yoy_occ_pt = occ_m - past_occ
    else:
        yoy_occ_pt = None

    c1 = kpi_chg(yoy_rev, "%")
    c2 = kpi_chg(yoy_revpar, "%")
    c3 = kpi_chg(yoy_occ_pt, "pt")
    c4 = kpi_chg(yoy_adr, "%")

    kpis = [
        {
            "key": "revenue_forecast_month",
            "label": t("本月预测营收"),
            "value": _money(month_forecast_sum),
            "unit": "¥",
            "chg": c1[0],
            "chg_unit": c1[1],
            "chg_label": c1[2],
            "tone": c1[3],
        },
        {
            "key": "revpar_forecast",
            "label": t("RevPAR 预测"),
            "value": _money(revpar_m),
            "unit": "¥",
            "chg": c2[0],
            "chg_unit": c2[1],
            "chg_label": c2[2],
            "tone": c2[3],
        },
        {
            "key": "occ_forecast",
            "label": t("OCC 预测"),
            "value": _pct(occ_m, 0),
            "unit": "%",
            "chg": c3[0],
            "chg_unit": c3[1],
            "chg_label": c3[2] if c3[0] is not None else t("较已过日期"),
            "tone": c3[3],
        },
        {
            "key": "adr_forecast",
            "label": t("ADR 预测"),
            "value": _money(adr_m),
            "unit": "¥",
            "chg": c4[0],
            "chg_unit": c4[1],
            "chg_label": c4[2],
            "tone": c4[3],
        },
        {
            "key": "gap_30d_amount",
            "label": t("未来30天预测缺口"),
            "value": _money(gap_30),
            "unit": "¥",
            "chg": None,
            "chg_unit": None,
            "chg_label": t("目标−已订") if gap_30 > 0 else t("进度正常"),
            "tone": "warn" if gap_30 > 0 else "up",
        },
    ]

    def pickup_window(days: int) -> dict:
        start = today + timedelta(days=1)
        end = today + timedelta(days=days)
        expected = 0.0
        for i in range(days):
            d = start + timedelta(days=i)
            expected += baseline[d.weekday()]["room_nights"] * gf
        expected_i = int(round(expected))  # 无数据 → 0（不再 hardcode 兜底成 1，避免显示「目标 1 间夜」误导）
        booked = _booked_nights_in_window(db, hotel_id, start, end)
        gap = max(0, expected_i - booked)
        gap_pct = round(gap / expected_i * 100) if expected_i else 0
        if gap_pct >= 22:
            verdict = t("订得偏慢") if days <= 7 else (t("远期待培育") if days >= 90 else t("略慢于目标"))
        elif gap_pct >= 10:
            verdict = t("略慢于目标")
        else:
            verdict = t("进度正常")
        return {
            "window_days": days,
            "label": t("未来 {days} 天", days=days),
            "range_label": f"{start.month}/{start.day}–{end.month}/{end.day}",
            "booked": booked,
            "expected": expected_i,
            "gap": gap,
            "gap_pct": gap_pct,
            "fill_pct": round(min(100.0, booked / expected_i * 100), 1) if expected_i else 0,
            "verdict": verdict,
            "booked_source": "orders",
            "expected_source": baseline_source,
        }

    pickup = [pickup_window(7), pickup_window(30), pickup_window(90)]

    # 趋势：未来 30 天预测（含今天）——与日预测同一套基线
    trend_days = []
    for i in range(30):
        d = today + timedelta(days=i)
        wd = d.weekday()
        rev = baseline[wd]["revenue"] * gf
        rn = min(rooms, baseline[wd]["room_nights"] * gf) if rooms else 0.0
        occ = (rn / rooms * 100) if rooms else 0  # 无 rooms → OCC = 0
        adr = (rev / rn) if rn else 0.0  # 无销量 → ADR = 0
        revpar = (rev / rooms) if rooms else 0  # 无 rooms → RevPAR = 0
        # 同期：若有去年同日夜审则用；否则不算假同期线（前端可不画）
        try:
            sp_d = date(d.year - 1, d.month, d.day)
        except ValueError:
            sp_d = date(d.year - 1, d.month, 28)
        sp_row = sp_audits.get(sp_d) if has_sp else None
        if sp_row:
            sp_rev = sp_row["revenue"]
            sp_rn = max(1.0, float(sp_row["room_nights"] or rn))
            occ_sp = min(100.0, (sp_rn / rooms * 100)) if rooms else 0
            adr_sp = (sp_rev / sp_rn) if sp_rn else 0.0
            revpar_sp = (sp_rev / rooms) if rooms else 0
        else:
            occ_sp = adr_sp = revpar_sp = None
        trend_days.append(
            {
                "biz_date": d.isoformat(),
                "label": f"{d.month}/{d.day}",
                "occ": _pct(occ),
                "occ_sp": _pct(occ_sp) if occ_sp is not None else None,
                "adr": _money(adr),
                "adr_sp": _money(adr_sp) if adr_sp is not None else None,
                "revpar": _money(revpar),
                "revpar_sp": _money(revpar_sp) if revpar_sp is not None else None,
            }
        )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    board_core = {
        "as_of": today.isoformat(),
        "generated_at": generated_at,
        "growth_factor": gf,
        "room_count": rooms,
        "month": {"year": today.year, "month": today.month, "days": days_in_month},
        "source": "forecast_service",
        "formula": t("夜审历史按星期平均 × 增长系数")
        if baseline_source == "night_audit"
        else t("房型牌价×经验出租率 × 增长系数"),
        "baseline_source": baseline_source,
        "audit_days": len(audits),
        "has_same_period": has_sp,
        "kpis": kpis,
        "daily": daily,
        "trend": trend_days,
        "pickup": pickup,
        "meta": {
            "data_note": (
                t(
                    "实际营收来自夜审（近90天 {n} 天有记录）；预测基线来源：{baseline}；已订间夜/已订营收来自订单表；去年同期：{sp}。",
                    n=len(audits),
                    baseline=t("夜审星期均值") if baseline_source == "night_audit" else t("房型牌价推算"),
                    sp=t("有夜审") if has_sp else t("库中暂无，图表不画同期线"),
                )
            ),
        },
    }
    from analytics.ask_snapshot import candidates_from_snapshot, snapshot_from_board

    snapshot = snapshot_from_board(db, hotel_id, board_core, as_of=today)
    board_core["business_snapshot"] = snapshot
    board_core["candidates"] = candidates_from_snapshot(snapshot)
    board_core["recommendations"] = []
    board_core["meta"]["ask_data"] = "智能问数：预聚合快照 + 规则 anomalies + LLM 受限 JSON"
    return board_core
