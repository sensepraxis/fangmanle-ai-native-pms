# SPDX-License-Identifier: Apache-2.0
"""
分群规则 → 确定性 SQL（无 LLM）。
支持：FilterSpec JSON、标签/指标 DSL、自然语言短语（规则解析）。
"""

from __future__ import annotations

import json
import re
from typing import Any


def _lit_list(vals: list[str]) -> str:
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in vals)


def _tag_exists(codes: list[str], alias: str = "gt") -> str:
    codes_sql = _lit_list(codes)
    return (
        f"EXISTS (\n"
        f"  SELECT 1 FROM guest_tags {alias}\n"
        f"  JOIN tag_definitions td ON td.id = {alias}.tag_id\n"
        f"  WHERE {alias}.guest_id = g.id AND td.code IN ({codes_sql})\n"
        f")"
    )


def _hotel_guest_scope(hotel: str = ":hotel_id") -> str:
    return f"EXISTS (\n  SELECT 1 FROM orders o0\n  WHERE o0.guest_id = g.id AND o0.hotel_id = {hotel}\n)"


def _min_nights_clause(min_n: int, days: int, hotel: str) -> str:
    return (
        f"EXISTS (\n"
        f"  SELECT 1 FROM orders sn\n"
        f"  WHERE sn.guest_id = g.id AND sn.hotel_id = {hotel}\n"
        f"    AND sn.status IN ('checked_out', 'checked_in')\n"
        f"    AND DATE(COALESCE(sn.created_at, sn.check_in)) >= DATE('now', '-{days} days')\n"
        f"    AND IFNULL(\n"
        f"      sn.nights,\n"
        f"      MAX(1, CAST(julianday(sn.check_out) - julianday(sn.check_in) AS INTEGER))\n"
        f"    ) >= {int(min_n)}\n"
        f")"
    )


def filter_spec_to_sql(spec: dict[str, Any], hotel: str = ":hotel_id") -> str:
    """NL FilterSpec → SQL。"""
    days = int(spec.get("window_days") or 90)
    statuses = list(spec.get("order_status") or [])
    tags = list(spec.get("tag_codes_any") or [])
    min_stays = spec.get("min_stays")
    min_nights = spec.get("min_nights")
    need_children = bool(spec.get("require_children_orders"))
    prefer_high = bool(spec.get("prefer_high_floor"))

    if statuses:
        where = [
            f"o.hotel_id = {hotel}",
            "o.guest_id IS NOT NULL",
            f"o.status IN ({_lit_list(statuses)})",
            f"DATE(COALESCE(o.created_at, o.check_in)) >= DATE('now', '-{days} days')",
        ]
        sql = (
            "SELECT DISTINCT g.id, g.name, g.one_id, g.ltv\n"
            "FROM guests g\n"
            "INNER JOIN orders o ON o.guest_id = g.id\n"
            "WHERE " + "\n  AND ".join(where)
        )
        if tags:
            sql += "\n  AND " + _tag_exists(tags).replace("\n", "\n  ")
        if min_stays:
            sql += (
                f"\n  AND (\n"
                f"    SELECT COUNT(*) FROM orders s\n"
                f"    WHERE s.guest_id = g.id AND s.hotel_id = {hotel}\n"
                f"      AND s.status IN ('checked_out', 'checked_in')\n"
                f"      AND DATE(COALESCE(s.created_at, s.check_in)) >= DATE('now', '-{days} days')\n"
                f"  ) >= {int(min_stays)}"
            )
        if min_nights:
            sql += "\n  AND " + _min_nights_clause(int(min_nights), days, hotel).replace("\n", "\n  ")
        if need_children:
            sql += (
                f"\n  AND (\n"
                f"    EXISTS (SELECT 1 FROM orders c WHERE c.guest_id = g.id AND c.hotel_id = {hotel} AND IFNULL(c.children,0) > 0)\n"
                f"    OR {_tag_exists(['family'], 'gt_fam')}\n"
                f"  )"
            )
        if prefer_high:
            sql += (
                f"\n  AND (\n"
                f"    {_tag_exists(['pref_quiet_high_floor'], 'gt_hf')}\n"
                f"    OR EXISTS (\n"
                f"      SELECT 1 FROM reservations r\n"
                f"      JOIN rooms rm ON rm.id = r.room_id\n"
                f"      JOIN orders ox ON ox.id = r.order_id\n"
                f"      WHERE ox.guest_id = g.id AND ox.hotel_id = {hotel}\n"
                f"        AND (IFNULL(rm.floor, 0) >= 8 OR CAST(rm.room_no AS INTEGER) >= 800)\n"
                f"    )\n"
                f"  )"
            )
        return sql

    # 无订单状态：本店客人 + 标签/次数条件
    where = [_hotel_guest_scope(hotel)]
    if tags:
        where.append(_tag_exists(tags))
    if min_stays:
        where.append(
            f"(\n"
            f"  SELECT COUNT(*) FROM orders s\n"
            f"  WHERE s.guest_id = g.id AND s.hotel_id = {hotel}\n"
            f"    AND s.status IN ('checked_out', 'checked_in')\n"
            f"    AND DATE(COALESCE(s.created_at, s.check_in)) >= DATE('now', '-{days} days')\n"
            f") >= {int(min_stays)}"
        )
    if min_nights:
        where.append(_min_nights_clause(int(min_nights), days, hotel))
    if need_children:
        where.append(
            f"(\n"
            f"  EXISTS (SELECT 1 FROM orders c WHERE c.guest_id = g.id AND c.hotel_id = {hotel} AND IFNULL(c.children,0) > 0)\n"
            f"  OR {_tag_exists(['family'], 'gt_fam')}\n"
            f")"
        )
    if prefer_high:
        where.append(
            f"(\n"
            f"  {_tag_exists(['pref_quiet_high_floor'], 'gt_hf')}\n"
            f"  OR EXISTS (\n"
            f"    SELECT 1 FROM reservations r\n"
            f"    JOIN rooms rm ON rm.id = r.room_id\n"
            f"    JOIN orders ox ON ox.id = r.order_id\n"
            f"    WHERE ox.guest_id = g.id AND ox.hotel_id = {hotel}\n"
            f"      AND (IFNULL(rm.floor, 0) >= 8 OR CAST(rm.room_no AS INTEGER) >= 800)\n"
            f"  )\n"
            f")"
        )

    return "SELECT g.id, g.name, g.one_id, g.ltv\nFROM guests g\nWHERE " + "\n  AND ".join(where)


def dsl_to_sql(rule: str, hotel: str = ":hotel_id") -> dict[str, Any] | None:
    """标签/指标 DSL → SQL + 语义。匹配 migrate_member_crm.match_rule。"""
    from infra.i18n import t as _t

    raw = (rule or "").strip()
    if not raw:
        return None
    r = raw.lower().replace(" ", "")
    bullets: list[str] = [_t("范围：本店有过订单的客人（orders.hotel_id）")]
    where = [_hotel_guest_scope(hotel)]

    if "ltv>5000" in r and "repeat" in r:
        where.append("IFNULL(g.ltv, 0) > 5000")
        where.append(_tag_exists(["repeat", "high_value"]))
        bullets = [
            _t("LTV（终身价值）> ¥5,000"),
            _t("且标签含「复购/回头」或「高价值」"),
            _t("范围：本店有过订单的客人"),
        ]
        meaning = _t("高价值复购客：LTV>5000 且带复购/高价值标签")
    elif r == "family" or (r.startswith("family") and "and" not in r):
        where.append(_tag_exists(["family"]))
        bullets = [_t("标签：亲子家庭（family）"), _t("范围：本店有过订单的客人")]
        meaning = _t("亲子家庭客：带有 family 标签")
    elif "churn" in r:
        where.append("IFNULL(g.churn_risk, 0) >= 0.7")
        bullets = [_t("流失风险 churn_risk ≥ 0.7"), _t("范围：本店有过订单的客人")]
        meaning = _t("高流失风险：churn_risk ≥ 0.7")
    elif r == "business" or ("business" in r and "ltv" not in r and "cancel" not in r):
        where.append(_tag_exists(["business"]))
        bullets = [_t("标签：商务常旅客（business）"), _t("范围：本店有过订单的客人")]
        meaning = _t("商务常旅客：带有 business 标签")
    elif r == "vip":
        where.append(
            f"(LOWER(IFNULL(g.vip_level,'')) IN ('silver','gold','platinum','diamond') OR {_tag_exists(['vip'])})"
        )
        bullets = [_t("会员等级 ∈ 银/金/白金/钻石，或带 VIP 标签"), _t("范围：本店有过订单的客人")]
        meaning = _t("VIP 会员：等级或 vip 标签")
    elif r == "new_guest" or "new_guest" in r:
        where.append("IFNULL(g.ltv, 0) < 800")
        where.append("LOWER(IFNULL(g.vip_level,'')) IN ('', 'normal')")
        bullets = [_t("近似本月新客：LTV < 800 且非 VIP"), _t("范围：本店有过订单的客人")]
        meaning = _t("本月新客（近似规则）")
    elif "high_intent" in r:
        where.append("IFNULL(g.ltv, 0) > 2000")
        where.append("IFNULL(g.churn_risk, 1) < 0.55")
        bullets = [_t("LTV > 2000 且流失风险 < 0.55"), _t("范围：本店有过订单的客人")]
        meaning = _t("高意向未转化")
    elif "repeat" in r:
        where.append(_tag_exists(["repeat"]))
        bullets = [_t("标签：复购客（repeat）"), _t("范围：本店有过订单的客人")]
        meaning = _t("复购客")
    else:
        return None

    sql = "SELECT g.id, g.name, g.one_id, g.ltv, g.vip_level, g.churn_risk\nFROM guests g\nWHERE " + "\n  AND ".join(
        where
    )
    return {
        "sql": sql,
        "meaning": meaning,
        "bullets": bullets,
        "source": "dsl",
        "dsl": raw,
    }


def rule_to_sql(rule: str | None, hotel: str = ":hotel_id") -> dict[str, Any]:
    """
    任意 filter_rule → { sql, meaning, bullets, source }。
    source: nl | dsl | snapshot | unknown
    """
    from infra.i18n import t as _t

    raw = (rule or "").strip()
    if not raw or raw == "—":
        return {
            "sql": (
                "SELECT g.id, g.name, g.one_id, g.ltv\n"
                "FROM guests g\n"
                "JOIN segment_members sm ON sm.guest_id = g.id\n"
                "WHERE sm.segment_id = :segment_id"
            ),
            "meaning": _t("无规则表达式：仅按分群已保存成员名单（segment_members）展示"),
            "bullets": [
                _t("下方列表 = 保存时写入的 guest_id，不是现场重算全库"),
                _t("关联：segment_members.guest_id = guests.id"),
            ],
            "source": "snapshot",
            "dsl": "",
        }

    # FilterSpec JSON
    if raw.startswith("{"):
        try:
            spec = json.loads(raw)
            if isinstance(spec, dict):
                sql = spec.get("sql") or filter_spec_to_sql(spec, hotel)
                bullets: list[str] = []
                if spec.get("window_days") and spec.get("order_status"):
                    bullets.append(_t("时间窗：近 {n} 天", n=spec.get("window_days")))
                st = spec.get("order_status") or []
                if st:
                    bullets.append(_t("订单状态：{s}", s=", ".join(st)))
                tags = spec.get("tag_codes_any") or []
                if tags:
                    bullets.append(_t("标签 code：{s}", s=" + ".join(tags)))
                if spec.get("min_stays"):
                    bullets.append(_t("实住次数 ≥ {n}", n=spec.get("min_stays")))
                if spec.get("min_nights"):
                    bullets.append(_t("单次入住间夜 ≥ {n}", n=spec.get("min_nights")))
                if spec.get("require_children_orders"):
                    bullets.append(_t("须有带儿童订单或亲子标签"))
                if spec.get("prefer_high_floor"):
                    bullets.append(_t("偏好高层房"))
                if spec.get("query"):
                    bullets.append(_t("原始描述：「{q}」", q=spec.get("query")))
                bullets.append(_t("关联：orders.guest_id = guests.id"))
                from infra.i18n import get_locale

                sep = "; " if str(get_locale() or "").lower().startswith("en") else "；"
                return {
                    "sql": sql,
                    "meaning": sep.join(bullets[:3]) if bullets else _t("自然语言条件已编译为 SQL"),
                    "bullets": bullets,
                    "source": "nl",
                    "dsl": json.dumps(
                        {k: v for k, v in spec.items() if k != "sql"},
                        ensure_ascii=False,
                    ),
                }
        except Exception:
            pass

    # 经典 DSL
    dsl_hit = dsl_to_sql(raw, hotel)
    if dsl_hit:
        return dsl_hit

    # 白话短语 → FilterSpec（规则引擎，非 LLM）
    from guests.nl_filter import parse_nl_to_filter

    if re.search(r"取消|近三|商务|亲子|回头|房客|住过|带孩|高层|安静|周末", raw):
        spec = parse_nl_to_filter(raw)
        sql = filter_spec_to_sql(spec, hotel)
        bullets = []
        if spec.get("order_status"):
            bullets.append(_t("时间窗：近 {n} 天", n=spec.get("window_days")))
            bullets.append(_t("订单状态：{s}", s=", ".join(spec["order_status"])))
        if spec.get("tag_codes_any"):
            bullets.append(_t("标签：{s}", s=" + ".join(spec["tag_codes_any"])))
        if not bullets:
            bullets.append(_t("按短语解析：{raw}", raw=raw))
        bullets.append(_t("关联：orders.guest_id = guests.id"))
        from infra.i18n import get_locale

        sep = "; " if str(get_locale() or "").lower().startswith("en") else "；"
        return {
            "sql": sql,
            "meaning": sep.join(bullets[:3]),
            "bullets": bullets,
            "source": "nl",
            "dsl": raw,
        }

    # 未知：仍给出成员快照 SQL，避免空白
    return {
        "sql": (
            "SELECT g.id, g.name, g.one_id, g.ltv\n"
            "FROM guests g\n"
            "JOIN segment_members sm ON sm.guest_id = g.id\n"
            "WHERE sm.segment_id = :segment_id\n"
            f"-- uncompiled rule: {raw[:80]}"
        ),
        "meaning": _t("规则「{raw}」暂无专用编译器，列表按已保存成员展示", raw=raw),
        "bullets": [
            _t("原始规则：{raw}", raw=raw),
            _t("展示名单来自 segment_members，非现场重算"),
        ],
        "source": "unknown",
        "dsl": raw,
    }
