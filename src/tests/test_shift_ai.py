# SPDX-License-Identifier: Apache-2.0
"""
交班 / 接班 AI Harness 测试

运行: python test_shift_ai.py
"""

from __future__ import annotations

import sys
import unittest

import pytest

from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry, ensure_float_carry_2000
from bootstrap.ensure_shift_handover import ensure_shift_handover_schema
from database import SessionLocal, engine
from finance.shift_handover_service import build_workspace
from finance.shift_handover_service.task_service import guest_situations_for_display
from infra.commercial_pack import commercial_enabled
from models import ShiftHandover, ShiftHandoverTask

if commercial_enabled():
    from commercial.finance.shift_ai_harness import (
        confirm_shift_ai_draft,
        generate_shift_ai_draft,
        reject_shift_ai_draft,
    )
else:
    confirm_shift_ai_draft = generate_shift_ai_draft = reject_shift_ai_draft = None  # type: ignore

HOTEL_ID = 1


@pytest.mark.commercial
class ShiftAiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_shift_handover_schema(engine)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_ai01_generate_handover_draft(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        hid = ws["handover_id"]
        plan = generate_shift_ai_draft(self.db, HOTEL_ID, hid, "handover")
        self.assertEqual(plan["status"], "draft")
        self.assertIn("items", plan)
        self.assertIn(plan.get("source"), {"llm", "unavailable"})
        if plan.get("source") != "llm":
            self.assertEqual(plan.get("items") or [], [])
            return
        self.assertGreater(len(plan["items"]), 0)
        ops = {it["op"] for it in plan["items"]}
        self.assertIn("write_narrative", ops)
        forbidden = {"write_float", "write_sign", "write_revenue"}
        self.assertFalse(forbidden & ops)

    def test_ai02_items_have_source(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        plan = generate_shift_ai_draft(self.db, HOTEL_ID, ws["handover_id"], "handover")
        if plan.get("source") != "llm":
            self.assertEqual(plan.get("items") or [], [])
            return
        for it in plan["items"]:
            self.assertIn(
                it.get("source"), {"oneid_history", "restaurant_sys", "feedback_sys", "system_events", "inventory_sys"}
            )

    def test_ai03_confirm_writes_audit_fields(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        hid = ws["handover_id"]
        plan = generate_shift_ai_draft(self.db, HOTEL_ID, hid, "handover")
        if plan.get("source") != "llm":
            self.skipTest("无可用大模型，不把规则草稿当 AI 确认")
        for it in plan["items"]:
            it["selected"] = it["op"] in ("write_narrative", "write_task", "write_replenish_task")
        res = confirm_shift_ai_draft(self.db, HOTEL_ID, plan=plan, approved_by=1, operator_name="test")
        self.assertTrue(res["ok"])
        row = self.db.get(ShiftHandover, hid)
        self.assertIsNotNone(row.ai_draft_confirmed_at)
        self.assertIsNotNone(row.ai_approved_json)
        self.assertTrue(row.narrative)
        ai_tasks = self.db.query(ShiftHandoverTask).filter_by(handover_id=hid, created_by="ai_agent").all()
        self.assertGreaterEqual(len(ai_tasks), 0)

    def test_ai04_reject_clears_draft(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        hid = ws["handover_id"]
        generate_shift_ai_draft(self.db, HOTEL_ID, hid, "handover")
        reject_shift_ai_draft(self.db, HOTEL_ID, hid, operator_id=1, reason="测试驳回")
        row = self.db.get(ShiftHandover, hid)
        self.assertIsNone(row.ai_draft_json)

    def test_ai05_workspace_includes_ai_block(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        self.assertIn("ai", ws)
        self.assertIn("has_draft", ws["ai"])

    def test_ai06_snapshot_after_confirm(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        hid = ws["handover_id"]
        plan = generate_shift_ai_draft(self.db, HOTEL_ID, hid, "handover")
        guest_items = [it for it in plan["items"] if it["op"] == "write_guest_situation"]
        if guest_items:
            for it in plan["items"]:
                it["selected"] = it["op"] == "write_guest_situation"
            confirm_shift_ai_draft(self.db, HOTEL_ID, plan=plan, approved_by=1)
            row = self.db.get(ShiftHandover, hid)
            situations = guest_situations_for_display(self.db, HOTEL_ID, row)
            self.assertTrue(any(s.get("ai_generated") for s in situations))

    def test_ai07_generate_takeover_draft_has_items_and_calls_path(self):
        from finance.shift_takeover_service import build_takeover_workspace

        tw = build_takeover_workspace(self.db, HOTEL_ID, 1)
        if not tw.get("ready"):
            self.skipTest("当前无待接班交班单")
        hid = tw["handover_id"]
        plan = generate_shift_ai_draft(self.db, HOTEL_ID, hid, "takeover")
        self.assertEqual(plan["status"], "draft")
        self.assertIn(plan.get("source"), {"llm", "unavailable"})
        if plan.get("source") != "llm":
            self.assertEqual(plan.get("items") or [], [])
            return
        self.assertGreater(len(plan["items"]), 0)
        ops = {it["op"] for it in plan["items"]}
        self.assertIn("write_takeover_brief", ops)
        self.assertTrue({"write_advice", "write_guest_focus", "write_claim_hint", "write_diff_draft"} & ops)
        forbidden = {"write_float", "write_sign", "write_revenue"}
        self.assertFalse(forbidden & ops)
        self.assertEqual(plan.get("source"), "llm")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
    sys.exit(0 if result.wasSuccessful() else 1)
