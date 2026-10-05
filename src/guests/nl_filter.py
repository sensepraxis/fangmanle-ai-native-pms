# SPDX-License-Identifier: Apache-2.0
"""自然语言客群查询：从 orders + guests + guest_tags 拉取真实人群。

从原 `bootstrap.ensure_nl_segment` 抽离（除种子函数）；种子函数
`seed_nl_cancel_demo` 与 `ensure_business_tag` / `ensure_family_repeat_tags` /
`_assign_tag` 仍在 `bootstrap.ensure_nl_segment` 里。
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from infra.i18n import t
from models import (
    Channel,
    Guest,
    GuestTag,
    Hotel,
    Order,
    OrderItem,
    Room,
    RoomType,
    TagDefinition,
)

# 幂等标记：用固定 order_no 前缀
CANCEL_PREFIX = "ORD-NL-CX-"
STAY_PREFIX = "ORD-NL-ST-"


def parse_nl_to_filter(query: str) -> dict[str, Any]:
    """把白话解析成可执行的 FilterSpec（规则引擎，非 Mock 名单）。"""
    text = (query or "").strip()
    window_days = 90
    if re.search(r"近\s*一\s*年|去年|过去一年", text):
        window_days = 365
    elif re.search(r"近\s*半\s*年|六个月", text):
        window_days = 180
    elif re.search(r"近\s*三\s*个?\s*月|近\s*90\s*天|三个月", text):
        window_days = 90
    elif re.search(r"近\s*一\s*个?\s*月|近\s*30\s*天", text):
        window_days = 30

    order_status: list[str] = []
    if "取消" in text:
        order_status.append("cancelled")
    if re.search(r"未到|no[\s\-]?show|noshow", text, re.I):
        order_status.append("no_show")

    tag_codes_any: list[str] = []
    if re.search(r"商务|商旅", text):
        tag_codes_any.append("business")
    if re.search(r"亲子|孩子|儿童|家庭|带娃", text):
        tag_codes_any.append("family")
    if re.search(r"回头|复购|常客", text):
        tag_codes_any.append("repeat")
    if re.search(r"VIP|贵宾", text, re.I):
        tag_codes_any.append("vip")
    if re.search(r"高价值", text):
        tag_codes_any.append("high_value")

    min_stays = None
    m = re.search(r"(\d+)\s*次\s*以上", text)
    if m:
        min_stays = int(m.group(1))
    elif re.search(r"三次以上|3次以上", text):
        min_stays = 3

    min_nights = None
    m_n = re.search(r"(?:单次)?(?:入住|间夜)(?:时间|天数)?\s*(?:大于|超过|≥|>=|至少)\s*(\d+)\s*(?:天|晚)", text)
    if m_n:
        min_nights = int(m_n.group(1))
    else:
        m_n2 = re.search(r"(\d+)\s*(?:天|晚)\s*(?:以上|及以上)", text)
        if m_n2 and not re.search(r"次", text[max(0, m_n2.start() - 2) : m_n2.end() + 2]):
            # 排除「近90天」类时间窗短语
            prefix = text[max(0, m_n2.start() - 4) : m_n2.start()]
            if not re.search(r"近|过去|最近", prefix):
                min_nights = int(m_n2.group(1))

    require_children_orders = bool(re.search(r"孩子|儿童|亲子|带娃", text))
    prefer_high_floor = bool(re.search(r"高层|高楼层", text))
    weekend_bias = bool(re.search(r"周末", text))
    quiet_pref = bool(re.search(r"安静", text))

    return {
        "query": text,
        "window_days": window_days,
        "order_status": order_status,
        "tag_codes_any": tag_codes_any,
        "min_stays": min_stays,
        "min_nights": min_nights,
        "require_children_orders": require_children_orders,
        "prefer_high_floor": prefer_high_floor,
        "weekend_bias": weekend_bias,
        "quiet_pref": quiet_pref,
    }


def _since(days: int) -> date:
    return date.today() - timedelta(days=max(1, days))


def _guest_tags_map(db: Session, guest_ids: list[int]) -> dict[int, list[str]]:
    if not guest_ids:
        return {}
    rows = (
        db.query(GuestTag.guest_id, TagDefinition.code, TagDefinition.name)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id.in_(guest_ids))
        .all()
    )
    out: dict[int, list[str]] = {}
    for gid, code, name in rows:
        bag = out.setdefault(gid, [])
        label = name or code or ""
        if label and label not in bag:
            bag.append(label)
    return out


def _guest_tag_codes_map(db: Session, guest_ids: list[int]) -> dict[int, set[str]]:
    if not guest_ids:
        return {}
    rows = (
        db.query(GuestTag.guest_id, TagDefinition.code)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id.in_(guest_ids))
        .all()
    )
    out: dict[int, set[str]] = {}
    for gid, code in rows:
        out.setdefault(gid, set()).add((code or "").lower())
    return out


def _order_anchor(o: Order) -> date:
    """取消/行为时间：优先 created_at 日期，否则 check_in。"""
    if o.created_at:
        try:
            return o.created_at.date() if hasattr(o.created_at, "date") else date.fromisoformat(str(o.created_at)[:10])
        except Exception:
            pass
    return o.check_in


def _order_nights(o: Order) -> int:
    if o.nights is not None and int(o.nights) > 0:
        return int(o.nights)
    if o.check_in and o.check_out:
        return max(1, (o.check_out - o.check_in).days)
    return 1


def query_nl_guests(
    db: Session,
    hotel_id: int,
    query: str,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """真查库：按 FilterSpec 从 orders/guests/tags 筛人。

    返回 guests 列表 + filter_spec（可写入 segment.filter_rule）。
    若传入 spec，则跳过规则解析（由上游 LLM/规则统一产出）。
    """
    from mkt.segment_sql import filter_spec_to_sql

    if spec is None:
        spec = parse_nl_to_filter(query)
    else:
        # 保证 query 字段存在
        spec = {**spec, "query": spec.get("query") or query}
    # 展示用 SQL 不入库重复；入库前再剥掉
    display_sql = filter_spec_to_sql({k: v for k, v in spec.items() if k not in ("sql", "meaning", "expression")})
    spec = {**spec, "sql": display_sql}
    since = _since(int(spec["window_days"]))
    statuses = list(spec["order_status"] or [])

    # ---- 主路径：有取消/未到行为 ----
    matched_ids: list[int] = []
    meta: dict[int, dict[str, Any]] = {}
    stay_counts: dict[int, int] = {}

    if statuses:
        q = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.guest_id.isnot(None),
                Order.status.in_(statuses),
            )
            .all()
        )
        by_guest: dict[int, list[Order]] = {}
        for o in q:
            if _order_anchor(o) < since:
                continue
            by_guest.setdefault(int(o.guest_id), []).append(o)

        for gid, ols in by_guest.items():
            meta[gid] = {
                "cancel_count": len(ols),
                "last_cancel_at": max(_order_anchor(o) for o in ols).isoformat(),
                "hit_orders": [o.order_no for o in ols[:5]],
            }
        matched_ids = list(by_guest.keys())
    else:
        # 无取消意图：本店有过订单的客人作为候选池
        rows = db.query(Order.guest_id).filter(Order.hotel_id == hotel_id, Order.guest_id.isnot(None)).distinct().all()
        matched_ids = [int(gid) for (gid,) in rows if gid]

    if not matched_ids:
        return {
            "filter_spec": spec,
            "filter_rule": json.dumps(spec, ensure_ascii=False),
            "sql": spec.get("sql") or "",
            "match_count": 0,
            "guests": [],
            "link_note": t("订单通过 orders.guest_id 关联 guests.id（会员主档）"),
        }

    code_map = _guest_tag_codes_map(db, matched_ids)
    name_map = _guest_tags_map(db, matched_ids)
    need_tags = [c.lower() for c in (spec["tag_codes_any"] or [])]

    # 标签过滤：指定的每个标签 code 都必须命中
    if need_tags:
        need_set = set(need_tags)
        matched_ids = [gid for gid in matched_ids if need_set.issubset(code_map.get(gid, set()))]

    # 入住次数（实住）/ 单次间夜 / 其他订单维度
    min_stays = spec.get("min_stays")
    min_nights = spec.get("min_nights")
    stay_since = _since(365 if (spec["window_days"] or 90) >= 180 else int(spec["window_days"]))
    if matched_ids and (
        min_stays or min_nights or spec.get("require_children_orders") or spec.get("prefer_high_floor")
    ):
        stay_orders = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.guest_id.in_(matched_ids),
                Order.status.in_(["checked_out", "checked_in"]),
            )
            .all()
        )
        stay_counts = {}
        for o in stay_orders:
            if _order_anchor(o) < stay_since:
                continue
            stay_counts[int(o.guest_id)] = stay_counts.get(int(o.guest_id), 0) + 1

        if min_stays:
            matched_ids = [gid for gid in matched_ids if stay_counts.get(gid, 0) >= int(min_stays)]

        if min_nights:
            long_stay_gids: set[int] = set()
            for o in stay_orders:
                if _order_anchor(o) < stay_since:
                    continue
                if _order_nights(o) >= int(min_nights):
                    long_stay_gids.add(int(o.guest_id))
            matched_ids = [gid for gid in matched_ids if gid in long_stay_gids]

        if spec.get("require_children_orders"):
            child_gids = {int(o.guest_id) for o in stay_orders if int(o.children or 0) > 0}
            matched_ids = [gid for gid in matched_ids if gid in child_gids or "family" in code_map.get(gid, set())]

        if spec.get("prefer_high_floor"):
            from models import Reservation

            high_tag = {gid for gid, codes in code_map.items() if "pref_quiet_high_floor" in codes}
            high_room: set[int] = set()
            res_rows = (
                db.query(Reservation, Room, Order)
                .join(Order, Reservation.order_id == Order.id)
                .join(Room, Reservation.room_id == Room.id)
                .filter(Order.hotel_id == hotel_id, Order.guest_id.in_(matched_ids))
                .all()
            )
            for _res, rm, o in res_rows:
                floor = 0
                try:
                    floor = int(rm.floor) if rm.floor is not None else 0
                except Exception:
                    floor = 0
                rn = 0
                try:
                    rn = int(re.sub(r"\D", "", str(rm.room_no) or "0") or 0)
                except Exception:
                    rn = 0
                if floor >= 8 or rn >= 800:
                    high_room.add(int(o.guest_id))
            matched_ids = [gid for gid in matched_ids if gid in high_tag or gid in high_room]

    if spec.get("quiet_pref") and not spec.get("prefer_high_floor"):
        matched_ids = [
            gid
            for gid in matched_ids
            if "pref_quiet_high_floor" in code_map.get(gid, set()) or any("安静" in t for t in name_map.get(gid, []))
        ]

    guests = db.query(Guest).filter(Guest.id.in_(matched_ids)).all() if matched_ids else []
    guests.sort(key=lambda g: float(g.ltv or 0), reverse=True)

    out_rows = []
    for g in guests:
        m = meta.get(g.id, {})
        out_rows.append(
            {
                "id": g.id,
                "name": g.name,
                "phone": g.phone,
                "vip_level": g.vip_level,
                "ltv": float(g.ltv or 0),
                "one_id": g.one_id,
                "tags": name_map.get(g.id, []),
                "cancel_count": m.get("cancel_count"),
                "last_cancel_at": m.get("last_cancel_at"),
                "hit_orders": m.get("hit_orders") or [],
                "stay_count_window": stay_counts.get(g.id),
            }
        )

    # 入库用的 filter_rule：去掉展示字段，保留可复算条件
    persist_spec = {
        k: v
        for k, v in spec.items()
        if k
        not in (
            "sql",
            "meaning",
            "expression",
            "_intent_model",
            "_intent_provider",
        )
    }
    persist_spec["sql"] = display_sql  # 看成员页可直接展示确定性 SQL

    return {
        "filter_spec": {**persist_spec, "meaning": spec.get("meaning"), "expression": spec.get("expression")},
        "filter_rule": json.dumps(persist_spec, ensure_ascii=False),
        "sql": display_sql,
        "match_count": len(out_rows),
        "guests": out_rows,
        "link_note": t("判定归属：orders.guest_id = guests.id；本店范围：orders.hotel_id"),
    }
