# SPDX-License-Identifier: Apache-2.0
"""支付结算 Strategy 单元测试。"""

from __future__ import annotations

import unittest

from finance.payment import (
    PAYMENT_MODES,
    PaymentSettleContext,
    get_payment_provider,
    resolve_checkout_mode,
)
from finance.payment.registry import register_payment_provider
from models import Order


class PaymentStrategyTests(unittest.TestCase):
    def test_modes_registered(self):
        self.assertEqual(set(PAYMENT_MODES), {"corp", "collect", "prepaid"})
        for m in PAYMENT_MODES:
            self.assertEqual(get_payment_provider(m).mode, m)

    def test_resolve_auto(self):
        o = Order(status="checked_in", payment_status="unpaid", order_type=1, channel_prepaid=False)
        self.assertEqual(resolve_checkout_mode(o, source_group="direct", payment_mode="auto"), "collect")
        self.assertEqual(resolve_checkout_mode(o, source_group="ota", payment_mode="auto"), "prepaid")
        self.assertEqual(resolve_checkout_mode(o, source_group="agreement", payment_mode="auto"), "corp")
        o2 = Order(status="checked_in", payment_status="unpaid", order_type=3)
        self.assertEqual(resolve_checkout_mode(o2, payment_mode="auto"), "corp")
        o3 = Order(status="checked_in", payment_status="paid", order_type=1)
        self.assertEqual(resolve_checkout_mode(o3, payment_mode="auto"), "prepaid")

    def test_resolve_explicit(self):
        o = Order(status="checked_in", payment_status="unpaid", order_type=1)
        self.assertEqual(resolve_checkout_mode(o, payment_mode="prepaid"), "prepaid")
        with self.assertRaises(ValueError):
            resolve_checkout_mode(o, payment_mode="bitcoin")

    def test_unknown_provider(self):
        with self.assertRaises(ValueError):
            get_payment_provider("cash_only")

    def test_prepaid_settle_marks_paid(self):
        class FakeDb:
            pass

        o = Order(status="checked_in", payment_status="unpaid", total_amount=100)
        get_payment_provider("prepaid").settle(FakeDb(), o, PaymentSettleContext())
        self.assertEqual(o.payment_status, "paid")

    def test_register_custom_provider(self):
        class Fake:
            mode = "custom_test"

            def settle(self, db, order, ctx):
                order.payment_status = "custom"

        register_payment_provider("custom_test", Fake())
        o = Order(status="checked_in", payment_status="unpaid")
        get_payment_provider("custom_test").settle(None, o, PaymentSettleContext())
        self.assertEqual(o.payment_status, "custom")
