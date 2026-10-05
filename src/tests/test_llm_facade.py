# SPDX-License-Identifier: Apache-2.0
"""LLM facade：可插拔，不假定 Ollama·qwen3:8b。"""

from __future__ import annotations

import unittest

import pytest


class LlmFacadeTests(unittest.TestCase):
    def tearDown(self):
        from extensions.llm.registry import activate_llm_extension, reset_llm_extension

        reset_llm_extension()
        activate_llm_extension(None)

    def test_resolve_model_follows_provider_catalog(self):
        from extensions.llm.facade import resolve_model_name, resolve_provider_id
        from extensions.llm.registry import activate_llm_extension, reset_llm_extension

        reset_llm_extension()
        activate_llm_extension("siliconflow")
        self.assertEqual(resolve_provider_id({"provider": "siliconflow"}), "siliconflow")
        self.assertEqual(
            resolve_model_name({"provider": "siliconflow"}),
            "Qwen/Qwen3-8B",
        )
        self.assertEqual(
            resolve_model_name({"provider": "deepseek"}),
            "deepseek-v4-flash",
        )
        # 显式配置优先于目录默认
        self.assertEqual(
            resolve_model_name({"provider": "siliconflow", "model": "Qwen/Qwen2.5-7B-Instruct"}),
            "Qwen/Qwen2.5-7B-Instruct",
        )

    def test_identity_not_hardcoded_ollama_qwen(self):
        from extensions.llm.facade import llm_identity

        ident = llm_identity({"provider": "deepseek", "model": "deepseek-v4-flash"})
        self.assertEqual(ident["provider"], "deepseek")
        self.assertEqual(ident["model"], "deepseek-v4-flash")
        self.assertNotEqual(ident["model"], "qwen3:8b")

    @pytest.mark.commercial
    def test_build_default_respects_active_extension(self):
        from commercial.ai_core.llm_defaults import build_default_llm_config
        from extensions.llm.registry import activate_llm_extension, reset_llm_extension

        reset_llm_extension()
        activate_llm_extension("deepseek")
        cfg = build_default_llm_config("zh-CN")
        self.assertEqual(cfg["provider"], "deepseek")
        self.assertEqual(cfg["model"], "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
