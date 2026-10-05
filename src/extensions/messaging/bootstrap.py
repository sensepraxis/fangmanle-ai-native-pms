# SPDX-License-Identifier: Apache-2.0
"""按 vendors.messaging 激活私域通道（支持 primary + fallback + packs）。"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_SUPPORTED = frozenset({"wecom", "line", "whatsapp", "webhook"})


def activate_messaging_extension(vendor: str) -> str:
    """兼容旧签名：仅 primary 字符串。"""
    return activate_messaging_spec({"primary": vendor})


def activate_messaging_spec(spec: dict | str) -> str:
    from infra.private_channel import apply_hotel_messaging_spec

    if isinstance(spec, str):
        spec = {"primary": spec}
    primary = str((spec or {}).get("primary") or (spec or {}).get("vendor") or "webhook").strip().lower()
    if primary not in _SUPPORTED:
        log.warning("[Extensions.messaging] unknown vendor=%s, fallback=webhook", primary)
        primary = "webhook"
        spec = {**(spec or {}), "primary": primary}
    vid = apply_hotel_messaging_spec(spec or {"primary": primary})
    log.info(
        "[Extensions.messaging] vendor=%s fallback=%s packs=%s",
        vid,
        (spec or {}).get("fallback"),
        (spec or {}).get("packs"),
    )
    return vid
