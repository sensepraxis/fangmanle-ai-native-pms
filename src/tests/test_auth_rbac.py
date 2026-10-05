# SPDX-License-Identifier: Apache-2.0
"""Auth + RBAC · 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_auth_rbac.py -v

用例清单
--------
Service 层：
  AUTH-S01  authenticate_user 正确密码 → AppContext 含 hotel_id/role
  AUTH-S02  authenticate_user 错误密码抛 401
  AUTH-S03  authenticate_user 不存在的用户抛 401
  AUTH-S04  authenticate_user is_active=False 抛 401
  AUTH-S05  issue_token + parse_token round-trip 一致
  AUTH-S06  parse_token 篡改签名抛 401
  AUTH-S07  hash_password 加盐后同密码也可校验；旧 SHA-256 hex 仍可 verify

路由层（需后端 8081）：
  AUTH-H01  POST /auth/login admin/admin123 → 200 + access_token
  AUTH-H02  POST /auth/login 错误密码 → 401
  AUTH-H03  GET /auth/me 带 token → 200 + user info
  AUTH-H04  GET /rbac/roles → 角色列表
  AUTH-H05  GET /rbac/permissions → 权限列表
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from database import SessionLocal
from domain import BusinessError  # noqa: F401

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


class AuthServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_s01_authenticate_ok(self):
        """AUTH-S01：correct password → AppContext。"""
        from infra.auth_local import authenticate_user

        ctx = authenticate_user(self.db, "admin", "admin123")
        self.assertEqual(ctx.username, "admin")
        self.assertEqual(ctx.hotel_id, HOTEL_ID)
        self.assertTrue(ctx.role)

    def test_s02_wrong_password(self):
        """AUTH-S02：错误密码抛 401。"""
        from fastapi import HTTPException

        from infra.auth_local import authenticate_user

        with self.assertRaises(BusinessError) as ctx:
            authenticate_user(self.db, "admin", "wrong_pw")
        self.assertEqual(ctx.exception.http_status, 401)

    def test_s03_unknown_user(self):
        """AUTH-S03：不存在的用户抛 401。"""
        from fastapi import HTTPException

        from infra.auth_local import authenticate_user

        with self.assertRaises(BusinessError) as ctx:
            authenticate_user(self.db, "no-such-user-xyz", "any")
        self.assertEqual(ctx.exception.http_status, 401)

    def test_s04_inactive_user(self):
        """AUTH-S04：is_active=False 抛 401。"""
        from fastapi import HTTPException

        from infra.auth_local import authenticate_user

        # 找一个 active 用户，临时改 is_active=False
        from models import User

        u = self.db.query(User).filter_by(username="admin").first()
        original = u.is_active
        try:
            u.is_active = False
            self.db.commit()
            with self.assertRaises(BusinessError) as ctx:
                authenticate_user(self.db, "admin", "admin123")
            self.assertEqual(ctx.exception.http_status, 401)
        finally:
            u.is_active = original
            self.db.commit()

    def test_s05_token_round_trip(self):
        """AUTH-S05：issue_token + parse_token round-trip。"""
        from infra.auth_local import issue_token, parse_token

        token = issue_token(user_id=1, hotel_id=HOTEL_ID, username="admin", role="admin")
        payload = parse_token(token)
        self.assertEqual(payload["user_id"], 1)
        self.assertEqual(payload["hotel_id"], HOTEL_ID)
        self.assertEqual(payload["username"], "admin")

    def test_s06_token_tamper(self):
        """AUTH-S06：篡改签名 → 401。"""
        from fastapi import HTTPException

        from infra.auth_local import issue_token, parse_token

        token = issue_token(user_id=1, hotel_id=HOTEL_ID, username="admin", role="admin")
        # 把最后 4 个字符改掉
        tampered = token[:-4] + "ZZZZ"
        with self.assertRaises(BusinessError) as ctx:
            parse_token(tampered)
        self.assertEqual(ctx.exception.http_status, 401)

    def test_s07_hash_password_consistency(self):
        """AUTH-S07：加盐哈希可校验；旧 SHA-256 兼容；错密码失败。"""
        from infra.auth_local import hash_password, verify_password

        h1 = hash_password("admin123")
        h2 = hash_password("admin123")
        self.assertNotEqual(h1, h2)
        self.assertTrue(verify_password("admin123", h1))
        self.assertTrue(verify_password("admin123", h2))
        self.assertFalse(verify_password("other", h1))
        legacy = __import__("hashlib").sha256(b"admin123").hexdigest()
        self.assertTrue(verify_password("admin123", legacy))
        self.assertFalse(verify_password("nope", legacy))


class AuthHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_login_ok(self):
        """AUTH-H01：admin login → 200 + access_token。"""
        self._skip_if_down()
        body = json.dumps({"username": "admin", "password": "admin123"}).encode()
        req = urllib.request.Request(
            API_BASE + "/api/v1/auth/login",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read())
        self.assertTrue(res.get("ok"), res)
        self.assertIn("access_token", res["data"])

    def test_h02_login_wrong_password(self):
        """AUTH-H02：错误密码 → 401。"""
        body = json.dumps({"username": "admin", "password": "wrong"}).encode()
        req = urllib.request.Request(
            API_BASE + "/api/v1/auth/login",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("应抛 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_h03_me(self):
        """AUTH-H03：/auth/me 带 token → 200 + user info。"""
        self._skip_if_down()
        res = _http("GET", "/api/v1/auth/me")
        self.assertTrue(res.get("ok"), res)
        self.assertEqual(res["data"]["username"], "admin")

    def test_h04_rbac_roles(self):
        """AUTH-H04：/rbac/roles 返回角色列表。"""
        self._skip_if_down()
        res = _http("GET", "/api/v1/rbac/roles")
        self.assertTrue(res.get("ok"), res)

    def test_h05_rbac_permissions(self):
        """AUTH-H05：/rbac/permissions 返回权限列表。"""
        self._skip_if_down()
        res = _http("GET", "/api/v1/rbac/permissions")
        self.assertTrue(res.get("ok"), res)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(AuthServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(AuthHttpTests))
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
