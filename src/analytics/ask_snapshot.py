# SPDX-License-Identifier: Apache-2.0
"""经营快照与规则预检（OpenCore）。LLM 诊断在 commercial.analytics.ask_data_service。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from infra.i18n import t
from models import Channel, Hotel, Order, Room, RoomType


def _pct01(n: float, digits: int = 4) -> float:
    return round(float(n or 0), digits)


def _channel_bucket(code: str | None, ctype: str | None) -> str:
    c = (code or "").lower()
    t = (ctype or "").lower()
    if c in ("agreement",) or t == "agreement":
        return "corp"
    if c in ("wechat", "wecom") or t == "wechat":
        return "member"
    if c in ("direct",) or t in ("direct", "map", "geo"):
        return "direct"
    if c in ("ctrip", "meituan", "fliggy", "ota", "meituan_voucher", "douyin", "xiaohongshu") or t in (
        "booking",
        "voucher",
        "xiaohongshu",
    ):
        return "ota"
    if t == "longstay":
        return "direct"
    return "ota"


def _segment_bucket(order: Order, ch_code: str | None) -> str:
    ot = int(order.order_type or 1)
    if ot == 5 or order.group_name:
        return "group"
    if ot == 3 or (ch_code or "").lower() == "agreement":
        return "business"
    if (ch_code or "").lower() in ("wechat", "wecom"):
        return "member"
    if ot == 4:
        return "leisure"
    return "leisure"


def _active_orders(db: Session, hotel_id: int, start: date, end: date) -> list[Order]:
    return (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in < end + timedelta(days=1),
            Order.check_out > start,
            Order.status.in_(["reserved", "confirmed", "checked_in", "pending", "checked_out"]),
        )
        .all()
    )


def _nights_in_window(o: Order, start: date, end: date) -> int:
    cur = max(o.check_in, start)
    last = min(o.check_out - timedelta(days=1), end)
    n = 0
    rooms = max(1, int(o.rooms or 1))
    while cur <= last:
        n += rooms
        cur += timedelta(days=1)
    return n


def _mix_from_orders(db: Session, hotel_id: int, start: date, end: date) -> tuple[dict[str, float], dict[str, float]]:
    channels = {c.id: c for c in db.query(Channel).all()}
    orders = _active_orders(db, hotel_id, start, end)
    ch_nights = {"ota": 0, "direct": 0, "corp": 0, "member": 0}
    seg_nights = {"leisure": 0, "business": 0, "group": 0, "member": 0}
    total = 0
    for o in orders:
        n = _nights_in_window(o, start, end)
        if n <= 0:
            continue
        ch = channels.get(o.channel_id)
        code = ch.code if ch else None
        ctype = ch.type if ch else None
        ch_nights[_channel_bucket(code, ctype)] += n
        seg_nights[_segment_bucket(o, code)] += n
        total += n
    if total <= 0:
        return (
            {"ota_pct": 0.0, "direct_pct": 0.0, "corp_pct": 0.0, "member_pct": 0.0},
            {"leisure_pct": 0.0, "business_pct": 0.0, "group_pct": 0.0, "member_pct": 0.0},
        )
    channel_mix = {
        "ota_pct": _pct01(ch_nights["ota"] / total),
        "direct_pct": _pct01(ch_nights["direct"] / total),
        "corp_pct": _pct01(ch_nights["corp"] / total),
        "member_pct": _pct01(ch_nights["member"] / total),
    }
    segment_mix = {
        "leisure_pct": _pct01(seg_nights["leisure"] / total),
        "business_pct": _pct01(seg_nights["business"] / total),
        "group_pct": _pct01(seg_nights["group"] / total),
        "member_pct": _pct01(seg_nights["member"] / total),
    }
    return channel_mix, segment_mix


def _business_share(db: Session, hotel_id: int, start: date, end: date) -> float:
    _, seg = _mix_from_orders(db, hotel_id, start, end)
    return float(seg.get("business_pct") or 0)


def _rule_anomaly_items(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """§2.1 规则预检：产出 code（入模）+ label（老板可读）+ severity。"""
    items: list[dict[str, str]] = []
    pk = (snapshot.get("pickup") or {}).get("w7") or {}
    booked = float(pk.get("booked") or 0)
    expected = float(pk.get("expected") or 0)
    gap = float(pk.get("gap") or max(0.0, expected - booked))
    gap_pct = (gap / expected * 100) if expected > 0 else 0.0
    if gap_pct > 20 and gap > 0:
        items.append(
            {
                "code": f"pickup.w7 缺口{gap_pct:.0f}%",
                "label": t(
                    "未来7天订房偏慢：已订 {booked} / 目标 {expected} 间夜，缺口约 {gap_pct}%",
                    booked=int(booked),
                    expected=int(expected),
                    gap_pct=f"{gap_pct:.0f}",
                ),
                "severity": "高" if gap_pct >= 35 else "中",
            }
        )

    seg = snapshot.get("segment_mix") or {}
    biz = float(seg.get("business_pct") or 0)
    biz_yoy = seg.get("business_yoy")
    if biz_yoy is not None:
        drop_pt = (float(biz_yoy) - biz) * 100
        if drop_pt > 5:
            items.append(
                {
                    "code": f"segment_mix.business 低于同期{drop_pt:.0f}pt",
                    "label": t(
                        "商务客占比偏低：当前 {biz}%，低于去年同期约 {drop_pt} 个百分点",
                        biz=f"{biz * 100:.0f}",
                        drop_pt=f"{drop_pt:.0f}",
                    ),
                    "severity": "中",
                }
            )

    ch = snapshot.get("channel_mix") or {}
    ota = float(ch.get("ota_pct") or 0)
    if ota > 0.55:
        items.append(
            {
                "code": "channel_mix.ota 占比>55%",
                "label": t(
                    "线上旅行社（OTA）订房占比偏高：约 {ota}%（超过 55%）",
                    ota=f"{ota * 100:.0f}",
                ),
                "severity": "中",
            }
        )

    price = snapshot.get("price_position") or {}
    idx = price.get("adr_index_vs_comp")
    # 仅在有真实 ADR / 牌价数据时触发（idx=0 表示无数据，不算「偏低」）
    if idx is not None and float(idx) > 0 and float(idx) < 0.92:
        items.append(
            {
                "code": f"price_position.adr_index_vs_comp {float(idx):.2f}<0.92",
                "label": t(
                    "房价相对参照偏低：指数 {idx}（低于 0.92，有上调空间）",
                    idx=f"{float(idx):.2f}",
                ),
                "severity": "中",
            }
        )

    kpi = snapshot.get("kpi") or {}
    occ = float(kpi.get("occ") or 0)
    adr_yoy = kpi.get("adr_yoy_pct")
    if occ < 0.60 and adr_yoy is not None and float(adr_yoy) < 0:
        items.append(
            {
                "code": f"kpi.occ {occ:.2f}<0.60 且 adr_yoy_pct {float(adr_yoy):.1f}<0",
                "label": t(
                    "平日入住偏弱且房价同比下滑：出租率约 {occ}%，房价同比 {adr_yoy}%",
                    occ=f"{occ * 100:.0f}",
                    adr_yoy=f"{float(adr_yoy):.1f}",
                ),
                "severity": "高",
            }
        )

    return items


def _rule_anomalies(snapshot: dict[str, Any]) -> list[str]:
    """入模用：保留字段码，供 LLM evidence 对齐。"""
    return [x["code"] for x in _rule_anomaly_items(snapshot)]


def snapshot_from_board(
    db: Session,
    hotel_id: int,
    board: dict[str, Any],
    *,
    as_of: Optional[date] = None,
) -> dict[str, Any]:
    """由营收预测 board + 订单聚合，生成 §3 business_snapshot。"""
    today = as_of or date.fromisoformat(str(board.get("as_of") or date.today().isoformat()))
    hotel = db.get(Hotel, hotel_id) or db.query(Hotel).order_by(Hotel.id.asc()).first()
    rooms = int(board.get("room_count") or db.query(Room).filter_by(hotel_id=hotel_id).count() or 1)

    kpi_map = {k["key"]: k for k in (board.get("kpis") or [])}
    occ = float((kpi_map.get("occ_forecast") or {}).get("value") or 0) / 100.0
    adr = float((kpi_map.get("adr_forecast") or {}).get("value") or 0)
    revpar = float((kpi_map.get("revpar_forecast") or {}).get("value") or 0)
    rev_m = float((kpi_map.get("revenue_forecast_month") or {}).get("value") or 0)

    def yoy_of(key: str) -> Optional[float]:
        k = kpi_map.get(key) or {}
        if k.get("chg") is None:
            return None
        return float(k.get("chg"))

    pickup_board = board.get("pickup") or []
    pickup: dict[str, Any] = {}
    for p, key in zip(pickup_board[:3], ("w7", "w30", "w90")):
        pickup[key] = {
            "booked": int(p.get("booked") or 0),
            "expected": int(p.get("expected") or 0),
            "gap": int(p.get("gap") or 0),
        }

    mix_start = today - timedelta(days=14)
    mix_end = today + timedelta(days=30)
    channel_mix, segment_mix = _mix_from_orders(db, hotel_id, mix_start, mix_end)
    try:
        yoy_start = date(mix_start.year - 1, mix_start.month, mix_start.day)
        yoy_end = date(mix_end.year - 1, mix_end.month, mix_end.day)
    except ValueError:
        yoy_start = mix_start - timedelta(days=365)
        yoy_end = mix_end - timedelta(days=365)
    segment_mix["business_yoy"] = _pct01(_business_share(db, hotel_id, yoy_start, yoy_end))

    types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    rack = [float(t.base_price or 0) for t in types if float(t.base_price or 0) > 0]
    rack_avg = sum(rack) / len(rack) if rack else (adr or 480)
    adr_index = _pct01((adr / rack_avg) if rack_avg else 1.0, 3)

    snapshot = {
        "hotel": {
            "name": hotel.name if hotel else "酒店",
            "room_count": int(rooms),
            "date": today.isoformat(),
            "type": "散客为主",
        },
        "kpi": {
            "occ": _pct01(occ, 3),
            "adr": round(adr, 2),
            "revpar": round(revpar, 2),
            "revenue_month": round(rev_m, 2),
            "occ_yoy_pt": yoy_of("occ_forecast"),
            "adr_yoy_pct": yoy_of("adr_forecast"),
            "revpar_yoy_pct": yoy_of("revpar_forecast"),
        },
        "pickup": pickup,
        "channel_mix": channel_mix,
        "segment_mix": segment_mix,
        "price_position": {
            "adr_index_vs_comp": adr_index,
            "note": "无竞品库时用 本店ADR/牌价均价 作代理指数",
        },
        "anomalies": [],
        "meta": {
            "baseline_source": board.get("baseline_source"),
            "audit_days": board.get("audit_days"),
            "data_note": (board.get("meta") or {}).get("data_note"),
        },
    }
    snapshot["anomalies"] = _rule_anomalies(snapshot)
    return snapshot


def build_business_snapshot(
    db: Session,
    hotel_id: int,
    *,
    as_of: Optional[date] = None,
    growth_factor: float = 1.0,
    board: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """§3 输入数据契约：不含原始订单行。"""
    if board is None:
        from analytics.forecast_service import build_revenue_forecast

        board = build_revenue_forecast(db, hotel_id, as_of=as_of, growth_factor=growth_factor)
    return snapshot_from_board(db, hotel_id, board, as_of=as_of)


def candidates_from_snapshot(snapshot: dict[str, Any]) -> list[dict]:
    """前端展示用：中文说明 + 高/中/低；入模仍用 anomalies 字段码。"""
    items = _rule_anomaly_items(snapshot)
    sev_class = {"高": "high", "中": "medium", "低": "low"}
    return [
        {
            "id": f"anom-{i + 1}",
            "kind": "rule_anomaly",
            "severity": sev_class.get(it["severity"], "medium"),
            "severity_label": t(it["severity"]),
            "summary": it["label"],
            "why_flagged": it["code"],
        }
        for i, it in enumerate(items)
    ]
