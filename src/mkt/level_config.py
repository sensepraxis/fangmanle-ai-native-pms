# SPDX-License-Identifier: Apache-2.0
"""会员等级 / 积分规则默认配置。

从原 `bootstrap.ensure_mkt_member_v2` 抽离；ensure_member_system_schema /
seed_member_system 仍在 `bootstrap.ensure_member_system` 里。
"""

from __future__ import annotations

DEFAULT_GROWTH = {"consume_yuan": 1, "stay_night": 80, "review": 20, "signin": 5}

DEFAULT_BENEFITS = {
    "silver": {
        "discount_rate": {"on": False, "value": 1.0},
        "free_breakfast": {"on": False, "value": 0},
        "late_checkout": {"on": False, "value": 0},
        "points_acceleration": {"on": True, "value": 1.0},
    },
    "gold": {
        "discount_rate": {"on": True, "value": 0.98},
        "free_breakfast": {"on": True, "value": 1},
        "late_checkout": {"on": True, "value": 2},
        "points_acceleration": {"on": True, "value": 1.5},
        "birthday_gift": {"on": True, "value": "points_1000"},
    },
    "platinum": {
        "discount_rate": {"on": True, "value": 0.95},
        "free_breakfast": {"on": True, "value": 1},
        "late_checkout": {"on": True, "value": 3},
        "dedicated_concierge": {"on": True, "value": "work_hours"},
        "points_acceleration": {"on": True, "value": 2.0},
    },
    "diamond": {
        "discount_rate": {"on": True, "value": 0.92},
        "free_breakfast": {"on": True, "value": 2},
        "upgrade_room": {"on": True, "value": "deluxe_to_exec"},
        "late_checkout": {"on": True, "value": 4},
        "dedicated_concierge": {"on": True, "value": "12h"},
        "points_acceleration": {"on": True, "value": 2.5},
    },
    "supreme": {
        "discount_rate": {"on": True, "value": 0.90},
        "free_breakfast": {"on": True, "value": 2},
        "upgrade_room": {"on": True, "value": "any_one_level"},
        "late_checkout": {"on": True, "value": 6},
        "free_cancellation": {"on": True, "value": 48},
        "dedicated_concierge": {"on": True, "value": "24h"},
        "points_acceleration": {"on": True, "value": 3.0},
        "birthday_gift": {"on": True, "value": "free_night"},
        "vip_lounge": {"on": True, "value": True},
    },
}

LEVEL_SPECS = [
    ("silver", "银卡", "L1", "#64748b", 0, 0, 0, 1),
    ("gold", "金卡", "L2", "#d4a14a", 1000, 800, 24, 2),
    ("platinum", "白金卡", "L3", "#7c3aed", 5000, 4000, 24, 3),
    ("diamond", "钻石卡", "L4", "#2563eb", 20000, 16000, 24, 4),
    ("supreme", "至尊卡", "L5", "#1f1f29", 80000, 60000, 24, 5),
]

DEFAULT_LEVEL_RULE = {
    "upgrade_mode": "growth",  # growth | growth_or_recharge | growth_and_recharge
    "benefit_effective": "next_order",
    "remind_before_expire_days": [30, 7, 1],
    "demote_protect_days": 90,
    "demote_action": "one_level",
    "notify_upgrade": True,
}

DEFAULT_POINT_RULE = {
    "base_rate": 1,
    "first_stay_bonus": 500,
    "first_stay_enabled": True,
    "night_bonus": 30,
    "signin_points": 5,
    "signin_streak_bonus": 30,
    "review_points": 20,
    "review_first_bonus": 50,
    "review_photo_bonus": 40,
    "referral_points": 200,
    "birthday_multiplier": 5,
    "holiday_multiplier": 2,
    "holiday_enabled": True,
    "points_per_yuan": 100,
    "max_deduct_ratio": 0.3,
    "min_reserve_points": 100,
    "usage_channels": "all",
    "usage_scenes": ["order_pay", "room_upgrade", "gift"],
    "level_multipliers": {
        "silver": 1.0,
        "gold": 1.5,
        "platinum": 2.0,
        "diamond": 2.5,
        "supreme": 3.0,
    },
    "birthday_bonus_by_level": {
        "silver": 5,
        "gold": 8,
        "platinum": 10,
        "diamond": 15,
        "supreme": 20,
    },
    "holiday_bonus_by_level": {
        "silver": 2,
        "gold": 3,
        "platinum": 5,
        "diamond": 8,
        "supreme": 10,
    },
    "expire_after_days": 365,
    "expiry_remind_days": [30, 7, 1],
    "frozen_before_days": 7,
    "year_end_clear": False,
    "daily_cap": 50000,
    "single_order_cap": 10000,
    "single_customer_cap": 1000000,
    "scope_note": "积分全渠道累计；使用范围可配置为前台 / 前台+企微H5 / 全渠道。",
}


def localized_scope_note() -> str:
    from infra.i18n import t as _t
    from seed.locale_pack import seed_text

    # seed 写入走 seed_text；API 展示走 t()
    return _t(DEFAULT_POINT_RULE["scope_note"])
