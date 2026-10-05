# SPDX-License-Identifier: Apache-2.0
"""Google Maps：密钥走 AppSetting / 环境变量；有 Key 时地理编码走 Geocoding API。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from extensions.map.impl.noop import NoopMap
from infra.i18n import t

_LAYERS = frozenset({"m", "s", "y", "t", "road", "satellite", "hybrid"})


def _google_key() -> str:
    from infra.map_config import runtime_get

    return runtime_get("google_api_key", "GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_KEY")


def _http_get_json(url: str, timeout: float = 12.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fangmanle-pms/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


class GoogleMap:
    name = "google"

    def __init__(self) -> None:
        self._fallback = NoopMap()

    def status(self) -> dict[str, Any]:
        s = self._fallback.status()
        key = _google_key()
        s.update(
            {
                "provider": "google",
                "provider_label": "Google Maps",
                "mode": "live" if key else "manual",
                "js_key_ok": bool(key),
                "web_enabled": bool(key),
                "note": t(
                    "已配置 Google Maps API Key。"
                    if key
                    else "已选择 Google Maps。未配 API Key 时地理编码为手工模式；瓦片代理可用。"
                ),
            }
        )
        caps = s.setdefault("capabilities", {})
        caps["tile_proxy"] = True
        caps["geocode"] = bool(key)
        caps["geocode_by_address"] = bool(key)
        caps["nearby"] = False
        caps["js_maps"] = bool(key)
        return s

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        addr = (address or "").strip()
        if not addr:
            raise ValueError(t("请输入本店地址"))
        key = _google_key()
        if not key:
            out = self._fallback.geocode(addr, city=city)
            out["source"] = "google"
            out["mode"] = "manual"
            out["note"] = t("未配置 Google API Key，无法地理编码")
            return out
        q = addr if not city else f"{city} {addr}"
        url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode({"address": q, "key": key})
        try:
            data = _http_get_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise RuntimeError(t("Google 地理编码请求失败：{err}", err=str(e))) from e
        st = str(data.get("status") or "")
        if st != "OK" or not (data.get("results") or []):
            raise RuntimeError(t("Google 地理编码失败：{st}", st=st or "UNKNOWN"))
        loc = ((data["results"][0] or {}).get("geometry") or {}).get("location") or {}
        return {
            "address": addr,
            "city": city or "",
            "lng": loc.get("lng"),
            "lat": loc.get("lat"),
            "source": "google",
            "mode": "live",
            "formatted": (data["results"][0] or {}).get("formatted_address") or addr,
        }

    def geocode_address(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        return self.geocode(address, city=city)

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        out = self._fallback.nearby_hotels(lng, lat, radius_m, **kwargs)
        out["source"] = "google"
        return out

    def render_config(self) -> dict[str, Any]:
        key = _google_key()
        return {
            "engine": "google",
            "provider_id": "google",
            "js_enabled": bool(key),
            "js_key": key or None,
            "security_js_code": None,
            "script_url": (f"https://maps.googleapis.com/maps/api/js?key={key}" if key else None),
            "tiles_url": "/api/v1/system/map-tile",
            "tile_layers": ["m"],
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

        layer = (layer or "m").strip().lower()
        lyrs = {"road": "m", "satellite": "s", "hybrid": "y"}.get(layer, layer)
        if lyrs not in _LAYERS and lyrs not in ("m", "s", "y", "t"):
            raise ValueError(t("非法图层"))
        if not (0 <= int(z) <= 21 and int(x) >= 0 and int(y) >= 0):
            raise ValueError(t("非法瓦片坐标"))
        sub = (int(x) + int(y)) % 4
        url = f"https://mt{sub}.google.com/vt/lyrs={lyrs}&x={int(x)}&y={int(y)}&z={int(z)}"
        key = _google_key()
        if key:
            url += f"&key={key}"
        return fetch_bytes(url, referer=referer or "https://maps.google.com/")
