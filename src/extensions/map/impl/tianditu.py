# SPDX-License-Identifier: Apache-2.0
"""天地图实现：经 IMap 暴露，服务细节留在 infra.tianditu_service。"""

from __future__ import annotations

from typing import Any, Optional

from infra.i18n import t

_TILE_LAYERS = frozenset({"vec_c", "cva_c", "vec_w", "cva_w", "img_c", "cia_c", "img_w", "cia_w"})


class TiandituMap:
    name = "tianditu"

    def status(self) -> dict[str, Any]:
        from infra.tianditu_service import tianditu_status

        s = tianditu_status()
        s["provider_label"] = t("天地图")
        s["switch_hint"] = t("可在「系统配置 · 地图配置」切换为高德")
        s["config_source"] = "db+env"
        s.setdefault("capabilities", {})["tile_proxy"] = True
        return s

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        from infra.tianditu_service import geocode_address as fn

        return fn(address, city=city)

    def geocode_address(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        return self.geocode(address, city=city)

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        from infra.tianditu_service import nearby_hotels as fn

        return fn(lng, lat, radius_m, **kwargs)

    def render_config(self) -> dict[str, Any]:
        from infra.tianditu_service import tianditu_js_tk

        tk = tianditu_js_tk()
        return {
            "engine": "tianditu",
            "js_enabled": bool(tk),
            "js_key": tk or None,
            "security_js_code": None,
            "script_url": (f"https://api.tianditu.gov.cn/api?v=4.0&tk={tk}" if tk else None),
            "tiles_url": "/api/v1/system/map-tile",
            "tile_layers": ["vec_w", "cva_w"],
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
        from extensions.map.tile_http import fetch_bytes
        from infra.tianditu_service import tianditu_js_tk, tianditu_tk

        layer = (layer or "").strip()
        if layer not in _TILE_LAYERS:
            raise ValueError(t("非法图层"))
        if not (0 <= int(z) <= 18 and int(x) >= 0 and int(y) >= 0):
            raise ValueError(t("非法瓦片坐标"))
        tk = tianditu_js_tk() or tianditu_tk()
        if not tk:
            raise RuntimeError(t("未配置天地图浏览器端 Key，无法代理瓦片"))
        sub = (int(x) + int(y)) % 8
        url = f"https://t{sub}.tianditu.gov.cn/DataServer?T={layer}&x={int(x)}&y={int(y)}&l={int(z)}&tk={tk}"
        return fetch_bytes(url, referer=referer)
