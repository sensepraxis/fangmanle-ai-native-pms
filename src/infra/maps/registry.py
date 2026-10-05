# SPDX-License-Identifier: Apache-2.0
"""兼容薄封装：真实注册表在 extensions.map.engine（YAML 驱动）。"""

from __future__ import annotations

from typing import Optional

from extensions.map.engine import (
    force_active,
    forced_active,
    get_instance,
    get_map,
    list_provider_ids,
    reset_engine,
    resolve_id,
)
from extensions.map.port import IMap, MapProvider


def register_map_provider(name: str, provider: MapProvider) -> None:
    """遗留 API：仍接受手工注册，写入引擎缓存（优先用 YAML class）。"""
    from extensions.map import engine as eng

    key = resolve_id(name)
    eng._instances[key] = provider  # noqa: SLF001 — 兼容桥


def force_map_provider(name: Optional[str]) -> None:
    force_active(name)


def forced_map_provider() -> Optional[str]:
    return forced_active()


def get_registered_map_provider(name: str) -> Optional[IMap]:
    try:
        return get_instance(name)
    except Exception:
        return None


def list_map_providers() -> list[str]:
    return list_provider_ids()


def reset_map_registry() -> None:
    reset_engine()


__all__ = [
    "force_map_provider",
    "forced_map_provider",
    "get_map",
    "get_registered_map_provider",
    "list_map_providers",
    "register_map_provider",
    "reset_map_registry",
]
