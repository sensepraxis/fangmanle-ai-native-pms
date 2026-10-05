# SPDX-License-Identifier: Apache-2.0
"""
财务参数扩展 · 测试用例（税率账期 / 收单费率 / 信用账龄）

运行: python test_finance_params_ext.py
      python -m unittest test_finance_params_ext -v

FP-01 | 税率工作台从 DB 读取，主营税率 6%
FP-02 | 账期种子 8 类齐全
FP-03 | 修改税率写入新版本并留痕（原因必填）
FP-04 | 原因过短拒绝改税
FP-05 | 调整客户账期写入 DB
FP-06 | 收单渠道从 DB 读取，含微信 0.60%
FP-07 | 改费率写入 DB 并留痕
FP-08 | 渠道开关切换
FP-09 | 授信客户从 DB 读取（≥8）
FP-10 | 调额度写入 DB；不可低于已用
FP-11 | 新增授信客户写入 DB 并留痕
FP-12 | 重复名称拒绝新增
FP-13 | 坏账准备率可调
FP-14 | HTTP 三工作台 200 + 新增客户 API
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from decimal import Decimal

from fastapi import HTTPException

from bootstrap.ensure_finance_params_ext import bootstrap_finance_params_ext
from database import SessionLocal, engine
from domain import BusinessError  # noqa: F401
from finance.finance_params_ext_service import (
    create_credit_customer,
    get_acquiring_workspace,
    get_credit_workspace,
    get_tax_workspace,
    toggle_acquiring_channel,
    update_acquiring_rate,
    update_bad_debt_rate,
    update_credit_limit,
    update_payment_term,
    update_tax_config,
)
from models import (
    FinanceAcquiringChannel,
    FinanceBadDebtRate,
    FinanceCreditCustomer,
    FinanceParamAudit,
    FinancePaymentTerm,
    FinanceTaxConfig,
)

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8000"
_TEST_TAG = "自动化测试财务参数"
_CREDIT_NAME = f"{_TEST_TAG}-授信客户"


def _cleanup(db) -> None:
    for row in (
        db.query(FinanceCreditCustomer)
        .filter(
            FinanceCreditCustomer.hotel_id == HOTEL_ID,
            FinanceCreditCustomer.name.like(f"{_TEST_TAG}%"),
        )
        .all()
    ):
        db.delete(row)
    for row in (
        db.query(FinanceParamAudit)
        .filter(
            FinanceParamAudit.hotel_id == HOTEL_ID,
            FinanceParamAudit.reason.like(f"%{_TEST_TAG}%"),
        )
        .all()
    ):
        db.delete(row)
    # 回滚测试中可能改坏的税率版本：保留 seed 外、带测试原因的 superseded
    for row in (
        db.query(FinanceTaxConfig)
        .filter(
            FinanceTaxConfig.hotel_id == HOTEL_ID,
            FinanceTaxConfig.change_reason.like(f"%{_TEST_TAG}%"),
        )
        .all()
    ):
        db.delete(row)
    db.commit()


def _auth_token(username: str = "admin", password: str = "admin123") -> str | None:
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
        return (body.get("data") or {}).get("access_token")
    except Exception:
        return None


def _http(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


class FinanceParamsExtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap_finance_params_ext(engine, HOTEL_ID)
        db = SessionLocal()
        try:
            _cleanup(db)
        finally:
            db.close()

    def setUp(self):
        self.db = SessionLocal()
        _cleanup(self.db)

    def tearDown(self):
        _cleanup(self.db)
        self.db.close()

    # ---- 税率与账期 ----

    def test_fp01_tax_from_db(self):
        ws = get_tax_workspace(self.db, HOTEL_ID)
        row = self.db.query(FinanceTaxConfig).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertIsNotNone(row)
        self.assertEqual(ws["tax"]["main_rate"], 6.0)
        self.assertEqual(ws["tax"]["taxpayer_type"], row.taxpayer_type)
        self.assertEqual(ws["tax"]["tax_code"], row.tax_code)

    def test_fp02_eight_payment_terms(self):
        ws = get_tax_workspace(self.db, HOTEL_ID)
        types = [t["customer_type"] for t in ws["terms"]]
        self.assertEqual(len(types), 8)
        for need in ("散客", "OTA 携程", "企业挂账", "旅行社"):
            self.assertIn(need, types)
        cnt = self.db.query(FinancePaymentTerm).filter_by(hotel_id=HOTEL_ID).count()
        self.assertEqual(cnt, 8)

    def test_fp03_update_tax_persists(self):
        before = self.db.query(FinanceTaxConfig).filter_by(hotel_id=HOTEL_ID, status="active").first()
        old_ver = before.version
        ws = update_tax_config(
            self.db,
            HOTEL_ID,
            taxpayer_type="一般纳税人",
            main_rate_pct=6.0,
            price_mode="价外",
            effective_mode="立即生效",
            reason=f"{_TEST_TAG}改税验证",
        )
        self.db.expire_all()
        active = self.db.query(FinanceTaxConfig).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertEqual(active.version, old_ver + 1)
        self.assertIn(_TEST_TAG, active.change_reason or "")
        audit = (
            self.db.query(FinanceParamAudit)
            .filter(
                FinanceParamAudit.hotel_id == HOTEL_ID,
                FinanceParamAudit.domain == "tax",
                FinanceParamAudit.reason.like(f"%{_TEST_TAG}%"),
            )
            .first()
        )
        self.assertIsNotNone(audit)
        self.assertTrue(any(h.get("type") == "税率" for h in ws["history"]))

    def test_fp04_tax_reason_required(self):
        with self.assertRaises(BusinessError) as ctx:
            update_tax_config(
                self.db,
                HOTEL_ID,
                taxpayer_type="一般纳税人",
                main_rate_pct=6,
                price_mode="价外",
                effective_mode="立即生效",
                reason="短",
            )
        self.assertEqual(ctx.exception.http_status, 400)

    def test_fp05_update_term(self):
        term = self.db.query(FinancePaymentTerm).filter_by(hotel_id=HOTEL_ID, customer_type="旅行社").first()
        self.assertIsNotNone(term)
        update_payment_term(
            self.db,
            HOTEL_ID,
            term.id,
            term_label="20 天",
            effective_mode="立即生效",
            reason=f"{_TEST_TAG}调账期",
        )
        self.db.refresh(term)
        self.assertEqual(term.term_label, "20 天")
        # 还原，避免污染
        term.term_label = "15 天"
        self.db.commit()

    # ---- 收单费率 ----

    def test_fp06_acquiring_from_db(self):
        ws = get_acquiring_workspace(self.db, HOTEL_ID)
        self.assertGreaterEqual(len(ws["channels"]), 6)
        wechat = next(c for c in ws["channels"] if c["code"] == "wechat")
        self.assertAlmostEqual(wechat["rate_pct"], 0.60, places=2)
        cnt = self.db.query(FinanceAcquiringChannel).filter_by(hotel_id=HOTEL_ID).count()
        self.assertEqual(cnt, len(ws["channels"]))
        self.assertIn("active_channels", ws["kpi"])

    def test_fp07_update_rate(self):
        ch = self.db.query(FinanceAcquiringChannel).filter_by(hotel_id=HOTEL_ID, channel_code="alipay").first()
        old = float(ch.rate_pct)
        update_acquiring_rate(
            self.db,
            HOTEL_ID,
            ch.id,
            rate_pct=0.55,
            effective_mode="立即生效",
            reason=f"{_TEST_TAG}改费率",
        )
        self.db.refresh(ch)
        self.assertAlmostEqual(float(ch.rate_pct), 0.55, places=2)
        ch.rate_pct = Decimal(str(old))
        self.db.commit()

    def test_fp08_toggle_channel(self):
        ch = self.db.query(FinanceAcquiringChannel).filter_by(hotel_id=HOTEL_ID, channel_code="unionpay_nfc").first()
        # 云闪付无费率，上线应失败
        with self.assertRaises(BusinessError):
            toggle_acquiring_channel(self.db, HOTEL_ID, ch.id, enabled=True)
        pos = self.db.query(FinanceAcquiringChannel).filter_by(hotel_id=HOTEL_ID, channel_code="pos_credit").first()
        was = bool(pos.enabled)
        toggle_acquiring_channel(self.db, HOTEL_ID, pos.id, enabled=not was)
        self.db.refresh(pos)
        self.assertEqual(bool(pos.enabled), not was)
        toggle_acquiring_channel(self.db, HOTEL_ID, pos.id, enabled=was)

    # ---- 信用与账龄 ----

    def test_fp09_credit_from_db(self):
        ws = get_credit_workspace(self.db, HOTEL_ID)
        self.assertGreaterEqual(len(ws["customers"]), 8)
        cnt = self.db.query(FinanceCreditCustomer).filter_by(hotel_id=HOTEL_ID).count()
        self.assertEqual(cnt, ws["kpi"]["customer_count"])
        names = [c["name"] for c in ws["customers"]]
        self.assertIn("中青旅控股", names)

    def test_fp10_credit_limit_rules(self):
        row = self.db.query(FinanceCreditCustomer).filter_by(hotel_id=HOTEL_ID, name="本地科技公司").first()
        used = float(row.credit_used)
        with self.assertRaises(BusinessError):
            update_credit_limit(
                self.db,
                HOTEL_ID,
                row.id,
                new_limit=used - 1,
                reason=f"{_TEST_TAG}低于已用",
            )
        old = float(row.credit_limit)
        update_credit_limit(
            self.db,
            HOTEL_ID,
            row.id,
            new_limit=old + 1000,
            reason=f"{_TEST_TAG}上调额度",
        )
        self.db.refresh(row)
        self.assertAlmostEqual(float(row.credit_limit), old + 1000, places=2)
        row.credit_limit = Decimal(str(old))
        self.db.commit()

    def test_fp11_create_credit_customer(self):
        ws = create_credit_customer(
            self.db,
            HOTEL_ID,
            name=_CREDIT_NAME,
            customer_type="企业挂账",
            grade="B",
            credit_limit=15000,
            term_label="30 天",
            reason=f"{_TEST_TAG}新增协议客户",
        )
        names = [c["name"] for c in ws["customers"]]
        self.assertIn(_CREDIT_NAME, names)
        row = self.db.query(FinanceCreditCustomer).filter_by(hotel_id=HOTEL_ID, name=_CREDIT_NAME).first()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(float(row.credit_limit), 15000)
        audit = (
            self.db.query(FinanceParamAudit)
            .filter_by(hotel_id=HOTEL_ID, domain="credit", action_type="新增", target=_CREDIT_NAME)
            .first()
        )
        self.assertIsNotNone(audit)

    def test_fp12_duplicate_name_rejected(self):
        create_credit_customer(
            self.db,
            HOTEL_ID,
            name=_CREDIT_NAME,
            customer_type="旅行社",
            grade="A",
            credit_limit=10000,
            term_label="15 天",
            reason=f"{_TEST_TAG}首次新增",
        )
        with self.assertRaises(BusinessError) as ctx:
            create_credit_customer(
                self.db,
                HOTEL_ID,
                name=_CREDIT_NAME,
                customer_type="旅行社",
                grade="A",
                credit_limit=10000,
                term_label="15 天",
                reason=f"{_TEST_TAG}重复新增",
            )
        self.assertEqual(ctx.exception.http_status, 400)

    def test_fp13_bad_debt_rate(self):
        row = self.db.query(FinanceBadDebtRate).filter_by(hotel_id=HOTEL_ID, bucket="30-60").first()
        old = float(row.rate_pct)
        update_bad_debt_rate(
            self.db,
            HOTEL_ID,
            row.id,
            rate_pct=6,
            reason=f"{_TEST_TAG}调坏账率",
        )
        self.db.refresh(row)
        self.assertAlmostEqual(float(row.rate_pct), 6.0)
        row.rate_pct = Decimal(str(old))
        self.db.commit()

    def test_fp14_http_workspaces_and_create(self):
        tok = _auth_token()
        if not tok:
            self.skipTest("后端未启动或无法登录")
        for path in ("tax", "acquiring", "credit"):
            body = _http("GET", f"/api/system/finance-params/{path}?hotel_id=1", token=tok)
            self.assertTrue(body.get("ok", True) or "data" in body)
            data = body.get("data") or body
            self.assertIsInstance(data, dict)
        name = f"{_CREDIT_NAME}-HTTP"
        try:
            body = _http(
                "POST",
                "/api/system/finance-params/credit?hotel_id=1",
                {
                    "name": name,
                    "customer_type": "OTA",
                    "grade": "B",
                    "credit_limit": 8000,
                    "term_label": "T+15",
                    "reason": f"{_TEST_TAG}HTTP新增",
                },
                token=tok,
            )
            data = body.get("data") or body
            names = [c["name"] for c in data.get("customers", [])]
            self.assertIn(name, names)
        finally:
            db = SessionLocal()
            try:
                for row in (
                    db.query(FinanceCreditCustomer).filter(FinanceCreditCustomer.name.like(f"{_TEST_TAG}%")).all()
                ):
                    db.delete(row)
                for row in db.query(FinanceParamAudit).filter(FinanceParamAudit.reason.like(f"%{_TEST_TAG}%")).all():
                    db.delete(row)
                db.commit()
            finally:
                db.close()


if __name__ == "__main__":
    # 确保服务层改动能被当前进程加载；HTTP 用例依赖已重启的 uvicorn
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinanceParamsExtTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
