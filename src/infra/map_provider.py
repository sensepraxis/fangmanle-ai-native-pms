# SPDX-License-Identifier: Apache-2.0
"""兼容门面：转发到 extensions.map.facade（业务请改用 extensions.map）。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from extensions.map.facade import (
    enrich_hotel_default_location,
    geocode_address,
    get_imap,
    get_map_provider,
    map_provider,
    map_status,
    nearby_hotels,
    proxy_map_tile,
)
from extensions.map.port import IMap, MapProvider

__all__ = [
    "IMap",
    "MapProvider",
    "enrich_hotel_default_location",
    "geocode_address",
    "get_imap",
    "get_map_provider",
    "map_provider",
    "map_status",
    "nearby_hotels",
    "proxy_map_tile",
]
