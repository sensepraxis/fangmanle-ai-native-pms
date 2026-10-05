# SPDX-License-Identifier: Apache-2.0
"""房间 · 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_rooms.py -v

用例清单
--------
Service 层：
  ROOM-S01  normalize 把历史/外部状态映射到标准状态
  ROOM-S02  transition：VC → VD 合法，写 RoomStatusLog
  ROOM-S03  transition 拒绝非法变迁（VC → OCC 直跳）
  ROOM-S04  transition 重复同状态 + force=False 无日志
  ROOM-S05  is_sellable 在可卖状态返回 True
  ROOM-S06  public_room_dict 含 status_label 中文

路由层（需后端 8081）：
  ROOM-H01  GET /rooms 返回房态列表
  ROOM-H02  GET /room-types 返回房型
  ROOM-H03  GET /inventory/calendar 返回日历结构
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from database import SessionLocal
from domain import BusinessError  # noqa: F401
from models import Room, RoomStatusLog

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8081"
_AUTH_TOKEN: str | None = None


def _ensure_auth_token() -> bool:
    global _AUTH_TOKEN
    if _AUTH_TOKEN:
        return True
    try:
        data = json.dumps({"username": "admin", "password": "admin123"}).encode()
        req = urllib.request.Request(
            API_BASE + "/api/v1/auth/login",
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


class RoomServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_s01_normalize(self):
        """ROOM-S01：normalize 各种写法 → 标准状态。"""
        from rooms.room_status import VC, VD, normalize

        self.assertEqual(normalize("VC"), VC)
        self.assertEqual(normalize("vacant"), VC)
        self.assertEqual(normalize("VD"), VD)
        self.assertEqual(normalize("dirty"), VD)
        self.assertEqual(normalize(None), VC)

    def test_s02_transition_vc_to_vd(self):
        """ROOM-S02：VC → VD 合法，写 RoomStatusLog。"""
        from rooms.room_status import VD, transition

        room = self.db.query(Room).filter_by(hotel_id=HOTEL_ID, status="VC").first()
        if not room:
            self.skipTest("无可用 VC 房")
        before_log = self.db.query(RoomStatusLog).filter_by(room_id=room.id).count()
        transition(self.db, room, VD, reason="自动化测试清洁完成")
        self.db.commit()
        after_log = self.db.query(RoomStatusLog).filter_by(room_id=room.id).count()
        self.assertGreater(after_log, before_log)
        # 改回来
        from rooms.room_status import VC

        transition(self.db, room, VC, reason="测试清理")
        self.db.commit()

    def test_s03_transition_rejects_illegal(self):
        """ROOM-S03：OCC → OOO 非法跳变被拒绝（在住不可直转 OOO，须先换房）。"""
        from fastapi import HTTPException

        from rooms.room_status import OOO, transition

        # 拿一间 OCC 房（如果没有，临时把一间改为 OCC 测试后改回）
        room = self.db.query(Room).filter_by(hotel_id=HOTEL_ID, status="OCC").first()
        if not room:
            # 用一间 VC 房临时改为 OCC（合法跳变），测完改回
            room = self.db.query(Room).filter_by(hotel_id=HOTEL_ID, status="VC").first()
            if not room:
                self.skipTest("无可用房间")
            from rooms.room_status import OCC

            transition(self.db, room, OCC, reason="测试前置")
            self.db.commit()
            try:
                with self.assertRaises(BusinessError) as ctx:
                    transition(self.db, room, OOO, reason="非法跳变")
                self.assertEqual(ctx.exception.http_status, 400)
            finally:
                # 清理：OCC → VD
                from rooms.room_status import VD

                transition(self.db, room, VD, reason="测试清理")
                self.db.commit()
        else:
            with self.assertRaises(BusinessError) as ctx:
                transition(self.db, room, OOO, reason="非法跳变")
            self.assertEqual(ctx.exception.http_status, 400)

    def test_s04_transition_noop(self):
        """ROOM-S04：重复同状态 + force=False → 不写 RoomStatusLog。"""
        from rooms.room_status import VC, transition

        room = self.db.query(Room).filter_by(hotel_id=HOTEL_ID, status="VC").first()
        if not room:
            self.skipTest("无可用 VC 房")
        before_log = self.db.query(RoomStatusLog).filter_by(room_id=room.id).count()
        # VC → VC 同状态，force=False
        transition(self.db, room, VC)
        self.db.commit()
        after_log = self.db.query(RoomStatusLog).filter_by(room_id=room.id).count()
        self.assertEqual(after_log, before_log, "同状态 noop 不应写新日志")

    def test_s05_is_sellable(self):
        """ROOM-S05：is_sellable 在可卖状态返回 True。"""
        from rooms.room_status import is_sellable

        self.assertTrue(is_sellable("VC"))
        self.assertTrue(is_sellable("clean"))
        self.assertTrue(is_sellable("inspected"))
        self.assertFalse(is_sellable("VD"))
        self.assertFalse(is_sellable("OOO"))

    def test_s06_public_room_dict_label(self):
        """ROOM-S06：public_room_dict 含 status_label 中文。"""
        from rooms.room_status import public_room_dict

        room = self.db.query(Room).filter_by(hotel_id=HOTEL_ID).first()
        if not room:
            self.skipTest("无可用房间")
        d = public_room_dict(room)
        self.assertIn("status_label", d)
        self.assertTrue(len(d["status_label"]) > 0)


class RoomHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_rooms(self):
        """ROOM-H01：/rooms 返回房态列表。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/rooms?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertIsInstance(data, (list, dict))

    def test_h02_room_types(self):
        """ROOM-H02：/room-types 返回房型列表。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/room-types?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)

    def test_h03_inventory_calendar(self):
        """ROOM-H03：/inventory/calendar 返回日历结构。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/inventory/calendar?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(RoomServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(RoomHttpTests))
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
