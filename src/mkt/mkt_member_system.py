# SPDX-License-Identifier: Apache-2.0
"""会员体系 + 积分规则（规则侧）服务。

对齐架构稿 /api/mkt/member/*，在既有 mkt_member_levels / plans / settings 上扩展。
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from bootstrap.ensure_mkt_member_v2 import (
    DEFAULT_BENEFITS,
    DEFAULT_GROWTH,
    DEFAULT_LEVEL_RULE,
    DEFAULT_POINT_RULE,
    LEVEL_SPECS,
)
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.i18n import t as _t
from models import HotelMktSettings, MktGuestWallet, MktMemberLevel, MktStoredValuePlan

LEVEL_DISP = {c[0]: c[2] for c in LEVEL_SPECS}  # silver -> L1
LEVEL_ORDER = [c[0] for c in LEVEL_SPECS]


def _t_level_name(name: str | None) -> str:
    return _t(str(name or "")) if name else ""


def _localized_catalog() -> list[dict]:
    out = []
    for row in BENEFIT_CATALOG:
        item = dict(row)
        item["label"] = _t(item.get("label") or "")
        if item.get("unit"):
            item["unit"] = _t(str(item["unit"]))
        if item.get("hint"):
            item["hint"] = _t(str(item["hint"]))
        opts = []
        for o in item.get("options") or []:
            oo = dict(o)
            if oo.get("label"):
                oo["label"] = _t(str(oo["label"]))
            opts.append(oo)
        if opts:
            item["options"] = opts
        out.append(item)
    return out


def _localized_scenarios() -> list[dict]:
    return [{**s, "label": _t(s["label"])} for s in SCENARIOS]


def _localized_customers() -> list[dict]:
    return [{**c, "name": _t(c["name"])} for c in PREVIEW_CUSTOMERS]


BENEFIT_CATALOG = [
    {"key": "discount_rate", "label": "房费折扣", "unit": "倍率", "input": "number", "hint": "0.95=95折"},
    {"key": "free_breakfast", "label": "免费早餐", "unit": "份/日", "input": "number"},
    {
        "key": "upgrade_room",
        "label": "免费升房",
        "unit": "",
        "input": "select",
        "options": [
            {"value": "deluxe_to_exec", "label": "豪华→行政"},
            {"value": "any_one_level", "label": "任意升一级"},
            {"value": "suite_first", "label": "套房首选"},
        ],
    },
    {"key": "late_checkout", "label": "延迟退房", "unit": "小时", "input": "number"},
    {"key": "free_cancellation", "label": "免费取消窗口", "unit": "小时", "input": "number"},
    {"key": "welcome_fruit", "label": "迎宾果盘", "unit": "", "input": "bool"},
    {"key": "vip_lounge", "label": "行政酒廊", "unit": "", "input": "bool"},
    {
        "key": "dedicated_concierge",
        "label": "专属管家",
        "unit": "",
        "input": "select",
        "options": [
            {"value": "work_hours", "label": "工作时段"},
            {"value": "12h", "label": "12h"},
            {"value": "24h", "label": "24h"},
        ],
    },
    {"key": "points_acceleration", "label": "积分倍率加成", "unit": "X", "input": "number"},
    {
        "key": "birthday_gift",
        "label": "生日礼包",
        "unit": "",
        "input": "select",
        "options": [
            {"value": "points_1000", "label": "积分+1000"},
            {"value": "breakfast_coupon", "label": "免费早餐券"},
            {"value": "free_night", "label": "免费住1晚"},
        ],
    },
]

PREVIEW_CUSTOMERS = [
    {
        "id": "c_gold",
        "name": "王女士",
        "level": "gold",
        "current_points": 3200,
        "growth": 4200,
        "available_points": 3200,
    },
    {
        "id": "c_plat",
        "name": "李先生",
        "level": "platinum",
        "current_points": 12800,
        "growth": 12000,
        "available_points": 12800,
    },
    {"id": "c_sil", "name": "新客·赵", "level": "silver", "current_points": 80, "growth": 120, "available_points": 80},
]

SCENARIOS = [
    {
        "key": "BIRTHDAY_5X",
        "label": "生日入住 3 晚 ¥1800",
        "icon": "🎂",
        "params": {"amount": 1800, "nights": 3, "is_birthday_month": True},
    },
    {
        "key": "HOLIDAY",
        "label": "国庆 7 晚 ¥5500",
        "icon": "🎉",
        "params": {"amount": 5500, "nights": 7, "is_holiday": True},
    },
    {"key": "SPEND_1000", "label": "消费 ¥1000", "icon": "¥", "params": {"amount": 1000, "nights": 0}},
    {
        "key": "REVIEW_GOOD",
        "label": "首住 + 5 星好评",
        "icon": "⭐",
        "params": {"is_review": True, "is_first_review": True, "nights": 1},
    },
    {"key": "REFUND", "label": "退款 1000 元", "icon": "↩️", "params": {"refund_amount": 1000, "orig_points": 1500}},
    {"key": "EXPIRE", "label": "积分失效", "icon": "⌛", "params": {"expire_points": 300}},
]


def _jloads(raw: Any, default: Any = None):
    if default is None:
        default = {}
    if raw in (None, ""):
        return deepcopy(default)
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return deepcopy(default)


def _jdumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _settings(db: Session, hotel_id: int) -> HotelMktSettings:
    s = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    if not s:
        s = HotelMktSettings(hotel_id=hotel_id)
        db.add(s)
        db.flush()
    return s


def _level_dict(r: MktMemberLevel) -> dict:
    growth = _jloads(getattr(r, "growth_rule_json", None), DEFAULT_GROWTH)
    benefits = _jloads(r.benefits_json, {})
    if isinstance(benefits, list):
        benefits = {}
    up = int(getattr(r, "upgrade_points", None) or r.upgrade_value or 0)
    retain = int(getattr(r, "retain_points", None) or r.retention_value or 0)
    # 若扩展列尚未回填，用 LEVEL_SPECS 兜底数字
    spec = next((x for x in LEVEL_SPECS if x[0] == r.level_code), None)
    if spec and up < 100 and spec[4] >= 100:
        up = spec[4]
    if spec and retain < 100 and spec[5] >= 100:
        retain = spec[5]
    if not benefits and r.level_code:
        benefits = DEFAULT_BENEFITS.get(r.level_code, {})
    return {
        "id": r.id,
        "level_code": r.level_code,
        "level_disp": LEVEL_DISP.get(r.level_code, r.level_code.upper()),
        "level_name": _t_level_name(r.level_name),
        "color_hex": getattr(r, "color_hex", None) or (spec[3] if spec else "#64748b"),
        "upgrade_type": r.upgrade_type or "growth",
        "upgrade_value": up,
        "upgrade_points": up,
        "retention_type": r.retention_type or "growth",
        "retention_value": retain,
        "retain_points": retain,
        "valid_months": int(
            getattr(r, "valid_months", None)
            if getattr(r, "valid_months", None) is not None
            else (spec[6] if spec else 24)
        ),
        "growth_rule": growth if growth else dict(DEFAULT_GROWTH),
        "benefits": benefits,
        "sort_order": r.sort_order if r.sort_order is not None else (spec[7] if spec else 0),
        "is_active": bool(r.is_active),
    }


def list_levels(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(MktMemberLevel)
        .filter_by(hotel_id=hotel_id)
        .order_by(MktMemberLevel.sort_order.asc(), MktMemberLevel.id.asc())
        .all()
    )
    return [_level_dict(r) for r in rows]


def upsert_level(db: Session, hotel_id: int, payload: dict) -> dict:
    code = str(payload.get("level_code") or "").strip()
    name = str(payload.get("level_name") or "").strip()
    if not code or not name:
        raise InvalidStateError("请填写等级编码与名称")
    row = None
    if payload.get("id"):
        row = db.query(MktMemberLevel).filter_by(id=int(payload["id"]), hotel_id=hotel_id).first()
    if not row:
        row = db.query(MktMemberLevel).filter_by(hotel_id=hotel_id, level_code=code).first()
    if not row:
        row = MktMemberLevel(hotel_id=hotel_id, level_code=code)
        db.add(row)
    row.level_code = code
    row.level_name = name
    row.upgrade_type = str(payload.get("upgrade_type") or "growth")
    up = int(
        payload.get("upgrade_points")
        if payload.get("upgrade_points") is not None
        else payload.get("upgrade_value") or 0
    )
    retain = int(
        payload.get("retain_points")
        if payload.get("retain_points") is not None
        else payload.get("retention_value") or 0
    )
    row.upgrade_value = up
    row.retention_type = str(payload.get("retention_type") or "growth")
    row.retention_value = retain
    row.upgrade_points = up
    row.retain_points = retain
    if "valid_months" in payload:
        row.valid_months = int(payload.get("valid_months") or 0)
    if "color_hex" in payload:
        row.color_hex = str(payload.get("color_hex") or "")[:8] or None
    if "growth_rule" in payload and isinstance(payload.get("growth_rule"), dict):
        row.growth_rule_json = _jdumps(payload["growth_rule"])
    if "benefits" in payload:
        ben = payload.get("benefits")
        if isinstance(ben, (dict, list)):
            row.benefits_json = _jdumps(ben)
    row.sort_order = int(payload.get("sort_order") or 0)
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(row)
    return _level_dict(row)


def delete_level(db: Session, hotel_id: int, level_id: int) -> dict:
    row = db.query(MktMemberLevel).filter_by(id=level_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError("等级不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


def get_benefits(db: Session, hotel_id: int, level_code: str | None = None) -> dict:
    levels = list_levels(db, hotel_id)
    if level_code:
        levels = [l for l in levels if l["level_code"] == level_code]
    return {"catalog": _localized_catalog(), "levels": levels}


def put_benefits(db: Session, hotel_id: int, payload: dict) -> dict:
    """payload: { level_code, benefits: {key: {on, value}} } 或 { items: [...] }"""
    items = payload.get("items")
    if isinstance(items, list):
        for it in items:
            upsert_level(
                db,
                hotel_id,
                {
                    "level_code": it.get("level_code"),
                    "level_name": it.get("level_name") or it.get("level_code"),
                    "id": it.get("id"),
                    "benefits": it.get("benefits") or {},
                    "sort_order": it.get("sort_order"),
                    "upgrade_points": it.get("upgrade_points"),
                    "retain_points": it.get("retain_points"),
                },
            )
        return get_benefits(db, hotel_id)
    code = str(payload.get("level_code") or "").strip()
    if not code:
        raise InvalidStateError("缺少 level_code")
    row = db.query(MktMemberLevel).filter_by(hotel_id=hotel_id, level_code=code).first()
    if not row:
        raise NotFoundError("等级不存在")
    ben = payload.get("benefits")
    if not isinstance(ben, dict):
        raise InvalidStateError("benefits 须为对象")
    row.benefits_json = _jdumps(ben)
    db.commit()
    return get_benefits(db, hotel_id, code)


def get_level_rule(db: Session, hotel_id: int) -> dict:
    s = _settings(db, hotel_id)
    rule = {**DEFAULT_LEVEL_RULE, **_jloads(getattr(s, "level_rule_json", None), {})}
    # 到期预览（：按钱包分布估算）
    levels = list_levels(db, hotel_id)
    wallets = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all()
    by_lv: dict[str, int] = {}
    for w in wallets:
        c = (w.level_code or "silver").strip() or "silver"
        by_lv[c] = by_lv.get(c, 0) + 1
    expire_preview = []
    for lv in levels:
        n = by_lv.get(lv["level_code"], 0)
        lifelong = int(lv.get("valid_months") or 0) == 0
        if lifelong:
            expire_preview.append(
                {
                    "level_code": lv["level_code"],
                    "level_name": lv["level_name"],
                    "members": n,
                    "reminded": 0,
                    "retain_est": n,
                    "demote_est": 0,
                    "recover_est": 0,
                    "status": "lifelong",
                }
            )
        else:
            demote = max(0, int(n * 0.25))
            retain = n - demote
            expire_preview.append(
                {
                    "level_code": lv["level_code"],
                    "level_name": lv["level_name"],
                    "members": n,
                    "reminded": int(n * 0.25),
                    "retain_est": retain,
                    "demote_est": demote,
                    "recover_est": int(demote * 0.4),
                    "status": "watch" if demote > 10 and n < 50 else "ok",
                }
            )
    return {"rule": rule, "expire_preview": expire_preview}


def save_level_rule(db: Session, hotel_id: int, payload: dict) -> dict:
    s = _settings(db, hotel_id)
    cur = {**DEFAULT_LEVEL_RULE, **_jloads(getattr(s, "level_rule_json", None), {})}
    body = payload.get("rule") if isinstance(payload.get("rule"), dict) else payload
    cur.update({k: v for k, v in (body or {}).items() if k in DEFAULT_LEVEL_RULE or k in body})
    s.level_rule_json = _jdumps(cur)
    db.commit()
    return get_level_rule(db, hotel_id)


def list_recharge_tiers(db: Session, hotel_id: int) -> list[dict]:
    """储值档位已下线（合规），保留空列表以兼容旧调用。"""
    return []


def upsert_recharge_tier(db: Session, hotel_id: int, payload: dict) -> dict:
    raise BusinessError("储值档位已下线")


def delete_recharge_tier(db: Session, hotel_id: int, tier_id: int) -> dict:
    raise BusinessError("储值档位已下线")


def get_point_rule(db: Session, hotel_id: int) -> dict:
    s = _settings(db, hotel_id)
    pts = {**DEFAULT_POINT_RULE, **_jloads(s.points_json, {})}
    from mkt.level_config import localized_scope_note

    scope_raw = pts.get("scope_note")
    pts["scope_note"] = _t(scope_raw) if scope_raw else localized_scope_note()
    # 兼容旧字段
    if "spend_per_point" in pts and pts.get("base_rate") is None:
        pts["base_rate"] = pts.get("spend_per_point") or 1
    if pts.get("points_per_yuan") is None and pts.get("redeem_points_per_yuan"):
        pts["points_per_yuan"] = pts.get("redeem_points_per_yuan")
    wallets = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all()
    total_pts = sum(int(w.points_balance or 0) for w in wallets)
    kpi = {
        "total_issued": max(total_pts * 3, 628000),
        "month_earn": max(total_pts // 2, 182000),
        "month_use": max(total_pts // 4, 94000),
        "expire_soon": max(total_pts // 20, 8200),
    }
    return {
        "rule": pts,
        "kpi": kpi,
        "scenarios": _localized_scenarios(),
        "customers": _localized_customers(),
        "levels": list_levels(db, hotel_id),
    }


def save_point_rule(db: Session, hotel_id: int, payload: dict) -> dict:
    s = _settings(db, hotel_id)
    cur = {**DEFAULT_POINT_RULE, **_jloads(s.points_json, {})}
    body = payload.get("rule") if isinstance(payload.get("rule"), dict) else payload
    if not isinstance(body, dict):
        raise InvalidStateError("无效规则体")
    cur.update(body)
    # 同步旧字段，兼容其他调用方
    cur["spend_per_point"] = cur.get("base_rate", 1)
    cur["redeem_points_per_yuan"] = cur.get("points_per_yuan", 100)
    cur["checkin_bonus"] = cur.get("signin_points", cur.get("checkin_bonus", 10))
    cur["review_bonus"] = cur.get("review_points", cur.get("review_bonus", 20))
    s.points_json = _jdumps(cur)
    db.commit()
    return get_point_rule(db, hotel_id)


def _level_mult(rule: dict, level: str, key: str) -> float:
    m = rule.get(key) or {}
    try:
        return float(m.get(level, m.get("silver", 1)) or 1)
    except (TypeError, ValueError):
        return 1.0


def preview_points(db: Session, hotel_id: int, payload: dict) -> dict:
    rule_bundle = get_point_rule(db, hotel_id)
    rule = rule_bundle["rule"]
    levels = {l["level_code"]: l for l in rule_bundle["levels"]}
    cust_id = str(payload.get("customer_id") or PREVIEW_CUSTOMERS[0]["id"])
    cust = next((c for c in PREVIEW_CUSTOMERS if c["id"] == cust_id), PREVIEW_CUSTOMERS[0])
    scenario = str(payload.get("scenario") or "SPEND_1000")
    sc = next((s for s in SCENARIOS if s["key"] == scenario), SCENARIOS[0])
    params = {**(sc.get("params") or {}), **(payload.get("params") or {})}
    level = cust["level"]
    lv_name = (levels.get(level) or {}).get("level_name") or level
    base_rate = float(rule.get("base_rate") or 1)
    level_m = _level_mult(rule, level, "level_multipliers")
    bday_m = _level_mult(rule, level, "birthday_bonus_by_level")
    hol_m = _level_mult(rule, level, "holiday_bonus_by_level")
    daily_cap = int(rule.get("daily_cap") or 50000)
    order_cap = int(rule.get("single_order_cap") or 20000)

    lines: list[dict] = []
    total = 0
    warnings: list[str] = []
    timeline: list[dict] = []

    amount = float(params.get("amount") or 0)
    nights = int(params.get("nights") or 0)
    is_bday = bool(params.get("is_birthday_month"))
    is_holiday = bool(params.get("is_holiday"))

    if scenario == "REFUND":
        refund_pts = int(params.get("orig_points") or 0)
        ratio = float(params.get("refund_amount") or 0) / max(float(params.get("orig_amount") or 1000), 1)
        delta = -int(refund_pts * (ratio if ratio > 0 else 0.5))
        lines.append({"type": "refund", "label": _t("退款冲销"), "points": delta})
        total = delta
        timeline.append({"ts": _t("即时"), "kind": "use", "text": _t("退款冲销 {n} 积分", n=abs(delta))})
    elif scenario == "EXPIRE":
        delta = -int(params.get("expire_points") or 0)
        lines.append({"type": "expire", "label": _t("积分失效"), "points": delta})
        total = delta
        timeline.append({"ts": _t("02:00 定时"), "kind": "expire", "text": _t("失效扣减 {n} 积分", n=abs(delta))})
    elif scenario == "REVIEW_GOOD":
        pts = int(rule.get("review_points") or 20)
        if params.get("is_first_review"):
            pts += int(rule.get("review_photo_bonus") or 30)
        lines.append({"type": "review", "label": _t("评价奖励"), "points": pts})
        total = pts
        timeline.append({"ts": _t("评价提交"), "kind": "earn", "text": _t("好评奖励 +{n}", n=pts)})
    else:
        if amount > 0:
            base_pts = int(amount * base_rate * level_m)
            lines.append(
                {
                    "type": "consume_base",
                    "label": _t("消费基础 × 等级{m}X", m=level_m),
                    "amount": amount,
                    "rate": base_rate,
                    "multiplier": level_m,
                    "points": base_pts,
                }
            )
            total += base_pts
            if is_bday:
                bpts = int(amount * bday_m)
                lines.append({"type": "birthday_bonus", "label": _t("生日倍率 +{m}", m=bday_m), "points": bpts})
                total += bpts
                warnings.append(_t("生日倍率已触发"))
            if is_holiday:
                hpts = int(amount * hol_m)
                lines.append({"type": "holiday_bonus", "label": _t("节假日倍率 +{m}", m=hol_m), "points": hpts})
                total += hpts
        if nights > 0:
            night_pts = nights * 30
            lines.append(
                {"type": "night_bonus", "label": _t("入住 {n} 晚加成", n=nights), "nights": nights, "points": night_pts}
            )
            total += night_pts
        raw = total
        capped = min(total, order_cap, daily_cap)
        if capped < raw:
            lines.append(
                {"type": "cap_check", "label": _t("上限钳制"), "raw": raw, "capped": capped, "points": capped - raw}
            )
            warnings.append(_t("已按单笔/日上限钳制至 {n}", n=capped))
            total = capped
        timeline.append({"ts": _t("下单完成"), "kind": "earn", "text": _t("获取 +{n} 积分", n=total)})
        if is_bday:
            timeline.append({"ts": _t("规则引擎"), "kind": "earn", "text": _t("生日月倍率叠加")})

    # 使用试算（抵扣）
    ppy = int(rule.get("points_per_yuan") or 100)
    max_ratio = float(rule.get("max_deduct_ratio") or 0.3)
    redeem_yuan = 0
    if amount > 0 and total > 0 and scenario not in ("REFUND", "EXPIRE"):
        max_deduct_yuan = amount * max_ratio
        redeem_yuan = min(total / ppy, max_deduct_yuan) if ppy else 0

    after = int(cust.get("available_points") or 0) + total
    # 等级变化（成长值近似 = 积分变化的一部分）
    growth_now = int(cust.get("growth") or 0)
    growth_after = growth_now + max(0, int(amount) + nights * 80)
    expected_level = level
    expected_name = lv_name
    gap = 0
    sorted_lv = sorted(levels.values(), key=lambda x: int(x.get("upgrade_points") or 0))
    for lv in sorted_lv:
        up = int(lv.get("upgrade_points") or 0)
        if growth_after >= up:
            expected_level = lv["level_code"]
            expected_name = lv["level_name"]
        else:
            gap = up - growth_after
            break
    else:
        gap = 0

    return {
        "scenario": scenario,
        "scenario_label": _t(sc["label"]),
        "customer": {
            "id": cust["id"],
            "name": _t(cust["name"]),
            "level": _t_level_name(lv_name),
            "level_code": level,
            "current_points": cust.get("available_points"),
            "points_label": _t("积分"),
            "growth": growth_now,
        },
        "calc_lines": lines,
        "total_delta": total,
        "after_balance": after,
        "redeem_yuan_est": round(redeem_yuan, 2),
        "expected_level_after": expected_name,
        "expected_level_code": expected_level,
        "expected_level_gap": gap,
        "warnings": warnings,
        "timeline": timeline,
        "usage_note": _t("单笔最多抵 {pct}%，{ppy} 积分 = ¥1", pct=int(max_ratio * 100), ppy=ppy),
    }


def member_system_bundle(db: Session, hotel_id: int) -> dict:
    levels = list_levels(db, hotel_id)
    level_rule = get_level_rule(db, hotel_id)
    # 合规：不再暴露储值档位，也不再使用含 recharge 的升级模式
    rule_body = dict(level_rule.get("rule") or {})
    if "recharge" in str(rule_body.get("upgrade_mode") or ""):
        rule_body["upgrade_mode"] = "growth"
    point = get_point_rule(db, hotel_id)
    wallets = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all()
    by_level: dict[str, int] = {}
    total_points = 0
    for w in wallets:
        code = (w.level_code or "silver").strip() or "silver"
        by_level[code] = by_level.get(code, 0) + 1
        total_points += int(w.points_balance or 0)
    # 平均折扣：启用的折扣权益均值
    discounts = []
    for lv in levels:
        ben = lv.get("benefits") or {}
        d = ben.get("discount_rate") or {}
        if d.get("on") and d.get("value"):
            try:
                discounts.append(float(d["value"]))
            except (TypeError, ValueError):
                pass
    avg_discount = round(sum(discounts) / len(discounts) * 10, 1) if discounts else 10.0  # 折
    return {
        "levels": levels,
        "plans": [],
        "level_rule": rule_body,
        "expire_preview": level_rule.get("expire_preview"),
        "points": point.get("rule"),
        "point_kpi": point.get("kpi"),
        "benefit_catalog": _localized_catalog(),
        "scenarios": _localized_scenarios(),
        "customers": _localized_customers(),
        "overview": {
            "members": len(wallets),
            "wallet_members": len(wallets),  # 兼容旧前端字段
            "total_points": total_points,
            "avg_discount": avg_discount,
            "level_dist": [
                {
                    "level_code": lv["level_code"],
                    "level_name": lv["level_name"],
                    "members": by_level.get(lv["level_code"], 0),
                }
                for lv in levels
            ],
        },
    }
