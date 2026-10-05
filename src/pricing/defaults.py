# SPDX-License-Identifier: Apache-2.0
"""价格助手默认值 / Mock 数据。

从原 `bootstrap.ensure_pricing_assistant` 抽离；ensure_pricing_assistant_schema /
seed_pricing_assistant_demo 仍在 `bootstrap.ensure_pricing_assistant` 里。
"""

from __future__ import annotations

from models import (
    CompetitorProperty,
    CompetitorRateSnapshot,
    CompetitorRoomMap,
    CompetitorSet,
    EventCalendar,
    PaceSnapshot,
    ParityAlert,
    PricingAssistantConfig,
    PricingDecision,
    PricingEffect,
    PricingRecommendation,
    RoomTypeBaseRate,
)

PRICING_MODELS = (
    PricingAssistantConfig,
    RoomTypeBaseRate,
    PricingRecommendation,
    PricingDecision,
    PricingEffect,
    CompetitorSet,
    CompetitorProperty,
    CompetitorRateSnapshot,
    CompetitorRoomMap,
    EventCalendar,
    ParityAlert,
    PaceSnapshot,
)

# 本店附近 Mock 竞品（GCJ-02 近似，上海示例）
MOCK_COMPETITORS = [
    {
        "name": "维也纳酒店·人民广场",
        "lat": 31.2335,
        "lng": 121.4750,
        "star": 3,
        "score": 4.5,
        "km": 0.8,
        "src": "manual",
    },
    {"name": "如家精选·南京东路", "lat": 31.2380, "lng": 121.4820, "star": 3, "score": 4.3, "km": 1.2, "src": "manual"},
    {"name": "全季酒店·外滩", "lat": 31.2405, "lng": 121.4900, "star": 4, "score": 4.6, "km": 1.5, "src": "manual"},
    {"name": "汉庭优佳·豫园", "lat": 31.2270, "lng": 121.4920, "star": 3, "score": 4.2, "km": 1.8, "src": "manual"},
    {"name": "亚朵酒店·陆家嘴", "lat": 31.2390, "lng": 121.5050, "star": 4, "score": 4.7, "km": 2.4, "src": "manual"},
    {"name": "桔子酒店·静安", "lat": 31.2280, "lng": 121.4480, "star": 3, "score": 4.4, "km": 2.6, "src": "manual"},
    {"name": "锦江都城·虹口", "lat": 31.2550, "lng": 121.4850, "star": 4, "score": 4.5, "km": 2.9, "src": "manual"},
    {"name": "麗枫酒店·徐汇", "lat": 31.1950, "lng": 121.4450, "star": 4, "score": 4.6, "km": 4.5, "src": "manual"},
]

MOCK_MAP_CANDIDATES = [
    {"name": "和颐至尊·静安", "lat": 31.2300, "lng": 121.4550, "star": 4, "score": 4.5, "km": 2.1},
    {"name": "希岸酒店·外滩", "lat": 31.2420, "lng": 121.4880, "star": 3, "score": 4.4, "km": 1.6},
    {"name": "美豪酒店·人民广场", "lat": 31.2320, "lng": 121.4720, "star": 3, "score": 4.3, "km": 0.9},
    {"name": "轻住酒店·南京路", "lat": 31.2365, "lng": 121.4780, "star": 3, "score": 4.1, "km": 1.0},
    {"name": "喆啡酒店·陆家嘴", "lat": 31.2410, "lng": 121.5020, "star": 4, "score": 4.5, "km": 2.3},
]
