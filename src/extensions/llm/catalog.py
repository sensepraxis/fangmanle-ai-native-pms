# SPDX-License-Identifier: Apache-2.0
"""LLM Provider 目录（扩展点元数据）。实现细节仍在 ai_core.llm_service。"""

from __future__ import annotations

from typing import Any

# id 与 AppSetting.llm.provider / 页面选择一致
LLM_PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "ollama",
        "label": "Ollama（本地）",
        "kind": "ollama",
        "needs_api_key": False,
        "default_base_url": "http://127.0.0.1:11434",
        "default_model": "qwen3:8b",
        "hint": "本地部署，无需 API Key。",
    },
    {
        "id": "bailian",
        "label": "阿里云百炼",
        "kind": "openai_compatible",
        "needs_api_key": True,
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "hint": "OpenAI 兼容接口，在百炼控制台申请 API Key。",
    },
    {
        "id": "siliconflow",
        "label": "硅基流动",
        "kind": "openai_compatible",
        "needs_api_key": True,
        "default_base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen3-8B",
        "hint": "OpenAI 兼容接口；模型名需带厂商前缀。",
    },
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "kind": "openai_compatible",
        "needs_api_key": True,
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-v4-flash",
        "hint": "",
    },
    {
        "id": "qwen",
        "label": "通义千问（兼容）",
        "kind": "openai_compatible",
        "needs_api_key": True,
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "hint": "与百炼兼容；可用 vendors.llm: qwen 作为出厂默认。",
    },
    {
        "id": "openai_compatible",
        "label": "其他 OpenAI 兼容",
        "kind": "openai_compatible",
        "needs_api_key": True,
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "hint": "任意 OpenAI Compatible 网关。",
    },
]

_BY_ID = {str(p["id"]): p for p in LLM_PROVIDER_CATALOG}


def catalog_ids() -> list[str]:
    return [str(p["id"]) for p in LLM_PROVIDER_CATALOG]


def catalog_meta(provider_id: str) -> dict[str, Any]:
    """未知 id 回退到通用 OpenAI 兼容（不假定本地 Ollama）。"""
    pid = (provider_id or "").strip().lower()
    if pid in _BY_ID:
        return dict(_BY_ID[pid])
    return dict(_BY_ID["openai_compatible"])
