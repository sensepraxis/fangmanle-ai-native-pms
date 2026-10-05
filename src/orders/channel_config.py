# SPDX-License-Identifier: Apache-2.0
"""订单渠道配置 + 按渠道归组 helper。

从原 `bootstrap.ensure_order_channels` 抽离；保留 schema 保活 / 样例单灌入在
`bootstrap.ensure_order_channels` 里，这里只放渠道元数据 + 纯函数。
"""

from __future__ import annotations

from typing import Any

from finance.channel_catalog import CN_OPS_SEEDS as EXTRA_CHANNELS

# code, zh_name, type, commission —— 展示名经 channel_display_name() 按 locale 解析
# EXTRA_CHANNELS 默认 CN；运行时请用 extra_channels() 取当前酒店 channels_preset 种子。

# 统一来源分组（前端 Tab / 筛选）；组 key 仍为 ota 以兼容订单中心，展示文案用「预订平台」
SOURCE_BY_CODE = {
    "ota": "ota",
    "ctrip": "ota",
    "meituan": "ota",
    "fliggy": "ota",
    "douyin": "voucher",
    "meituan_voucher": "voucher",
    "direct": "direct",
    "map_baidu": "map",
    "map_amap": "map",
    "geo_doubao": "geo",
    "longstay": "longstay",
    "agreement": "agreement",
    "wechat": "wechat",
    "wecom": "wechat",
    "xiaohongshu": "wechat",
    "booking": "ota",
    "agoda": "ota",
    "expedia": "ota",
    "traveloka": "ota",
}

# 常住判定：连住晚数阈值（不含仅住 1–2 天的短住）
LONGSTAY_MIN_NIGHTS = 7

SOURCE_META = [
    {"key": "all", "label": "全部来源", "hint": "订单中心总览"},
    {"key": "ota", "label": "预订平台", "hint": "OTA / 在线旅行社预付预订"},
    {"key": "voucher", "label": "团购核销", "hint": "美团/抖音券到店成单"},
    {"key": "direct", "label": "散客直订", "hint": "前台建单或即时入住"},
    {"key": "group", "label": "团体订单", "hint": "会议/旅游团等多间主单"},
    {"key": "wechat", "label": "企微私域", "hint": "企业微信/私域顾问跟进成单"},
    {"key": "map", "label": "地图预订", "hint": "百度/高德 POI 订房"},
    {"key": "geo", "label": "GEO推荐", "hint": "豆包等 AI 推荐落地"},
    {"key": "longstay", "label": "常住客", "hint": "时长驱动：长住（通常 ≥7 晚），个人画像与续约"},
    {"key": "agreement", "label": "协议客", "hint": "关系驱动：合作企业协议价 · 挂账 · 可长可短"},
]


# code → 中文 msgid（展示一律 t(msgid)；EN seed 写入 DB 时改用 pack 英文名）
CHANNEL_ZH: dict[str, str] = {
    "ctrip": "携程",
    "meituan": "美团酒店",
    "fliggy": "飞猪",
    "douyin": "抖音团购",
    "meituan_voucher": "美团团购",
    "xiaohongshu": "小红书",
    "direct": "散客直订",
    "map_baidu": "百度地图",
    "map_amap": "高德地图",
    "geo_doubao": "GEO·豆包",
    "longstay": "常住客",
    "agreement": "协议客户",
    "wechat": "企微私域",
    "wecom": "企业微信",
    "ota": "其他预订渠道",
    "booking": "Booking.com",
    "agoda": "Agoda",
    "expedia": "Expedia",
    "traveloka": "Traveloka",
}


def extra_channels() -> list[tuple[str, str, str, float]]:
    """当前 pack 的渠道种子（CN=携程美团；sg=Booking/Agoda）。"""
    from infra.packs import pack_channel_seeds

    return list(pack_channel_seeds())


def channel_display_name(code: str | None, zh_fallback: str | None = None, *, for_seed: bool = False) -> str:
    """渠道 code → 展示名。

    - for_seed=True：按 SEED_LOCALE 写入 DB（EN pack 英文名 / 否则中文 msgid）
    - 默认：按请求 X-Locale 经 t() 翻译（中文 msgid 为 key）
    """
    from infra.i18n import t
    from seed.locale_pack import get_pack, get_seed_locale

    c = (code or "").strip().lower()
    zh = CHANNEL_ZH.get(c) or zh_fallback or c or "未标注"
    if for_seed and get_seed_locale().startswith("en"):
        pack = get_pack()
        for row in getattr(pack, "CHANNELS", []) or []:
            if len(row) >= 2 and str(row[0]).lower() == c:
                return str(row[1])
        return t(zh)  # en.json 译文作 DB 英文名
    return t(zh)


def source_group_for(channel: Any, nights: int | None = None) -> str:
    """按渠道归组。协议客可长可短，不因晚数改归常住客。

    入参类型刻意不强依赖 `Channel` ORM 类，便于 pms_core / mkt 等模块复用：
    只要传入对象有 `.code` 与 `.type` 属性即可。
    """
    if not channel:
        return "direct"
    code = channel.code or ""
    return SOURCE_BY_CODE.get(code, channel.type or "direct")
