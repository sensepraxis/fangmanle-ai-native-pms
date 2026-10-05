# SPDX-License-Identifier: Apache-2.0
"""地图执行引擎：读 YAML 目录动态加载实现类，再按 vendors.map / DB 选型。"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Optional

from extensions.map.port import IMap

log = logging.getLogger(__name__)

_catalog: dict[str, Any] | None = None
_instances: dict[str, IMap] = {}
_alias_to_id: dict[str, str] = {}
_active_id: Optional[str] = None
_forced_id: Optional[str] = None


def _repo_root() -> Path:
    from infra.hotel_config import repo_root

    return repo_root()


def _catalog_path() -> Path:
    override = (__import__("os").environ.get("FML_MAPS_CATALOG") or "").strip()
    if override:
        return Path(override)
    return _repo_root() / "config" / "extensions" / "maps.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError as e:
        raise RuntimeError("读取 maps.yaml 需要 PyYAML：pip install pyyaml") from e
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_catalog(*, force: bool = False) -> dict[str, Any]:
    """加载 config/extensions/maps.yaml（providers + fallback）。"""
    global _catalog, _alias_to_id
    if _catalog is not None and not force:
        return _catalog
    path = _catalog_path()
    doc = _read_yaml(path)
    providers = doc.get("providers") or {}
    if not isinstance(providers, dict):
        providers = {}
    alias: dict[str, str] = {}
    for pid, meta in providers.items():
        key = str(pid).strip().lower()
        alias[key] = key
        if isinstance(meta, dict):
            for a in meta.get("aliases") or []:
                alias[str(a).strip().lower()] = key
    # 常见同义（即使 YAML 未写）
    alias.setdefault("amap", alias.get("gaode", "gaode"))
    alias.setdefault("高德", alias.get("gaode", "gaode"))
    _alias_to_id = alias
    _catalog = {
        "providers": providers,
        "fallback": str(doc.get("fallback") or "noop").strip().lower() or "noop",
        "path": str(path),
    }
    log.info("[IMap.engine] catalog=%s providers=%s", path, sorted(providers.keys()))
    return _catalog


def resolve_id(raw: str | None) -> str:
    load_catalog()
    key = (raw or "").strip().lower() or ""
    if not key:
        return str((_catalog or {}).get("fallback") or "noop")
    return _alias_to_id.get(key, key)


def _import_class(dotted: str) -> type:
    mod_name, _, cls_name = dotted.rpartition(".")
    if not mod_name or not cls_name:
        raise ValueError(f"invalid map class path: {dotted!r}")
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name, None)
    if cls is None:
        raise ImportError(f"{dotted} not found")
    return cls


def get_instance(provider_id: str) -> IMap:
    """按目录 id 取实现（懒加载 + 缓存）。"""
    load_catalog()
    pid = resolve_id(provider_id)
    if pid in _instances:
        return _instances[pid]
    providers = (_catalog or {}).get("providers") or {}
    meta = providers.get(pid)
    if not isinstance(meta, dict) or not meta.get("class"):
        fb = str((_catalog or {}).get("fallback") or "noop")
        if pid != fb:
            log.warning("[IMap.engine] unknown id=%s, fallback=%s", pid, fb)
            return get_instance(fb)
        # 最后兜底：内置 Noop，避免目录缺失导致崩
        from extensions.map.impl.noop import NoopMap

        inst: IMap = NoopMap()
        _instances[pid] = inst
        return inst
    cls = _import_class(str(meta["class"]))
    inst = cls()
    _instances[pid] = inst
    return inst


def list_provider_ids() -> list[str]:
    load_catalog()
    return sorted(((_catalog or {}).get("providers") or {}).keys())


def force_active(provider_id: Optional[str]) -> None:
    """pack 可强制某实现（如 intl→noop）；None 取消强制。"""
    global _forced_id
    _forced_id = resolve_id(provider_id) if provider_id else None


def forced_active() -> Optional[str]:
    return _forced_id


def set_active(provider_id: str) -> str:
    """记录当前选型（YAML vendors.map / DB）；不强制时 get_map 用此 id。"""
    global _active_id
    _active_id = resolve_id(provider_id)
    # 预热实例
    get_instance(_active_id)
    return _active_id


def active_id() -> str:
    if _forced_id:
        return _forced_id
    if _active_id:
        return _active_id
    load_catalog()
    return str((_catalog or {}).get("fallback") or "noop")


def get_map(provider_id: str | None = None) -> IMap:
    """执行引擎入口：返回当前（或指定）IMap 实现。"""
    pid = resolve_id(provider_id) if provider_id else active_id()
    return get_instance(pid)


def activate_from_vendor(vendor_map: str) -> str:
    """由酒店 YAML 的 vendors.map 写入出厂默认；配置页保存后以库为准。"""
    pid = set_active(vendor_map)
    force_active(None)
    log.info("[IMap.engine] active=%s", active_id())
    return pid


def reset_engine() -> None:
    """测试用。"""
    global _catalog, _instances, _alias_to_id, _active_id, _forced_id
    _catalog = None
    _instances.clear()
    _alias_to_id.clear()
    _active_id = None
    _forced_id = None
    try:
        from infra.map_config import clear_runtime

        clear_runtime()
    except Exception:
        pass
