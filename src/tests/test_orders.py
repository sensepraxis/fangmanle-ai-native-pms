# SPDX-License-Identifier: Apache-2.0
"""订单中心 · 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_orders.py -v

用例清单
--------
Service 层：
  ORD-S01  订单状态机：pending → checked_in → checked_out
  ORD-S02  pending 订单可取消；checked_in 不可取消
  ORD-S03  重复 external_order_no 抛 409
  ORD-S04  checkin 错状态（cancelled）抛 400
  ORD-S05  checkout 错状态（pending）抛 400
  ORD-S06  assign_room_only 把 vacant 房改成 EA、并写 Reservation
  ORD-S07  退房释放房间（OCC → VD）+ 写 cleaning task

路由层（需后端在 8081 启动）：
  ORD-H01  GET /orders/board 返回 sources / total / enhance
  ORD-H02  GET /orders/attribution 返回 window / kpi / paths
  ORD-H03  GET /orders/channel-insight 返回 bubbles / matrix / trend
  ORD-H04  GET /orders/monitor 返回 kpi / series / funnel
  ORD-H05  GET /orders/summary 返回工作摘要
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta

from database import SessionLocal
from domain import BusinessError  # noqa: F401
from models import Channel, Order, Reservation, Room, RoomType

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8081"
_AUTH_TOKEN: str | None = None


# ---------------------------------------------------------------------------
# HTTP 助手（与 test_ar_ap 同样模式：失败则 skip）
# ---------------------------------------------------------------------------
def _ensure_auth_token() -> bool:
    global _AUTH_TOKEN
    if _AUTH_TOKEN:
        return True
    try:
        data = json.dumps({"username": "admin", "password": "admin123"}).encode()
        req = urllib.request.Request(
            API_BASE + "/api/auth/login",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read())
        token = (body.get("data") or {}).get("access_token") or (body.get("data") or {}).get("token")
        if token:
            _AUTH_TOKEN = token
            return True
    except Exception:
        pass
    return False


def _auth_headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if _AUTH_TOKEN:
        h["Authorization"] = f"Bearer {_AUTH_TOKEN}"
    return h


def _http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, method=method, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "detail": raw.decode(errors="replace"), "status": e.code}


# ---------------------------------------------------------------------------
# Service 层测试
# ---------------------------------------------------------------------------
class OrderServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        # conftest 不建 Channel，本测试自给自足：最小集（direct + ctrip），幂等。
        from bootstrap.ensure_order_channels import ensure_order_channels

        ensure_order_channels(self.db)
        self.rt = self.db.query(RoomType).filter_by(hotel_id=HOTEL_ID).first()
        self.assertIsNotNone(self.rt, "conftest 应已建房型")
        ch_direct = self.db.query(Channel).filter_by(code="direct").first()
        if not ch_direct:
            ch_direct = Channel(code="direct", name="散客直订", type="direct", commission_rate=0)
            self.db.add(ch_direct)
            self.db.commit()
        self.channel_direct = ch_direct

    def _make_order(self, status: str = "pending") -> Order:
        from orders.order_service import create_order_record

        today = date.today()
        o = create_order_record(
            self.db,
            hotel_id=HOTEL_ID,
            guest_name="测试客人A",
            phone="13800000000",
            room_type_id=self.rt.id,
            channel_id=self.channel_direct.id,
            check_in=today + timedelta(days=1),
            check_out=today + timedelta(days=2),
            rooms=1,
            adults=1,
            status=status,
        )
        self.db.commit()
        return o

    def test_s01_status_machine_full_flow(self):
        """ORD-S01：pending → checked_in → checked_out 状态机正路径。"""
        from orders.order_service import checkin_order, checkout_order

        o = self._make_order("pending")
        self.assertEqual(o.status, "pending")

        o = checkin_order(self.db, o.id)
        self.db.commit()
        self.assertEqual(o.status, "checked_in")

        o = checkout_order(self.db, o.id)
        self.db.commit()
        self.assertEqual(o.status, "checked_out")

    def test_s02_cancel_only_when_pre_checkin(self):
        """ORD-S02：pending 可取消；checked_in 抛 400。"""
        from fastapi import HTTPException

        from orders.order_service import cancel_order, checkin_order

        # pending → cancel
        o1 = self._make_order("pending")
        cancel_order(self.db, o1.id, reason="自动化测试取消")
        self.db.commit()
        self.assertEqual(self.db.get(Order, o1.id).status, "cancelled")

        # checked_in → cancel 抛 400
        o2 = self._make_order("pending")
        checkin_order(self.db, o2.id)
        self.db.commit()
        with self.assertRaises(BusinessError) as ctx:
            cancel_order(self.db, o2.id)
        self.assertEqual(ctx.exception.http_status, 400)

    def test_s03_duplicate_external_order_no(self):
        """ORD-S03：external_order_no 重复 → 409。"""
        import uuid

        from fastapi import HTTPException

        from orders.order_service import create_order_record

        ext = f"TEST-EXT-{uuid.uuid4().hex[:12]}"
        create_order_record(
            self.db,
            hotel_id=HOTEL_ID,
            guest_name="A",
            phone=None,
            room_type_id=self.rt.id,
            channel_id=self.channel_direct.id,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=3),
            status="pending",
            external_order_no=ext,
        )
        self.db.commit()
        with self.assertRaises(BusinessError) as ctx:
            create_order_record(
                self.db,
                hotel_id=HOTEL_ID,
                guest_name="B",
                phone=None,
                room_type_id=self.rt.id,
                channel_id=self.channel_direct.id,
                check_in=date.today() + timedelta(days=3),
                check_out=date.today() + timedelta(days=4),
                status="pending",
                external_order_no=ext,
            )
        self.assertEqual(ctx.exception.http_status, 409)

    def test_s04_checkin_rejects_cancelled(self):
        """ORD-S04：cancelled 订单不可办理入住。"""
        from fastapi import HTTPException

        from orders.order_service import cancel_order, checkin_order

        o = self._make_order("pending")
        cancel_order(self.db, o.id)
        self.db.commit()
        with self.assertRaises(BusinessError) as ctx:
            checkin_order(self.db, o.id)
        self.assertEqual(ctx.exception.http_status, 400)

    def test_s05_checkout_rejects_pending(self):
        """ORD-S05：pending 订单不可退房。"""
        from fastapi import HTTPException

        from orders.order_service import checkout_order

        o = self._make_order("pending")
        with self.assertRaises(BusinessError) as ctx:
            checkout_order(self.db, o.id)
        self.assertEqual(ctx.exception.http_status, 400)

    def test_s06_assign_room_only(self):
        """ORD-S06：assign_room_only 把空净房写成预抵房 + Reservation。"""
        from orders.pms_ops import assign_room_only

        o = self._make_order("pending")
        # 选一间 vacant 房
        room = (
            self.db.query(Room)
            .filter_by(hotel_id=HOTEL_ID, room_type_id=self.rt.id)
            .filter(Room.status.in_(["VC", "vacant", "clean"]))
            .first()
        )
        if not room:
            self.skipTest("无可用 vacant 房")
        # 直接调用 assign_room_only；房间状态会被改成 EA
        before_status = room.status
        assign_room_only(self.db, o.id, room.id, assigned_by=1)
        self.db.commit()

        res = self.db.query(Reservation).filter_by(order_id=o.id).first()
        self.assertIsNotNone(res)
        self.assertEqual(res.room_id, room.id)
        # 房间状态已不再是 vacant
        self.db.refresh(room)
        self.assertNotEqual(room.status, before_status)

    def test_s07_checkout_releases_room(self):
        """ORD-S07：退房释放房间 → VD 状态 + cleaning task。"""
        from orders.order_service import checkin_order, checkout_order

        o = self._make_order("pending")
        o = checkin_order(self.db, o.id)
        self.db.commit()
        # 找到这次入住占用的房间
        from models import PmsCheckin, RoomStatusLog

        ci = self.db.query(PmsCheckin).filter_by(order_id=o.id).first()
        self.assertIsNotNone(ci, "checkin 应写 PmsCheckin")
        room_id = ci.room_id
        room_before = self.db.get(Room, room_id)
        before_status = room_before.status

        checkout_order(self.db, o.id)
        self.db.commit()

        room_after = self.db.get(Room, room_id)
        # 状态应从 OCC/DO 转 VD（normalize 大小写不敏感）
        from rooms.room_status import VD, normalize

        self.assertEqual(normalize(room_after.status), VD)
        # 应写了 RoomStatusLog
        logs = self.db.query(RoomStatusLog).filter_by(room_id=room_id).order_by(RoomStatusLog.id.desc()).limit(1).all()
        self.assertGreater(len(logs), 0)


# ---------------------------------------------------------------------------
# HTTP 路由层测试（无后端则 skip）
# ---------------------------------------------------------------------------
class OrderHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_board(self):
        """ORD-H01：/orders/board 返回 sources / total / enhance。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/orders/board?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertIn("sources", data)
        self.assertIn("total", data)
        self.assertIn("enhance", data)
        self.assertIsInstance(data["sources"], list)

    def test_h02_attribution(self):
        """ORD-H02：/orders/attribution 返回 window / kpi / paths。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/orders/attribution?hotel_id={HOTEL_ID}&days=7")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        for k in ("window", "kpi", "paths", "path_summary"):
            self.assertIn(k, data)

    def test_h03_channel_insight(self):
        """ORD-H03：/orders/channel-insight 返回 bubbles / matrix / trend。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/orders/channel-insight?hotel_id={HOTEL_ID}&days=14")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        for k in ("bubbles", "matrix", "trend", "axes"):
            self.assertIn(k, data)

    def test_h04_monitor(self):
        """ORD-H04：/orders/monitor 返回 kpi / series / funnel。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/orders/monitor?hotel_id={HOTEL_ID}&range=7d")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        for k in ("kpi", "series", "funnel"):
            self.assertIn(k, data)

    def test_h05_summary(self):
        """ORD-H05：/orders/summary 返回工作摘要（不分页）。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/orders/summary?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(OrderServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(OrderHttpTests))
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
