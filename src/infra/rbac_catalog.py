# SPDX-License-Identifier: Apache-2.0
"""RBAC 权限目录与四角色默认矩阵（单一事实源）。"""

from __future__ import annotations

# (code, name, module, sort)
MENUS: list[tuple[str, str, str, int]] = [
    ("menu.overview.dashboard", "经营看板", "overview", 10),
    ("menu.overview.pricing", "价格助手", "overview", 20),
    ("menu.overview.forecast", "营收预测", "overview", 30),
    ("menu.orders.center", "订单中心", "orders", 10),
    ("menu.orders.booking", "前台预订", "orders", 20),
    ("menu.orders.assign", "待分房", "orders", 30),
    ("menu.orders.checkout", "收银退房", "orders", 40),
    ("menu.rooms.board", "房态看板", "rooms", 10),
    ("menu.rooms.hk", "房务任务", "rooms", 20),
    ("menu.rooms.inventory", "库存预售", "rooms", 30),
    ("menu.rooms.assets", "设备设施", "rooms", 40),
    ("menu.rooms.hk_reports", "房务报表", "rooms", 50),
    ("menu.crm.directory", "全景列表", "crm", 10),
    ("menu.crm.cohort", "客群运营", "crm", 20),
    ("menu.crm.oneid", "OneID归并", "crm", 30),
    ("menu.crm.vip", "VIP管家", "crm", 40),
    ("menu.crm.tags", "标签管理", "crm", 50),
    ("menu.analytics.insights", "专题洞察", "analytics", 10),
    ("menu.analytics.profit", "利润优化", "analytics", 20),
    ("menu.analytics.ai", "AI问数", "analytics", 30),
    ("menu.finance.deposit", "押金管理", "finance", 10),
    ("menu.finance.refund", "退改与反结账", "finance", 20),
    ("menu.finance.shift", "交班接班", "finance", 30),
    ("menu.finance.night_audit", "夜间审计", "finance", 40),
    ("menu.finance.recon", "财务对账", "finance", 50),
    ("menu.finance.invoice", "发票管理", "finance", 60),
    ("menu.finance.ar_ap", "应收应付", "finance", 70),
    ("menu.finance.reports", "财务报表", "finance", 80),
    ("menu.mkt.overview", "私域总览", "mkt", 10),
    ("menu.mkt.coupons", "优惠券中心", "mkt", 20),
    ("menu.mkt.landing", "页面装修器", "mkt", 30),
    ("menu.mkt.members", "会员体系", "mkt", 40),
    ("menu.mkt.points", "积分规则", "mkt", 50),
    ("menu.system.wecom", "企业微信接入", "extensions", 10),
    ("menu.system.llm", "大语言模型", "extensions", 20),
    ("menu.system.map", "地图配置", "extensions", 25),
    ("menu.system.finance_params", "财务参数", "system", 30),
    ("menu.system.room_types", "房型管理", "system", 40),
    ("menu.system.room_master", "房间档案", "system", 50),
    ("menu.system.users", "用户与账号", "system", 60),
    ("menu.system.rbac", "角色权限", "system", 70),
]

ACTIONS: list[tuple[str, str, str, int]] = [
    ("action.orders.write", "订单订住退分房", "orders", 10),
    ("action.rooms.status", "房态日常改态", "rooms", 10),
    ("action.rooms.lock_ooo_price", "锁房/OOO/改价", "rooms", 20),
    ("action.rooms.master_write", "房间/房型改删", "rooms", 30),
    ("action.hk.dispatch", "房务派工排班", "rooms", 40),
    ("action.pricing.accept", "价格建议采纳", "overview", 10),
    ("action.finance.night_audit", "夜审执行", "finance", 10),
    ("action.finance.refund", "退款/反结账", "finance", 20),
    ("action.mkt.coupon_grant", "发券/活动审批", "mkt", 10),
    ("action.pii.reveal", "证件揭示/问数PII", "crm", 10),
    ("action.system.users", "用户管理", "system", 10),
    ("action.system.rbac", "角色权限配置", "system", 20),
    ("action.system.map", "地图配置保存", "extensions", 30),
]

MODULE_LABELS = {
    "overview": "经营总览",
    "orders": "订单管理",
    "rooms": "房务与房态",
    "crm": "客户会员",
    "analytics": "数据洞察",
    "finance": "财务管理",
    "mkt": "私域运营",
    "system": "系统配置",
    "extensions": "扩展能力",
}

ROLES = [
    ("admin", "系统管理员", "全权限；用户与角色配置"),
    ("gm", "店长", "单店经营与审批；可进系统配置（不含用户/RBAC）"),
    ("rm", "收益经理", "定价、收益与洞察"),
    ("fd", "前台", "订单、房态与日常接待"),
]

SYSTEM_ROLE_CODES = frozenset(c for c, *_ in ROLES)

# 角色 → 默认菜单 codes（None = 该模块全部菜单）
_ALL_MENUS = [c for c, *_ in MENUS]
_ALL_ACTIONS = [c for c, *_ in ACTIONS]


def _menus(*codes: str) -> list[str]:
    return list(codes)


DEFAULT_MENUS: dict[str, list[str]] = {
    "admin": list(_ALL_MENUS),
    "gm": [c for c in _ALL_MENUS if c not in ("menu.system.users", "menu.system.rbac")],
    "rm": _menus(
        "menu.overview.dashboard",
        "menu.overview.pricing",
        "menu.overview.forecast",
        "menu.rooms.inventory",
        "menu.analytics.insights",
        "menu.analytics.profit",
        "menu.analytics.ai",
    ),
    "fd": _menus(
        "menu.orders.center",
        "menu.orders.booking",
        "menu.orders.assign",
        "menu.orders.checkout",
        "menu.rooms.board",
        "menu.rooms.hk",
        "menu.rooms.assets",
        "menu.crm.directory",
        "menu.crm.cohort",
        "menu.crm.vip",
    ),
}

DEFAULT_ACTIONS: dict[str, list[str]] = {
    "admin": list(_ALL_ACTIONS),
    "gm": [
        "action.orders.write",
        "action.rooms.status",
        "action.rooms.lock_ooo_price",
        "action.rooms.master_write",
        "action.hk.dispatch",
        "action.pricing.accept",
        "action.finance.night_audit",
        "action.finance.refund",
        "action.mkt.coupon_grant",
        "action.pii.reveal",
    ],
    "rm": [
        "action.pricing.accept",
    ],
    "fd": [
        "action.orders.write",
        "action.rooms.status",
    ],
}

# 前端路径 → 所需二级菜单（命中任一前缀即要求该 menu）
# 更具体的路径须排在前面
MENU_PATH_RULES: list[tuple[str, str]] = [
    ("/a-ai-core/users", "menu.system.users"),
    ("/a-ai-core/rbac", "menu.system.rbac"),
    ("/a-ai-core/private-channel", "menu.system.wecom"),
    ("/a-ai-core/wecom-integration", "menu.system.wecom"),
    ("/a-ai-core/ai-system-configuration", "menu.system.llm"),
    ("/a-ai-core/map-config", "menu.system.map"),
    ("/a-ai-core/finance-params-float-carry", "menu.system.finance_params"),
    ("/a-ai-core/ota-commission", "menu.system.finance_params"),
    ("/a-ai-core/room-type-management", "menu.system.room_types"),
    ("/a-ai-core/room-master", "menu.system.room_master"),
    ("/c5-frontdesk/room-asset-configuration", "menu.system.room_types"),
    ("/pricing", "menu.overview.pricing"),
    ("/c9-finance/revenue-forecast", "menu.overview.forecast"),
    ("/c5-frontdesk/pending-assignment", "menu.orders.assign"),
    ("/c5-frontdesk/cashiering-checkout", "menu.orders.checkout"),
    ("/c5-frontdesk/voucher-verification", "menu.orders.checkout"),
    ("/c5-frontdesk/walk-in-quick-check-in", "menu.orders.booking"),
    ("/c5-frontdesk/front-desk-booking", "menu.orders.booking"),
    ("/c5-frontdesk/group-booking", "menu.orders.booking"),
    ("/c5-frontdesk/agreement-corp", "menu.orders.booking"),
    ("/c5-frontdesk/engine", "menu.orders.booking"),
    ("/orders", "menu.orders.center"),
    ("/c5-frontdesk/orders", "menu.orders.center"),
    ("/c5-frontdesk/filter", "menu.orders.center"),
    ("/room-board", "menu.rooms.board"),
    ("/c6-housekeeping/reports", "menu.rooms.hk_reports"),
    ("/c6-housekeeping", "menu.rooms.hk"),
    ("/housekeeping", "menu.rooms.hk"),
    ("/c5-frontdesk/smart-inventory", "menu.rooms.inventory"),
    ("/c8-assets", "menu.rooms.assets"),
    ("/b-data/global-guest-directory", "menu.crm.directory"),
    ("/guests", "menu.crm.directory"),
    ("/b-data/cohort-list", "menu.crm.cohort"),
    ("/b-data/one-id", "menu.crm.oneid"),
    ("/b-data/ai-high-confidence", "menu.crm.oneid"),
    ("/b-data/consolidated-asset", "menu.crm.oneid"),
    ("/b-data/one-id-audit", "menu.crm.oneid"),
    ("/c4-reputation/ms-lin-vip", "menu.crm.vip"),
    ("/b-data/tag-management", "menu.crm.tags"),
    ("/b-data/master-tag", "menu.crm.tags"),
    ("/b-data/semantic-tag", "menu.crm.tags"),
    ("/b-data/tag-ecosystem", "menu.crm.tags"),
    ("/b-data/guest-segmentation", "menu.crm.tags"),
    ("/analytics", "menu.analytics.insights"),
    ("/ai", "menu.analytics.ai"),
    ("/c9-finance/deposit-management", "menu.finance.deposit"),
    ("/c9-finance/refund-adjustment", "menu.finance.refund"),
    ("/c9-finance/shift-handover", "menu.finance.shift"),
    ("/c9-finance/night-audit", "menu.finance.night_audit"),
    ("/c9-finance/smart-reconciliation", "menu.finance.recon"),
    ("/c9-finance/happy-house", "menu.finance.invoice"),
    ("/c9-finance/ar-ap", "menu.finance.ar_ap"),
    ("/c9-finance/daily-operations", "menu.finance.reports"),
    ("/acquisition/coupons", "menu.mkt.coupons"),
    ("/acquisition/landing-pages", "menu.mkt.landing"),
    ("/acquisition/members", "menu.mkt.members"),
    ("/acquisition/points", "menu.mkt.points"),
    ("/acquisition", "menu.mkt.overview"),
    ("/", "menu.overview.dashboard"),
]

# 一级侧栏：任一二级菜单即可显示
SIDEBAR_MENU_GROUPS: dict[str, list[str]] = {
    "overview": [c for c, _, m, _ in MENUS if m == "overview"],
    "orders": [c for c, _, m, _ in MENUS if m == "orders"],
    "rooms": [c for c, _, m, _ in MENUS if m == "rooms"],
    "crm": [c for c, _, m, _ in MENUS if m == "crm"],
    "analytics": [c for c, _, m, _ in MENUS if m == "analytics"],
    "finance": [c for c, _, m, _ in MENUS if m == "finance"],
    "mkt": [c for c, _, m, _ in MENUS if m == "mkt"],
    "system": [c for c, _, m, _ in MENUS if m == "system"],
    "extensions": [c for c, _, m, _ in MENUS if m == "extensions"],
}
