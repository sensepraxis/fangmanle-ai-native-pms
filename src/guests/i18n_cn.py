# SPDX-License-Identifier: Apache-2.0
"""OneID 审计相关展示字典 + 查询函数（经 i18n）。

从原 `bootstrap.ensure_oneid_audit` 抽离；ensure_oneid_audit_schema /
create_realistic_identities / rebuild_events_for_guest / backfill_guest_identities /
ensure_oneid_audit_realism 仍在 `bootstrap.ensure_oneid_audit` 里。
"""

from __future__ import annotations

from infra.i18n import t

SRC_CN = {
    "wechat": "微信",
    "wecom": "企微",
    "ctrip": "携程",
    "meituan": "美团",
    "fliggy": "飞猪",
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "official": "官网",
    "walkin": "散客",
    "ota": "OTA",
    "agreement": "协议客户",
    "direct": "直订",
    "system": "系统",
}

MERGE_METHOD_CN = {
    "phone_exact": "手机号完全一致",
    "phone_last6": "手机号后六位匹配",
    "phone_last4": "手机号后四位匹配（旧）",
    "order_match": "订单姓名+手机匹配",
    "ai_fuzzy": "AI 模糊匹配",
    "manual_review": "人工复核确认",
    "primary_bind": "首渠道建档",
    "wecom_sync": "企微外部联系人同步",
    "name_match": "企微昵称匹配",
    "qr_state_bind": "专属活码强绑定",
}

ACTION_CN = {
    "oneid_born": "生成 OneID",
    "primary_bind": "建立主档锚点",
    "channel_merge": "归并渠道身份",
    "merge_confirm": "归并确认",
}


def source_cn(source: str | None, default: str = "未知渠道") -> str:
    """渠道编码 → 展示名（统一出口，避免前后端各抄一份）。"""
    raw = (source or "").strip()
    if not raw:
        return t(default)
    return t(SRC_CN.get(raw.lower(), raw))


def merge_method_cn(method: str | None, default: str = "—") -> str:
    raw = (method or "").strip()
    if not raw:
        return t(default) if default != "—" else default
    return t(MERGE_METHOD_CN.get(raw, raw))


def action_cn(action: str | None, default: str = "—") -> str:
    raw = (action or "").strip()
    if not raw:
        return t(default) if default != "—" else default
    return t(ACTION_CN.get(raw, raw))
