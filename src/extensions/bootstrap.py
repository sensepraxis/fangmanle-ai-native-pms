# SPDX-License-Identifier: Apache-2.0
"""启动时按酒店 YAML 组装 Extensions：map / llm / messaging / tax。"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_activated = False


def reset_extensions() -> None:
    global _activated
    _activated = False
    try:
        from extensions.map.bootstrap import reset_map_extension

        reset_map_extension()
    except Exception:
        pass
    try:
        from extensions.llm.registry import reset_llm_extension

        reset_llm_extension()
    except Exception:
        pass
    try:
        from extensions.tax import reset_tax_engine

        reset_tax_engine()
    except Exception:
        pass


def ensure_extensions(profile: dict[str, Any] | None = None) -> dict[str, str]:
    """对齐当前酒店 YAML 的 vendors，返回 {map, llm, messaging, tax}。"""
    global _activated
    if profile is None:
        from infra.hotel import active_hotel_id, ensure_hotel
        from infra.hotel_config import get_profile, load_hotel_doc

        ensure_hotel()
        profile = get_profile(active_hotel_id()) or load_hotel_doc()

    from infra.hotel_config import messaging_spec, vendor_llm, vendor_map, vendor_messaging, vendor_tax

    map_id = vendor_map(profile)
    msg_spec = messaging_spec(profile)
    msg_id = vendor_messaging(profile)
    llm_id = vendor_llm(profile)
    tax_cfg = vendor_tax(profile)

    from extensions.llm.registry import activate_llm_extension
    from extensions.map.bootstrap import activate_map_extension
    from extensions.messaging.bootstrap import activate_messaging_spec
    from extensions.tax import activate_tax

    activate_map_extension(map_id)
    active_llm = activate_llm_extension(llm_id or None)
    activate_messaging_spec(msg_spec)
    tax_id = activate_tax(tax_cfg)

    _activated = True
    out = {"map": map_id, "llm": active_llm, "messaging": msg_id, "tax": tax_id}
    log.info("[Extensions] active=%s", out)
    return out
