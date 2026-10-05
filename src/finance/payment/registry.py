# SPDX-License-Identifier: Apache-2.0
"""支付策略注册表 + auto 模式解析。"""

from __future__ import annotations

from finance.payment.protocol import PaymentSettleProvider
from finance.payment.providers import (
    CollectSettleProvider,
    CorpSettleProvider,
    PrepaidSettleProvider,
)
from models import Order

# mode → provider（对齐 LLM_PROVIDERS / messaging factory）
_PROVIDERS: dict[str, PaymentSettleProvider] = {
    "corp": CorpSettleProvider(),
    "collect": CollectSettleProvider(),
    "prepaid": PrepaidSettleProvider(),
}

PAYMENT_MODES = tuple(_PROVIDERS.keys())


def get_payment_provider(mode: str) -> PaymentSettleProvider:
    """按结算模式取策略；未知 mode 抛 ValueError。"""
    key = (mode or "").strip().lower()
    if key not in _PROVIDERS:
        raise ValueError(f"不支持的支付结算模式: {mode!r}；可选 {PAYMENT_MODES}")
    return _PROVIDERS[key]


def resolve_checkout_mode(
    order: Order,
    *,
    source_group: str = "",
    payment_mode: str = "auto",
) -> str:
    """将 auto / 显式模式解析为 corp|collect|prepaid。"""
    mode = (payment_mode or "auto").strip().lower()
    if mode != "auto":
        if mode not in _PROVIDERS:
            raise ValueError(f"不支持的支付结算模式: {payment_mode!r}")
        return mode
    sg = source_group or ""
    if sg == "agreement" or order.payment_status == "on_account" or int(order.order_type or 0) == 3:
        return "corp"
    if sg in ("ota", "voucher") or order.payment_status == "paid" or bool(order.channel_prepaid):
        return "prepaid"
    return "collect"


def register_payment_provider(mode: str, provider: PaymentSettleProvider) -> None:
    """插件/测试可注册自定义结算策略。"""
    _PROVIDERS[mode.strip().lower()] = provider


def unregister_payment_provider(mode: str) -> bool:
    """卸载插件注册的结算策略；内置 corp/collect/prepaid 不可卸。"""
    key = (mode or "").strip().lower()
    if key in ("corp", "collect", "prepaid"):
        raise ValueError(f"不可卸载内置支付模式: {key}")
    return _PROVIDERS.pop(key, None) is not None


__all__ = [
    "PAYMENT_MODES",
    "get_payment_provider",
    "resolve_checkout_mode",
    "register_payment_provider",
    "unregister_payment_provider",
]
