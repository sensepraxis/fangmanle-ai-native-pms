# SPDX-License-Identifier: Apache-2.0
"""
会员体系 + 积分规则 + 客户360私域资产 · 测试用例

运行（在 src 目录或项目根，PYTHONPATH 含 src）:
  python test_mkt_member_system.py
  python -m unittest test_mkt_member_system -v

用例编号 | 场景 | 预期
--------|------|------
TC-M01 | 种子后至少 5 级 | silver~supreme 齐全，含 upgrade_points
TC-M02 | 更新等级成长值 | PUT 后读回一致，不影响其他等级
TC-M03 | 权益装配 | 按 level 写 benefits，读回 on/value
TC-M04 | 升降级规则读写 | demote_protect_days 等可保存
TC-M05 | 储值档位 CRUD | 新建/更新/列表含 gift_points
TC-M06 | 积分规则分组字段 | base_rate / points_per_yuan / 倍率矩阵 / 失效
TC-M07 | 试算·生日入住 | BIRTHDAY_5X 金卡 total_delta > 0 且含生日行
TC-M08 | 试算·退款冲销 | REFUND total_delta < 0
TC-M09 | 试算·上限钳制 | 大额消费不超 single_order_cap
TC-M10 | bundle 概览 | members/total_points/levels 完整
TC-G01 | 客户360 h5_membership | 有私域等级 + 积分（不含储值）
TC-G02 | 指定客人积分可读 | wallet.points_balance == h5.points_balance
TC-H01 | HTTP members bundle | 200 + levels≥5（需服务已启动）
TC-H02 | HTTP point preview | 200 + total_delta（需服务已启动）
TC-H03 | HTTP guests/:id | h5_membership.points_balance 存在（需服务已启动）
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from bootstrap.ensure_mkt_member_v2 import ensure_member_system_schema, seed_member_system
from database import SessionLocal, engine
from mkt.mkt_member_system import (
    delete_recharge_tier,
    get_level_rule,
    get_point_rule,
    list_levels,
    list_recharge_tiers,
    member_system_bundle,
    preview_points,
    put_benefits,
    save_level_rule,
    save_point_rule,
    upsert_level,
    upsert_recharge_tier,
)
from mkt.mkt_service import get_guest_h5_membership
from models import Guest, MktGuestWallet

HOTEL_ID = 1
BASE = "http://127.0.0.1:8000"
_HTTP_OK = None


def _http_available() -> bool:
    global _HTTP_OK
    if _HTTP_OK is not None:
        return _HTTP_OK
    try:
        with urllib.request.urlopen(BASE + "/api/hotel", timeout=1.5) as resp:
            body = resp.read()
        # 仅当响应为合法 JSON（真实后端）才认为服务可用；残留前端 SPA 返回 HTML
        # 会被判定为不可用，避免本地误判导致 HTTP 用例在非 API 服务上失败。
        json.loads(body)
        _HTTP_OK = True
    except Exception:
        _HTTP_OK = False
    return _HTTP_OK


def http_call(method: str, path: str, body=None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"ok": False, "detail": str(e)}


def _login_token() -> str | None:
    """尝试账号登录；失败则返回 None（部分接口可能仍可匿名）。"""
    for payload in (
        {"username": "admin", "password": "admin123"},
        {"username": "demo", "password": "demo"},
        {"phone": "13800000000", "password": "123456"},
    ):
        for path in ("/api/auth/login", "/api/login"):
            try:
                r = http_call("POST", path, payload)
                if r.get("ok") and isinstance(r.get("data"), dict):
                    t = r["data"].get("token") or r["data"].get("access_token")
                    if t:
                        return t
            except Exception:
                pass
    return None


class MemberSystemUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_member_system_schema(engine)
        db = SessionLocal()
        try:
            seed_member_system(db, HOTEL_ID)
            db.commit()
        finally:
            db.close()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # ----- TC-M01 -----
    def test_M01_seed_five_levels(self):
        levels = list_levels(self.db, HOTEL_ID)
        codes = {l["level_code"] for l in levels}
        for c in ("silver", "gold", "platinum", "diamond", "supreme"):
            self.assertIn(c, codes, f"缺少等级 {c}")
        supreme = next(l for l in levels if l["level_code"] == "supreme")
        self.assertGreaterEqual(int(supreme["upgrade_points"]), 1000)
        self.assertIsInstance(supreme.get("benefits"), dict)

    # ----- TC-M02 -----
    def test_M02_update_level_growth(self):
        gold = next(l for l in list_levels(self.db, HOTEL_ID) if l["level_code"] == "gold")
        new_up = int(gold["upgrade_points"]) + 7
        out = upsert_level(
            self.db,
            HOTEL_ID,
            {
                "id": gold["id"],
                "level_code": "gold",
                "level_name": gold["level_name"],
                "upgrade_points": new_up,
                "retain_points": gold["retain_points"],
                "valid_months": gold["valid_months"],
                "sort_order": gold["sort_order"],
                "growth_rule": gold.get("growth_rule") or {},
                "benefits": gold.get("benefits") or {},
            },
        )
        self.assertEqual(out["upgrade_points"], new_up)
        # 恢复，避免污染后续
        upsert_level(
            self.db,
            HOTEL_ID,
            {
                "id": gold["id"],
                "level_code": "gold",
                "level_name": gold["level_name"],
                "upgrade_points": gold["upgrade_points"],
                "retain_points": gold["retain_points"],
                "valid_months": gold["valid_months"],
                "sort_order": gold["sort_order"],
                "benefits": gold.get("benefits") or {},
            },
        )

    # ----- TC-M03 -----
    def test_M03_benefits_put(self):
        payload = {
            "level_code": "gold",
            "benefits": {
                "discount_rate": {"on": True, "value": 0.98},
                "free_breakfast": {"on": True, "value": 1},
                "points_acceleration": {"on": True, "value": 1.5},
            },
        }
        out = put_benefits(self.db, HOTEL_ID, payload)
        gold = next(l for l in out["levels"] if l["level_code"] == "gold")
        self.assertTrue(gold["benefits"]["discount_rate"]["on"])
        self.assertAlmostEqual(float(gold["benefits"]["discount_rate"]["value"]), 0.98)

    # ----- TC-M04 -----
    def test_M04_level_rule_rw(self):
        save_level_rule(
            self.db,
            HOTEL_ID,
            {
                "upgrade_mode": "growth",
                "demote_protect_days": 90,
                "demote_action": "one_level",
                "notify_upgrade": True,
            },
        )
        rule = get_level_rule(self.db, HOTEL_ID)["rule"]
        self.assertEqual(int(rule["demote_protect_days"]), 90)
        self.assertIn("expire_preview", get_level_rule(self.db, HOTEL_ID))

    # ----- TC-M05 -----
    def test_M05_recharge_tier_offline(self):
        self.assertEqual(list_recharge_tiers(self.db, HOTEL_ID), [])
        with self.assertRaises(Exception) as ctx:
            upsert_recharge_tier(
                self.db,
                HOTEL_ID,
                {"tier_name": "测试档", "recharge_amt": 888, "bonus_amt": 88},
            )
        msg = str(getattr(ctx.exception, "detail", None) or ctx.exception)
        self.assertIn("下线", msg)

    # ----- TC-M06 -----
    def test_M06_point_rule_fields(self):
        save_point_rule(
            self.db,
            HOTEL_ID,
            {
                "rule": {
                    "base_rate": 1,
                    "points_per_yuan": 100,
                    "max_deduct_ratio": 0.3,
                    "expire_after_days": 365,
                    "frozen_before_days": 7,
                    "daily_cap": 50000,
                    "single_order_cap": 10000,
                    "level_multipliers": {"gold": 1.5, "silver": 1.0},
                    "birthday_bonus_by_level": {"gold": 8},
                }
            },
        )
        rule = get_point_rule(self.db, HOTEL_ID)["rule"]
        self.assertEqual(float(rule["base_rate"]), 1)
        self.assertEqual(int(rule["points_per_yuan"]), 100)
        self.assertEqual(float(rule["level_multipliers"]["gold"]), 1.5)
        self.assertEqual(int(rule["expire_after_days"]), 365)

    # ----- TC-M07 -----
    def test_M07_preview_birthday(self):
        r = preview_points(
            self.db,
            HOTEL_ID,
            {"customer_id": "c_gold", "scenario": "BIRTHDAY_5X"},
        )
        self.assertGreater(int(r["total_delta"]), 0)
        types = [x.get("type") or x.get("label") for x in r["calc_lines"]]
        joined = " ".join(str(t) for t in types)
        self.assertTrue(
            any("birthday" in str(t).lower() or "生日" in str(t) for t in types) or "生日" in joined,
            f"应含生日加成行: {r['calc_lines']}",
        )

    # ----- TC-M08 -----
    def test_M08_preview_refund(self):
        r = preview_points(self.db, HOTEL_ID, {"customer_id": "c_gold", "scenario": "REFUND"})
        self.assertLess(int(r["total_delta"]), 0)

    # ----- TC-M09 -----
    def test_M09_preview_cap(self):
        # 先把单笔上限设小，再试算大额
        save_point_rule(self.db, HOTEL_ID, {"rule": {"single_order_cap": 5000, "daily_cap": 50000}})
        r = preview_points(
            self.db,
            HOTEL_ID,
            {
                "customer_id": "c_plat",
                "scenario": "HOLIDAY",
                "params": {"amount": 20000, "nights": 3, "is_holiday": True},
            },
        )
        self.assertLessEqual(int(r["total_delta"]), 5000)
        # 恢复默认
        save_point_rule(self.db, HOTEL_ID, {"rule": {"single_order_cap": 10000}})

    # ----- TC-M10 -----
    def test_M10_bundle_overview(self):
        b = member_system_bundle(self.db, HOTEL_ID)
        self.assertGreaterEqual(len(b["levels"]), 5)
        self.assertIn("overview", b)
        self.assertIn("total_points", b["overview"])
        self.assertIn("members", b["overview"])
        self.assertTrue(b.get("scenarios"))
        self.assertTrue(b.get("customers"))


class Guest360PrivatePointsTests(unittest.TestCase):
    """客户360：指定客人的私域积分可读。"""

    @classmethod
    def setUpClass(cls):
        ensure_member_system_schema(engine)
        db = SessionLocal()
        try:
            seed_member_system(db, HOTEL_ID)
            db.commit()
        finally:
            db.close()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _pick_guest_with_wallet(self):
        w = (
            self.db.query(MktGuestWallet)
            .filter_by(hotel_id=HOTEL_ID)
            .order_by(MktGuestWallet.points_balance.desc())
            .first()
        )
        if w:
            return w
        guest = self.db.query(Guest).first()
        if not guest:
            self.skipTest("无客人数据，跳过 360 用例")
        w = MktGuestWallet(
            hotel_id=HOTEL_ID,
            guest_id=guest.id,
            level_code="gold",
            points_balance=2680,
            stored_balance=1280,
            nights_ytd=6,
            spend_ytd=8800,
        )
        self.db.add(w)
        self.db.commit()
        self.db.refresh(w)
        return w

    # ----- TC-G01 -----
    def test_G01_h5_membership_fields(self):
        w = self._pick_guest_with_wallet()
        h5 = get_guest_h5_membership(self.db, HOTEL_ID, w.guest_id, ensure=False)
        self.assertIsNotNone(h5)
        self.assertIn("level_code", h5)
        self.assertIn("points_balance", h5)
        self.assertNotIn("stored_balance", h5)
        self.assertEqual(h5.get("labels", {}).get("points"), "私域积分")

    # ----- TC-G02 -----
    def test_G02_points_match_wallet(self):
        w = self._pick_guest_with_wallet()
        h5 = get_guest_h5_membership(self.db, HOTEL_ID, w.guest_id, ensure=False)
        self.assertEqual(int(h5["points_balance"]), int(w.points_balance or 0))
        guest = self.db.get(Guest, w.guest_id)
        print(
            f"\n  [客户360样例] guest_id={w.guest_id} name={getattr(guest, 'name', None)} "
            f"等级={h5['level_name']} 私域积分={h5['points_balance']}"
        )


@unittest.skipUnless(_http_available(), "后端未启动，跳过 HTTP 用例（先 deploy/dev/start.bat）")
class MemberSystemHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = _login_token()

    def _get(self, path: str):
        return http_call("GET", path, token=self.token)

    def _post(self, path: str, body: dict):
        return http_call("POST", path, body, token=self.token)

    # ----- TC-H01 -----
    def test_H01_members_bundle(self):
        r = self._get(f"/api/mkt/members?hotel_id={HOTEL_ID}")
        self.assertTrue(r.get("ok"), r)
        data = r["data"]
        self.assertGreaterEqual(len(data.get("levels") or []), 5)

    # ----- TC-H02 -----
    def test_H02_point_preview(self):
        r = self._post(
            f"/api/mkt/member/point/preview?hotel_id={HOTEL_ID}",
            {"customer_id": "c_gold", "scenario": "BIRTHDAY_5X"},
        )
        self.assertTrue(r.get("ok"), r)
        self.assertIn("total_delta", r["data"])

    # ----- TC-H03 -----
    def test_H03_guest_360_points(self):
        db = SessionLocal()
        try:
            w = (
                db.query(MktGuestWallet)
                .filter_by(hotel_id=HOTEL_ID)
                .order_by(MktGuestWallet.points_balance.desc())
                .first()
            )
            if not w:
                self.skipTest("无 wallet")
            gid = w.guest_id
            expect_pts = int(w.points_balance or 0)
        finally:
            db.close()
        r = self._get(f"/api/guests/{gid}?hotel_id={HOTEL_ID}")
        self.assertTrue(r.get("ok"), r)
        h5 = (r.get("data") or {}).get("h5_membership")
        self.assertIsNotNone(h5, "客户360应返回 h5_membership")
        self.assertEqual(int(h5.get("points_balance") or 0), expect_pts)
        self.assertNotIn("stored_balance", h5)


def main():
    print("=" * 60)
    print("会员体系 / 积分规则 / 客户360私域积分 · 自动化测试")
    print("=" * 60)
    if not _http_available():
        print("提示: 后端未监听 8000，HTTP 用例将跳过。单元用例仍会执行。")
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("-" * 60)
    print(
        f"结果: ran={result.testsRun} failures={len(result.failures)} "
        f"errors={len(result.errors)} skipped={len(result.skipped)}"
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
