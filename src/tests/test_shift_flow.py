# SPDX-License-Identifier: Apache-2.0
"""
交班 + 接班 · 综合测试用例

运行:
  python test_shift_flow.py
  python -m unittest test_shift_flow -v

用例清单
--------
交班 HO-10  实物盘库持久化 + expected 对齐 supplies.current_stock
交班 HO-11  交班人签字前须完成钱/物盘库
交班 HO-12  交班人签字后 status=pending_acknowledgment
交班 HO-13  短款须填原因，否则 save_float_count 拒绝
交班 HO-14  实物差异须填原因，否则 save_asset_count 拒绝

接班 TK-08  营收/押金确认持久化
接班 TK-09  实物复点与交班人不符时须勾选「差异已知晓」
接班 TK-10  未完成复核时 can_sign=False
接班 TK-11  客情/待办认领进度正确
接班 TK-12  差异上报后 manager_required=True

闭环 E2E-01  交班盘库→交班签字→接班全流程→完成归档
闭环 E2E-02  HTTP 交班/接班工作台均可访问

HTTP HO-15  POST float-count / asset-count
HTTP TK-13  POST takeover revenue-ack / float-recount
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from fastapi import HTTPException

from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry, ensure_float_carry_2000
from bootstrap.ensure_shift_handover import ensure_shift_handover_schema
from database import SessionLocal, engine
from domain import BusinessError  # noqa: F401
from finance.shift_handover_service import (
    build_workspace,
    complete_handover,
    save_asset_count,
    save_float_count,
    sign_handover,
)
from finance.shift_takeover_service import (
    ack_takeover_deposit,
    ack_takeover_guest,
    ack_takeover_revenue,
    build_takeover_workspace,
    claim_takeover_task,
    complete_takeover_receive,
    confirm_takeover_matters,
    report_receive_diff,
    save_takeover_asset_recount,
    save_takeover_float_recount,
    sign_takeover_receive,
)
from models import Room, ShiftAssetCount, ShiftHandover, Supply

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


def _http(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    token = _auth_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"ok": False, "detail": raw.decode(errors="replace")}


def _reset_takeover_state(db, row: ShiftHandover) -> None:
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
    row.completed_at = None
    row.archived_at = None
    if row.outgoing_signed_at:
        row.status = "pending_acknowledgment"
    db.commit()


def _confirm_handover_money_assets(db, hid: int) -> None:
    ws = build_workspace(db, HOTEL_ID, 1)
    denoms = [
        {"denom": d["denom"], "actual_qty": int(d.get("expected_qty") or 0)} for d in ws["float"]["denominations"]
    ]
    expected = float(ws["float"]["expected"])
    actual_sum = sum(float(d["denom"]) * int(d["actual_qty"]) for d in denoms)
    diff_reason = "自动化测试面额取整差异" if abs(actual_sum - expected) >= 0.01 else ""
    save_float_count(db, HOTEL_ID, hid, denoms, diff_reason=diff_reason, operator_id=1)
    assets = [{"id": a["id"], "actual_qty": int(a.get("expected_qty") or 0), "diff_reason": ""} for a in ws["assets"]]
    save_asset_count(db, HOTEL_ID, hid, assets, operator_id=1)


def _full_takeover(db, hid: int) -> None:
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
    confirm_takeover_matters(db, HOTEL_ID, hid, operator_id=1)


class HandoverExtraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_shift_handover_schema(engine)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _hid(self) -> int:
        return build_workspace(self.db, HOTEL_ID, 1)["handover_id"]

    def test_ho10_asset_count_persists_and_matches_supplies(self):
        """HO-10 实物盘库持久化，应有数=supplies.current_stock"""
        hid = self._hid()
        ws = build_workspace(self.db, HOTEL_ID, 1)
        supplies = {s.id: s for s in self.db.query(Supply).filter_by(hotel_id=HOTEL_ID).all()}
        assets_payload = []
        for a in ws["assets"]:
            qty = int(a.get("expected_qty") or 0)
            assets_payload.append({"id": a["id"], "actual_qty": qty, "diff_reason": ""})
        save_asset_count(self.db, HOTEL_ID, hid, assets_payload, operator_id=1)
        row = self.db.get(ShiftHandover, hid)
        self.assertTrue(row.assets_confirmed)
        for a in self.db.query(ShiftAssetCount).filter_by(handover_id=hid).all():
            if a.asset_name == "万能房卡":
                rooms = self.db.query(Room).filter_by(hotel_id=HOTEL_ID).count()
                expected = min(4, max(1, rooms // 30)) if rooms else 0
                self.assertEqual(a.expected_qty, expected)
            elif a.supply_id:
                sup = supplies.get(a.supply_id)
                self.assertIsNotNone(sup)
                self.assertEqual(a.expected_qty, int(float(sup.current_stock or 0)))

    def test_ho11_outgoing_sign_requires_float_and_assets(self):
        """HO-11 未完成盘库不能交班签字"""
        hid = self._hid()
        row = self.db.get(ShiftHandover, hid)
        row.float_confirmed = False
        row.assets_confirmed = False
        self.db.commit()
        with self.assertRaises(BusinessError) as ctx:
            sign_handover(self.db, HOTEL_ID, hid, "outgoing", 1)
        self.assertIn("备用金", str(ctx.exception))

    def test_ho12_outgoing_sign_sets_pending_acknowledgment(self):
        """HO-12 交班人签字 → pending_acknowledgment"""
        hid = self._hid()
        _confirm_handover_money_assets(self.db, hid)
        sign_handover(self.db, HOTEL_ID, hid, "outgoing", 1)
        row = self.db.get(ShiftHandover, hid)
        self.assertIsNotNone(row.outgoing_signed_at)
        self.assertEqual(row.status, "pending_acknowledgment")

    def test_ho13_float_short_requires_reason(self):
        """HO-13 备用金短款须填原因"""
        hid = self._hid()
        ws = build_workspace(self.db, HOTEL_ID, 1)
        denoms = [{"denom": d["denom"], "actual_qty": 0} for d in ws["float"]["denominations"]]
        with self.assertRaises(BusinessError):
            save_float_count(self.db, HOTEL_ID, hid, denoms, diff_reason="", operator_id=1)

    def test_ho14_asset_diff_requires_reason(self):
        """HO-14 实物差异须填原因"""
        hid = self._hid()
        ws = build_workspace(self.db, HOTEL_ID, 1)
        a0 = ws["assets"][0]
        with self.assertRaises(BusinessError):
            save_asset_count(
                self.db,
                HOTEL_ID,
                hid,
                [{"id": a0["id"], "actual_qty": max(0, int(a0["expected_qty"]) - 1), "diff_reason": ""}],
                operator_id=1,
            )


class TakeoverExtraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_shift_handover_schema(engine)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _prepare(self) -> int:
        hid = build_workspace(self.db, HOTEL_ID, 1)["handover_id"]
        _confirm_handover_money_assets(self.db, hid)
        sign_handover(self.db, HOTEL_ID, hid, "outgoing", 1)
        row = self.db.get(ShiftHandover, hid)
        _reset_takeover_state(self.db, row)
        return hid

    def test_tk08_revenue_deposit_ack_persist(self):
        """TK-08 营收/押金确认写入数据库"""
        hid = self._prepare()
        ack_takeover_revenue(self.db, HOTEL_ID, hid, ok=True, operator_id=1)
        ack_takeover_deposit(self.db, HOTEL_ID, hid, ok=True, operator_id=1)
        row = self.db.get(ShiftHandover, hid)
        self.assertTrue(row.received_revenue_ok)
        self.assertTrue(row.deposit_ack)
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws["revenue"]["acknowledged"])
        self.assertTrue(ws["deposit"]["acknowledged"])

    def test_tk09_asset_mismatch_requires_ack(self):
        """TK-09 实物复点不符须勾选差异已知晓"""
        hid = self._prepare()
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        a0 = ws["assets"][0]
        out_qty = int(a0["outgoing_qty"] or 0)
        all_assets = [
            {"id": a["id"], "received_qty": int(a["outgoing_qty"] or 0), "received_ack": False} for a in ws["assets"]
        ]
        all_assets[0] = {"id": a0["id"], "received_qty": max(0, out_qty - 1), "received_ack": False}
        with self.assertRaises(BusinessError):
            save_takeover_asset_recount(self.db, HOTEL_ID, hid, all_assets, confirm=True, operator_id=1)
        all_assets[0]["received_ack"] = True
        save_takeover_asset_recount(self.db, HOTEL_ID, hid, all_assets, confirm=True, operator_id=1)
        row = self.db.get(ShiftHandover, hid)
        self.assertTrue(row.assets_received_confirmed)

    def test_tk10_cannot_sign_before_full_prep(self):
        """TK-10 未完成复核不能签字"""
        hid = self._prepare()
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertFalse(ws["flags"]["can_sign"])
        with self.assertRaises(BusinessError):
            sign_takeover_receive(self.db, HOTEL_ID, hid, incoming_user_id=1, operator_id=1)

    def test_tk11_guest_task_progress(self):
        """TK-11 客情/待办认领进度"""
        hid = self._prepare()
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        if ws["guest_progress"]["total"]:
            ack_takeover_guest(self.db, HOTEL_ID, hid, keys=[ws["guest_situations"][0]["key"]], operator_id=1)
            ws2 = build_takeover_workspace(self.db, HOTEL_ID, 1)
            self.assertGreaterEqual(ws2["guest_progress"]["done"], 1)
        if ws["task_progress"]["total"]:
            claim_takeover_task(self.db, HOTEL_ID, hid, task_index=0, action="claimed", operator_id=1)
            ws3 = build_takeover_workspace(self.db, HOTEL_ID, 1)
            self.assertGreaterEqual(ws3["task_progress"]["done"], 1)

    def test_tk12_diff_report_triggers_manager(self):
        """TK-12 差异上报触发店长审核"""
        hid = self._prepare()
        ws = build_takeover_workspace(self.db, HOTEL_ID, 1)
        report_receive_diff(
            self.db,
            HOTEL_ID,
            hid,
            item_type="float",
            item_key="total",
            declared_val=ws["float"]["outgoing_actual"],
            received_val=ws["float"]["outgoing_actual"] - 10,
            reason="自动化测试：重盘少十元",
            operator_id=1,
        )
        ws2 = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(ws2["signatures"]["manager_required"])
        self.assertGreaterEqual(len(ws2.get("receive_diffs") or []), 1)


class ShiftFlowE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_shift_handover_schema(engine)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        cls.db = SessionLocal()
        ensure_float_carry_2000(cls.db, HOTEL_ID)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_e2e01_full_handover_takeover_archive(self):
        """E2E-01 交班→接班→归档闭环"""
        hid = build_workspace(self.db, HOTEL_ID, 1)["handover_id"]
        _confirm_handover_money_assets(self.db, hid)
        sign_handover(self.db, HOTEL_ID, hid, "outgoing", 1)
        row = self.db.get(ShiftHandover, hid)
        _reset_takeover_state(self.db, row)

        tw = build_takeover_workspace(self.db, HOTEL_ID, 1)
        self.assertTrue(tw["ready"])

        _full_takeover(self.db, hid)
        sign_takeover_receive(self.db, HOTEL_ID, hid, incoming_user_id=1, operator_id=1)

        row = self.db.get(ShiftHandover, hid)
        self.assertIsNotNone(row.incoming_signed_at)
        self.assertIn(row.status, ("signed", "manager_review"))

        if not row.manager_required:
            complete_takeover_receive(self.db, HOTEL_ID, hid, operator_id=1)
            row = self.db.get(ShiftHandover, hid)
            self.assertEqual(row.status, "archived")
            self.assertIsNotNone(row.archived_at)

    def test_e2e02_complete_requires_both_signatures(self):
        """E2E-01b 仅交班签字不能归档"""
        hid = build_workspace(self.db, HOTEL_ID, 1)["handover_id"]
        _confirm_handover_money_assets(self.db, hid)
        sign_handover(self.db, HOTEL_ID, hid, "outgoing", 1)
        with self.assertRaises(BusinessError):
            complete_handover(self.db, HOTEL_ID, hid, operator_id=1)


class ShiftFlowHttpTests(unittest.TestCase):
    def test_ho15_http_float_and_asset_count(self):
        """HO-15 HTTP 盘库接口"""
        if not _auth_token():
            self.skipTest("API 未启动")
        code, res = _http("GET", f"/api/finance/shift-handover/workspace?hotel_id={HOTEL_ID}")
        self.assertEqual(code, 200)
        ws = res.get("data") or res
        hid = ws["handover_id"]
        denoms = [
            {"denom": d["denom"], "actual_qty": int(d.get("expected_qty") or 0)} for d in ws["float"]["denominations"]
        ]
        expected = float(ws["float"]["expected"])
        actual_sum = sum(float(d["denom"]) * int(d["actual_qty"]) for d in denoms)
        diff_reason = "自动化测试面额取整差异" if abs(actual_sum - expected) >= 0.01 else ""
        code2, res2 = _http(
            "POST",
            f"/api/finance/shift-handover/{hid}/float-count?hotel_id={HOTEL_ID}",
            {"denominations": denoms, "diff_reason": diff_reason},
        )
        self.assertEqual(code2, 200, msg=str(res2))
        assets = [
            {"id": a["id"], "actual_qty": int(a.get("expected_qty") or 0), "diff_reason": ""} for a in ws["assets"]
        ]
        code3, res3 = _http(
            "POST",
            f"/api/finance/shift-handover/{hid}/asset-count?hotel_id={HOTEL_ID}",
            {"assets": assets},
        )
        self.assertEqual(code3, 200, msg=str(res3))

    def test_tk13_http_takeover_acks(self):
        """TK-13 HTTP 接班确认接口"""
        if not _auth_token():
            self.skipTest("API 未启动")
        code, res = _http("GET", f"/api/finance/shift-handover/takeover/workspace?hotel_id={HOTEL_ID}")
        if code == 404:
            self.skipTest("接班 API 不可用")
        self.assertEqual(code, 200)
        tw = res.get("data") or res
        if not tw.get("ready"):
            self.skipTest("当前无待接班单，跳过 HTTP 接班操作测试")
        hid = tw["handover_id"]
        code2, _ = _http(
            "POST", f"/api/finance/shift-handover/{hid}/takeover/revenue-ack?hotel_id={HOTEL_ID}", {"ok": True}
        )
        self.assertEqual(code2, 200)
        code3, _ = _http(
            "POST", f"/api/finance/shift-handover/{hid}/takeover/deposit-ack?hotel_id={HOTEL_ID}", {"ok": True}
        )
        self.assertEqual(code3, 200)

    def test_e2e02_http_both_workspaces(self):
        """E2E-02 HTTP 交班/接班工作台"""
        if not _auth_token():
            self.skipTest("API 未启动")
        c1, r1 = _http("GET", f"/api/finance/shift-handover/workspace?hotel_id={HOTEL_ID}")
        c2, r2 = _http("GET", f"/api/finance/shift-handover/takeover/workspace?hotel_id={HOTEL_ID}")
        self.assertEqual(c1, 200)
        self.assertIn(c2, (200, 404))
        if c2 == 200:
            d2 = r2.get("data") or r2
            self.assertIn("ready", d2)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
