# SPDX-License-Identifier: Apache-2.0
"""地图 Extension：IMap 接口 + YAML 目录驱动实现类。"""

from __future__ import annotations

from extensions.map.engine import get_map, list_provider_ids, reset_engine
from extensions.map.facade import geocode_address, get_imap, get_map_provider, map_provider, map_status, nearby_hotels
from extensions.map.port import IMap, MapProvider

# 兼容旧名
list_map_providers = list_provider_ids

__all__ = [
    "IMap",
    "MapProvider",
    "geocode_address",
    "get_imap",
    "get_map",
    "get_map_provider",
    "list_map_providers",
    "list_provider_ids",
    "map_provider",
    "map_status",
    "nearby_hotels",
    "reset_engine",
]
