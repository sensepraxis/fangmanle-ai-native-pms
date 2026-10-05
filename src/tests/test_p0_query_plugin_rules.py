# SPDX-License-Identifier: Apache-2.0
"""读路径 Query 下沉冒烟（P0 Fat Query Router）。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock


class FinanceQueryServiceTests(unittest.TestCase):
    def test_list_ledger_entries_empty(self):
        from finance.finance_query_service import list_ledger_entries

        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter_by.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        out = list_ledger_entries(db, 1, limit=10)
        self.assertEqual(out["entries"], [])
        self.assertIn("summary", out)

    def test_flow_summary_shape(self):
        from finance.finance_query_service import finance_flow_summary

        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter_by.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.first.return_value = None
        q.count.return_value = 0
        q.all.return_value = []
        out = finance_flow_summary(db, 1)
        self.assertIsNone(out["latest_audit"])
        self.assertEqual(out["open_exceptions"], 0)
        self.assertEqual(out["reports"], [])


class GuestQueryServiceTests(unittest.TestCase):
    def test_list_tags_with_coverage(self):
        from guests.guest_query_service import list_tags_with_coverage

        db = MagicMock()
        tag = MagicMock()
        tag.id = 1
        # row_to_dict 会对 ORM 取 __table__.columns；这里绕开真实 ORM
        import guests.guest_query_service as mod

        orig = mod.row_to_dict
        mod.row_to_dict = lambda t: {"id": t.id, "name": "t"}
        try:
            q = MagicMock()
            db.query.return_value = q
            q.order_by.return_value = q
            q.all.return_value = [tag]
            q.group_by.return_value = q

            # second query for counts
            def query_side(*args, **kwargs):
                m = MagicMock()
                m.order_by.return_value = m
                m.group_by.return_value = m
                if len(args) >= 2:
                    m.all.return_value = [(1, 3)]
                else:
                    m.all.return_value = [tag]
                return m

            db.query.side_effect = query_side
            out = list_tags_with_coverage(db)
            self.assertEqual(out[0]["cover_count"], 3)
        finally:
            mod.row_to_dict = orig


class WecomTicketQueryTests(unittest.TestCase):
    def test_empty_token(self):
        from wecom.wecom_service.ticket_query import get_bind_ticket_by_token

        self.assertIsNone(get_bind_ticket_by_token(MagicMock(), ""))


class RuleEnginesDocTests(unittest.TestCase):
    def test_doc_exists(self):
        import os

        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, "docs", "RULE_ENGINES.md")
        self.assertTrue(os.path.isfile(path), path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("进程内 RuleSet", text)
        self.assertIn("mkt_auto_rules", text)


if __name__ == "__main__":
    unittest.main()
