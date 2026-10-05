# SPDX-License-Identifier: Apache-2.0
"""
交班管理 · 测试用例（数据真实性与流程）

运行: python test_shift_handover.py
      python -m unittest test_shift_handover -v

SH-01 | 备用金应有额 = 财务参数 ¥2000（非硬编码 5000）
SH-02 | 备用金来源标记 finance_params
SH-03 | 未盘库实盘为 0 / null，不预填对平
SH-04 | 无占位假待办
SH-05 | 营收与 payments 表一致（班次窗口）
SH-06 | 目标完成度无配置时为 null
SH-07 | 实物应有数来自 supplies / 房间数
SH-08 | 备用金盘库可持久化
SH-09 | HTTP 交班工作台 200 + float 2000
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry, ensure_float_carry_2000
from database import SessionLocal, engine
from finance.shift_handover_service import build_workspace, save_float_count
from models import FinanceFloatCarry, Payment, ShiftAssetCount, ShiftFloatCount, ShiftHandover

HOTEL_ID = 1
API_BASE = "http://127.0.0.1:8000"
_AUTH_TOKEN: str | None = None


def _auth_token() -> str | None:
    global _AUTH_TOKEN
    if _AUTH_TOKEN:
        return _AUTH_TOKEN
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
        _AUTH_TOKEN = (body.get("data") or {}).get("access_token") or (body.get("data") or {}).get("token")
        return _AUTH_TOKEN
    except Exception:
        return None


def _http(method: str, path: str, body: dict | None = None) -> dict:
    token = _auth_token()
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


def _shift_window_revenue(db, hotel_id: int, handover: ShiftHandover) -> float:
    now = datetime.now()
    start = handover.start_at or now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_cap = handover.end_at or now
    end = min(now, end_cap)
    rows = (
        db.query(Payment)
        .filter(
            Payment.hotel_id == hotel_id,
            Payment.paid_at >= start,
            Payment.paid_at < end,
            Payment.amount > 0,
        )
        .all()
    )
    return round(sum(float(p.amount or 0) for p in rows), 2)


class ShiftHandoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _ws(self):
        return build_workspace(self.db, HOTEL_ID, 1)

    def test_sh01_float_expected_from_finance_params(self):
        ws = self._ws()
        active = self.db.query(FinanceFloatCarry).filter_by(hotel_id=HOTEL_ID, status="active").first()
        self.assertIsNotNone(active)
        self.assertEqual(ws["float"]["expected"], float(active.amount))
        self.assertEqual(ws["float"]["expected"], 2000.0)
        self.assertNotEqual(ws["float"]["expected"], 5000.0)

    def test_sh02_carry_source_finance_params(self):
        ws = self._ws()
        self.assertEqual(ws["float"]["carry_source"], "finance_params")

    def test_sh03_unconfirmed_actual_not_prefilled(self):
        ws = self._ws()
        handover = self.db.get(ShiftHandover, ws["handover_id"])
        if handover and not handover.float_confirmed:
            for d in ws["float"]["denominations"]:
                self.assertEqual(int(d.get("actual_qty") or 0), 0)
        for a in ws["assets"]:
            if handover and not handover.assets_confirmed:
                self.assertIsNone(a["actual_qty"])

    def test_sh04_no_placeholder_tasks(self):
        ws = self._ws()
        for t in ws["tasks"]:
            self.assertNotIn("班次正常", t.get("content") or "")
            self.assertNotIn("按 SOP", t.get("content") or "")

    def test_sh05_revenue_matches_payments(self):
        ws = self._ws()
        handover = self.db.get(ShiftHandover, ws["handover_id"])
        self.assertIsNotNone(handover)
        expected_rev = _shift_window_revenue(self.db, HOTEL_ID, handover)
        self.assertEqual(ws["revenue"]["total"], expected_rev)
        self.assertEqual(ws["banner"]["total_revenue"], expected_rev)

    def test_sh06_target_pct_null_without_config(self):
        ws = self._ws()
        self.assertIsNone(ws["revenue"].get("target_pct"))

    def test_sh07_assets_from_inventory(self):
        ws = self._ws()
        asset_rows = self.db.query(ShiftAssetCount).filter_by(handover_id=ws["handover_id"]).all()
        legacy = [a for a in asset_rows if a.asset_type in ("room_card", "receipt_book", "invoice_book")]
        self.assertEqual(len(legacy), 0, "不应存在硬编码实物模板")
        self.assertGreater(len(ws["assets"]), 0)

    def test_sh08_float_count_persists(self):
        ws = self._ws()
        hid = ws["handover_id"]
        denoms = [
            {"denom": d["denom"], "actual_qty": int(d.get("expected_qty") or 0)} for d in ws["float"]["denominations"]
        ]
        actual_sum = sum(float(d["denom"]) * int(d["actual_qty"]) for d in denoms)
        expected = float(ws["float"]["expected"])
        diff_reason = ""
        if abs(actual_sum - expected) >= 0.01:
            diff_reason = "自动化测试面额取整差异"
        save_float_count(self.db, HOTEL_ID, hid, denoms, diff_reason=diff_reason, operator_id=1, operator_name="test")
        row = self.db.get(ShiftHandover, hid)
        self.assertTrue(row.float_confirmed)
        self.assertAlmostEqual(float(row.float_actual or 0), actual_sum, delta=0.01)


class ShiftHandoverHttpTests(unittest.TestCase):
    def test_sh09_http_workspace(self):
        if not _auth_token():
            self.skipTest("API 未启动，跳过 HTTP 测试")
        res = _http("GET", f"/api/finance/shift-handover/workspace?hotel_id={HOTEL_ID}")
        data = res.get("data") or res
        self.assertEqual(float(data.get("float", {}).get("expected", 0)), 2000.0)
        self.assertEqual(data.get("float", {}).get("carry_source"), "finance_params")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
