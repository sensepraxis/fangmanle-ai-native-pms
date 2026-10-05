# SPDX-License-Identifier: Apache-2.0
"""auto-generated-style facade for LLM config / chat（Commercial Core）。"""

from __future__ import annotations

from infra.commercial_pack import bind as _cbind

_localized_llm_providers = _cbind("commercial.ai_core.llm_service", "localized_llm_providers")
_load_llm_config = _cbind("commercial.ai_core.llm_service", "load_llm_config")
_mask_llm_config = _cbind("commercial.ai_core.llm_service", "mask_llm_config")
_save_llm_config = _cbind("commercial.ai_core.llm_service", "save_llm_config")
_test_llm_connection = _cbind("commercial.ai_core.llm_service", "test_llm_connection")
_chat = _cbind("commercial.ai_core.llm_service", "chat")


def localized_llm_providers(*args, **kwargs):
    return _localized_llm_providers(*args, **kwargs)


def load_llm_config(*args, **kwargs):
    return _load_llm_config(*args, **kwargs)


def mask_llm_config(*args, **kwargs):
    return _mask_llm_config(*args, **kwargs)


def save_llm_config(*args, **kwargs):
    return _save_llm_config(*args, **kwargs)


def test_llm_connection(*args, **kwargs):
    return _test_llm_connection(*args, **kwargs)


def chat(*args, **kwargs):
    return _chat(*args, **kwargs)
