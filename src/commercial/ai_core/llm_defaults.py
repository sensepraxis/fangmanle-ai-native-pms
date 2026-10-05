# SPDX-License-Identifier: BUSL-1.1
"""系统 LLM 配置默认值。

从原 `bootstrap.ensure_llm_defaults` 抽离；ensure_llm_schema / ensure_llm_defaults 仍在
`bootstrap.ensure_llm` 里。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from commercial.ai_core.prompt_packs import get_default_system_prompt
from infra.i18n import normalize_locale

LLM_SETTING_KEY = "llm"


def _seed_or_default_locale(locale: Optional[str] = None) -> str:
    raw = locale or os.environ.get("SEED_LOCALE") or os.environ.get("FML_DEFAULT_LOCALE") or "zh-CN"
    return normalize_locale(raw)


def build_default_llm_config(locale: Optional[str] = None) -> dict[str, Any]:
    """按 SEED_LOCALE / FML_DEFAULT_LOCALE / 显式 locale 生成默认 LLM 配置。

    厂商/模型来自酒店 YAML 激活的 catalog，不写死 Ollama·qwen3:8b。
    """
    loc = _seed_or_default_locale(locale)
    from extensions.llm.catalog import catalog_meta
    from extensions.llm.facade import fallback_provider_id

    provider = fallback_provider_id()
    try:
        from extensions.llm.registry import active_llm_default

        provider = active_llm_default() or provider
    except Exception:
        pass
    meta = catalog_meta(provider)
    base_url = str(meta.get("default_base_url") or "").rstrip("/")
    model = str(meta.get("default_model") or "").strip()
    return {
        "enabled": True,
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "api_key": "",
        "temperature": 0.7,
        "max_tokens": 2048,
        "timeout_sec": 120,
        "system_prompt": get_default_system_prompt(loc),
    }


# 结构默认（中文 prompt）；灌库请用 build_default_llm_config()
DEFAULT_LLM_CONFIG = build_default_llm_config("zh-CN")
