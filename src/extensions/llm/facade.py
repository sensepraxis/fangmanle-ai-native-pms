# SPDX-License-Identifier: Apache-2.0
"""LLM 防腐门面：业务只依赖本模块，不假定 Ollama / qwen3:8b。

选型目录见 ``extensions.llm.catalog``；实际 HTTP 调用仍由 ``commercial.ai_core.llm_service`` 执行
（按 AppSetting.llm.provider 的 kind：ollama | openai_compatible）。
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session


def fallback_provider_id() -> str:
    """无配置时的厂商回退：酒店 YAML 激活值 → 目录内本地 ollama（零密钥）→ OpenAI 兼容。

    注意：回退的是「厂商」，模型名始终来自该厂商 catalog.default_model，
    业务层禁止再写死 qwen3:8b。
    """
    from extensions.llm.catalog import catalog_ids

    ids = catalog_ids()
    try:
        from extensions.llm.registry import active_llm_default

        pid = (active_llm_default() or "").strip().lower()
        if pid and pid in ids:
            return pid
    except Exception:
        pass
    if "ollama" in ids:
        return "ollama"
    return "openai_compatible" if "openai_compatible" in ids else (ids[0] if ids else "openai_compatible")


def resolve_provider_id(cfg: dict | None = None, *, res: dict | None = None) -> str:
    from extensions.llm.catalog import catalog_ids

    raw = str((res or {}).get("provider") or (cfg or {}).get("provider") or "").strip().lower()
    if raw and raw in catalog_ids():
        return raw
    return fallback_provider_id()


def resolve_model_name(cfg: dict | None = None, *, res: dict | None = None) -> str:
    """当前应展示/落库的模型名：响应 > 配置 > 该厂商目录默认。永不写死 qwen3:8b。"""
    for src in ((res or {}).get("model"), (cfg or {}).get("model")):
        m = str(src or "").strip()
        if m:
            return m
    from extensions.llm.catalog import catalog_meta

    pid = resolve_provider_id(cfg, res=res)
    return str(catalog_meta(pid).get("default_model") or "").strip() or "default"


def provider_label(provider_id: str | None = None, *, cfg: dict | None = None) -> str:
    from extensions.llm.catalog import catalog_meta
    from infra.i18n import t

    pid = provider_id or resolve_provider_id(cfg)
    return t(str(catalog_meta(pid).get("label") or pid))


def llm_identity(cfg: dict | None = None, res: dict | None = None) -> dict:
    provider = resolve_provider_id(cfg, res=res)
    model = resolve_model_name(cfg, res=res)
    return {
        "provider": provider,
        "provider_label": provider_label(provider),
        "model": model,
    }


def _llm_mod():
    from infra.commercial_pack import load_module, unavailable_error

    mod = load_module("commercial.ai_core.llm_service")
    if mod is None:
        raise unavailable_error()
    return mod


def load_llm_config(db: Session) -> dict:
    return _llm_mod().load_llm_config(db)


def chat(
    db: Session,
    messages: list[dict],
    system_hint: str | None = None,
    **kwargs: Any,
) -> dict:
    return _llm_mod().chat(db, messages, system_hint, **kwargs)


def chat_stream(
    db: Session,
    messages: list[dict],
    system_hint: str | None = None,
    **kwargs: Any,
) -> Iterator[str]:
    return _llm_mod().chat_stream(db, messages, system_hint, **kwargs)


def chat_stream_parts(
    db: Session,
    messages: list[dict],
    system_hint: str | None = None,
    **kwargs: Any,
) -> Iterator[tuple[str, str]]:
    return _llm_mod().chat_stream_parts(db, messages, system_hint, **kwargs)


def format_llm_fallback_note(cfg: dict | None, err: Any, *, max_err: int = 100) -> str:
    try:
        return _llm_mod().format_llm_fallback_note(cfg, err, max_err=max_err)
    except Exception:
        from infra.i18n import t

        ident = llm_identity(cfg)
        who = ident.get("provider_label") or ident.get("provider") or t("当前大模型")
        model = ident.get("model")
        label = f"{who} · {model}" if model else str(who)
        msg = str(err)[:max_err]
        return t("{who}暂不可用：{text}", who=label, text=msg)


def list_providers() -> list[dict[str, Any]]:
    from extensions.llm.registry import list_llm_providers

    return list_llm_providers()


__all__ = [
    "chat",
    "chat_stream",
    "chat_stream_parts",
    "fallback_provider_id",
    "format_llm_fallback_note",
    "list_providers",
    "llm_identity",
    "load_llm_config",
    "provider_label",
    "resolve_model_name",
    "resolve_provider_id",
]
