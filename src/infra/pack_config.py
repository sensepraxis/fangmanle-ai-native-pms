# SPDX-License-Identifier: Apache-2.0
"""兼容层：正式入口为 infra.hotel_config（config/hotels/*.yaml）。"""

from __future__ import annotations

from infra.hotel_config import (  # noqa: F401
    DeployChoice,
    alias_map,
    channels_preset,
    get_profile,
    hide_menus_from_profile,
    hotels_dir,
    list_profile_ids,
    load_deploy_doc,
    load_hotel_doc,
    load_packs_doc,
    messaging_spec,
    profiles,
    repo_root,
    reset_hotel_config_cache,
    reset_pack_config_cache,
    resolve_deploy,
    resolve_hotel_file,
    vendor_llm,
    vendor_map,
    vendor_messaging,
    vendor_tax,
)

# 旧名
deploy_dir = hotels_dir
