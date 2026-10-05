# SPDX-License-Identifier: Apache-2.0
"""私域通道配置（AppSetting + 环境变量）。

读取优先级（primary vendor）：
1. 环境变量 ``PRIVATE_CHANNEL_VENDOR``（进程级强制，便于 CI / 演示）
2. AppSetting key=``private_channel`` 的 ``vendor`` 字段
3. 默认 ``wecom``

支持 primary：wecom / line / whatsapp / webhook
支持 fallback：sms / email（以及其它已注册通道，作触达兜底）

环境变量 ``PRIVATE_CHANNEL_FALLBACK`` 可用逗号分隔覆盖 fallback 列表。
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Optional

from sqlalchemy.orm import Session

PRIVATE_CHANNEL_SETTING_KEY = "private_channel"

# 可作为酒店「主私域 IM」的 vendor
PRIMARY_VENDORS = frozenset({"wecom", "line", "whatsapp", "webhook"})
# 可作为兜底触达的通道
FALLBACK_VENDORS = frozenset({"sms", "email", "webhook"})
_SUPPORTED = PRIMARY_VENDORS  # resolve_vendor 仍只解析 primary

DEFAULT_PRIVATE_CHANNEL_CONFIG: dict[str, Any] = {
    "vendor": "wecom",
    # 触达兜底：主 IM 不可达 / demo 时可降级
    "fallback": [],
    # 能力包：private_ops_core 全球内核；wecom_deep 仅中国企微增强
    "packs": ["private_ops_core"],
    "per_hotel": {},
    "line": {
        "enabled": False,
        "channel_id": "",
        "channel_secret": "",
        "channel_access_token": "",
    },
    "whatsapp": {
        "enabled": False,
        "phone_number_id": "",
        "access_token": "",
    },
    "sms": {"enabled": True, "provider": "demo"},
    "email": {"enabled": True, "provider": "demo"},
    "webhook": {
        "enabled": True,
        "endpoint_hint": "",
    },
}

# 进程缓存（api 启动 / 保存配置后刷新）
_cached_vendor: Optional[str] = None
_cached_fallback: Optional[list[str]] = None


def clear_vendor_cache() -> None:
    global _cached_vendor, _cached_fallback
    _cached_vendor = None
    _cached_fallback = None


def default_private_channel_config() -> dict:
    return deepcopy(DEFAULT_PRIVATE_CHANNEL_CONFIG)


def default_fallback_for(vendor: str) -> list[str]:
    v = (vendor or "").strip().lower()
    if v == "wecom":
        return ["sms"]
    if v in ("line", "whatsapp"):
        return ["sms", "email"]
    if v == "webhook":
        return ["email", "sms"]
    return ["sms", "email"]


def default_packs_for(vendor: str) -> list[str]:
    packs = ["private_ops_core"]
    if (vendor or "").strip().lower() == "wecom":
        packs.append("wecom_deep")
    return packs


def load_private_channel_config(db: Session) -> dict:
    from infra.config_registry import load_app_setting_json

    cfg = load_app_setting_json(
        db,
        PRIVATE_CHANNEL_SETTING_KEY,
        default_factory=default_private_channel_config,
        protect_keys=("vendor",),
    )
    # 兼容旧库：补齐新字段
    if not isinstance(cfg.get("fallback"), list):
        cfg["fallback"] = default_fallback_for(str(cfg.get("vendor") or "wecom"))
    if not isinstance(cfg.get("packs"), list) or not cfg["packs"]:
        cfg["packs"] = default_packs_for(str(cfg.get("vendor") or "wecom"))
    for key, blank in (
        ("whatsapp", DEFAULT_PRIVATE_CHANNEL_CONFIG["whatsapp"]),
        ("sms", DEFAULT_PRIVATE_CHANNEL_CONFIG["sms"]),
        ("email", DEFAULT_PRIVATE_CHANNEL_CONFIG["email"]),
    ):
        if not isinstance(cfg.get(key), dict):
            cfg[key] = deepcopy(blank)
    return cfg


def _mask_secret(val: str, keep: int = 4) -> str:
    s = str(val or "")
    if len(s) <= keep:
        return "****" if s else ""
    return s[:keep] + "****"


def mask_private_channel_config(cfg: dict) -> dict:
    """对外展示：敏感字段掩码。"""
    out = deepcopy(cfg or {})
    line = out.get("line") if isinstance(out.get("line"), dict) else {}
    line_out = dict(line)
    token = str(line.get("channel_access_token") or "")
    secret = str(line.get("channel_secret") or "")
    line_out["channel_access_token"] = _mask_secret(token) if token else ""
    line_out["channel_secret"] = _mask_secret(secret) if secret else ""
    line_out["channel_access_token_set"] = bool(token)
    line_out["channel_secret_set"] = bool(secret)
    out["line"] = line_out

    wa = out.get("whatsapp") if isinstance(out.get("whatsapp"), dict) else {}
    wa_out = dict(wa)
    wa_token = str(wa.get("access_token") or "")
    wa_out["access_token"] = _mask_secret(wa_token) if wa_token else ""
    wa_out["access_token_set"] = bool(wa_token)
    out["whatsapp"] = wa_out
    return out


def _normalize_fallback(raw: Any, vendor: str) -> list[str]:
    if raw is None:
        return default_fallback_for(vendor)
    if isinstance(raw, str):
        items = [x.strip().lower() for x in raw.split(",") if x.strip()]
    elif isinstance(raw, (list, tuple)):
        items = [str(x).strip().lower() for x in raw if str(x).strip()]
    else:
        items = default_fallback_for(vendor)
    out: list[str] = []
    for x in items:
        if x == vendor:
            continue
        if x in FALLBACK_VENDORS or x in PRIMARY_VENDORS:
            if x not in out:
                out.append(x)
    return out


def _normalize_packs(raw: Any, vendor: str) -> list[str]:
    if not isinstance(raw, (list, tuple)) or not raw:
        return default_packs_for(vendor)
    out: list[str] = []
    for x in raw:
        s = str(x).strip().lower()
        if s and s not in out:
            out.append(s)
    if "private_ops_core" not in out:
        out.insert(0, "private_ops_core")
    if vendor == "wecom" and "wecom_deep" not in out:
        out.append("wecom_deep")
    if vendor != "wecom":
        out = [p for p in out if p != "wecom_deep"]
    return out


def save_private_channel_config(db: Session, payload: dict) -> dict:
    from infra.config_registry import save_app_setting_json

    existing = load_private_channel_config(db)
    cfg = default_private_channel_config()
    for k, v in existing.items():
        if k in cfg or k in ("line", "webhook", "whatsapp", "sms", "email", "per_hotel", "fallback", "packs"):
            cfg[k] = deepcopy(v) if isinstance(v, (dict, list)) else v

    vendor = str((payload or {}).get("vendor") or cfg.get("vendor") or "wecom").strip().lower()
    if vendor not in _SUPPORTED:
        raise ValueError(f"不支持的 private_channel.vendor: {vendor}；可选 {sorted(_SUPPORTED)}")
    cfg["vendor"] = vendor

    if "fallback" in (payload or {}):
        cfg["fallback"] = _normalize_fallback(payload.get("fallback"), vendor)
    else:
        cfg["fallback"] = _normalize_fallback(cfg.get("fallback"), vendor)

    if "packs" in (payload or {}):
        cfg["packs"] = _normalize_packs(payload.get("packs"), vendor)
    else:
        cfg["packs"] = _normalize_packs(cfg.get("packs"), vendor)

    if isinstance(payload.get("per_hotel"), dict):
        cfg["per_hotel"] = payload["per_hotel"]

    for block in ("line", "whatsapp", "sms", "email", "webhook"):
        if not isinstance(payload.get(block), dict):
            continue
        prev = cfg.get(block) if isinstance(cfg.get(block), dict) else {}
        nxt = dict(prev)
        for k, v in payload[block].items():
            if k.endswith("_set"):
                continue
            if isinstance(v, str) and "****" in v:
                continue
            if v is None or v == "":
                continue
            nxt[k] = v
        if "enabled" in payload[block]:
            nxt["enabled"] = bool(payload[block]["enabled"])
        cfg[block] = nxt

    save_app_setting_json(db, PRIVATE_CHANNEL_SETTING_KEY, cfg)
    configure_vendor(vendor, fallback=cfg.get("fallback"))
    return cfg


def ensure_private_channel_defaults(db: Session) -> dict:
    """幂等写入默认 private_channel 配置。"""
    from models import AppSetting

    row = db.query(AppSetting).filter_by(key=PRIVATE_CHANNEL_SETTING_KEY).first()
    if row and row.value_json:
        cfg = load_private_channel_config(db)
        configure_vendor(cfg.get("vendor"), fallback=cfg.get("fallback"))
        return cfg
    cfg = default_private_channel_config()
    from infra.config_registry import save_app_setting_json

    save_app_setting_json(db, PRIVATE_CHANNEL_SETTING_KEY, cfg)
    configure_vendor(cfg["vendor"], fallback=cfg.get("fallback"))
    return cfg


def configure_vendor(vendor: Optional[str], fallback: Any = None) -> str:
    """刷新进程缓存；返回规范化后的 vendor。"""
    global _cached_vendor, _cached_fallback
    name = (vendor or DEFAULT_PRIVATE_CHANNEL_CONFIG["vendor"]).strip().lower()
    if name not in _SUPPORTED:
        name = DEFAULT_PRIVATE_CHANNEL_CONFIG["vendor"]
    _cached_vendor = name
    if fallback is not None:
        _cached_fallback = _normalize_fallback(fallback, name)
    try:
        from messaging.factory import reset_channel_cache

        reset_channel_cache()
    except Exception:
        pass
    return name


def configure_from_db(db: Session) -> str:
    """启动时从库加载 vendor 到缓存。"""
    cfg = load_private_channel_config(db)
    return configure_vendor(cfg.get("vendor"), fallback=cfg.get("fallback"))


def apply_hotel_messaging_spec(spec: dict[str, Any]) -> str:
    """酒店 YAML messaging 规格写入进程（不落库，启动时生效）。"""
    primary = str(spec.get("primary") or spec.get("vendor") or "webhook").strip().lower()
    if primary not in _SUPPORTED:
        primary = "webhook"
    fb = spec.get("fallback")
    if fb is None:
        fb = default_fallback_for(primary)
    packs = spec.get("packs") or default_packs_for(primary)
    # 仅在未强制 env 时设置 primary
    if not (os.environ.get("PRIVATE_CHANNEL_VENDOR") or "").strip():
        os.environ["PRIVATE_CHANNEL_VENDOR"] = primary
    if not (os.environ.get("PRIVATE_CHANNEL_FALLBACK") or "").strip():
        os.environ["PRIVATE_CHANNEL_FALLBACK"] = ",".join(_normalize_fallback(fb, primary))
    # packs 用 env 传递给 facade（轻量）
    os.environ["PRIVATE_CHANNEL_PACKS"] = ",".join(_normalize_packs(packs, primary))
    return configure_vendor(primary, fallback=fb)


def resolve_vendor(explicit: Optional[str] = None) -> str:
    """解析当前应使用的 primary vendor（供 messaging.factory 调用）。"""
    if explicit:
        return str(explicit).strip().lower()
    env = (os.environ.get("PRIVATE_CHANNEL_VENDOR") or "").strip().lower()
    if env:
        if env not in _SUPPORTED:
            raise ValueError(f"PRIVATE_CHANNEL_VENDOR={env} 不受支持；可选 {sorted(_SUPPORTED)}")
        return env
    if _cached_vendor:
        return _cached_vendor
    return DEFAULT_PRIVATE_CHANNEL_CONFIG["vendor"]


def resolve_fallback(explicit: Optional[list[str]] = None) -> list[str]:
    """解析触达兜底通道列表。"""
    vendor = resolve_vendor()
    if explicit is not None:
        return _normalize_fallback(explicit, vendor)
    env = (os.environ.get("PRIVATE_CHANNEL_FALLBACK") or "").strip()
    if env:
        return _normalize_fallback(env, vendor)
    if _cached_fallback is not None:
        return list(_cached_fallback)
    return default_fallback_for(vendor)


def resolve_packs() -> list[str]:
    env = (os.environ.get("PRIVATE_CHANNEL_PACKS") or "").strip()
    vendor = resolve_vendor()
    if env:
        return _normalize_packs([x.strip() for x in env.split(",") if x.strip()], vendor)
    return default_packs_for(vendor)


__all__ = [
    "PRIVATE_CHANNEL_SETTING_KEY",
    "PRIMARY_VENDORS",
    "FALLBACK_VENDORS",
    "DEFAULT_PRIVATE_CHANNEL_CONFIG",
    "clear_vendor_cache",
    "default_private_channel_config",
    "default_fallback_for",
    "default_packs_for",
    "load_private_channel_config",
    "mask_private_channel_config",
    "save_private_channel_config",
    "ensure_private_channel_defaults",
    "configure_vendor",
    "configure_from_db",
    "apply_hotel_messaging_spec",
    "resolve_vendor",
    "resolve_fallback",
    "resolve_packs",
]
