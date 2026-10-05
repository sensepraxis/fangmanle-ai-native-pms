# SPDX-License-Identifier: Apache-2.0
"""LLM Extension 注册表：可发现的 Provider + 出厂默认 active。"""

from __future__ import annotations

import logging
from typing import Any

from extensions.llm.catalog import LLM_PROVIDER_CATALOG, catalog_ids, catalog_meta

log = logging.getLogger(__name__)

_active_default: str | None = None


class _CatalogLlmProvider:
    """目录项包装：满足 LlmProvider Protocol，调用仍走 commercial.ai_core.llm_service。"""

    def __init__(self, provider_id: str):
        self.name = provider_id
        self._meta = catalog_meta(provider_id)

    def meta(self) -> dict[str, Any]:
        return dict(self._meta)

    def kind(self) -> str:
        return str(self._meta.get("kind") or "openai_compatible")


_PROVIDERS: dict[str, _CatalogLlmProvider] = {}


def reset_llm_extension() -> None:
    global _active_default, _PROVIDERS
    _active_default = None
    _PROVIDERS = {}


def _ensure_registered() -> None:
    if _PROVIDERS:
        return
    for row in LLM_PROVIDER_CATALOG:
        pid = str(row["id"])
        _PROVIDERS[pid] = _CatalogLlmProvider(pid)


def list_llm_providers() -> list[dict[str, Any]]:
    _ensure_registered()
    from infra.i18n import t

    out = []
    for p in LLM_PROVIDER_CATALOG:
        row = dict(p)
        if row.get("label"):
            row["label"] = t(str(row["label"]))
        if row.get("hint"):
            row["hint"] = t(str(row["hint"]))
        out.append(row)
    return out


def get_llm_provider(provider_id: str | None = None) -> _CatalogLlmProvider:
    _ensure_registered()
    from extensions.llm.facade import fallback_provider_id

    pid = (provider_id or _active_default or fallback_provider_id()).strip().lower()
    if pid not in _PROVIDERS:
        pid = fallback_provider_id()
        if pid not in _PROVIDERS:
            pid = next(iter(_PROVIDERS))
    return _PROVIDERS[pid]


def active_llm_default() -> str:
    """酒店 YAML / activate 写入的出厂默认；未设置时不假装一定是 ollama。"""
    if _active_default:
        return _active_default
    return ""


def activate_llm_extension(provider_id: str | None) -> str:
    """设置出厂默认 LLM（库里已有配置时仍以 DB 为准）。"""
    global _active_default
    _ensure_registered()
    from extensions.llm.facade import fallback_provider_id

    if not provider_id:
        _active_default = None
        return fallback_provider_id()
    pid = provider_id.strip().lower()
    # 兼容别名
    aliases = {"minimax": "openai_compatible", "tongyi": "qwen", "dashscope": "bailian"}
    pid = aliases.get(pid, pid)
    if pid not in catalog_ids():
        log.warning("[Extensions.llm] unknown provider=%s, keep catalog only", pid)
        _active_default = None
        return fallback_provider_id()
    _active_default = pid
    log.info("[Extensions.llm] default_provider=%s", pid)
    return pid
