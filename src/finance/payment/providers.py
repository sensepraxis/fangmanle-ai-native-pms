# SPDX-License-Identifier: Apache-2.0
"""内置退房结算策略实现。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from finance.payment.protocol import PaymentSettleContext
from models import Invoice, LedgerEntry, Order
from orders.pms_domain import post_ar_charge, post_payment


class CorpSettleProvider:
    """协议挂账：on_account + AR。"""

    mode = "corp"

    def settle(self, db: Session, order: Order, ctx: PaymentSettleContext) -> None:
        order.payment_status = "on_account"
        post_ar_charge(db, order, operator_id=ctx.operator_id)


class CollectSettleProvider:
    """现收：写 Payment + 简易发票/凭证；已 paid 则跳过。"""

    mode = "collect"

    def settle(self, db: Session, order: Order, ctx: PaymentSettleContext) -> None:
        if order.payment_status in ("paid",):
            return
        post_payment(
            db,
            order,
            amount=float(order.total_amount or 0),
            method=ctx.method,
            pos_slip_no=ctx.pos_slip_no,
            settle_type="full",
            operator_id=ctx.operator_id,
        )
        from finance.tax.registry import get_tax_provider

        rate = float(get_tax_provider().tax_rate)
        db.add(
            Invoice(
                hotel_id=order.hotel_id,
                order_id=order.id,
                invoice_no=f"INV-{order.id:06d}",
                amount=order.total_amount,
                tax=round(float(order.total_amount or 0) * rate, 2),
                status="issued",
                issued_at=datetime.now(),
            )
        )
        db.add(
            LedgerEntry(
                hotel_id=order.hotel_id,
                biz_date=order.check_out,
                account="主营业务收入-房费",
                credit=order.total_amount,
                ref_type="order",
                ref_id=order.id,
            )
        )
        order.payment_status = "paid"


class PrepaidSettleProvider:
    """渠道/券预付：仅标记 paid（已 paid/on_account 跳过）。"""

    mode = "prepaid"

    def settle(self, db: Session, order: Order, ctx: PaymentSettleContext) -> None:
        if order.payment_status not in ("paid", "on_account"):
            order.payment_status = "paid"
