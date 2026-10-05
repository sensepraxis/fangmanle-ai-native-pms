# SPDX-License-Identifier: Apache-2.0
"""库存预测 / 日历看板（从 room_board_service 绞杀抽出）。

公开：build_inventory_forecast / build_inventory_calendar / build_inventory_forecast_day_detail
``room_board_service`` 仍 re-export。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

import models as _models
from domain import ValidationError
from infra.i18n import t

globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})

_WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _date_label(d: date) -> str:
    return t("{y}年{m}月{d}日", y=d.year, m=d.month, d=d.day)


def _date_label_md(d: date) -> str:
    return t("{m}月{d}日", m=d.month, d=d.day)


def _weekday_label(d: date) -> str:
    return t(_WD[d.weekday()])


def build_inventory_forecast(db: Session, hotel_id: int, days: int = 30, start_date: Optional[str] = None):
    """未来窗口入住压力热力：锚点日起 N 天；已订率来自 room_night_inventory，预测来自 demand_forecast。"""
    from bootstrap.ensure_room_inventory import ensure_hotel_nights

    days = max(7, min(90, int(days or 30)))
    today = date.today()
    if start_date:
        try:
            start = date.fromisoformat(str(start_date)[:10])
        except ValueError:
            start = today
    else:
        start = today
    end = start + timedelta(days=days - 1)

    # 物化覆盖 [min(today,start), end]，保证未来锚点窗口有数据
    mat_start = min(today, start)
    mat_days = (end - mat_start).days + 1
    ensure_hotel_nights(db, hotel_id, mat_days, start=mat_start)

    room_total = db.query(Room).filter_by(hotel_id=hotel_id).count() or 1
    types = {rt.id: rt for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}
    wd_cn = [t(x) for x in _WD]

    night_rows = (
        db.query(RoomNightInventory)
        .filter(
            RoomNightInventory.hotel_id == hotel_id,
            RoomNightInventory.biz_date >= start,
            RoomNightInventory.biz_date <= end,
        )
        .all()
    )
    nights_by_day: dict = {}
    for n in night_rows:
        bag = nights_by_day.setdefault(n.biz_date, {"sold": 0, "available": 0, "blocked": 0})
        st = (n.status or "").lower()
        if st == "sold":
            bag["sold"] += 1
        elif st == "blocked":
            bag["blocked"] += 1
        else:
            bag["available"] += 1

    fc_rows = (
        db.query(DemandForecast)
        .filter(
            DemandForecast.hotel_id == hotel_id,
            DemandForecast.biz_date >= start,
            DemandForecast.biz_date <= end,
        )
        .all()
    )
    pred_by_day: dict = {}
    adr_by_day: dict = {}
    for f in fc_rows:
        if f.predicted_occ is not None:
            pred_by_day.setdefault(f.biz_date, []).append(float(f.predicted_occ))
        if f.predicted_adr is not None:
            adr_by_day.setdefault(f.biz_date, []).append(float(f.predicted_adr))

    def _occ_from_nights(d: date) -> dict:
        bag = nights_by_day.get(d) or {"sold": 0, "available": 0, "blocked": 0}
        sold = int(bag["sold"])
        available = int(bag["available"])
        blocked = int(bag["blocked"])
        if sold + available + blocked > 0:
            sellable = max(1, sold + available)
        else:
            sellable = max(1, room_total - blocked)
            available = sellable - sold
        booked_pct = min(100, round(100 * sold / sellable))
        return {
            "sold": sold,
            "available": available,
            "blocked": blocked,
            "sellable": sellable,
            "booked_pct": booked_pct,
        }

    def _hist_booked(d: date) -> int | None:
        """历史已订率：优先夜库存，否则用订单占房粗算。"""
        rows = (
            db.query(RoomNightInventory)
            .filter(RoomNightInventory.hotel_id == hotel_id, RoomNightInventory.biz_date == d)
            .all()
        )
        if rows:
            sold = sum(1 for n in rows if (n.status or "").lower() == "sold")
            blocked = sum(1 for n in rows if (n.status or "").lower() == "blocked")
            avail = sum(1 for n in rows if (n.status or "").lower() not in ("sold", "blocked"))
            sellable = max(1, sold + avail) if (sold + avail + blocked) else max(1, room_total - blocked)
            return min(100, round(100 * sold / sellable))
        orders = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.status.in_(("checked_in", "confirmed", "pending", "checked_out")),
                Order.check_in <= d,
                Order.check_out > d,
            )
            .all()
        )
        if not orders:
            return None
        booked_n = sum(max(1, int(o.rooms or 1)) for o in orders)
        return min(100, round(100 * booked_n / room_total))

    day_list = []
    for i in range(days):
        d = start + timedelta(days=i)
        st = _occ_from_nights(d)
        preds = pred_by_day.get(d) or []
        predicted_pct = round(100 * (sum(preds) / len(preds))) if preds else None
        booked_pct = st["booked_pct"]
        # 压力色：有预测用预测，否则用已订（避免混成一个数）
        pressure = predicted_pct if predicted_pct is not None else booked_pct
        heat = "high" if pressure >= 81 else ("med" if pressure >= 41 else "low")
        yoy = _hist_booked(
            date(d.year - 1, d.month, d.day) if not (d.month == 2 and d.day == 29) else date(d.year - 1, 2, 28)
        )
        try:
            mom_d = d.replace(month=d.month - 1) if d.month > 1 else d.replace(year=d.year - 1, month=12)
        except ValueError:
            mom_d = d - timedelta(days=30)
        mom = _hist_booked(mom_d)
        adrs = adr_by_day.get(d) or []
        day_list.append(
            {
                "date": d.isoformat(),
                "day": d.day,
                "weekday": d.weekday(),
                "weekday_cn": wd_cn[d.weekday()],
                "label": _date_label(d),
                "label_md": _date_label_md(d),
                "label_cell": f"{_date_label(d)} {wd_cn[d.weekday()]}",
                "predicted_pct": predicted_pct,
                "booked_pct": booked_pct,
                "pct": pressure,
                "sold": st["sold"],
                "available": st["available"],
                "blocked": st["blocked"],
                "sellable": st["sellable"],
                "adr": round(sum(adrs) / len(adrs), 0) if adrs else None,
                "heat": heat,
                "special": pressure >= 88,
                "hist_yoy_pct": yoy,
                "hist_mom_pct": mom,
                "pct_source": "predicted" if predicted_pct is not None else "booked",
            }
        )

    weeks = []
    for w in range(0, min(days, 35), 7):
        chunk = day_list[w : w + 7]
        if not chunk:
            break
        weeks.append(
            {
                "wk": f"第{len(weeks) + 1}周",
                "booked": round(sum(x["booked_pct"] for x in chunk) / len(chunk)),
                "forecast": round(sum(x["pct"] for x in chunk) / len(chunk)),
            }
        )

    def _ymd(iso: str) -> str:
        dd = date.fromisoformat(iso)
        return f"{dd.year}年{dd.month}月{dd.day}日"

    def _tip_for_day(hd: dict):
        d = date.fromisoformat(hd["date"])
        tip_rt = None
        best_adr = 0.0
        for f in fc_rows:
            if f.biz_date == d and float(f.predicted_adr or 0) > best_adr:
                best_adr = float(f.predicted_adr or 0)
                tip_rt = types.get(f.room_type_id)
        return tip_rt, best_adr

    def _range_label(start_iso: str, end_iso: str | None = None) -> str:
        if not end_iso or end_iso == start_iso:
            return _ymd(start_iso)
        a = date.fromisoformat(start_iso)
        b = date.fromisoformat(end_iso)
        if a.year == b.year and a.month == b.month:
            return f"{a.year}年{a.month}月{a.day}日 – {b.day}日"
        if a.year == b.year:
            return f"{a.year}年{a.month}月{a.day}日 – {b.month}月{b.day}日"
        return f"{_ymd(start_iso)} – {_ymd(end_iso)}"

    opportunities = []
    used_dates: set = set()
    ranked = sorted(day_list, key=lambda x: -x["pct"])
    for hd in ranked:
        if len(opportunities) >= 2:
            break
        if hd["date"] in used_dates:
            continue
        tip_rt, best_adr = _tip_for_day(hd)
        bump = 15 if hd["pct"] >= 88 else (12 if hd["pct"] >= 75 else 8)
        tone = "raise" if hd["pct"] >= 72 else "watch"
        action = f"建议提价 +{bump}%" if tone == "raise" else "观察中"
        bits = [f"AI 备注：压力 {hd['pct']}%（已订 {hd['booked_pct']}% · 已售 {hd['sold']}/可售库存 {hd['sellable']}）"]
        if tip_rt and best_adr:
            bits.append(f"{tip_rt.name} ADR 约 ¥{int(best_adr)}")
        bits.append("库存偏紧，建议收紧折扣。" if hd["pct"] >= 80 else "压力可控，可微调周末价格。")
        opportunities.append(
            {
                "range": _ymd(hd["date"]),
                "action": action,
                "tone": tone,
                "note": "，".join(bits),
                "room_type": tip_rt.name if tip_rt else None,
                "pct": hd["pct"],
                "booked_pct": hd["booked_pct"],
                "adr": int(best_adr) if best_adr else hd.get("adr"),
            }
        )
        used_dates.add(hd["date"])

    for i, hd in enumerate(day_list):
        if len(opportunities) >= 4:
            break
        if date.fromisoformat(hd["date"]).weekday() != 4:
            continue
        chunk = day_list[i : i + 3]
        if len(chunk) < 2 or any(x["date"] in used_dates for x in chunk):
            continue
        avg_pct = round(sum(x["pct"] for x in chunk) / len(chunk))
        tip_rt, best_adr = _tip_for_day(max(chunk, key=lambda x: x["pct"]))
        opportunities.append(
            {
                "range": _range_label(chunk[0]["date"], chunk[-1]["date"]),
                "action": "建议提价 +10%" if avg_pct >= 65 else "周末包价观察",
                "tone": "raise" if avg_pct >= 65 else "watch",
                "note": f"AI 备注：周末段平均压力 {avg_pct}%。可组合连住优惠与高价值房型加价。",
                "room_type": tip_rt.name if tip_rt else None,
                "pct": avg_pct,
                "booked_pct": round(sum(x["booked_pct"] for x in chunk) / len(chunk)),
                "adr": int(best_adr) if best_adr else None,
            }
        )
        used_dates.update(x["date"] for x in chunk)

    for hd in sorted(day_list, key=lambda x: x["pct"]):
        if len(opportunities) >= 5:
            break
        if hd["date"] in used_dates or hd["pct"] > 55:
            continue
        tip_rt, best_adr = _tip_for_day(hd)
        opportunities.append(
            {
                "range": _ymd(hd["date"]),
                "action": "建议促销 -8%" if hd["pct"] <= 40 else "观察中",
                "tone": "promo" if hd["pct"] <= 40 else "watch",
                "note": f"AI 备注：压力仅 {hd['pct']}%（已订 {hd['booked_pct']}%），可开放限时闪促填补空房。",
                "room_type": tip_rt.name if tip_rt else None,
                "pct": hd["pct"],
                "booked_pct": hd["booked_pct"],
                "adr": int(best_adr) if best_adr else hd.get("adr"),
            }
        )
        used_dates.add(hd["date"])

    for hd in ranked:
        if len(opportunities) >= 4:
            break
        if hd["date"] in used_dates:
            continue
        tip_rt, best_adr = _tip_for_day(hd)
        opportunities.append(
            {
                "range": _ymd(hd["date"]),
                "action": "观察中",
                "tone": "watch",
                "note": f"AI 备注：压力 {hd['pct']}%（已订 {hd['booked_pct']}%），持续监测渠道转化。",
                "room_type": tip_rt.name if tip_rt else None,
                "pct": hd["pct"],
                "booked_pct": hd["booked_pct"],
                "adr": int(best_adr) if best_adr else hd.get("adr"),
            }
        )
        used_dates.add(hd["date"])

    peak = max((x["pct"] for x in day_list), default=0)
    insights = [
        {
            "insight": (
                f"窗口 {_ymd(start.isoformat())} 起共 {days} 天，峰值压力约 {peak}%。蓝=宜促 · 黄=正常 · 红=宜提价。"
            ),
        },
        {
            "insight": f"在册客房 {room_total} 间；夜库存行 {len(night_rows)} 条。历史同比/环比仅悬停参考。",
        },
    ]

    return {
        "days": day_list,
        "weeks": weeks or [{"wk": "第1周", "booked": 0, "forecast": 0}],
        "opportunities": opportunities,
        "insights": insights,
        "room_total": room_total,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "buffer_rooms": max(1, round(room_total * 0.05)),
        "buffer_pct": 85 if peak < 90 else 70,
        "meta": {
            "source": "room_night_inventory + demand_forecast",
            "night_rows": len(night_rows),
            "covered_days": sum(
                1 for x in day_list if (x.get("sold", 0) + x.get("available", 0) + x.get("blocked", 0)) > 0
            ),
            "room_total": room_total,
            "formula": "已订率 = 已售/(已售+可售)×100（停用房不计）；压力色优先用预测入住率，无预测则用已订率",
            "colors": {"low": "#4ECDC4", "med": "#F7B731", "high": "#E74C3C"},
        },
    }


def build_inventory_calendar(db: Session, hotel_id: int, days: int = 30, rebuild: bool = False):
    """按日库存面板：优先读 room_night_inventory（按日×房间），缺数据时从订单/房态物化。"""
    from bootstrap.ensure_room_inventory import ensure_hotel_nights, rebuild_room_night_inventory

    days = max(1, min(31, int(days or 14)))
    start = date.today()
    end = start + timedelta(days=days - 1)

    if rebuild:
        rebuild_room_night_inventory(db, hotel_id, days)
    else:
        ensure_hotel_nights(db, hotel_id, days)

    room_rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id)
        .order_by(Room.room_no)
        .all()
    )
    room_meta = {
        r.id: {
            "id": r.id,
            "room_no": r.room_no,
            "room_type_name": rt.name if rt else "客房",
            "room_status": r.status,
        }
        for r, rt in room_rows
    }

    night_rows = (
        db.query(RoomNightInventory)
        .filter(
            RoomNightInventory.hotel_id == hotel_id,
            RoomNightInventory.biz_date >= start,
            RoomNightInventory.biz_date <= end,
        )
        .all()
    )
    by_day: dict = {}
    for n in night_rows:
        by_day.setdefault(n.biz_date, []).append(n)

    unassigned_orders = (
        db.query(Order, Guest, RoomType)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .outerjoin(RoomType, Order.room_type_id == RoomType.id)
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed")),
            Order.check_in <= end,
            Order.check_out > start,
            Reservation.id.is_(None),
        )
        .order_by(Order.check_in, Order.id)
        .all()
    )
    unassigned_summary = []
    for od, g, rt in unassigned_orders:
        holds = (
            db.query(RoomNightInventory, Room)
            .join(Room, RoomNightInventory.room_id == Room.id)
            .filter(
                RoomNightInventory.hotel_id == hotel_id,
                RoomNightInventory.order_id == od.id,
                RoomNightInventory.source == "order_hold",
                RoomNightInventory.biz_date >= start,
                RoomNightInventory.biz_date <= end,
            )
            .all()
        )
        room_nos = sorted({rm.room_no for _, rm in holds})
        unassigned_summary.append(
            {
                "order_id": od.id,
                "order_no": od.order_no,
                "guest_name": g.name if g else None,
                "room_type_name": rt.name if rt else "客房",
                "rooms": max(1, int(od.rooms or 1)),
                "assigned_rooms": room_nos,
                "check_in": od.check_in.isoformat(),
                "check_out": od.check_out.isoformat(),
                "fully_assigned": len(room_nos) >= max(1, int(od.rooms or 1)),
            }
        )

    day_panels = []
    for i in range(days):
        d = start + timedelta(days=i)
        sold, available, blocked = [], [], []
        for n in by_day.get(d, []):
            meta = room_meta.get(n.room_id)
            if not meta:
                continue
            cell = {
                "id": n.room_id,
                "room_no": meta["room_no"],
                "room_type_name": meta["room_type_name"],
                "status": meta["room_status"],
                "inventory_status": n.status,
                "guest_name": n.guest_name,
                "order_no": n.order_no,
                "order_status": None,
                "source": n.source,
                "check_in": n.check_in.isoformat() if n.check_in else None,
                "check_out": n.check_out.isoformat() if n.check_out else None,
            }
            if n.status == "sold":
                sold.append(cell)
            elif n.status == "blocked":
                cell["reason"] = t("停用/维修")
                blocked.append(cell)
            else:
                available.append(cell)

        sold.sort(key=lambda x: x["room_no"])
        available.sort(key=lambda x: x["room_no"])
        blocked.sort(key=lambda x: x["room_no"])
        day_panels.append(
            {
                "date": d.isoformat(),
                "label": _date_label(d),
                "label_short": f"{d.year}-{d.month:02d}-{d.day:02d}",
                "weekday": _weekday_label(d),
                "is_today": d == start,
                "sold_count": len(sold),
                "available_count": len(available),
                "blocked_count": len(blocked),
                "sold": sold,
                "available": available,
                "blocked": blocked,
            }
        )

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "room_total": len(room_meta),
        "days": day_panels,
        "unassigned_orders": unassigned_summary,
        "table": "room_night_inventory",
        "note": "",
    }


def build_inventory_forecast_day_detail(db: Session, hotel_id: int, biz_date: Optional[str] = None):
    """高压日下钻：房型 × 日 已售/可售明细。"""
    from bootstrap.ensure_room_inventory import ensure_hotel_nights

    try:
        d = date.fromisoformat(str(biz_date)[:10])
    except ValueError:
        raise ValidationError("biz_date 无效")

    today = date.today()
    mat_start = min(today, d)
    ensure_hotel_nights(db, hotel_id, (d - mat_start).days + 1, start=mat_start)

    room_rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id)
        .all()
    )
    room_type_name = {r.id: (rt.name if rt else "客房") for r, rt in room_rows}

    nights = (
        db.query(RoomNightInventory)
        .filter(RoomNightInventory.hotel_id == hotel_id, RoomNightInventory.biz_date == d)
        .all()
    )
    by_type: dict = {}
    for n in nights:
        tname = room_type_name.get(n.room_id, "客房")
        bag = by_type.setdefault(tname, {"sold": 0, "available": 0, "blocked": 0})
        st = (n.status or "").lower()
        if st == "sold":
            bag["sold"] += 1
        elif st == "blocked":
            bag["blocked"] += 1
        else:
            bag["available"] += 1

    items = []
    for name, bag in sorted(by_type.items(), key=lambda x: -x[1]["sold"]):
        sellable = max(1, bag["sold"] + bag["available"])
        pct = min(100, round(100 * bag["sold"] / sellable))
        items.append(
            {
                "room_type_name": name,
                "sold": bag["sold"],
                "available": bag["available"],
                "blocked": bag["blocked"],
                "sellable": sellable,
                "booked_pct": pct,
                "heat": "high" if pct >= 81 else ("med" if pct >= 41 else "low"),
                "sold_out": bag["available"] == 0 and bag["sold"] > 0,
            }
        )
    items.sort(key=lambda x: (-(1 if x["sold_out"] else 0), -x["booked_pct"]))

    return {
        "biz_date": d.isoformat(),
        "label": f"{d.year}年{d.month}月{d.day}日",
        "items": items,
    }
