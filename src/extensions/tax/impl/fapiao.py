# SPDX-License-Identifier: Apache-2.0
"""数电票口径（酒店 YAML：vendors.tax: fapiao）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from infra.i18n import t
from models import Channel, CorpAccount, Guest, Order

TAX_RATE = 0.06
OTA_CODES = {
    "ctrip",
    "meituan",
    "fliggy",
    "douyin",
    "xiaohongshu",
    "meituan_voucher",
    "ota",
}


class FapiaoTax:
    name = "fapiao"
    enabled = True
    supports_issue = True
    supports_void = True
    tax_rate = TAX_RATE

    def buyer_for_order(self, db: Session, order: Order, channel: Optional[Channel]) -> dict[str, str]:
        if order.agreement_id:
            corp = db.get(CorpAccount, order.agreement_id)
            if corp:
                return {
                    "title_type": "corp_special",
                    "buyer_name": corp.name or t("协议企业"),
                    "tax_no": (getattr(corp, "tax_no", None) or "").strip(),
                }
        if channel and (channel.code or "") in OTA_CODES:
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
        mask = (name[0] + "*") if name else t("个人")
        return {"title_type": "personal", "buyer_name": t("个人 · {mask}", mask=mask), "tax_no": ""}

    def split_amounts(self, gross: float, commission_rate: float) -> dict[str, float]:
        g = round(float(gross or 0), 2)
        fee = round(g * commission_rate, 2) if commission_rate > 0 else 0.0
        net = round(g - fee, 2)
        excl = round(g / (1 + TAX_RATE), 2)
        tax = round(g - excl, 2)
        return {
            "gross_amount": g,
            "platform_fee": fee,
            "net_amount": net,
            "tax_rate": TAX_RATE,
            "tax_amount": tax,
            "amount_excl_tax": excl,
        }

    def issue(self, db: Session, hotel_id: int, order_id: int) -> None:
        return None

    def void(self, db: Session, hotel_id: int, invoice_id: int, reason: str) -> None:
        return None

    def workspace(self, db: Session, hotel_id: int) -> dict:
        return {"tax_documents_enabled": True, "tax_provider": self.name}


# 兼容旧名
FapiaoTaxProvider = FapiaoTax
