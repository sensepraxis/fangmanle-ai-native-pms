# SPDX-License-Identifier: Apache-2.0
"""会员体系 / 积分规则：扩展列 + 默认规则种子。

会员等级 / 积分规则默认已抽到 `mkt.level_config`；本文件保留 schema 保活与种子函数。
"""

from __future__ import annotations

import json

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from mkt.level_config import (
    DEFAULT_BENEFITS,
    DEFAULT_GROWTH,
    DEFAULT_LEVEL_RULE,
    DEFAULT_POINT_RULE,
    LEVEL_SPECS,
)
from models import HotelMktSettings, MktMemberLevel, MktStoredValuePlan


def _add_col(conn, insp, table: str, col: str, ddl: str) -> None:
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_member_system_schema(engine) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for col, ddl in [
            ("color_hex", "color_hex VARCHAR(8)"),
            ("upgrade_points", "upgrade_points INTEGER DEFAULT 0"),
            ("retain_points", "retain_points INTEGER DEFAULT 0"),
            ("valid_months", "valid_months INTEGER DEFAULT 24"),
            ("growth_rule_json", "growth_rule_json TEXT"),
        ]:
            _add_col(conn, insp, "mkt_member_levels", col, ddl)
        for col, ddl in [
            ("tier_name", "tier_name VARCHAR(64)"),
            ("gift_points", "gift_points INTEGER DEFAULT 0"),
            ("first_time_only", "first_time_only INTEGER DEFAULT 0"),
            ("payment_methods_json", "payment_methods_json TEXT"),
        ]:
            _add_col(conn, insp, "mkt_stored_value_plans", col, ddl)
        _add_col(conn, insp, "hotel_mkt_settings", "level_rule_json", "level_rule_json TEXT")


def seed_member_system(db: Session, hotel_id: int = 1) -> dict:
    from seed.locale_pack import seed_text as _st

    created = {"levels": 0, "plans": 0}
    for code, name, _disp, color, up, retain, months, sort in LEVEL_SPECS:
        loc_name = _st(name)
        row = db.query(MktMemberLevel).filter_by(hotel_id=hotel_id, level_code=code).first()
        if not row:
            row = MktMemberLevel(
                hotel_id=hotel_id,
                level_code=code,
                level_name=loc_name,
                upgrade_type="growth",
                upgrade_value=up,
                retention_type="growth",
                retention_value=retain,
                benefits_json=json.dumps(DEFAULT_BENEFITS.get(code, {}), ensure_ascii=False),
                sort_order=sort,
                is_active=True,
            )
            db.add(row)
            created["levels"] += 1
        else:
            row.level_name = loc_name
        # 补齐扩展字段
        if hasattr(row, "color_hex"):
            row.color_hex = color
        if hasattr(row, "upgrade_points"):
            current = int(getattr(row, "upgrade_points", None) or row.upgrade_value or 0)
            # 旧 nights 阈值通常很小，迁移为成长值门槛
            if current < 100 and up >= 100:
                row.upgrade_points = up
                row.upgrade_value = up
                row.upgrade_type = "growth"
            elif current == 0:
                row.upgrade_points = up
                row.upgrade_value = up
        if hasattr(row, "retain_points"):
            cur_r = int(getattr(row, "retain_points", None) or row.retention_value or 0)
            if cur_r < 100 and retain >= 100:
                row.retain_points = retain
                row.retention_value = retain
                row.retention_type = "growth"
            elif cur_r == 0:
                row.retain_points = retain
                row.retention_value = retain
        if hasattr(row, "valid_months"):
            if row.valid_months is None:
                row.valid_months = months
        if hasattr(row, "growth_rule_json") and not row.growth_rule_json:
            row.growth_rule_json = json.dumps(DEFAULT_GROWTH, ensure_ascii=False)
        # 权益若仍是旧字符串数组，升级为结构化
        try:
            ben = json.loads(row.benefits_json or "[]")
        except Exception:
            ben = []
        if isinstance(ben, list):
            row.benefits_json = json.dumps(DEFAULT_BENEFITS.get(code, {}), ensure_ascii=False)

    # 储值档补 gift_points / tier_name
    plans = db.query(MktStoredValuePlan).filter_by(hotel_id=hotel_id).all()
    name_map = {1000: "入门档", 3000: "常规档", 5000: "推荐档", 20000: "企业档"}
    gift_pts = {1000: 500, 3000: 1500, 5000: 3000, 20000: 15000}
    if not any(float(p.recharge_amt or 0) >= 20000 for p in plans):
        db.add(
            MktStoredValuePlan(
                hotel_id=hotel_id,
                recharge_amt=20000,
                bonus_amt=3500,
                bonus_type="amount",
                sort_order=4,
                is_active=True,
            )
        )
        created["plans"] += 1
        db.flush()
        plans = db.query(MktStoredValuePlan).filter_by(hotel_id=hotel_id).all()
    for p in plans:
        amt = int(float(p.recharge_amt or 0))
        if hasattr(p, "tier_name") and not p.tier_name:
            p.tier_name = name_map.get(amt, f"储值¥{amt}")
        if hasattr(p, "gift_points") and not p.gift_points:
            p.gift_points = gift_pts.get(amt, 0)

    s = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    if not s:
        s = HotelMktSettings(hotel_id=hotel_id)
        db.add(s)
    if hasattr(s, "level_rule_json") and not s.level_rule_json:
        s.level_rule_json = json.dumps(DEFAULT_LEVEL_RULE, ensure_ascii=False)
    # 合并积分规则
    try:
        pts = json.loads(s.points_json or "{}")
    except Exception:
        pts = {}
    merged = {**DEFAULT_POINT_RULE, **(pts or {})}
    # 兼容旧字段
    if "spend_per_point" in pts and "base_rate" not in pts:
        merged["base_rate"] = pts.get("spend_per_point") or 1
    if "redeem_points_per_yuan" in pts and pts.get("points_per_yuan") is None:
        merged["points_per_yuan"] = pts.get("redeem_points_per_yuan") or 100
    s.points_json = json.dumps(merged, ensure_ascii=False)
    db.flush()
    return created
