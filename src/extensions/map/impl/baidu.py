# SPDX-License-Identifier: Apache-2.0
"""百度地图：密钥走 AppSetting / 环境变量；有 AK 时地理编码走 Geocoding API。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from extensions.map.impl.noop import NoopMap
from infra.i18n import t


def _baidu_ak() -> str:
    from infra.map_config import runtime_get

    return runtime_get("baidu_ak", "BAIDU_MAP_AK", "BAIDU_MAP_KEY")


def _baidu_js_ak() -> str:
    from infra.map_config import runtime_get

    return runtime_get("baidu_js_ak", "BAIDU_MAP_JS_AK") or _baidu_ak()


def _http_get_json(url: str, timeout: float = 12.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fangmanle-pms/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


class BaiduMap:
    name = "baidu"

    def __init__(self) -> None:
        self._fallback = NoopMap()

    def status(self) -> dict[str, Any]:
        s = self._fallback.status()
        key = _baidu_ak()
        js = _baidu_js_ak()
        s.update(
            {
                "provider": "baidu",
                "provider_label": t("百度地图"),
                "mode": "live" if key else "manual",
                "js_key_ok": bool(js),
                "web_enabled": bool(key),
                "note": t("已配置百度地图 AK。" if key else "已选择百度地图。未配 AK 时请手工填经纬度。"),
            }
        )
        caps = s.setdefault("capabilities", {})
        caps["tile_proxy"] = False
        caps["geocode"] = bool(key)
        caps["geocode_by_address"] = bool(key)
        return s

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        addr = (address or "").strip()
        if not addr:
            raise ValueError(t("请输入本店地址"))
        key = _baidu_ak()
        if not key:
            out = self._fallback.geocode(addr, city=city)
            out["source"] = "baidu"
            out["note"] = t("未配置百度地图 AK，无法地理编码")
            return out
        q = addr if not city else f"{city}{addr}"
        url = "https://api.map.baidu.com/geocoding/v3/?" + urllib.parse.urlencode(
            {"address": q, "output": "json", "ak": key}
        )
        try:
            data = _http_get_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise RuntimeError(t("百度地理编码请求失败：{err}", err=str(e))) from e
        st = data.get("status")
        loc = (data.get("result") or {}).get("location") or {}
        if st not in (0, "0") or loc.get("lng") is None:
            raise RuntimeError(t("百度地理编码失败：{st}", st=str(st)))
        return {
            "address": addr,
            "city": city or "",
            "lng": loc.get("lng"),
            "lat": loc.get("lat"),
            "source": "baidu",
            "mode": "live",
        }

    def geocode_address(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        return self.geocode(address, city=city)

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        out = self._fallback.nearby_hotels(lng, lat, radius_m, **kwargs)
        out["source"] = "baidu"
        return out

    def render_config(self) -> dict[str, Any]:
        key = _baidu_js_ak()
        return {
            "engine": "baidu",
            "provider_id": "baidu",
            "js_enabled": bool(key),
            "js_key": key or None,
            "security_js_code": None,
            "script_url": (f"https://api.map.baidu.com/api?v=3.0&ak={key}" if key else None),
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
