# SPDX-License-Identifier: Apache-2.0
"""
门店备用金财务参数 · 测试用例

运行: python test_finance_float_carry.py
      python -m unittest test_finance_float_carry -v

FC-01 | 生效底数为 ¥2000 CNY
FC-02 | 交班读取源为 finance_params
FC-03 | 提交变更须身份复核密码
FC-04 | 前台角色不可提交变更
FC-05 | 双授权完整流程生效新底数
FC-06 | 驳回后底数不变
FC-07 | 相同金额不可重复提交
FC-08 | 申请人不可自审
FC-09 | 财务与店长须不同复核人
FC-10 | HTTP 工作台返回 2000
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from fastapi import HTTPException

from bootstrap.ensure_finance_float_carry import (
    bootstrap_finance_float_carry,
    ensure_finance_review_users,
    ensure_float_carry_2000,
)
from database import SessionLocal, engine
from domain import BusinessError  # noqa: F401
from finance.finance_float_service import (
    approve_float_carry_finance,
    approve_float_carry_manager,
    get_active_float_carry_amount,
    get_float_carry_workspace,
    reject_float_carry_change,
    submit_float_carry_change,
)
from infra.auth_local import authenticate_user
from models import FinanceFloatCarry, User

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8000"
_TEST_TAG = "自动化测试备用金"
_AUTH: dict[str, str | None] = {"admin": None, "finance": None, "front": None}


def _cleanup_pending(db, hotel_id: int = HOTEL_ID) -> None:
    rows = (
        db.query(FinanceFloatCarry)
        .filter(
            FinanceFloatCarry.hotel_id == hotel_id,
            FinanceFloatCarry.change_reason.like(f"%{_TEST_TAG}%"),
        )
        .all()
    )
    for r in rows:
        db.delete(r)
    db.commit()


def _auth_token(username: str, password: str) -> str | None:
    try:
        data = json.dumps({"username": username, "password": password}).encode()
        req = urllib.request.Request(
            API_BASE + "/api/auth/login",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read())
        return (body.get("data") or {}).get("access_token") or (body.get("data") or {}).get("token")
    except Exception:
        return None


def _http(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "detail": raw.decode(errors="replace"), "status": e.code}


class FinanceFloatCarryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_finance_review_users(cls.db)
        # ensure_rbac_users 会把 finance 标记为停用（遗留账户映射），但双授权备用金流程
        # 需要 finance / manager 账号可用，这里强制激活。
        for _uname in ("finance", "manager"):
            _u = cls.db.query(User).filter_by(username=_uname).first()
            if _u:
                _u.is_active = True
        cls.db.commit()
        ensure_float_carry_2000(cls.db, HOTEL_ID)
        _cleanup_pending(cls.db)
        cls.admin = authenticate_user(cls.db, "admin", "admin123")
        cls.finance = authenticate_user(cls.db, "finance", "finance123")
        cls.manager = authenticate_user(cls.db, "manager", "manager123")
        cls.front = authenticate_user(cls.db, "front", "front123")

    @classmethod
    def tearDownClass(cls):
        _cleanup_pending(cls.db)
        ensure_float_carry_2000(cls.db, HOTEL_ID)
        cls.db.close()

    def setUp(self):
        _cleanup_pending(self.db)
        ensure_float_carry_2000(self.db, HOTEL_ID)

    def test_fc01_active_2000_cny(self):
        ws = get_float_carry_workspace(self.db, HOTEL_ID)
        self.assertIsNotNone(ws["active"])
        self.assertEqual(ws["active"]["amount"], 2000.0)
        self.assertEqual(ws["active"]["currency"], "CNY")
        self.assertEqual(get_active_float_carry_amount(self.db, HOTEL_ID), 2000.0)

    def test_fc02_handover_reads_finance_params(self):
        from finance.shift_handover_service import build_workspace

        ws = build_workspace(self.db, HOTEL_ID, self.admin.user_id)
        self.assertEqual(ws["float"]["expected"], 2000.0)
        self.assertEqual(ws["float"]["carry_source"], "finance_params")

    def test_fc03_submit_requires_review_password(self):
        with self.assertRaises(BusinessError) as ctx:
            submit_float_carry_change(
                self.db,
                HOTEL_ID,
                2500.0,
                f"{_TEST_TAG} 缺密码",
                self.admin,
                review_password="",
            )
        self.assertIn("二次校验", str(ctx.exception))

    def test_fc04_front_cannot_submit(self):
        with self.assertRaises(BusinessError) as ctx:
            submit_float_carry_change(
                self.db,
                HOTEL_ID,
                2500.0,
                f"{_TEST_TAG} 前台越权",
                self.front,
                review_password="front123",
            )
        self.assertEqual(ctx.exception.http_status, 403)

    def test_fc05_dual_auth_flow(self):
        row = submit_float_carry_change(
            self.db,
            HOTEL_ID,
            2500.0,
            f"{_TEST_TAG} 双授权流程",
            self.admin,
            review_password="admin123",
        )
        approve_float_carry_finance(self.db, HOTEL_ID, row["id"], self.finance, "finance123")
        approve_float_carry_manager(self.db, HOTEL_ID, row["id"], self.manager, "manager123")
        self.assertEqual(get_active_float_carry_amount(self.db, HOTEL_ID), 2500.0)

    def test_fc06_reject_keeps_amount(self):
        row = submit_float_carry_change(
            self.db,
            HOTEL_ID,
            2600.0,
            f"{_TEST_TAG} 驳回",
            self.admin,
            review_password="admin123",
        )
        reject_float_carry_change(self.db, HOTEL_ID, row["id"], self.finance, "审批驳回", "finance123")
        self.assertEqual(get_active_float_carry_amount(self.db, HOTEL_ID), 2000.0)

    def test_fc07_same_amount_rejected(self):
        with self.assertRaises(BusinessError):
            submit_float_carry_change(
                self.db,
                HOTEL_ID,
                2000.0,
                f"{_TEST_TAG} 相同金额",
                self.admin,
                review_password="admin123",
            )

    def test_fc08_applicant_cannot_self_review(self):
        row = submit_float_carry_change(
            self.db,
            HOTEL_ID,
            2400.0,
            f"{_TEST_TAG} 自审",
            self.admin,
            review_password="admin123",
        )
        with self.assertRaises(BusinessError) as ctx:
            approve_float_carry_finance(self.db, HOTEL_ID, row["id"], self.admin, "admin123")
        self.assertEqual(ctx.exception.http_status, 403)

    def test_fc09_same_reviewer_cannot_manager_approve(self):
        row = submit_float_carry_change(
            self.db,
            HOTEL_ID,
            2450.0,
            f"{_TEST_TAG} 同人二审",
            self.admin,
            review_password="admin123",
        )
        approve_float_carry_finance(self.db, HOTEL_ID, row["id"], self.finance, "finance123")
        with self.assertRaises(BusinessError) as ctx:
            approve_float_carry_manager(self.db, HOTEL_ID, row["id"], self.finance, "finance123")
        self.assertEqual(ctx.exception.http_status, 403)


class FinanceFloatCarryHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_ok = bool(_auth_token("admin", "admin123"))
        if cls.api_ok:
            _AUTH["admin"] = _auth_token("admin", "admin123")
            _AUTH["finance"] = _auth_token("finance", "finance123")

    def test_fc10_http_workspace_2000(self):
        if not self.api_ok:
            self.skipTest("API 未启动，跳过 HTTP 测试")
        res = _http("GET", f"/api/system/finance-params/float-carry?hotel_id={HOTEL_ID}", token=_AUTH["admin"])
        data = res.get("data") or res
        self.assertEqual(float((data.get("active") or {}).get("amount", 0)), 2000.0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
