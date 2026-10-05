# SPDX-License-Identifier: Apache-2.0
"""无图商：只支持手工经纬度。"""

from __future__ import annotations

from typing import Any, Optional

from infra.i18n import t


class NoopMap:
    name = "noop"

    def status(self) -> dict[str, Any]:
        return {
            "provider": "noop",
            "provider_label": t("手工坐标"),
            "web_enabled": False,
            "js_enabled": False,
            "js_key": None,
            "security_js_code": None,
            "mode": "noop",
            "note": t("本部署未接地图服务；请手工填写经纬度。"),
            "js_key_required": False,
            "js_key_ok": False,
            "docs": {},
            "capabilities": {
                "geocode_by_address": False,
                "nearby_hotels_in_radius": False,
                "draw_circle_on_map": False,
                "checkbox_select_competitors": False,
            },
            "switch_hint": "",
            "config_source": "pack",
            "enabled": True,
        }

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        addr = (address or "").strip()
        if not addr:
            raise ValueError(t("请输入本店地址"))
        return {
            "address": addr,
            "city": city or "",
            "lng": None,
            "lat": None,
            "source": "noop",
            "note": t("未接地图服务，无法地理编码"),
        }

    # 兼容旧 Protocol 方法名
    def geocode_address(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        return self.geocode(address, city=city)

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        return {
            "source": "noop",
            "radius_m": radius_m,
            "center": {"lng": lng, "lat": lat},
            "count": 0,
            "hotels": [],
            "note": t("未接地图服务，无周边 POI"),
        }

    def render_config(self) -> dict[str, Any]:
        return {
            "engine": "noop",
            "js_enabled": False,
            "js_key": None,
            "security_js_code": None,
            "script_url": None,
            "tiles_url": None,
            "tile_layers": [],
        }

    def js_config(self) -> dict[str, Any]:
        return self.render_config()

    def fetch_tile(
        self,
        layer: str,
        z: int,
        y: int,
        x: int,
        *,
        referer: str = "",
    ) -> Optional[tuple[bytes, str]]:
        return None
