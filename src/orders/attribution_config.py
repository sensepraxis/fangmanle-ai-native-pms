# SPDX-License-Identifier: Apache-2.0
"""订单渠道归因配置 + 渠道展示名。

从原 `bootstrap.ensure_order_attribution` 抽离；ensure_order_attribution 仍在
`bootstrap.ensure_order_attribution` 里。
"""

from __future__ import annotations

from typing import Any

ASSIST_SOURCES = ("xiaohongshu", "douyin", "ota")
ASSIST_WEIGHTS = (0.45, 0.30, 0.25)

# code → 中文 msgid
_SOURCE_LABEL_ZH = {
    "xiaohongshu": "小红书自然流量",
    "douyin": "抖音短视频",
    "ota": "OTA 搜索",
    "wechat": "企微私域",
    "wecom": "企微直订",
    "direct": "散客直订",
}

_PATH_CHIP_ZH = {
    "xiaohongshu": {"label": "小红书阅读", "tone": "red"},
    "douyin": {"label": "抖音视频互动", "tone": "purple"},
    "ota": {"label": "OTA 浏览", "tone": "orange"},
    "wechat": {"label": "企微私域", "tone": "green", "icon": "chat"},
    "wecom": {"label": "企微直订", "tone": "green", "icon": "chat"},
    "direct": {"label": "散客直订", "tone": "blue"},
}


class _TranslatingSourceLabel(dict):
    def get(self, key, default=None):  # type: ignore[override]
        from infra.i18n import t

        if key in _SOURCE_LABEL_ZH:
            return t(_SOURCE_LABEL_ZH[key])
        if default is not None:
            return t(str(default)) if isinstance(default, str) else default
        return t(str(key)) if key else default


SOURCE_LABEL = _TranslatingSourceLabel(_SOURCE_LABEL_ZH)


def path_chip_for(code: str | None, fallback_label: str | None = None) -> dict[str, Any]:
    from infra.i18n import t
    from orders.channel_config import channel_display_name

    c = (code or "").strip().lower()
    meta = _PATH_CHIP_ZH.get(c)
    if meta:
        out = dict(meta)
        out["label"] = t(meta["label"])
        return out
    label = channel_display_name(c, fallback_label) if c else t(fallback_label or "未标注")
    return {"label": label, "tone": "blue"}
