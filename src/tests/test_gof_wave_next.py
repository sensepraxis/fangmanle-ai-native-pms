# SPDX-License-Identifier: Apache-2.0
"""下一波 GoF：报表 Registry / 押金绞杀 / 事件 Matcher / AI Harness 基座。"""

from __future__ import annotations

import unittest

import pytest


class ReportBuildersRegistryTests(unittest.TestCase):
    def test_registry_covers_catalog_codes(self):
        from finance.reports.builders import REPORT_BUILDERS, REPORT_META

        for code in (
            "manager_flash",
            "channel_sales",
            "p_l",
            "trial_balance",
            "night_daily",
            "vat_summary",
        ):
            self.assertIn(code, REPORT_BUILDERS)
        # 未知 code 走 night_daily 兜底
        self.assertIn("night_daily", REPORT_BUILDERS)
        self.assertTrue(REPORT_META)


class DepositStranglerTests(unittest.TestCase):
    def test_facade_reexports(self):
        from finance import deposit_board, deposit_lookup, deposit_ops
        from finance import deposit_service as ds

        self.assertIs(ds.board, deposit_board.board)
        self.assertIs(ds.detect_anomalies, deposit_board.detect_anomalies)
        self.assertIs(ds.collect, deposit_ops.collect)
        self.assertIs(ds.capture, deposit_ops.capture)
        self.assertIs(ds.lookup_by_phone, deposit_lookup.lookup_by_phone)


class AutoRuleEventMatcherTests(unittest.TestCase):
    def test_table_driven_match(self):
        from mkt.auto_rule_event_matchers import EVENT_MATCHERS, get_event_matcher
        from mkt.mkt_auto_rules import _event_match

        self.assertGreaterEqual(len(EVENT_MATCHERS), 9)
        fn = get_event_matcher("HIGH_VALUE_NEW")
        ok, text = fn({"min_avg_order": 500}, {"stay_records": 1, "avg_order_value": 600}, None)
        self.assertTrue(ok)
        self.assertIn("500", text)

        class Rule:
            event_type = "CUSTOM"
            event_params = '{"event_key":"FOO"}'

        ok2, _ = _event_match(Rule(), {}, event_key="FOO")
        self.assertTrue(ok2)
        ok3, _ = _event_match(Rule(), {}, event_key="BAR")
        self.assertFalse(ok3)


@pytest.mark.commercial
class AiHarnessBaseTests(unittest.TestCase):
    def test_parse_and_scenes(self):
        import commercial.finance.shift_ai_harness  # noqa: F401 — 触发注册
        import commercial.hk.hk_ai_harness  # noqa: F401
        from commercial.ai_core.ai_harness_base import parse_json_blob, strip_think
        from commercial.hk.hk_ai_scene_registry import list_hk_scenes
        from finance.shift_scene_registry import list_shift_scenes

        self.assertEqual(parse_json_blob('```json\n{"x":1}\n```'), {"x": 1})
        self.assertTrue(strip_think("<think>ab</think>ok").endswith("ok") or strip_think("<think>ab</think>ok") == "ok")
        self.assertEqual(set(list_shift_scenes()), {"handover", "takeover"})
        self.assertIn("cleaning_plan", list_hk_scenes())


@pytest.mark.commercial
class LocaleLlmPipelineTests(unittest.TestCase):
    def setUp(self):
        from infra.i18n import clear_locale, reload_catalogs

        reload_catalogs()
        clear_locale()

    def tearDown(self):
        from infra.i18n import clear_locale

        clear_locale()

    def test_locale_text_en_drops_cjk(self):
        from commercial.ai_core.locale_llm import locale_optional, locale_str_list, locale_text
        from infra.i18n import set_locale, t

        set_locale("en")
        self.assertEqual(locale_text("建议确认 3 张操作单", "建议确认 {n} 张操作单"), t("建议确认 {n} 张操作单"))
        self.assertIsNone(locale_optional("备用金已对平"))
        self.assertIsNone(locale_str_list(["临期押金"]))
        self.assertEqual(locale_text("Confirm 2 tickets", "建议确认 {n} 张操作单"), "Confirm 2 tickets")

    def test_compose_system_appends_language_once(self):
        from commercial.ai_core.locale_llm import compose_system
        from commercial.ai_core.prompt_packs import language_instruction
        from infra.i18n import set_locale

        set_locale("en")
        lang = language_instruction()
        once = compose_system("You are a clerk.")
        twice = compose_system(once)
        self.assertIn(lang, once)
        self.assertEqual(once.count(lang), 1)
        self.assertEqual(twice.count(lang), 1)

    def test_parse_llm_json_truncated_and_fence(self):
        from commercial.ai_core.locale_llm import parse_llm_json

        fenced = parse_llm_json('```json\n{"summary":"ok","selected_ids":["a"]}\n```')
        self.assertEqual(fenced["summary"], "ok")
        truncated = parse_llm_json('{"insight":"RevPAR down","findings":[{"title":"occ"')
        self.assertIsInstance(truncated, dict)
        self.assertEqual(truncated.get("insight"), "RevPAR down")

    def test_run_locale_llm_json_retry_then_ok(self):
        from commercial.ai_core.locale_llm import run_locale_llm_json
        from infra.i18n import set_locale

        set_locale("en")
        calls = {"n": 0}

        def chat(_db, messages, system, overrides=None):
            calls["n"] += 1
            self.assertIn("Language: Respond entirely in English", system)
            if calls["n"] == 1:
                return {"content": "not json", "model": "m1"}
            return {"content": '{"summary":"Pick two tickets","selected_ids":["f-1"]}', "model": "m2"}

        result = run_locale_llm_json(
            None,
            system="You are a clerk.",
            user="pick",
            retry_user="again",
            chat_fn=chat,
        )
        self.assertEqual(calls["n"], 2)
        self.assertIsNone(result.error)
        self.assertEqual(result.parsed.get("summary"), "Pick two tickets")
        self.assertEqual(result.model, "m2")


if __name__ == "__main__":
    unittest.main()
