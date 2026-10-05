# SPDX-License-Identifier: Apache-2.0
"""退款用例冒烟：灌种子 + HTTP 逐项验证。

用法（在 src 目录）:
  python scripts/smoke_refund_cases.py
"""

from __future__ import annotations

import json
import sys
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

import httpx

from bootstrap.ensure_refund_adjust import (
    REFUND_CASE_ORDERS,
    REFUND_CASE_PHONE,
    REFUND_CASE_ROOM,
    seed_refund_cases_demo,
)
from database import SessionLocal

BASE = "http://127.0.0.1:8000"
HOTEL = 1


def login(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE}/api/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    token = (data.get("data") or data).get("access_token")
    if not token:
        raise RuntimeError(f"login failed: {data}")
    return token


def get(client: httpx.Client, path: str, **params: Any) -> dict:
    r = client.get(f"{BASE}{path}", params={"hotel_id": HOTEL, **params}, timeout=30)
    body = r.json() if r.content else {}
    return {"status": r.status_code, "ok": r.status_code < 400, "body": body, "raw": r}


def post(client: httpx.Client, path: str, payload: dict) -> dict:
    r = client.post(
        f"{BASE}{path}",
        params={"hotel_id": HOTEL},
        json=payload,
        timeout=30,
    )
    body = r.json() if r.content else {}
    return {"status": r.status_code, "ok": r.status_code < 400, "body": body}


def data_of(res: dict) -> Any:
    body = res.get("body") or {}
    return body.get("data", body)


def main() -> int:
    db = SessionLocal()
    try:
        seed = seed_refund_cases_demo(db, hotel_id=HOTEL, force=False)
        print("SEED:", json.dumps(seed, ensure_ascii=False))
    finally:
        db.close()

    results: list[tuple[str, bool, str]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append((name, cond, detail))
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    with httpx.Client() as client:
        token = login(client)
        client.headers["Authorization"] = f"Bearer {token}"

        # —— UC-A1 手机号优先找客 ——
        print("\n== UC-A1 手机号优先 ==")
        r = get(client, "/api/refund-adjust/lookup-by-phone", phone=REFUND_CASE_PHONE)
        d = data_of(r)
        check("接口 200", r["ok"], f"status={r['status']}")
        check("matched", bool(d.get("matched")), str(d.get("hint") or ""))
        orders = d.get("orders") or []
        nos = {o.get("order_no") for o in orders}
        check("含微信可退单 RF-WX-001", REFUND_CASE_ORDERS["wx"] in nos, f"orders={sorted(nos)}")
        check("含支付宝可退单 RF-ALI-002", REFUND_CASE_ORDERS["ali"] in nos, f"count={len(orders)}")
        check("不含已全额退 RF-FULL-003", REFUND_CASE_ORDERS["full"] not in nos)
        check("不含已取消 RF-CANCEL-004", REFUND_CASE_ORDERS["cancel"] not in nos)

        guest = d.get("guest") or {}
        check(
            "认人：脱敏名/手机掩码",
            bool(guest.get("name_masked") or guest.get("name")) and bool(guest.get("phone_mask")),
            f"name={guest.get('name_masked') or guest.get('name')} phone={guest.get('phone_mask')}",
        )

        # —— UC-A2/A3 选单详情 + 原路锁定 ——
        print("\n== UC-A2/A3 认人区 + 原路锁定 ==")
        wx = next((o for o in orders if o.get("order_no") == REFUND_CASE_ORDERS["wx"]), None)
        oid = wx["order_id"] if wx else None
        check("拿到微信单 order_id", oid is not None, str(oid))
        detail = data_of(get(client, "/api/refund-adjust/order-detail", order_id=oid)) if oid else {}
        lock = detail.get("payment_lock") or {}
        check("脱敏姓名", bool(detail.get("guest_name_masked")), str(detail.get("guest_name_masked")))
        check("房号", detail.get("room_no") == REFUND_CASE_ROOM, str(detail.get("room_no")))
        check("住期", bool(detail.get("check_in")) and bool(detail.get("check_out")))
        check("已收金额", float(detail.get("received_yuan") or 0) > 0, str(detail.get("received_yuan")))
        check("口头核验 hint", "口头核验" in str(detail.get("confirm_hint") or ""))
        check("payment_lock.locked", lock.get("locked") is True)
        check("渠道=微信", "wechat" in str(lock.get("pay_channel") or ""), str(lock.get("pay_channel")))
        check(
            "transaction_id 锁定",
            lock.get("transaction_id") == "WX20260831RF001",
            str(lock.get("transaction_id")),
        )
        check("允许现金特批例外", lock.get("allow_cash_special") is True)
        lines = detail.get("lines") or []
        check("分录可勾选", len(lines) >= 1, f"lines={len(lines)}")

        # —— UC-A4 订单号 / 房号边角 ——
        print("\n== UC-A4 订单号/房号边角 ==")
        by_no = data_of(get(client, "/api/refund-adjust/lookup-order", q=REFUND_CASE_ORDERS["ali"]))
        check(
            "订单号定位支付宝单",
            by_no.get("order_no") == REFUND_CASE_ORDERS["ali"]
            and "alipay" in str((by_no.get("payment_lock") or {}).get("pay_channel") or ""),
            f"ch={(by_no.get('payment_lock') or {}).get('pay_channel')}",
        )
        by_room = data_of(get(client, "/api/refund-adjust/lookup-order", q=REFUND_CASE_ROOM))
        check(
            "房号定位微信单",
            by_room.get("order_no") == REFUND_CASE_ORDERS["wx"],
            f"order={by_room.get('order_no')}",
        )

        # —— UC-C 工单点入 ——
        print("\n== UC-C 待办工单点入 ==")
        board = data_of(get(client, "/api/refund-adjust/board"))
        pending = board.get("my_pending") or board.get("tickets") or []
        linked = next(
            (
                t
                for t in pending
                if t.get("order_id") == oid or t.get("order_no") in (REFUND_CASE_ORDERS["wx"], "No.8821")
            ),
            None,
        )
        check("看板有退款待办", linked is not None, f"pending={len(pending)}")
        if linked and linked.get("order_id"):
            from_ticket = data_of(get(client, "/api/refund-adjust/order-detail", order_id=linked["order_id"]))
            check(
                "工单 order_id 可载入源单",
                from_ticket.get("order_id") == linked["order_id"]
                and bool((from_ticket.get("payment_lock") or {}).get("locked")),
                f"ticket={linked.get('ticket_no')}",
            )
        else:
            check("工单 order_id 可载入源单", False, "待办未绑定 order_id")

        # —— UC-D 兼容 No.8821 ——
        print("\n== UC-D No.8821 定位 ==")
        demo = data_of(get(client, "/api/refund-adjust/lookup-order", q="No.8821"))
        # 若已绑定真实单则走真实；否则 demo fallback
        demo_ok = bool(demo.get("payment_lock")) and (
            demo.get("demo") or demo.get("order_no") in (REFUND_CASE_ORDERS["wx"], "No.8821")
        )
        check("No.8821 可定位", demo_ok, f"order={demo.get('order_no')} demo={demo.get('demo')}")

        # —— UC-S 提交校验 ——
        print("\n== UC-S 提交校验 ==")
        base_payload = {
            "order_id": oid,
            "order_no": REFUND_CASE_ORDERS["wx"],
            "guest_name_masked": detail.get("guest_name_masked") or "王**",
            "lines": [{"id": lines[0]["id"], "label": lines[0]["label"], "amount_yuan": 50, "checked": True}]
            if lines
            else [{"id": "ALL", "label": "测试", "amount_yuan": 50, "checked": True}],
            "fee_yuan": 0,
            "reason": "用例冒烟原路退",
            "payment_lock": lock,
            "refund_mode": "original",
            "face_confirmed": True,
        }

        no_face = post(
            client,
            "/api/refund-adjust/refund",
            {**base_payload, "face_confirmed": False},
        )
        check("未当面核验 → 拒绝", not no_face["ok"], f"status={no_face['status']}")

        no_lock = post(
            client,
            "/api/refund-adjust/refund",
            {**base_payload, "payment_lock": {}},
        )
        check("缺原路锁定 → 拒绝", not no_lock["ok"], f"status={no_lock['status']}")

        cash_no = post(
            client,
            "/api/refund-adjust/refund",
            {
                **base_payload,
                "refund_mode": "cash_special",
                "special_approval": False,
                "reason": "现金特批无审批",
            },
        )
        check("现金特批无勾选 → 拒绝", not cash_no["ok"], f"status={cash_no['status']}")

        ok_orig = post(client, "/api/refund-adjust/refund", base_payload)
        td = data_of(ok_orig)
        method = (td.get("ticket") or {}).get("refund_method") or ""
        check(
            "原路退提交成功",
            ok_orig["ok"] and method.startswith("original:"),
            f"method={method} msg={td.get('message')}",
        )

        ok_cash = post(
            client,
            "/api/refund-adjust/refund",
            {
                **base_payload,
                "refund_mode": "cash_special",
                "special_approval": True,
                "reason": "现金特批已审批",
                "lines": [
                    {
                        "id": "CASH1",
                        "label": "特批小额",
                        "amount_yuan": 30,
                        "checked": True,
                    }
                ],
            },
        )
        td2 = data_of(ok_cash)
        check(
            "现金特批+审批 → 成功",
            ok_cash["ok"] and (td2.get("ticket") or {}).get("refund_method") == "cash_special",
            f"need_auth={td2.get('need_manager_auth')}",
        )

        # 全额退订单详情应失败
        from models import Order

        db2 = SessionLocal()
        try:
            fo = db2.query(Order).filter_by(hotel_id=HOTEL, order_no=REFUND_CASE_ORDERS["full"]).first()
            full_id = fo.id if fo else None
        finally:
            db2.close()
        if full_id:
            full_res = get(client, "/api/refund-adjust/order-detail", order_id=full_id)
            check(
                "已全额退详情不可退",
                not full_res["ok"],
                f"status={full_res['status']}",
            )
        else:
            check("已全额退详情不可退", False, "未找到 RF-FULL-003")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n======= 结果: {passed} PASS / {failed} FAIL / {len(results)} TOTAL =======")
    if failed:
        print("失败项:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
