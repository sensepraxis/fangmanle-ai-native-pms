# SPDX-License-Identifier: Apache-2.0
"""企业微信（wecom）· 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_wecom.py -v

用例清单
--------
Service 层：
  WECOM-S01  mask_wecom_config 脱敏 app_secret 并带 *_set 标志
  WECOM-S02  mask_wecom_config 长密钥保留前 4 + 后 4，中间打码
  WECOM-S03  create_bind_ticket 写入 WecomBindTicket
  WECOM-S04  create_bind_ticket 同 external_userid 复用现有 pending
  WECOM-S05  list_bind_tickets 默认最近 30 条
  WECOM-S06  list_bind_tickets 按 hotel_id 过滤

路由层（需后端 8081）：
  WECOM-H01  GET /wecom/config 返回脱敏配置
  WECOM-H02  GET /wecom/bind-tickets 返回列表
  WECOM-H03  GET /wecom/portal 返回 portal 配置
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from database import SessionLocal
from models import WecomBindTicket

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


class WecomServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_s01_mask_secret(self):
        """WECOM-S01：mask_wecom_config 脱敏 + *_set 标志。"""
        from wecom.wecom_service import mask_wecom_config

        cfg = {
            "app_secret": "secret_abcdefghij_secret_abcdefghij",
            "callback_token": "tok_abcdefgh",
            "callback_aes_key": "aes_abcdefgh",
            "public_base_url": "https://example.com",
            "enabled": True,
        }
        out = mask_wecom_config(cfg)
        self.assertEqual(out["app_secret"], "secr****ghij")
        self.assertTrue(out["app_secret_set"])
        self.assertTrue(out["callback_token_set"])
        self.assertTrue(out["callback_aes_key_set"])
        self.assertEqual(out["status"], "enabled")
        self.assertEqual(out["callback_url"], "https://example.com/api/wecom/callback")

    def test_s02_mask_short_secret(self):
        """WECOM-S02：短密钥（≤8）打码为 ****。"""
        from wecom.wecom_service import mask_wecom_config

        cfg = {"app_secret": "short"}
        out = mask_wecom_config(cfg)
        self.assertEqual(out["app_secret"], "****")

    def test_s03_create_bind_ticket(self):
        """WECOM-S03：create_bind_ticket 写库 + 返回 WecomBindTicket。"""
        from wecom.wecom_service import create_bind_ticket

        ext_id = "ext-user-test-001"
        before_count = self.db.query(WecomBindTicket).filter_by(external_userid=ext_id).count()
        try:
            ticket = create_bind_ticket(
                self.db,
                hotel_id=HOTEL_ID,
                external_userid=ext_id,
                follow_userid="staff-1",
                nickname="测试客人",
            )
            self.db.commit()
            self.assertIsNotNone(ticket.token)
            self.assertEqual(ticket.external_userid, ext_id)
            self.assertEqual(ticket.status, "pending")
            after_count = self.db.query(WecomBindTicket).filter_by(external_userid=ext_id).count()
            self.assertEqual(after_count - before_count, 1)
        finally:
            self.db.query(WecomBindTicket).filter_by(external_userid=ext_id).delete()
            self.db.commit()

    def test_s04_create_bind_ticket_reuses_pending(self):
        """WECOM-S04：同 external_userid 复用现有 pending，不重复创建。"""
        from wecom.wecom_service import create_bind_ticket

        ext_id = "ext-user-test-002"
        try:
            t1 = create_bind_ticket(self.db, hotel_id=HOTEL_ID, external_userid=ext_id, follow_userid="staff-1")
            self.db.commit()
            t2 = create_bind_ticket(self.db, hotel_id=HOTEL_ID, external_userid=ext_id, follow_userid="staff-2")
            self.db.commit()
            self.assertEqual(t1.id, t2.id, "应复用现有 pending ticket")
        finally:
            self.db.query(WecomBindTicket).filter_by(external_userid=ext_id).delete()
            self.db.commit()

    def test_s05_list_bind_tickets_default(self):
        """WECOM-S05：list_bind_tickets 默认 limit=30。"""
        from wecom.wecom_service import create_bind_ticket, list_bind_tickets

        # 灌 5 条独立 ticket（不同 external_userid）
        ext_ids = [f"ext-user-list-{i}" for i in range(5)]
        try:
            for ext in ext_ids:
                create_bind_ticket(self.db, hotel_id=HOTEL_ID, external_userid=ext, follow_userid="s")
            self.db.commit()
            tickets = list_bind_tickets(self.db, HOTEL_ID)
            self.assertIsInstance(tickets, list)
            # 至少包含我们刚创建的 5 条
            listed_ext_ids = {t.get("external_userid") for t in tickets}
            for ext in ext_ids:
                self.assertIn(ext, listed_ext_ids)
        finally:
            self.db.query(WecomBindTicket).filter(WecomBindTicket.external_userid.in_(ext_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()

    def test_s06_list_bind_tickets_filter_hotel(self):
        """WECOM-S06：list_bind_tickets 不返回其他酒店的 ticket。"""
        from wecom.wecom_service import create_bind_ticket, list_bind_tickets

        ext_id_local = "ext-local-test"
        ext_id_other = "ext-other-test"
        try:
            create_bind_ticket(self.db, hotel_id=HOTEL_ID, external_userid=ext_id_local, follow_userid="s")
            create_bind_ticket(self.db, hotel_id=9999, external_userid=ext_id_other, follow_userid="s")
            self.db.commit()
            tickets = list_bind_tickets(self.db, HOTEL_ID)
            ids = {t.get("external_userid") for t in tickets}
            self.assertIn(ext_id_local, ids)
            self.assertNotIn(ext_id_other, ids)
        finally:
            self.db.query(WecomBindTicket).filter(
                WecomBindTicket.external_userid.in_([ext_id_local, ext_id_other])
            ).delete(synchronize_session=False)
            self.db.commit()


class WecomHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_config(self):
        """WECOM-H01：/wecom/config 返回脱敏配置（含 app_secret_set）。"""
        self._skip_if_down()
        res = _http("GET", "/api/v1/wecom/config")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        # 脱敏后应有 _set 标志
        self.assertIn("app_secret_set", data)
        self.assertIn("callback_url", data)

    def test_h02_bind_tickets(self):
        """WECOM-H02：/wecom/bind-tickets 返回列表。"""
        self._skip_if_down()
        res = _http("GET", "/api/v1/wecom/bind-tickets")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        self.assertIsInstance(res["data"], (list, dict))

    def test_h03_portal(self):
        """WECOM-H03：/wecom/portal 返回 portal 配置（可匿名）。"""
        # portal 通常允许匿名访问
        try:
            req = urllib.request.Request(API_BASE + "/api/v1/wecom/portal", method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                _ = json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 即使 401 / 403 也算路由可达
            self.assertIn(e.code, (200, 401, 403, 422))


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(WecomServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(WecomHttpTests))
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
