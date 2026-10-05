# SPDX-License-Identifier: Apache-2.0
"""客人券包 source 归一：把美团/抖音/小红书/企微等渠道码统一为几个稳定来源。

从原 `bootstrap.ensure_coupon_wallet` 抽离；ensure / backfill 仍在
`bootstrap.ensure_coupon_wallet` 里。

本店营销券统一码：``infra.branding.NATIVE_WALLET_SOURCE``（``native_mkt``）。
历史 ``fangmanle_mkt`` 仍被识别为同义，启动期会迁移。
"""

from __future__ import annotations

from infra.branding import (
    LEGACY_WALLET_SOURCES,
    NATIVE_WALLET_SOURCE,
    is_native_wallet_source,
    wallet_source_label,
)


def _wallet_source_label_map() -> dict[str, str]:
    label = wallet_source_label()
    m = {
        NATIVE_WALLET_SOURCE: label,
        "wecom": "企业微信",
        "wecom_scan": "企业微信",
        "landing_page": "企业微信",
        "meituan": "美团",
        "douyin": "抖音",
        "xhs": "小红书",
        "ota": "OTA",
        "grant": label,
    }
    for legacy in LEGACY_WALLET_SOURCES:
        m[legacy] = label
    return m


# 兼容旧 import：模块加载时快照；动态标签请用 label_for_wallet_source()
WALLET_SOURCE_LABEL = _wallet_source_label_map()


def label_for_wallet_source(raw: str | None) -> str:
    """展示用标签（随品牌配置变化）。"""
    ns = normalize_wallet_source(raw)
    return _wallet_source_label_map().get(ns, ns or "未知")


def normalize_wallet_source(raw: str | None) -> str:
    """把任意渠道字符串归一为稳定来源编码。

    规则：
    - 空 → 'wecom'（历史默认）
    - native_mkt / fangmanle_mkt / mkt_* → native_mkt
    - wecom / wecom_scan / landing_page / wecom_* → wecom
    - 已知外部渠道 → 原样
    - 其它 → 截断到 40 字符
    """
    s = str(raw or "").strip()
    if not s:
        return "wecom"
    if is_native_wallet_source(s):
        return NATIVE_WALLET_SOURCE
    if s in ("wecom_scan", "wecom", "landing_page") or s.startswith("wecom"):
        return "wecom"
    labels = _wallet_source_label_map()
    if s in labels:
        return s
    return s[:40]


__all__ = [
    "WALLET_SOURCE_LABEL",
    "NATIVE_WALLET_SOURCE",
    "normalize_wallet_source",
    "label_for_wallet_source",
]
