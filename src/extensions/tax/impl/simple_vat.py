# SPDX-License-Identifier: Apache-2.0
"""价内增值税 / GST（酒店 YAML：tax.name + tax.rate 或 vendors.tax: simple_vat）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from infra.i18n import t
from models import Channel, Guest, Order


class SimpleVatTax:
    enabled = True
    supports_issue = True
    supports_void = True

    def __init__(
        self,
        *,
        name: str = "vat",
        tax_rate: float = 0.0,
        ota_codes: frozenset[str] | None = None,
    ) -> None:
        self.name = name
        self.tax_rate = float(tax_rate)
        self._ota = ota_codes or frozenset()

    def buyer_for_order(self, db: Session, order: Order, channel: Optional[Channel]) -> dict[str, str]:
        if order.agreement_id:
            from models import CorpAccount

            corp = db.get(CorpAccount, order.agreement_id)
            if corp:
                return {
                    "title_type": "corp_normal",
                    "buyer_name": corp.name or t("协议企业"),
                    "tax_no": (getattr(corp, "tax_no", None) or "").strip(),
                }
        if channel and (channel.code or "") in self._ota:
            ch_disp = t(channel.name) if channel.name else (channel.code or t("渠道"))
            return {
                "title_type": "corp_normal",
                "buyer_name": t("{ch} · 平台抬头", ch=ch_disp),
                "tax_no": "",
            }
        gname = None
        if order.guest_id:
            g = db.get(Guest, order.guest_id)
            gname = g.name if g else None
        name = gname or order.guest_phone or t("散客")
        return {"title_type": "personal", "buyer_name": name, "tax_no": ""}

    def split_amounts(self, gross: float, commission_rate: float) -> dict[str, float]:
        rate = self.tax_rate
        g = round(float(gross or 0), 2)
        fee = round(g * commission_rate, 2) if commission_rate > 0 else 0.0
        net = round(g - fee, 2)
        excl = round(g / (1 + rate), 2) if rate else g
        tax = round(g - excl, 2)
        return {
            "gross_amount": g,
            "platform_fee": fee,
            "net_amount": net,
            "tax_rate": rate,
            "tax_amount": tax,
            "amount_excl_tax": excl,
        }

    def issue(self, db: Session, hotel_id: int, order_id: int) -> None:
        # 国际 VAT/GST：本实现只做价税拆分；正式税局对接由各国 fork 扩展
        return None

    def void(self, db: Session, hotel_id: int, invoice_id: int, reason: str) -> None:
        return None

    def workspace(self, db: Session, hotel_id: int) -> dict:
        return {
            "tax_documents_enabled": True,
            "tax_provider": self.name,
            "tax_rate": self.tax_rate,
            "capabilities": {
                "split_amounts": True,
                "issue_to_authority": False,
                "void_to_authority": False,
                "note": "amount split only; no tax-authority e-invoice in this provider",
            },
        }


SimpleVatProvider = SimpleVatTax
