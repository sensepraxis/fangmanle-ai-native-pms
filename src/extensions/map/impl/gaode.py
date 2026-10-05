# SPDX-License-Identifier: Apache-2.0
"""高德地图实现（YAML id=gaode，别名 amap）。"""

from __future__ import annotations

from typing import Any, Optional

from infra.i18n import t

# 同源代理图层别名 → 高德 web 瓦片 style
_LAYER_STYLE = {
    "road": "8",
    "vec": "8",
    "vec_w": "8",
    "satellite": "6",
    "img": "6",
    "img_w": "6",
}


class GaodeMap:
    name = "gaode"

    def status(self) -> dict[str, Any]:
        from infra.amap_service import amap_status

        s = amap_status()
        s["provider"] = "gaode"
        s["provider_label"] = t("高德地图")
        s["switch_hint"] = t("可在「系统配置 · 地图配置」切换为天地图")
        s["config_source"] = "db+env"
        s.setdefault("capabilities", {})["tile_proxy"] = True
        return s

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        from infra.amap_service import geocode_address as fn

        out = fn(address, city=city)
        if isinstance(out, dict) and out.get("source") == "amap":
            out = {**out, "source": "gaode"}
        return out

    def geocode_address(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        return self.geocode(address, city=city)

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        from infra.amap_service import nearby_hotels as fn

        out = fn(lng, lat, radius_m, **kwargs)
        if isinstance(out, dict) and out.get("source") == "amap":
            out = {**out, "source": "gaode"}
        return out

    def render_config(self) -> dict[str, Any]:
        from infra.amap_service import amap_js_key, amap_security_code

        key = (amap_js_key() or "").strip()
        sec = (amap_security_code() or "").strip()
        return {
            "engine": "amap",
            "provider_id": "gaode",
            "js_enabled": bool(key),
            "js_key": key or None,
            "security_js_code": sec or None,
            "script_url": f"https://webapi.amap.com/maps?v=2.0&key={key}" if key else None,
            # JS SDK 自带底图；需要同源代理时也可走 /map-tile
            "tiles_url": "/api/v1/system/map-tile",
            "tile_layers": ["road"],
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

        layer = (layer or "road").strip().lower()
        style = _LAYER_STYLE.get(layer)
        if not style:
            raise ValueError(t("非法图层"))
        if not (0 <= int(z) <= 18 and int(x) >= 0 and int(y) >= 0):
            raise ValueError(t("非法瓦片坐标"))
        sub = (int(x) + int(y)) % 4 + 1
        url = (
            f"https://webrd0{sub}.is.autonavi.com/appmaptile?"
            f"lang=zh_cn&size=1&scale=1&style={style}&x={int(x)}&y={int(y)}&z={int(z)}"
        )
        return fetch_bytes(url, referer=referer or "https://www.amap.com/")
