# SPDX-License-Identifier: Apache-2.0
"""酒店组装配置：config/hotels/<hotel>.yaml（不是国情包）。

启动示例：
  deploy/dev/start.bat abc-hotel
  deploy/dev/start.bat abc-hotel.yaml
  set FML_HOTEL_FILE=E:\\path\\to\\abc-hotel.yaml
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_catalog: dict[str, dict[str, Any]] | None = None
_hotel_doc: dict[str, Any] | None = None
_hotel_id: str | None = None


def repo_root() -> Path:
    env = (os.environ.get("FML_REPO_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def hotels_dir() -> Path:
    return repo_root() / "config" / "hotels"


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    suf = path.suffix.lower()
    if suf in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError("读取 YAML 需要 PyYAML：pip install pyyaml") from e
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    return data if isinstance(data, dict) else {}


def _first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p.is_file():
            return p
    return None


def _hotel_id_of(path: Path, doc: dict[str, Any]) -> str:
    raw = doc.get("id") or doc.get("hotel") or doc.get("pack") or path.stem
    return str(raw).strip().lower()


def _annotate(path: Path, doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    hid = _hotel_id_of(path, doc)
    out["_id"] = hid
    out["_path"] = str(path.resolve())
    return out


def _scan_hotels(*, force: bool = False) -> dict[str, dict[str, Any]]:
    global _catalog
    if _catalog is not None and not force:
        return _catalog
    out: dict[str, dict[str, Any]] = {}
    d = hotels_dir()
    if d.is_dir():
        for path in sorted(set(d.glob("*.yaml")) | set(d.glob("*.yml"))):
            doc = _annotate(path, _read_mapping(path) or {})
            out[str(doc["_id"])] = doc
    _catalog = out
    return _catalog


def reset_hotel_config_cache() -> None:
    global _catalog, _hotel_doc, _hotel_id
    _catalog = None
    _hotel_doc = None
    _hotel_id = None


# 兼容旧名
reset_pack_config_cache = reset_hotel_config_cache


def _resolve_stem(stem: str) -> Path | None:
    """按文件名或 aliases 解析酒店 YAML。"""
    stem = (stem or "").strip()
    if not stem:
        return None
    p = Path(stem)
    if p.is_file():
        return p
    cand = _first_existing(
        hotels_dir() / f"{stem}.yaml",
        hotels_dir() / f"{stem}.yml",
        hotels_dir() / stem,
    )
    if cand:
        return cand
    # aliases：sg → demo-sg.yaml
    key = stem.lower().removesuffix(".yaml").removesuffix(".yml")
    for hid, prof in _scan_hotels().items():
        aliases = [str(a).strip().lower() for a in (prof.get("aliases") or [])]
        if key == hid or key in aliases:
            path = Path(str(prof.get("_path") or ""))
            if path.is_file():
                return path
    return None


def resolve_hotel_file() -> Path | None:
    """解析当前酒店 YAML 路径：FML_HOTEL_FILE / FML_DEPLOY_FILE / 默认 demo-cn。"""
    for key in ("FML_HOTEL_FILE", "FML_DEPLOY_FILE"):
        override = (os.environ.get(key) or "").strip()
        if override:
            found = _resolve_stem(override)
            if found:
                return found
    # FML_HOTEL / FML_PACKS 仅 id 时也解析
    for key in ("FML_HOTEL", "FML_PACKS"):
        stem = (os.environ.get(key) or "").strip()
        if stem:
            found = _resolve_stem(stem)
            if found:
                return found
    return _first_existing(
        hotels_dir() / "demo-cn.yaml",
        hotels_dir() / "abc-hotel.yaml",
        hotels_dir() / "cn.yaml",
    )


def load_hotel_doc(*, force: bool = False) -> dict[str, Any]:
    """当前选中的酒店 YAML。"""
    global _hotel_doc, _hotel_id
    if _hotel_doc is not None and not force:
        return _hotel_doc
    path = resolve_hotel_file()
    if path is None:
        _hotel_doc = {}
        _hotel_id = None
        # stderr: keep stdout clean for print_deploy_env → eval / set
        print("Hotel config: no YAML found under config/hotels/", file=sys.stderr, flush=True)
        return _hotel_doc
    abs_path = path.resolve()
    doc = _annotate(path, _read_mapping(path) or {})
    _hotel_doc = doc
    _hotel_id = str(doc.get("_id") or "")
    print(f"Hotel config loaded from: {abs_path}", file=sys.stderr, flush=True)
    return _hotel_doc


# 兼容
load_deploy_doc = load_hotel_doc


def profiles() -> dict[str, dict[str, Any]]:
    return dict(_scan_hotels())


def vendor_map(prof: dict[str, Any]) -> str:
    vendors = prof.get("vendors") if isinstance(prof.get("vendors"), dict) else {}
    raw = vendors.get("map") or prof.get("map") or "noop"
    return str(raw).strip().lower() or "noop"


def messaging_spec(prof: dict[str, Any]) -> dict[str, Any]:
    """解析 vendors.messaging：支持字符串或 {primary, fallback, packs}。"""
    vendors = prof.get("vendors") if isinstance(prof.get("vendors"), dict) else {}
    raw = vendors.get("messaging") if "messaging" in vendors else prof.get("private_channel")
    if raw is None:
        raw = "webhook"
    if isinstance(raw, dict):
        primary = str(raw.get("primary") or raw.get("vendor") or "webhook").strip().lower() or "webhook"
        fb = raw.get("fallback") or raw.get("fallbacks")
        packs = raw.get("packs")
        return {"primary": primary, "fallback": fb, "packs": packs}
    primary = str(raw).strip().lower() or "webhook"
    return {"primary": primary, "fallback": None, "packs": None}


def vendor_messaging(prof: dict[str, Any]) -> str:
    """主私域通道 vendor（字符串，兼容旧调用）。"""
    return messaging_spec(prof)["primary"]


def vendor_llm(prof: dict[str, Any]) -> str:
    vendors = prof.get("vendors") if isinstance(prof.get("vendors"), dict) else {}
    raw = vendors.get("llm") or ""
    return str(raw).strip().lower()


def vendor_tax(prof: dict[str, Any]) -> dict[str, Any]:
    """返回 tax 选型：{provider, name?, rate?}。"""
    vendors = prof.get("vendors") if isinstance(prof.get("vendors"), dict) else {}
    tax = prof.get("tax") if isinstance(prof.get("tax"), dict) else {}
    feat = prof.get("features") if isinstance(prof.get("features"), dict) else {}
    if feat.get("invoice") is False:
        return {"provider": "noop"}

    raw = vendors.get("tax")
    if isinstance(raw, dict):
        out = dict(raw)
        out["provider"] = str(out.get("provider") or out.get("kind") or "noop").strip().lower()
        out.setdefault("name", tax.get("name"))
        out.setdefault("rate", tax.get("rate"))
        return out
    if isinstance(raw, str) and raw.strip():
        prov = raw.strip().lower()
        out: dict[str, Any] = {"provider": prov}
        if tax.get("name") is not None:
            out["name"] = tax.get("name")
        if tax.get("rate") is not None:
            out["rate"] = tax.get("rate")
        return out

    if isinstance(prof.get("tax"), str) and str(prof.get("tax")).strip().lower() in ("noop", "off", "none"):
        return {"provider": "noop"}
    if tax:
        prov = str(tax.get("provider") or tax.get("kind") or "").strip().lower()
        if not prov and (tax.get("rate") is not None or tax.get("name")):
            prov = "simple_vat"
        return {
            "provider": prov or "noop",
            "name": tax.get("name"),
            "rate": tax.get("rate"),
        }
    return {"provider": "noop"}


def channels_preset(prof: dict[str, Any]) -> str:
    raw = prof.get("channels_preset") or prof.get("channel_preset") or prof.get("_id") or "intl"
    return str(raw).strip().lower() or "intl"


_SYSTEM_TAB_MENUS: dict[str, str] = {
    # 私域通道 Tab（历史 key=menu.system.wecom，与是否企微无关）
    "private_channel": "menu.system.wecom",
    "wecom": "menu.system.wecom",
    "wechat": "menu.system.wecom",
    "llm": "menu.system.llm",
    "map": "menu.system.map",
    "finance": "menu.system.finance_params",
    "financial": "menu.system.finance_params",
    "room_types": "menu.system.room_types",
    "room-type": "menu.system.room_types",
    "rooms": "menu.system.room_master",
    "roominfo": "menu.system.room_master",
    "users": "menu.system.users",
    "user-acct": "menu.system.users",
    "rbac": "menu.system.rbac",
    "role-permission": "menu.system.rbac",
}


def _system_flags(prof: dict[str, Any]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    blob = prof.get("system")
    if isinstance(blob, dict):
        for k, v in blob.items():
            flags[str(k).strip().lower()] = bool(v)
    feat = prof.get("features") if isinstance(prof.get("features"), dict) else {}
    nested = feat.get("system")
    if isinstance(nested, dict):
        for k, v in nested.items():
            flags[str(k).strip().lower()] = bool(v)
    if "wecom" in feat:
        flags["wecom"] = bool(feat.get("wecom"))
    if "wechat" in feat:
        flags["wecom"] = bool(feat.get("wechat"))
    return flags


def hide_menus_from_profile(prof: dict[str, Any]) -> tuple[str, ...]:
    hide: list[str] = [str(x) for x in (prof.get("hide_menus") or [])]
    flags = _system_flags(prof)
    # private_channel 优先于历史 wecom 开关，避免国外酒店关掉 wecom 后丢私域 Tab
    if "private_channel" in flags:
        flags["wecom"] = flags["private_channel"]
        flags["wechat"] = flags["private_channel"]
    for key, on in flags.items():
        menu = _SYSTEM_TAB_MENUS.get(key)
        if menu and on is False and menu not in hide:
            hide.append(menu)
    feat = prof.get("features") if isinstance(prof.get("features"), dict) else {}
    if feat.get("invoice") is False and "menu.finance.invoice" not in hide:
        hide.append("menu.finance.invoice")
    tax = vendor_tax(prof)
    if tax.get("provider") in ("noop", "off", "none") and "menu.finance.invoice" not in hide:
        hide.append("menu.finance.invoice")
    return tuple(dict.fromkeys(hide))


def alias_map() -> dict[str, str]:
    cat: dict[str, str] = {}
    for hid, prof in profiles().items():
        key = str(hid).strip().lower()
        cat[key] = key
        for a in prof.get("aliases") or []:
            ak = str(a).strip().lower()
            if ak:
                cat[ak] = key
    return cat


def list_profile_ids() -> list[str]:
    return sorted(profiles().keys())


def get_profile(pid: str) -> dict[str, Any]:
    key = str(pid or "").strip().lower()
    aliases = alias_map()
    resolved = aliases.get(key, key)
    found = profiles().get(resolved)
    if found:
        return dict(found)
    hotel = load_hotel_doc()
    if str(hotel.get("_id") or "") == key or str(hotel.get("_id") or "") == resolved:
        return dict(hotel)
    return {}


def load_packs_doc(*, force: bool = False) -> dict[str, Any]:
    return {"default": "demo-cn", "profiles": profiles()}


@dataclass(frozen=True)
class DeployChoice:
    pack: str  # 兼容字段名 = hotel id
    locale: str


def resolve_deploy(*, pack: str | None = None, locale: str | None = None) -> DeployChoice:
    """环境变量 > 参数 > FML_HOTEL_FILE > 默认 demo-cn。"""
    cat = alias_map()
    hotel = load_hotel_doc()
    raw = (
        pack
        or os.environ.get("FML_HOTEL")
        or os.environ.get("FML_PACKS")
        or hotel.get("_id")
        or hotel.get("hotel")
        or hotel.get("id")
        or "demo-cn"
    )
    raw = str(raw).strip().lower()
    if raw in ("", "default", "cn"):
        # cn 作为别名：若有 demo-cn 用 demo-cn，否则 cn
        raw = "demo-cn" if "demo-cn" in cat or "demo-cn" in profiles() else ("cn" if "cn" in cat else raw)
    pid = cat.get(raw)
    if not pid:
        if raw == str(hotel.get("_id") or ""):
            pid = raw
        else:
            known = ", ".join(list_profile_ids())
            raise ValueError(f"未知酒店配置={raw!r}。在 config/hotels/<name>.yaml 加一份。已有: {known}")
    loc = (
        locale
        or os.environ.get("SEED_LOCALE")
        or (hotel.get("locale") if str(hotel.get("_id") or "") == pid else None)
        or get_profile(pid).get("locale")
        or "en"
    )
    loc = str(loc).strip() or "en"
    return DeployChoice(pack=pid, locale=loc)
