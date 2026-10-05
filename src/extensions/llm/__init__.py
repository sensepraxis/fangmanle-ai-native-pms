# SPDX-License-Identifier: Apache-2.0
"""LLM Extension：Port = LlmProvider；业务入口 = facade（可插拔，不绑死某一模型）。"""

from __future__ import annotations

from extensions.llm.facade import (
    chat,
    chat_stream,
    llm_identity,
    load_llm_config,
    resolve_model_name,
    resolve_provider_id,
)
from extensions.llm.port import LlmProvider
from extensions.llm.registry import (
    activate_llm_extension,
    active_llm_default,
    get_llm_provider,
    list_llm_providers,
)

__all__ = [
    "LlmProvider",
    "list_llm_providers",
    "get_llm_provider",
    "active_llm_default",
    "activate_llm_extension",
    "chat",
    "chat_stream",
    "load_llm_config",
    "llm_identity",
    "resolve_model_name",
    "resolve_provider_id",
]
