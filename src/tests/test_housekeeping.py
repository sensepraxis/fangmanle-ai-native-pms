# SPDX-License-Identifier: Apache-2.0
"""房务中心 · 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_housekeeping.py -v

用例清单
--------
Service 层：
  HK-S01  create_housekeeping_task 写入 task_type/room_id
  HK-S02  start_task：open → in_progress
  HK-S03  start_task 拒绝终态（done）任务
  HK-S04  finish_clean：in_progress → pending_inspect
  HK-S05  inspect_task 通过 → done；失败 → rework
  HK-S06  create_guest_request 写 service_requests 表

路由层（需后端 8081）：
  HK-H01  GET /housekeeping 返回 task[]
  HK-H02  GET /housekeeping/board 返回看板结构
  HK-H03  GET /service-requests 返回 request[]
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from database import SessionLocal
from domain import BusinessError  # noqa: F401
from models import HousekeepingTask, Room, RoomType, ServiceRequest

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


class HkServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _make_room(self) -> Room:
        rt = self.db.query(RoomType).filter_by(hotel_id=HOTEL_ID).first()
        # 选一间 VD/VC 房
        room = (
            self.db.query(Room)
            .filter_by(hotel_id=HOTEL_ID, room_type_id=rt.id)
            .filter(Room.status.in_(["VD", "VC", "vacant", "clean", "dirty"]))
            .first()
        )
        self.assertIsNotNone(room)
        return room

    def test_s01_create_task(self):
        """HK-S01：create_housekeeping_task 写入 task_type / room_id。"""
        from hk.housekeeping_service import create_housekeeping_task

        room = self._make_room()
        t, _ = create_housekeeping_task(
            self.db,
            hotel_id=HOTEL_ID,
            room_id=room.id,
            task_type="clean",
            priority=3,
        )
        self.db.commit()
        self.assertEqual(t.task_type, "clean")
        self.assertEqual(t.room_id, room.id)
        # 状态：找到 attendant 自动 assigned，否则 open
        self.assertIn(t.status, ("open", "assigned"))

        # 清掉
        self.db.delete(t)
        self.db.commit()

    def test_s02_start_task(self):
        """HK-S02：start_task：open → in_progress。"""
        from hk.housekeeping_service import create_housekeeping_task, start_task

        room = self._make_room()
        t, _ = create_housekeeping_task(self.db, hotel_id=HOTEL_ID, room_id=room.id, task_type="clean")
        self.db.commit()
        started = start_task(self.db, t.id, operator_id=1)
        self.db.commit()
        self.assertEqual(started.status, "in_progress")
        self.assertIsNotNone(started.assignee_id)

        # 清理
        self.db.delete(self.db.get(HousekeepingTask, t.id))
        self.db.commit()

    def test_s03_start_task_rejects_done(self):
        """HK-S03：start_task 拒绝终态（done）任务。"""
        from fastapi import HTTPException

        from hk.housekeeping_service import create_housekeeping_task, finish_clean, inspect_task, start_task

        room = self._make_room()
        t, _ = create_housekeeping_task(self.db, hotel_id=HOTEL_ID, room_id=room.id, task_type="clean")
        self.db.commit()
        # 走完整流程到 done
        start_task(self.db, t.id, operator_id=1)
        finish_clean(self.db, t.id)
        inspect_task(self.db, t.id, passed=True, inspector_id=1)
        self.db.commit()
        # 再 start 应当失败
        with self.assertRaises(BusinessError) as ctx:
            start_task(self.db, t.id, operator_id=1)
        self.assertEqual(ctx.exception.http_status, 400)

        # 清理
        self.db.delete(self.db.get(HousekeepingTask, t.id))
        self.db.commit()

    def test_s04_finish_clean(self):
        """HK-S04：finish_clean：in_progress → pending_inspect。"""
        from hk.housekeeping_service import create_housekeeping_task, finish_clean, start_task

        room = self._make_room()
        t, _ = create_housekeeping_task(self.db, hotel_id=HOTEL_ID, room_id=room.id, task_type="clean")
        self.db.commit()
        start_task(self.db, t.id, operator_id=1)
        finished = finish_clean(self.db, t.id)
        self.db.commit()
        self.assertEqual(finished.status, "pending_inspect")

        # 清理
        self.db.delete(self.db.get(HousekeepingTask, t.id))
        self.db.commit()

    def test_s05_inspect_task(self):
        """HK-S05：inspect_task 通过 → done；失败 → rework。"""
        from hk.housekeeping_service import create_housekeeping_task, finish_clean, inspect_task, start_task

        room = self._make_room()
        # 用不同 task_type 避免「同房同类型未完成单」幂等返回 existing。
        t1, _ = create_housekeeping_task(self.db, hotel_id=HOTEL_ID, room_id=room.id, task_type="clean")
        t2, _ = create_housekeeping_task(self.db, hotel_id=HOTEL_ID, room_id=room.id, task_type="inspect")
        self.db.commit()

        # t1 走通
        start_task(self.db, t1.id, operator_id=1)
        finish_clean(self.db, t1.id)
        r1 = inspect_task(self.db, t1.id, passed=True, inspector_id=1)
        self.db.commit()
        self.assertEqual(r1["task"].status, "done")
        self.assertTrue(r1.get("passed"))

        # t2 失败 → rework
        start_task(self.db, t2.id, operator_id=1)
        finish_clean(self.db, t2.id)
        r2 = inspect_task(self.db, t2.id, passed=False, inspector_id=1, fail_reason="镜子未擦")
        self.db.commit()
        self.assertEqual(r2["task"].status, "rework")
        self.assertEqual(r2.get("fail_reason"), "镜子未擦")
        self.assertFalse(r2.get("passed"))

        # 清理
        for tid in (t1.id, t2.id):
            self.db.delete(self.db.get(HousekeepingTask, tid))
        self.db.commit()

    def test_s06_create_guest_request(self):
        """HK-S06：create_guest_request 写 service_requests 表。"""
        from hk.housekeeping_service import create_guest_request

        room = self._make_room()
        before_count = self.db.query(ServiceRequest).filter_by(hotel_id=HOTEL_ID, content="自动化测试-客需").count()
        try:
            r = create_guest_request(
                self.db,
                hotel_id=HOTEL_ID,
                room_id=room.id,
                content="自动化测试-客需",
                priority=3,
            )
            self.db.commit()
            after_count = self.db.query(ServiceRequest).filter_by(hotel_id=HOTEL_ID, content="自动化测试-客需").count()
            self.assertEqual(after_count - before_count, 1)
            self.assertEqual(r.get("priority"), 3)
        finally:
            # 清理
            self.db.query(ServiceRequest).filter_by(hotel_id=HOTEL_ID, content="自动化测试-客需").delete()
            # 同时可能产生 HK 工单，一起清
            self.db.query(HousekeepingTask).filter(
                HousekeepingTask.hotel_id == HOTEL_ID,
                HousekeepingTask.task_type == "service",
                HousekeepingTask.room_id == room.id,
            ).delete()
            self.db.commit()


class HkHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_tasks(self):
        """HK-H01：/housekeeping 返回 task 列表。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/housekeeping?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertIsInstance(data, (list, dict))
        if isinstance(data, dict):
            self.assertIn("items", data)

    def test_h02_board(self):
        """HK-H02：/housekeeping/board 返回看板结构。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/housekeeping/board?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)

    def test_h03_service_requests(self):
        """HK-H03：/service-requests 返回列表。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/service-requests?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(HkServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(HkHttpTests))
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
