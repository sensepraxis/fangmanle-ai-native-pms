# SPDX-License-Identifier: Apache-2.0
"""支付风险分流：预付跟进（应预付未到账）vs 到店收款准备。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from models import Channel, Order
from orders.channel_config import source_group_for

OPEN_BOOKING = {"pending", "confirmed"}
UNSETTLED = {"unpaid", "partial"}


def near_arrival_unsettled(o: Order, today: date, *, days: int = 2) -> bool:
    """近 N 日入住、仍有效预订、且未结清。"""
    return (
        (o.status or "") in OPEN_BOOKING
        and (o.payment_status or "") in UNSETTLED
        and bool(o.check_in and today <= o.check_in <= today + timedelta(days=days))
    )


def expects_prepay(o: Order, channel: Optional[Channel] = None) -> bool:
    """
    是否「应先付」：
    - 有订金要求
    - 渠道已标预付 / OTA·团购口径
    - order_type=2（OTA）
    协议挂账不算催客人。
    """
    if (o.payment_status or "") == "on_account":
        return False
    if float(getattr(o, "deposit_amount", 0) or 0) > 0:
        return True
    if bool(getattr(o, "channel_prepaid", False)):
        return True
    if int(getattr(o, "order_type", 1) or 1) == 2:
        return True
    sg = source_group_for(channel, int(o.nights or 0)) if channel else "direct"
    return sg in ("ota", "voucher")


def classify_near_pay_action(
    o: Order,
    channel: Optional[Channel],
    today: date,
    *,
    days: int = 2,
) -> Optional[str]:
    """返回 remind_pay | prep_collect | None。"""
    if not near_arrival_unsettled(o, today, days=days):
        return None
    return "remind_pay" if expects_prepay(o, channel) else "prep_collect"
