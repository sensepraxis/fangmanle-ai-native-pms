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
from models import Campaign, Channel, ChannelAttribution, Guest, Order, RoomType

# models.__all__ 未覆盖全部 ORM（如 SupplyAlert）；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})


def order_source_group(ch: Optional[Channel], nights: Optional[int] = None) -> str:
    from orders.channel_config import source_group_for

    return source_group_for(ch, nights)


def compose_orders_attribution(db: Session, hotel_id: int, days: int = 7) -> dict:
    """订单渠道归因聚合（不含 LLM）。"""
    from orders.attribution_config import SOURCE_LABEL

    today = date.today()
    d0 = today - timedelta(days=max(0, days - 1))
    prev0 = d0 - timedelta(days=days)
    prev1 = d0 - timedelta(days=1)

    channels = {c.id: c for c in db.query(Channel).all()}

    attrs = (
        db.query(ChannelAttribution)
        .filter(
            ChannelAttribution.hotel_id == hotel_id,
            ChannelAttribution.created_at >= datetime.combine(d0, datetime.min.time()),
        )
        .all()
    )
    # created_at 可能为空：回退用 order.check_in
    if not attrs:
        attrs = db.query(ChannelAttribution).filter_by(hotel_id=hotel_id).all()

    orders = db.query(Order).filter_by(hotel_id=hotel_id).all()
    order_map = {o.id: o for o in orders}

    def in_win(o: Optional[Order]) -> bool:
        if not o or not o.check_in:
            return False
        return d0 <= o.check_in <= today

    def in_prev(o: Optional[Order]) -> bool:
        if not o or not o.check_in:
            return False
        return prev0 <= o.check_in <= prev1

    win_attrs = []
    for a in attrs:
        o = order_map.get(a.order_id) if a.order_id else None
        if o and in_win(o):
            win_attrs.append(a)
        elif not o and a.created_at and d0 <= a.created_at.date() <= today:
            win_attrs.append(a)
    if not win_attrs:
        win_attrs = list(attrs)

    # ---- 首触点分布（归因 source，按量取 Top）----
    touch_cnt: dict[str, float] = {}
    for a in win_attrs:
        src = (a.source or "other").lower()
        touch_cnt[src] = touch_cnt.get(src, 0) + 1
    # 若归因空，用窗口内订单成单渠道兜底为首触
    if not touch_cnt:
        for o in orders:
            if not in_win(o):
                continue
            ch = channels.get(o.channel_id)
            code = (ch.code if ch else "other") or "other"
            touch_cnt[code] = touch_cnt.get(code, 0) + 1

    from infra.i18n import t as _t

    TOUCH_META = {
        "xiaohongshu": {"label": "小红书", "short": "小", "tone": "red"},
        "douyin": {"label": "抖音", "short": "抖", "tone": "blue"},
        "ota": {"label": "OTA", "short": None, "tone": "orange", "icon": "travel_explore"},
        "wechat": {"label": "企微/微信", "short": "微", "tone": "green", "icon": "chat"},
        "wecom": {"label": "企微直订", "short": "企", "tone": "green", "icon": "chat"},
        "direct": {"label": "散客直订", "short": "直", "tone": "blue"},
        "meituan": {"label": "美团", "short": "美", "tone": "orange"},
        "ctrip": {"label": "携程", "short": "携", "tone": "orange"},
        "fliggy": {"label": "飞猪", "short": "飞", "tone": "orange"},
    }

    def touch_meta(code: str) -> dict:
        m = TOUCH_META.get(code)
        if m:
            out = dict(m)
            out["label"] = _t(str(m["label"]))
            return out
        # 尝试用渠道表名称
        for ch in channels.values():
            if (ch.code or "").lower() == code:
                raw = ch.name or code
                return {"label": _t(str(raw)), "short": (ch.name or code)[:1], "tone": "blue"}
        return {"label": SOURCE_LABEL.get(code, code), "short": code[:1], "tone": "blue"}

    touch_total = sum(touch_cnt.values()) or 1
    first_touch = []
    for code, n in sorted(touch_cnt.items(), key=lambda x: -x[1])[:5]:
        if n <= 0:
            continue
        meta = touch_meta(code)
        first_touch.append(
            {
                "code": code,
                "label": meta["label"],
                "short": meta.get("short"),
                "icon": meta.get("icon"),
                "tone": meta.get("tone") or "blue",
                "count": int(n),
                "pct": round(100.0 * n / touch_total, 0),
            }
        )

    # ---- 成单承接：有归因且「首触 ≠ 成单渠道」的订单，按成单渠道聚合 ----
    mid_cnt: dict[str, int] = {}
    assisted_order_ids: set[int] = set()
    for a in win_attrs:
        if not a.order_id:
            continue
        o = order_map.get(a.order_id)
        if not o or not in_win(o) or (o.status or "") == "cancelled":
            continue
        ch = channels.get(o.channel_id)
        book = ((ch.code if ch else "") or "").lower()
        src = (a.source or "").lower()
        if not book:
            continue
        if src and src != book:
            mid_cnt[book] = mid_cnt.get(book, 0) + 1
            assisted_order_ids.add(o.id)
        elif not src:
            mid_cnt[book] = mid_cnt.get(book, 0) + 1
            assisted_order_ids.add(o.id)

    mid_total = sum(mid_cnt.values()) or 1
    mid_touch = []
    for code, n in sorted(mid_cnt.items(), key=lambda x: -x[1])[:4]:
        meta = touch_meta(code)
        mid_touch.append(
            {
                "code": code,
                "label": meta["label"],
                "short": meta.get("short"),
                "icon": meta.get("icon") or "storefront",
                "tone": meta.get("tone") or "blue",
                "count": int(n),
                "pct": round(100.0 * n / mid_total, 0),
            }
        )

    # ---- 最终转化：窗口内未取消成单（按成单渠道汇总 Top）----
    book_cnt: dict[str, int] = {}
    for o in orders:
        if not in_win(o) or (o.status or "") == "cancelled":
            continue
        ch = channels.get(o.channel_id)
        code = ((ch.code if ch else "other") or "other").lower()
        book_cnt[code] = book_cnt.get(code, 0) + 1
    conv_count = sum(book_cnt.values())
    top_book = max(book_cnt.items(), key=lambda x: x[1]) if book_cnt else ("direct", 0)
    conv_label = touch_meta(top_book[0])["label"]
    if len(book_cnt) > 1:
        conv_label = f"全渠道成单（主：{conv_label}）"

    # 微信/直销转化率 KPI（保留原口径）
    conv_codes = {"wechat", "direct", "wecom"}
    wechat_like = sum(book_cnt.get(c, 0) for c in conv_codes)
    win_n = conv_count or 1
    wechat_rate = round(100.0 * wechat_like / win_n, 1)

    prev_book = 0
    prev_wechat = 0
    for o in orders:
        if not in_prev(o) or (o.status or "") == "cancelled":
            continue
        prev_book += 1
        ch = channels.get(o.channel_id)
        code = ((ch.code if ch else "") or "").lower()
        if code in conv_codes:
            prev_wechat += 1
    prev_n = prev_book or 1
    wechat_rate_prev = 100.0 * prev_wechat / prev_n
    wechat_delta = round(wechat_rate - wechat_rate_prev, 1)

    # ---- Campaign KPI：小红书 ROI · CAC ----
    camps = db.query(Campaign).filter_by(hotel_id=hotel_id).all()
    xhs = [c for c in camps if (c.channel or "") == "xiaohongshu"]
    xhs_roi = float(xhs[0].roi) if xhs and xhs[0].roi is not None else None
    if xhs_roi is None and xhs:
        sp = float(xhs[0].spend or 0) or 1
        xhs_roi = round(float(xhs[0].attributed_rev or 0) / sp, 1)
    if xhs_roi is None:
        xhs_spend = sum(float(c.spend or 0) for c in camps if (c.channel or "") == "xiaohongshu")
        xhs_rev = sum(float(a.attributed_rev or 0) for a in win_attrs if (a.source or "") == "xiaohongshu")
        xhs_roi = round(xhs_rev / xhs_spend, 1) if xhs_spend else 0.0

    total_spend = sum(
        float(c.spend or 0) for c in camps if (c.channel or "") in ("xiaohongshu", "douyin", "geo", "ota")
    )
    # 按活动跨度摊销到查询窗，避免 7 天窗 CAC 虚高
    spend_in_window = total_spend * (days / 30.0) if total_spend else 0.0
    cac_den = max(len({a.order_id for a in win_attrs if a.order_id}), conv_count, 1)
    cac = round(spend_in_window / cac_den, 2) if spend_in_window else 0.0

    # 环比：上期归因营收 / 摊销花费
    prev_attrs = []
    for a in attrs:
        o = order_map.get(a.order_id) if a.order_id else None
        if o and in_prev(o):
            prev_attrs.append(a)
        elif not o and a.created_at and prev0 <= a.created_at.date() <= prev1:
            prev_attrs.append(a)
    spend_prev = total_spend * (days / 30.0) if total_spend else 0.0
    xhs_rev_prev = sum(float(a.attributed_rev or 0) for a in prev_attrs if (a.source or "") == "xiaohongshu")
    xhs_roi_prev = (
        round(xhs_rev_prev / spend_prev, 1)
        if spend_prev and xhs_rev_prev
        else (
            round(
                xhs_rev_prev / (sum(float(c.spend or 0) for c in camps if (c.channel or "") == "xiaohongshu") or 1), 1
            )
            if xhs_rev_prev
            else 0.0
        )
    )
    if xhs_roi_prev > 0:
        roi_delta_pct = round(100.0 * (float(xhs_roi or 0) - xhs_roi_prev) / xhs_roi_prev, 1)
    else:
        roi_delta_pct = 0.0
    prev_cac_den = max(len({a.order_id for a in prev_attrs if a.order_id}), prev_wechat, 1)
    cac_prev = round(spend_prev / prev_cac_den, 2) if spend_prev else 0.0
    if cac_prev > 0:
        cac_delta_pct = round(100.0 * (cac - cac_prev) / cac_prev, 1)
    else:
        cac_delta_pct = 0.0

    # ---- 种草→成单路径排行（首触 source → 订单成单渠道）----
    path_agg: dict[tuple[str, str], dict] = {}
    for a in win_attrs:
        if not a.order_id:
            continue
        o = order_map.get(a.order_id)
        if not o or not in_win(o) or (o.status or "") == "cancelled":
            continue
        ch = channels.get(o.channel_id)
        book = ((ch.code if ch else "") or "other").lower()
        src = ((a.source or "") or book).lower()
        key = (src, book)
        bucket = path_agg.get(key)
        if not bucket:
            bucket = {"orders": 0, "revenue": 0.0}
            path_agg[key] = bucket
        bucket["orders"] += 1
        bucket["revenue"] += float(a.attributed_rev or o.total_amount or 0)

    attributed_n = sum(b["orders"] for b in path_agg.values())
    single_n = sum(b["orders"] for (s, bch), b in path_agg.items() if s == bch)
    cross_n = attributed_n - single_n
    path_den = attributed_n or 1
    path_summary = {
        "attributed_orders": attributed_n,
        "single_touch_orders": single_n,
        "cross_touch_orders": cross_n,
        "single_pct": round(100.0 * single_n / path_den, 0),
        "cross_pct": round(100.0 * cross_n / path_den, 0),
    }
    paths = []
    for (src, book), b in sorted(path_agg.items(), key=lambda x: -x[1]["orders"])[:10]:
        sm = touch_meta(src)
        bm = touch_meta(book)
        paths.append(
            {
                "from_code": src,
                "from_label": sm["label"],
                "from_tone": sm.get("tone") or "blue",
                "to_code": book,
                "to_label": bm["label"],
                "to_tone": bm.get("tone") or "green",
                "orders": int(b["orders"]),
                "revenue": round(float(b["revenue"]), 2),
                "single_touch": src == book,
                "pct": round(100.0 * b["orders"] / path_den, 0),
            }
        )

    top_path = paths[0] if paths else None
    if top_path:
        path_phrase = (
            f"{top_path['from_label']}→{top_path['to_label']}"
            if not top_path["single_touch"]
            else _t("{name}（同渠道）", name=top_path["from_label"])
        )
        insight = _t(
            "近 {days} 天有归因成单 <strong>{n}</strong> 单："
            "单触点 <strong>{single}%</strong>，"
            "跨渠道 <strong>{cross}%</strong>；"
            "最常见路径 <strong>{path}</strong>（{orders} 单）。"
            "口径：归因首触 → 订单成单渠道。",
            days=days,
            n=attributed_n,
            single=int(path_summary["single_pct"]),
            cross=int(path_summary["cross_pct"]),
            path=path_phrase,
            orders=top_path["orders"],
        )
    else:
        insight = _t(
            "近 {days} 天窗口内暂无可用归因路径；成单合计 <strong>{n}</strong> 单。口径：归因表首触 → 订单成单渠道。",
            days=days,
            n=conv_count,
        )

    # ---- 高价值订单溯源 ----
    VIP = {"gold", "platinum", "diamond", "silver"}
    from infra.i18n import t
    from orders.attribution_config import path_chip_for
    from orders.channel_config import channel_display_name

    high_value = []
    ranked = sorted(
        [o for o in orders if (o.status or "") != "cancelled" and float(o.total_amount or 0) > 0],
        key=lambda x: float(x.total_amount or 0),
        reverse=True,
    )[:40]
    # 优先：有归因的高价值单
    attr_by_oid = {}
    for a in attrs:
        if a.order_id and a.order_id not in attr_by_oid:
            attr_by_oid[a.order_id] = a

    picked = []
    for o in ranked:
        if o.id in attr_by_oid:
            picked.append(o)
        if len(picked) >= 12:
            break
    if len(picked) < 8:
        for o in ranked:
            if o not in picked:
                picked.append(o)
            if len(picked) >= 12:
                break

    for o in picked[:10]:
        g = db.get(Guest, o.guest_id) if o.guest_id else None
        ch = channels.get(o.channel_id)
        a = attr_by_oid.get(o.id)
        first_src = (a.source if a else None) or (ch.code if ch else "direct")
        chip0 = path_chip_for(first_src, ch.name if ch else first_src)
        # 路径：首触 → 最终成单渠道（仅真实字段，不捏造中间触点）
        path = [dict(chip0)]
        final_code = ch.code if ch else None
        if final_code and final_code != first_src:
            path.append(path_chip_for(final_code, ch.name if ch else final_code))
        # 时长：仅用 created_at → check_in 真实差值
        hours = None
        if o.created_at and o.check_in:
            delta_h = (datetime.combine(o.check_in, datetime.min.time()) - o.created_at).total_seconds() / 3600
            if delta_h >= 0:
                hours = round(delta_h, 1)
        vip = (g.vip_level or "").lower() if g else ""
        guest_label = g.name if g else t("散客")
        if vip in VIP:
            guest_label = f"{guest_label} (VIP)"
        high_value.append(
            {
                "order_id": o.id,
                "order_no": o.order_no,
                "guest": guest_label,
                "amount": round(float(o.total_amount or 0), 2),
                "path": path,
                "hours_to_convert": hours,
                "first_touch": first_src,
                "channel": channel_display_name(ch.code, ch.name) if ch else "",
            }
        )

    return {
        "days": days,
        "window": {"from": d0.isoformat(), "to": today.isoformat()},
        "kpi": {
            "xhs_roi": round(float(xhs_roi or 0), 1),
            "xhs_roi_delta_pct": roi_delta_pct,
            "cac": cac,
            "cac_delta_pct": cac_delta_pct,
            "wechat_conv_rate": wechat_rate,
            "wechat_conv_delta": wechat_delta,
        },
        "insight_html": insight,
        "path_summary": path_summary,
        "paths": paths,
        "journey": {
            "first_touch": first_touch,
            "mid_touch": mid_touch,
            "consideration": {
                "label": "成单渠道承接",
                "assisted_orders": len(assisted_order_ids),
                "items": mid_touch,
            },
            "conversion": {
                "label": conv_label,
                "orders": conv_count,
            },
        },
        "high_value_orders": high_value,
    }


def compose_orders_channel_insight(
    db: Session,
    hotel_id: int,
    days: int = 30,
    room_type_id: Optional[int] = None,
) -> dict:
    """全渠道订单洞察聚合（不含 LLM）。"""
    from orders.channel_config import source_group_for

    today = date.today()
    d0 = today - timedelta(days=max(0, days - 1))
    prev0 = d0 - timedelta(days=days)
    prev1 = d0 - timedelta(days=1)

    channels = {c.id: c for c in db.query(Channel).all()}
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).order_by(RoomType.id).all()
    orders = db.query(Order).filter_by(hotel_id=hotel_id).all()
    if room_type_id:
        orders = [o for o in orders if o.room_type_id == room_type_id]

    CHURN = {"cancelled", "no_show"}
    CONVERTED = {"checked_in", "checked_out", "confirmed"}

    def in_win(o: Order) -> bool:
        return bool(o.check_in and d0 <= o.check_in <= today)

    def in_prev(o: Order) -> bool:
        return bool(o.check_in and prev0 <= o.check_in <= prev1)

    def is_channel_churn(o: Order) -> bool:
        st = o.status or ""
        if st == "cancelled":
            return True
        # 未到店仅计入入住日已过（本接口窗口已截止到 today，仍显式判断）
        return st == "no_show" and bool(o.check_in and o.check_in <= today)

    def tone_for(code: str, group: str) -> str:
        c = (code or "").lower()
        if c == "xiaohongshu":
            return "xhs"
        if c in ("douyin", "meituan_voucher") or group == "voucher":
            return "douyin"
        if group == "ota" or c in ("ota", "ctrip", "meituan", "fliggy"):
            return "ota"
        return "direct"

    def trend_bucket(code: str, group: str) -> str:
        c = (code or "").lower()
        if c == "xiaohongshu":
            return "xhs"
        if c in ("douyin", "meituan_voucher") or group == "voucher":
            return "douyin"
        if group == "ota" or c in ("ota", "ctrip", "meituan", "fliggy"):
            return "ota"
        return "direct"

    # ---- 按渠道聚合（入住日落在窗口）----
    win_orders = [o for o in orders if in_win(o)]
    prev_orders = [o for o in orders if in_prev(o)]

    def agg_by_channel(order_list: list) -> dict:
        out: dict = {}
        for o in order_list:
            ch = channels.get(o.channel_id)
            key = ch.id if ch else 0
            if key not in out:
                from infra.i18n import t as _t
                from orders.channel_config import channel_display_name

                name = channel_display_name(ch.code, ch.name) if ch else _t("未标注")
                code = ch.code if ch else "other"
                group = source_group_for(ch, int(o.nights or 0)) if ch else "direct"
                out[key] = {
                    "id": str(key or "x"),
                    "channel_id": key or None,
                    "label": name,
                    "channel": name,
                    "code": code,
                    "group": group,
                    "tone": tone_for(code, group),
                    "bookings": 0,
                    "converted": 0,
                    "churn": 0,
                    "revenue": 0.0,
                    "room_nights": 0,
                }
            st = out[key]
            st["bookings"] += 1
            nights = max(1, int(o.nights or 1)) * max(1, int(o.rooms or 1))
            st["room_nights"] += nights
            # 渠道 ADR 用客房收入，不含 other_amount（餐饮/会议等）
            st["revenue"] += max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
            status = o.status or ""
            if is_channel_churn(o):
                st["churn"] += 1
            elif status in CONVERTED:
                st["converted"] += 1
        return out

    cur_agg = agg_by_channel(win_orders)
    prev_agg = agg_by_channel(prev_orders)

    adrs = []
    for st in cur_agg.values():
        rn = st["room_nights"] or 1
        st["adr"] = round(st["revenue"] / rn, 2)
        bn = st["bookings"] or 1
        st["conv_rate"] = round(100.0 * st["converted"] / bn, 1)
        st["cancel_rate"] = round(100.0 * st["churn"] / bn, 1)
        adrs.append(st["adr"])

    adr_min = min(adrs) if adrs else 0
    adr_max = max(adrs) if adrs else 1
    adr_span = max(adr_max - adr_min, 1.0)
    max_bookings = max((st["bookings"] for st in cur_agg.values()), default=1)
    max_conv = max((st["conv_rate"] for st in cur_agg.values()), default=10)
    max_conv = max(max_conv, 5)

    bubbles = []
    matrix = []
    for st in sorted(cur_agg.values(), key=lambda x: -x["bookings"]):
        if st["bookings"] <= 0:
            continue
        price_idx = round(8 + 84 * (st["adr"] - adr_min) / adr_span, 1)
        vol = round(100.0 * st["bookings"] / max_bookings, 1)
        tip_adr = "高客单" if price_idx >= 66 else ("中客单" if price_idx >= 33 else "低客单")
        tip_cx = "高取消" if st["cancel_rate"] >= 25 else ("中取消" if st["cancel_rate"] >= 12 else "低取消")
        bubbles.append(
            {
                "id": st["id"],
                "channel": st["channel"],
                "tone": st["tone"],
                "price": price_idx,
                "conv": st["conv_rate"],
                "volume": vol,
                "label": st["label"],
                "bookings": st["bookings"],
                "adr": st["adr"],
            }
        )
        matrix.append(
            {
                "id": "m" + st["id"],
                "name": st["label"],
                "cancel": min(100.0, st["cancel_rate"] * 2.2),  # 拉伸到矩阵可读区间
                "cancel_rate": st["cancel_rate"],
                "adr": price_idx,
                "adr_value": st["adr"],
                "volume": vol,
                "tone": {
                    "direct": "#005bbf",
                    "xhs": "#8c33b3",
                    "douyin": "#ba1a1a",
                    "ota": "#79747e",
                }.get(st["tone"], "#005bbf"),
                "tip": f"{tip_adr} · {tip_cx} · {st['bookings']} 单",
                "bookings": st["bookings"],
            }
        )

    # ---- 近 N 天分桶趋势（按入住日）----
    day_list = []
    cur_d = d0
    while cur_d <= today:
        day_list.append(cur_d)
        cur_d += timedelta(days=1)

    by_day: dict = {d: {"direct": 0, "xhs": 0, "douyin": 0, "ota": 0} for d in day_list}
    for o in orders:
        if not o.check_in or o.check_in not in by_day:
            continue
        ch = channels.get(o.channel_id)
        code = ch.code if ch else ""
        group = source_group_for(ch, int(o.nights or 0)) if ch else "direct"
        bucket = trend_bucket(code, group)
        by_day[o.check_in][bucket] += max(1, int(o.rooms or 1)) * max(1, int(o.nights or 1))

    trend = []
    for d in day_list:
        b = by_day[d]
        total = b["direct"] + b["xhs"] + b["douyin"] + b["ota"]
        from infra.i18n import t as _t_day

        trend.append(
            {
                "date": d.isoformat(),
                "label": _t_day("{n}日", n=d.day),
                "direct": b["direct"],
                "xhs": b["xhs"],
                "douyin": b["douyin"],
                "ota": b["ota"],
                "total": total,
            }
        )

    # ---- AI 洞察：对比上期同长度窗 ----
    def channel_bookings(agg: dict, pred) -> int:
        return sum(st["bookings"] for st in agg.values() if pred(st))

    xhs_cur = channel_bookings(cur_agg, lambda s: s["tone"] == "xhs")
    xhs_prev = channel_bookings(prev_agg, lambda s: s["tone"] == "xhs")
    ota_churn_cur = [st for st in cur_agg.values() if st["tone"] == "ota" and st["bookings"] >= 2]
    ota_churn_cur.sort(key=lambda s: -s["cancel_rate"])
    top_ota = ota_churn_cur[0] if ota_churn_cur else None

    if xhs_prev > 0:
        xhs_delta_pct = round(100.0 * (xhs_cur - xhs_prev) / xhs_prev, 0)
    else:
        xhs_delta_pct = 100.0 if xhs_cur else 0.0

    from infra.i18n import t as _t_ins

    insight_parts = []
    if xhs_cur or xhs_prev:
        direction = _t_ins("增长") if xhs_delta_pct >= 0 else _t_ins("下降")
        insight_parts.append(
            _t_ins(
                "近 {days} 天<strong>小红书</strong>渠道预订 {cur} 单，"
                "较上期{dir} <strong>{pct}%</strong>（上期 {prev} 单）。",
                days=days,
                cur=xhs_cur,
                dir=direction,
                pct=abs(int(xhs_delta_pct)),
                prev=xhs_prev,
            )
        )
    if top_ota:
        insight_parts.append(
            _t_ins(
                "<strong>{name}</strong> 取消/确认未到店率 <strong>{rate}%</strong>（{churn}/{bookings}）。",
                name=top_ota["label"],
                rate=top_ota["cancel_rate"],
                churn=top_ota["churn"],
                bookings=top_ota["bookings"],
            )
        )
        insight_parts.append(
            _t_ins(
                "建议核查 <strong>{name}</strong> 价差与退改政策，评估是否收紧配额。",
                name=top_ota["label"],
            )
        )
    if not insight_parts:
        insight_parts.append(_t_ins("近 {days} 天共 {n} 单有入住日落在窗口内。", days=days, n=len(win_orders)))
        insight_parts.append(_t_ins("建议继续观察各渠道 ADR 与取消结构，优先复核高取消渠道。"))
    # 价格敏感提示：找高转化+偏低价渠道
    elastic = sorted(
        [b for b in bubbles if b["bookings"] >= 3],
        key=lambda b: (-b["conv"], b["price"]),
    )
    if elastic:
        e0 = elastic[0]
        insight_parts.append(
            _t_ins(
                "转化表现较好的是 <strong>{name}</strong>（转化 {conv}% · ADR ¥{adr}）。",
                name=e0["label"],
                conv=e0["conv"],
                adr=f"{e0['adr']:.0f}",
            )
        )

    return {
        "days": days,
        "window": {"from": d0.isoformat(), "to": today.isoformat()},
        "room_types": [{"id": rt.id, "name": rt.name, "code": getattr(rt, "code", None)} for rt in room_types],
        "axes": {
            "max_conv": max_conv,
            "adr_min": adr_min,
            "adr_max": adr_max,
        },
        "bubbles": bubbles,
        "matrix": matrix,
        "trend": trend,
        "insight_html": " ".join(insight_parts),
        "kpi": {
            "bookings": len(win_orders),
            "channels": len(bubbles),
            "xhs_delta_pct": int(xhs_delta_pct),
            "xhs_bookings": xhs_cur,
        },
    }


def build_orders_board(db: Session, hotel_id: int):
    """订单中心看板：按来源计数 + 增强入口提示。"""
    from orders.channel_config import SOURCE_META

    meta = list(SOURCE_META)
    if "wechat" not in {m["key"] for m in meta}:
        meta.append({"key": "wechat", "label": "企微私域", "hint": "企业微信/私域顾问跟进成单"})

    channels = {c.id: c for c in db.query(Channel).all()}
    orders = db.query(Order).filter_by(hotel_id=hotel_id).all()
    counts = {m["key"]: 0 for m in meta}
    counts["all"] = len(orders)
    for o in orders:
        ch = channels.get(o.channel_id)
        nights = int(o.nights or 0)
        if int(getattr(o, "order_type", None) or 0) == 5 or getattr(o, "group_name", None):
            counts["group"] = counts.get("group", 0) + 1
            continue
        sg = order_source_group(ch, nights)
        if sg == "wechat" or (ch and ch.code in ("wechat", "wecom", "xiaohongshu")):
            counts["wechat"] = counts.get("wechat", 0) + 1
        elif sg in counts:
            counts[sg] += 1
    sources = [{**m, "count": counts.get(m["key"], 0)} for m in meta]
    return {
        "sources": sources,
        "total": counts["all"],
        "enhance": [
            {"key": "analytics", "label": "经营分析", "path": "/analytics"},
            {"key": "monitor", "label": "订单异常与流失预警", "path": "/analytics/order-health/churn-warning"},
            {"key": "insight", "label": "全渠道订单洞察", "path": "/analytics/channel-insight/omni"},
            {"key": "attribution", "label": "订单渠道归因分析", "path": "/analytics/marketing-attribution/path"},
        ],
    }


def build_orders_monitor(db: Session, hotel_id: int, range: str = "7d"):
    """订单异常与流失：转化/取消趋势 + KPI，基于 orders 真实聚合。"""
    from orders.channel_config import source_group_for

    range_key = (range or "7d").lower().strip()
    if range_key not in ("24h", "7d", "14d"):
        range_key = "7d"

    today = date.today()
    channels = {c.id: c for c in db.query(Channel).all()}
    orders = db.query(Order).filter_by(hotel_id=hotel_id).all()

    CHURN_STATUSES = {"cancelled", "no_show"}  # 仅作注释参考；真正流失见 is_churn
    CONVERTED = {"checked_in", "checked_out"}
    OPEN_BOOKING = {"pending", "confirmed"}

    def is_cancelled(o: Order) -> bool:
        return (o.status or "") == "cancelled"

    def is_confirmed_no_show(o: Order) -> bool:
        """确认未到店：已标记 no_show 且入住日已到/已过。未来入住日的预订不算流失。"""
        return (o.status or "") == "no_show" and bool(o.check_in and o.check_in <= today)

    def is_churn(o: Order) -> bool:
        """已流失 = 取消，或入住日过后的确认未到店。不含「还没住」的待到店。"""
        return is_cancelled(o) or is_confirmed_no_show(o)

    def is_awaiting(o: Order) -> bool:
        st = o.status or ""
        return bool(o.check_in and o.check_in > today and st in OPEN_BOOKING)

    def is_overdue(o: Order) -> bool:
        """逾期未办：入住日已过仍未入住，尚未标 no_show —— 风险，不算已流失。"""
        st = o.status or ""
        return bool(o.check_in and o.check_in < today and st in OPEN_BOOKING)

    def is_converted(o: Order) -> bool:
        return (o.status or "") in CONVERTED

    # ---- 时间窗：以入住日为轴，覆盖过去与临近未来（捕获远期取消）----
    if range_key == "24h":
        d0, d1 = today, today
    elif range_key == "14d":
        d0, d1 = today - timedelta(days=6), today + timedelta(days=7)
    else:  # 7d
        d0, d1 = today - timedelta(days=3), today + timedelta(days=3)

    days = []
    cur = d0
    while cur <= d1:
        days.append(cur)
        cur += timedelta(days=1)

    by_day = {d: {"bookings": 0, "converted": 0, "churn": 0, "pending": 0, "lost_amt": 0.0} for d in days}
    for o in orders:
        if not o.check_in or o.check_in not in by_day:
            continue
        b = by_day[o.check_in]
        b["bookings"] += 1
        amt = float(o.total_amount or 0)
        if is_churn(o):
            b["churn"] += 1
            b["lost_amt"] += amt
        elif is_converted(o):
            b["converted"] += 1
        elif is_awaiting(o) or is_overdue(o) or (o.status or "") in OPEN_BOOKING:
            # 待到店 / 逾期未办：计入 pending，不算流失
            b["pending"] += 1

    series = []
    for d in days:
        b = by_day[d]
        n = b["bookings"] or 0
        series.append(
            {
                "date": d.isoformat(),
                "label": f"{d.month}/{d.day}",
                "bookings": n,
                "converted": b["converted"],
                "churn": b["churn"],
                "pending": b["pending"],
                "lost_amt": round(b["lost_amt"], 2),
                "conv_rate": round(b["converted"] / n, 4) if n else 0,
                "churn_rate": round(b["churn"] / n, 4) if n else 0,
                "is_today": d == today,
            }
        )

    # 24h：按创建_at 小时桶（无则按 id 散列）补充小时粒度
    hourly = []
    if range_key == "24h":
        buckets = [{"hour": h, "bookings": 0, "churn": 0, "converted": 0} for h in range(24)]
        for o in orders:
            if o.check_in != today and not (o.created_at and o.created_at.date() == today):
                continue
            if o.created_at:
                h = int(o.created_at.hour)
            else:
                h = int(o.id or 0) % 24
            buckets[h]["bookings"] += 1
            if is_churn(o):
                buckets[h]["churn"] += 1
            elif is_converted(o):
                buckets[h]["converted"] += 1
        # 压缩为 8 个 3 小时桶，图更清晰
        for i in range(0, 24, 3):
            chunk = buckets[i : i + 3]
            hourly.append(
                {
                    "label": f"{i:02d}:00",
                    "bookings": sum(x["bookings"] for x in chunk),
                    "churn": sum(x["churn"] for x in chunk),
                    "converted": sum(x["converted"] for x in chunk),
                }
            )

    # ---- KPI：窗内 + 对比上一等长窗 ----
    win_orders = [o for o in orders if o.check_in and d0 <= o.check_in <= d1]
    span = (d1 - d0).days + 1
    prev0, prev1 = d0 - timedelta(days=span), d0 - timedelta(days=1)
    prev_orders = [o for o in orders if o.check_in and prev0 <= o.check_in <= prev1]

    cancelled_count = sum(1 for o in win_orders if is_cancelled(o))
    no_show_count = sum(1 for o in win_orders if is_confirmed_no_show(o))
    # cancel_count = 已确认流失合计（取消 + 入住日已过的未到店）；不含待到店
    cancel_count = cancelled_count + no_show_count
    cancel_prev = sum(1 for o in prev_orders if is_churn(o))
    lost_revenue = round(sum(float(o.total_amount or 0) for o in win_orders if is_churn(o)), 2)
    awaiting_count = sum(1 for o in win_orders if is_awaiting(o))
    overdue_count = sum(1 for o in win_orders if is_overdue(o))

    from finance.pay_risk import classify_near_pay_action

    prepaid_risk_n = 0
    collect_prep_n = 0
    for o in orders:
        act = classify_near_pay_action(o, channels.get(o.channel_id), today)
        if act == "remind_pay":
            prepaid_risk_n += 1
        elif act == "prep_collect":
            collect_prep_n += 1
    # 兼容旧字段：pay_risk_count = 应预付未到账·跟进
    pay_risk = prepaid_risk_n

    win_n = len(win_orders) or 1
    conv_n = sum(1 for o in win_orders if is_converted(o))
    pending_n = sum(1 for o in win_orders if (o.status or "") in OPEN_BOOKING)

    # ---- 渠道流失 ----
    from infra.i18n import t
    from orders.channel_config import channel_display_name

    ch_stat: dict = {}
    for o in orders:
        ch = channels.get(o.channel_id)
        sg = source_group_for(ch, int(o.nights or 0))
        name = channel_display_name(ch.code, ch.name) if ch else t("未标注")
        if name not in ch_stat:
            ch_stat[name] = {"channel": name, "source_group": sg, "bookings": 0, "churn": 0, "lost_amt": 0.0}
        ch_stat[name]["bookings"] += 1
        if is_churn(o):
            ch_stat[name]["churn"] += 1
            ch_stat[name]["lost_amt"] += float(o.total_amount or 0)
    channel_churn = []
    for v in ch_stat.values():
        if v["churn"] <= 0:
            continue
        bn = v["bookings"] or 1
        channel_churn.append(
            {
                **v,
                "lost_amt": round(v["lost_amt"], 2),
                "rate": round(v["churn"] / bn, 4),
            }
        )
    channel_churn.sort(key=lambda x: (-x["churn"], -x["lost_amt"]))

    # 取消原因：原为硬编码推断，已移除（无真实 cancel_reason 字段聚合）
    cancel_reasons: list = []

    # ---- 漏斗 ----
    funnel = {
        "bookings": len(win_orders),
        "pending": pending_n,
        "awaiting": awaiting_count,
        "overdue": overdue_count,
        "converted": conv_n,
        "cancelled": cancelled_count,
        "no_show": no_show_count,
        "churn": cancel_count,
        "in_house": sum(1 for o in win_orders if (o.status or "") == "checked_in"),
        "checked_out": sum(1 for o in win_orders if (o.status or "") == "checked_out"),
    }

    # ---- 滚动条文案：取近期已确认流失 ----
    ticker = []
    recent_churn = sorted(
        [o for o in orders if is_churn(o) and o.check_in],
        key=lambda x: x.check_in,
        reverse=True,
    )[:6]
    for o in recent_churn:
        ch = channels.get(o.channel_id)
        tag = t("确认未到店") if is_confirmed_no_show(o) else t("取消")
        ch_label = channel_display_name(ch.code, ch.name) if ch else t("渠道")
        ticker.append(
            {
                "time": o.check_in.isoformat() if o.check_in else "",
                "level": "error" if is_cancelled(o) else "warn",
                "text": f"{tag} {o.order_no} · {ch_label} · ¥{float(o.total_amount or 0):,.0f}",
            }
        )

    # ---- 风险单 Top：支付风险 / 逾期未办优先；确认流失次之（未来入住不算未到流失）----
    top_risk: list = []
    seen_ids: set = set()
    guest_ids = {o.guest_id for o in orders if o.guest_id}
    guest_name_by_id = (
        {g.id: (g.name or t("客人")) for g in db.query(Guest).filter(Guest.id.in_(guest_ids)).all()}
        if guest_ids
        else {}
    )

    def push_risk(o: Order, risk_type: str, risk_code: str, hint: str):
        if o.id in seen_ids or len(top_risk) >= 15:
            return
        seen_ids.add(o.id)
        ch = channels.get(o.channel_id)
        top_risk.append(
            {
                "id": o.id,
                "order_no": o.order_no,
                "guest": guest_name_by_id.get(o.guest_id) or t("客人"),
                "channel": channel_display_name(ch.code, ch.name) if ch else t("未标注"),
                "amount": round(float(o.total_amount or 0), 2),
                "check_in": o.check_in.isoformat() if o.check_in else "",
                "risk_type": t(risk_type),
                "risk_code": risk_code,
                "hint": t(hint),
            }
        )

    for o in sorted(
        [o for o in orders if classify_near_pay_action(o, channels.get(o.channel_id), today) == "remind_pay"],
        key=lambda x: (-float(x.total_amount or 0), x.check_in or today),
    ):
        push_risk(
            o,
            "预付跟进",
            "pay",
            "应预付/订金未到账 · 提醒付款或核对渠道到账",
        )

    for o in sorted(
        [o for o in orders if classify_near_pay_action(o, channels.get(o.channel_id), today) == "prep_collect"],
        key=lambda x: (-float(x.total_amount or 0), x.check_in or today),
    ):
        push_risk(
            o,
            "到店收款",
            "collect",
            "到店付口径 · 前台交接收款即可，无需催客人",
        )

    for o in sorted(
        [o for o in orders if is_overdue(o)],
        key=lambda x: (x.check_in or today, -float(x.total_amount or 0)),
    ):
        push_risk(o, "逾期未办", "overdue", "入住日已过仍未办入住 · 请确认是否标记未到店")

    for o in recent_churn:
        if is_confirmed_no_show(o):
            push_risk(o, "确认未到店", "no_show", "入住日已过且已标记未到店")
        else:
            push_risk(o, "已取消", "cancel", "已取消 · 建议跟进挽留策略")

    return {
        "range": range_key,
        "window": {"from": d0.isoformat(), "to": d1.isoformat()},
        "kpi": {
            "cancel_count": cancel_count,
            "cancelled_count": cancelled_count,
            "cancel_prev": cancel_prev,
            "cancel_delta": cancel_count - cancel_prev,
            "lost_revenue": lost_revenue,
            "pay_risk_count": pay_risk,
            "collect_prep_count": collect_prep_n,
            "no_show_count": no_show_count,
            "awaiting_count": awaiting_count,
            "overdue_count": overdue_count,
            "conversion_rate": round(conv_n / win_n, 4),
            "churn_rate": round(cancel_count / win_n, 4),
            "bookings": len(win_orders),
            "traffic_gap_pct": round(
                max(-0.6, min(0.2, (cancel_count / win_n) - 0.05)) * -100 if win_n else 0,
                1,
            ),
        },
        "series": series,
        "hourly": hourly,
        "channel_churn": channel_churn[:8],
        "cancel_reasons": cancel_reasons,
        "funnel": funnel,
        "ticker": ticker,
        "top_risk_orders": top_risk,
    }
