# SPDX-License-Identifier: Apache-2.0
"""删除指定客人及其企微扫码关联数据（/测试用）。"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import (
    Guest,
    GuestAlias,
    GuestCoupon,
    GuestIdentity,
    GuestTag,
    OneIdMergeEvent,
    OneIdPhoneConflict,
    Order,
    OrderItem,
    Review,
    SegmentMember,
    WecomBindTicket,
)


def purge_guest(db, guest_id: int) -> dict:
    g = db.get(Guest, guest_id)
    if not g:
        return {"ok": False, "error": "guest_not_found"}

    external_ids = [i.external_id for i in db.query(GuestIdentity).filter_by(guest_id=guest_id).all() if i.external_id]

    stats = {
        "guest_id": guest_id,
        "guest_name": g.name,
        "guest_aliases": db.query(GuestAlias).filter_by(guest_id=guest_id).delete()
        + db.query(GuestAlias).filter_by(merged_from_guest_id=guest_id).delete(),
        "guest_identities": db.query(GuestIdentity).filter_by(guest_id=guest_id).delete(),
        "guest_coupons": db.query(GuestCoupon).filter_by(guest_id=guest_id).delete(),
        "oneid_merge_events": db.query(OneIdMergeEvent).filter_by(guest_id=guest_id).delete(),
        "guest_tags": db.query(GuestTag).filter_by(guest_id=guest_id).delete(),
        "orders_unlinked": db.query(Order).filter_by(guest_id=guest_id).update({"guest_id": None}),
        "reviews_unlinked": db.query(Review).filter_by(guest_id=guest_id).update({"guest_id": None}),
        "segment_members": db.query(SegmentMember).filter_by(guest_id=guest_id).delete(),
    }

    ticket_q = db.query(WecomBindTicket).filter(
        (WecomBindTicket.guest_id == guest_id) | WecomBindTicket.external_userid.in_(external_ids or ["__none__"])
    )
    stats["wecom_bind_tickets"] = ticket_q.delete(synchronize_session=False)

    # 冲突候选/已解记录里去掉该客人
    for c in db.query(OneIdPhoneConflict).all():
        try:
            ids = json.loads(c.candidate_guest_ids_json or "[]")
        except json.JSONDecodeError:
            ids = []
        if guest_id in ids or c.resolved_guest_id == guest_id:
            if c.status == "pending" and guest_id in ids:
                new_ids = [x for x in ids if int(x) != guest_id]
                if len(new_ids) <= 1:
                    db.delete(c)
                    stats.setdefault("conflicts_removed", 0)
                    stats["conflicts_removed"] += 1
                else:
                    c.candidate_guest_ids_json = json.dumps(new_ids)
            elif c.resolved_guest_id == guest_id:
                c.resolved_guest_id = None

    db.delete(g)
    db.commit()
    stats["ok"] = True
    return stats


if __name__ == "__main__":
    gid = int(sys.argv[1]) if len(sys.argv) > 1 else 227
    db = SessionLocal()
    try:
        print(purge_guest(db, gid))
    finally:
        db.close()
