# SPDX-License-Identifier: Apache-2.0
"""税务凭证契约：开具/红冲口径由 pack 提供；AR 挂账不在此。"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from models import Channel, Order


@runtime_checkable
class TaxDocumentProvider(Protocol):
    name: str
    enabled: bool
    supports_issue: bool
    supports_void: bool
    tax_rate: float

    def buyer_for_order(self, db: Session, order: Order, channel: Optional[Channel]) -> dict[str, str]: ...

    def split_amounts(self, gross: float, commission_rate: float) -> dict[str, float]: ...

    def issue(self, db: Session, hotel_id: int, order_id: int) -> None:
        """开具前校验/地区税控钩子。内核随后写 Invoice 状态机。"""
        ...

    def void(self, db: Session, hotel_id: int, invoice_id: int, reason: str) -> None:
        """红冲前校验/地区税控钩子。"""
        ...

    def workspace(self, db: Session, hotel_id: int) -> dict[str, Any]:
        """工作台附加字段（enabled / provider 等）。"""
        ...
