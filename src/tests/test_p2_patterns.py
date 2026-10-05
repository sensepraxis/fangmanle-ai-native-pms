# SPDX-License-Identifier: Apache-2.0
"""P2：Strategy / CoR / Template Method / Query Object 单测。"""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.commercial
class FinanceAiSceneRegistryTests(unittest.TestCase):
    def test_scenes_registered(self):
        import commercial.finance.finance_ai_harness as harness  # noqa: F401 — 触发注册
        from commercial.finance.ai_scene_registry import get_finance_scene, list_finance_scenes

        scenes = list_finance_scenes()
        self.assertIn("deposit", scenes)
        self.assertIn("ar_ap", scenes)
        meta = get_finance_scene("recon")
        self.assertEqual(meta["title"], "AI 对账安排")


class DualAuthChainTests(unittest.TestCase):
    def test_mgr_then_fin(self):
        from domain import InvalidStateError
        from finance.dual_auth_chain import apply_dual_auth_role

        class T:
            auth_mgr_done = 0
            auth_fin_done = 0
            auth_mgr_by = None
            auth_fin_by = None

        t = T()
        self.assertEqual(apply_dual_auth_role(t, "gm", "alice"), "AUTH_MGR")
        self.assertEqual(t.auth_mgr_done, 1)
        self.assertEqual(apply_dual_auth_role(t, "fin", "bob"), "AUTH_FIN")
        self.assertEqual(t.auth_fin_done, 1)
        with self.assertRaises(InvalidStateError):
            apply_dual_auth_role(t, "hacker", "x")


class NightAuditPipelineTests(unittest.TestCase):
    def test_pipeline_steps_order(self):
        from finance.night_audit_pipeline import NightAuditContext, NightAuditPipeline

        calls = []

        class Spy(NightAuditPipeline):
            def step_post_room_charges(self, ctx):
                calls.append("post")

            def step_flip_rooms(self, ctx):
                calls.append("flip")

            def step_purge_id_docs(self, ctx):
                calls.append("purge")

            def step_summarize_or_skip(self, ctx):
                calls.append("sum")
                ctx.skipped_summary = True
                ctx.result = {"ok": True}

            def step_persist_log(self, ctx):
                calls.append("persist")

            def step_commit(self, ctx):
                calls.append("commit")

            def step_emit(self, ctx):
                calls.append("emit")

        db = MagicMock()
        ctx = NightAuditContext(db=db, hotel_id=1, biz_date=date(2026, 10, 1))
        out = Spy().run(ctx)
        self.assertEqual(calls, ["post", "flip", "purge", "sum", "commit", "emit"])
        self.assertTrue(out.get("ok"))


class OpenServiceRequestsQueryTests(unittest.TestCase):
    def test_as_dicts_empty(self):
        from hk.queries import OpenServiceRequestsQuery

        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        self.assertEqual(OpenServiceRequestsQuery(hotel_id=1).as_dicts(db), [])


class IntentRegisterTests(unittest.TestCase):
    def test_register_intent(self):
        from analytics.ask_catalog import INTENT_CATALOG, get_intent, register_intent

        register_intent(
            "p2_test_intent",
            {"intent_label": "P2测试", "required_slots": [], "keywords": ["p2test"]},
        )
        self.assertIn("p2_test_intent", INTENT_CATALOG)
        self.assertEqual(get_intent("p2_test_intent")["intent_label"], "P2测试")
        INTENT_CATALOG.pop("p2_test_intent", None)


class BoundedContextDocTests(unittest.TestCase):
    def test_doc(self):
        import os

        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, "docs", "BOUNDED_CONTEXTS.md")
        self.assertTrue(os.path.isfile(path))
        text = open(path, encoding="utf-8").read()
        self.assertIn("application.orders", text)
        self.assertIn("RULE_ENGINES", text)
        fw = os.path.join(root, "docs", "FRAMEWORK.md")
        self.assertTrue(os.path.isfile(fw))
        self.assertIn("register_intent", open(fw, encoding="utf-8").read())


class FrameworkHookTests(unittest.TestCase):
    def test_register_query(self):
        from analytics.ask_queries import QUERY_REGISTRY, register_query

        def _fn(*_a, **_k):
            return {"title": "hook"}

        register_query("q_p2_hook", _fn)
        self.assertIs(QUERY_REGISTRY["q_p2_hook"], _fn)
        QUERY_REGISTRY.pop("q_p2_hook", None)

    def test_pricing_rule_hook_roundtrip(self):
        from pricing.pricing_assistant.rule_hooks import (
            list_pricing_rule_hooks,
            register_pricing_rule_hook,
            run_extra_recommendation_hooks,
        )

        def _hook(_db, _hid, _ctx):
            return 0

        register_pricing_rule_hook("p2_noop", _hook)
        self.assertIn("p2_noop", list_pricing_rule_hooks())
        self.assertEqual(run_extra_recommendation_hooks(None, 1, {}), 0)

    def test_shift_scene_registry_api(self):
        from finance.shift_scene_registry import list_shift_scenes, register_shift_scene

        self.assertTrue(callable(register_shift_scene))
        self.assertIsInstance(list_shift_scenes(), tuple)


if __name__ == "__main__":
    unittest.main()
