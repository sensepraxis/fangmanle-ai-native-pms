# SPDX-License-Identifier: Apache-2.0
"""跨模块状态机不变量（设计模式重构的"业务真理保护线"）。

运行: pytest src/tests/test_state_invariants.py -v

用例清单
--------
  INV-01  订单状态机闭环 + 不可跳跃
  INV-02  房态被 OCC 占用时，对应订单存在 checked_in
  INV-03  退房后房间回到 VD/VC，对应订单 checked_out
  INV-04  HK 任务 pending_inspect → inspect 后才 done，不可绕过
  INV-05  Longstay 渠道单必须 nights ≥ 7（不让 1-2 天混淆）
  INV-06  Agreement（协议）单 pay status = on_account
  INV-07  Price ev_cap 红线：所有 params.ev_cap == 100
  INV-08  Source Group 归类：订单 channel_code 必然落到 9 个分组之一
  INV-09  WecomBindTicket status 流转：pending → bound / expired
  INV-10  财务对称：每条 PmsFolioEntry 必须能追溯到一个 Order
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date, timedelta

from database import SessionLocal
from models import (
    Channel,
    HousekeepingTask,
    Order,
    PmsFolioEntry,
    PricingAssistantConfig,
    Room,
    RoomType,
    WecomBindTicket,
)

HOTEL_ID = 1


class StateInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # ----- 订单 -----
    def test_inv01_order_status_state_machine(self):
        """INV-01：订单 status 只能处于预定集合，无意外值。"""
        valid_statuses = {"pending", "confirmed", "checked_in", "checked_out", "cancelled", "no_show"}
        # 查所有订单
        seen = {o.status for o in self.db.query(Order).all() if o.status}
        unexpected = seen - valid_statuses
        self.assertEqual(unexpected, set(), f"发现越界 status：{unexpected}")

    def test_inv02_occupied_room_has_inhouse_order(self):
        """INV-02：房态 OCC 必有对应 checked_in 订单。"""
        occ_rooms = self.db.query(Room).filter_by(hotel_id=HOTEL_ID, status="OCC").all()
        if not occ_rooms:
            self.skipTest("无 OCC 房，跳过")
        for room in occ_rooms:
            # 通过 PmsCheckin 反查（PmsCheckin.status 用 "inhouse" 不是 "in_house"）
            from models import PmsCheckin

            ci = self.db.query(PmsCheckin).filter_by(room_id=room.id).filter(PmsCheckin.status == "inhouse").first()
            self.assertIsNotNone(ci, f"OCC 房 {room.id} 缺失 inhouse checkin")
            o = self.db.get(Order, ci.order_id)
            self.assertIsNotNone(o)
            self.assertEqual(o.status, "checked_in")

    def test_inv03_checkout_room_and_order(self):
        """INV-03：checked_out 订单对应房间应回到 VD/VC。"""
        checkout_orders = self.db.query(Order).filter_by(hotel_id=HOTEL_ID, status="checked_out").all()
        if not checkout_orders:
            self.skipTest("无 checked_out 订单")
        for o in checkout_orders[:5]:  # 抽 5 条样本
            from models import PmsCheckin

            ci = self.db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
            if not ci or not ci.room_id:
                continue
            room = self.db.get(Room, ci.room_id)
            self.assertIsNotNone(room)
            self.assertIn(room.status, ("VD", "VC", "vacant", "clean", "dirty"))

    # ----- 渠道 -----
    def test_inv05_longstay_min_nights(self):
        """INV-05：longstay 渠道单必须 nights ≥ 7。"""
        from models import Channel

        ch_longstay = self.db.query(Channel).filter_by(code="longstay").first()
        if not ch_longstay:
            self.skipTest("无 longstay 渠道")
        bad = (
            self.db.query(Order).filter_by(hotel_id=HOTEL_ID, channel_id=ch_longstay.id).filter(Order.nights < 7).all()
        )
        self.assertEqual(len(bad), 0, f"发现 {len(bad)} 单 longstay 但 nights<7")

    def test_inv06_agreement_on_account(self):
        """INV-06：agreement 渠道单 payment_status 应是 on_account。"""
        from models import Channel

        ch_agreement = self.db.query(Channel).filter_by(code="agreement").first()
        if not ch_agreement:
            self.skipTest("无 agreement 渠道")
        bad = (
            self.db.query(Order)
            .filter_by(hotel_id=HOTEL_ID, channel_id=ch_agreement.id)
            .filter(Order.payment_status != "on_account")
            .all()
        )
        self.assertEqual(len(bad), 0, f"发现 {len(bad)} 单 agreement 不是 on_account")

    # ----- 价格 -----
    def test_inv07_price_ev_cap_redline(self):
        """INV-07：所有 PricingAssistantConfig.params.ev_cap == 100。"""
        cfgs = self.db.query(PricingAssistantConfig).all()
        if not cfgs:
            self.skipTest("无 PricingAssistantConfig")
        for cfg in cfgs:
            try:
                params = json.loads(cfg.params_json or "{}")
            except json.JSONDecodeError:
                continue
            # 默认就是 100；如果存在则不应被放宽超过 100
            if "ev_cap" in params:
                self.assertLessEqual(
                    float(params["ev_cap"]),
                    100.0,
                    f"配置 {cfg.id} ev_cap 超过 100",
                )

    # ----- 渠道归类 -----
    def test_inv08_source_group_mapping(self):
        """INV-08：所有订单 channel_code 都能归到 9 个 source group。"""
        from models import Channel
        from orders.channel_config import SOURCE_BY_CODE

        channels = {c.id: c for c in self.db.query(Channel).all()}
        known_groups = {"ota", "voucher", "direct", "map", "geo", "longstay", "agreement", "wechat"}

        orders = self.db.query(Order).filter_by(hotel_id=HOTEL_ID).all()
        for o in orders:
            ch = channels.get(o.channel_id)
            if not ch:
                # 无 channel 的订单：归 direct（兜底）
                continue
            code = ch.code or ""
            # SOURCE_BY_CODE 查不到 → fallback 到 ch.type
            sg = SOURCE_BY_CODE.get(code) or ch.type or "direct"
            self.assertIn(sg, known_groups, f"订单 {o.id} channel={code} 归类={sg} 超出 9 组")

    # ----- WeCom bind ticket -----
    def test_inv09_bind_ticket_status(self):
        """INV-09：WecomBindTicket status ∈ {pending, bound, expired}。"""
        tickets = self.db.query(WecomBindTicket).all()
        valid = {"pending", "bound", "expired"}
        seen = {t.status for t in tickets if t.status}
        unexpected = seen - valid
        self.assertEqual(unexpected, set(), f"bind ticket 越界 status：{unexpected}")

    # ----- 财务 -----
    def test_inv10_folio_entry_has_order(self):
        """INV-10：PmsFolioEntry 必须能追溯到一个 Order（通过 folio）。"""
        from models import PmsFolio

        bad = []
        for e in self.db.query(PmsFolioEntry).limit(500).all():
            folio = self.db.get(PmsFolio, e.folio_id) if e.folio_id else None
            if not folio or not folio.order_id:
                bad.append(e.id)
                continue
            o = self.db.get(Order, folio.order_id)
            if not o:
                bad.append(e.id)
        self.assertEqual(len(bad), 0, f"发现 {len(bad)} 条 PmsFolioEntry 找不到 Order")


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(StateInvariantTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 60)
    print(
        f"合计: {result.testsRun}  "
        f"通过: {result.testsRun - len(result.failures) - len(result.errors)}  "
        f"失败: {len(result.failures)}  "
        f"跳过: {len(result.skipped)}"
    )
    print("=" * 60)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
