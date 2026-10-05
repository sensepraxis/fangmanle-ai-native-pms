# SPDX-License-Identifier: Apache-2.0
# hk.housekeeping_service.board_service — auto-split by AST

"""
房务工单流：与房态分离。

INT-01 退房 → 建清洁单（房态已是 VD）
HK-02/03 开始/完成清洁 → pending_inspect（房态仍 VD）
HK-04 查房通过 → VD→VC
HK-05 不通过 → rework
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models as _models
from models import HousekeepingTask, Room, User

globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})
from infra.i18n import t as _t
from rooms.room_status import OCC, OOO, VC, VD, normalize, transition

HK_TYPE_CN = {
    "clean": "退房清扫",
    "inspect": "查房质检",
    "turn": "住中整理",
    "daily": "日常清洁",
    "repair": "维修",
    "service": "客需服务",
}
HK_ICON = {
    "clean": "cleaning_services",
    "inspect": "fact_check",
    "turn": "hotel",
    "daily": "mop",
    "repair": "build",
    "service": "room_service",
}

# ---- 模块级常量（在原文件中位于 def 之后但属于模块层）----
HK_TASK_TYPES = {
    "clean": "退房清洁",
    "turn": "住中整理",
    "daily": "日常清洁",
    "repair": "维修",
    "service": "客中服务",
    "inspect": "查房验收",
}
HK_AI_DISPATCH_SYSTEM = '你是单体酒店客房主管的派工助手。酒店规模小（通常 1–2 层、每层约 12 间），不要按百间酒店的编制来估人力。\n\n目标：根据「系统现状」、MCP 工具结果和人员负荷，给出可立刻执行的派工方案，并筛选待建保洁任务。\n\n硬约束：\n1. 只能使用输入里出现的 task_id、staff id、room_id，禁止编造人员、房号或楼层。\n2. 休息（status=rest）的人不能派工。\n3. 优先：同楼层就近 → 空闲/低负荷 → VIP/高优（priority 数字越小越急）。\n4. 每人最多派 4 单；本轮最多派 8 单。不要把全部开放任务塞给一个人。\n5. 缺口人数 = max(0, 待分配任务数 − 可派工人数)，两层小楼缺口通常是 0–2。\n6. new_tasks 只能从 MCP 工具 `draft_housekeeping_tasks` 返回的草稿里挑选，最多 6 条；不要给已有未完成工单的房间再建一张。\n7. 只输出一个 JSON 对象，不要 markdown、不要解释性前后文。\n\nJSON 格式：\n{\n  "summary": "不超过 80 字：先结论后理由",\n  "mode": "smart",\n  "focus_floor": 1,\n  "gap": 0,\n  "assignments": [\n    {"task_id": 12, "assignee_id": 5, "reason": "同层且空闲"}\n  ],\n  "new_tasks": [\n    {"room_id": 3, "task_type": "clean", "priority": 2, "assignee_id": null, "reason": "空脏无工单"}\n  ]\n}\n'
from hk.hk_status import HK_OPENISH_ACTIVE as HK_OPENISH

HK_TYPE_ALIASES = {
    "checkout": "clean",
    "checkout_clean": "clean",
    "清扫": "clean",
    "退房": "clean",
    "退房清洁": "clean",
    "退房清扫": "clean",
    "daily_clean": "daily",
    "日常": "daily",
    "日常清洁": "daily",
    "turn_down": "turn",
    "turndown": "turn",
    "住中": "turn",
    "住中整理": "turn",
    "maint": "repair",
    "maintenance": "repair",
    "维修": "repair",
    "客需": "service",
    "客中": "service",
    "客中服务": "service",
    "客需服务": "service",
    "查房": "inspect",
    "质检": "inspect",
    "查房验收": "inspect",
    "查房质检": "inspect",
}

# 跨子模块 helper：模块别名访问（避开循环 import）
from hk.housekeeping_service import dispatch_service as _hk_dispatch_service


def hk_ui_status(raw: str) -> str:
    s = (raw or "").lower()
    if s in ("done", "closed", "completed", "ignored"):
        return "done"
    if s in ("pending_inspect", "inspect", "qa"):
        return "inspect"
    if s in ("in_progress", "progress", "doing"):
        return "progress"
    return "waiting"


def ensure_open_tasks_from_rooms(db: Session, hotel_id: int) -> int:
    """
    为脏房/打扫中房间补齐真实 HousekeepingTask（写入数据库，幂等）。
    返回新建条数。不再向前端返回 synthetic 假任务。
    """
    from rooms.room_status import VD
    from rooms.room_status import normalize as norm_st

    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    created = 0
    for r in rooms:
        st = norm_st(r.status)
        if st not in (VD, "cleaning") and (r.status or "") not in ("dirty", "cleaning", "VD"):
            continue
        from hk.hk_status import HK_OPENISH as _HK_OPENISH_FULL

        _hk_openish_values = [s.value for s in _HK_OPENISH_FULL]
        openish = (
            db.query(HousekeepingTask)
            .filter(
                HousekeepingTask.hotel_id == hotel_id,
                HousekeepingTask.room_id == r.id,
                HousekeepingTask.task_type.in_(("turn", "clean")),
                HousekeepingTask.status.in_(_hk_openish_values),
            )
            .first()
        )
        if openish:
            if openish.status == "ignored":
                continue
            if (r.status or "") == "cleaning" and openish.status in ("open", "assigned"):
                openish.status = "in_progress"
            continue
        t = HousekeepingTask(
            hotel_id=hotel_id,
            room_id=r.id,
            task_type="clean",
            assignee_id=None,
            priority=2 if st == VD or (r.status or "") == "dirty" else 3,
            status="in_progress" if (r.status or "") == "cleaning" else "open",
            created_at=datetime.now(),
            due_at=datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
            if datetime.now().hour < 14
            else datetime.now(),
        )
        db.add(t)
        created += 1
    if created:
        db.flush()
    return created


def _room_open_types(db: Session, hotel_id: int) -> dict[int, set[str]]:
    rows = (
        db.query(HousekeepingTask.room_id, HousekeepingTask.task_type)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(HK_OPENISH),
            HousekeepingTask.room_id.isnot(None),
        )
        .all()
    )
    out: dict[int, set[str]] = {}
    for rid, tt in rows:
        out.setdefault(int(rid), set()).add(tt or "clean")
    return out


def mcp_list_room_status(db: Session, hotel_id: int) -> list[dict]:
    """MCP 工具：列出本店房态与未完成工单类型。"""
    open_types = _room_open_types(db, hotel_id)
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).order_by(Room.room_no.asc()).all()
    out = []
    for r in rooms:
        st = normalize(r.status)
        out.append(
            {
                "room_id": r.id,
                "room_no": r.room_no,
                "floor": int(r.floor) if r.floor else None,
                "status": st,
                "open_types": sorted(open_types.get(r.id, set())),
            }
        )
    return out


def mcp_list_staff_load(db: Session, hotel_id: int) -> list[dict]:
    """MCP 工具：在岗保洁负荷。"""
    staff = _hk_dispatch_service._on_duty_staff(db, hotel_id)
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "status": "rest" if s.get("shift") == "off" else "busy" if s.get("open") else "idle",
            "open": s.get("open") or 0,
            "floors": s.get("floors") or [],
        }
        for s in staff
    ]


def mcp_list_guest_requests(db: Session, hotel_id: int) -> list[dict]:
    """MCP 工具：未结客中请求。"""
    from hk.queries import OpenServiceRequestsQuery

    return OpenServiceRequestsQuery(hotel_id=hotel_id, limit=20).as_dicts(db)


def mcp_draft_housekeeping_tasks(db: Session, hotel_id: int, limit: int = 8) -> list[dict]:
    """MCP 工具：根据房态/客需起草待建保洁任务（不写库）。"""
    rooms = mcp_list_room_status(db, hotel_id)
    staff = mcp_list_staff_load(db, hotel_id)
    requests = mcp_list_guest_requests(db, hotel_id)
    drafts: list[dict] = []
    seen: set[tuple[int, str]] = set()

    def add(room: dict, task_type: str, priority: int, reason: str):
        key = (int(room["room_id"]), task_type)
        if key in seen:
            return
        open_types = set(room.get("open_types") or [])
        if task_type in open_types:
            return
        if task_type == "clean" and ("turn" in open_types or "daily" in open_types):
            return
        if task_type in ("turn", "daily") and ("clean" in open_types or "turn" in open_types or "daily" in open_types):
            return
        pick = _hk_dispatch_service._pick_staff_for_floor(staff, room.get("floor"))
        type_msgid = HK_TASK_TYPES.get(task_type, task_type)
        drafts.append(
            {
                "room_id": room["room_id"],
                "room_no": room["room_no"],
                "floor": room.get("floor"),
                "task_type": task_type,
                "task_type_label": _t(type_msgid),
                "priority": priority,
                "assignee_id": pick["id"] if pick else None,
                "assignee": pick["name"] if pick else None,
                "reason": reason,
            }
        )
        seen.add(key)

    by_id = {r["room_id"]: r for r in rooms}
    for r in rooms:
        st = r.get("status")
        if st == VD:
            add(r, "clean", 2, _t("空脏无开放清洁单"))
        elif st == OOO:
            add(r, "repair", 2, _t("维修房需跟进"))
        elif st == OCC:
            add(r, "daily", 3, _t("在住房今日无日常整理"))
    for sr in requests:
        rm = by_id.get(sr.get("room_id"))
        if not rm:
            continue
        add(
            rm,
            "service",
            min(2, sr.get("priority") or 2),
            _t("客需：{content}", content=sr.get("content") or _t("未结请求")),
        )
    if len(drafts) < 3:
        for r in rooms:
            if r.get("status") == VC:
                add(r, "inspect", 3, _t("空净预查，保证可售"))
            if len(drafts) >= limit:
                break
    return drafts[: max(1, min(int(limit), 12))]


def run_hk_mcp_tools(db: Session, hotel_id: int) -> dict:
    """依次调用房务 MCP 工具，把结果交给 LLM 筛选。"""
    rooms = mcp_list_room_status(db, hotel_id)
    staff = mcp_list_staff_load(db, hotel_id)
    requests = mcp_list_guest_requests(db, hotel_id)
    drafts = mcp_draft_housekeeping_tasks(db, hotel_id)
    tools = [
        {"name": "list_room_status", "ok": True, "count": len(rooms), "result": rooms},
        {"name": "list_staff_load", "ok": True, "count": len(staff), "result": staff},
        {"name": "list_guest_requests", "ok": True, "count": len(requests), "result": requests},
        {"name": "draft_housekeeping_tasks", "ok": True, "count": len(drafts), "result": drafts},
    ]
    return {"tools": tools, "drafts": drafts, "rooms": rooms, "staff": staff, "requests": requests}


def _parse_json_blob(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search("\\{[\\s\\S]*\\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def build_housekeeping_board(db: Session, hotel_id: int, perf_range: str = "7d"):
    """房务作业台聚合：任务 / 员工负荷 / 客需 / 效能 / 质检（全部来自数据库，无假数）。"""
    from hk.housekeeping_service import ensure_open_tasks_from_rooms

    ensure_open_tasks_from_rooms(db, hotel_id)
    db.commit()
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    by_status: dict = {}
    for r in rooms:
        by_status[r.status or "vacant"] = by_status.get(r.status or "vacant", 0) + 1
    rt_map = {rt.id: rt for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}
    users = {u.id: u for u in db.query(User).filter((User.hotel_id == hotel_id) | User.hotel_id.is_(None)).all()}
    role_map = {r.id: r.name for r in db.query(Role).all()}
    task_rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(HousekeepingTask.hotel_id == hotel_id)
        .order_by(HousekeepingTask.priority.asc(), HousekeepingTask.id.desc())
        .all()
    )
    tasks = []
    staff_agg: dict = {}
    for t, rm in task_rows:
        if (t.status or "").lower() == "ignored":
            continue
        u = users.get(t.assignee_id) if t.assignee_id else None
        name = u.full_name or u.username if u else "待分配"
        tt = t.task_type or "clean"
        ui_st = hk_ui_status(t.status)
        elapsed = ""
        elapsed_min = None
        if t.created_at and ui_st == "progress":
            elapsed_min = max(1, int((datetime.now() - t.created_at).total_seconds() // 60))
            if elapsed_min > 480:
                elapsed_min = min(90, elapsed_min // 60)
            elapsed = _t("{n} 分钟", n=elapsed_min)
        tip = None
        fail_reason = getattr(t, "fail_reason", None) or None
        fail_count = int(getattr(t, "fail_count", 0) or 0)
        if fail_reason and (t.status or "") == "rework":
            tip = _t("退回：{reason}", reason=fail_reason)
        elif fail_reason and tt == "repair":
            tip = fail_reason
        elif (t.priority or 5) <= 2:
            tip = _t("高优：临近预抵或 VIP，建议优先闭环。")
        elif rm and (rm.status or "") in ("dirty", "VD", "cleaning"):
            tip = _t("退房空脏，建议按楼层就近派工。")
        if ui_st == "inspect":
            tip = _t("清洁已完成，待查房验收后才可改空净。")
        rt = rt_map.get(rm.room_type_id) if rm and rm.room_type_id else None
        due_hm = t.due_at.strftime("%H:%M") if t.due_at else None
        type_ui = (
            "repair"
            if tt in ("repair", "maint")
            else "service"
            if tt == "service"
            else "inspect"
            if tt == "inspect"
            else "clean"
        )
        _title_msgid = HK_TYPE_CN.get(tt)
        item = {
            "id": t.id,
            "room_no": rm.room_no if rm else "—",
            "floor": rm.floor if rm else None,
            "room_type": (rt.name if rt else None) or None,
            "room_type_name": (rt.name if rt else None) or None,
            "title": _t(_title_msgid) if _title_msgid else tt,
            "type": type_ui,
            "task_type": tt,
            "assignee": name if t.assignee_id else "",
            "assignee_id": t.assignee_id,
            "priority": (t.priority or 5) <= 2,
            "priority_rank": t.priority,
            "vip": (t.priority or 5) <= 1,
            "urgent": (t.priority or 5) <= 1 or fail_count >= 2,
            "status": ui_st,
            "raw_status": t.status,
            "icon": HK_ICON.get(tt, "cleaning_services"),
            "tip": tip,
            "note": fail_reason or tip,
            "fail_reason": fail_reason,
            "fail_count": fail_count,
            "escalate": fail_count >= 2,
            "elapsed": elapsed,
            "elapsed_min": elapsed_min,
            "eta_min": 40 if tt in ("repair", "maint") else 25,
            "due_at": t.due_at.isoformat() if t.due_at else None,
            "deadline": due_hm,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None,
            "synthetic": False,
        }
        tasks.append(item)
        if t.assignee_id and ui_st != "done":
            bag = staff_agg.setdefault(
                t.assignee_id, {"id": t.assignee_id, "name": name, "done": 0, "total": 0, "area": "—", "open": 0}
            )
            bag["total"] += 1
            bag["open"] += 1
        if t.assignee_id and ui_st == "done":
            bag = staff_agg.setdefault(
                t.assignee_id, {"id": t.assignee_id, "name": name, "done": 0, "total": 0, "area": "—", "open": 0}
            )
            bag["done"] += 1
            bag["total"] += 1
    shifts = (
        db.query(StaffShift).filter_by(hotel_id=hotel_id, shift_date=date.today()).order_by(StaffShift.id.desc()).all()
    )
    if not shifts:
        shifts = (
            db.query(StaffShift)
            .filter_by(hotel_id=hotel_id)
            .order_by(StaffShift.shift_date.desc(), StaffShift.id.desc())
            .limit(8)
            .all()
        )
    shift_by_user = {s.user_id: s for s in shifts}
    SH_CN = {"morning": "早班", "afternoon": "中班", "night": "晚班", "hourly": "中班", "off": "休息"}
    for uid, bag in list(staff_agg.items()):
        sh = shift_by_user.get(uid)
        if sh:
            shift_l = _t(SH_CN[sh.shift]) if sh.shift in SH_CN else (sh.shift or _t("当班"))
            note = sh.handover_note if sh.handover_note else _t("正常")
            bag["area"] = f"{shift_l} · {note}"[:40]
            bag["shift"] = sh.shift
            bag["status"] = "rest" if sh.shift == "off" else "work" if bag.get("open") else "idle"
        else:
            floors = sorted({x["floor"] for x in tasks if x["assignee_id"] == uid and x.get("floor")})
            bag["area"] = _t("{n}楼", n=floors[0]) if floors else _t("全楼")
            bag["status"] = "work" if bag.get("open") else "idle"
    for s in shifts:
        if s.user_id in staff_agg:
            continue
        u = users.get(s.user_id)
        role_raw = (role_map.get(u.role_id) if u and u.role_id else None) or "保洁"
        staff_agg[s.user_id] = {
            "id": s.user_id,
            "name": u.full_name or u.username if u else _t("员工{id}", id=s.user_id),
            "done": 0,
            "total": 0,
            "open": 0,
            "area": _t(SH_CN[s.shift]) if s.shift in SH_CN else (s.shift or _t("当班")),
            "shift": s.shift,
            "status": "rest" if (s.shift or "") == "off" else "idle",
            "role": _t(role_raw) if role_raw in ("保洁", "客房", "工程") else role_raw,
        }
    staff = list(staff_agg.values())
    for s in staff:
        uid = s.get("id")
        u = users.get(uid) if isinstance(uid, int) else None
        if u and "role" not in s:
            role_raw = role_map.get(u.role_id) or "保洁"
            s["role"] = _t(role_raw) if role_raw in ("保洁", "客房", "工程") else role_raw
        elif isinstance(s.get("role"), str) and s["role"] in ("保洁", "客房", "工程"):
            s["role"] = _t(s["role"])
        tot = max(s["total"], 1)
        s["load"] = round(100 * s["open"] / tot) if s["total"] else 0
        s["busy"] = s["open"] > 0
        if "status" not in s:
            s["status"] = "work" if s["busy"] else "idle"
        s["statusLabel"] = _t("休息") if s.get("status") == "rest" else _t("工作中") if s["busy"] else _t("空闲")
        s["room"] = s.get("area") or ""
    sr_rows = (
        db.query(ServiceRequest, Room)
        .outerjoin(Room, ServiceRequest.room_id == Room.id)
        .filter(ServiceRequest.hotel_id == hotel_id)
        .order_by(ServiceRequest.priority.asc(), ServiceRequest.id.desc())
        .limit(40)
        .all()
    )
    service_requests = []
    for sr, rm in sr_rows:
        open_ = (sr.status or "") not in ("done", "closed", "resolved")
        au = users.get(sr.assignee_id) if getattr(sr, "assignee_id", None) else None
        service_requests.append(
            {
                "id": sr.id,
                "room": rm.room_no if rm else "—",
                "room_no": rm.room_no if rm else "—",
                "content": sr.content or "",
                "msg": sr.content or "",
                "parse": sr.content or "客需服务",
                "priority": sr.priority,
                "status": sr.status,
                "open": open_,
                "channel": "客需",
                "time": sr.created_at.strftime("%H:%M") if sr.created_at else "—",
                "iot": "空调" in (sr.content or ""),
                "assignee": au.full_name or au.username if au else "未分配",
                "assignee_id": getattr(sr, "assignee_id", None),
            }
        )
    open_tasks = sum(1 for x in tasks if x["status"] != "done")
    open_sr = sum(1 for x in service_requests if x["open"])
    from rooms.room_status import BLK, DO, EA, OCC, OOO, VC, VD
    from rooms.room_status import normalize as _rst_norm

    dirty = sum(1 for r in rooms if _rst_norm(r.status) == VD)
    cleaning = sum(1 for x in tasks if x["status"] == "progress")
    vacant = sum(1 for r in rooms if _rst_norm(r.status) == VC)
    ooo = sum(1 for r in rooms if _rst_norm(r.status) in (OOO, BLK))
    occupied = sum(1 for r in rooms if _rst_norm(r.status) in (OCC, EA, DO))
    floor_open: dict = {}
    floor_dirty: dict = {}
    floor_cleaning: dict = {}
    for x in tasks:
        if x["status"] == "done":
            continue
        fl = x.get("floor")
        if fl:
            floor_open[fl] = floor_open.get(fl, 0) + 1
    for r in rooms:
        fl = r.floor
        if not fl:
            continue
        if _rst_norm(r.status) == VD:
            floor_dirty[fl] = floor_dirty.get(fl, 0) + 1
        elif _rst_norm(r.status) in (OOO, BLK):
            pass
    for x in tasks:
        if x["status"] == "progress" and x.get("floor"):
            fl = x["floor"]
            floor_cleaning[fl] = floor_cleaning.get(fl, 0) + 1
    all_floors = sorted(set(list(floor_open.keys()) + list(floor_dirty.keys()) + list(floor_cleaning.keys())))
    floor_heatmap = []
    max_score = 1
    for fl in all_floors:
        open_n = floor_open.get(fl, 0)
        dirty_n = floor_dirty.get(fl, 0)
        clean_n = floor_cleaning.get(fl, 0)
        score = open_n * 2 + dirty_n + clean_n
        max_score = max(max_score, score)
        floor_heatmap.append(
            {
                "floor": fl,
                "label": f"{fl}F",
                "open_tasks": open_n,
                "dirty": dirty_n,
                "cleaning": clean_n,
                "score": score,
            }
        )
    for row in floor_heatmap:
        pct = round(100 * row["score"] / max_score) if max_score else 0
        row["pct"] = max(pct, 8 if row["score"] else 0)
        if pct >= 70:
            row["level"] = "high"
            row["level_label"] = "告警"
            row["color"] = "#ba1a1a"
        elif pct >= 40:
            row["level"] = "mid"
            row["level_label"] = "紧张"
            row["color"] = "#f9ab00"
        else:
            row["level"] = "low"
            row["level_label"] = "正常"
            row["color"] = "#16a34a"
    floor_heatmap.sort(key=lambda x: x["floor"])
    _today = date.today()
    hour_load_today = [0] * 24
    for t, _rm in task_rows:
        ts = t.created_at or t.due_at
        if not ts:
            continue
        try:
            if ts.date() != _today:
                continue
        except Exception:
            continue
        hour_load_today[ts.hour] += 1
    waiting_n = sum(1 for x in tasks if x["status"] == "waiting")
    progress_n = sum(1 for x in tasks if x["status"] == "progress")
    inspect_n = sum(1 for x in tasks if x["status"] == "inspect")
    to_clean_n = waiting_n + progress_n
    scheduled_on = [s for s in staff if s.get("status") != "rest"]
    scheduled_n = len(scheduled_on)
    active_ids: set = set()
    for x in tasks:
        if x.get("assignee_id") and x["status"] == "progress":
            active_ids.add(int(x["assignee_id"]))
    for t, _rm in task_rows:
        if t.assignee_id and t.done_at and (t.done_at.date() == _today):
            active_ids.add(int(t.assignee_id))
        if t.assignee_id and (t.status or "") == "in_progress":
            active_ids.add(int(t.assignee_id))
    if active_ids:
        on_duty = len(active_ids)
        on_duty_source = "task_activity"
        on_duty_label = _t("作业在岗")
    else:
        on_duty = scheduled_n
        on_duty_source = "shift_roster"
        on_duty_label = _t("排班应到（无打卡/作业痕迹）")
    _staff_on_tmp = max(1, on_duty or 1)
    std_rooms_per_hour = 2.0
    cap_per_hour = max(1.0, _staff_on_tmp * std_rooms_per_hour)

    def _ratio_level(n: int, cap: float) -> int:
        if n <= 0:
            return 0
        ratio = n / max(0.1, cap)
        if ratio <= 0.8:
            return 1
        if ratio <= 1.2:
            return 2
        return 3

    hour_slots = []
    for h in range(8, 20):
        n = hour_load_today[h]
        ratio = n / cap_per_hour
        hour_slots.append(
            {
                "hour": f"{h:02d}:00",
                "count": n,
                "level": _ratio_level(n, cap_per_hour),
                "ratio": round(ratio, 2),
                "capacity": round(cap_per_hour, 1),
            }
        )
    now_dt = datetime.now()
    now_h = now_dt.hour
    future_slots = [s for s in hour_slots if int(str(s["hour"])[:2]) >= now_h and s["count"] > 0]
    past_slots = [s for s in hour_slots if int(str(s["hour"])[:2]) < now_h and s["count"] > 0]
    if future_slots:
        focus_slot = max(future_slots, key=lambda x: x["count"])
        peak_kind = "current" if int(str(focus_slot["hour"])[:2]) == now_h else "next"
    elif past_slots:
        focus_slot = max(past_slots, key=lambda x: x["count"])
        peak_kind = "past"
    else:
        focus_slot = None
        peak_kind = "none"
    remain_h = max(1, min(20, now_h + 2) - now_h) if now_h < 20 else 1
    deadline_h = min(20, now_h + 2) if now_h < 20 else 20
    need_before = to_clean_n
    supply = round(cap_per_hour * remain_h, 1)
    capacity_ok = need_before <= supply
    if peak_kind == "past" and focus_slot:
        ph = int(str(focus_slot["hour"])[:2])
        peak_label = _t(
            "今日高峰已过 {start}–{end}（新建 {n}）",
            start=f"{ph:02d}:00",
            end=f"{(ph + 1) % 24:02d}:00",
            n=focus_slot["count"],
        )
    elif focus_slot:
        ph = int(str(focus_slot["hour"])[:2])
        tag = _t("当前时段") if peak_kind == "current" else _t("下一高峰")
        peak_label = _t(
            "{tag} {start}–{end} 新建 {n} 单",
            tag=tag,
            start=f"{ph:02d}:00",
            end=f"{(ph + 1) % 24:02d}:00",
            n=focus_slot["count"],
        )
    else:
        peak_label = ""
    verdict = _t("够") if capacity_ok else _t("不够")
    decision_text = _t(
        "{h}:00 前待清洁 {need} 间（待分配 {wait} + 进行中 {prog}），{duty_label} {duty} 人·产能约 {cap} 间/时，窗口产能约 {supply} 间 → {verdict}",
        h=f"{deadline_h:02d}",
        need=need_before,
        wait=waiting_n,
        prog=progress_n,
        duty_label=on_duty_label,
        duty=on_duty,
        cap=f"{cap_per_hour:.0f}",
        supply=f"{supply:.0f}",
        verdict=verdict,
    )
    top = max(floor_heatmap, key=lambda x: x["score"]) if floor_heatmap else None
    floor_wait: dict = {}
    floor_prog: dict = {}
    for x in tasks:
        fl = x.get("floor")
        if not fl:
            continue
        if x["status"] == "waiting":
            floor_wait[fl] = floor_wait.get(fl, 0) + 1
        elif x["status"] == "progress":
            floor_prog[fl] = floor_prog.get(fl, 0) + 1
    floor_staff: dict = {}
    for s in scheduled_on:
        fl = None
        area = str(s.get("area") or s.get("room") or "")
        for tok in area.replace("楼", " ").replace("F", " ").split():
            if tok.isdigit():
                fl = int(tok)
                break
        if fl is None and isinstance(s.get("id"), int):
            for x in tasks:
                if x.get("assignee_id") == s["id"] and x.get("floor") and (x["status"] == "progress"):
                    fl = x["floor"]
                    break
        if fl is None:
            continue
        floor_staff[fl] = floor_staff.get(fl, 0) + 1
    dispatch_suggest = None
    if floor_wait:
        to_fl = max(floor_wait.keys(), key=lambda f: floor_wait[f])
        to_n = floor_wait[to_fl]
        candidates = [f for f in floor_staff if f != to_fl and floor_wait.get(f, 0) < to_n] or [
            f for f in floor_staff if f != to_fl
        ]
        if not candidates:
            candidates = [f for f in sorted(set(list(floor_wait) + list(floor_staff))) if f != to_fl]
        if candidates and to_n >= 2:
            from_fl = min(candidates, key=lambda f: floor_wait.get(f, 0))
            move_n = 1 if to_n < 10 else 2
            eta_min = max(25, int(round(to_n / max(1, (floor_staff.get(to_fl, 0) + move_n) * std_rooms_per_hour) * 60)))
            dispatch_suggest = {
                "from_floor": from_fl,
                "to_floor": to_fl,
                "people": move_n,
                "eta_min": eta_min,
                "to_waiting": to_n,
                "message": _t(
                    "{to}F 待分配积压 {n} 间，建议从 {frm}F 调 {people} 人支援，预计约 {eta} 分钟消化积压",
                    to=to_fl,
                    n=to_n,
                    frm=from_fl,
                    people=move_n,
                    eta=eta_min,
                ),
            }
    rooms_total = len(rooms)
    status_parts = [
        _t("总房 {n}", n=rooms_total),
        _t("脏房 {n}", n=dirty),
        _t("净房 {n}", n=vacant),
        _t("占用/维修锁房 {n}", n=occupied + ooo),
        _t("待清洁 {n}（待分配 {w}+进行中 {p}）", n=to_clean_n, w=waiting_n, p=progress_n),
        _t("待验收 {n}", n=inspect_n),
        f"{on_duty_label} {on_duty}",
    ]
    if decision_text:
        status_parts.append(decision_text)
    if top and top.get("open_tasks"):
        status_parts.append(_t("积压最重 {floor} 楼（开放 {n}）", floor=top["floor"], n=top["open_tasks"]))
    status_text = " · ".join(status_parts)
    status_snapshot = {
        "text": status_text,
        "rooms_total": rooms_total,
        "dirty": dirty,
        "vacant": vacant,
        "occupied": occupied,
        "ooo": ooo,
        "waiting": waiting_n,
        "progress": progress_n,
        "inspect": inspect_n,
        "to_clean": to_clean_n,
        "on_duty": on_duty,
        "on_duty_source": on_duty_source,
        "on_duty_label": on_duty_label,
        "scheduled_on": scheduled_n,
        "peak_hour": focus_slot["hour"] if focus_slot else None,
        "peak_kind": peak_kind,
        "peak_label": peak_label,
        "decision_text": decision_text,
        "capacity_ok": capacity_ok,
        "hot_floor": top["floor"] if top else None,
        "hot_floor_open": top["open_tasks"] if top else 0,
        "dispatch_suggest": dispatch_suggest,
    }
    dispatch_alert = {
        "title": _t("系统现状"),
        "message": status_text,
        "peak_hour": focus_slot["hour"] if focus_slot else None,
        "peak_kind": peak_kind,
        "peak_label": peak_label,
        "decision_text": decision_text,
        "floor": top["floor"] if top else None,
        "gap": None if capacity_ok else need_before - supply,
        "suggest": (dispatch_suggest or {}).get("message"),
        "dispatch_suggest": dispatch_suggest,
        "waiting": waiting_n,
        "progress": progress_n,
        "inspect": inspect_n,
        "to_clean": to_clean_n,
        "on_duty": on_duty,
        "on_duty_label": on_duty_label,
        "rooms_total": rooms_total,
        "dirty": dirty,
        "vacant": vacant,
        "occupied_ooo": occupied + ooo,
    }
    import json as _json
    from collections import defaultdict

    from hk.staffing_service import build_ai_forecast, mcp_forecast_departures

    insp_rows = (
        db.query(RoomInspection)
        .filter_by(hotel_id=hotel_id)
        .order_by(RoomInspection.inspected_at.desc(), RoomInspection.id.desc())
        .all()
    )
    today = date.today()
    pr = (perf_range or "7d").lower()
    if pr == "week":
        day0 = today - timedelta(days=today.weekday())
        n_days = (today - day0).days + 1
        range_label = _t("本周 {a}–{b}", a=f"{day0.month}/{day0.day}", b=f"{today.month}/{today.day}")
    elif pr == "30d":
        day0 = today - timedelta(days=29)
        n_days = 30
        range_label = _t("近30天 {a}–{b}", a=f"{day0.month}/{day0.day}", b=f"{today.month}/{today.day}")
    else:
        day0 = today - timedelta(days=6)
        n_days = 7
        range_label = _t("近7天 {a}–{b}", a=f"{day0.month}/{day0.day}", b=f"{today.month}/{today.day}")
    prev0 = day0 - timedelta(days=n_days)
    prev1 = day0 - timedelta(days=1)

    def _task_day(t):
        ts = t.done_at or t.created_at
        return ts.date() if ts else None

    def _duration_min(t):
        if t.status == "done" and t.created_at and t.done_at:
            return max(1, int((t.done_at - t.created_at).total_seconds() // 60))
        return None

    period_durs = []
    prev_durs = []
    day_durs: dict = defaultdict(list)
    done_in_period = 0
    for t, _rm in task_rows:
        d = _task_day(t)
        if not d:
            continue
        dm = _duration_min(t)
        if day0 <= d <= today:
            if (t.status or "") == "done":
                done_in_period += 1
            if dm is not None:
                period_durs.append(dm)
                day_durs[d].append(dm)
        elif prev0 <= d <= prev1 and dm is not None:
            prev_durs.append(dm)
    avg_min = round(sum(period_durs) / len(period_durs)) if period_durs else None
    prev_avg = round(sum(prev_durs) / len(prev_durs)) if prev_durs else None
    if avg_min is not None and prev_avg is not None and (prev_avg > 0):
        duration_delta_pct = round((prev_avg - avg_min) / prev_avg * 100)
    else:
        duration_delta_pct = None
    insp_done = [r for r in insp_rows if (r.status or "") in ("passed", "failed")]
    insp_period = [r for r in insp_done if r.inspected_at and day0 <= r.inspected_at.date() <= today]
    insp_prev = [r for r in insp_done if r.inspected_at and prev0 <= r.inspected_at.date() <= prev1]
    once_pass = (
        round(100 * sum(1 for r in insp_period if r.status == "passed") / len(insp_period)) if insp_period else None
    )
    prev_pass = round(100 * sum(1 for r in insp_prev if r.status == "passed") / len(insp_prev)) if insp_prev else None
    pass_wow = once_pass - prev_pass if once_pass is not None and prev_pass is not None else None
    shift_rows_range = (
        db.query(StaffShift)
        .filter(StaffShift.hotel_id == hotel_id, StaffShift.shift_date >= day0, StaffShift.shift_date <= today)
        .all()
    )
    match = []
    days_ok = 0
    days_with_need = 0
    hours_per_staff = 4.0
    CN_WD = [_t("一"), _t("二"), _t("三"), _t("四"), _t("五"), _t("六"), _t("日")]
    for i in range(n_days):
        d = day0 + timedelta(days=i)
        on_shift = sum(1 for s in shift_rows_range if s.shift_date == d and (s.shift or "") not in ("off", "", None))
        actual_h = round(on_shift * hours_per_staff, 1)
        fc = mcp_forecast_departures(db, hotel_id, d)
        need_rooms = int(fc.get("rooms") or 0)
        need_h = round(need_rooms * 0.5, 1)
        if need_h <= 0 and day_durs.get(d):
            need_h = round(sum(day_durs[d]) / 60, 1)
        day_align = None
        if need_h > 0:
            days_with_need += 1
            day_align = min(100, round(100 * min(actual_h, need_h) / max(need_h, 0.1)))
            if actual_h >= need_h:
                days_ok += 1
        match.append(
            {
                "label": CN_WD[d.weekday()] if n_days <= 7 else f"{d.month}/{d.day}",
                "date": d.isoformat(),
                "need": need_h,
                "ai": need_h,
                "actual": actual_h,
                "need_rooms": need_rooms,
                "on_shift": on_shift,
                "align": day_align,
                "surplus": round(actual_h - need_h, 1) if need_h > 0 else None,
            }
        )
    match_pct = round(100 * days_ok / days_with_need) if days_with_need else None
    range_key = "本周" if pr == "week" else "近30天" if pr == "30d" else "近7天"
    match_note = (
        _t("{range} {ok}/{need} 天实际 ≥ 需求", range=_t(range_key), ok=days_ok, need=days_with_need)
        if days_with_need
        else _t("本区间无需求样本")
    )
    prev_ok = 0
    prev_need_days = 0
    prev_shifts = (
        db.query(StaffShift)
        .filter(StaffShift.hotel_id == hotel_id, StaffShift.shift_date >= prev0, StaffShift.shift_date <= prev1)
        .all()
    )
    for i in range(n_days):
        d = prev0 + timedelta(days=i)
        if d > prev1:
            break
        on_shift = sum(1 for s in prev_shifts if s.shift_date == d and (s.shift or "") not in ("off", "", None))
        actual_h = on_shift * hours_per_staff
        need_rooms = int(mcp_forecast_departures(db, hotel_id, d).get("rooms") or 0)
        need_h = round(need_rooms * 0.5, 1)
        if need_h > 0:
            prev_need_days += 1
            if actual_h >= need_h:
                prev_ok += 1
    prev_match_pct = round(100 * prev_ok / prev_need_days) if prev_need_days else None
    match_wow = match_pct - prev_match_pct if match_pct is not None and prev_match_pct is not None else None
    fc_board = build_ai_forecast(db, hotel_id, days=5)
    gap_people = 0
    gap_focus = None
    for c in (fc_board.get("days") or [])[:5]:
        delta = c.get("delta") or {}
        g = int(delta.get("morning") or 0) + int(delta.get("afternoon") or 0)
        if g > 0 and (not gap_focus):
            gap_focus = c
        gap_people += g
    labor_gap = -gap_people if gap_people else 0
    if gap_people and gap_focus:
        labor_forecast_msg = _t(
            "未来5天预测：退房客单与排班对比，预计缺口约 {n} 人次（主要集中在 {when}）。建议提前调配。",
            n=gap_people,
            when=gap_focus.get("label") or gap_focus.get("date"),
        )
    elif gap_people:
        labor_forecast_msg = _t(
            "未来5天预测：退房客单与排班对比，预计缺口约 {n} 人次。建议提前调配。",
            n=gap_people,
        )
    else:
        labor_forecast_msg = _t("未来5天预测：退房客单与排班对比，暂无明显人力缺口。")
    trend = []
    trend_labels = []
    trend_samples = []
    trend_dates = []
    target_line = []
    if pr == "30d":
        week_bags: dict = defaultdict(list)
        week_order = []
        for i in range(n_days):
            d = day0 + timedelta(days=i)
            wk = d - timedelta(days=d.weekday())
            key = wk.isoformat()
            if key not in week_bags:
                week_order.append(key)
            week_bags[key].extend(day_durs.get(d) or [])
        for key in week_order:
            vals = week_bags[key]
            wk = date.fromisoformat(key)
            trend.append(round(sum(vals) / len(vals), 1) if vals else None)
            trend_samples.append(len(vals))
            trend_labels.append(f"{wk.month}/{wk.day}周")
            trend_dates.append(key)
            target_line.append(28)
    else:
        for i in range(n_days):
            d = day0 + timedelta(days=i)
            vals = day_durs.get(d) or []
            trend.append(round(sum(vals) / len(vals), 1) if vals else None)
            trend_samples.append(len(vals))
            trend_labels.append(CN_WD[d.weekday()] if n_days <= 7 else f"{d.month}/{d.day}")
            trend_dates.append(d.isoformat())
            target_line.append(28)
    heat_n = min(n_days, 7) if pr != "30d" else 7
    heat_day0 = today - timedelta(days=heat_n - 1)
    staff_day_min: dict = defaultdict(lambda: [0.0] * heat_n)
    staff_day_cnt: dict = defaultdict(lambda: [0] * heat_n)
    for t, _rm in task_rows:
        if (t.status or "") != "done" or not t.done_at:
            continue
        d = t.done_at.date()
        if d < heat_day0 or d > today:
            continue
        idx = (d - heat_day0).days
        uid = t.assignee_id
        if not uid:
            continue
        u = users.get(uid)
        nm = u.full_name or u.username if u else f"员工{uid}"
        dm = _duration_min(t) or 30
        staff_day_min[nm][idx] += dm
        staff_day_cnt[nm][idx] += 1
    heat_shifts = (
        db.query(StaffShift)
        .filter(StaffShift.hotel_id == hotel_id, StaffShift.shift_date >= heat_day0, StaffShift.shift_date <= today)
        .all()
    )
    off_by_name_day: dict = defaultdict(set)
    for s in heat_shifts:
        if (s.shift or "") != "off":
            continue
        u = users.get(s.user_id)
        nm = u.full_name or u.username if u else None
        if not nm:
            continue
        idx = (s.shift_date - heat_day0).days
        if 0 <= idx < heat_n:
            off_by_name_day[nm].add(idx)
    heat_labels = [CN_WD[(heat_day0 + timedelta(days=i)).weekday()] for i in range(heat_n)]
    load_heat = []
    for nm, mins in list(staff_day_min.items())[:8]:
        cells = []
        for i in range(heat_n):
            if i in off_by_name_day.get(nm, set()) and staff_day_cnt[nm][i] == 0:
                cells.append({"h": None, "rest": True, "tasks": 0, "avg_min": None})
            elif staff_day_cnt[nm][i] <= 0:
                cells.append({"h": None, "rest": False, "tasks": 0, "avg_min": None})
            else:
                h = round(mins[i] / 60, 1)
                avg_m = round(mins[i] / staff_day_cnt[nm][i])
                cells.append({"h": h, "rest": False, "tasks": staff_day_cnt[nm][i], "avg_min": avg_m})
        load_heat.append({"name": nm, "cells": cells})
    for nm, offs in off_by_name_day.items():
        if any(r["name"] == nm for r in load_heat):
            continue
        cells = [{"h": None, "rest": i in offs, "tasks": 0, "avg_min": None} for i in range(heat_n)]
        load_heat.append({"name": nm, "cells": cells})
        if len(load_heat) >= 8:
            break
    staff_stats: dict = defaultdict(lambda: {"durs": [], "done": 0, "pass": 0, "insp": 0, "high_days": 0})
    for t, _rm in task_rows:
        if (t.status or "") != "done" or not t.done_at:
            continue
        d = t.done_at.date()
        if d < day0 or d > today:
            continue
        u = users.get(t.assignee_id) if t.assignee_id else None
        nm = u.full_name or u.username if u else None
        if not nm:
            continue
        staff_stats[nm]["done"] += 1
        dm = _duration_min(t)
        if dm is not None:
            staff_stats[nm]["durs"].append(dm)
    for r in insp_period:
        nm = (r.inspector or "").strip()
        if not nm:
            continue
        staff_stats[nm]["insp"] += 1
        if r.status == "passed":
            staff_stats[nm]["pass"] += 1
    for row in load_heat:
        high = sum(1 for c in row["cells"] if c.get("h") is not None and c["h"] > 3)
        if row["name"] in staff_stats:
            staff_stats[row["name"]]["high_days"] = high
    staff_top = []
    by_avg = sorted(
        [(n, s) for n, s in staff_stats.items() if s["durs"]], key=lambda x: sum(x[1]["durs"]) / len(x[1]["durs"])
    )
    if by_avg:
        n, s = by_avg[0]
        avg = round(sum(s["durs"]) / len(s["durs"]))
        staff_top.append({"rank": 1, "name": n, "metric": _t("平均时长最短"), "value": f"{avg} min", "kind": "speed"})
    by_done = sorted(staff_stats.items(), key=lambda x: x[1]["done"], reverse=True)
    if by_done and by_done[0][1]["done"] > 0:
        n, s = by_done[0]
        if not any(x["name"] == n and x["kind"] == "speed" for x in staff_top):
            staff_top.append(
                {
                    "rank": len(staff_top) + 1,
                    "name": n,
                    "metric": _t("完成任务最多"),
                    "value": _t("{n} 单", n=s["done"]),
                    "kind": "volume",
                }
            )
        elif len(by_done) > 1:
            n, s = by_done[1]
            staff_top.append(
                {
                    "rank": len(staff_top) + 1,
                    "name": n,
                    "metric": _t("完成任务最多"),
                    "value": _t("{n} 单", n=s["done"]),
                    "kind": "volume",
                }
            )
    by_pass = sorted(
        [(n, s) for n, s in staff_stats.items() if s["insp"] >= 1],
        key=lambda x: x[1]["pass"] / max(1, x[1]["insp"]),
        reverse=True,
    )
    if by_pass:
        n, s = by_pass[0]
        pct = round(100 * s["pass"] / s["insp"])
        staff_top.append(
            {
                "rank": len(staff_top) + 1,
                "name": n,
                "metric": _t("一次通过率最高"),
                "value": f"{pct}%",
                "kind": "quality",
            }
        )
    warn = sorted(staff_stats.items(), key=lambda x: x[1]["high_days"], reverse=True)
    if warn and warn[0][1]["high_days"] >= 2:
        n, s = warn[0]
        staff_top.append(
            {
                "rank": len(staff_top) + 1,
                "name": n,
                "metric": _t("连续 {n} 天高负荷预警", n=s["high_days"]),
                "value": _t("需关注"),
                "kind": "warn",
            }
        )
    insights = []
    if period_durs and avg_min is not None:
        insights.append(
            {
                "t": _t("清扫时长"),
                "d": _t(
                    "本区间平均清扫 {n} min（样本 {s} 单，目标 28 min）{tip}",
                    n=avg_min,
                    s=len(period_durs),
                    tip=_t("，偏高建议关注退房高峰派工。") if avg_min > 30 else "。",
                ),
                "c": "var(--primary)",
                "action": _t("去派单"),
                "link": "/c6-housekeeping/housekeeping",
            }
        )
    if days_with_need:
        insights.append(
            {
                "t": _t("排班吻合"),
                "d": match_note
                + (_t("，规划偏松可微调班次。") if match_pct and match_pct >= 90 else _t("，存在不足日建议补班。")),
                "c": "var(--tertiary)",
                "action": _t("去排班"),
                "link": "/c6-housekeeping/staffing",
            }
        )
    if insp_period and once_pass is not None:
        insights.append(
            {
                "t": _t("查房质量"),
                "d": _t("一次通过率 {pct}%（样本 {n}），目标 92%。", pct=once_pass, n=len(insp_period)),
                "c": "var(--outline)",
                "action": _t("去派单"),
                "link": "/c6-housekeeping/housekeeping",
            }
        )
    if not insights:
        insights.append(
            {
                "t": _t("样本提示"),
                "d": _t("本区间完成时长/查房样本仍较少，指标随作业闭环会更稳定。"),
                "c": "var(--outline)",
            }
        )

    def _kpi_val(v):
        return "—" if v is None else str(v)

    def _wow_txt(v):
        if v is None:
            return _t("无上期数据")
        sign = "+" if v > 0 else ""
        return f"{sign}{v}%"

    period_tag = _t("本周") if pr == "week" else _t("近 30 天") if pr == "30d" else _t("近 7 天")
    performance = {
        "kpis": [
            {
                "label": _t("平均清扫时长"),
                "value": _kpi_val(avg_min),
                "unit": "min" if avg_min is not None else "",
                "up": None if duration_delta_pct is None else duration_delta_pct >= 0,
                "ico": "timer",
                "group": "efficiency",
                "group_label": _t("效率"),
                "target": "28",
                "target_unit": "min",
                "wow": _wow_txt(duration_delta_pct),
                "wow_available": duration_delta_pct is not None,
                "sample": len(period_durs),
                "period": period_tag,
            },
            {
                "label": _t("查房一次通过率"),
                "value": _kpi_val(once_pass),
                "unit": "%" if once_pass is not None else "",
                "up": None if pass_wow is None else pass_wow >= 0,
                "ico": "fact_check",
                "group": "quality",
                "group_label": _t("质量"),
                "target": "92",
                "target_unit": "%",
                "wow": _wow_txt(pass_wow),
                "wow_available": pass_wow is not None,
                "sample": len(insp_period),
                "period": period_tag,
            },
            {
                "label": _t("排班吻合度"),
                "value": _kpi_val(match_pct),
                "unit": "%" if match_pct is not None else "",
                "up": None if match_wow is None else match_wow >= 0,
                "ico": "smart_toy",
                "group": "planning",
                "group_label": _t("规划"),
                "target": "90",
                "target_unit": "%",
                "wow": _wow_txt(match_wow),
                "wow_available": match_wow is not None,
                "note": match_note,
                "period": period_tag,
            },
        ],
        "labor_gap": labor_gap,
        "labor_forecast": {"gap": labor_gap, "people": gap_people, "message": labor_forecast_msg, "focus": gap_focus},
        "range": pr,
        "range_label": range_label,
        "period_tag": period_tag,
        "trend": trend,
        "trend_labels": trend_labels,
        "trend_samples": trend_samples,
        "trend_dates": trend_dates,
        "target": target_line,
        "insights": insights,
        "quality": load_heat,
        "load_heat": load_heat,
        "heat_labels": heat_labels,
        "match": match,
        "match_target": 90,
        "match_note": match_note,
        "match_days_ok": days_ok,
        "match_days_need": days_with_need,
        "staff_top": staff_top,
        "done_in_period": done_in_period,
        "samples": {"duration": len(period_durs), "inspection": len(insp_period), "align_days": days_with_need},
    }
    from hk.hk_live_cache import cache_get, cache_set

    today_start = datetime.combine(today, datetime.min.time())
    done_today = [t for t, _rm in task_rows if (t.status or "") == "done" and t.done_at and (t.done_at >= today_start)]
    workload = len(done_today) + to_clean_n
    completion_progress = round(100 * len(done_today) / workload) if workload else None
    yday = today - timedelta(days=1)
    y0 = datetime.combine(yday, datetime.min.time())
    y1 = datetime.combine(today, datetime.min.time())
    done_yday = sum((1 for t, _ in task_rows if (t.status or "") == "done" and t.done_at and (y0 <= t.done_at < y1)))
    wow_progress = None
    if completion_progress is not None and done_yday > 0 and (len(done_today) > 0):
        wow_progress = round((len(done_today) - done_yday) / done_yday * 100)
    today_durs = [m for m in (_duration_min(t) for t in done_today) if m is not None]
    avg_today = round(sum(today_durs) / len(today_durs)) if today_durs else None
    sample_today = len(today_durs)
    shift_code = "night" if now_h >= 16 else "afternoon" if now_h >= 12 else "morning"
    if shift_code == "morning":
        sh0, sh1 = (8, 16)
    elif shift_code == "afternoon":
        sh0, sh1 = (12, 20)
    else:
        sh0, sh1 = (16, 24)
    d7 = today - timedelta(days=6)
    shift_durs = []
    for t, _rm in task_rows:
        if (t.status or "") != "done" or not t.done_at or (not t.created_at):
            continue
        if t.done_at.date() < d7:
            continue
        h = t.done_at.hour
        if sh0 <= h < sh1:
            dm = _duration_min(t)
            if dm is not None:
                shift_durs.append(dm)
    avg_7d_shift = round(sum(shift_durs) / len(shift_durs)) if shift_durs else None
    sample_7d = len(shift_durs)
    if sample_today >= 5 and avg_today is not None:
        avg_display = avg_today
        avg_basis = "today"
        avg_note = f"基于今日 {sample_today} 单"
    elif avg_7d_shift is not None:
        avg_display = avg_7d_shift
        avg_basis = "7d_shift"
        avg_note = (
            f"近7天同班次平均（今日仅 {sample_today} 单）"
            if sample_today
            else f"近7天同班次平均（基于 {sample_7d} 单）"
        )
    elif avg_today is not None:
        avg_display = avg_today
        avg_basis = "today"
        avg_note = f"基于今日 {sample_today} 单（样本偏少）"
    else:
        avg_display = None
        avg_basis = None
        avg_note = "暂无完成时长样本"
    cache_key = f"hk_heat:{hotel_id}:{today.isoformat()}"
    cached_heat = cache_get(cache_key)
    if cached_heat and isinstance(cached_heat, dict):
        floor_hour_heatmap = cached_heat.get("floor_hour_heatmap") or []
    else:
        floor_hour: dict = defaultdict(lambda: [0] * 12)
        for t, rm in task_rows:
            ts = t.created_at or t.due_at
            fl = rm.floor if rm else None
            if not ts or not fl:
                continue
            try:
                if ts.date() != today:
                    continue
            except Exception:
                continue
            h = ts.hour
            if 8 <= h <= 19:
                floor_hour[fl][h - 8] += 1
        floors_sorted = sorted(floor_hour.keys()) or sorted({r.floor for r in rooms if r.floor})
        fl_cap: dict = {}
        for fl in floors_sorted:
            n_staff_fl = floor_staff.get(fl, 0)
            if n_staff_fl <= 0:
                n_staff_fl = max(1, on_duty) / max(1, len(floors_sorted))
            fl_cap[fl] = max(0.5, n_staff_fl * std_rooms_per_hour)
        floor_hour_heatmap = []
        for fl in floors_sorted:
            counts = floor_hour.get(fl) or [0] * 12
            cap = fl_cap[fl]
            levels = [_ratio_level(n, cap) for n in counts]
            ratios = [round(n / cap, 2) if n else 0 for n in counts]
            floor_hour_heatmap.append(
                {
                    "floor": fl,
                    "label": f"{fl}F",
                    "slots": levels,
                    "counts": counts,
                    "capacity": round(cap, 1),
                    "ratios": ratios,
                }
            )
        cache_set(cache_key, {"floor_hour_heatmap": floor_hour_heatmap}, ttl=30)
    labor_today = {
        "completion_progress": completion_progress,
        "fulfillment": completion_progress,
        "metric_name": "今日完成进度",
        "target_fulfill": 90,
        "wow_fulfill": wow_progress,
        "done_today": len(done_today),
        "to_clean": to_clean_n,
        "open_tasks": to_clean_n,
        "avg_min_today": avg_today,
        "avg_min_display": avg_display,
        "avg_sample_today": sample_today,
        "avg_sample_7d": sample_7d,
        "avg_basis": avg_basis,
        "avg_note": avg_note,
        "waiting": waiting_n,
        "progress": progress_n,
        "inspect": inspect_n,
        "on_duty": on_duty,
        "on_duty_source": on_duty_source,
        "on_duty_label": on_duty_label,
        "scheduled_on": scheduled_n,
        "rooms_total": rooms_total,
        "dirty": dirty,
        "vacant": vacant,
        "occupied": occupied,
        "ooo": ooo,
        "peak_label": peak_label,
        "peak_kind": peak_kind,
        "decision_text": decision_text,
        "dispatch_suggest": dispatch_suggest,
        "route_count": 0,
        "route_excluded": [],
        "floor_hour_heatmap": floor_hour_heatmap,
        "heatmap_formula": "该时段新增任务数 ÷ 该楼层当前产能（在岗×2间/时）；绿≤80% 黄80–120% 红>120%",
        "cache_ttl_sec": 30,
    }
    vision_rooms = []
    history = []
    detail = {
        "room": "—",
        "uploader": staff[0]["name"] if staff else "房务",
        "time": "—",
        "findings": [],
        "boxes": [],
        "summary": "",
        "score": 0,
    }
    pending_rows = [r for r in insp_rows if (r.status or "") == "pending"]
    done_rows = [r for r in insp_rows if (r.status or "") in ("passed", "failed")]

    def _parse_findings(row):
        try:
            return _json.loads(row.findings_json or "[]")
        except Exception:
            return []

    _photo = "/demo/room-inspection.jpg"
    for i, row in enumerate(pending_rows[:12]):
        findings = _parse_findings(row)
        need = any(not f.get("ok", True) for f in findings)
        rm = db.get(Room, row.room_id) if row.room_id else None
        vision_rooms.append(
            {
                "id": row.id,
                "room": row.room_no or "—",
                "type": row.summary or "空净待查",
                "floor": f"{rm.floor}F" if rm and rm.floor else "—",
                "aiReviewed": False,
                "needAction": need,
                "note": row.inspector or "待查房",
                "active": i == 0,
                "score": row.score,
                "findings": findings,
                "inspector": row.inspector,
                "time": row.inspected_at.strftime("%H:%M") if row.inspected_at else "—",
                "summary": row.summary,
                "photo_url": _photo,
            }
        )
    if not vision_rooms:
        for x in tasks:
            if x["task_type"] == "inspect" or x["type"] == "inspect":
                vision_rooms.append(
                    {
                        "id": x["id"],
                        "room": x["room_no"],
                        "type": x["title"],
                        "floor": f"{x['floor']}F" if x.get("floor") else "—",
                        "aiReviewed": x["status"] == "done",
                        "needAction": x["status"] != "done" and x["priority"],
                        "note": x["assignee"],
                        "active": False,
                        "findings": [],
                    }
                )
        if not vision_rooms:
            for r in rooms:
                if r.status in ("vacant", "clean"):
                    vision_rooms.append(
                        {
                            "id": r.id,
                            "room": r.room_no,
                            "type": "空净待查",
                            "floor": f"{r.floor}F" if r.floor else "—",
                            "aiReviewed": False,
                            "needAction": False,
                            "note": "待查房",
                            "active": False,
                            "findings": [],
                        }
                    )
                if len(vision_rooms) >= 8:
                    break
        if vision_rooms:
            vision_rooms[0]["active"] = True
    if vision_rooms:
        cur = vision_rooms[0]
        findings = cur.get("findings") or []
        boxes = []
        for f in findings:
            box = f.get("box") or {}
            boxes.append(
                {
                    "label": f.get("label") or "检测",
                    "ok": bool(f.get("ok", True)),
                    "confidence": f.get("confidence"),
                    "t": box.get("t", "30%"),
                    "l": box.get("l", "20%"),
                    "w": box.get("w", "30%"),
                    "h": box.get("h", "20%"),
                }
            )
        detail = {
            "id": cur.get("id"),
            "room": cur.get("room"),
            "uploader": cur.get("inspector") or cur.get("note") or (staff[0]["name"] if staff else "房务"),
            "time": cur.get("time") or datetime.now().strftime("%H:%M"),
            "findings": findings,
            "boxes": boxes,
            "summary": cur.get("summary") or "",
            "score": cur.get("score") or 0,
            "photo_url": cur.get("photo_url") or _photo,
        }
    for row in done_rows[:10]:
        history.append(
            {
                "room": row.room_no,
                "time": row.inspected_at.strftime("%m-%d %H:%M") if row.inspected_at else "—",
                "result": "fail" if row.status == "failed" else "pass",
                "inspector": row.inspector,
                "score": row.score,
            }
        )
    trend_vision = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        day_rows = [r for r in done_rows if r.inspected_at and r.inspected_at.date() == day]
        if day_rows:
            passed = sum(1 for r in day_rows if r.status == "passed")
            pct = round(100 * passed / len(day_rows))
        else:
            pct = None
        trend_vision.append(
            {
                "day": ["一", "二", "三", "四", "五", "六", "日"][day.weekday()],
                "pct": pct,
                "date": day.isoformat(),
                "sample": len(day_rows),
            }
        )
    inspected_n = len(done_rows)
    pending_n = len(pending_rows) if pending_rows else sum(1 for v in vision_rooms if not v.get("aiReviewed"))
    vision = {
        "stats": {
            "pending": pending_n,
            "inspected": inspected_n,
            "total": pending_n + inspected_n or len(vision_rooms),
            "pass_rate": round(100 * sum(1 for r in done_rows if r.status == "passed") / inspected_n)
            if inspected_n
            else None,
        },
        "rooms": vision_rooms[:12],
        "detail": detail,
        "trend": trend_vision,
        "history": history,
    }
    ooo_room_nos = {r.room_no for r in rooms if _rst_norm(r.status) in (OOO, BLK) and r.room_no}
    waiting_tasks = [x for x in tasks if x["status"] == "waiting"]
    route_excluded = []
    route_pool = []
    for x in waiting_tasks:
        rn = x.get("room_no")
        if rn and rn in ooo_room_nos:
            route_excluded.append({"id": x.get("id"), "room_no": rn, "reason": "维修/锁房"})
        else:
            route_pool.append(x)
    route = sorted(route_pool, key=lambda x: (x.get("floor") or 99, x.get("room_no") or ""))
    for i, n in enumerate(route):
        n["tag"] = "高优" if n["priority"] else "查房" if n["type"] == "inspect" else "脏房"
        n["seq"] = i + 1
        if n.get("elapsed_min"):
            n["eta"] = f"已耗时 {n['elapsed_min']} 分"
        elif n.get("deadline"):
            n["eta"] = f"截止 {n['deadline']}"
        else:
            n["eta"] = None
    labor_today["route_count"] = len(route)
    labor_today["route_excluded"] = route_excluded
    labor_today["waiting"] = waiting_n
    if route_excluded:
        labor_today["route_note"] = (
            f"待分配 {waiting_n} 间，路径规划 {len(route)} 间（已排除 {len(route_excluded)} 间："
            + "、".join(f"{e['room_no']}{e['reason']}" for e in route_excluded[:5])
            + ("…" if len(route_excluded) > 5 else "")
            + "）"
        )
    else:
        labor_today["route_note"] = f"待分配 {waiting_n} 间，路径规划 {len(route)} 间"
    care = None
    open_list = [x for x in service_requests if x["open"]]
    if open_list:
        top = open_list[0]
        care = {
            "room": top["room"],
            "badge": "高优推荐" if (top.get("priority") or 3) <= 2 else "主动关怀",
            "note": f"未结客需：{top['content']}。建议优先派送并回写工单状态。",
        }
    assignee_by_room = {}
    tip_by_room = {}
    for x in tasks:
        if x.get("room_no") and x["status"] != "done":
            assignee_by_room[x["room_no"]] = x.get("assignee") or "待分配"
            if x.get("tip"):
                tip_by_room[x["room_no"]] = x["tip"]
    sr_by_room = {}
    for x in service_requests:
        if x.get("open") and x.get("room_no") and (x["room_no"] not in sr_by_room):
            sr_by_room[x["room_no"]] = x.get("content") or ""
    stay_by_room_id: dict = {}
    for res, od, g in (
        db.query(Reservation, Order, Guest)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .all()
    ):
        if res.room_id:
            stay_by_room_id[res.room_id] = (od, g)
    room_cards = []
    for r in rooms:
        od, g = stay_by_room_id.get(r.id, (None, None))
        tip = tip_by_room.get(r.room_no)
        if not tip and sr_by_room.get(r.room_no):
            tip = f"未结客需：{sr_by_room[r.room_no][:28]}"
        room_cards.append(
            {
                "id": r.id,
                "room_no": r.room_no,
                "status": r.status,
                "floor": r.floor,
                "room_type_name": None,
                "assignee": assignee_by_room.get(r.room_no) or "未分配人员",
                "guest_name": g.name if g else None,
                "check_out": od.check_out.strftime("%m-%d") if od and od.check_out else None,
                "open_request": sr_by_room.get(r.room_no),
                "ai_tip": tip,
            }
        )
    rt_map = {rt.id: rt.name for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}
    for r, card in zip(rooms, room_cards):
        card["room_type_name"] = rt_map.get(r.room_type_id) or ""
    return {
        "tasks": tasks,
        "schedule": [x for x in tasks if x["status"] != "done"][:8],
        "queue": tasks,
        "staff": staff,
        "service_requests": service_requests,
        "stream": service_requests[:8],
        "care": care,
        "route": route,
        "dispatch_alert": dispatch_alert,
        "status_snapshot": status_snapshot,
        "floor_heatmap": floor_heatmap,
        "hour_slots": hour_slots,
        "floor_hour_heatmap": labor_today.get("floor_hour_heatmap") or [],
        "labor_today": labor_today,
        "performance": performance,
        "vision": vision,
        "rooms": room_cards,
        "room_status": {
            "total": len(rooms),
            "dirty": dirty,
            "cleaning": cleaning,
            "vacant": vacant,
            "ooo": ooo,
            "occupied": occupied,
            "by_status": by_status,
        },
        "counts": {
            "open_tasks": open_tasks,
            "open_requests": open_sr,
            "done_tasks": sum(1 for x in tasks if x["status"] == "done"),
            "staff_on": len(staff),
        },
        "flow_hint": status_snapshot["text"],
    }
