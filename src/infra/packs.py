# SPDX-License-Identifier: Apache-2.0
"""兼容层：正式入口为 infra.hotel（酒店 YAML 组装）。"""

from __future__ import annotations

from infra.hotel import (
    HotelAssembly,
    active_hotel_id,
    active_profile,
    current_assembly,
    current_spec,
    ensure_hotel,
    ensure_packs,
    hotel_channel_seeds,
    hotel_menus_hidden,
    list_pack_ids,
    pack_channel_seeds,
    pack_menus_hidden,
    parse_hotel,
    parse_packs,
    public_hotel_dict,
    public_pack_dict,
    reset_hotel,
    reset_packs,
)

__all__ = [
    "HotelAssembly",
    "active_hotel_id",
    "active_profile",
    "current_assembly",
    "current_spec",
    "ensure_hotel",
    "ensure_packs",
    "hotel_channel_seeds",
    "hotel_menus_hidden",
    "list_pack_ids",
    "pack_channel_seeds",
    "pack_menus_hidden",
    "parse_hotel",
    "parse_packs",
    "public_hotel_dict",
    "public_pack_dict",
    "reset_hotel",
    "reset_packs",
]
