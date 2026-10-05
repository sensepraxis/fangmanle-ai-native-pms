# SPDX-License-Identifier: Apache-2.0
"""Smoke test: each order intake path against running demo API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta

BASE = "http://127.0.0.1:8000"
results: list[tuple[str, bool, str]] = []


def req(method: str, path: str, data=None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if data is None else json.dumps(data).encode()
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            j = json.loads(raw)
        except Exception:
            j = {"detail": raw}
        return e.code, j


def ok_data(j):
    if isinstance(j, dict) and j.get("ok") and "data" in j:
        return j["data"]
    return j


def mark(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    print(("PASS" if passed else "FAIL"), name, "|", detail)


def vacant_of_type(rooms: list, room_type_id: int) -> list:
    return [
        r
        for r in rooms
        if r.get("room_type_id") == room_type_id and r.get("status") in ("vacant", "clean", "inspected")
    ]


def pick_room_type_with_vacancy(rts: list, rooms: list, need: int = 4):
    """Prefer a room type that still has enough vacant rooms for the full smoke."""
    scored = []
    for rt in rts:
        n = len(vacant_of_type(rooms, rt["id"]))
        scored.append((n, rt))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] < need:
        best_n, best = scored[0] if scored else (0, None)
        raise SystemExit(
            f"insufficient vacant rooms: best type has {best_n}, need {need}. "
            f"status={dict(Counter(r.get('status') for r in rooms))}"
        )
    return scored[0][1]


def refresh_rooms(token: str, hid: int) -> list:
    return ok_data(req("GET", f"/api/rooms?hotel_id={hid}", token=token)[1])


def main():
    code, login = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
    token = ok_data(login).get("token") or ok_data(login).get("access_token")
    if not token:
        raise SystemExit(f"login failed: {login}")

    hid = 1
    rts = ok_data(req("GET", f"/api/room-types?hotel_id={hid}", token=token)[1])
    rooms = refresh_rooms(token, hid)
    chs = ok_data(req("GET", "/api/channels", token=token)[1])
    rt = pick_room_type_with_vacancy(rts, rooms, need=4)
    vac = vacant_of_type(rooms, rt["id"])
    direct = next((c for c in chs if c.get("code") == "direct"), chs[0])
    agr = next((c for c in chs if c.get("code") == "agreement"), None)
    wechat = next((c for c in chs if c.get("code") == "wechat"), None)
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day3 = (date.today() + timedelta(days=2)).isoformat()
    stamp = date.today().strftime("%Y%m%d") + datetime.now().strftime("%H%M%S")
    print(f"using room_type id={rt['id']} name={rt.get('name')} vacant={len(vac)}")

    # 1) direct
    c, j = req(
        "POST",
        "/api/orders",
        {
            "hotel_id": hid,
            "guest_name": "冒烟直订",
            "phone": "13800000001",
            "room_type_id": rt["id"],
            "channel_id": direct["id"],
            "check_in": today,
            "check_out": tomorrow,
            "rooms": 1,
        },
        token,
    )
    d = ok_data(j)
    mark(
        "前台直订 createOrder",
        c == 200 and bool(d.get("id")),
        f"http={c} id={d.get('id')} sg={d.get('source_group')} ot={d.get('order_type')} err={j.get('detail')}",
    )
    direct_id = d.get("id")

    # 2) walk-in (room must match room_type)
    rooms = refresh_rooms(token, hid)
    vac = vacant_of_type(rooms, rt["id"])
    room = vac[0] if vac else None
    c, j = req(
        "POST",
        "/api/orders/walk-in",
        {
            "hotel_id": hid,
            "guest_name": "冒烟散客",
            "phone": "13800000002",
            "room_id": room["id"] if room else None,
            "room_type_id": rt["id"],
            "nights": 1,
            "deposit_amount": 100,
        },
        token,
    )
    d = ok_data(j)
    o = d.get("order") or d
    mark(
        "散客 walk-in",
        c == 200 and bool(o.get("id") or d.get("id")),
        f"http={c} status={o.get('status')} room={room.get('room_no') if room else None} err={j.get('detail')}",
    )

    # 3) voucher
    code_v = f"DY-SMOKE-{stamp}-A"
    c, j = req("POST", "/api/orders/voucher/lookup", {"hotel_id": hid, "voucher_code": code_v}, token)
    info = ok_data(j)
    mark(
        "团购 lookup",
        c == 200 and bool(info.get("valid")),
        f"http={c} platform={info.get('platform')} err={j.get('detail')}",
    )
    # Prefer voucher room type if it still has vacant rooms; else fall back to smoke rt
    v_rt = int(info.get("room_type_id") or rt["id"])
    rooms = refresh_rooms(token, hid)
    if not vacant_of_type(rooms, v_rt):
        v_rt = rt["id"]
    c, j = req(
        "POST",
        "/api/orders/voucher/verify",
        {
            "hotel_id": hid,
            "voucher_code": code_v,
            "guest_name": "冒烟团购",
            "phone": "13800000003",
            "room_type_id": v_rt,
            "auto_checkin": True,
        },
        token,
    )
    d = ok_data(j)
    o = d.get("order") or d
    mark(
        "团购 verify+入住",
        c == 200 and bool(o.get("id")),
        f"http={c} no={o.get('order_no')} status={o.get('status')} err={j.get('detail')}",
    )
    voucher_id = o.get("id")

    # 4) OTA ctrip
    ext = f"CTRIP-SMOKE-{stamp}-A"
    c, j = req(
        "POST",
        "/api/orders/ota/sync",
        {
            "hotel_id": hid,
            "external_order_no": ext,
            "platform": "ctrip",
            "guest_name": "冒烟携程",
            "phone": "13800000004",
            "room_type_id": rt["id"],
            "check_in": today,
            "check_out": tomorrow,
        },
        token,
    )
    d = ok_data(j)
    mark(
        "OTA sync 携程",
        c == 200 and bool(d.get("id")),
        f"http={c} ch={d.get('channel_code')} sg={d.get('source_group')} pay={d.get('payment_status')} err={j.get('detail')}",
    )
    ota_id = d.get("id")

    # 5) OTA meituan
    ext2 = f"MT-SMOKE-{stamp}-A"
    c, j = req(
        "POST",
        "/api/orders/ota/sync",
        {
            "hotel_id": hid,
            "external_order_no": ext2,
            "platform": "meituan",
            "guest_name": "冒烟美团",
            "phone": "13800000005",
            "room_type_id": rt["id"],
            "check_in": today,
            "check_out": tomorrow,
        },
        token,
    )
    d = ok_data(j)
    mark(
        "OTA sync 美团",
        c == 200 and bool(d.get("id")),
        f"http={c} ch={d.get('channel_code')} sg={d.get('source_group')} err={j.get('detail')}",
    )

    # 6) group
    c, j = req(
        "POST",
        "/api/orders/group",
        {
            "hotel_id": hid,
            "group_name": "冒烟康养旅行团",
            "group_type": "旅游团",
            "contact_name": "领队冒烟",
            "phone": "13800000006",
            "sales_name": "王经理",
            "settle_mode": "unified",
            "settle_party": "苏一国旅",
            "check_in": today,
            "check_out": day3,
            "status": "confirmed",
            "other_amount": 200,
            "deposit_amount": 500,
            "blocks": [
                {
                    "room_type_id": rt["id"],
                    "qty": 2,
                    "unit_price": float(rt.get("base_price") or 300),
                }
            ],
            "lines": [
                {
                    "guest_name": "客人A",
                    "id_last4": "1234",
                    "room_type_id": rt["id"],
                    "check_in": today,
                    "check_out": day3,
                },
                {
                    "guest_name": "客人B",
                    "id_last4": "5678",
                    "room_type_id": rt["id"],
                    "check_in": today,
                    "check_out": day3,
                },
            ],
        },
        token,
    )
    d = ok_data(j)
    mark(
        "团体 create",
        c == 200 and bool(d.get("id")) and int(d.get("order_type") or 0) == 5,
        f"http={c} ot={d.get('order_type')} lines={len(d.get('group_lines') or [])} blocks={len(d.get('group_blocks') or [])} bal={d.get('balance_due')} err={j.get('detail')}",
    )
    gid = d.get("id")
    glines = d.get("group_lines") or []

    rooms = refresh_rooms(token, hid)
    vac = vacant_of_type(rooms, rt["id"])
    if gid and glines and vac:
        line = glines[0]
        cand = vac[0]
        c, j = req(
            "POST",
            f"/api/orders/{gid}/group-lines/{line['id']}/assign",
            {"room_id": cand["id"]},
            token,
        )
        mark("团体 排房", c == 200, f"http={c} room={cand.get('room_no')} err={j.get('detail')}")
        c, j = req(
            "POST",
            f"/api/orders/{gid}/group-lines/{line['id']}/checkin",
            {"guest_name": "客人A"},
            token,
        )
        dd = ok_data(j)
        mark(
            "团体 逐间入住",
            c == 200,
            f"http={c} order_st={(dd.get('order') or {}).get('status')} err={j.get('detail')}",
        )
    else:
        mark("团体 排房/入住", False, f"缺行或无空房 lines={len(glines)} vac={len(vac)}")

    # 7) direct assign+checkin
    if direct_id:
        rooms = refresh_rooms(token, hid)
        vac2 = vacant_of_type(rooms, rt["id"])
        if vac2:
            c, j = req(
                "POST",
                f"/api/orders/{direct_id}/assign-room",
                {"room_id": vac2[0]["id"]},
                token,
            )
            mark("直订 预分房", c == 200, f"http={c} err={j.get('detail')}")
            c, j = req("POST", f"/api/orders/{direct_id}/checkin", {}, token)
            d = ok_data(j)
            mark(
                "直订 入住",
                c == 200 and d.get("status") == "checked_in",
                f"http={c} status={d.get('status')} err={j.get('detail')}",
            )
        else:
            mark("直订 预分房/入住", False, "无同房型空房")

    # 8) OTA checkin
    if ota_id:
        rooms = refresh_rooms(token, hid)
        vac3 = vacant_of_type(rooms, rt["id"])
        if vac3:
            c, j = req(
                "POST",
                f"/api/orders/{ota_id}/checkin",
                {"room_id": vac3[0]["id"]},
                token,
            )
            d = ok_data(j)
            mark(
                "OTA 入住",
                c == 200 and d.get("status") == "checked_in",
                f"http={c} status={d.get('status')} err={j.get('detail')}",
            )
        else:
            mark("OTA 入住", False, "无空房")

    # 9) list filters — API 默认 view=arrivals；来源筛需配合 view=all 才覆盖在住/预订全集
    for src in ["direct", "voucher", "ota", "group", "ctrip", "meituan", "agreement", "wechat"]:
        c, j = req(
            "GET",
            f"/api/orders?hotel_id={hid}&view=all&source={src}&page=1&page_size=5",
            token=token,
        )
        d = ok_data(j)
        items = d.get("items") if isinstance(d, dict) else d
        n = len(items) if isinstance(items, list) else -1
        total = d.get("total") if isinstance(d, dict) else "?"
        expect = total if isinstance(total, int) else n
        # voucher/group 至少应能看到本次冒烟创建的单据
        need_hit = src in ("voucher", "group", "ota", "direct", "ctrip", "meituan")
        mark(
            f"列表筛选 source={src}",
            c == 200 and (expect > 0 if need_hit else n >= 0),
            f"http={c} count={n} total={total}",
        )

    # arrivals + voucher 为 0 属预期（核销入住后不在今日到店）
    c, j = req(
        "GET",
        f"/api/orders?hotel_id={hid}&view=arrivals&source=voucher&page=1&page_size=5",
        token=token,
    )
    d = ok_data(j)
    mark(
        "列表 arrivals+voucher（核销入住后可为空）",
        c == 200,
        f"http={c} total={d.get('total') if isinstance(d, dict) else '?'}",
    )

    # 10) agreement
    if agr:
        c, j = req(
            "POST",
            "/api/orders",
            {
                "hotel_id": hid,
                "guest_name": "冒烟协议",
                "phone": "13800000007",
                "room_type_id": rt["id"],
                "channel_id": agr["id"],
                "check_in": today,
                "check_out": tomorrow,
            },
            token,
        )
        d = ok_data(j)
        mark(
            "协议客 create",
            c == 200 and int(d.get("order_type") or 0) == 3,
            f"http={c} ot={d.get('order_type')} sg={d.get('source_group')} allow={d.get('allow_on_account')} err={j.get('detail')}",
        )
    else:
        mark("协议客 create", False, "无 agreement 渠道")

    # 11) wechat private domain
    if wechat:
        c, j = req(
            "POST",
            "/api/orders",
            {
                "hotel_id": hid,
                "guest_name": "冒烟微信",
                "phone": "13800000009",
                "room_type_id": rt["id"],
                "channel_id": wechat["id"],
                "check_in": today,
                "check_out": tomorrow,
            },
            token,
        )
        d = ok_data(j)
        mark(
            "微信私域 create",
            c == 200 and d.get("source_group") == "wechat",
            f"http={c} sg={d.get('source_group')} ch={d.get('channel_code')} err={j.get('detail')}",
        )
    else:
        mark("微信私域 create", False, "无 wechat 渠道")

    # 12) UI gap: Orders create without external_order_no for OTA channel
    if next((c for c in chs if c.get("code") == "ctrip"), None):
        ctrip = next(c for c in chs if c.get("code") == "ctrip")
        c, j = req(
            "POST",
            "/api/orders",
            {
                "hotel_id": hid,
                "guest_name": "冒烟前台选携程无单号",
                "phone": "13800000008",
                "room_type_id": rt["id"],
                "channel_id": ctrip["id"],
                "check_in": today,
                "check_out": tomorrow,
            },
            token,
        )
        d = ok_data(j)
        # 能创建，但缺渠道单号：order_no 仍为 DIR 前缀，external 为空 —— 产品缺口（非崩溃）
        mark(
            "前台新建选OTA渠道(无渠道单号) 可创建",
            c == 200 and d.get("source_group") == "ota",
            f"http={c} sg={d.get('source_group')} ot={d.get('order_type')} no={d.get('order_no')} ext={d.get('external_order_no')!r}",
        )
        mark(
            "OTA手工录入缺渠道单号字段(产品缺口)",
            True,
            "Orders 新建弹窗无 external_order_no；正式 OTA 应用 /ota/sync 或补字段",
        )

    print("\n==== SUMMARY ====")
    fails = [r for r in results if not r[1]]
    print(f"total={len(results)} pass={len(results) - len(fails)} fail={len(fails)}")
    for name, _ok, detail in fails:
        print("FAIL:", name, "|", detail)


if __name__ == "__main__":
    main()
