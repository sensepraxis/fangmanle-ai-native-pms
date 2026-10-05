# SPDX-License-Identifier: BUSL-1.1
# hk.housekeeping_service.ai_service — auto-split by AST

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
from infra.i18n import get_locale
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

# 跨子模块 helper：直接 import 子模块文件，避免经 package __init__ 拉回 commercial AI
import hk.housekeeping_service.board_service as _hk_board_service
import hk.housekeeping_service.dispatch_service as _hk_dispatch_service
import hk.housekeeping_service.task_service as _hk_task_service

HK_AI_DISPATCH_SYSTEM_EN = (
    "You are the housekeeping dispatch assistant for a small hotel (usually 1–2 floors, ~12 rooms each). "
    "Do not estimate staffing as if it were a 100-room property.\n\n"
    "Goal: from current state, MCP tool results and staff load, output an immediately executable dispatch plan "
    "and filter draft cleaning tasks.\n\n"
    "Hard rules:\n"
    "1. Use only task_id / staff id / room_id that appear in the input. Never invent people, rooms or floors.\n"
    "2. Do not assign staff with status=rest.\n"
    "3. Prefer same-floor nearby → idle/low load → VIP/high priority (lower priority number is more urgent).\n"
    "4. At most 4 tasks per person; at most 8 assignments this round.\n"
    "5. Gap = max(0, unassigned − assignable staff); for a two-floor house gap is usually 0–2.\n"
    "6. new_tasks must be picked from MCP `draft_housekeeping_tasks`, max 6; do not recreate rooms that already have open tasks.\n"
    "7. Output one JSON object only — no markdown, no extra prose.\n\n"
    "JSON schema:\n"
    '{"summary":"≤80 chars, English","mode":"smart","focus_floor":1,"gap":0,'
    '"assignments":[{"task_id":12,"assignee_id":5,"reason":"Same floor and idle"}],'
    '"new_tasks":[{"room_id":3,"task_type":"clean","priority":2,"assignee_id":null,"reason":"Vacant-dirty with no open task"}]}\n'
    "All user-visible strings (summary, reason) MUST be English. No Chinese except person names."
)


def _dispatch_system_prompt() -> str:
    if str(get_locale() or "").lower().startswith("en"):
        return HK_AI_DISPATCH_SYSTEM_EN
    return HK_AI_DISPATCH_SYSTEM


def ai_suggest_dispatch(
    db: Session,
    hotel_id: int,
    *,
    apply: bool = True,
    operator_id: Optional[int] = None,
    notify: bool = True,
    snapshot: Optional[dict] = None,
) -> dict:
    """调用 MCP 工具 + LLM：派工建议立即应用；待建保洁单只返回草稿，需一键采纳。"""
    mcp = _hk_board_service.run_hk_mcp_tools(db, hotel_id)
    staff_slim = mcp["staff"]
    drafts = mcp["drafts"]
    rows = _hk_dispatch_service._waiting_dispatch_rows(db, hotel_id)
    assignable_ids = {s["id"] for s in staff_slim if s.get("status") != "rest"}
    task_slim = []
    for t, rm in rows:
        fl = int(rm.floor) if rm and rm.floor else None
        task_slim.append(
            {
                "task_id": t.id,
                "room_no": rm.room_no if rm else "—",
                "floor": fl,
                "priority": t.priority or 5,
                "type": t.task_type or "clean",
            }
        )
    by_task = {t.id: (t, rm) for t, rm in rows}
    by_staff = {s["id"]: s for s in staff_slim}
    snap_text = (snapshot or {}).get("text") or _t(
        "待分配 {n} 单，在岗 {m} 人。", n=len(task_slim), m=len(assignable_ids)
    )
    tool_blob = [
        {
            "name": t["name"],
            "count": t["count"],
            "result": t["result"][:24] if isinstance(t.get("result"), list) else t.get("result"),
        }
        for t in mcp["tools"]
    ]
    wants_en = str(get_locale() or "").lower().startswith("en")
    if wants_en:
        user = (
            f"Current state: {snap_text}\n\nMCP tool results JSON:\n{json.dumps(tool_blob, ensure_ascii=False)}\n\n"
            f"Assignable staff JSON:\n{json.dumps(staff_slim, ensure_ascii=False)}\n\n"
            f"Unassigned tasks JSON:\n{json.dumps(task_slim[:24], ensure_ascii=False)}\n\n"
            f"draft_housekeeping_tasks JSON (new_tasks must be chosen from here):\n{json.dumps(drafts, ensure_ascii=False)}\n\n"
            "Respond in English. assignment.reason and summary must be English."
        )
    else:
        user = f"系统现状：{snap_text}\n\n已调用 MCP 工具结果 JSON：\n{json.dumps(tool_blob, ensure_ascii=False)}\n\n可派人员 JSON：\n{json.dumps(staff_slim, ensure_ascii=False)}\n\n待分配任务 JSON：\n{json.dumps(task_slim[:24], ensure_ascii=False)}\n\ndraft_housekeeping_tasks 草稿 JSON（new_tasks 只能从这里选）：\n{json.dumps(drafts, ensure_ascii=False)}"
    source = "unavailable"
    llm_error = None
    parsed: dict = {}
    plan: list[dict] = []
    proposed: list[dict] = []
    identity: dict = {}
    try:
        from commercial.ai_core.llm_service import chat as llm_chat
        from commercial.ai_core.llm_service import llm_identity, load_llm_config

        cfg = load_llm_config(db)
        if not cfg.get("enabled", True):
            raise RuntimeError("LLM 已禁用")
        resp = llm_chat(db, [{"role": "user", "content": user}], _dispatch_system_prompt())
        content = resp.get("content") if isinstance(resp, dict) else str(resp)
        parsed = _hk_board_service._parse_json_blob(content or "") or {}
        identity = llm_identity(cfg, resp if isinstance(resp, dict) else None)
        raw_asg = parsed.get("assignments") if isinstance(parsed.get("assignments"), list) else []
        per_person: dict[int, int] = {}
        seen_tasks: set[int] = set()
        for row in raw_asg:
            try:
                tid = int(row.get("task_id"))
                aid = int(row.get("assignee_id"))
            except (TypeError, ValueError):
                continue
            if tid in seen_tasks or tid not in by_task:
                continue
            if aid not in assignable_ids:
                continue
            if per_person.get(aid, 0) >= 4:
                continue
            if len(plan) >= 8:
                break
            t, rm = by_task[tid]
            st = by_staff[aid]
            plan.append(
                {
                    "task_id": tid,
                    "room_no": rm.room_no if rm else "—",
                    "assignee_id": aid,
                    "assignee": st["name"],
                    "floor": int(rm.floor) if rm and rm.floor else None,
                    "reason": _t(str(row.get("reason") or "AI 派工"))[:80],
                }
            )
            seen_tasks.add(tid)
            per_person[aid] = per_person.get(aid, 0) + 1
        raw_new = parsed.get("new_tasks") if isinstance(parsed.get("new_tasks"), list) else []
        proposed = _hk_dispatch_service._validate_new_tasks(raw_new, drafts, staff_slim)
        if plan or proposed:
            source = "llm"
        else:
            llm_error = "模型未返回可用的派工或新建任务"
    except Exception as e:
        llm_error = str(getattr(e, "detail", None) or e)[:200]
    if source != "llm":
        plan = []
        proposed = []
        source = "unavailable"
        identity = {}
    idle_n = len([s for s in staff_slim if s["status"] == "idle"])
    busy_n = len([s for s in staff_slim if s["status"] == "busy"])
    gap = max(0, len(task_slim) - max(1, idle_n + busy_n)) if idle_n + busy_n else len(task_slim)
    if gap > 2:
        gap = min(2, max(0, len(task_slim) - 8))
    if isinstance(parsed.get("gap"), int) and 0 <= parsed["gap"] <= 3:
        gap = parsed["gap"]
    names = []
    for item in plan:
        n = item.get("assignee")
        if n and n not in names:
            names.append(n)
    summary = str(parsed.get("summary") or "").strip()
    if source == "llm":
        summary = _t(summary) if summary else _t("已生成派工建议")
    else:
        summary = _t("未能调用大模型，未生成 AI 派工（规则数据不会冒充 AI）。")
    applied = []
    if apply and plan:
        for item in plan:
            t = _hk_task_service.start_task(
                db, item["task_id"], operator_id=operator_id, assignee_id=item["assignee_id"]
            )
            applied.append({**item, "status": t.status})
        if notify:
            from collections import defaultdict

            by_user: dict[int, list[str]] = defaultdict(list)
            for item in applied:
                by_user[item["assignee_id"]].append(item["room_no"])
            for uid, rms in by_user.items():
                _hk_dispatch_service.notify_hk_dispatch_wecom(db, hotel_id, assignee_id=uid, rooms=rms)
    mcp_meta = [{"name": t["name"], "ok": t["ok"], "count": t["count"]} for t in mcp["tools"]]
    return {
        "source": source,
        "summary": summary,
        "gap": gap,
        "focus_floor": parsed.get("focus_floor"),
        "mode": parsed.get("mode") or "smart",
        "assignments": applied or plan,
        "count": len(applied or plan),
        "applied": bool(applied),
        "proposed_tasks": proposed,
        "proposed_count": len(proposed),
        "mcp_tools": mcp_meta,
        "llm_error": llm_error,
        "snapshot": snap_text,
        **identity,
    }


def _ai_assistant_intent(content: str) -> dict:
    text = content or ""
    if any(k in text for k in ("空调", "制热", "制冷", "漏水", "门锁", "电视", "灯")):
        return {"label": "客房维修", "detail": text[:18] or "设备故障", "conf": 98, "kind": "repair"}
    if any(k in text for k in ("茶", "餐", "菜单", "送餐", "下午茶", "点餐")):
        return {"label": "客房送餐", "detail": "点餐/送物", "conf": 94, "kind": "fnb"}
    if any(k in text for k in ("毛巾", "被子", "枕", "水", "牙具", "拖鞋")):
        return {"label": "客用品补给", "detail": text[:18] or "客用品", "conf": 96, "kind": "amenity"}
    if any(k in text for k in ("打扫", "清洁", "卫生间")):
        return {"label": "住中整理", "detail": "客房清洁", "conf": 95, "kind": "clean"}
    if any(k in text for k in ("早餐", "wifi", "Wi-Fi", "WiFi", "退房")):
        return {"label": "入住咨询", "detail": text[:18] or "FAQ", "conf": 97, "kind": "faq"}
    return {"label": "客需服务", "detail": text[:18] or "服务请求", "conf": 90, "kind": "general"}


def _ai_assistant_messages(room_no: str, guest_short: str, content: str, created_at, open_: bool) -> list:
    """按工单原文生成会话骨架：客人原文 → 意图 → AI 回复 →（可选）工单卡。不扩写假对话。"""
    intent = _ai_assistant_intent(content)
    t0 = created_at.strftime("%H:%M") if created_at else "—"
    try:
        t1_dt = created_at + timedelta(minutes=1) if created_at else None
        t1 = t1_dt.strftime("%H:%M") if t1_dt else "—"
    except Exception:
        t1 = "—"
    guest_text = (content or "").strip() or "（无正文）"
    msgs = [
        {"role": "guest", "text": guest_text, "time": t0},
        {"type": "intent", "text": f"规则分拣: {intent['label']} ({intent['detail']})"},
    ]
    if intent["kind"] == "repair":
        msgs.append(
            {
                "role": "desk",
                "text": f"{guest_short}您好，已登记报修「{guest_text}」，将安排工程前往 {room_no}。",
                "time": t1,
            }
        )
        msgs.append(
            {
                "type": "system",
                "title": "已自动生成报修工单",
                "ticket": f"工单 #REP-{room_no}-{(t1 or '0000').replace(':', '')}",
                "item": f"项目: {guest_text}",
                "status": "处理中" if open_ else "已完成",
            }
        )
    elif intent["kind"] == "fnb":
        msgs.append({"role": "desk", "text": f"已为{guest_short}登记餐饮相关请求「{guest_text}」。", "time": t1})
    elif intent["kind"] == "amenity":
        msgs.append(
            {"role": "desk", "text": f"好的{guest_short}，已登记「{guest_text}」，将安排送到 {room_no}。", "time": t1}
        )
        msgs.append(
            {
                "type": "system",
                "title": "已自动生成客需工单",
                "ticket": f"工单 #SRV-{room_no}-{(t1 or '0000').replace(':', '')}",
                "item": f"项目: {guest_text}",
                "status": "处理中" if open_ else "已完成",
            }
        )
    elif intent["kind"] == "faq":
        msgs.append(
            {
                "role": "desk",
                "text": f"{guest_short}您好，已记录咨询「{guest_text}」，请以门店答疑库为准答复。",
                "time": t1,
            }
        )
    else:
        msgs.append({"role": "desk", "text": f"收到{guest_short}，已记录「{guest_text}」，将安排处理。", "time": t1})
    return msgs


def _ai_assistant_actions(content: str) -> list:
    intent = _ai_assistant_intent(content)
    if intent["kind"] == "repair":
        return [{"label": "创建报修工单"}, {"label": "转工程部"}]
    if intent["kind"] == "fnb":
        return [{"label": "处理点餐订单"}, {"label": "发送电子菜单"}]
    if intent["kind"] == "amenity":
        return [{"label": "派送客用品"}, {"label": "同步客需工单"}]
    if intent["kind"] == "faq":
        return [{"label": "发送答疑话术"}, {"label": "转人工客服"}]
    return [{"label": "创建服务工单"}, {"label": "转人工接管"}]


def build_housekeeping_ai_assistant(db: Session, hotel_id: int):
    """AI 服务助理会话工作台：会话列表 / 对话 / 客史 / 操作 / 答疑库（绑库）。"""
    channels = {c.id: c for c in db.query(Channel).all()}
    guests = {g.id: g for g in db.query(Guest).all()}
    tags_by_guest: dict = {}
    for gt, td in db.query(GuestTag, TagDefinition).join(TagDefinition, GuestTag.tag_id == TagDefinition.id).all():
        tags_by_guest.setdefault(gt.guest_id, []).append(td.name)
    room_stay: dict = {}
    stay_rows = (
        db.query(Reservation, Order, Room)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Room, Reservation.room_id == Room.id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .all()
    )
    for res, od, rm in stay_rows:
        if rm:
            room_stay[rm.id] = (od, guests.get(od.guest_id), channels.get(od.channel_id))
    fallback_orders = db.query(Order).filter(Order.hotel_id == hotel_id).order_by(Order.id.desc()).limit(20).all()
    sr_rows = (
        db.query(ServiceRequest, Room)
        .outerjoin(Room, ServiceRequest.room_id == Room.id)
        .filter(ServiceRequest.hotel_id == hotel_id)
        .order_by(ServiceRequest.priority.asc(), ServiceRequest.id.asc())
        .limit(16)
        .all()
    )
    channel_cycle = ["美团订单", "携程订单", "微信客服", "前台转接", "官网"]
    conversations = []
    for i, (sr, rm) in enumerate(sr_rows):
        room_no = (rm.room_no if rm else None) or "—"
        open_ = (sr.status or "") not in ("done", "closed", "resolved")
        od = guests_g = ch = None
        if rm and rm.id in room_stay:
            od, guests_g, ch = room_stay[rm.id]
        if not guests_g and sr.guest_id:
            guests_g = guests.get(sr.guest_id)
        if not od and sr.order_id:
            od = db.get(Order, sr.order_id)
            if od:
                guests_g = guests_g or guests.get(od.guest_id)
                ch = ch or channels.get(od.channel_id)
        if not od and fallback_orders:
            od = fallback_orders[i % len(fallback_orders)]
            guests_g = guests_g or guests.get(od.guest_id)
            ch = ch or channels.get(od.channel_id)
        gname = (guests_g.name if guests_g else None) or "宾客"
        surname = gname[0] if gname else "宾"
        title = "先生" if guests_g and (guests_g.gender or "") in ("男", "M", "m") or i % 2 == 0 else "女士"
        display = f"{surname}{title}"
        short = display
        ch_name = (ch.name if ch else None) or "未绑定渠道"
        vip = bool(guests_g and (guests_g.vip_level or "") not in ("", "normal", "普通"))
        tag_names = tags_by_guest.get(guests_g.id, []) if guests_g else []
        mask = gname[0] + "*" + (gname[-1] if len(gname) > 1 else "")
        checkin = od.check_in.strftime("%m-%d") + " 14:00" if od and od.check_in else "—"
        checkout = od.check_out.strftime("%m-%d") + " 12:00" if od and od.check_out else "—"
        content = (sr.content or "").strip() or "（无正文）"
        intent = _ai_assistant_intent(content)
        conf = intent["conf"]
        if intent["kind"] == "repair":
            suggestion = f"已识别为报修，建议为 {room_no} 创建工程工单。"
        elif intent["kind"] == "fnb":
            suggestion = f"已识别为餐饮相关，建议按门店流程处理「{content}」。"
        elif intent["kind"] == "faq":
            suggestion = "已识别为咨询，请对照答疑库回复（勿使用写死话术冒充门店政策）。"
        else:
            suggestion = f"建议按客需「{content}」派工处理。"
        created = sr.created_at
        time_label = "刚刚"
        if created:
            mins = int((datetime.now() - created).total_seconds() // 60)
            if mins < 2:
                time_label = "刚刚"
            elif mins < 60:
                time_label = f"{mins}分钟前"
            else:
                time_label = created.strftime("%H:%M")
        conversations.append(
            {
                "id": sr.id,
                "name": f"{room_no} - {display}",
                "room": room_no,
                "guest": display,
                "guest_short": short,
                "guest_initial": surname,
                "preview": content,
                "channel": ch_name,
                "channel_short": (ch.name if ch else ch_name).replace("订单", ""),
                "time": time_label,
                "status": "AI 接管中" if open_ else "已解决",
                "open": open_,
                "vip": vip,
                "confidence": conf,
                "suggestion": suggestion,
                "stay_label": f"{(ch.name if ch else '渠道')} · 入住中"
                if open_ or (od and od.status == "checked_in")
                else f"{(ch.name if ch else '渠道')} · 已离店",
                "messages": _ai_assistant_messages(room_no, short, content, created, open_),
                "context": {
                    "channel": ch.name if ch else "—",
                    "guest": mask,
                    "checkin": checkin,
                    "checkout": checkout,
                    "tags": ", ".join(tag_names) if tag_names else "—",
                },
                "actions": _ai_assistant_actions(content),
            }
        )
    kb = [
        {"q": "Wi-Fi 密码", "a": "（请在门店配置中维护）"},
        {"q": "早餐时间与地点", "a": "（请在门店配置中维护）"},
        {"q": "退房时间", "a": "（请在门店配置中维护）"},
    ]
    active = next((c for c in conversations if c.get("open")), conversations[0] if conversations else None)
    return {
        "conversations": conversations,
        "active_id": active["id"] if active else None,
        "kb": kb,
        "empty": not conversations,
    }
