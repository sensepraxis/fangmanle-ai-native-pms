# SPDX-License-Identifier: Apache-2.0
"""高德地图 Web 服务：地理编码 + 周边酒店 POI。

能：以本店为圆心、按半径（如 3/5km）列出周边「住宿服务/酒店」POI，供勾选为竞品。
Key：环境变量 AMAP_KEY（Web 服务）/ AMAP_JS_KEY（JS API，可选）/ AMAP_SECURITY_CODE（可选）。
无 Key 时走兜底（城市中心近似定位 + 模拟周边酒店），保证流程可跑通。
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

CITY_CENTERS = {
    "北京": (116.397428, 39.90923),
    "上海": (121.473701, 31.230416),
    "广州": (113.264385, 23.12911),
    "深圳": (114.085947, 22.547),
    "杭州": (120.15507, 30.274084),
    "成都": (104.065735, 30.659462),
    "重庆": (106.551556, 29.563009),
    "武汉": (114.298572, 30.584355),
    "南京": (118.796877, 32.060255),
    "西安": (108.940175, 34.341568),
}


def amap_web_key() -> str:
    from infra.map_config import runtime_get

    return runtime_get("amap_web_key", "AMAP_KEY", "AMAP_WEB_KEY")


def amap_js_key() -> str:
    from infra.map_config import runtime_get

    return runtime_get("amap_js_key", "AMAP_JS_KEY") or amap_web_key()


def amap_security_code() -> str:
    from infra.map_config import runtime_get

    return runtime_get("amap_security_code", "AMAP_SECURITY_CODE")


def amap_status() -> dict:
    web = bool(amap_web_key())
    js = bool(amap_js_key())
    return {
        "provider": "amap",
        "web_enabled": web,
        "js_enabled": js,
        "js_key": amap_js_key() if js else None,
        "security_js_code": amap_security_code() or None,
        "mode": "live" if web else "demo",
        "note": (
            "已配置高德 Key：周边酒店为真实 POI 检索。"
            if web
            else "未配置 AMAP_KEY：使用定位与模拟周边酒店；手工录入始终可用。"
        ),
        "capabilities": {
            "geocode_by_address": True,
            "nearby_hotels_in_radius": True,  # 高德原生支持；无 Key 时用数据
            "draw_circle_on_map": True,
            "checkbox_select_competitors": True,
        },
    }


def _http_get_json(url: str, timeout: float = 12.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fangmanle-pms/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(min(1.0, math.sqrt(a))), 2)


def _offset_lnglat(lng: float, lat: float, east_m: float, north_m: float) -> tuple[float, float]:
    dlat = north_m / 111320.0
    dlng = east_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    return (round(lng + dlng, 6), round(lat + dlat, 6))


def geocode_address(address: str, city: Optional[str] = None) -> dict:
    addr = (address or "").strip()
    if not addr:
        raise ValueError("请输入本店地址")

    key = amap_web_key()
    if key:
        qs = urllib.parse.urlencode(
            {
                "key": key,
                "address": addr,
                "city": (city or "").strip(),
            }
        )
        data = _http_get_json(f"https://restapi.amap.com/v3/geocode/geo?{qs}")
        if str(data.get("status")) != "1" or not data.get("geocodes"):
            raise RuntimeError(data.get("info") or "高德地理编码失败")
        g = data["geocodes"][0]
        loc = str(g.get("location") or "").split(",")
        if len(loc) != 2:
            raise RuntimeError("高德未返回有效坐标")
        lng, lat = float(loc[0]), float(loc[1])
        return {
            "address": g.get("formatted_address") or addr,
            "lng": lng,
            "lat": lat,
            "city": g.get("city") or g.get("province") or city,
            "adcode": g.get("adcode"),
            "source": "amap",
        }

    # 兜底：按城市名匹配中心点
    hit_city = None
    for name in CITY_CENTERS:
        if name in addr or (city and name in str(city)):
            hit_city = name
            break
    if not hit_city and city:
        for name in CITY_CENTERS:
            if name in str(city):
                hit_city = name
                break
    hit_city = hit_city or "广州"
    lng, lat = CITY_CENTERS[hit_city]
    # 轻微偏移，避免所有酒店叠在同一点
    digest = sum(ord(c) for c in addr) % 97
    lng, lat = _offset_lnglat(lng, lat, (digest - 48) * 40, (digest % 17 - 8) * 40)
    return {
        "address": addr,
        "lng": lng,
        "lat": lat,
        "city": hit_city,
        "adcode": None,
        "source": "demo",
        "note": "定位（未配置 AMAP_KEY）。配置 Key 后将使用高德真实地理编码。",
    }


def nearby_hotels(
    lng: float,
    lat: float,
    radius_m: int = 3000,
    *,
    keywords: str = "酒店",
    page_size: int = 25,
) -> dict:
    radius_m = max(500, min(int(radius_m), 50000))
    key = amap_web_key()
    if key:
        qs = urllib.parse.urlencode(
            {
                "key": key,
                "location": f"{lng},{lat}",
                "keywords": keywords or "酒店",
                "types": "100000",  # 住宿服务
                "radius": radius_m,
                "offset": min(page_size, 25),
                "page": 1,
                "extensions": "base",
                "sortrule": "distance",
            }
        )
        data = _http_get_json(f"https://restapi.amap.com/v3/place/around?{qs}")
        if str(data.get("status")) != "1":
            raise RuntimeError(data.get("info") or "高德周边搜索失败")
        pois = []
        for p in data.get("pois") or []:
            loc = str(p.get("location") or "").split(",")
            if len(loc) != 2:
                continue
            plng, plat = float(loc[0]), float(loc[1])
            dist_m = p.get("distance")
            try:
                dist_km = (
                    round(float(dist_m) / 1000.0, 2) if dist_m not in (None, "") else haversine_km(lng, lat, plng, plat)
                )
            except (TypeError, ValueError):
                dist_km = haversine_km(lng, lat, plng, plat)
            pois.append(
                {
                    "poi_id": p.get("id"),
                    "comp_name": p.get("name"),
                    "address": p.get("address") or p.get("pname") or "",
                    "comp_lng": plng,
                    "comp_lat": plat,
                    "distance_km": dist_km,
                    "tel": p.get("tel") or "",
                    "type": p.get("type") or "",
                    "data_source": "amap",
                    "source_ref": f"amap:{p.get('id')}",
                }
            )
        return {
            "source": "amap",
            "radius_m": radius_m,
            "center": {"lng": lng, "lat": lat},
            "count": len(pois),
            "hotels": pois,
        }

    # 周边酒店（相对圆心均匀分布，落在半径内）
    demo_names = [
        "如家精选酒店",
        "汉庭酒店",
        "全季酒店",
        "桔子酒店",
        "亚朵酒店",
        "锦江之星",
        "7天优品",
        "维也纳酒店",
        "速8酒店",
        "希尔顿欢朋",
        "假日酒店",
        "格林豪泰",
    ]
    hotels = []
    for i, name in enumerate(demo_names):
        # 0.35R ~ 0.92R 之间分布
        ratio = 0.35 + (i % 7) * 0.08
        ang = (i * 47) % 360
        east = radius_m * ratio * math.cos(math.radians(ang))
        north = radius_m * ratio * math.sin(math.radians(ang))
        plng, plat = _offset_lnglat(lng, lat, east, north)
        dist = haversine_km(lng, lat, plng, plat)
        hotels.append(
            {
                "poi_id": f"demo_{i}",
                "comp_name": name,
                "address": f"距本店约 {dist} 公里（ POI）",
                "comp_lng": plng,
                "comp_lat": plat,
                "distance_km": dist,
                "tel": "",
                "type": "住宿服务",
                "data_source": "amap_demo",
                "source_ref": f"demo:{i}",
            }
        )
    hotels.sort(key=lambda x: x["distance_km"])
    return {
        "source": "demo",
        "radius_m": radius_m,
        "center": {"lng": lng, "lat": lat},
        "count": len(hotels),
        "hotels": hotels,
        "note": "数据。配置 AMAP_KEY 后将检索真实周边酒店。",
    }


def enrich_hotel_default_location(db, hotel_id: int) -> dict[str, Any]:
    """从酒店档案给出默认地址建议。"""
    from models import Hotel

    h = db.get(Hotel, hotel_id)
    if not h:
        return {}
    return {
        "hotel_name": h.name,
        "city": h.city,
        "address": h.address or (f"{h.city or ''}{h.name}" if h.name else ""),
    }
