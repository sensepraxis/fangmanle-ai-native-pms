# SPDX-License-Identifier: Apache-2.0
"""P1 状态机 / Strategy / Observer 补充测试。"""

from __future__ import annotations

import unittest


class HKTransitionTests(unittest.TestCase):
    def test_transition_to_and_helpers(self):
        from domain import InvalidStateError
        from models import HousekeepingTask

        t = HousekeepingTask(status="open")
        t.mark_assigned()
        self.assertEqual(t.status, "assigned")
        t.mark_in_progress()
        self.assertEqual(t.status, "in_progress")
        t.mark_pending_inspect()
        self.assertEqual(t.status, "pending_inspect")
        t.mark_done()
        self.assertEqual(t.status, "done")
        with self.assertRaises(InvalidStateError):
            t.mark_in_progress()

    def test_illegal_jump(self):
        from domain import InvalidStateError
        from models import HousekeepingTask

        t = HousekeepingTask(status="open")
        with self.assertRaises(InvalidStateError):
            t.transition_to("done")


class FolioDepositServiceRequestTests(unittest.TestCase):
    def test_folio_sync(self):
        from models import PmsFolio

        f = PmsFolio(status="open", balance=100, payment_total=0, charge_total=100)
        f.sync_status_from_totals()
        self.assertEqual(f.status, "open")
        f.balance = 0
        f.payment_total = 100
        f.sync_status_from_totals()
        self.assertEqual(f.status, "closed")
        self.assertIsNotNone(f.closed_at)

    def test_deposit_apply_event(self):
        from models import Deposit

        d = Deposit(
            deposit_id="T1",
            hotel_id=1,
            order_id=1,
            customer_id="c",
            room_no="101",
            form="CASH",
            original_amount=10000,
            captured_amount=0,
            remaining_refund=10000,
            status="CREATED",
        )
        d.apply_event("COLLECT")
        self.assertEqual(d.status, "FROZEN")
        d.apply_event("CAPTURE", full_capture=False)
        self.assertEqual(d.status, "PARTIAL_CAPTURE")
        d.apply_event("RELEASE")
        self.assertEqual(d.status, "RELEASED_AFTER_CAPTURE")

    def test_service_request_assign(self):
        from models import ServiceRequest

        sr = ServiceRequest(hotel_id=1, content="送水", status="open")
        sr.assign(5)
        self.assertEqual(sr.status, "assigned")
        self.assertEqual(sr.assignee_id, 5)
        sr.resolve()
        self.assertEqual(sr.status, "done")


class CouponStrategyTests(unittest.TestCase):
    def test_cash_and_discount(self):
        from mkt.coupon_strategy import build_face_text_by_type, calc_discount_by_type

        self.assertEqual(
            calc_discount_by_type("CASH_ALL", {"reduce_amount": 50, "threshold": 0}, 200),
            50,
        )
        self.assertEqual(
            calc_discount_by_type("DISCOUNT", {"discount_rate": 0.8, "max_discount": 30}, 200),
            30,
        )
        self.assertIn("立减", build_face_text_by_type("CASH_ROOM", reduce_amount=20, threshold=0))


class DepositStatusModuleTests(unittest.TestCase):
    def test_imported_from_service(self):
        from finance import deposit_service as ds
        from finance.deposit_status import TRANSITIONS as T2

        self.assertIs(ds.TRANSITIONS, T2)


if __name__ == "__main__":
    unittest.main()
