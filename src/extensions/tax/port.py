# SPDX-License-Identifier: Apache-2.0
"""税票防腐接口：业务只依赖本 Protocol。"""

from __future__ import annotations

from finance.tax.protocol import TaxDocumentProvider

# 统一命名
ITax = TaxDocumentProvider

__all__ = ["ITax", "TaxDocumentProvider"]
