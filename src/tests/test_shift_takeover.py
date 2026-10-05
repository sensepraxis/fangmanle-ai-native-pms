# SPDX-License-Identifier: Apache-2.0
"""
接班确认 · 测试用例（与交班共用 shift_handover）

运行: python test_shift_takeover.py
      python -m unittest test_shift_takeover -v
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry, ensure_float_carry_2000
from bootstrap.ensure_shift_handover import ensure_shift_handover_schema
from database import SessionLocal, engine
from finance.shift_handover_service import build_workspace, save_asset_count, save_float_count, sign_handover
from finance.shift_takeover_service import (
    ack_takeover_carryover,
    ack_takeover_deposit,
    ack_takeover_guest,
    ack_takeover_revenue,
    build_takeover_workspace,
    claim_takeover_task,
    confirm_takeover_matters,
    report_receive_diff,
    save_takeover_asset_recount,
    save_takeover_float_recount,
    sign_takeover_receive,
)
from models import ShiftAssetCount, ShiftFloatCount, ShiftHandover, ShiftReceiveDiff

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


def _prepare_outgoing_signed(db) -> int:
    """完成交班人盘库并签字，返回 handover_id。"""
    ws = build_workspace(db, HOTEL_ID, 1)
    hid = ws["handover_id"]
    denoms = [
        {"denom": d["denom"], "actual_qty": int(d.get("expected_qty") or 0)} for d in ws["float"]["denominations"]
    ]
    expected = float(ws["float"]["expected"])
    actual_sum = sum(float(d["denom"]) * int(d["actual_qty"]) for d in denoms)
    diff_reason = ""
    if abs(actual_sum - expected) >= 0.01:
        diff_reason = "自动化测试面额取整差异"
    save_float_count(db, HOTEL_ID, hid, denoms, diff_reason=diff_reason, operator_id=1)
    assets = [{"id": a["id"], "actual_qty": int(a.get("expected_qty") or 0), "diff_reason": ""} for a in ws["assets"]]
    save_asset_count(db, HOTEL_ID, hid, assets, operator_id=1)
    sign_handover(db, HOTEL_ID, hid, "outgoing", 1)
    row = db.get(ShiftHandover, hid)
    row.incoming_signed_at = None
    row.incoming_user_id = None
    row.manager_required = False
    row.manager_signed_at = None
    row.manager_user_id = None
    row.received_revenue_ok = False
    row.deposit_ack = False
    row.float_received_confirmed = False
    row.assets_received_confirmed = False
    row.matters_confirmed = False
    row.guest_situation_acks = None
    row.task_claims = None
    row.carryover_acks = None
    row.status = "pending_acknowledgment"
    db.commit()
    return hid


def _full_takeover_prep(db, hid: int) -> None:
    ws = build_takeover_workspace(db, HOTEL_ID, 1)
    ack_takeover_revenue(db, HOTEL_ID, hid, ok=True, operator_id=1)
    ack_takeover_deposit(db, HOTEL_ID, hid, ok=True, operator_id=1)
    denoms = [{"denom": d["denom"], "received_qty": d["outgoing_qty"]} for d in ws["float"]["denominations"]]
    save_takeover_float_recount(db, HOTEL_ID, hid, denoms, confirm=True, operator_id=1)
    assets = [{"id": a["id"], "received_qty": a["outgoing_qty"], "received_ack": False} for a in ws["assets"]]
    save_takeover_asset_recount(db, HOTEL_ID, hid, assets, confirm=True, operator_id=1)
    for g in ws.get("guest_situations") or []:
        ack_takeover_guest(db, HOTEL_ID, hid, keys=[g["key"]], operator_id=1)
    for t in ws.get("tasks") or []:
        claim_takeover_task(db, HOTEL_ID, hid, task_index=t["index"], action="claimed", operator_id=1)
    for c in ws.get("carryover") or []:
        ack_takeover_carryover(db, HOTEL_ID, hid, carryover_ids=[c["id"]], operator_id=1)
    confirm_takeover_matters(db, HOTEL_ID, hid, operator_id=1)


class ShiftTakeoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_shift_handover_schema(engine)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)
        # 清空本测试类可能受前序 ShiftHandover/ShiftFlow 测试污染的班次数据
        # （_find_takeover_handover 按 id desc 取最新一条，前序测试留下的 handover
        # 会让"未签字 → ready=False"这条断言失效）。
        cls.db.query(ShiftReceiveDiff).filter(
            ShiftReceiveDiff.handover_id.in_(cls.db.query(ShiftHandover.id).filter_by(hotel_id=HOTEL_ID))
        ).delete(synchronize_session=False)
        cls.db.query(ShiftAssetCount).filter(
            ShiftAssetCount.handover_id.in_(cls.db.query(ShiftHandover.id).filter_by(hotel_id=HOTEL_ID))
        ).delete(synchronize_session=False)
        cls.db.query(ShiftFloatCount).filter(
            ShiftFloatCount.handover_id.in_(cls.db.query(ShiftHandover.id).filter_by(hotel_id=HOTEL_ID))
        ).delete(synchronize_session=False)
        cls.db.query(ShiftHandover).filter_by(hotel_id=HOTEL_ID).delete()
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_st01_not_ready_without_outgoing_sign(self):
        ws = build_workspace(self.db, HOTEL_ID, 1)
        row = self.db.get(ShiftHandover, ws["handover_id"])
        row.outgoing_signed_at = None
        row.status = "in_progress"
        self.db.commit()
        takeover = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertFalse(takeover.get("ready"))

    def test_st02_ready_after_outgoing_signed(self):
        hid = _prepare_outgoing_signed(self.db)
        takeover = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(takeover.get("ready"))
        self.assertEqual(takeover["handover_id"], hid)
        self.assertTrue(takeover["signatures"]["outgoing_signed"])
        self.assertFalse(takeover["signatures"]["incoming_signed"])

    def test_st03_float_recount_match(self):
        hid = _prepare_outgoing_signed(self.db)
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        denoms = [{"denom": d["denom"], "received_qty": d["outgoing_qty"]} for d in ws["float"]["denominations"]]
        save_takeover_float_recount(self.db, HOTEL_ID, hid, denoms, confirm=True, operator_id=1)
        ws2 = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws2["float"]["match_outgoing"])
        self.assertTrue(ws2["float"]["confirmed"])

    def test_st04_float_mismatch_report(self):
        hid = _prepare_outgoing_signed(self.db)
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        denoms = [
            {"denom": d["denom"], "received_qty": max(0, int(d["outgoing_qty"]) - 1)}
            for d in ws["float"]["denominations"]
        ]
        save_takeover_float_recount(self.db, HOTEL_ID, hid, denoms, confirm=False, operator_id=1)
        ws2 = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertFalse(ws2["float"]["match_outgoing"])
        report_receive_diff(
            self.db,
            HOTEL_ID,
            hid,
            item_type="float",
            item_key="total",
            declared_val=ws2["float"]["outgoing_actual"],
            received_val=ws2["float"]["received_actual"],
            reason="自动化测试：找零时少一枚硬币",
            operator_id=1,
        )
        ws3 = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws3["signatures"]["manager_required"])
        self.assertGreaterEqual(len(ws3.get("receive_diffs") or []), 1)

    def test_st05_sign_after_full_flow(self):
        hid = _prepare_outgoing_signed(self.db)
        _full_takeover_prep(self.db, hid)
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws["flags"]["can_sign"])
        sign_takeover_receive(self.db, HOTEL_ID, hid, incoming_user_id=1, operator_id=1)
        ws2 = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws2["signatures"]["incoming_signed"])
        self.assertTrue(ws2["flags"]["can_complete"])

    def test_st06_matters_confirm_requires_all(self):
        hid = _prepare_outgoing_signed(self.db)
        with self.assertRaises(Exception):
            confirm_takeover_matters(self.db, HOTEL_ID, hid, operator_id=1)


class ShiftTakeoverHttpTests(unittest.TestCase):
    def test_st07_http_takeover_workspace(self):
        if not _auth_token():
            self.skipTest("API 未启动，跳过 HTTP 测试")
        res = _http("GET", f"/api/finance/shift-handover/takeover/workspace?hotel_id={HOTEL_ID}")
        if res.get("status") == 404 or res.get("detail") == "Not Found":
            self.skipTest("API 未加载接班路由，跳过 HTTP 测试")
        data = res.get("data") or res
        self.assertIn("ready", data)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
