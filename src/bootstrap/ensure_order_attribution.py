# SPDX-License-Identifier: Apache-2.0
"""
订单渠道归因补种：为「微信/直销成交单」补上首触点辅助归因，贴近多触点原型。
在已有 demo.db 上可幂等执行，无需 --reset。
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import Campaign, Channel, ChannelAttribution, Hotel, Order
from orders.attribution_config import ASSIST_SOURCES, ASSIST_WEIGHTS


def ensure_order_attribution(db: Session) -> dict:
    """幂等：补 Campaign + 直销/私域单的辅助归因。"""
    hotels = db.query(Hotel).all()
    channels = {c.code: c for c in db.query(Channel).all()}
    wechat_id = channels.get("wechat").id if channels.get("wechat") else None
    direct_id = channels.get("direct").id if channels.get("direct") else None
    conv_ids = {x for x in (wechat_id, direct_id) if x}

    added_attr = 0
    added_camp = 0
    today = date.today()

    for h in hotels:
        # 确保有小红书/抖音活动，供 ROI / CAC
        existing = {(c.channel or ""): c for c in db.query(Campaign).filter_by(hotel_id=h.id).all()}
        for ch, name in (("xiaohongshu", "小红书种草笔记"), ("douyin", "抖音探店挑战赛")):
            if ch in existing:
                continue
            spend = round(random.uniform(5000, 18000), 2)
            rev = round(spend * random.uniform(2.2, 4.5), 2)
            db.add(
                Campaign(
                    hotel_id=h.id,
                    channel=ch,
                    name=name,
                    status="active",
                    spend=spend,
                    attributed_rev=rev,
                    roi=round(rev / spend, 2),
                    start_date=today - timedelta(days=30),
                    end_date=today + timedelta(days=7),
                )
            )
            added_camp += 1

        if not conv_ids:
            continue

        attributed_oids = {
            r[0]
            for r in db.query(ChannelAttribution.order_id)
            .filter_by(hotel_id=h.id)
            .filter(ChannelAttribution.order_id.isnot(None))
            .all()
        }

        candidates = (
            db.query(Order)
            .filter(
                Order.hotel_id == h.id,
                Order.channel_id.in_(list(conv_ids)),
                Order.status.in_(("pending", "checked_in", "checked_out")),
            )
            .order_by(Order.id.asc())
            .all()
        )
        for o in candidates:
            if o.id in attributed_oids:
                continue
            # 约 70% 补辅助触点，保留部分「直达」
            if (o.id or 0) % 10 < 3:
                continue
            src = random.choices(ASSIST_SOURCES, weights=ASSIST_WEIGHTS, k=1)[0]
            db.add(
                ChannelAttribution(
                    hotel_id=h.id,
                    order_id=o.id,
                    source=src,
                    attributed_rev=float(o.total_amount or 0),
                )
            )
            added_attr += 1

    if added_attr or added_camp:
        db.commit()
    return {"campaigns_added": added_camp, "attributions_added": added_attr}
