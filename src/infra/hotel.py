# SPDX-License-Identifier: Apache-2.0
"""酒店组装：读 config/hotels/<hotel>.yaml → 激活 extensions（map/llm/messaging/tax）。

业务内核不变；差异化全部来自酒店 YAML + extensions 实现类。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

_activated = False
_activating = False
_hotel_id = "demo-cn"
_owned_webhook_default = False


@dataclass(frozen=True)
class HotelAssembly:
    hotel_id: str
    menus_hidden: tuple[str, ...] = ()
    channels_preset: str = "intl"
    private_channel_default: str = "webhook"
    locale: str = "en"
    currency: str = ""


_assembly = HotelAssembly(hotel_id="demo-cn")


def parse_hotel(raw: str | None = None) -> str:
    from infra.hotel_config import alias_map, list_profile_ids, load_hotel_doc

    if raw is not None:
        s = str(raw).strip().lower()
    else:
        s = (os.environ.get("FML_HOTEL") or os.environ.get("FML_PACKS") or "").strip().lower()
        if not s:
            d = load_hotel_doc()
            s = str(d.get("_id") or d.get("hotel") or d.get("id") or "").strip().lower()
        if not s:
            s = "demo-cn"
    if not s or s in ("default",):
        s = "demo-cn"
    # 旧习惯 cn → demo-cn（若存在）
    cat = alias_map()
    if s == "cn" and "demo-cn" in cat:
        s = "demo-cn"
    if s in cat:
        return cat[s]
    first = s.split(",")[0].strip()
    if first in cat:
        return cat[first]
    known = ", ".join(list_profile_ids())
    raise ValueError(f"未知酒店={s!r}。在 config/hotels/<name>.yaml 配置。已有: {known}")


def active_hotel_id() -> str:
    return _hotel_id


def current_assembly() -> HotelAssembly:
    ensure_hotel()
    return _assembly


def hotel_menus_hidden() -> tuple[str, ...]:
    return current_assembly().menus_hidden


def hotel_channel_seeds() -> tuple[tuple[str, str, str, float], ...]:
    ensure_hotel()
    from finance.channel_catalog import ops_channel_seeds

    return ops_channel_seeds(_assembly.channels_preset)


def public_hotel_dict() -> dict[str, Any]:
    ensure_hotel()
    from finance.tax.registry import get_tax_provider
    from infra.hotel_config import list_profile_ids
    from infra.map_provider import map_provider
    from infra.private_channel import resolve_fallback, resolve_packs, resolve_vendor

    tax = get_tax_provider()
    a = _assembly
    from infra.commercial_pack import commercial_enabled, commercial_ui_hidden_menus
    from infra.currency import currency_public_dict

    hidden = list(a.menus_hidden)
    for code in commercial_ui_hidden_menus():
        if code not in hidden:
            hidden.append(code)

    out = {
        "hotel_id": _hotel_id,
        "packs_profile": _hotel_id,  # 兼容旧前端字段
        "private_channel_vendor": resolve_vendor(),
        "private_channel_fallback": resolve_fallback(),
        "private_channel_packs": resolve_packs(),
        "tax_documents_enabled": bool(tax.enabled),
        "tax_provider": tax.name,
        "map_provider": map_provider(None),
        "menus_hidden": hidden,
        "commercial_enabled": commercial_enabled(),
        "channels_preset": a.channels_preset,
        "available_hotels": list_profile_ids(),
        "available_packs": list_profile_ids(),  # 兼容
        "deployment_mode": "single_hotel",  # 单店单进程，非 SaaS 多租户
        "locale": a.locale,
    }
    out.update(currency_public_dict())
    return out


def _apply_private_channel_default(vendor: str) -> None:
    """兼容旧调用：仅设置 primary vendor。"""
    global _owned_webhook_default
    from infra.private_channel import apply_hotel_messaging_spec

    apply_hotel_messaging_spec({"primary": vendor})
    if vendor != "wecom":
        _owned_webhook_default = True


def ensure_hotel() -> str:
    """组装当前酒店：菜单隐藏 + 私域默认 + extensions。"""
    global _activated, _activating, _hotel_id, _assembly
    if _activated:
        return _hotel_id
    if _activating:
        return _hotel_id

    from infra.hotel_config import (
        channels_preset,
        get_profile,
        hide_menus_from_profile,
        load_hotel_doc,
        messaging_spec,
        vendor_messaging,
        vendor_tax,
    )
    from infra.private_channel import apply_hotel_messaging_spec

    _activating = True
    try:
        _hotel_id = parse_hotel()
        doc = load_hotel_doc()
        file_id = str(doc.get("_id") or "").strip().lower()
        if file_id and file_id == _hotel_id:
            prof = dict(doc)
        else:
            prof = get_profile(_hotel_id) or dict(doc)

        hide = hide_menus_from_profile(prof)
        msg_spec = messaging_spec(prof)
        msg = vendor_messaging(prof)
        preset = channels_preset(prof)
        if preset in ("demo-cn", "abc-hotel"):
            preset = "cn"
        elif preset in ("demo-sg", "singapore"):
            preset = "sg"

        _assembly = HotelAssembly(
            hotel_id=_hotel_id,
            menus_hidden=hide,
            channels_preset=preset,
            private_channel_default=msg,
            locale=str(prof.get("locale") or "en"),
            currency=str(prof.get("currency") or ""),
        )
        apply_hotel_messaging_spec(msg_spec)
        if msg != "wecom":
            _owned_webhook_default = True

        try:
            from extensions.bootstrap import ensure_extensions

            ensure_extensions(prof)
        except Exception as e:
            log.warning("[Hotel] ensure_extensions failed: %s", e)

        _activated = True
        log.info(
            "[Hotel] id=%s locale=%s tax=%s file=%s",
            _hotel_id,
            _assembly.locale,
            vendor_tax(prof).get("provider"),
            prof.get("_path"),
        )
        return _hotel_id
    finally:
        _activating = False


def reset_hotel() -> None:
    global _activated, _activating, _hotel_id, _owned_webhook_default, _assembly
    from finance.tax.registry import reset_tax_provider
    from infra.hotel_config import reset_hotel_config_cache
    from infra.maps.registry import reset_map_registry

    try:
        from extensions.bootstrap import reset_extensions

        reset_extensions()
    except Exception:
        pass
    try:
        from extensions.tax import reset_tax_engine

        reset_tax_engine()
    except Exception:
        pass
    reset_map_registry()
    reset_tax_provider()
    reset_hotel_config_cache()
    try:
        from infra.rbac_service import invalidate_rbac_cache

        invalidate_rbac_cache()
    except Exception:
        pass
    if _owned_webhook_default:
        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        _owned_webhook_default = False
        try:
            from infra.private_channel import clear_vendor_cache
            from messaging import reset_channel_cache

            clear_vendor_cache()
            reset_channel_cache()
        except Exception:
            pass
    _activated = False
    _activating = False
    _hotel_id = "demo-cn"
    _assembly = HotelAssembly(hotel_id="demo-cn")


# ---------- 兼容旧 Pack API ----------
def ensure_packs() -> str:
    return ensure_hotel()


def reset_packs() -> None:
    reset_hotel()


def active_profile() -> str:
    return active_hotel_id()


def parse_packs(raw: str | None = None) -> str:
    return parse_hotel(raw)


def current_spec():
    return current_assembly()


def pack_menus_hidden() -> tuple[str, ...]:
    return hotel_menus_hidden()


def pack_channel_seeds() -> tuple[tuple[str, str, str, float], ...]:
    return hotel_channel_seeds()


def public_pack_dict() -> dict[str, Any]:
    return public_hotel_dict()


def list_pack_ids() -> list[str]:
    from infra.hotel_config import list_profile_ids

    return list_profile_ids()
