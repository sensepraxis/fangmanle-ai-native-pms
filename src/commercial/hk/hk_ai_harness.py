# SPDX-License-Identifier: BUSL-1.1
"""房务 AI Harness：先列现状 → 再给可确认行动计划 → 人工确认后落库。

默认调用系统 LLM（当前 AppSetting.llm 选型，可插拔）；失败则 source=unavailable，不把规则候选冒充 AI。
分场景提示词；产品话术不暴露模型名。
"""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.llm_service import llm_identity, load_llm_config
from commercial.ai_core.locale_llm import (
    CJK_RE,
    compose_system,
    locale_optional,
    locale_str_list,
    locale_text,
    run_locale_llm_json,
    wants_en,
)
from commercial.ai_core.prompt_packs import get_scene_prompt
from commercial.hk.hk_ai_scene_registry import (
    build_hk_candidates,
    get_hk_scene,
    list_hk_scenes,
    register_hk_scene,
)
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.branding import brand_text
from infra.i18n import get_locale, t

SCENES = (
    "cleaning_plan",
    "dispatch_assign",
    "floor_rebalance",
    "staffing_gap",
)

# —— 分场景系统提示（产品向，强调先读现状再出计划）——
SCENE_SYSTEM: dict[str, str] = {
    "cleaning_plan": brand_text("""你是「{APP_NAME}」客房主管助理，专责「清扫安排」。
先根据「现状」判断哪些房必须立刻建清洁/翻台单，再从候选行动中挑选。
原则：
1. 只依据消息中的现状与候选 items，禁止编造 room_id。
2. 优先空脏、预离、高优房间；同房同类型不重复建。
3. 输出单一 JSON（无 Markdown 围栏）：
{"summary":"≤36字行动总述","situation_note":"≤40字补充现状解读（可空）","reasons":["依据1","依据2"],"selected_ids":["优先执行的 item id"]}
4. 用户可见文案须与请求语言一致，面向主管，不出现模型名、数据库、API 等词。"""),
    "dispatch_assign": brand_text("""你是「{APP_NAME}」派工主管助理，专责「智能派工」。
先看清待分配任务与在岗人力，再决定派给谁、是否需新建单。
原则：
1. 只依据现状与候选 items，禁止编造 task_id / assignee_id。
2. 优先楼层就近、负荷均衡；每人不宜一次压过多任务。
3. 输出单一 JSON（无 Markdown 围栏）：
{"summary":"≤36字行动总述","situation_note":"≤40字补充现状解读（可空）","reasons":["依据1","依据2"],"selected_ids":["优先执行的 item id"]}
4. 用户可见文案须与请求语言一致，面向主管。"""),
    "floor_rebalance": brand_text("""你是「{APP_NAME}」当班调度助理，专责「楼层调拨」。
先指出哪一层积压、哪一侧可支援，再挑改派行动。
原则：
1. 只依据现状与候选 items，禁止编造 task_id / assignee_id。
2. 优先把积压楼层任务改派给有余力的支援人员。
3. 输出单一 JSON（无 Markdown 围栏）：
{"summary":"≤36字行动总述","situation_note":"≤40字补充现状解读（可空）","reasons":["依据1","依据2"],"selected_ids":["优先执行的 item id"]}
4. 用户可见文案须与请求语言一致，面向当班主管。"""),
    "staffing_gap": brand_text("""你是「{APP_NAME}」排班助理，专责「补班安排」。
先对照未来几天预离量与在岗缺口，再挑选调班格。
原则：
1. 只依据现状与候选 items，禁止编造 user_id / date。
2. 只补缺口日；不改动已说明为手改锁定的班次。
3. 输出单一 JSON（无 Markdown 围栏）：
{"summary":"≤36字行动总述","situation_note":"≤40字补充现状解读（可空）","reasons":["依据1","依据2"],"selected_ids":["优先执行的 item id"]}
4. 用户可见文案须与请求语言一致，面向排班主管。"""),
}


def _item(
    *,
    op: str,
    label: str,
    reason: str,
    payload: dict,
    risk: str = "low",
) -> dict:
    return {
        "id": f"i-{uuid.uuid4().hex[:8]}",
        "op": op,
        "label": label,
        "reason": reason,
        "payload": payload,
        "risk": risk,
        "selected": True,
    }


def _situation(headline: str, bullets: list[str], metrics: Optional[list[dict]] = None) -> dict:
    return {
        "headline": headline,
        "bullets": [b for b in bullets if b][:8],
        "metrics": metrics or [],
    }


# ---------- 现状（分场景） ----------


def _situation_cleaning(db: Session, hotel_id: int) -> dict:
    from models import HousekeepingTask, Room
    from rooms.room_status import BLK, DO, EA, OCC, OOO, VC, VD, normalize

    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    dirty = sum(1 for r in rooms if normalize(r.status) == VD)
    clean = sum(1 for r in rooms if normalize(r.status) == VC)
    occ = sum(1 for r in rooms if normalize(r.status) in (OCC, EA, DO))
    ooo = sum(1 for r in rooms if normalize(r.status) in (OOO, BLK))
    open_n = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned", "in_progress", "rework")),
        )
        .count()
    )
    from hk.housekeeping_service import mcp_draft_housekeeping_tasks

    drafts = mcp_draft_housekeeping_tasks(db, hotel_id, limit=20)
    by_type: dict[str, int] = defaultdict(int)
    for d in drafts:
        by_type[t(str(d.get("task_type_label") or d.get("task_type") or "清扫"))] += 1
    sep = "、" if str(get_locale()).startswith("zh") else ", "
    type_txt = sep.join(f"{k}×{v}" for k, v in list(by_type.items())[:4]) or t("暂无")
    return _situation(
        t("当前空脏 {dirty} 间，尚有 {n} 间可建清洁单", dirty=dirty, n=len(drafts)),
        [
            t(
                "总房 {total} · 空脏 {dirty} · 空净 {clean} · 占用 {occ} · 维修锁房 {ooo}",
                total=len(rooms),
                dirty=dirty,
                clean=clean,
                occ=occ,
                ooo=ooo,
            ),
            t("已有进行中/待处理清洁单 {n} 张", n=open_n),
            t("建议新建类型分布：{dist}", dist=type_txt),
        ],
        [
            {"label": t("空脏"), "value": dirty},
            {"label": t("可建单"), "value": len(drafts)},
            {"label": t("在途单"), "value": open_n},
        ],
    )


def _situation_dispatch(db: Session, hotel_id: int) -> dict:
    from hk.housekeeping_service import _on_duty_staff, _waiting_dispatch_rows
    from models import HousekeepingTask, Room

    waiting = _waiting_dispatch_rows(db, hotel_id)
    staff = _on_duty_staff(db, hotel_id)
    active = [s for s in staff if s.get("status") != "rest"]
    idle = [s for s in active if s.get("status") == "idle"]
    busy = [s for s in active if s.get("status") == "busy"]
    floor_wait: dict[int, int] = defaultdict(int)
    for tsk, rm in waiting:
        fl = int(rm.floor) if rm and rm.floor else 0
        floor_wait[fl] += 1
    hot = ""
    if floor_wait:
        fl = max(floor_wait.keys(), key=lambda f: floor_wait[f])
        hot = t("{fl}F 待分配最多（{n} 间）", fl=fl, n=floor_wait[fl])
    progress = db.query(HousekeepingTask).filter_by(hotel_id=hotel_id, status="in_progress").count()
    return _situation(
        t(
            "待分配 {waiting} 单，在岗 {active} 人（空闲 {idle}）",
            waiting=len(waiting),
            active=len(active),
            idle=len(idle),
        ),
        [
            t("待分配 {waiting} · 进行中 {progress}", waiting=len(waiting), progress=progress),
            t(
                "在岗 {active} 人（空闲 {idle} / 忙碌 {busy}）",
                active=len(active),
                idle=len(idle),
                busy=len(busy),
            ),
            hot or t("各楼层待分配较均衡"),
        ],
        [
            {"label": t("待分配"), "value": len(waiting)},
            {"label": t("在岗"), "value": len(active)},
            {"label": t("空闲"), "value": len(idle)},
        ],
    )


def _situation_rebalance(db: Session, hotel_id: int) -> dict:
    from hk.housekeeping_service import _on_duty_staff
    from models import HousekeepingTask, Room

    staff = _on_duty_staff(db, hotel_id)
    active = [s for s in staff if s.get("status") != "rest"]
    rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned")),
        )
        .all()
    )
    floor_wait: dict[int, int] = defaultdict(int)
    for tsk, rm in rows:
        fl = int(rm.floor) if rm and rm.floor else 0
        floor_wait[fl] += 1
    ranked = sorted(floor_wait.items(), key=lambda x: -x[1])
    top = ranked[0] if ranked else None
    light = ranked[-1] if len(ranked) > 1 else None
    bullets = [
        t("待分配合计 {n} 间，在岗可调 {active} 人", n=len(rows), active=len(active)),
    ]
    if top:
        bullets.append(t("积压最重：{floor}F（{n} 间待分配）", floor=top[0], n=top[1]))
    if light and light[0] != (top or (None,))[0]:
        bullets.append(t("相对较松：{floor}F（{n} 间）", floor=light[0], n=light[1]))
    if len(ranked) >= 2:
        dist = " · ".join(f"{f}F {n}" for f, n in ranked[:5])
        bullets.append(t("楼层分布：{dist}", dist=dist))
    headline = (
        t("{floor}F 积压 {n} 间，建议跨层支援", floor=top[0], n=top[1])
        if top and top[1] >= 2
        else t("各楼层待分配压力不高")
    )
    return _situation(
        headline,
        bullets,
        [
            {"label": t("待分配"), "value": len(rows)},
            {"label": t("积压楼层"), "value": f"{top[0]}F" if top else "—"},
            {"label": t("在岗"), "value": len(active)},
        ],
    )


def _situation_staffing(db: Session, hotel_id: int) -> dict:
    from hk.staffing_service import build_ai_forecast

    fc = build_ai_forecast(db, hotel_id, days=5)
    days = fc.get("days") or []
    gap_days = [c for c in days if c.get("has_gap")]
    total_need = sum(int(c.get("need_clean") or 0) for c in days)
    bullets = [
        t("未来 {n} 天预离合计约 {rooms} 间次", n=len(days), rooms=total_need),
        t("存在人力缺口的日期：{n} 天", n=len(gap_days)),
    ]
    for c in gap_days[:3]:
        bullets.append(
            t(
                "{label}：预离 {n} 间 · {hint}",
                label=c.get("label") or c.get("date"),
                n=c.get("need_clean"),
                hint=c.get("suggest") or c.get("reason") or t("建议补班"),
            )
        )
    if not gap_days:
        bullets.append(t("未来几天与预离对比，暂无明显缺口"))
    return _situation(
        t("未来 5 天有 {n} 天存在补班缺口", n=len(gap_days)) if gap_days else t("未来 5 天人力基本够用"),
        bullets,
        [
            {"label": t("预离间次"), "value": total_need},
            {"label": t("缺口日"), "value": len(gap_days)},
            {"label": t("可调班格"), "value": sum(len(c.get("proposed") or []) for c in days)},
        ],
    )


def build_situation(db: Session, hotel_id: int, scene: str) -> dict:
    _ensure_hk_scenes_registered()
    meta = get_hk_scene(scene)
    sb = meta.get("situation_builder")
    if sb:
        return sb(db, hotel_id)
    return _situation(t("暂无现状"), [])


# ---------- 候选行动 ----------


def _candidates_cleaning(db: Session, hotel_id: int) -> tuple[list[dict], list[str]]:
    from hk.housekeeping_service import mcp_draft_housekeeping_tasks

    drafts = mcp_draft_housekeeping_tasks(db, hotel_id, limit=12)
    items = []
    for d in drafts[:12]:
        task_label = t(str(d.get("task_type_label") or "清扫"))
        reason = t(str(d.get("reason") or "房态需清洁"))
        items.append(
            _item(
                op="create_task",
                label=t(
                    "新建 {room} {task} → {assignee}",
                    room=d["room_no"],
                    task=task_label,
                    assignee=d.get("assignee") or t("待派"),
                ),
                reason=reason,
                payload={
                    "room_id": d["room_id"],
                    "room_no": d.get("room_no"),
                    "task_type": d.get("task_type") or "clean",
                    "assignee_id": d.get("assignee_id"),
                    "assignee_name": d.get("assignee"),
                    "priority": d.get("priority") or 3,
                    "reason": t("清扫安排：{reason}", reason=reason)[:180],
                },
            )
        )
    reasons = [
        t("对照空脏与未建单房间，起草 {n} 条清扫安排", n=len(items)),
        t("确认后创建清洁任务（同房同类型不重复建）"),
    ]
    return items, reasons


def _candidates_dispatch(db: Session, hotel_id: int) -> tuple[list[dict], list[str]]:
    from hk.housekeeping_service import ai_suggest_dispatch

    res = ai_suggest_dispatch(db, hotel_id, apply=False, notify=False)
    items = []
    for a in res.get("assignments") or []:
        items.append(
            _item(
                op="assign_start",
                label=t(
                    "派工 {room} → {assignee}",
                    room=a.get("room_no"),
                    assignee=a.get("assignee"),
                ),
                reason=_visible_text(a.get("reason") or "", fallback="楼层就近派工"),
                payload={
                    "task_id": a["task_id"],
                    "assignee_id": a["assignee_id"],
                    "assignee_name": a.get("assignee"),
                    "room_no": a.get("room_no"),
                },
            )
        )
    for p in (res.get("proposed_tasks") or [])[:8]:
        task_label = t(str(p.get("task_type_label") or "清扫"))
        reason = t(str(p.get("reason") or "建议建单"))
        items.append(
            _item(
                op="create_task",
                label=t(
                    "新建 {room} {task} → {assignee}",
                    room=p.get("room_no"),
                    task=task_label,
                    assignee=p.get("assignee") or t("待派"),
                ),
                reason=reason,
                payload={
                    "room_id": p["room_id"],
                    "room_no": p.get("room_no"),
                    "task_type": p.get("task_type") or "clean",
                    "assignee_id": p.get("assignee_id"),
                    "assignee_name": p.get("assignee"),
                    "priority": p.get("priority") or 3,
                    "reason": t("派工建单：{reason}", reason=reason)[:180],
                },
            )
        )
    reasons = [
        _visible_text(res.get("summary") or "", fallback=t("待派/待建共 {n} 项", n=len(items))),
        t("按楼层就近与在岗负荷匹配（确认后才会生效）"),
    ]
    return items, reasons


def _candidates_rebalance(db: Session, hotel_id: int) -> tuple[list[dict], list[str]]:
    from hk.housekeeping_service import _on_duty_staff
    from models import HousekeepingTask, Room

    staff = _on_duty_staff(db, hotel_id)
    active = [s for s in staff if s.get("status") != "rest"]
    rows = (
        db.query(HousekeepingTask, Room)
        .outerjoin(Room, HousekeepingTask.room_id == Room.id)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(("open", "assigned")),
        )
        .order_by(HousekeepingTask.priority.asc(), HousekeepingTask.id.asc())
        .all()
    )
    floor_wait: dict[int, list] = {}
    for tsk, rm in rows:
        fl = int(rm.floor) if rm and rm.floor else 0
        floor_wait.setdefault(fl, []).append((tsk, rm))
    if not floor_wait or not active:
        return [], [t("当前无待分配积压或无可调人员")]

    to_fl = max(floor_wait.keys(), key=lambda f: len(floor_wait[f]))
    if len(floor_wait[to_fl]) < 2:
        return [], [t("{floor}F 待分配较少，暂无需调拨", floor=to_fl)]

    donors = []
    for s in active:
        floors = s.get("floors") or []
        if to_fl in floors:
            continue
        donors.append(s)
    if not donors:
        donors = active[:]

    move_n = 1 if len(floor_wait[to_fl]) < 10 else 2
    donors = donors[:move_n]
    victims = floor_wait[to_fl][: max(2, move_n * 2)]
    items = []
    for i, (tsk, rm) in enumerate(victims):
        donor = donors[i % len(donors)]
        items.append(
            _item(
                op="reassign",
                label=t(
                    "调拨 {room}（{floor}F）→ {name}",
                    room=rm.room_no if rm else tsk.id,
                    floor=to_fl,
                    name=donor.get("name"),
                ),
                reason=t("从支援力量改派消化 {floor}F 积压", floor=to_fl),
                payload={
                    "task_id": tsk.id,
                    "assignee_id": donor["id"],
                    "assignee_name": donor.get("name"),
                    "room_no": rm.room_no if rm else None,
                    "from_floor": to_fl,
                },
                risk="medium",
            )
        )
    from_names = ("、" if str(get_locale()).startswith("zh") else ", ").join(
        d.get("name") or str(d["id"]) for d in donors
    )
    reasons = [
        t(
            "{floor}F 待分配 {n} 间，建议 {names} 支援",
            floor=to_fl,
            n=len(floor_wait[to_fl]),
            names=from_names,
        ),
        t("确认后更新任务指派人"),
    ]
    return items, reasons


def _candidates_staffing(db: Session, hotel_id: int) -> tuple[list[dict], list[str]]:
    from hk.staffing_service import build_ai_forecast, shift_label

    fc = build_ai_forecast(db, hotel_id, days=5)
    items = []
    for card in fc.get("days") or []:
        for p in card.get("proposed") or []:
            from_cn = shift_label(p.get("from_shift")) if p.get("from_shift") else t("空")
            to_cn = shift_label(p.get("to_shift") or "morning")
            items.append(
                _item(
                    op="upsert_shift",
                    label=t(
                        "{date} {name}：{from}→{to}",
                        date=p.get("date"),
                        name=p.get("name"),
                        **{"from": from_cn, "to": to_cn},
                    ),
                    reason=p.get("reason") or card.get("label") or t("预离缺口补班"),
                    payload={
                        "user_id": p.get("user_id"),
                        "date": p.get("date"),
                        "to_shift": p.get("to_shift") or "morning",
                        "from_shift": p.get("from_shift"),
                        "name": p.get("name"),
                    },
                    risk="medium",
                )
            )
    reasons = [
        t(fc.get("subtitle") or "未来预离与排班对比"),
        t("可调整 {n} 个班次（不会覆盖你已手改的班）", n=len(items)),
    ]
    if not items:
        reasons = [t("未来 5 天暂无明显人力缺口，或缺口格均已手改锁定")]
    return items[:16], reasons


def _visible_text(s: str, *, fallback: str = "") -> str:
    """展示文案跟 Locale；EN 下残留中文则套模板或回退。"""
    raw = str(s or "").strip()
    if not raw:
        return t(fallback) if fallback else ""
    out = t(raw)
    if not wants_en() or not CJK_RE.search(out):
        return out
    m = re.search(r"分配\s*(\d+)\s*单.*?新建\s*(\d+)\s*单", out)
    if m:
        return t(
            "分配 {assign} 单，新建 {create} 单，优先同层就近负荷任务。",
            assign=m.group(1),
            create=m.group(2),
        )
    m2 = re.search(r"按楼层就近将\s*(\d+)\s*个", out)
    if m2:
        return t("按楼层就近将 {n} 个待分配任务派给在岗保洁", n=m2.group(1))
    return t(fallback) if fallback else out


def _build_candidates(db: Session, hotel_id: int, scene: str) -> tuple[list[dict], list[str], str]:
    _ensure_hk_scenes_registered()
    return build_hk_candidates(db, hotel_id, scene)


def _refine_with_llm(
    db: Session,
    *,
    scene: str,
    title: str,
    situation: dict,
    items: list[dict],
    reasons: list[str],
) -> tuple[list[dict], list[str], str, Optional[str], str, Optional[str], Optional[str]]:
    """返回 items, reasons, summary, situation_note, source, model, llm_error"""
    if not items:
        return items, reasons, t("暂无可执行安排"), None, "rules", None, None

    slim = [
        {
            "id": it["id"],
            "op": it["op"],
            "label": it["label"],
            "reason": it["reason"],
        }
        for it in items
    ]
    system = compose_system(get_scene_prompt("hk", scene) or SCENE_SYSTEM.get(scene) or SCENE_SYSTEM["dispatch_assign"])
    if wants_en():
        user = (
            f"[Scene] {title}\n\n"
            f"[Current state]\n"
            f"Headline: {situation.get('headline') or ''}\n"
            f"Bullets: {json.dumps(situation.get('bullets') or [], ensure_ascii=False)}\n"
            f"Metrics: {json.dumps(situation.get('metrics') or [], ensure_ascii=False)}\n\n"
            f"[Candidate actions]\n{json.dumps(slim, ensure_ascii=False)}\n\n"
            f"[Rule reasons]\n{json.dumps(reasons, ensure_ascii=False)}\n\n"
            "Understand the situation, pick the best actions, output summary / situation_note / reasons / selected_ids. "
            "All user-visible strings MUST be English (no Chinese except person names)."
        )
    else:
        user = (
            f"【场景】{title}\n\n"
            f"【现状】\n"
            f"总述：{situation.get('headline') or ''}\n"
            f"要点：{json.dumps(situation.get('bullets') or [], ensure_ascii=False)}\n"
            f"指标：{json.dumps(situation.get('metrics') or [], ensure_ascii=False)}\n\n"
            f"【候选行动】\n{json.dumps(slim, ensure_ascii=False)}\n\n"
            f"【规则初判依据】\n{json.dumps(reasons, ensure_ascii=False)}\n\n"
            "请先理解现状，再挑选最该执行的行动，输出 summary / situation_note / reasons / selected_ids。"
        )
    call = run_locale_llm_json(db, system=system, user=user)
    if call.error and not call.parsed:
        return [], reasons, "", None, "unavailable", None, call.error
    parsed = call.parsed
    ids = parsed.get("selected_ids") if isinstance(parsed.get("selected_ids"), list) else []
    id_set = {str(x) for x in ids}
    by_id = {it["id"]: it for it in items}
    if id_set:
        ordered = [by_id[i] for i in ids if i in by_id]
        rest = [it for it in items if it["id"] not in id_set]
        for it in ordered:
            it["selected"] = True
        for it in rest:
            it["selected"] = False
        items = ordered + rest
    n_sel = sum(1 for i in items if i["selected"])
    raw_sum = str(parsed.get("summary") or "").strip()
    summary = locale_text(raw_sum, "建议执行 {n} 项安排", 80) if raw_sum else t("建议执行 {n} 项安排", n=n_sel)
    if "{n}" in summary:
        summary = t("建议执行 {n} 项安排", n=n_sel)
    note = locale_optional(parsed.get("situation_note"), 80)
    llm_reasons = locale_str_list(parsed.get("reasons"))
    if llm_reasons:
        reasons = llm_reasons
    source = "llm" if parsed else "unavailable"
    if source != "llm":
        return [], reasons, "", None, "unavailable", None, call.error
    return items, reasons, summary, note, source, call.model or None, call.error


def generate_plan(db: Session, hotel_id: int, scene: str) -> dict:
    _ensure_hk_scenes_registered()
    scene = (scene or "").strip()
    get_hk_scene(scene)  # 校验

    situation = build_situation(db, hotel_id, scene)
    items, reasons, title = _build_candidates(db, hotel_id, scene)
    items, reasons, summary, sit_note, source, model, llm_error = _refine_with_llm(
        db,
        scene=scene,
        title=title,
        situation=situation,
        items=items,
        reasons=reasons,
    )
    if sit_note:
        sit_note = _visible_text(sit_note)
        bullets = list(situation.get("bullets") or [])
        if sit_note not in bullets:
            bullets.append(sit_note)
        situation = {**situation, "bullets": bullets[:8]}

    summary = _visible_text(summary)
    reasons = [_visible_text(r) for r in (reasons or []) if r]
    for it in items:
        it["label"] = _visible_text(it.get("label") or "")
        it["reason"] = _visible_text(it.get("reason") or "", fallback="楼层就近派工")

    plan_id = f"hk-{scene}-{uuid.uuid4().hex[:10]}"
    cfg = load_llm_config(db)
    identity = llm_identity(cfg, {"model": model} if model else None) if source == "llm" else {}
    return {
        "plan_id": plan_id,
        "hotel_id": hotel_id,
        "scene": scene,
        "title": t(title),
        "situation": situation,
        "summary": summary,
        "reasons": reasons,
        "items": items,
        "source": source,
        "llm_error": llm_error,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "draft",
        "hint": t("先核对现状，再勾选行动，点「AI确认执行」即可生效"),
        **identity,
    }


def _exec_item(db: Session, hotel_id: int, item: dict, *, operator_id: Optional[int]) -> dict:
    from hk.housekeeping_service import (
        assign_task,
        create_housekeeping_task,
        start_task,
        urge_task,
    )
    from hk.staffing_service import upsert_shift

    op = item.get("op")
    payload = item.get("payload") or {}
    try:
        if op == "create_task":
            t, created = create_housekeeping_task(
                db,
                hotel_id,
                room_id=int(payload["room_id"]),
                task_type=str(payload.get("task_type") or "clean"),
                assignee_id=payload.get("assignee_id"),
                assignee_name=payload.get("assignee_name"),
                priority=payload.get("priority") or 3,
                reason=str(payload.get("reason") or "AI安排"),
            )
            return {
                "ok": True,
                "op": op,
                "task_id": t.id,
                "created": created,
                "label": item.get("label"),
            }
        if op == "assign_start":
            tid = int(payload["task_id"])
            start_task(
                db,
                tid,
                operator_id=operator_id,
                assignee_id=payload.get("assignee_id"),
                assignee_name=payload.get("assignee_name"),
            )
            return {"ok": True, "op": op, "task_id": tid, "label": item.get("label")}
        if op == "reassign":
            tid = int(payload["task_id"])
            assign_task(
                db,
                tid,
                assignee_id=payload.get("assignee_id"),
                assignee_name=payload.get("assignee_name"),
            )
            return {"ok": True, "op": op, "task_id": tid, "label": item.get("label")}
        if op == "urge":
            tid = int(payload["task_id"])
            urge_task(db, tid)
            return {"ok": True, "op": op, "task_id": tid, "label": item.get("label")}
        if op == "upsert_shift":
            uid = int(payload["user_id"])
            d = date.fromisoformat(str(payload["date"])[:10])
            to_shift = str(payload.get("to_shift") or "morning")
            _row, written = upsert_shift(
                db,
                hotel_id,
                user_id=uid,
                shift_date=d,
                shift=to_shift,
                note="[AI安排] 确认执行",
                source="ai",
                protect_manual=True,
            )
            return {
                "ok": True,
                "op": op,
                "written": written,
                "user_id": uid,
                "date": d.isoformat(),
                "label": item.get("label"),
                "skipped_manual": not written,
            }
        return {"ok": False, "error": f"未知 op：{op}", "label": item.get("label")}
    except Exception as e:
        return {
            "ok": False,
            "op": op,
            "error": str(getattr(e, "detail", None) or e)[:200],
            "label": item.get("label"),
        }


def confirm_plan(
    db: Session,
    hotel_id: int,
    *,
    plan: dict,
    operator_id: Optional[int] = None,
) -> dict:
    if not isinstance(plan, dict):
        raise InvalidStateError("缺少 plan")
    items = plan.get("items") if isinstance(plan.get("items"), list) else []
    selected = [it for it in items if isinstance(it, dict) and it.get("selected", True)]
    if not selected:
        raise InvalidStateError("请至少勾选一项再确认")

    results = []
    for it in selected[:20]:
        results.append(_exec_item(db, hotel_id, it, operator_id=operator_id))

    ok_n = sum(1 for r in results if r.get("ok"))
    fail_n = len(results) - ok_n
    return {
        "plan_id": plan.get("plan_id"),
        "scene": plan.get("scene"),
        "status": "confirmed" if fail_n == 0 else "partial",
        "applied": ok_n,
        "failed": fail_n,
        "results": results,
        "message": t("已生效 {n} 项", n=ok_n) + (t("，未成功 {n} 项", n=fail_n) if fail_n else ""),
        "written_at": datetime.now().isoformat(timespec="seconds"),
    }


def _ensure_hk_scenes_registered() -> None:
    if list_hk_scenes():
        return
    specs = (
        ("cleaning_plan", "AI清扫安排", _candidates_cleaning, _situation_cleaning),
        ("dispatch_assign", "AI派工安排", _candidates_dispatch, _situation_dispatch),
        ("floor_rebalance", "AI楼层调拨", _candidates_rebalance, _situation_rebalance),
        ("staffing_gap", "AI补班安排", _candidates_staffing, _situation_staffing),
    )
    for key, title, builder, sit in specs:
        register_hk_scene(
            key,
            title=title,
            builder=builder,
            situation_builder=sit,
            system_prompt=None,  # 运行时 get_scene_prompt，跟随 X-Locale
        )


_ensure_hk_scenes_registered()
