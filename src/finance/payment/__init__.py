# SPDX-License-Identifier: Apache-2.0
"""退房结算支付策略（Strategy + Registry）。

对齐 messaging Factory / LLM_PROVIDERS：checkout 只选策略，不写 if/elif 分支。

用法::

    from finance.payment import resolve_checkout_mode, get_payment_provider
    mode = resolve_checkout_mode(order, channel, source_group, payment_mode="auto")
    get_payment_provider(mode).settle(db, order, method="wechat", pos_slip_no=None)
"""

from __future__ import annotations

from finance.payment.protocol import PaymentSettleContext, PaymentSettleProvider
from finance.payment.registry import (
    PAYMENT_MODES,
    get_payment_provider,
    register_payment_provider,
    resolve_checkout_mode,
    unregister_payment_provider,
)

__all__ = [
    "PaymentSettleContext",
    "PaymentSettleProvider",
    "PAYMENT_MODES",
    "get_payment_provider",
    "register_payment_provider",
    "unregister_payment_provider",
    "resolve_checkout_mode",
]
