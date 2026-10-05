# SPDX-License-Identifier: Apache-2.0
"""业务防腐门面：价格助手 / 路由只 import 本模块，不碰图商实现类。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from extensions.map.engine import (
    active_id,
    force_active,
    forced_active,
    get_map,
    list_provider_ids,
    resolve_id,
)
from extensions.map.port import IMap


def _ensure_pack_wired() -> None:
    from infra.hotel import ensure_hotel

    ensure_hotel()


def current_map_id(db: Optional[Session] = None) -> str:
    from infra.map_config import apply_runtime_from_db, runtime_provider

    _ensure_pack_wired()
    if db is not None:
        apply_runtime_from_db(db)
    forced = forced_active()
    if forced:
        return forced
    return resolve_id(runtime_provider() or active_id())


def get_imap(db: Optional[Session] = None) -> IMap:
    """取得当前 IMap 实现（由 YAML 目录 + vendors.map / DB 决定）。"""
    from infra.map_config import apply_runtime_from_db

    _ensure_pack_wired()
    if db is not None:
        apply_runtime_from_db(db)
    return get_map(current_map_id(None))


def map_status(db: Optional[Session] = None) -> dict[str, Any]:
    from infra.map_config import apply_runtime_from_db, load_map_config

    cfg = apply_runtime_from_db(db) if db is not None else load_map_config(None)
    prov = get_imap(None)
    s = prov.status()
    s["enabled"] = bool(cfg.get("enabled", True))
    s.setdefault("config_source", "db+env")
    s["engine"] = prov.name
    s["provider"] = prov.name
    s["js_config"] = prov.render_config()
    s["available_providers"] = list_provider_ids()
    return s


def geocode_address(address: str, city: Optional[str] = None, db: Optional[Session] = None) -> dict[str, Any]:
    if db is not None:
        from infra.map_config import apply_runtime_from_db

        apply_runtime_from_db(db)
    return get_imap(None).geocode(address, city=city)


def nearby_hotels(
    lng: float,
    lat: float,
    radius_m: int = 3000,
    db: Optional[Session] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if db is not None:
        from infra.map_config import apply_runtime_from_db

        apply_runtime_from_db(db)
    return get_imap(None).nearby_hotels(lng, lat, radius_m, **kwargs)


def enrich_hotel_default_location(db: Session, hotel_id: int) -> dict[str, Any]:
    from infra.map_config import apply_runtime_from_db
    from models import Hotel

    apply_runtime_from_db(db)
    h = db.get(Hotel, hotel_id)
    if not h:
        return {}
    return {
        "hotel_name": h.name,
        "city": h.city,
        "address": h.address or (f"{h.city or ''}{h.name}" if h.name else ""),
    }


def get_map_provider(db: Optional[Session] = None) -> IMap:
    return get_imap(db)


def map_provider(db: Optional[Session] = None) -> str:
    return current_map_id(db)


def proxy_map_tile(
    layer: str,
    z: int,
    y: int,
    x: int,
    *,
    referer: str = "",
    db: Optional[Session] = None,
) -> tuple[bytes, str]:
    """
    同源瓦片代理：交给当前 IMap.fetch_tile。
    返回 (body, media_type)；不支持时抛 ValueError / RuntimeError。
    """
    if db is not None:
        from infra.map_config import apply_runtime_from_db

        apply_runtime_from_db(db)
    prov = get_imap(None)
    out = prov.fetch_tile(layer, z, y, x, referer=referer)
    if out is None:
        raise RuntimeError(f"当前地图提供方 {getattr(prov, 'name', '?')} 未启用瓦片代理（可用官方 JS SDK 底图）")
    return out


__all__ = [
    "IMap",
    "current_map_id",
    "enrich_hotel_default_location",
    "force_active",
    "geocode_address",
    "get_imap",
    "get_map_provider",
    "map_provider",
    "map_status",
    "nearby_hotels",
    "proxy_map_tile",
]
