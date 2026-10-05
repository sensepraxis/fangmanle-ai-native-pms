# SPDX-License-Identifier: Apache-2.0
"""一次性灌入可关联真实订单的押金数据。"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8")

from database import SessionLocal
from finance.deposit_service import board
from models import Deposit, DepositLedgerEntry, Guest, Order, PmsCheckin, Room


def main() -> None:
    db = SessionLocal()
    hotel_id = 1
    try:
        olds = db.query(Deposit).filter(Deposit.hotel_id == hotel_id).all()
        ids = [d.deposit_id for d in olds]
        if ids:
            db.query(DepositLedgerEntry).filter(DepositLedgerEntry.deposit_id.in_(ids)).delete(
                synchronize_session=False
            )
            db.query(Deposit).filter(Deposit.deposit_id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            print(f"cleared {len(ids)} old deposits")

        rooms = db.query(Room).filter(Room.hotel_id == hotel_id).order_by(Room.room_no).all()
        room_nos = [r.room_no for r in rooms if r.room_no]
        print("rooms available:", room_nos[:12])

        seen_guests: set[int] = set()
        picked: list[tuple[Order, Guest]] = []

        # 优先：已在住订单（便于结账页直接看押金）
        checked_in = (
            db.query(Order)
            .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
            .order_by(Order.id.desc())
            .limit(80)
            .all()
        )
        others = (
            db.query(Order)
            .filter(Order.hotel_id == hotel_id, Order.status != "checked_in")
            .order_by(Order.id.desc())
            .limit(200)
            .all()
        )
        for o in list(checked_in) + list(others):
            if not o.guest_id or o.guest_id in seen_guests:
                continue
            g = db.get(Guest, o.guest_id)
            if not g or not g.name:
                continue
            seen_guests.add(o.guest_id)
            picked.append((o, g))
            if len(picked) >= 12:
                break
        print("picked guests:", [g.name for _, g in picked])
        print("picked statuses:", [o.status for o, _ in picked])

        now = datetime.now()
        day = now.strftime("%Y%m%d")
        scenarios = [
            dict(form="WECHAT_DEPOSIT", status="FROZEN", amount=100000, auth=True, expire_days=28, label="在押-微信"),
            dict(
                form="PREAUTH_CARD",
                status="EXPIRED",
                amount=150000,
                auth=True,
                expire_days=-3,
                label="预授权过期",
                room_force="1512",
            ),
            dict(
                form="WECHAT_DEPOSIT",
                status="PARTIAL_CAPTURE",
                amount=50000,
                captured=35000,
                auth=True,
                expire_days=20,
                label="扣减中-在押不足",
                room_force="0908",
            ),
            dict(
                form="WECHAT_DEPOSIT",
                status="DISPUTED",
                amount=120000,
                auth=True,
                expire_days=12,
                updated_hours=20,
                label="争议未结",
                room_force="1105",
            ),
            dict(form="CASH", status="FROZEN", amount=50000, receipt=None, label="现金无收据", room_force="0603"),
            dict(form="ALIPAY_DEPOSIT", status="FROZEN", amount=100000, auth=True, expire_days=25, label="在押-支付宝"),
            dict(
                form="WECHAT_DEPOSIT", status="RELEASED", amount=65400, auth=True, released_today=True, label="今日已退"
            ),
            dict(form="PREAUTH_CARD", status="FROZEN", amount=200000, auth=True, expire_days=2, label="预授权临期"),
            dict(form="AR", status="FROZEN", amount=0, label="挂账免押展示"),
            dict(form="CASH", status="FROZEN", amount=80000, receipt="RCPT-20260831-88", label="现金在押正常"),
        ]

        added = []
        for i, sc in enumerate(scenarios):
            if i >= len(picked):
                break
            o, g = picked[i]
            room = sc.get("room_force") or (room_nos[i % len(room_nos)] if room_nos else f"{1000 + i}")
            amount = int(sc["amount"])
            captured = int(sc.get("captured") or 0)
            remaining = max(0, amount - captured)
            if sc["status"] in ("RELEASED", "RELEASED_AFTER_CAPTURE", "CAPTURED"):
                remaining = 0
            dep_id = f"DPS-{day}-{i + 1:04d}"
            auth_code = f"AUTH-{day}-{i + 1:03d}" if sc.get("auth") else None
            auth_expire = (now + timedelta(days=int(sc.get("expire_days", 30)))) if sc.get("auth") else None
            receipt = sc.get("receipt") if sc["form"] == "CASH" else None

            d = Deposit(
                deposit_id=dep_id,
                hotel_id=hotel_id,
                order_id=o.id,
                customer_id=g.one_id,
                guest_id=g.id,
                room_no=str(room)[:8],
                form=sc["form"],
                original_amount=amount,
                captured_amount=captured,
                remaining_refund=remaining,
                status=sc["status"],
                auth_code=auth_code,
                auth_expire_at=auth_expire,
                receipt_no=receipt,
                operator_id="demo",
                idempotency_key=f"demo-rich-{hotel_id}-{dep_id}",
                guest_name=g.name,
                order_no=o.order_no,
                released_at=now if sc.get("released_today") else None,
                updated_at=now - timedelta(hours=int(sc.get("updated_hours") or 1)),
                created_at=now - timedelta(days=1, hours=i),
            )
            db.add(d)
            db.flush()
            db.add(
                DepositLedgerEntry(
                    deposit_id=dep_id,
                    event="COLLECT",
                    from_status="CREATED",
                    to_status="FROZEN",
                    amount_delta=amount,
                    operator_id="demo",
                    memo="收押",
                    channel_ref=auth_code,
                )
            )
            if captured:
                db.add(
                    DepositLedgerEntry(
                        deposit_id=dep_id,
                        event="CAPTURE",
                        from_status="FROZEN",
                        to_status="PARTIAL_CAPTURE",
                        amount_delta=-captured,
                        operator_id="demo",
                        memo="迷你吧扣减",
                    )
                )
            if sc["status"] == "EXPIRED":
                db.add(
                    DepositLedgerEntry(
                        deposit_id=dep_id,
                        event="EXPIRE",
                        from_status="FROZEN",
                        to_status="EXPIRED",
                        amount_delta=0,
                        operator_id="system",
                        memo="预授权过期",
                    )
                )
            if sc["status"] == "DISPUTED":
                db.add(
                    DepositLedgerEntry(
                        deposit_id=dep_id,
                        event="DISPUTE",
                        from_status="FROZEN",
                        to_status="DISPUTED",
                        amount_delta=0,
                        operator_id="demo",
                        memo="金额不符争议",
                    )
                )
            if sc.get("released_today"):
                db.add(
                    DepositLedgerEntry(
                        deposit_id=dep_id,
                        event="RELEASE",
                        from_status="FROZEN",
                        to_status="RELEASED",
                        amount_delta=-amount,
                        operator_id="demo",
                        memo="今日退还",
                    )
                )

            if amount > 0:
                o.deposit_amount = Decimal(str(amount / 100.0))

            ck = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
            if ck:
                ck.room_no = str(room)
                ck.guest_name = g.name
                if ck.status != "inhouse" and sc["status"] not in ("RELEASED", "CAPTURED", "RELEASED_AFTER_CAPTURE"):
                    ck.status = "inhouse"
            else:
                db.add(
                    PmsCheckin(
                        hotel_id=hotel_id,
                        order_id=o.id,
                        guest_id=g.id,
                        guest_name=g.name,
                        status="inhouse",
                        room_no=str(room),
                        actual_checkin_at=now - timedelta(days=1),
                    )
                )
            # 在押场景：确保订单为在住，便于结账页
            if sc["status"] in ("FROZEN", "PARTIAL_CAPTURE", "EXPIRED", "DISPUTED"):
                if o.status != "checked_in":
                    o.status = "checked_in"

            added.append(
                {
                    "deposit_id": dep_id,
                    "label": sc["label"],
                    "guest": g.name,
                    "room": room,
                    "order_id": o.id,
                    "order_no": o.order_no,
                    "order_status": o.status,
                    "status": sc["status"],
                    "amount_yuan": amount / 100,
                }
            )

        db.commit()
        print("=== deposits ready (all linked to real orders) ===")
        for a in added:
            print(
                f"{a['deposit_id']} | {a['label']} | {a['guest']} | room {a['room']} | "
                f"order #{a['order_id']} {a['order_no']} ({a['order_status']}) | {a['status']} | Y{a['amount_yuan']:.0f}"
            )
        print("=== checkout demo links (checked_in + held) ===")
        for a in added:
            if a["order_status"] == "checked_in" and a["status"] in (
                "FROZEN",
                "PARTIAL_CAPTURE",
                "EXPIRED",
                "DISPUTED",
            ):
                print(f"  #/c5-frontdesk/cashiering-checkout?orderId={a['order_id']}  ← {a['guest']} {a['label']}")

        b = board(db, hotel_id)
        print("summary:", b["summary"])
        print("anomalies:")
        for x in b["anomalies"]:
            print(f"  - {x['title']}: {x['detail']} -> {x['deposit_id']}")

        # verify FK
        ok_n = 0
        for a in added:
            o = db.get(Order, a["order_id"])
            d = db.get(Deposit, a["deposit_id"])
            assert o and d and d.order_id == o.id and d.order_no == o.order_no
            ok_n += 1
        print(f"link check OK: {ok_n}/{len(added)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
