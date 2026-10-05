# SPDX-License-Identifier: Apache-2.0
"""English seed constants (demo DB for SEED_LOCALE=en)."""

from __future__ import annotations

SURNAMES = [
    "Wang",
    "Li",
    "Zhang",
    "Liu",
    "Chen",
    "Yang",
    "Huang",
    "Zhao",
    "Zhou",
    "Wu",
    "Xu",
    "Sun",
    "Ma",
    "Zhu",
    "Hu",
    "Guo",
    "He",
    "Gao",
    "Lin",
    "Zheng",
]
GIVEN = [
    "Wei",
    "Fang",
    "Na",
    "Min",
    "Jing",
    "Li",
    "Qiang",
    "Lei",
    "Jun",
    "Yang",
    "Yong",
    "Yan",
    "Jie",
    "Juan",
    "Tao",
    "Ming",
    "Chao",
    "Xia",
    "Ping",
    "Gang",
    "Ting",
    "Yu",
    "Hao",
    "Xue",
    "Lin",
]
CITIES = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Hangzhou"]

HOTELS = [("LOCAL", "Fangmanle", "Local", "Set address in property settings", 4)]
LOCAL_USERS = [
    ("admin", "admin123", "admin", "System Admin"),
    ("gm", "gm123", "gm", "General Manager"),
    ("revenue", "rm123", "rm", "Revenue Manager"),
    ("front", "front123", "fd", "Front Desk"),
]
ROLES = [
    ("admin", "System Admin", "Full access"),
    ("gm", "General Manager", "Property ops"),
    ("rm", "Revenue Manager", "Pricing & revenue"),
    ("fd", "Front Desk", "Reception & cashier"),
]

ROOM_TYPE_TPL = [
    ("std-twin", "Economy Twin", "Twin", 2, 199, False),
    ("deluxe-king", "Deluxe King", "King", 2, 480, True),
    ("premier-king", "Premier King", "King", 2, 520, True),
    ("biz-twin", "Business Twin", "Twin", 2, 420, True),
    ("family", "Family Room", "King + Single", 3, 680, True),
    ("exec-suite", "Executive Suite", "King", 2, 880, True),
]

CHANNELS = [
    ("ctrip", "Ctrip", "booking", 0.12),
    ("meituan", "Meituan Hotel", "booking", 0.1),
    ("fliggy", "Fliggy", "booking", 0.11),
    ("douyin", "Douyin Deals", "voucher", 0.08),
    ("meituan_voucher", "Meituan Voucher", "voucher", 0.1),
    ("xiaohongshu", "Xiaohongshu", "xiaohongshu", 0.06),
    ("direct", "Walk-in / Direct", "direct", 0.0),
    ("map_baidu", "Baidu Maps", "map", 0.06),
    ("map_amap", "Amap", "map", 0.06),
    ("geo_doubao", "GEO · Doubao", "geo", 0.05),
    ("longstay", "Long-stay", "longstay", 0.04),
    ("agreement", "Corporate", "agreement", 0.05),
    ("wechat", "WeCom private", "wechat", 0.03),
]

TAGS = [
    ("high_value", "High-value guest", "Value", "Annual spend ≥ ¥50,000 or LTV ≥ ¥8,000"),
    ("price_sensitive", "Price sensitive", "Behavior", "High promo conversion · ADR 15% below rack"),
    ("family", "Family with kids", "Profile", "≥ 2 stays with children"),
    ("business", "Business frequent", "Profile", "Weekday stays > 70%"),
    ("complaint_risk", "Complaint risk", "Risk", "Model: Complaint_v2 (confidence > 80%)"),
    ("douyin_fan", "Douyin fan", "Channel", "≥ 1 Douyin order or ≥ 3 private interactions"),
    ("xhs_fan", "Xiaohongshu fan", "Channel", "≥ 1 Xiaohongshu-sourced order"),
    ("repeat", "Repeat guest", "Loyalty", "≥ 5 orders in 180 days"),
    ("vip", "VIP", "Loyalty", "Gold/Platinum member or ≥ 20 room-nights"),
]

SUPPLY_CATS = [
    ("Consumables", None),
    ("Linen", None),
    ("Cleaning", None),
    ("Guest amenities", None),
]
SUPPLIES = [
    ("Consumables", "Dental kit", "set", 200, 60),
    ("Consumables", "Shampoo", "bottle", 300, 80),
    ("Consumables", "Slippers", "pair", 250, 70),
    ("Linen", "Bed sheet", "pc", 120, 40),
    ("Linen", "Bath towel", "pc", 150, 50),
    ("Cleaning", "Vacuum bag", "pc", 80, 20),
    ("Guest amenities", "Mineral water", "bottle", 500, 150),
    ("Guest amenities", "Tea bag", "box", 180, 50),
]

ASSET_TPL = [
    "Central AC",
    "Elevator",
    "Smart TV",
    "Mattress",
    "Hot water system",
    "Access control",
    "Fresh air",
    "Fire panel",
]
ASSET_FLOW_TPL = [
    (
        "Daikin central AC",
        "HVAC",
        "402",
        "4F",
        "DK-AC-402-01",
        "FTXG50JV2W",
        4500,
        72,
        "Filter clean due in ~3 days",
        "maintenance",
    ),
    (
        "TOTO smart toilet",
        "In-room",
        "305",
        "3F",
        "TT-305-A2",
        "CES9788",
        6800,
        45,
        "Water pressure fluctuation — check valve",
        "abnormal",
    ),
    (
        'Sony 65" smart TV',
        "In-room",
        "302",
        "3F",
        "SNY-8839-2A",
        "XR-65X90J",
        6500,
        88,
        "Power stable; backlight healthy",
        "active",
    ),
    (
        "Dyson HD15 dryer",
        "In-room",
        "410",
        "4F",
        "DYN-4471-9F",
        "HD15",
        3200,
        62,
        "Bluetooth tag drops occasionally",
        "active",
    ),
    (
        "Midea central AC",
        "HVAC",
        "",
        "Lobby",
        "MTC-2207-B3",
        "MDV-D280",
        28000,
        88,
        "Routine service next month",
        "active",
    ),
    (
        "Smart door lock",
        "Low-voltage",
        "510",
        "5F",
        "LK-510-09",
        "Yale-YDM7116",
        1800,
        55,
        "Battery below 15%",
        "maintenance",
    ),
    (
        "Lobby aroma unit",
        "Public",
        "",
        "1F Lobby",
        "AR-LOBBY-01",
        "AromaPro",
        4200,
        70,
        "Solution runs out tomorrow night",
        "active",
    ),
    (
        "Elevator A",
        "Elevator",
        "",
        "Lobby",
        "EL-A-01",
        "OTIS-Gen2",
        150000,
        78,
        "Routine service window this week",
        "maintenance",
    ),
    ("Heat-pump hot water", "HVAC", "", "B1 plant", "HP-B1-01", "Gree-GHP", 210000, 91, "Running normally", "active"),
    ("Fresh air unit", "HVAC", "", "Shaft", "FAU-03", "Holtop-X", 96000, 85, "Filter life ~40% left", "active"),
    (
        "Sealy mattress",
        "In-room",
        "302",
        "3F",
        "SL-302-M1",
        "Sealy-Posture",
        8800,
        68,
        "High occupancy — near replace cycle",
        "active",
    ),
    ("NVR CCTV", "Low-voltage", "", "Fire control", "NVR-01", "Hikvision-DS", 58000, 93, "Disk space OK", "active"),
]

HK_NAMES = [
    ("hk-a", "Auntie Wang"),
    ("hk-b", "Sister Li"),
    ("hk-c", "Master Zhang"),
    ("hk-d", "Zhao (HK)"),
    ("hk-e", "Chen (HK)"),
]
HK_ROLE_NAME = "Housekeeping"

RATE_STRATEGY_NAME = "Default revenue guardrail"
AMENITY_BF = "Breakfast"
AMENITY_EXTRA_BED = "Extra bed OK"
AMENITY_LIVING = "Living area"
AMENITY_TUB = "Bathtub"
AMENITY_SHOWER = "Shower"

PRICING_EVENTS = [
    ("holiday", "Mid-Autumn Festival", 20, 21, None, "中", None, 1.0),
    ("holiday", "National Day Golden Week", 28, 34, None, "强", None, 1.0),
    ("concert", "Jay Chou Shanghai Concert", 2, 3, 3.2, "爆", 95, 1.0),
    ("exhibition", "Hotel Supplies Expo", 10, 12, 4.5, "中", 60, 1.0),
]
