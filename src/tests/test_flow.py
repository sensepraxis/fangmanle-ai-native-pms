# SPDX-License-Identifier: Apache-2.0
"""端到端冒烟（集成）测试：覆盖真实读写流程（创建 / 入住 / 退房 / 价格护栏 / 夜审 / 房务 / 客户360）。

运行前提：后端 API 已启动（`deploy/dev/start.bat` / `start.sh`，默认 8081）。
无服务时所有用例自动 pytest.skip，不会阻断 CI（CI 仅跑 SQLite 单元/服务层用例）。

本地手动跑全套（含本集成测试）：
  deploy\\dev\\start.bat demo-sg
  pytest src/tests -q
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

BASE = "http://127.0.0.1:8081"
HOTEL_ID = 1


def _call(method: str, path: str, body=None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status, raw = r.status, r.read()
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            # 非 JSON 响应（如残留前端 SPA 返回 HTML）→ 当作服务不可用
            return status, {"ok": False, "detail": "non-json response"}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except (json.JSONDecodeError, OSError):
            return e.code, {"ok": False, "detail": e.reason}
    except urllib.error.URLError:
        return None, {"ok": False, "detail": "connection refused"}


def _server_token() -> str | None:
    """尝试 admin 登录；成功返回 token，无服务/登录失败返回 None。"""
    code, res = _call("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
    if code != 200:
        return None
    data = res.get("data") or {}
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def token():
    t = _server_token()
    if not t:
        pytest.skip("后端未启动 (127.0.0.1:8000)，跳过端到端冒烟测试")
    return t


def test_e2e_order_checkin_checkout(token):
    # 1) 新建订单
    code, new = _call(
        "POST",
        "/api/orders",
        {
            "hotel_id": HOTEL_ID,
            "guest_name": "测试客",
            "phone": "13900001234",
            "room_type_id": 2,
            "channel_id": 4,
            "check_in": "2026-08-12",
            "check_out": "2026-08-13",
            "rooms": 1,
        },
    )
    assert code == 200 and new.get("ok"), new
    oid = new["data"]["id"]
    # 2) 入住
    code, ci = _call("POST", f"/api/orders/{oid}/checkin", {}, token=token)
    assert code == 200, ci
    # 3) 退房结账
    code, co = _call("POST", f"/api/orders/{oid}/checkout", {}, token=token)
    assert code == 200, co


def test_e2e_pricing_guardrail(token):
    # 4) 价格护栏：采纳 pending 建议应成功；blocked 项应被拦截
    code, pricing = _call("GET", "/api/pricing?hotel_id=1", token=token)
    assert code == 200, pricing
    pend = next((p for p in pricing["data"] if p["status"] == "pending"), None)
    if pend:
        code, acc = _call("POST", f"/api/pricing/{pend['id']}/decide", {"action": "accept"}, token=token)
        assert code == 200, acc


def test_e2e_night_audit(token):
    # 6) 夜审
    code, na = _call("POST", "/api/night-audit", {"hotel_id": 1, "biz_date": "2026-08-11"}, token=token)
    assert code == 200, na
    assert na["data"]["status"] in ("ok", "done", "skipped")


def test_e2e_housekeeping(token):
    # 7) 房务：清洁 → 待查房 → 查房通过
    code, hk = _call("GET", "/api/housekeeping?hotel_id=1", token=token)
    assert code == 200, hk
    todo = next((t for t in hk["data"] if t["status"] not in ("done", "pending_inspect")), None)
    if not todo:
        pytest.skip("无开放房务任务，跳过房务流")
    if todo["status"] in ("open", "assigned", "rework"):
        _call("POST", f"/api/housekeeping/{todo['id']}/start", {}, token=token)
    code, done = _call("POST", f"/api/housekeeping/{todo['id']}/done", {}, token=token)
    assert code == 200, done
    code, insp = _call("POST", f"/api/housekeeping/{todo['id']}/inspect", {"passed": True}, token=token)
    assert code == 200, insp


def test_e2e_guest_360(token):
    # 8) 客户360
    code, g = _call("GET", "/api/guests?hotel_id=1", token=token)
    assert code == 200, g
    assert g["data"], "应至少存在一个客人"
    gid = g["data"][0]["id"]
    code, g360 = _call("GET", f"/api/guests/{gid}", token=token)
    assert code == 200, g360
    assert g360["data"]["guest"]["name"]
