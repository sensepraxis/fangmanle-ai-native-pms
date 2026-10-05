# SPDX-License-Identifier: Apache-2.0
"""Rule Engine 单元测试 + hk 派单规则 demo 验证。"""

from __future__ import annotations

import unittest

from rules import Rule, RuleSet, apply, get_rule_set, register_rule_set


class RuleEngineUnitTests(unittest.TestCase):
    def test_basic_predicate_action(self):
        rs = RuleSet("test_basic")
        fired = []

        def add_five(ctx):
            fired.append(ctx["n"] + 5)

        rs.register(
            Rule(
                id="R1",
                name="Add five",
                when=lambda ctx: ctx["n"] > 3,
                then=add_five,
                priority=100,
            )
        )

        ctx = {"n": 10}
        traces = rs.apply(ctx)
        self.assertEqual(len(traces), 1)
        self.assertTrue(traces[0].matched)
        self.assertEqual(fired, [15])

    def test_priority_order(self):
        rs = RuleSet("test_prio")
        fired = []

        rs.register(
            Rule(
                id="R_low",
                name="low",
                when=lambda c: True,
                then=lambda c: fired.append("low"),
                priority=1,
            )
        )
        rs.register(
            Rule(
                id="R_high",
                name="high",
                when=lambda c: True,
                then=lambda c: fired.append("high"),
                priority=100,
            )
        )

        rs.apply({})
        # R_high priority=100 先跑，stop_on_match=True (default) → 终止后续
        self.assertEqual(fired, ["high"])

    def test_priority_order_with_no_stop(self):
        rs = RuleSet("test_prio_no_stop")
        fired = []

        rs.register(
            Rule(
                id="R_low",
                name="low",
                when=lambda c: True,
                then=lambda c: fired.append("low"),
                priority=1,
                stop_on_match=False,
            )
        )
        rs.register(
            Rule(
                id="R_high",
                name="high",
                when=lambda c: True,
                then=lambda c: fired.append("high"),
                priority=100,
                stop_on_match=False,
            )
        )

        rs.apply({})
        # 两条都 stop_on_match=False → 按 priority 顺序都跑
        self.assertEqual(fired, ["high", "low"])

    def test_stop_on_match_false(self):
        rs = RuleSet("test_no_stop")
        fired = []

        rs.register(
            Rule(
                id="R1",
                name="first",
                when=lambda c: True,
                then=lambda c: fired.append("first"),
                priority=100,
                stop_on_match=False,
            )
        )
        rs.register(
            Rule(
                id="R2",
                name="second",
                when=lambda c: True,
                then=lambda c: fired.append("second"),
                priority=50,
            )
        )

        rs.apply({})
        self.assertEqual(fired, ["first", "second"])

    def test_predicate_exception_isolated(self):
        rs = RuleSet("test_err")
        fired = []

        def boom(ctx):
            raise RuntimeError("predicate broken")

        rs.register(
            Rule(
                id="R_boom",
                name="boom",
                when=boom,
                then=lambda c: None,
                priority=100,
            )
        )
        rs.register(
            Rule(
                id="R_ok",
                name="ok",
                when=lambda c: True,
                then=lambda c: fired.append("ok"),
                priority=50,
            )
        )

        ctx = {}
        traces = rs.apply(ctx)
        self.assertEqual(fired, ["ok"])
        # R_boom 失败但不影响 R_ok
        matched_ids = [t.rule_id for t in traces if t.matched]
        self.assertEqual(matched_ids, ["R_ok"])

    def test_unregister(self):
        rs = RuleSet("test_unreg")
        rule = Rule(id="R1", name="r", when=lambda c: True, then=lambda c: None)
        rs.register(rule)
        self.assertEqual(len(rs.list_rules()), 1)
        self.assertTrue(rs.unregister("R1"))
        self.assertEqual(len(rs.list_rules()), 0)

    def test_global_register_get(self):
        rs = RuleSet("test_global")
        register_rule_set(rs)
        got = get_rule_set("test_global")
        self.assertIs(got, rs)

        # apply 便捷函数
        fired = []
        rs.register(
            Rule(
                id="R_global",
                name="g",
                when=lambda c: True,
                then=lambda c: fired.append(c["v"]),
            )
        )
        traces = apply("test_global", {"v": 42})
        self.assertEqual(fired, [42])
        self.assertEqual(traces[0].rule_id, "R_global")


class HKDemoRuleTests(unittest.TestCase):
    """hk/hk_rules.py 注册的演示规则（由 conftest 自动加载）。"""

    def test_vip_dispatch_priority(self):
        from hk.hk_rules import HK_DISPATCH_RULESET

        self.assertIsNotNone(HK_DISPATCH_RULESET)
        ctx = {"task_id": 1, "guest_vip": True, "hour": 14}
        traces = HK_DISPATCH_RULESET.apply(ctx)
        # 按 priority 倒序：R004(110) → R001(100) → R002(90) → R003(80)
        # R004 (urgency=1) False；R001 (guest_vip=True) True → stop_on_match
        r001_trace = next(t for t in traces if t.rule_id == "R001")
        self.assertTrue(r001_trace.matched)
        self.assertTrue(ctx.get("priority_boost"))
        self.assertEqual(ctx.get("assignee_id"), 1)

    def test_night_task_escalation(self):
        from hk.hk_rules import HK_DISPATCH_RULESET

        ctx = {"task_id": 2, "hour": 3}
        HK_DISPATCH_RULESET.apply(ctx)
        self.assertEqual(ctx.get("escalation"), "night_team")

    def test_same_floor_match(self):
        from hk.hk_rules import HK_DISPATCH_RULESET

        ctx = {"room_floor": 3, "staff_floor": 3}
        HK_DISPATCH_RULESET.apply(ctx)
        self.assertTrue(ctx.get("priority_boost"))

    def test_urgency_1_immediate(self):
        from hk.hk_rules import HK_DISPATCH_RULESET

        ctx = {"urgency": 1}
        HK_DISPATCH_RULESET.apply(ctx)
        self.assertTrue(ctx.get("immediate"))
        self.assertTrue(ctx.get("notify_supervisor"))
