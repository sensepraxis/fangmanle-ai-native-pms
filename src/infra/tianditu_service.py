# SPDX-License-Identifier: Apache-2.0
"""天地图 Web 服务：地理编码 + 周边搜索（酒店）。

申请 Key（旧 console.tianditu.gov.cn 已迁移）：
- 登录 https://oauth.tianditu.gov.cn/login
- 注册 https://uums.tianditu.gov.cn/register
- 控制台 https://cloudcenter.tianditu.gov.cn/ → 开发管理 → 创建应用
文档：
- 地理编码 http://lbs.tianditu.gov.cn/server/geocoding.html
- 搜索 V2  http://lbs.tianditu.gov.cn/server/search2.html
- JS API 4.0 https://lbs.tianditu.gov.cn/api/js4.0/guide.html

环境变量：
- TIANDITU_TK      服务端 Key（地理编码 / 周边搜索）
- TIANDITU_JS_TK   浏览器端 Key（地图展示，可与上面相同若控制台允许）
"""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from typing import Any, Optional

# 与 amap 兜底共用城市中心（近似）
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


def tianditu_tk() -> str:
    from infra.map_config import runtime_get

    return runtime_get("tianditu_tk", "TIANDITU_TK", "TIANDITU_KEY")


def tianditu_js_tk() -> str:
    """浏览器端 Key（不可回落到服务器端 Key，否则瓦片 403）。"""
    from infra.map_config import runtime_get

    return runtime_get("tianditu_js_tk", "TIANDITU_JS_TK")


def tianditu_status() -> dict:
    web = bool(tianditu_tk())
    js = bool(tianditu_js_tk())
    return {
        "provider": "tianditu",
        "provider_label": "天地图",
        "web_enabled": web,
        "js_enabled": js,
        "js_key": tianditu_js_tk() if js else None,
        "security_js_code": None,
        "mode": "live" if web else "demo",
        "note": (
            "已配置天地图：服务端 Key 用于编码/搜索；浏览器端 Key 用于底图瓦片（二者不可互换）。"
            if web and js
            else (
                "已配置服务端 Key，但缺少浏览器端 Key：底图会裂图。请在系统配置填写「浏览器端」密钥。"
                if web and not js
                else "未配置 TIANDITU_TK：定位 + 模拟周边酒店。申请：cloudcenter.tianditu.gov.cn"
            )
        ),
        "js_key_required": True,
        "js_key_ok": js,
        "docs": {
            "apply_key": "https://cloudcenter.tianditu.gov.cn/",
            "login": "https://oauth.tianditu.gov.cn/login",
            "register": "https://uums.tianditu.gov.cn/register",
            "geocode": "http://lbs.tianditu.gov.cn/server/geocoding.html",
            "search": "http://lbs.tianditu.gov.cn/server/search2.html",
            "js_api": "https://lbs.tianditu.gov.cn/api/js4.0/guide.html",
        },
        "capabilities": {
            "geocode_by_address": True,
            "nearby_hotels_in_radius": True,
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

    tk = tianditu_tk()
    if tk:
        # ds 必须是 JSON 字符串
        ds = json.dumps({"keyWord": addr}, ensure_ascii=False)
        qs = urllib.parse.urlencode({"ds": ds, "tk": tk})
        data = _http_get_json(f"https://api.tianditu.gov.cn/geocoder?{qs}")
        # status "0" 成功
        if str(data.get("status")) not in ("0", "000", "1000"):
            raise RuntimeError(data.get("msg") or data.get("message") or "天地图地理编码失败")
        loc = data.get("location") or {}
        lon = loc.get("lon")
        lat = loc.get("lat")
        if lon is None or lat is None:
            raise RuntimeError("天地图未返回有效坐标")
        return {
            "address": data.get("formatted_address") or addr,
            "lng": float(lon),
            "lat": float(lat),
            "city": (data.get("addressComponent") or {}).get("city") or city,
            "adcode": None,
            "source": "tianditu",
        }

    # 兜底
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
    digest = sum(ord(c) for c in addr) % 97
    lng, lat = _offset_lnglat(lng, lat, (digest - 48) * 40, (digest % 17 - 8) * 40)
    return {
        "address": addr,
        "lng": lng,
        "lat": lat,
        "city": hit_city,
        "adcode": None,
        "source": "demo",
        "note": "定位（未配置 TIANDITU_TK）。配置后走天地图真实地理编码。",
    }


def nearby_hotels(
    lng: float,
    lat: float,
    radius_m: int = 3000,
    *,
    keywords: str = "酒店",
    page_size: int = 25,
) -> dict:
    radius_m = max(500, min(int(radius_m), 10000))  # 天地图周边搜索文档：10 公里内
    tk = tianditu_tk()
    if tk:
        # 「酒店」在部分城区 POI 词库命中为 0；依次回退宾馆/旅馆等
        kw_list: list[str] = []
        for k in [keywords, "宾馆", "旅馆", "饭店", "住宿"]:
            k = (k or "").strip()
            if k and k not in kw_list:
                kw_list.append(k)

        hotels: list[dict] = []
        last_raw: dict = {}
        for kw in kw_list:
            post = {
                "keyWord": kw,
                "level": 12,
                "queryRadius": str(radius_m),
                "pointLonlat": f"{lng},{lat}",
                "queryType": "3",
                "start": "0",
                "count": str(min(page_size, 50)),
                "show": "2",
            }
            qs = urllib.parse.urlencode(
                {
                    "postStr": json.dumps(post, ensure_ascii=False),
                    "type": "query",
                    "tk": tk,
                }
            )
            data = _http_get_json(f"https://api.tianditu.gov.cn/v2/search?{qs}")
            last_raw = data
            pois_raw = data.get("pois") or data.get("poi") or []
            if isinstance(pois_raw, dict):
                pois_raw = [pois_raw]
            if not pois_raw:
                continue
            for p in pois_raw:
                lonlat = str(p.get("lonlat") or p.get("pointLonlat") or "")
                parts = lonlat.replace(" ", "").split(",")
                if len(parts) != 2:
                    continue
                try:
                    plng, plat = float(parts[0]), float(parts[1])
                except ValueError:
                    continue
                name = str(p.get("name") or "")
                type_name = str(p.get("typeName") or p.get("poiType") or "")
                # 住宿类启发过滤（避免「住宿」关键字扫到小区）
                blob = name + type_name
                if kw in ("住宿",) and not any(
                    x in blob for x in ("酒店", "宾馆", "旅馆", "饭店", "客栈", "民宿", "旅店", "公寓")
                ):
                    continue
                dist_km = haversine_km(lng, lat, plng, plat)
                hotels.append(
                    {
                        "poi_id": str(p.get("hotPointID") or p.get("poiId") or p.get("id") or f"{plng},{plat}"),
                        "comp_name": name or "未命名",
                        "address": p.get("address") or p.get("address_name") or "",
                        "comp_lng": plng,
                        "comp_lat": plat,
                        "distance_km": dist_km,
                        "tel": p.get("phone") or p.get("tel") or "",
                        "type": type_name,
                        "data_source": "tianditu",
                        "source_ref": f"tianditu:{p.get('hotPointID') or name}",
                        "matched_keyword": kw,
                    }
                )
            if hotels:
                break

        # 去重
        seen = set()
        uniq = []
        for h in hotels:
            k = h["poi_id"] or h["comp_name"]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(h)
        uniq.sort(key=lambda x: x["distance_km"])
        return {
            "source": "tianditu",
            "radius_m": radius_m,
            "center": {"lng": lng, "lat": lat},
            "count": len(uniq),
            "hotels": uniq[:page_size],
            "note": (None if uniq else "天地图未检索到周边住宿类 POI（该区域词库可能稀疏），可手工添加竞品。"),
            "raw_status": last_raw.get("status"),
        }

    # 周边
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
                "data_source": "tianditu_demo",
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
        "note": "数据。配置 TIANDITU_TK 后将检索天地图真实周边 POI。",
    }


def enrich_hotel_default_location(db, hotel_id: int) -> dict[str, Any]:
    from models import Hotel

    h = db.get(Hotel, hotel_id)
    if not h:
        return {}
    return {
        "hotel_name": h.name,
        "city": h.city,
        "address": h.address or (f"{h.city or ''}{h.name}" if h.name else ""),
    }
