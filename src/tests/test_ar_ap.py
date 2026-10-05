# SPDX-License-Identifier: Apache-2.0
"""
应收应付中心 · 测试用例与自动化验证

运行: python test_ar_ap.py
      python -m unittest test_ar_ap -v

用例编号 | 场景 | 预期
--------|------|------
TC-01 | 工作台无假应付 | ap_type 仅 ota_commission
TC-02 | 企业 AR 与 charge 对齐 | corp AR 数 = charge 数；每个 on_account 订单有明细
TC-03 | 企业 AR 绑定挂账明细 | 每条 corp AR 有 pms_ar_entry_id，金额一致
TC-04 | OTA 净额 = 毛额 − 佣金 | ota_settlements 与 channels.commission_rate 一致
TC-05 | 授信校验-充足 | check_credit blocked=False
TC-06 | 授信校验-超额 | 超大金额 blocked=True
TC-07 | 手工挂账+回款 | create_corp_charge → apply_receipt → settled
TC-08 | 超额挂账拦截 | create_corp_charge 超授信抛 400
TC-09 | OTA 佣金不可单独付款 | apply_payment 抛 400
TC-10 | 坏账须审批人 | write_off 无 approver 抛 400
TC-11 | 待办关闭 | dismiss_ar_ap_todo 写 todo_dismiss 日志
TC-12 | purge 清除假应付 | 插入 supplier AP 后 purge 删除
TC-13 | 工作台结构 | list_workspace 返回 kpi/aging/ar/ap/todos
TC-14 | HTTP 工作台 | GET workspace 200，无假应付
TC-15 | HTTP 授信 | POST check-credit blocked=False
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from decimal import Decimal

from database import SessionLocal
from domain import BusinessError  # noqa: F401
from models import (
    ApInvoice,
    ArApLog,
    ArInvoice,
    Channel,
    CorpAccount,
    Order,
    OtaSettlement,
    PmsArEntry,
    PmsArLedger,
)

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8000"
_AUTH_TOKEN: str | None = None


def _cleanup_automation_test_data(db, hotel_id: int) -> None:
    """清除历次 TC-07 等自动化测试遗留的手工挂账（charge + settle + AR）。"""
    test_ars = (
        db.query(ArInvoice).filter(ArInvoice.hotel_id == hotel_id, ArInvoice.doc_label.like("%自动化测试%")).all()
    )
    for ar in test_ars:
        entry_id = ar.pms_ar_entry_id
        db.query(ArApLog).filter(ArApLog.hotel_id == hotel_id, ArApLog.ref_id == ar.id).delete()
        db.delete(ar)
        if entry_id:
            entry = db.get(PmsArEntry, entry_id)
            if entry:
                db.delete(entry)
    orphan_entries = db.query(PmsArEntry).filter(PmsArEntry.note.like("%自动化测试%")).all()
    if test_ars or orphan_entries:
        for entry in orphan_entries:
            db.delete(entry)
        db.commit()


def _auth_headers() -> dict[str, str]:
    global _AUTH_TOKEN
    headers = {"Content-Type": "application/json"}
    if _AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {_AUTH_TOKEN}"
    return headers


def _ensure_auth_token() -> bool:
    """尝试 admin 登录；失败则返回 False。"""
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


def _http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API_BASE + path,
        data=data,
        method=method,
        headers=_auth_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "detail": raw.decode(errors="replace"), "status": e.code}


class ArApServiceTests(unittest.TestCase):
    """服务层：数据真实性与业务规则。"""

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        _cleanup_automation_test_data(cls.db, HOTEL_ID)
        from finance.ar_ap_service import list_workspace

        list_workspace(cls.db, HOTEL_ID)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_tc01_no_fake_ap(self):
        """TC-01: 无供应商/房租等假应付。"""
        fake = (
            self.db.query(ApInvoice)
            .filter(ApInvoice.hotel_id == HOTEL_ID, ApInvoice.ap_type != "ota_commission")
            .count()
        )
        self.assertEqual(fake, 0, "仍存在非 OTA 佣金应付")

    def test_tc02_on_account_alignment(self):
        """TC-02: 企业 AR 与 charge 明细一致；每个 on_account 订单均有挂账明细。"""
        on_ac_ids = {o.id for o in self.db.query(Order).filter_by(hotel_id=HOTEL_ID, payment_status="on_account").all()}
        entries = (
            self.db.query(PmsArEntry)
            .join(PmsArLedger, PmsArLedger.id == PmsArEntry.ar_ledger_id)
            .filter(PmsArLedger.hotel_id == HOTEL_ID, PmsArEntry.entry_type == "charge")
            .all()
        )
        corp_ar = (
            self.db.query(ArInvoice)
            .filter(
                ArInvoice.hotel_id == HOTEL_ID,
                ArInvoice.ar_type.in_(("corp_on_account", "longstay", "meeting")),
            )
            .count()
        )
        entry_order_ids = {e.order_id for e in entries if e.order_id}
        self.assertEqual(len(entries), corp_ar, "企业 AR 条数应等于 charge 明细数")
        self.assertTrue(on_ac_ids.issubset(entry_order_ids), "每个 on_account 订单都应有 charge 明细")
        self.assertGreaterEqual(len(entries), len(on_ac_ids), "允许存在无订单的手工挂账")

    def test_tc03_corp_ar_entry_link(self):
        """TC-03: 企业 AR 与 pms_ar_entries 金额一致。"""
        rows = (
            self.db.query(ArInvoice)
            .filter(
                ArInvoice.hotel_id == HOTEL_ID,
                ArInvoice.ar_type.in_(("corp_on_account", "longstay", "meeting")),
            )
            .all()
        )
        if not rows:
            self.skipTest("无企业 AR 样本（本种子库未灌在住挂账订单，CI 跳过）")
        for ar in rows:
            self.assertIsNotNone(ar.pms_ar_entry_id)
            entry = self.db.get(PmsArEntry, ar.pms_ar_entry_id)
            self.assertIsNotNone(entry)
            self.assertAlmostEqual(float(ar.amount), float(entry.amount), places=2)
            if ar.order_id:
                order = self.db.get(Order, ar.order_id)
                self.assertIsNotNone(order)

    def test_tc04_ota_net_formula(self):
        """TC-04: OTA 结算净额 = 毛额 − 佣金。"""
        settle = self.db.query(OtaSettlement).filter_by(hotel_id=HOTEL_ID).first()
        if not settle:
            self.skipTest("无 OTA 结算批次")
        gross = float(settle.gross_amount or 0)
        comm = float(settle.commission_amount or 0)
        net = float(settle.net_amount or 0)
        self.assertAlmostEqual(net, round(gross - comm, 2), places=2)

    def test_tc05_check_credit_ok(self):
        """TC-05: 正常金额授信通过。"""
        from finance.ar_ap_service import check_credit

        corp = self.db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertIsNotNone(corp)
        r = check_credit(self.db, HOTEL_ID, corp.id, 100.0)
        self.assertFalse(r["blocked"])
        self.assertGreaterEqual(r["credit_available"], 100.0)

    def test_tc06_check_credit_blocked(self):
        """TC-06: 超额授信拦截。"""
        from finance.ar_ap_service import check_credit

        corp = self.db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertIsNotNone(corp)
        huge = float(corp.credit_limit or 0) + 1_000_000
        r = check_credit(self.db, HOTEL_ID, corp.id, huge)
        self.assertTrue(r["blocked"])

    def test_tc07_charge_and_receipt(self):
        """TC-07: 手工挂账 → 回款 → 结清。"""
        from finance.ar_ap_service import apply_receipt, create_corp_charge, list_workspace

        corp = self.db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertIsNotNone(corp)
        amt = 88.0
        before_used = float(corp.credit_used or 0)
        out = create_corp_charge(self.db, HOTEL_ID, corp.id, amt, "测试员", "自动化测试挂账")
        ar_id = out["ar_id"]
        self.db.refresh(corp)
        self.assertGreaterEqual(float(corp.credit_used or 0), before_used + amt - 0.01)

        apply_receipt(self.db, HOTEL_ID, ar_id, amt, "对公转账", "测试员", "TEST-RCPT")
        ar = self.db.get(ArInvoice, ar_id)
        self.assertEqual(ar.status, "settled")
        self.assertAlmostEqual(float(ar.paid_amount), amt, places=2)

        logs = self.db.query(ArApLog).filter_by(hotel_id=HOTEL_ID, action="receipt", ref_id=ar_id).count()
        self.assertGreaterEqual(logs, 1)
        list_workspace(self.db, HOTEL_ID)
        _cleanup_automation_test_data(self.db, HOTEL_ID)

    def test_tc08_charge_over_limit(self):
        """TC-08: 超额挂账被拒绝。"""
        from fastapi import HTTPException

        from finance.ar_ap_service import create_corp_charge

        corp = self.db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first()
        huge = float(corp.credit_limit or 0) + 999_999
        with self.assertRaises(BusinessError) as ctx:
            create_corp_charge(self.db, HOTEL_ID, corp.id, huge, "测试员")
        self.assertEqual(ctx.exception.http_status, 400)

    def test_tc09_ota_commission_payment_rejected(self):
        """TC-09: OTA 佣金不可单独付款。"""
        from fastapi import HTTPException

        from finance.ar_ap_service import apply_payment

        ap = (
            self.db.query(ApInvoice)
            .filter_by(hotel_id=HOTEL_ID, ap_type="ota_commission", status="pending_deduct")
            .first()
        )
        if not ap:
            ap = self.db.query(ApInvoice).filter_by(hotel_id=HOTEL_ID, ap_type="ota_commission").first()
        if not ap:
            self.skipTest("无 OTA 佣金应付")
        with self.assertRaises(BusinessError) as ctx:
            apply_payment(self.db, HOTEL_ID, ap.id, 100.0, "对公转账", "测试员")
        self.assertEqual(ctx.exception.http_status, 400)

    def test_tc10_write_off_requires_approver(self):
        """TC-10: 坏账核销须填审批人。"""
        from fastapi import HTTPException

        from finance.ar_ap_service import write_off_ar

        ar = (
            self.db.query(ArInvoice)
            .filter(
                ArInvoice.hotel_id == HOTEL_ID,
                ArInvoice.status.in_(("open", "overdue", "partial")),
                ArInvoice.ar_type == "corp_on_account",
            )
            .first()
        )
        if not ar:
            self.skipTest("无开放企业 AR")
        with self.assertRaises(BusinessError) as ctx:
            write_off_ar(self.db, HOTEL_ID, ar.id, "测试原因", "", "测试员")
        self.assertEqual(ctx.exception.http_status, 400)

    def test_tc11_dismiss_todo(self):
        """TC-11: 关闭待办写审计日志。"""
        from finance.ar_ap_service import dismiss_ar_ap_todo, list_ar_ap_todos

        todos = list_ar_ap_todos(self.db, HOTEL_ID)
        if not todos:
            self.skipTest("无待办样本")
        tid = todos[0]["id"]
        dismiss_ar_ap_todo(self.db, HOTEL_ID, tid, "测试员", "自动化关闭")
        log = (
            self.db.query(ArApLog)
            .filter_by(hotel_id=HOTEL_ID, action="todo_dismiss")
            .order_by(ArApLog.id.desc())
            .first()
        )
        self.assertIsNotNone(log)

    def test_tc12_purge_fake_ap(self):
        """TC-12: purge 删除假应付。"""
        from finance.ar_ap_service import purge_non_real_ar_ap

        self.db.add(
            ApInvoice(
                hotel_id=HOTEL_ID,
                invoice_no="AP-TEST-FAKE",
                ap_type="supplier",
                vendor_name="测试假供应商",
                doc_label="应被清除",
                amount=Decimal("1"),
                status="open",
            )
        )
        self.db.commit()
        r = purge_non_real_ar_ap(self.db, HOTEL_ID)
        self.assertGreaterEqual(r.get("ap_fake_removed", 0), 1)
        left = self.db.query(ApInvoice).filter_by(hotel_id=HOTEL_ID, invoice_no="AP-TEST-FAKE").first()
        self.assertIsNone(left)

    def test_tc13_workspace_shape(self):
        """TC-13: 工作台结构完整。"""
        from finance.ar_ap_service import list_workspace

        ws = list_workspace(self.db, HOTEL_ID)
        for key in ("kpi", "aging", "credit_accounts", "ar_invoices", "ap_invoices", "todos", "as_of"):
            self.assertIn(key, ws)
        self.assertIsInstance(ws["ar_invoices"], list)
        self.assertIsInstance(ws["ap_invoices"], list)


class ArApHttpTests(unittest.TestCase):
    """HTTP 层：需后端 8000 运行；使用 admin 登录 token。"""

    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def test_http_workspace(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8000)")
        res = _http("GET", f"/api/finance/ar-ap/workspace?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertIn("kpi", data)
        self.assertIn("ar_invoices", data)
        fake_ap = [x for x in data.get("ap_invoices", []) if x.get("type_code") != "ota_commission"]
        self.assertEqual(len(fake_ap), 0)

    def test_http_check_credit(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8000)")
        db = SessionLocal()
        try:
            corp = db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first()
            self.assertIsNotNone(corp)
            res = _http(
                "POST",
                f"/api/finance/ar-ap/check-credit?hotel_id={HOTEL_ID}",
                {"corp_id": corp.id, "amount": 100},
            )
            self.assertTrue(res.get("ok"), res)
            self.assertFalse(res["data"]["blocked"])
        finally:
            db.close()


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(ArApServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(ArApHttpTests))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 60)
    print(f"合计: {result.testsRun}  通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}  错误: {len(result.errors)}  跳过: {len(result.skipped)}")
    print("=" * 60)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
