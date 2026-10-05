# SPDX-License-Identifier: Apache-2.0
"""自动发券规则四表：建表 + 种子（权威稿 mkt_coupon_auto_rule*）。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models import (
    Base,
    MktCoupon,
    MktCouponAutoRule,
    MktCouponAutoRuleCoupon,
    MktCouponAutoRuleFilter,
    MktCouponAutoRuleTrigger,
    MktCouponGrantLog,
)


def auto_rule_msgid(rule: MktCouponAutoRule) -> str:
    """规则展示用中文 msgid（与 DB seed 后的 name 解耦）。"""
    from seed.locale_pack import seed_text as st

    name = (rule.name or "").strip()
    for spec in AUTO_RULE_SEED_SPECS:
        zh = spec["name"]
        en = spec.get("name_en") or zh
        if name in (zh, en, st(zh, en)):
            return zh
    return name


def _find_seed_rule(db: Session, hotel_id: int, spec: dict) -> MktCouponAutoRule | None:
    from seed.locale_pack import seed_text as st

    zh = spec["name"]
    en = spec.get("name_en") or zh
    labels = {zh, en, st(zh, en)}
    q = db.query(MktCouponAutoRule).filter_by(property_id=hotel_id)
    for row in q.all():
        if (row.name or "").strip() in labels:
            return row
    return None


AUTO_RULE_SEED_SPECS: list[dict] = []


def _add_col_if_missing(conn, insp, table: str, col: str, ddl: str) -> None:
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_auto_rules_schema(engine) -> None:
    Base.metadata.create_all(
        engine,
        tables=[
            MktCouponAutoRule.__table__,
            MktCouponAutoRuleCoupon.__table__,
            MktCouponAutoRuleFilter.__table__,
            MktCouponAutoRuleTrigger.__table__,
        ],
    )
    insp = inspect(engine)
    with engine.begin() as conn:
        _add_col_if_missing(conn, insp, "mkt_coupon_grant_logs", "auto_rule_id", "auto_rule_id INTEGER")


def seed_auto_rules_demo(db: Session, hotel_id: int = 1) -> dict:
    """种子：对齐原型示例规则（幂等）。"""
    coupons = {c.batch_no: c for c in db.query(MktCoupon).filter_by(hotel_id=hotel_id).all()}
    if not coupons:
        return {"auto_rules": 0}

    def batch(*keys: str) -> MktCoupon | None:
        for k in keys:
            if k in coupons:
                return coupons[k]
        return next(iter(coupons.values()), None)

    specs = [
        {
            "name": "新客首住欢迎礼",
            "name_en": "Welcome gift for new WeCom members",
            "description": "新客加入企微 · 1 张/人/天",
            "description_en": "New WeCom member · 1 coupon/guest/day",
            "event_type": "NEW_WECHAT_MEMBER",
            "event_params": {},
            "scan_frequency": "realtime",
            "status": "active",
            "max_per_customer_day": 1,
            "rule_cooldown_days": 9999,
            "global_silence_days": 7,
            "active_window_start": "09:00:00",
            "active_window_end": "21:00:00",
            "batches": ["COUPON-DEMO-70"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 1248,
            "last_hours": 0.03,
        },
        {
            "name": "注册满月礼",
            "name_en": "30-day registration gift",
            "description": "注册满 30 天 · 满减关怀",
            "description_en": "Registered 30 days · discount care",
            "event_type": "REG_DAYS",
            "event_params": {"reg_days": 30},
            "scan_frequency": "daily",
            "status": "active",
            "batches": ["COUPON-DEMO-REG30"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
                {"group_id": 1, "field": "registered_days", "op": "=", "value_json": {"v": 30}},
            ],
            "trigger_count_7d": 892,
            "last_hours": 1,
        },
        {
            "name": "退房 7 天召回",
            "name_en": "7-day post-checkout recall",
            "description": "退房后 7 天 · 满减券",
            "description_en": "7 days after checkout · discount coupon",
            "event_type": "CHECKOUT_DAYS",
            "event_params": {"checkout_days": 7},
            "scan_frequency": "daily",
            "status": "active",
            "batches": ["COUPON-DEMO-CO7"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
                {"group_id": 1, "field": "last_stay_days", "op": "=", "value_json": {"v": 7}},
            ],
            "trigger_count_7d": 624,
            "last_hours": 1,
        },
        {
            "name": "沉睡 60 天唤醒",
            "name_en": "60-day dormant wake-up",
            "description": "沉默 60 天 · 唤醒券",
            "description_en": "Silent 60 days · wake-up coupon",
            "event_type": "SILENT_DAYS",
            "event_params": {"silent_days": 60},
            "scan_frequency": "daily",
            "status": "active",
            "batches": ["COUPON-DEMO-REG100"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
                {"group_id": 1, "field": "last_stay_days", "op": ">=", "value_json": {"v": 60}},
            ],
            "trigger_count_7d": 418,
            "last_hours": 3,
        },
        {
            "name": "国庆双倍券",
            "name_en": "National Day double coupon",
            "description": "HOLIDAY national_day",
            "description_en": "HOLIDAY national_day",
            "event_type": "HOLIDAY",
            "event_params": {"holiday": "national_day"},
            "scan_frequency": "daily",
            "status": "active",
            "batches": ["COUPON-DEMO-70"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 0,
            "last_hours": None,
        },
        {
            "name": "生日礼提前 7 天",
            "name_en": "Birthday gift 7 days ahead",
            "description": "BIRTHDAY · 权益券",
            "description_en": "BIRTHDAY · benefit coupon",
            "event_type": "BIRTHDAY",
            "event_params": {"ahead_days": 7},
            "scan_frequency": "daily",
            "status": "paused",
            "batches": ["COUPON-DEMO-REG30"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 312,
            "last_hours": 24,
        },
        {
            "name": "高价值新客专属礼",
            "name_en": "High-value new guest exclusive",
            "description": "首住单价 ≥ 600 · 升房券",
            "description_en": "First stay avg ≥ ¥600 · room upgrade",
            "event_type": "HIGH_VALUE_NEW",
            "event_params": {"min_avg_order": 600},
            "scan_frequency": "daily",
            "status": "active",
            "batches": ["COUPON-DEMO-70"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
                {"group_id": 1, "field": "avg_order_value", "op": ">=", "value_json": {"v": 600}},
                {"group_id": 1, "field": "stay_records", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 148,
            "last_hours": 4,
        },
        {
            "name": "自定义事件 · API 触发",
            "name_en": "Custom event · API trigger",
            "description": "连住达标 · API",
            "description_en": "Multi-night stay · API",
            "event_type": "CUSTOM",
            "event_params": {"event_key": "stay_completed"},
            "scan_frequency": "realtime",
            "status": "draft",
            "batches": ["COUPON-DEMO-REG100"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 0,
            "last_hours": None,
        },
        {
            "name": "PMS 退房即送",
            "name_en": "PMS instant checkout grant",
            "description": "退房即触发",
            "description_en": "Triggers on checkout",
            "event_type": "PMS_EVENT",
            "event_params": {"pms_event": "checkout_completed", "offset_days": 0},
            "scan_frequency": "realtime",
            "status": "draft",
            "batches": ["COUPON-DEMO-CO7"],
            "filters": [
                {"group_id": 1, "field": "channel_reachable", "op": "=", "value_json": {"v": 1}},
            ],
            "trigger_count_7d": 0,
            "last_hours": None,
        },
    ]

    global AUTO_RULE_SEED_SPECS
    AUTO_RULE_SEED_SPECS = specs

    from seed.locale_pack import seed_text as st

    created = 0
    now = datetime.now()
    for spec in specs:
        zh = spec["name"]
        en = spec.get("name_en") or zh
        display_name = st(zh, en)
        desc_zh = spec.get("description")
        desc_en = spec.get("description_en")
        display_desc = st(desc_zh, desc_en) if desc_zh else None

        row = _find_seed_rule(db, hotel_id, spec)
        if row:
            row.name = display_name
            if display_desc is not None:
                row.description = display_desc
            continue
        last_at = None
        if spec.get("last_hours") is not None:
            last_at = now - timedelta(hours=float(spec["last_hours"]))
        row = MktCouponAutoRule(
            property_id=hotel_id,
            name=display_name,
            description=display_desc,
            event_type=spec["event_type"],
            event_params=json.dumps(spec.get("event_params") or {}, ensure_ascii=False),
            scan_frequency=spec.get("scan_frequency") or "daily",
            max_per_customer_day=spec.get("max_per_customer_day", 1),
            rule_cooldown_days=spec.get("rule_cooldown_days", 30),
            global_silence_days=spec.get("global_silence_days", 7),
            active_window_start=spec.get("active_window_start", "09:00:00"),
            active_window_end=spec.get("active_window_end", "21:00:00"),
            push_channel="wecom",
            status=spec.get("status") or "draft",
            last_triggered_at=last_at,
            trigger_count_7d=int(spec.get("trigger_count_7d") or 0),
            created_by="seed",
            updated_by="seed",
        )
        db.add(row)
        db.flush()
        prio = 1
        for bno in spec.get("batches") or []:
            c = batch(bno)
            if not c:
                continue
            db.add(MktCouponAutoRuleCoupon(rule_id=row.id, batch_id=c.id, priority=prio))
            prio += 1
        for i, f in enumerate(spec.get("filters") or []):
            db.add(
                MktCouponAutoRuleFilter(
                    rule_id=row.id,
                    group_id=int(f.get("group_id") or 1),
                    field=f["field"],
                    op=f["op"],
                    value_json=json.dumps(f.get("value_json") or {}, ensure_ascii=False),
                    sort_order=i,
                )
            )
        created += 1

    db.flush()
    return {"auto_rules": created}
