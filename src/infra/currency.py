# SPDX-License-Identifier: Apache-2.0
"""货币展示：由酒店 YAML ``currency`` 驱动，禁止业务写死 ¥。"""

from __future__ import annotations

from typing import Any, Optional

# ISO 4217 → 常用符号（开源 fork 可再扩展）
_SYMBOLS: dict[str, str] = {
    "CNY": "¥",
    "JPY": "¥",
    "USD": "$",
    "SGD": "S$",
    "GBP": "£",
    "EUR": "€",
    "HKD": "HK$",
    "TWD": "NT$",
    "KRW": "₩",
    "THB": "฿",
    "VND": "₫",
    "MYR": "RM",
    "IDR": "Rp",
    "AUD": "A$",
    "CAD": "C$",
}


def hotel_currency_code() -> str:
    try:
        from infra.hotel import current_assembly, ensure_hotel

        ensure_hotel()
        code = str(current_assembly().currency or "").strip().upper()
        if code:
            return code
    except Exception:
        pass
    # 未组装时按 locale 粗分
    try:
        from infra.i18n import get_locale

        loc = str(get_locale() or "").lower()
        if loc.startswith("zh"):
            return "CNY"
    except Exception:
        pass
    return "USD"


def currency_symbol(code: Optional[str] = None) -> str:
    c = (code or hotel_currency_code()).strip().upper() or "USD"
    return _SYMBOLS.get(c, c + " ")


def format_money(
    amount: Any,
    *,
    code: Optional[str] = None,
    with_symbol: bool = True,
    digits: int = 2,
) -> str:
    try:
        n = float(amount or 0)
    except (TypeError, ValueError):
        n = 0.0
    body = f"{n:,.{digits}f}"
    if not with_symbol:
        return body
    return f"{currency_symbol(code)}{body}"


def currency_public_dict() -> dict[str, str]:
    code = hotel_currency_code()
    return {
        "currency": code,
        "currency_symbol": currency_symbol(code),
    }


__all__ = [
    "currency_public_dict",
    "currency_symbol",
    "format_money",
    "hotel_currency_code",
]
