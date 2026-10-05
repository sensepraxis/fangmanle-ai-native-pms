# SPDX-License-Identifier: Apache-2.0
"""无税票。"""

from __future__ import annotations

from finance.tax.noop import NoopTaxProvider

NoopTax = NoopTaxProvider

__all__ = ["NoopTax", "NoopTaxProvider"]
