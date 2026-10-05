# SPDX-License-Identifier: Apache-2.0
"""产品白标 / 品牌配置（开源可换皮入口）。

所有用户可见的产品名、钱包源码、AI 人设前缀，统一从这里读。
换皮只需设环境变量，不必改业务代码：

    FML_APP_NAME=星宿酒店
    FML_APP_NAME_EN=StarStay
    FML_APP_SLUG=starstay
    FML_APP_TAGLINE=AI 原生酒店 PMS

可选运行时覆盖（AppSetting key=``branding``）由 ``load_branding_overrides`` 合并。
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Optional

from sqlalchemy.orm import Session

# ---- 稳定业务码（入库用，与展示名解耦）----
# 历史值 fangmanle_mkt 在 ensure_coupon_wallet 启动时幂等迁移为 native_mkt。
NATIVE_WALLET_SOURCE = "native_mkt"
LEGACY_WALLET_SOURCES = frozenset({"fangmanle_mkt", "mkt"})

BRANDING_SETTING_KEY = "branding"

_DEFAULTS = {
    "app_name": "房满乐",
    "app_name_en": "fangmanle",
    "app_slug": "fangmanle",
    "tagline": "AI 原生酒店 PMS",
    "wallet_source_label": "本店私域",
    "primary_color": "",
    "logo_url": "",
}

# AppSetting 合并缓存（进程级；测试可 clear）
_overrides: dict[str, Any] = {}


def _env(name: str, default: str) -> str:
    v = (os.environ.get(name) or "").strip()
    return v if v else default


def clear_branding_cache() -> None:
    """测试用：清空运行时覆盖。"""
    _overrides.clear()


def load_branding_overrides(db: Session) -> dict:
    """从 AppSetting 读 branding 覆盖并缓存；无记录则保持空。"""
    global _overrides
    from infra.config_registry import load_app_setting_json

    merged = load_app_setting_json(
        db,
        BRANDING_SETTING_KEY,
        default_factory=lambda: {},
    )
    _overrides = {k: v for k, v in merged.items() if v not in (None, "")}
    return dict(_overrides)


def ensure_branding_defaults(db: Session) -> dict:
    """幂等写入空 branding 记录（方便后台编辑）；不覆盖用户已存值。"""
    from infra.config_registry import load_app_setting_json, save_app_setting_json

    existing = load_app_setting_json(db, BRANDING_SETTING_KEY, default_factory=lambda: {})
    if existing:
        return existing
    # 不强制写死默认中文名到库——默认走代码/_env，库里留空表示「用默认」
    save_app_setting_json(db, BRANDING_SETTING_KEY, {})
    return {}


def _get(key: str) -> str:
    if key in _overrides and _overrides[key]:
        return str(_overrides[key])
    env_map = {
        "app_name": "FML_APP_NAME",
        "app_name_en": "FML_APP_NAME_EN",
        "app_slug": "FML_APP_SLUG",
        "tagline": "FML_APP_TAGLINE",
        "wallet_source_label": "FML_WALLET_SOURCE_LABEL",
        "primary_color": "FML_PRIMARY",
        "logo_url": "FML_LOGO_URL",
    }
    return _env(env_map.get(key, ""), _DEFAULTS.get(key, ""))


def app_name() -> str:
    return _get("app_name")


def app_name_en() -> str:
    return _get("app_name_en")


def app_slug() -> str:
    return _get("app_slug")


def tagline() -> str:
    return _get("tagline")


def wallet_source_label() -> str:
    return _get("wallet_source_label")


def product_title() -> str:
    """FastAPI / 文档标题：如「房满乐 PMS」。"""
    return f"{app_name()} PMS"


def ai_system_prefix() -> str:
    """AI system prompt 通用前缀：如「你是房满乐酒店 PMS」。"""
    return f"你是{app_name()}酒店 PMS"


def ai_role(role: str) -> str:
    """「你是{品牌}酒店 PMS 的「{role}」。」"""
    return f"{ai_system_prefix()} 的「{role}」。"


def ai_assistant(role: str) -> str:
    """「你是「{品牌}」{role}」短前缀（房务/财务 harness 用）。"""
    return f"你是「{app_name()}」{role}"


def primary_color() -> str:
    return _get("primary_color")


def logo_url() -> str:
    return _get("logo_url")


def branding_public_dict() -> dict:
    """给前端 / 开源部署页用的公开品牌信息（无密钥）。"""
    from infra.commercial_pack import commercial_enabled

    out = {
        "app_name": app_name(),
        "app_name_en": app_name_en(),
        "app_slug": app_slug(),
        "tagline": tagline(),
        "product_title": product_title(),
        "wallet_source": NATIVE_WALLET_SOURCE,
        "wallet_source_label": wallet_source_label(),
        "legacy_wallet_sources": sorted(LEGACY_WALLET_SOURCES),
        "primary_color": primary_color(),
        "logo_url": logo_url(),
        "deployment_mode": "single_hotel",
        "commercial_enabled": commercial_enabled(),
    }
    try:
        from infra.hotel import public_hotel_dict

        out.update(public_hotel_dict())
    except Exception:
        try:
            from infra.packs import public_pack_dict

            out.update(public_pack_dict())
        except Exception:
            pass
    return out


def is_native_wallet_source(raw: Optional[str]) -> bool:
    s = str(raw or "").strip()
    return s == NATIVE_WALLET_SOURCE or s in LEGACY_WALLET_SOURCES or s.startswith("mkt_")


def brand_text(template: str) -> str:
    """把模板里的 ``{APP_NAME}`` 替换为当前品牌名（避免 f-string 与 JSON 花括号冲突）。

    英文 locale 下 ``{APP_NAME}`` 使用 slug（如 fangmanle），避免中文品牌名混入英文提示词。
    """
    try:
        from infra.i18n import get_locale

        use_en = str(get_locale() or "").lower().startswith("en")
    except Exception:
        use_en = False
    display = app_slug() if use_en else app_name()
    return (
        template.replace("{APP_NAME}", display)
        .replace("{APP_NAME_EN}", app_name_en() or app_slug())
        .replace("{APP_SLUG}", app_slug())
    )


__all__ = [
    "NATIVE_WALLET_SOURCE",
    "LEGACY_WALLET_SOURCES",
    "BRANDING_SETTING_KEY",
    "clear_branding_cache",
    "load_branding_overrides",
    "ensure_branding_defaults",
    "app_name",
    "app_name_en",
    "app_slug",
    "tagline",
    "wallet_source_label",
    "product_title",
    "ai_system_prefix",
    "ai_role",
    "ai_assistant",
    "brand_text",
    "branding_public_dict",
    "is_native_wallet_source",
    "primary_color",
    "logo_url",
]
