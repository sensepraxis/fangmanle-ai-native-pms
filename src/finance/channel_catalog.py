# SPDX-License-Identifier: Apache-2.0
"""渠道出厂目录：按酒店 YAML 的 channels_preset 给空库灌第一份默认值。

运行期真相在 DB /「财务参数 · OTA 佣金」页；用户改过的费率不被本模块覆盖。
酒店 YAML 不写 channels 明细。
"""

from __future__ import annotations

from typing import Any

# 订单侧运营渠道种子（demo-cn / channels_preset: cn）
CN_OPS_SEEDS: tuple[tuple[str, str, str, float], ...] = (
    ("ctrip", "携程", "booking", 0.12),
    ("meituan", "美团酒店", "booking", 0.10),
    ("fliggy", "飞猪", "booking", 0.11),
    ("wecom", "企业微信", "wechat", 0.03),
    ("meituan_voucher", "美团团购", "voucher", 0.10),
    ("map_baidu", "百度地图", "map", 0.06),
    ("map_amap", "高德地图", "map", 0.06),
    ("geo_doubao", "GEO·豆包", "geo", 0.05),
    ("longstay", "常住客", "longstay", 0.04),
)

# 中国财务档案（UI 历史 code：ota_*）；与运营侧 ctrip/meituan 通过别名同步
CN_FINANCE_SEED: list[dict[str, Any]] = [
    {
        "code": "ota_ctrip",
        "name": "携程",
        "type": "ota",
        "commission_rate": 0.12,
        "settle_cycle": "T+7",
        "note": "整改后 10/12/15% 自选，本表存中档 12%",
    },
    {
        "code": "ota_meituan",
        "name": "美团",
        "type": "ota",
        "commission_rate": 0.10,
        "settle_cycle": "T+7",
        "note": "舒适型及以上 10% 起",
    },
    {
        "code": "ota_fliggy",
        "name": "飞猪",
        "type": "ota",
        "commission_rate": 0.08,
        "settle_cycle": "T+7",
        "note": "阿里系导流，行业最低区间",
    },
    {
        "code": "ota_douyin",
        "name": "抖音来客",
        "type": "ota",
        "commission_rate": 0.08,
        "settle_cycle": "T+1",
        "note": "2025-01 起核销佣金 8%",
    },
    {
        "code": "ota_tongcheng",
        "name": "同程/去哪儿",
        "type": "ota",
        "commission_rate": 0.12,
        "settle_cycle": "T+7",
        "note": "携程系，12%–18%",
    },
    {
        "code": "ota_elong",
        "name": "艺龙",
        "type": "ota",
        "commission_rate": 0.10,
        "settle_cycle": "T+7",
        "note": "携程系，分销 10%–15%",
    },
    {
        "code": "jd",
        "name": "京东",
        "type": "ota",
        "commission_rate": 0.00,
        "settle_cycle": "月结",
        "note": "三年期零佣金（流量待验证）",
    },
    {
        "code": "direct",
        "name": "官网直订",
        "type": "direct",
        "commission_rate": 0.00,
        "settle_cycle": "实时",
        "note": "仅支付通道 ~1.5%，房满乐战略重心",
    },
    {
        "code": "member",
        "name": "小程序/会员",
        "type": "membership",
        "commission_rate": 0.00,
        "settle_cycle": "实时",
        "note": "仅支付通道 ~2%，私域直订",
    },
    {
        "code": "ota_agoda",
        "name": "Agoda/Booking",
        "type": "ota",
        "commission_rate": 0.15,
        "settle_cycle": "月结",
        "note": "海外渠道，跨境客参考",
    },
]

_SEA: list[dict[str, Any]] = [
    {
        "code": "direct",
        "name": "Walk-in / Direct",
        "type": "direct",
        "commission_rate": 0.0,
        "settle_cycle": "实时",
        "note": "Official / walk-in",
    },
    {
        "code": "booking",
        "name": "Booking.com",
        "type": "ota",
        "commission_rate": 0.15,
        "settle_cycle": "月结",
        "note": "SEA OTA default",
    },
    {
        "code": "agoda",
        "name": "Agoda",
        "type": "ota",
        "commission_rate": 0.15,
        "settle_cycle": "月结",
        "note": "SEA OTA default",
    },
    {
        "code": "expedia",
        "name": "Expedia",
        "type": "ota",
        "commission_rate": 0.18,
        "settle_cycle": "月结",
        "note": "SEA OTA default",
    },
    {
        "code": "traveloka",
        "name": "Traveloka",
        "type": "ota",
        "commission_rate": 0.12,
        "settle_cycle": "月结",
        "note": "SEA OTA default",
    },
    {
        "code": "longstay",
        "name": "Long stay",
        "type": "longstay",
        "commission_rate": 0.04,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "agreement",
        "name": "Corporate",
        "type": "agreement",
        "commission_rate": 0.05,
        "settle_cycle": "月结",
        "note": "",
    },
]

_UK: list[dict[str, Any]] = [
    {
        "code": "direct",
        "name": "Walk-in / Direct",
        "type": "direct",
        "commission_rate": 0.0,
        "settle_cycle": "实时",
        "note": "",
    },
    {
        "code": "booking",
        "name": "Booking.com",
        "type": "ota",
        "commission_rate": 0.15,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "expedia",
        "name": "Expedia",
        "type": "ota",
        "commission_rate": 0.18,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "longstay",
        "name": "Long stay",
        "type": "longstay",
        "commission_rate": 0.04,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "agreement",
        "name": "Corporate",
        "type": "agreement",
        "commission_rate": 0.05,
        "settle_cycle": "月结",
        "note": "",
    },
]

_INTL: list[dict[str, Any]] = [
    {
        "code": "direct",
        "name": "Walk-in / Direct",
        "type": "direct",
        "commission_rate": 0.0,
        "settle_cycle": "实时",
        "note": "",
    },
    {
        "code": "booking",
        "name": "Booking.com",
        "type": "ota",
        "commission_rate": 0.15,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "agreement",
        "name": "Corporate",
        "type": "agreement",
        "commission_rate": 0.05,
        "settle_cycle": "月结",
        "note": "",
    },
    {
        "code": "longstay",
        "name": "Long stay",
        "type": "longstay",
        "commission_rate": 0.04,
        "settle_cycle": "月结",
        "note": "",
    },
]

_SEA_PACKS = frozenset({"sg", "vn", "th", "mm", "my", "kr"})


def _active_preset() -> str:
    try:
        from infra.hotel import current_assembly, ensure_hotel

        ensure_hotel()
        return (current_assembly().channels_preset or "intl").strip().lower()
    except Exception:
        import os

        return (
            os.environ.get("FML_CHANNELS_PRESET") or os.environ.get("FML_HOTEL") or os.environ.get("FML_PACKS") or "cn"
        ).strip().lower().split(",")[0] or "cn"


def finance_seed_rows(pack_id: str | None = None) -> list[dict[str, Any]]:
    """财务页 / Channel 表首灌行。"""
    pid = (pack_id or _active_preset()).strip().lower()
    if pid in ("cn", "demo-cn", "abc-hotel"):
        return list(CN_FINANCE_SEED)
    if pid in ("gb", "demo-gb", "uk"):
        return [dict(r) for r in _UK]
    if pid in ("intl", "demo-intl"):
        return [dict(r) for r in _INTL]
    if pid in _SEA_PACKS or pid.startswith("demo-"):
        # demo-sg / demo-th … 走 SEA 出厂
        if pid in ("demo-gb",):
            return [dict(r) for r in _UK]
        if pid.replace("demo-", "") in _SEA_PACKS or pid in _SEA_PACKS:
            return [dict(r) for r in _SEA]
        if "intl" in pid:
            return [dict(r) for r in _INTL]
        return [dict(r) for r in _SEA]
    return [dict(r) for r in _SEA]


def finance_archive_codes(pack_id: str | None = None) -> list[str]:
    return [str(r["code"]) for r in finance_seed_rows(pack_id)]


def ops_channel_seeds(pack_id: str | None = None) -> tuple[tuple[str, str, str, float], ...]:
    """订单 / demo seed 用的 (code, name, type, commission)。"""
    pid = (pack_id or _active_preset()).strip().lower()
    if pid in ("cn", "demo-cn", "abc-hotel"):
        return CN_OPS_SEEDS
    rows = finance_seed_rows(pid)
    return tuple(
        (
            str(r["code"]),
            str(r["name"]),
            str(r.get("type") or "ota"),
            float(r.get("commission_rate") or 0),
        )
        for r in rows
    )
