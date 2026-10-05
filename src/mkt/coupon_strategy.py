# SPDX-License-Identifier: Apache-2.0
"""券类型 Strategy：对齐 PaymentProvider 的表驱动扩展点。

``mkt_coupon_engine.calc_discount_amount`` / ``build_face_text`` 委托本注册表；
新增券型只需 ``register_coupon_type(...)``，不必再扩 elif。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from domain import InvalidStateError
from infra.i18n import t as _t


class CouponTypeStrategy(Protocol):
    coupon_type: str

    def calc_discount(self, fields: dict[str, Any], order_amount: float) -> float: ...

    def build_face_text(self, **kwargs: Any) -> str: ...


@dataclass
class _CashRoomStrategy:
    coupon_type: str = "CASH_ROOM"

    def calc_discount(self, fields: dict[str, Any], order_amount: float) -> float:
        thr = float(fields.get("threshold") or 0)
        if thr > 0 and order_amount > 0 and order_amount < thr:
            raise InvalidStateError(f"未满门槛¥{int(thr)}")
        return float(fields.get("reduce_amount") or 0)

    def build_face_text(self, **kwargs: Any) -> str:
        amt = int(float(kwargs.get("reduce_amount") or 0))
        thr = float(kwargs.get("threshold") or 0)
        if thr > 0:
            return _t("指定房型立减¥{amt}（满{thr}可用）").format(amt=amt, thr=int(thr))
        return _t("指定房型立减¥{amt}").format(amt=amt)


@dataclass
class _CashAllStrategy:
    coupon_type: str = "CASH_ALL"

    def calc_discount(self, fields: dict[str, Any], order_amount: float) -> float:
        thr = float(fields.get("threshold") or 0)
        if thr > 0 and order_amount > 0 and order_amount < thr:
            raise InvalidStateError(f"未满门槛¥{int(thr)}")
        return float(fields.get("reduce_amount") or 0)

    def build_face_text(self, **kwargs: Any) -> str:
        amt = int(float(kwargs.get("reduce_amount") or 0))
        return _t("通用立减¥{amt}（无门槛）").format(amt=amt)


@dataclass
class _DiscountStrategy:
    coupon_type: str = "DISCOUNT"

    def calc_discount(self, fields: dict[str, Any], order_amount: float) -> float:
        rate = float(fields.get("discount_rate") or 1)
        if order_amount <= 0:
            return 0.0
        saved = order_amount * (1.0 - rate)
        cap = fields.get("max_discount")
        if cap is not None:
            saved = min(saved, float(cap))
        return round(saved, 2)

    def build_face_text(self, **kwargs: Any) -> str:
        from infra.i18n import get_locale

        rate = float(kwargs.get("discount_rate") or 0)
        if str(get_locale() or "").lower().startswith("en") and 0 < rate <= 1:
            # 7折 → 30% off（按减免比例，避免 "{n}% off" 误成 7% off）
            label = f"{int(round((1.0 - rate) * 100))}% off"
        elif 0 < rate <= 1:
            n = f"{(rate * 10):.1f}".rstrip("0").rstrip(".")
            label = _t("{n}折").format(n=n)
        else:
            label = _t("{n}折").format(n=rate)
        max_discount = kwargs.get("max_discount")
        if max_discount:
            return _t("房价{label}（最高减¥{cap}）").format(label=label, cap=int(float(max_discount)))
        return _t("房价{label}").format(label=label)


@dataclass
class _BenefitStrategy:
    coupon_type: str = "BENEFIT"

    def calc_discount(self, fields: dict[str, Any], order_amount: float) -> float:
        return 0.0

    def build_face_text(self, **kwargs: Any) -> str:
        key = (kwargs.get("benefit_key") or "CUSTOM").upper()
        val = (kwargs.get("benefit_value") or "").strip()
        cn = {
            "BREAKFAST": _t("免费双早"),
            "LATE_CHECKOUT": (_t("延迟退房至 {val}").format(val=val) if val else _t("延迟退房")),
            "ROOM_UPGRADE": (_t("升房·{val}").format(val=val) if val else _t("升房")),
            "FREE_NIGHT": (_t("住{val}送1").format(val=val or "N") if val else _t("连住送夜")),
            "CUSTOM": val or _t("专属权益"),
        }
        return (cn.get(key) or val or _t("权益券"))[:128]


_STRATEGIES: dict[str, CouponTypeStrategy] = {}


def register_coupon_type(strategy: CouponTypeStrategy) -> None:
    _STRATEGIES[strategy.coupon_type.upper()] = strategy


def get_coupon_strategy(coupon_type: str) -> CouponTypeStrategy:
    key = (coupon_type or "").strip().upper()
    if key not in _STRATEGIES:
        raise InvalidStateError(f"不支持的券类型「{coupon_type}」")
    return _STRATEGIES[key]


def calc_discount_by_type(coupon_type: str, fields: dict[str, Any], order_amount: float) -> float:
    return get_coupon_strategy(coupon_type).calc_discount(fields, order_amount)


def build_face_text_by_type(coupon_type: str, **kwargs: Any) -> str:
    return get_coupon_strategy(coupon_type).build_face_text(**kwargs)


# 内置注册
for _s in (_CashRoomStrategy(), _CashAllStrategy(), _DiscountStrategy(), _BenefitStrategy()):
    register_coupon_type(_s)


__all__ = [
    "CouponTypeStrategy",
    "register_coupon_type",
    "get_coupon_strategy",
    "calc_discount_by_type",
    "build_face_text_by_type",
]
