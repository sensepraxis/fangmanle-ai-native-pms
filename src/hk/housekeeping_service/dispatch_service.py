# SPDX-License-Identifier: Apache-2.0
# hk.housekeeping_service.dispatch_service — auto-split by AST

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

from fastapi import HTTPException  # noqa: F401  (except 分支用)
from sqlalchemy.orm import Session

import models as _models
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.branding import app_name
from models import HousekeepingTask, Room, User

globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})
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
from hk.housekeeping_service import task_service as _hk_task_service


def _pick_attendant(db: Session, hotel_id: int, room_id: Optional[int] = None) -> Optional[int]:
    """按当日排班在岗人派单：同楼层优先，其次开放任务少。全员休息则不指派。"""
    from models import Role

    floor: Optional[int] = None
    if room_id:
        rm = db.get(Room, int(room_id))
        if rm and rm.floor is not None:
            try:
                floor = int(rm.floor)
            except (TypeError, ValueError):
                floor = None
    on_duty = _hk_dispatch_service._on_duty_staff(db, hotel_id)
    if on_duty:
        scored: list[tuple[int, int, int]] = []
        for s in on_duty:
            floors = s.get("floors") or []
            same = 0 if floor is not None and floor in floors else 1
            scored.append((same, int(s.get("open") or 0), int(s["id"])))
        scored.sort()
        return scored[0][2]
    from datetime import date

    from models import StaffShift

    had_today = db.query(StaffShift).filter_by(hotel_id=hotel_id, shift_date=date.today()).first() is not None
    if had_today:
        return None
    hk = db.query(Role).filter_by(code="hk").first()
    if hk:
        u = db.query(User).filter_by(hotel_id=hotel_id, role_id=hk.id, is_active=True).order_by(User.id.asc()).first()
        if u:
            return u.id
    u = db.query(User).filter_by(hotel_id=hotel_id, is_active=True).first()
    return u.id if u else None


def _resolve_assignee_id(
    db: Session, hotel_id: int, *, assignee_id: Optional[int] = None, assignee_name: Optional[str] = None
) -> Optional[int]:
    """按 id 或姓名解析本店用户；找不到则返回 None。"""
    if assignee_id:
        u = db.get(User, int(assignee_id))
        if u and u.is_active and (u.hotel_id is None or u.hotel_id == hotel_id):
            return u.id
        raise InvalidStateError("执行人不存在或不属于本店")
    name = (assignee_name or "").strip()
    if not name:
        return None
    users = db.query(User).filter(User.is_active == True, (User.hotel_id == hotel_id) | User.hotel_id.is_(None)).all()
    for u in users:
        if (u.full_name or "").strip() == name or (u.username or "").strip() == name:
            return u.id
    for u in users:
        fn = (u.full_name or "").strip()
        un = (u.username or "").strip()
        if name in fn or name in un or fn in name:
            return u.id
    raise InvalidStateError(f"未找到执行人「{name}」")


def _parse_floors_from_text(text: str) -> list[int]:
    import re

    s = text or ""
    floors: list[int] = []
    for m in re.finditer("(\\d+)\\s*[-~～至到]\\s*(\\d+)\\s*[楼層Ff]?", s):
        a, b = (int(m.group(1)), int(m.group(2)))
        floors.extend(range(min(a, b), max(a, b) + 1))
    for m in re.finditer("(?<!\\d)(\\d{1,2})\\s*[楼層Ff]", s):
        floors.append(int(m.group(1)))
    return sorted(set(floors))


def _on_duty_staff(db: Session, hotel_id: int) -> list[dict]:
    """当日排班保洁 + 开放任务负荷。"""
    from datetime import date

    from hk.staffing_service import canon_shift
    from models import Role, StaffShift

    today_rows = (
        db.query(StaffShift).filter_by(hotel_id=hotel_id, shift_date=date.today()).order_by(StaffShift.id.asc()).all()
    )
    had_today = bool(today_rows)
    shifts = today_rows
    if not shifts:
        shifts = (
            db.query(StaffShift)
            .filter_by(hotel_id=hotel_id)
            .order_by(StaffShift.shift_date.desc(), StaffShift.id.asc())
            .limit(12)
            .all()
        )
    hk_role = db.query(Role).filter_by(code="hk").first()
    users = {
        u.id: u
        for u in db.query(User)
        .filter(User.is_active == True, (User.hotel_id == hotel_id) | User.hotel_id.is_(None))
        .all()
    }
    open_rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned", "in_progress", "rework")),
        )
        .all()
    )
    load: dict[int, int] = {}
    floor_load: dict[int, list[int]] = {}
    for t, rm in open_rows:
        if not t.assignee_id:
            continue
        load[t.assignee_id] = load.get(t.assignee_id, 0) + 1
        if rm and rm.floor:
            floor_load.setdefault(t.assignee_id, []).append(int(rm.floor))
    out: list[dict] = []
    seen = set()
    for s in shifts:
        if s.user_id in seen:
            continue
        code = canon_shift(s.shift)
        if code == "off":
            continue
        u = users.get(s.user_id)
        if not u:
            continue
        if hk_role and u.role_id and (u.role_id != hk_role.id):
            pass
        floors = _parse_floors_from_text(s.handover_note or "")
        if not floors and floor_load.get(u.id):
            from collections import Counter

            floors = [fl for fl, _ in Counter(floor_load[u.id]).most_common(3)]
        seen.add(u.id)
        out.append(
            {
                "id": u.id,
                "name": u.full_name or u.username,
                "username": u.username,
                "shift": code,
                "note": s.handover_note or "",
                "floors": floors,
                "open": load.get(u.id, 0),
                "area_floor": floors[0] if floors else None,
            }
        )
    if not out:
        if had_today:
            return []
        for u in list(users.values())[:6]:
            out.append(
                {
                    "id": u.id,
                    "name": u.full_name or u.username,
                    "username": u.username,
                    "shift": "morning",
                    "note": "",
                    "floors": [],
                    "open": load.get(u.id, 0),
                    "area_floor": None,
                }
            )
    claimed = {f for s in out for f in s["floors"]}
    hotel_floors = sorted(
        {
            int(r.floor)
            for r in db.query(Room.floor).filter_by(hotel_id=hotel_id).all()
            if r.floor is not None and int(r.floor) > 0
        }
    )
    if out and (not claimed) and hotel_floors:
        n = len(hotel_floors)
        for i, s in enumerate(out):
            if n == 1:
                s["floors"] = hotel_floors[:]
            else:
                s["floors"] = [hotel_floors[i % n], hotel_floors[(i + 1) % n]]
            s["area_floor"] = s["floors"][0]
    return out


def _plan_batch_dispatch(
    db: Session, hotel_id: int, task_ids: list[int], *, mode: str, assignee_id: Optional[int] = None
) -> list[dict]:
    """生成分配方案（不写库）。每项: task, room, assignee_id, assignee, floor, reason。"""
    if not task_ids:
        raise InvalidStateError("请选择任务")
    mode = (mode or "single").strip().lower()
    rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(HousekeepingTask.hotel_id == hotel_id, HousekeepingTask.id.in_(task_ids))
        .all()
    )
    by_id = {t.id: (t, rm) for t, rm in rows}
    missing = [i for i in task_ids if i not in by_id]
    if missing:
        raise NotFoundError(f"任务不存在：{missing[:5]}")
    staff = _hk_dispatch_service._on_duty_staff(db, hotel_id)
    if not staff:
        raise InvalidStateError("暂无可用保洁人员")
    plan: list[dict] = []
    ordered = [(by_id[i][0], by_id[i][1]) for i in task_ids]
    if mode == "single":
        aid = _hk_dispatch_service._resolve_assignee_id(db, hotel_id, assignee_id=assignee_id)
        if not aid:
            raise InvalidStateError("指定一人模式请选择保洁员")
        u = db.get(User, aid)
        name = u.full_name or u.username if u else str(aid)
        for t, rm in ordered:
            if t.status in ("done", "ignored", "closed", "pending_inspect"):
                continue
            plan.append(
                {
                    "task_id": t.id,
                    "room_no": rm.room_no if rm else "—",
                    "floor": rm.floor if rm else None,
                    "assignee_id": aid,
                    "assignee": name,
                    "reason": "指定一人",
                }
            )
        return plan
    if mode == "by_floor":
        floor_owner: dict[int, dict] = {}
        for s in staff:
            for fl in s["floors"] or []:
                floor_owner.setdefault(int(fl), s)
        rr = 0
        for t, rm in ordered:
            if t.status in ("done", "ignored", "closed", "pending_inspect"):
                continue
            fl = int(rm.floor) if rm and rm.floor else None
            s = floor_owner.get(fl) if fl else None
            if not s:
                s = staff[rr % len(staff)]
                rr += 1
                reason = f"楼层{fl or '?'}无专职，轮询派给 {s['name']}"
            else:
                reason = f"{fl}F 区域负责人"
            plan.append(
                {
                    "task_id": t.id,
                    "room_no": rm.room_no if rm else "—",
                    "floor": fl,
                    "assignee_id": s["id"],
                    "assignee": s["name"],
                    "reason": reason,
                }
            )
        return plan
    loads = {s["id"]: int(s["open"] or 0) for s in staff}
    staff_by_id = {int(s["id"]): s for s in staff}
    hour = datetime.now().hour
    for t, rm in ordered:
        if t.status in ("done", "ignored", "closed", "pending_inspect"):
            continue
        fl = int(rm.floor) if rm and rm.floor else None
        # RuleEngine：VIP / 紧急度 / 凌晨升级等（assignee_id 仅当在岗才采纳）
        rule_ctx = _hk_dispatch_rule_context(db, t, rm, staff=staff, hour=hour)
        try:
            import hk.hk_rules  # noqa: F401 确保规则集已注册
            from rules import apply as apply_rules

            apply_rules("hk_dispatch", rule_ctx)
        except Exception:
            pass
        forced_aid = rule_ctx.get("assignee_id")
        rule_reason = (rule_ctx.get("dispatch_reason") or "").strip()
        priority_boost = bool(rule_ctx.get("priority_boost"))
        if forced_aid is not None and int(forced_aid) in staff_by_id:
            best = staff_by_id[int(forced_aid)]
            reason = rule_reason or f"规则派单 → {best['name']}"
        else:

            def score(s: dict) -> tuple:
                floor_hit = 0
                if fl and fl in (s.get("floors") or []):
                    floor_hit = -20
                elif fl and s.get("area_floor") and (abs(int(s["area_floor"]) - fl) <= 1):
                    floor_hit = -8
                boost = -15 if priority_boost and fl and fl in (s.get("floors") or []) else 0
                return (loads.get(s["id"], 0) + floor_hit + boost, loads.get(s["id"], 0), s["id"])

            best = min(staff, key=score)
            reason = "智能：低负载"
            if rule_reason:
                reason = f"{rule_reason} + 低负载"
            elif fl and fl in (best.get("floors") or []):
                reason = f"智能：同楼层{fl}F + 低负载"
            elif fl and best.get("area_floor"):
                reason = f"智能：就近{best['area_floor']}F区 + 低负载"
            if rule_ctx.get("escalation") == "night_team":
                reason = f"夜班升级 · {reason}"
        loads[best["id"]] = loads.get(best["id"], 0) + 1
        plan.append(
            {
                "task_id": t.id,
                "room_no": rm.room_no if rm else "—",
                "floor": fl,
                "assignee_id": best["id"],
                "assignee": best["name"],
                "reason": reason,
            }
        )
    return plan


def _hk_dispatch_rule_context(
    db: Session, task: HousekeepingTask, rm: Optional[Room], *, staff: list[dict], hour: int
) -> dict:
    """为 hk_dispatch RuleSet 组装上下文（guest_vip / urgency / 楼层等）。"""
    guest_vip = False
    try:
        from models import Guest, Order, Reservation

        order_id = getattr(task, "order_id", None)
        guest_id = None
        if order_id:
            o = db.get(Order, int(order_id))
            guest_id = o.guest_id if o else None
        if not guest_id and rm is not None:
            res = db.query(Reservation).filter_by(room_id=rm.id).order_by(Reservation.id.desc()).first()
            if res and res.order_id:
                o = db.get(Order, res.order_id)
                guest_id = o.guest_id if o else None
        if guest_id:
            g = db.get(Guest, int(guest_id))
            lvl = (g.vip_level or "normal").strip().lower() if g else "normal"
            guest_vip = lvl not in ("", "normal", "普通", "普通会员")
    except Exception:
        guest_vip = False
    fl = int(rm.floor) if rm and rm.floor else None
    staff_floor = None
    if fl is not None:
        for s in staff:
            if fl in (s.get("floors") or []):
                staff_floor = fl
                break
        if staff_floor is None and staff:
            staff_floor = staff[0].get("area_floor")
    urgency = int(task.priority or 5)
    return {
        "task_id": task.id,
        "hotel_id": task.hotel_id,
        "guest_vip": guest_vip,
        "hour": hour,
        "room_floor": fl,
        "staff_floor": staff_floor,
        "urgency": urgency,
    }


def notify_hk_dispatch_wecom(db: Session, hotel_id: int, *, assignee_id: int, rooms: list[str]) -> dict:
    """经 messaging 通道通知保洁（失败不阻断派单，返回 pushed=false）。"""
    u = db.get(User, assignee_id)
    name = u.full_name or u.username if u else str(assignee_id)
    rooms_txt = "/".join(rooms[:8]) + ("…" if len(rooms) > 8 else "")
    content = f"【{app_name()} · 新清洁任务】\n您好 {name}，主管刚派给您 {len(rooms)} 间：{rooms_txt}\n请尽快在 PMS / 企微接单并开始清扫。"
    try:
        from messaging import notify_staff

        touser = u.username if u and u.username and (not str(u.username).startswith("admin")) else None
        result = notify_staff(hotel_id=hotel_id, content=content, userid=touser, db=db)
        return {
            "assignee_id": assignee_id,
            "name": name,
            "rooms": rooms,
            "pushed": bool(result.get("pushed")),
            "touser": result.get("touser"),
            "hint": result.get("hint"),
        }
    except Exception as e:
        return {
            "assignee_id": assignee_id,
            "name": name,
            "rooms": rooms,
            "pushed": False,
            "hint": f"已记队列：{str(e)[:100]}",
            "queued": True,
        }


def batch_dispatch(
    db: Session,
    hotel_id: int,
    task_ids: list[int],
    *,
    mode: str = "single",
    assignee_id: Optional[int] = None,
    preview: bool = False,
    operator_id: Optional[int] = None,
    notify: bool = True,
) -> dict:
    """
    批量派单：待分配 → 指派并开始（in_progress）。
    mode: single | by_floor | smart
    """
    try:
        from hk.hk_live_cache import cache_invalidate

        cache_invalidate(f"hk_heat:{hotel_id}:")
    except Exception:
        pass
    plan = _plan_batch_dispatch(db, hotel_id, [int(x) for x in task_ids], mode=mode, assignee_id=assignee_id)
    if not plan:
        raise InvalidStateError("所选任务均不可派单（可能已完成/已忽略）")
    if preview:
        return {"preview": True, "mode": mode, "items": plan, "count": len(plan)}
    assigned = []
    for item in plan:
        t = _hk_task_service.start_task(db, item["task_id"], operator_id=operator_id, assignee_id=item["assignee_id"])
        assigned.append({**item, "status": t.status})
    if assigned:
        from events import emit

        emit(
            "hk.batch_dispatched",
            {
                "hotel_id": hotel_id,
                "mode": mode,
                "count": len(assigned),
                "task_ids": [x["task_id"] for x in assigned],
                "operator_id": operator_id,
            },
        )
    wecom_out = []
    if notify:
        from collections import defaultdict

        by_user: dict[int, list[str]] = defaultdict(list)
        for item in assigned:
            by_user[item["assignee_id"]].append(item["room_no"])
        for uid, rooms in by_user.items():
            wecom_out.append(_hk_dispatch_service.notify_hk_dispatch_wecom(db, hotel_id, assignee_id=uid, rooms=rooms))
    return {"preview": False, "mode": mode, "items": assigned, "count": len(assigned), "wecom": wecom_out}


def _pick_staff_for_floor(staff: list[dict], floor: Optional[int]) -> Optional[dict]:
    idle = [s for s in staff if s.get("status") != "rest"]
    if not idle:
        return None
    if floor:
        same = [s for s in idle if floor in (s.get("floors") or [])]
        pool = same or idle
    else:
        pool = idle
    pool = sorted(pool, key=lambda s: (s.get("open") or 0, s["id"]))
    return pool[0]


def _waiting_dispatch_rows(db: Session, hotel_id: int) -> list[tuple[HousekeepingTask, Optional[Room]]]:
    return (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(HousekeepingTask.hotel_id == hotel_id, HousekeepingTask.status.in_(("open", "assigned", "rework")))
        .order_by(HousekeepingTask.priority.asc(), HousekeepingTask.id.asc())
        .all()
    )


def _rule_dispatch_plan(db: Session, hotel_id: int, task_ids: list[int]) -> list[dict]:
    if not task_ids:
        return []
    return _plan_batch_dispatch(db, hotel_id, task_ids, mode="smart")


def _validate_new_tasks(raw_list: list, drafts: list[dict], staff_slim: list[dict]) -> list[dict]:
    """只接受 MCP 草稿里出现过的 room_id + task_type。"""
    allowed = {(int(d["room_id"]), d["task_type"]): d for d in drafts}
    by_staff = {s["id"]: s for s in staff_slim}
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for row in raw_list or []:
        if not isinstance(row, dict):
            continue
        try:
            rid = int(row.get("room_id"))
        except (TypeError, ValueError):
            continue
        try:
            tt = _hk_task_service._norm_task_type(str(row.get("task_type") or row.get("type") or "clean"))
        except HTTPException:
            continue
        key = (rid, tt)
        if key not in allowed or key in seen:
            continue
        base = dict(allowed[key])
        aid = row.get("assignee_id", base.get("assignee_id"))
        try:
            aid = int(aid) if aid is not None else None
        except (TypeError, ValueError):
            aid = base.get("assignee_id")
        st = by_staff.get(aid) if aid else None
        if st and st.get("status") == "rest":
            st = None
            aid = None
        pri = row.get("priority", base.get("priority") or 3)
        try:
            pri = max(1, min(5, int(pri)))
        except (TypeError, ValueError):
            pri = 3
        out.append(
            {
                **base,
                "assignee_id": aid,
                "assignee": (st or {}).get("name") or base.get("assignee"),
                "priority": pri,
                "reason": str(row.get("reason") or base.get("reason") or "AI 建议新建")[:40],
            }
        )
        seen.add(key)
        if len(out) >= 6:
            break
    return out
