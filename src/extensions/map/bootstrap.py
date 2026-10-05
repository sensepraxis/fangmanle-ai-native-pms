# SPDX-License-Identifier: Apache-2.0
"""兼容入口：地图注册改由 YAML + engine，不再在此硬编码 register。"""

from __future__ import annotations

from extensions.map.engine import activate_from_vendor, reset_engine


def reset_map_extension() -> None:
    reset_engine()
    # 同步旧 registry 清空（遗留代码可能仍引用）
    try:
        from infra.maps.registry import reset_map_registry

        reset_map_registry()
    except Exception:
        pass


def activate_map_extension(provider_id: str) -> str:
    return activate_from_vendor(provider_id)
