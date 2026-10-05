# SPDX-License-Identifier: Apache-2.0
"""模拟房态用例 01～12 点击流（走真实 HTTP API，等同前端操作）。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

B = "http://127.0.0.1:8000"
TOKEN = ""
RESULTS: list[tuple[str, bool, str]] = []


def call(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(B + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "detail": raw or str(e)}


def ok(resp) -> bool:
    return bool(resp) and resp.get("ok") is not False and "data" in resp


def record(case: str, passed: bool, detail: str):
    RESULTS.append((case, passed, detail))
    mark = "PASS" if passed else "FAIL"
    line = f"[{mark}] {case}: {detail}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("gbk", errors="replace").decode("gbk"))


def room_by_id(rid: int):
    rooms = call("GET", "/api/rooms?hotel_id=1").get("data") or []
    return next((r for r in rooms if r["id"] == rid), None)


def pick_room(*statuses: str):
    rooms = call("GET", "/api/rooms?hotel_id=1").get("data") or []
    for st in statuses:
        for r in rooms:
            if r.get("status") == st:
                return r
    return None


def pick_vc_of_type(type_id: int):
    rooms = call("GET", "/api/rooms?hotel_id=1").get("data") or []
    for r in rooms:
        if r.get("status") == "VC" and r.get("room_type_id") == type_id:
            return r
    return None


def order_id_of(resp) -> int | None:
    if not ok(resp):
        return None
    d = resp.get("data") or {}
    if isinstance(d.get("order"), dict):
        return d["order"].get("id")
    return d.get("id") or d.get("order_id")


def main():
    global TOKEN
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # ---- 登录（等同打开系统）----
    login = call("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
    if not ok(login):
        print("登录失败", login)
        sys.exit(1)
    TOKEN = login["data"]["access_token"]
    print("=== 登录成功 · 开始模拟房态点击流 ===\n")

    # ---- 房态-11 房态图 ----
    board = call("GET", "/api/rooms?hotel_id=1")
    rooms = board.get("data") or []
    labels = sorted({f"{r.get('status')}:{r.get('status_label')}" for r in rooms})
    record(
        "房态-11 房态图实时查看",
        ok(board) and len(rooms) > 0,
        f"房间 {len(rooms)} 间 · 状态分布 {', '.join(labels[:8])}",
    )

    # ---- 房态-12 超售预警 ----
    ov = call("GET", "/api/rooms/oversell?hotel_id=1&days=7")
    record(
        "房态-12 超售与房量不足预警",
        ok(ov),
        ov.get("data", {}).get("summary") or str(ov.get("detail")),
    )

    # ---- 准备：选「有空净房」的房型 ----
    types = call("GET", "/api/room-types?hotel_id=1").get("data") or []
    all_rooms = call("GET", "/api/rooms?hotel_id=1").get("data") or []
    vc_types = {r.get("room_type_id") for r in all_rooms if r.get("status") == "VC"}
    rtype = next((t for t in types if t["id"] in vc_types), None)
    if not rtype:
        record("准备房型", False, "无带空净房的房型")
        sys.exit(1)
    tid = rtype["id"]
    print(f"选用房型: {rtype.get('name')} (id={tid}) · 空净可分\n")

    walk_oid = None
    walk_rid = None
    checked_in_oid = None
    checked_in_rid = None

    # ---- 房态-08 锁房与解锁 ----
    r_blk = pick_vc_of_type(tid)
    if not r_blk:
        record("房态-08 锁房与解锁", False, "没有空净房可锁")
    else:
        lock = call(
            "POST",
            f"/api/rooms/{r_blk['id']}/status",
            {"status": "BLK", "reason": "模拟·预留升级"},
        )
        locked = room_by_id(r_blk["id"])
        unlock = call(
            "POST",
            f"/api/rooms/{r_blk['id']}/status",
            {"status": "VC", "reason": "模拟·解锁"},
        )
        unlocked = room_by_id(r_blk["id"])
        record(
            "房态-08 锁房与解锁",
            ok(lock)
            and locked
            and locked["status"] == "BLK"
            and ok(unlock)
            and unlocked
            and unlocked["status"] == "VC",
            f"{r_blk['room_no']}: 空净→锁房→空净",
        )

    # ---- 房态-06 / 07 维修房 ----
    r_ooo = pick_vc_of_type(tid)
    if not r_ooo:
        record("房态-06/07 维修房", False, "没有空净房可设维修")
    else:
        set_o = call(
            "POST",
            f"/api/rooms/{r_ooo['id']}/status",
            {
                "status": "OOO",
                "reason": "模拟·空调故障",
                "eta": (today + timedelta(days=3)).isoformat(),
            },
        )
        mid = room_by_id(r_ooo["id"])
        # 在住房禁止直接维修：另取一间 OCC 验证拦截
        r_occ = pick_room("OCC", "DO")
        blocked_ooo = True
        if r_occ:
            bad = call(
                "POST",
                f"/api/rooms/{r_occ['id']}/status",
                {"status": "OOO", "reason": "应被拒绝"},
            )
            blocked_ooo = not ok(bad)
        clr = call(
            "POST",
            f"/api/rooms/{r_ooo['id']}/status",
            {"status": "VC", "reason": "模拟·维修完成"},
        )
        after = room_by_id(r_ooo["id"])
        record(
            "房态-06 设置维修房",
            ok(set_o) and mid and mid["status"] == "OOO" and blocked_ooo,
            f"{r_ooo['room_no']}->维修房" + (" · 在住禁设维修OK" if blocked_ooo else " · 在住禁设未拦住"),
        )
        record(
            "房态-07 解除维修房",
            ok(clr) and after and after["status"] == "VC",
            f"{r_ooo['room_no']}→空净房 note已清",
        )

    # ---- 房态-01 散客入住 ----
    r_wi = pick_vc_of_type(tid)
    walk_oid = None
    walk_rid = None
    if not r_wi:
        record("房态-01 办理散客入住", False, "无空净房")
    else:
        # 脏房应失败
        r_vd = pick_room("VD")
        reject_dirty = True
        if r_vd:
            bad_wi = call(
                "POST",
                "/api/orders/walk-in",
                {
                    "hotel_id": 1,
                    "guest_name": "模拟脏房客",
                    "room_type_id": r_vd.get("room_type_id") or tid,
                    "room_id": r_vd["id"],
                    "nights": 1,
                },
            )
            reject_dirty = not ok(bad_wi)
        wi = call(
            "POST",
            "/api/orders/walk-in",
            {
                "hotel_id": 1,
                "guest_name": "模拟散客甲",
                "phone": "13900000001",
                "room_type_id": tid,
                "room_id": r_wi["id"],
                "nights": 1,
                "id_doc_type": "id_card",
                "id_doc_no": "110101199001011234",
            },
        )
        walk_oid = order_id_of(wi)
        after = room_by_id(r_wi["id"])
        walk_rid = r_wi["id"]
        record(
            "房态-01 办理散客入住",
            ok(wi) and after and after["status"] == "OCC" and reject_dirty,
            f"{r_wi['room_no']} 空净→已入住 order=#{walk_oid}"
            + (" · 脏房禁入OK" if reject_dirty else " · 脏房禁入未拦住"),
        )

    # ---- 房态-05 标记预抵 + 房态-02 预订入住 ----
    # 建预订单 → 分房(EA) → 入住(OCC)
    new_o = call(
        "POST",
        "/api/orders",
        {
            "hotel_id": 1,
            "guest_name": "模拟预抵客",
            "phone": "13900000002",
            "room_type_id": tid,
            "check_in": today.isoformat(),
            "check_out": tomorrow.isoformat(),
            "rooms": 1,
            "status": "confirmed",
        },
    )
    oid = order_id_of(new_o)
    r_ea = pick_vc_of_type(tid)
    if not ok(new_o) or not oid or not r_ea:
        record(
            "房态-05 标记预抵房",
            False,
            f"建单/空净不足 new={ok(new_o)} oid={oid} room={bool(r_ea)} tid={tid}",
        )
        record("房态-02 办理预订客人入住", False, "依赖预抵未就绪")
        checked_in_oid = None
        checked_in_rid = None
    else:
        asg = call(
            "POST",
            f"/api/orders/{oid}/assign-room",
            {"room_id": r_ea["id"]},
        )
        after_ea = room_by_id(r_ea["id"])
        record(
            "房态-05 标记预抵房",
            ok(asg) and after_ea and after_ea["status"] == "EA",
            f"订单#{oid} 分房 {r_ea['room_no']} → 预抵房"
            + (f" status={asg.get('data', {}).get('room_status')}" if ok(asg) else f" err={asg.get('detail')}"),
        )
        ci = call(
            "POST",
            f"/api/orders/{oid}/checkin",
            {"room_id": r_ea["id"], "guest_name": "模拟预抵客"},
        )
        after_ci = room_by_id(r_ea["id"])
        checked_in_oid = oid if ok(ci) else None
        checked_in_rid = r_ea["id"] if ok(ci) else None
        record(
            "房态-02 办理预订客人入住",
            ok(ci) and after_ci and after_ci["status"] == "OCC",
            f"{r_ea['room_no']} 预抵→已入住" + ("" if ok(ci) else f" err={ci.get('detail')}"),
        )

    # ---- 房态-04 标记预离 ----
    r_mark = pick_room("OCC")
    if not r_mark:
        record("房态-04 标记预离房", False, "无已入住房")
    else:
        md = call("POST", f"/api/rooms/{r_mark['id']}/mark-due-out", {"reason": "模拟·今日预离"})
        after = room_by_id(r_mark["id"])
        record(
            "房态-04 标记预离房",
            ok(md) and after and after["status"] == "DO",
            f"{r_mark['room_no']} 已入住→预离",
        )
        # 续住清预离
        stay = call(
            "POST",
            f"/api/rooms/{r_mark['id']}/status",
            {"status": "OCC", "reason": "模拟·续住"},
        )
        after2 = room_by_id(r_mark["id"])
        record(
            "房态-04 续住清除预离",
            ok(stay) and after2 and after2["status"] == "OCC",
            f"{r_mark['room_no']} 预离→已入住",
        )

    # ---- 房态-09 换房（用刚入住的预订单）----
    change_oid = checked_in_oid or walk_oid
    cur_room_id = checked_in_rid or walk_rid
    new_target = pick_vc_of_type(tid)
    if not change_oid or not new_target or not cur_room_id:
        record("房态-09 换房", False, "无在住单或无目标空净房")
    else:
        chg = call(
            "POST",
            f"/api/orders/{change_oid}/change-room",
            {"room_id": new_target["id"], "reason": "模拟换房"},
        )
        old_st = room_by_id(cur_room_id)
        new_st = room_by_id(new_target["id"])
        record(
            "房态-09 换房",
            ok(chg) and new_st and new_st["status"] == "OCC" and (old_st is None or old_st["status"] == "VD"),
            f"订单#{change_oid} {old_st and old_st.get('room_no')}→空脏 · "
            f"{new_target['room_no']}→已入住" + ("" if ok(chg) else f" err={chg.get('detail')}"),
        )
        # 换房后在住房变为新房，供退房用
        if ok(chg):
            checked_in_rid = new_target["id"]
            checked_in_oid = change_oid

    # ---- 房态-03 客人退房 ----
    co_oid = checked_in_oid
    co_rid = checked_in_rid
    if not co_oid:
        # 再造一笔：空净 walk-in
        r_co = pick_vc_of_type(tid)
        if not r_co:
            record("房态-03 客人退房", False, "无空净房可造退房样本")
            co_oid = None
        else:
            wi2 = call(
                "POST",
                "/api/orders/walk-in",
                {
                    "hotel_id": 1,
                    "guest_name": "模拟退房客",
                    "room_type_id": tid,
                    "room_id": r_co["id"],
                    "nights": 1,
                },
            )
            co_oid = order_id_of(wi2)
            co_rid = r_co["id"]
    if co_oid and co_rid:
        co = call("POST", f"/api/orders/{co_oid}/checkout", {})
        after = room_by_id(co_rid)
        hk = call("GET", "/api/housekeeping?hotel_id=1")
        tasks = hk.get("data") or []
        has_task = any(t.get("room_id") == co_rid and t.get("status") not in ("done", "closed") for t in tasks)
        # board 也可能带 open_hk
        if not has_task and after and after.get("open_hk"):
            has_task = True
        record(
            "房态-03 客人退房",
            ok(co) and after and after["status"] == "VD",
            f"订单#{co_oid} {(after or {}).get('room_no')}→空脏 · 清洁提示={'有' if has_task or (after or {}).get('open_hk') else '无'}"
            + ("" if ok(co) else f" err={co.get('detail')}"),
        )

    # ---- 房态-10 夜审翻转 ----
    # 先造一间 OCC 并标预离，再续住场景用另一间
    r_na = pick_room("OCC")
    if r_na:
        call("POST", f"/api/rooms/{r_na['id']}/mark-due-out", {"reason": "夜审前预离样本"})
    # 造一笔未来到店的预抵，避免被当成超时释放
    r_future = pick_vc_of_type(tid)
    future_oid = None
    if r_future:
        fo = call(
            "POST",
            "/api/orders",
            {
                "hotel_id": 1,
                "guest_name": "模拟明日预抵",
                "room_type_id": tid,
                "check_in": tomorrow.isoformat(),
                "check_out": (tomorrow + timedelta(days=1)).isoformat(),
                "rooms": 1,
                "status": "confirmed",
            },
        )
        future_oid = (fo.get("data") or {}).get("id")
        if future_oid:
            call("POST", f"/api/orders/{future_oid}/assign-room", {"room_id": r_future["id"]})
    na = call(
        "POST",
        "/api/night-audit",
        {"hotel_id": 1, "biz_date": today.isoformat(), "force": True},
    )
    flip = (na.get("data") or {}).get("room_flip") or {}
    future_st = room_by_id(r_future["id"]) if r_future else None
    record(
        "房态-10 夜审状态翻转",
        ok(na) and isinstance(flip, dict),
        f"预离+{flip.get('marked_due_out', 0)} · 清预离{flip.get('cleared_due_out', 0)} · "
        f"释放预抵{flip.get('released_ea', 0)} · no_show{flip.get('no_show_orders', 0)}"
        + (f" · 明日预抵保留={future_st.get('status')}" if future_st else ""),
    )

    # ---- 汇总 ----
    print("\n=== 汇总 ===")
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    for case, p, detail in RESULTS:
        tag = "OK" if p else "NG"
        line = f"  [{tag}] {case} -- {detail}"
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("gbk", errors="replace").decode("gbk"))
    print(f"\n合计 {passed} 通过 / {failed} 失败 / 共 {len(RESULTS)} 项")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
