# SPDX-License-Identifier: Apache-2.0
"""不开税务凭证：税额为 0，issue/void 标记为不支持。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError
from infra.i18n import t
from models import Channel, Guest, Order


class NoopTaxProvider:
    name = "noop"
    enabled = False
    supports_issue = False
    supports_void = False
    tax_rate = 0.0

    def buyer_for_order(self, db: Session, order: Order, channel: Optional[Channel]) -> dict[str, str]:
        gname = None
        if order.guest_id:
            g = db.get(Guest, order.guest_id)
            gname = g.name if g else None
        name = gname or order.guest_phone or t("散客")
        return {"title_type": "personal", "buyer_name": name, "tax_no": ""}

    def split_amounts(self, gross: float, commission_rate: float) -> dict[str, float]:
        g = round(float(gross or 0), 2)
        fee = round(g * commission_rate, 2) if commission_rate > 0 else 0.0
        return {
            "gross_amount": g,
            "platform_fee": fee,
            "net_amount": round(g - fee, 2),
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "amount_excl_tax": g,
        }

    def issue(self, db: Session, hotel_id: int, order_id: int) -> None:
        raise InvalidStateError(t("本部署未启用税务凭证"))

    def void(self, db: Session, hotel_id: int, invoice_id: int, reason: str) -> None:
        raise InvalidStateError(t("本部署未启用税务凭证"))

    def workspace(self, db: Session, hotel_id: int) -> dict:
        return {
            "tax_documents_enabled": False,
            "tax_provider": self.name,
        }
