# SPDX-License-Identifier: Apache-2.0
"""地图对接配置：落库 AppSetting.key=map，密钥优先库、环境变量兜底。"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import AppSetting

MAP_SETTING_KEY = "map"

# provider 空字符串 = 跟随酒店 YAML vendors.map，不要用默认 tianditu 盖掉国际店
DEFAULT_MAP_CONFIG: dict[str, Any] = {
    "enabled": True,
    "provider": "",
    "tianditu_tk": "",
    "tianditu_js_tk": "",
    "amap_web_key": "",
    "amap_js_key": "",
    "amap_security_code": "",
    "google_api_key": "",
    "baidu_ak": "",
    "baidu_js_ak": "",
}

SECRET_KEYS = (
    "tianditu_tk",
    "tianditu_js_tk",
    "amap_web_key",
    "amap_js_key",
    "amap_security_code",
    "google_api_key",
    "baidu_ak",
    "baidu_js_ak",
)

CANONICAL_PROVIDERS = ("tianditu", "gaode", "baidu", "google", "noop")

# 配置页字段（与 LLM 卡片同一交互）
PROVIDER_UI: dict[str, dict[str, Any]] = {
    "tianditu": {
        "label": "天地图",
        "hint": "自然资源部公共服务底图，适合国内合规场景。",
        "docs_url": "https://cloudcenter.tianditu.gov.cn/",
        "fields": [
            {"key": "tianditu_tk", "label": "服务端 Key"},
            {"key": "tianditu_js_tk", "label": "浏览器 JS Key"},
        ],
    },
    "gaode": {
        "label": "高德地图",
        "hint": "国内 Web 服务 + JS API；周边酒店 POI 检索。",
        "docs_url": "https://console.amap.com/",
        "fields": [
            {"key": "amap_web_key", "label": "Web 服务 Key"},
            {"key": "amap_js_key", "label": "JS API Key"},
            {"key": "amap_security_code", "label": "安全密钥"},
        ],
    },
    "baidu": {
        "label": "百度地图",
        "hint": "国内图商；地理编码使用服务端 AK，浏览器端可另配 JS AK。",
        "docs_url": "https://lbsyun.baidu.com/",
        "fields": [
            {"key": "baidu_ak", "label": "服务端 AK"},
            {"key": "baidu_js_ak", "label": "浏览器 JS AK"},
        ],
    },
    "google": {
        "label": "Google Maps",
        "hint": "国际店常用。需启用 Maps JavaScript API / Geocoding API。",
        "docs_url": "https://console.cloud.google.com/google/maps-apis",
        "fields": [
            {"key": "google_api_key", "label": "API Key"},
        ],
    },
    "noop": {
        "label": "手工坐标",
        "hint": "不接图商，价格助手等场景请手工填写经纬度。",
        "docs_url": "",
        "fields": [],
    },
}

_RUNTIME: dict[str, Any] = {}


def _env_defaults() -> dict[str, Any]:
    return {
        "provider": (os.environ.get("MAP_PROVIDER") or "").strip().lower(),
        "tianditu_tk": (os.environ.get("TIANDITU_TK") or os.environ.get("TIANDITU_KEY") or "").strip(),
        "tianditu_js_tk": (os.environ.get("TIANDITU_JS_TK") or "").strip(),
        "amap_web_key": (os.environ.get("AMAP_KEY") or os.environ.get("AMAP_WEB_KEY") or "").strip(),
        "amap_js_key": (os.environ.get("AMAP_JS_KEY") or "").strip(),
        "amap_security_code": (os.environ.get("AMAP_SECURITY_CODE") or "").strip(),
        "google_api_key": (os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_MAPS_KEY") or "").strip(),
        "baidu_ak": (os.environ.get("BAIDU_MAP_AK") or os.environ.get("BAIDU_MAP_KEY") or "").strip(),
        "baidu_js_ak": (os.environ.get("BAIDU_MAP_JS_AK") or "").strip(),
    }


def _normalize_provider(p: str) -> str:
    p = (p or "").strip().lower()
    if p in ("amap", "gaode", "高德"):
        return "gaode"
    if p in ("noop", "none", "off", "manual"):
        return "noop"
    if p in ("google", "baidu", "tianditu"):
        return p
    return ""


def load_map_config(db: Optional[Session] = None) -> dict[str, Any]:
    """合并：默认 ← 环境变量 ← 数据库（库优先覆盖）。"""
    cfg = deepcopy(DEFAULT_MAP_CONFIG)
    env = _env_defaults()
    for k, v in env.items():
        if v:
            cfg[k] = v
    if db is not None:
        row = db.query(AppSetting).filter_by(key=MAP_SETTING_KEY).first()
        if row and row.value_json:
            try:
                data = json.loads(row.value_json)
            except json.JSONDecodeError:
                data = {}
            for k, v in (data or {}).items():
                if v is None:
                    continue
                if k in SECRET_KEYS and not str(v).strip():
                    continue
                cfg[k] = v
    cfg["provider"] = _normalize_provider(str(cfg.get("provider") or ""))
    if cfg["provider"] == "gaode" and not cfg.get("amap_js_key") and cfg.get("amap_web_key"):
        cfg["amap_js_key"] = cfg["amap_web_key"]
    cfg["enabled"] = bool(cfg.get("enabled", True))
    return cfg


def apply_runtime_from_db(db: Optional[Session] = None) -> dict[str, Any]:
    global _RUNTIME
    _RUNTIME = load_map_config(db)
    return _RUNTIME


def clear_runtime() -> None:
    global _RUNTIME
    _RUNTIME = {}


def runtime_get(key: str, *env_keys: str) -> str:
    """供地图服务读密钥：运行时缓存 → 环境变量。"""
    v = str((_RUNTIME or {}).get(key) or "").strip()
    if v:
        return v
    for e in env_keys:
        vv = (os.environ.get(e) or "").strip()
        if vv:
            return vv
    return ""


def runtime_provider() -> str:
    """当前图商 id。库/环境未写时跟随 YAML vendors.map。"""
    p = _normalize_provider(str((_RUNTIME or {}).get("provider") or ""))
    if p:
        return p
    env_p = _normalize_provider(os.environ.get("MAP_PROVIDER") or "")
    if env_p:
        return env_p
    try:
        from extensions.map.engine import active_id

        return active_id()
    except Exception:
        return "tianditu"


def _mask_secret(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return ""
    if len(s) <= 8:
        return "****"
    return s[:4] + "****" + s[-4:]


def _has_web_key(cfg: dict) -> bool:
    if not cfg.get("enabled", True):
        return False
    p = _normalize_provider(str(cfg.get("provider") or "")) or runtime_provider()
    if p == "noop":
        return False
    if p == "gaode":
        return bool(str(cfg.get("amap_web_key") or "").strip())
    if p == "google":
        return bool(str(cfg.get("google_api_key") or "").strip())
    if p == "baidu":
        return bool(str(cfg.get("baidu_ak") or "").strip())
    return bool(str(cfg.get("tianditu_tk") or "").strip())


def mask_map_config(cfg: dict) -> dict:
    out = deepcopy(cfg)
    for k in SECRET_KEYS:
        raw = str(out.get(k) or "")
        out[f"{k}_set"] = bool(raw.strip())
        out[k] = _mask_secret(raw) if raw.strip() else ""
    out["mode"] = "live" if _has_web_key(cfg) else "demo"
    return out


def map_providers_ui() -> list[dict[str, Any]]:
    from extensions.map.engine import load_catalog
    from infra.i18n import t

    cat = load_catalog()
    providers = cat.get("providers") or {}
    order = [p for p in CANONICAL_PROVIDERS if p in providers]
    for pid in providers:
        if pid not in order:
            order.append(str(pid))
    out: list[dict[str, Any]] = []
    for pid in order:
        meta = providers.get(pid) if isinstance(providers.get(pid), dict) else {}
        ui = PROVIDER_UI.get(pid) or {}
        label = ui.get("label") or (meta or {}).get("label") or pid
        hint = ui.get("hint") or ""
        fields = []
        for f in ui.get("fields") or []:
            fields.append({**f, "label": t(str(f.get("label") or f.get("key")))})
        out.append(
            {
                "id": pid,
                "label": t(str(label)),
                "hint": t(str(hint)) if hint else "",
                "docs_url": ui.get("docs_url") or "",
                "fields": fields,
            }
        )
    return out


def save_map_config(db: Session, payload: dict) -> dict:
    current = load_map_config(db)
    if "enabled" in payload:
        current["enabled"] = bool(payload.get("enabled"))
    if "provider" in payload:
        current["provider"] = _normalize_provider(str(payload.get("provider") or ""))
    for k in SECRET_KEYS:
        if k not in payload:
            continue
        val = str(payload.get(k) or "").strip()
        if not val or "****" in val:
            continue
        current[k] = val

    row = db.query(AppSetting).filter_by(key=MAP_SETTING_KEY).first()
    if not row:
        row = AppSetting(key=MAP_SETTING_KEY)
        db.add(row)
    to_store = {k: current.get(k) for k in DEFAULT_MAP_CONFIG.keys()}
    row.value_json = json.dumps(to_store, ensure_ascii=False)
    db.commit()
    apply_runtime_from_db(db)
    pid = runtime_provider()
    try:
        from extensions.map.engine import force_active, set_active

        force_active(None)
        if pid:
            set_active(pid)
    except Exception:
        pass
    return load_map_config(db)


def ensure_map_defaults(db: Session) -> None:
    """确保 AppSetting 行存在（可为空密钥，便于系统配置页编辑）。"""
    row = db.query(AppSetting).filter_by(key=MAP_SETTING_KEY).first()
    if row:
        return
    row = AppSetting(key=MAP_SETTING_KEY, value_json=json.dumps(deepcopy(DEFAULT_MAP_CONFIG), ensure_ascii=False))
    db.add(row)
    db.commit()
