# SPDX-License-Identifier: Apache-2.0
"""价格助手 · 测试用例（service 层 + HTTP 路由层）

运行: pytest src/tests/test_pricing.py -v

用例清单
--------
Service 层：
  PRC-S01  get_config_dict 返回 hotel_id / params / commission
  PRC-S02  update_config 持久化 params
  PRC-S03  update_config 红线：ev_cap 不可超过 100
  PRC-S04  update_config 红线：档位锚点不可超过 ev_cap
  PRC-S05  update_config 拒绝非法 agg 档
  PRC-S06  list_events 默认含 inactive；只 active 时不含
  PRC-S07  list_competitor_sets 在空数据下返回 []

路由层（需后端 8081）：
  PRC-H01  GET /pricing-assistant/config 200 + 包含 params
  PRC-H02  GET /pricing-assistant/calendar 200 + 含 days 天的 day[]
  PRC-H03  GET /pricing-assistant/events?include_inactive=true 200
  PRC-H04  GET /pricing-assistant/competitor-sets 200
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


class PricingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_s01_get_config_dict(self):
        """PRC-S01：get_config_dict 返回结构完整。"""
        from pricing.pricing_assistant import get_config_dict

        cfg = get_config_dict(self.db, HOTEL_ID)
        self.assertEqual(cfg["hotel_id"], HOTEL_ID)
        self.assertIn("params", cfg)
        self.assertIn("commission", cfg)
        # 红线值：ev_cap=100
        self.assertEqual(cfg["params"]["ev_cap"], 100)

    def test_s02_update_config_persists(self):
        """PRC-S02：update_config 写入 params_json 持久化。"""
        from pricing.pricing_assistant import get_config_dict, update_config

        before = get_config_dict(self.db, HOTEL_ID)
        # 设置新 params
        new_agg = "conservative" if before["params"].get("agg") != "conservative" else "balanced"
        update_config(self.db, HOTEL_ID, {"params": {"agg": new_agg}})
        self.db.commit()

        after = get_config_dict(self.db, HOTEL_ID)
        self.assertEqual(after["params"]["agg"], new_agg)

    def test_s03_update_config_ev_cap_redline(self):
        """PRC-S03：ev_cap 红线：尝试设 999 应被夹到 100。"""
        from pricing.pricing_assistant import get_config_dict, update_config

        update_config(self.db, HOTEL_ID, {"params": {"ev_cap": 999.0}})
        self.db.commit()
        cfg = get_config_dict(self.db, HOTEL_ID)
        self.assertEqual(cfg["params"]["ev_cap"], 100, "ev_cap 应被夹回硬上限 100")

    def test_s04_update_config_anchor_redline(self):
        """PRC-S04：档位锚点 ev_strong 不可超过 ev_cap。"""
        from pricing.pricing_assistant import get_config_dict, update_config

        update_config(self.db, HOTEL_ID, {"params": {"ev_strong": 999.0}})
        self.db.commit()
        cfg = get_config_dict(self.db, HOTEL_ID)
        self.assertLessEqual(cfg["params"]["ev_strong"], 100)

    def test_s05_update_config_rejects_bad_agg(self):
        """PRC-S05：非法 agg 档抛 400。"""
        from fastapi import HTTPException

        from pricing.pricing_assistant import update_config

        with self.assertRaises(BusinessError) as ctx:
            update_config(self.db, HOTEL_ID, {"params": {"agg": "wild"}})
        self.assertEqual(ctx.exception.http_status, 400)

    def test_s06_list_events_include_inactive(self):
        """PRC-S06：list_events 默认含 inactive；include_inactive=False 只返 active。"""
        from datetime import datetime, timedelta

        from models import EventCalendar
        from pricing.pricing_assistant import list_events

        now = datetime.now()
        # 灌一个 active + 一个 inactive 事件（幂等：先清掉本测试数据）
        self.db.query(EventCalendar).filter(
            EventCalendar.hotel_id == HOTEL_ID,
            EventCalendar.event_name.in_(["自动化测试-active-事件", "自动化测试-inactive-事件"]),
        ).delete()
        self.db.commit()
        self.db.add(
            EventCalendar(
                hotel_id=HOTEL_ID,
                event_id="EV-TEST-ACTIVE",
                event_name="自动化测试-active-事件",
                event_type="holiday",
                start_at=now,
                end_at=now + timedelta(days=1),
                intensity="中",
                is_active=True,
            )
        )
        self.db.add(
            EventCalendar(
                hotel_id=HOTEL_ID,
                event_id="EV-TEST-INACTIVE",
                event_name="自动化测试-inactive-事件",
                event_type="holiday",
                start_at=now,
                end_at=now + timedelta(days=1),
                intensity="中",
                is_active=False,
            )
        )
        self.db.commit()

        all_events = list_events(self.db, HOTEL_ID, include_inactive=True)
        active_events = list_events(self.db, HOTEL_ID, include_inactive=False)
        all_names = {e.get("event_name") or e.get("name") for e in all_events}
        active_names = {e.get("event_name") or e.get("name") for e in active_events}
        self.assertIn("自动化测试-active-事件", all_names)
        self.assertIn("自动化测试-inactive-事件", all_names)
        self.assertIn("自动化测试-active-事件", active_names)
        self.assertNotIn("自动化测试-inactive-事件", active_names)

        # 清理
        self.db.query(EventCalendar).filter(
            EventCalendar.hotel_id == HOTEL_ID,
            EventCalendar.event_name.in_(["自动化测试-active-事件", "自动化测试-inactive-事件"]),
        ).delete()
        self.db.commit()

    def test_s07_list_competitor_sets_empty(self):
        """PRC-S07：空数据下 list_competitor_sets 返回 []。"""
        from pricing.pricing_assistant import list_competitor_sets

        sets = list_competitor_sets(self.db, HOTEL_ID)
        self.assertIsInstance(sets, list)


class PricingHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_up = _ensure_auth_token()

    def _skip_if_down(self):
        if not self.server_up:
            self.skipTest("后端未启动 (8081)")

    def test_h01_config(self):
        """PRC-H01：/pricing-assistant/config 返回结构完整。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/pricing-assistant/config?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertEqual(data["hotel_id"], HOTEL_ID)
        self.assertIn("params", data)
        self.assertEqual(data["params"]["ev_cap"], 100)

    def test_h02_calendar(self):
        """PRC-H02：/pricing-assistant/calendar?days=30 返回 30 天日历。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/pricing-assistant/calendar?hotel_id={HOTEL_ID}&days=30")
        self.assertTrue(res.get("ok"), res.get("detail") or res)
        data = res["data"]
        self.assertIn("days", data)
        self.assertEqual(data["days"], 30)

    def test_h03_events(self):
        """PRC-H03：/pricing-assistant/events?include_inactive=true 200。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/pricing-assistant/events?hotel_id={HOTEL_ID}&include_inactive=true")
        self.assertTrue(res.get("ok"), res.get("detail") or res)

    def test_h04_competitor_sets(self):
        """PRC-H04：/pricing-assistant/competitor-sets 200。"""
        self._skip_if_down()
        res = _http("GET", f"/api/v1/pricing-assistant/competitor-sets?hotel_id={HOTEL_ID}")
        self.assertTrue(res.get("ok"), res.get("detail") or res)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(PricingServiceTests))
    suite.addTests(loader.loadTestsFromTestCase(PricingHttpTests))
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
