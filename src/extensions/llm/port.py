# SPDX-License-Identifier: Apache-2.0
"""LLM 防腐层契约。

说明：
- ``LlmProvider``：厂商目录项（可插拔选型：ollama / siliconflow / deepseek / …）
- 运行时对话统一走 ``extensions.llm.facade.chat``（读 DB 当前 provider/model），
  不在 Port 实例上绑死某一模型名。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmProvider(Protocol):
    """大模型厂商目录契约。密钥与模型落在 AppSetting.llm（按 provider 分 profile）。"""

    name: str

    def meta(self) -> dict[str, Any]:
        """UI 目录：label / kind / needs_api_key / default_model / default_base_url…"""
        ...

    def kind(self) -> str:
        """传输形态：ollama | openai_compatible（与具体模型名无关）。"""
        ...
