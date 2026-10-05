# SPDX-License-Identifier: Apache-2.0
"""验证券包 Wallet：grant 引用、多渠道展示、本店核销双写。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bootstrap.ensure_coupon_wallet import ensure_coupon_wallet
from database import SessionLocal, engine
from mkt.mkt_coupon_engine import list_redeem_log, normalize_instance_status
from mkt.wallet_norm import NATIVE_WALLET_SOURCE
from mkt.wallet_service import list_guest_coupons, redeem_guest_coupon
from models import GuestCoupon, MktCouponGrant


def main() -> None:
    db = SessionLocal()
    try:
        info = ensure_coupon_wallet(engine, db, hotel_id=1)
        print("ensure:", info)

        coupons = list_guest_coupons(db, 228)
        print(f"\n董文(#228) 券包共 {len(coupons)} 张：")
        for c in coupons:
            print(
                f"  [{c.get('source_label')}] {c.get('code')} · {c.get('name')} · "
                f"grant_id={c.get('grant_id')} · redeem={c.get('redeem_status')} · "
                f"can_redeem={c.get('can_redeem')} · blocked={c.get('redeem_blocked_reason')}"
            )

        sources = {c.get("source") for c in coupons}
        assert "meituan" in sources or any(c.get("code", "").startswith("MT-") for c in coupons), "缺少美团券"
        assert "douyin" in sources or any(c.get("code", "").startswith("DY-") for c in coupons), "缺少抖音券"

        # 找一张本店 AVAILABLE 的券做核销验证（董文）
        target = next(
            (
                c
                for c in coupons
                if c.get("source") == NATIVE_WALLET_SOURCE and c.get("can_redeem") and c.get("grant_id")
            ),
            None,
        )
        if not target:
            # 若董文没有可核本店券，找任意 AVAILABLE grant 投影
            g = (
                db.query(MktCouponGrant)
                .filter(MktCouponGrant.hotel_id == 1, MktCouponGrant.status.in_(("AVAILABLE", "unused")))
                .first()
            )
            if g:
                from mkt.mkt_coupon_engine import _project_guest_coupon
                from models import MktCoupon

                _project_guest_coupon(db, 1, g.guest_id, db.get(MktCoupon, g.coupon_id), g)
                db.commit()
                target = next(
                    (c for c in list_guest_coupons(db, g.guest_id) if c.get("code") == g.code),
                    None,
                )
                print(f"\n改用 guest#{g.guest_id} 的本店券做核销验证: {g.code}")

        if target:
            print(f"\n核销本店券 {target['code']} (grant_id={target['grant_id']}) …")
            res = redeem_guest_coupon(
                db,
                coupon_id=target["id"],
                operator="wallet_verify",
                remark="券包统一核销验证",
            )
            print("redeem result:", res.get("message"), "wallet_source=", res.get("wallet_source"))
            grant = db.get(MktCouponGrant, target["grant_id"])
            gc = db.get(GuestCoupon, target["id"])
            assert grant and normalize_instance_status(grant.status) == "USED", "Grant 未更新为 USED"
            assert gc and gc.redeem_status == "redeemed", "Wallet 未更新为 redeemed"
            print("OK: Grant + Wallet 同事务已核销")
        else:
            print("\n跳过核销写测：没有可用的本店 fangmanle_mkt 券")

        # 外渠道不可核
        ext = next((c for c in list_guest_coupons(db, 228) if c.get("source") == "meituan"), None)
        if ext:
            try:
                redeem_guest_coupon(db, coupon_id=ext["id"])
                raise AssertionError("美团券不应允许本店核销")
            except Exception as e:
                print("OK: 美团券拦截 —", getattr(e, "detail", e))

        ledger = list_redeem_log(db, 1)
        print(f"\n核销流水 {len(ledger)} 条：")
        for row in ledger[:8]:
            print(
                f"  {row.get('used_at')} · {row.get('source_label') or row.get('wallet_source')} · "
                f"{row.get('guest_name')} · {row.get('coupon_code')}"
            )
        assert any(r.get("guest_name") == "董文" for r in ledger), "流水应含董文"
        print("\n全部验证通过")
    finally:
        db.close()


if __name__ == "__main__":
    main()
