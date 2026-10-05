# SPDX-License-Identifier: Apache-2.0
"""退房结算策略契约。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from models import Order


@dataclass
class PaymentSettleContext:
    """结算上下文（渠道收款方式、POS 单号等）。"""

    method: str = "wechat"
    pos_slip_no: Optional[str] = None
    operator_id: Optional[int] = None


@runtime_checkable
class PaymentSettleProvider(Protocol):
    """退房结算策略：corp / collect / prepaid。"""

    mode: str

    def settle(self, db: Session, order: Order, ctx: PaymentSettleContext) -> None:
        """就地更新订单支付态与账务；调用方负责 flush/commit。"""
        ...
