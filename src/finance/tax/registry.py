# SPDX-License-Identifier: Apache-2.0
"""税务凭证 Provider 注册表。"""

from __future__ import annotations

from typing import Optional

from finance.tax.protocol import TaxDocumentProvider

_PROVIDER: Optional[TaxDocumentProvider] = None


def register_tax_provider(provider: TaxDocumentProvider) -> None:
    global _PROVIDER
    _PROVIDER = provider


def get_tax_provider() -> TaxDocumentProvider:
    from infra.hotel import ensure_hotel

    ensure_hotel()
    if _PROVIDER is None:
        from finance.tax.noop import NoopTaxProvider

        return NoopTaxProvider()
    return _PROVIDER


def reset_tax_provider() -> None:
    global _PROVIDER
    _PROVIDER = None
