# SPDX-License-Identifier: Apache-2.0
"""税票引擎：读 config/extensions/tax.yaml，按酒店 YAML 选型。"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Optional

from extensions.tax.port import ITax

log = logging.getLogger(__name__)

_catalog: dict[str, Any] | None = None
_alias: dict[str, str] = {}
_active: Optional[ITax] = None


def _repo_root() -> Path:
    from infra.hotel_config import repo_root

    return repo_root()


def load_catalog(*, force: bool = False) -> dict[str, Any]:
    global _catalog, _alias
    if _catalog is not None and not force:
        return _catalog
    path = _repo_root() / "config" / "extensions" / "tax.yaml"
    try:
        import yaml

        doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except Exception:
        doc = {}
    providers = (doc or {}).get("providers") or {}
    alias: dict[str, str] = {}
    for pid, meta in providers.items():
        key = str(pid).strip().lower()
        alias[key] = key
        if isinstance(meta, dict):
            for a in meta.get("aliases") or []:
                alias[str(a).strip().lower()] = key
    _alias = alias
    _catalog = {
        "providers": providers,
        "fallback": str((doc or {}).get("fallback") or "noop").strip().lower() or "noop",
        "path": str(path),
    }
    return _catalog


def resolve_id(raw: str | None) -> str:
    load_catalog()
    key = (raw or "").strip().lower()
    if not key:
        return str((_catalog or {}).get("fallback") or "noop")
    return _alias.get(key, key)


def _import_class(dotted: str) -> type:
    mod_name, _, cls_name = dotted.rpartition(".")
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)


def build_tax(cfg: dict[str, Any]) -> ITax:
    """按酒店 tax 配置构造实例。simple_vat 可带 name/rate。"""
    load_catalog()
    pid = resolve_id(str(cfg.get("provider") or "noop"))
    providers = (_catalog or {}).get("providers") or {}
    meta = providers.get(pid)
    if not isinstance(meta, dict) or not meta.get("class"):
        from extensions.tax.impl.noop import NoopTax

        return NoopTax()
    cls = _import_class(str(meta["class"]))
    if pid == "simple_vat":
        name = str(cfg.get("name") or "vat")
        rate = float(cfg.get("rate") or 0)
        ota = cfg.get("ota_codes")
        ota_set = frozenset(str(x) for x in ota) if ota else None
        return cls(name=name, tax_rate=rate, ota_codes=ota_set)
    return cls()


def activate_tax(cfg: dict[str, Any]) -> str:
    global _active
    from finance.tax.registry import register_tax_provider

    inst = build_tax(cfg)
    register_tax_provider(inst)
    _active = inst
    log.info("[ITax.engine] active=%s", getattr(inst, "name", "?"))
    return str(getattr(inst, "name", "noop"))


def reset_tax_engine() -> None:
    global _catalog, _alias, _active
    from finance.tax.registry import reset_tax_provider

    _catalog = None
    _alias.clear()
    _active = None
    reset_tax_provider()
