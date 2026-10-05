# SPDX-License-Identifier: BUSL-1.1
"""交班 / 接班 AI Harness：草稿 → 人工确认 → 写非资金可追溯字段。

禁止 AI 写：营收/备用金/押金数、实物实盘、签字、财务参数。
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from commercial.ai_core.ai_harness_base import parse_json_blob, strip_think
from commercial.ai_core.llm_service import llm_identity, load_llm_config
from commercial.ai_core.locale_llm import (
    compose_system,
    locale_optional,
    locale_str_list,
    locale_text,
    run_locale_llm_json,
)
from commercial.ai_core.prompt_packs import get_scene_prompt
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from finance.shift_handover_service import (
    _build_tasks,
    _guest_situations,
    _log,
    build_workspace,
    get_or_create_handover,
)
from finance.shift_scene_registry import (
    build_shift_candidates,
    get_shift_scene,
    list_shift_scenes,
    register_shift_scene,
)
from finance.shift_takeover_service import build_takeover_workspace
from infra.branding import brand_text
from infra.i18n import t
from models import ShiftAssetCount, ShiftHandover, ShiftHandoverTask, ShiftReceiveDiff

VALID_SOURCES = frozenset({"oneid_history", "restaurant_sys", "feedback_sys", "system_events", "inventory_sys"})
SCENES = ("handover", "takeover")

SYSTEM_HANDOVER = brand_text("""你是「{APP_NAME}」酒店前台交班助手。
任务：根据本班「候选清单」做优先级筛选，并写一句交班人口语化摘要。

硬性红线（违反则无效）：
1) 只能从候选 items 里选 id，禁止编造新客情/新待办/新偏好。
2) 禁止建议改动：营收金额、备用金盘库、押金实数、实物实盘、签字、财务参数。
3) 每条被选中项必须能对应候选里的真实 source。

筛选原则（按优先级）：
- 必选：客诉/P0、VIP 在店偏好、低库存补货、交班叙事。
- 宜选：即将到店（有特殊备注）、延迟退房、应收跟进。
- 可跳过：无实质内容的普通到店、重复表述。

文案要求：
- summary ≤36 字，像班组长口头交代，接地气（例：「本班 2 条 VIP 客情 + 1 条补货，备用金已对平」）。
- narrative 80–160 字：先钱（营收一句）→ 再客情要点 → 再待办/遗留；不要会计行话。
- reasons 写 2–3 条「为什么选这些」的依据，引用候选事实。

只输出一个 JSON（不要 Markdown、不要解释）：
{
  "summary": "≤36字",
  "narrative": "80-160字交班叙事",
  "reasons": ["依据1","依据2"],
  "selected_ids": ["候选id…"]
}""")

SYSTEM_TAKEOVER = brand_text("""你是「{APP_NAME}」酒店前台接班助手。
任务：根据「接班候选清单」生成接班人可确认的草稿——接班要点、客情关注、待办承接顺序、重盘比对结论、差异拟稿。

硬性红线：
1) 只能从候选 items 里选 id，禁止编造新客情/新待办/新差异数字。
2) 禁止建议自动改：营收、备用金实数、押金实数、实物实盘、签字、财务参数。
3) 差异项 suggestion 只能是「追补」或「交回」。
4) 客情/待办只能复述候选已有事实，禁止虚构偏好。

筛选原则：
- 必选：接班要点 brief、未勾选的 VIP/客诉客情、P0 待办、真实重盘差异。
- 宜选：备用金/实物比对结论（advice）、即将到店、遗留事项。
- 对平无差异时仍要写 brief + 比对结论，selected_ids 不能为空。

文案：
- summary ≤36 字，像接班组长口头交代。
- brief 80–160 字：先核对钱物状态 → 再客情重点 → 再待办承接顺序；接地气，不要会计行话。
- reasons 2–3 条依据，引用候选事实。

只输出一个 JSON（不要 Markdown）：
{
  "summary": "≤36字",
  "brief": "80-160字接班要点",
  "reasons": ["依据1","依据2"],
  "selected_ids": ["候选id…"],
  "guest_patches": [{"id":"候选id","note":"≤40字注意","action":"≤24字接班动作"}],
  "claim_patches": [{"id":"候选id","action":"≤24字承接建议"}],
  "diff_patches": [{"id":"候选id","reason":"≤40字","suggestion":"追补|交回"}],
  "advice_patches": [{"id":"候选id","note":"≤60字比对结论"}]
}""")


def _strip_think(text: str) -> str:
    return strip_think(text)


def _parse_json_blob(text: str) -> dict | None:
    return parse_json_blob(text)


def _jload(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _jsave(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def _guest_action(stype: str) -> str:
    return {
        "vip": "接班后按偏好接待，勿遗漏备注",
        "special": "按特殊需求安排，交接时当面说明",
        "complaint": "客诉未闭环，接班后优先跟进",
        "inbound": "到店前备好房与备注，到店时核对",
    }.get(stype or "", "接班时请关注并当面交接")


def _guest_card_fields(s: dict) -> dict:
    """前台可读字段：谁 / 什么情况 / 注意什么 / 接班做什么。"""
    stype = s.get("type") or ""
    type_label = s.get("type_label") or {
        "vip": "VIP 在店",
        "special": "特殊需求",
        "complaint": "客诉",
        "inbound": "即将到店",
    }.get(stype, "客情")
    who = (s.get("guest_token") or "客人").strip() or "客人"
    room = (s.get("room_no") or "").strip()
    if room in ("", "—", "-"):
        room = ""
    note = (s.get("content") or "").strip()
    if not note:
        if stype == "vip":
            note = "高价值客人，请按 VIP 标准接待"
        elif stype == "inbound":
            note = "今日/明日到店，请留意到达时间"
        else:
            note = "请查看系统备注并当面交接"

    if stype == "inbound":
        title = who
        subtitle = (s.get("title") or "").replace(who, "").strip(" ·") or type_label
    elif room:
        title = f"{who} · {room} 房"
        subtitle = type_label
    else:
        title = who
        subtitle = type_label

    return {
        "who": who,
        "room_no": room or None,
        "type_label": type_label,
        "title": title,
        "subtitle": subtitle,
        "note": note[:120],
        "action": _guest_action(stype),
    }


def _item(
    *,
    category: str,
    op: str,
    label: str,
    reason: str,
    payload: dict,
    source: str,
    confidence: float = 0.82,
    selected: bool = True,
) -> dict:
    if source not in VALID_SOURCES:
        source = "system_events"
    return {
        "id": f"sh-{uuid.uuid4().hex[:8]}",
        "category": category,
        "op": op,
        "label": label,
        "reason": reason,
        "payload": payload,
        "source": source,
        "confidence": confidence,
        "risk": "low",
        "selected": selected,
    }


def _situation_from_ws(ws: dict) -> dict:
    rev = ws.get("revenue", {})
    fl = ws.get("float", {})
    dep = ws.get("deposit", {})
    tasks = ws.get("tasks") or []
    guests = ws.get("guest_situations") or []
    p0 = sum(1 for t in tasks if t.get("priority") == "P0")
    channels = len(rev.get("channels") or [])
    float_diff = float(fl.get("diff") or 0)
    deposit_net = float(dep.get("net") or 0)

    metrics: list[dict] = [
        {
            "key": "revenue",
            "label": "本班营收",
            "value": f"¥{float(rev.get('total') or 0):,.2f}",
            "hint": f"渠道 {channels} 个",
            "tone": "neutral",
        },
        {
            "key": "tasks",
            "label": "待办",
            "value": str(len(tasks)),
            "hint": f"含 {p0} 条 P0" if p0 else "交接待办",
            "tone": "warn" if p0 else "neutral",
        },
        {
            "key": "guest",
            "label": "客情",
            "value": str(len(guests)),
            "hint": "重点客情",
            "tone": "info",
        },
    ]
    if abs(float_diff) >= 0.01:
        metrics.append(
            {
                "key": "float",
                "label": "备用金差异",
                "value": f"¥{float_diff:,.2f}",
                "hint": t("长款") if float_diff > 0 else t("短款"),
                "tone": "danger",
            }
        )
    if deposit_net > 0:
        metrics.append(
            {
                "key": "deposit",
                "label": "退押压力",
                "value": f"¥{deposit_net:,.2f}",
                "hint": t("待退押金"),
                "tone": "warn",
            }
        )

    bullets = [f"{m['label']} {m['value']}" + (f"（{m['hint']}）" if m.get("hint") else "") for m in metrics]
    return {
        "headline": t(
            "本班营收 ¥{amt} · 渠道 {n} 个",
            amt=f"{float(rev.get('total') or 0):,.2f}",
            n=channels,
        ),
        "bullets": bullets[:8],
        "metrics": metrics,
    }


def _source_for_situation(s: dict) -> str:
    t = s.get("type") or ""
    if t == "vip":
        return "oneid_history"
    if t == "inbound":
        return "system_events"
    if t == "complaint":
        return "feedback_sys"
    return "system_events"


def _stable_key(s: dict, idx: int) -> str:
    gid = s.get("guest_id")
    oid = s.get("order_id")
    if gid:
        return f"{s.get('type')}:{gid}"
    if oid:
        return f"{s.get('type')}:o{oid}"
    return f"{s.get('type')}:{idx}"


def _enrich_guest_situations(db: Session, hotel_id: int, situations: list[dict]) -> list[dict]:
    from models import Guest, Order

    out = []
    for i, s in enumerate(situations):
        row = dict(s)
        row["key"] = _stable_key(row, i)
        row["source"] = _source_for_situation(row)
        title = row.get("title") or ""
        # 反查 guest_id / order_id
        if not row.get("guest_id"):
            token = (row.get("guest_token") or "").replace("*", "")
            if token:
                g = db.query(Guest).filter(Guest.name.like(f"{token}%")).first()
                if g:
                    row["guest_id"] = str(g.id)
        if not row.get("order_id") and row.get("type") == "inbound":
            o = (
                db.query(Order)
                .filter(Order.hotel_id == hotel_id, Order.status.in_(("confirmed", "pending")))
                .order_by(Order.id.asc())
                .offset(i)
                .first()
            )
            if o:
                row["order_id"] = o.id
        if not row.get("guest_id"):
            continue  # 无来源 guest_id 的 inbound 仍可用 order 关联
        if row.get("type") == "inbound" and not row.get("guest_id") and not row.get("order_id"):
            continue
        out.append(row)
    # inbound 允许无 guest_id 但有 order
    for i, s in enumerate(situations):
        if s in [x for x in out]:
            continue
        row = dict(s)
        row["key"] = _stable_key(row, i)
        row["source"] = _source_for_situation(row)
        if row.get("type") == "inbound":
            out.append(row)
    return out[:8]


def _candidates_handover(db: Session, hotel_id: int, handover_id: int) -> tuple[dict, list[dict], list[str]]:
    ws = build_workspace(db, hotel_id, None)
    situation = _situation_from_ws(ws)
    items: list[dict] = []
    reasons = ["客情/待办须带来源；无来源不落库", "资金与实盘须人工盘点，AI 不碰"]

    raw_situations = _guest_situations(db, hotel_id)
    for i, s in enumerate(raw_situations):
        s = dict(s)
        s["key"] = _stable_key(s, i)
        src = _source_for_situation(s)
        if not s.get("guest_id") and not s.get("order_id"):
            continue
        card = _guest_card_fields(s)
        items.append(
            _item(
                category="guest_situation",
                op="write_guest_situation",
                label=card["title"],
                reason=card["note"],
                source=src,
                confidence=0.9 if s.get("type") in ("vip", "complaint") else 0.82,
                payload={
                    "key": s["key"],
                    "guest_id": str(s["guest_id"]) if s.get("guest_id") else None,
                    "order_id": s.get("order_id"),
                    "type": s.get("type"),
                    "type_label": card["type_label"],
                    "title": s.get("title") or card["title"],
                    "content": card["note"],
                    "room_no": card["room_no"],
                    "guest_token": card["who"],
                    "subtitle": card["subtitle"],
                    "action": card["action"],
                    "priority": "P0" if s.get("type") == "complaint" else "P1" if s.get("type") == "vip" else "P2",
                },
            )
        )

    for task in _build_tasks(db, hotel_id, ws.get("banner", {}).get("shift_no") or 1):
        title = (task.get("content") or "待办")[:48]
        owner = task.get("owner_name") or "前台"
        pri = task.get("priority") or "P2"
        action = "接班后尽快处理" if pri == "P0" else "本班未完结，请接班跟进"
        items.append(
            _item(
                category="task",
                op="write_task",
                label=title,
                reason=action,
                source="system_events",
                confidence=0.88 if pri == "P0" else 0.8,
                payload={
                    "title": task.get("content"),
                    "priority": pri,
                    "owner": owner,
                    "due": task.get("due_at"),
                    "type": "normal",
                    "linked_order_id": task.get("linked_order_id"),
                    "subtitle": f"负责人：{owner}" + (f" · {pri}" if pri else ""),
                    "action": action,
                    "note": "本班遗留待办，确认后写入交班清单",
                },
            )
        )

    assets = db.query(ShiftAssetCount).filter_by(handover_id=handover_id).all()
    for a in assets:
        if a.reorder_triggered or (
            a.expected_qty is not None and a.actual_qty is not None and int(a.actual_qty) < int(a.expected_qty or 0)
        ):
            qty = max(1, int(a.expected_qty or 0) - int(a.actual_qty or 0))
            items.append(
                _item(
                    category="replenish",
                    op="write_replenish_task",
                    label=f"{a.asset_name} 缺 {qty} 件",
                    reason=t("前台库存不足，请安排补货"),
                    source="inventory_sys",
                    payload={
                        "item": a.asset_name,
                        "qty": qty,
                        "type": "replenish",
                        "supply_id": a.supply_id,
                        "subtitle": "前台物资",
                        "note": f"实盘少于应备量，建议补 {qty} 件",
                        "action": "确认后生成补货工单",
                    },
                )
            )

    narrative = (
        f"本班营收 ¥{float(ws.get('revenue', {}).get('total') or 0):,.2f}；"
        f"待办 {len(ws.get('tasks') or [])} 条、客情 {len(raw_situations)} 条。"
        f"备用金{'已对平' if abs(float(ws.get('float', {}).get('diff') or 0)) < 0.01 else '有差异须说明'}。"
    )
    items.append(
        _item(
            category="narrative",
            op="write_narrative",
            label=t("交班口头摘要"),
            reason=t("给接班人念一遍的交接话术"),
            source="system_events",
            payload={
                "narrative": narrative,
                "subtitle": "交班口述",
                "note": "确认后写入本班叙事，供接班人查看",
                "action": "可改写后再确认",
            },
            selected=True,
        )
    )
    return situation, items, reasons


def _situation_from_takeover(tw: dict) -> dict:
    """接班视角：复核进度 + 钱物状态（只描述，不改数）。"""
    base = _situation_from_ws(tw)
    fl = tw.get("float") or {}
    gp = tw.get("guest_progress") or {}
    tp = tw.get("task_progress") or {}
    cp = tw.get("carryover_progress") or {}
    metrics = list(base.get("metrics") or [])
    float_confirmed = bool(fl.get("confirmed"))
    if float_confirmed:
        match = bool(fl.get("match_outgoing"))
        metrics.insert(
            0,
            {
                "key": "float_check",
                "label": "备用金重盘",
                "value": "一致" if match else "不符",
                "hint": "已重盘",
                "tone": "info" if match else "danger",
            },
        )
    else:
        metrics.insert(
            0,
            {
                "key": "float_check",
                "label": "备用金重盘",
                "value": "待重盘",
                "hint": "请先点钞",
                "tone": "warn",
            },
        )
    metrics.append(
        {
            "key": "guest_ack",
            "label": "客情已知晓",
            "value": f"{int(gp.get('done') or 0)}/{int(gp.get('total') or 0)}",
            "hint": "逐条复核",
            "tone": "warn" if int(gp.get("done") or 0) < int(gp.get("total") or 0) else "info",
        }
    )
    metrics.append(
        {
            "key": "task_claim",
            "label": "待办承接",
            "value": f"{int(tp.get('done') or 0)}/{int(tp.get('total') or 0)}",
            "hint": "未承接优先",
            "tone": "warn" if int(tp.get("done") or 0) < int(tp.get("total") or 0) else "neutral",
        }
    )
    if int(cp.get("total") or 0):
        metrics.append(
            {
                "key": "carry",
                "label": "上轮遗留",
                "value": f"{int(cp.get('done') or 0)}/{int(cp.get('total') or 0)}",
                "hint": "遗留复核",
                "tone": "warn" if int(cp.get("done") or 0) < int(cp.get("total") or 0) else "neutral",
            }
        )
    bullets = [f"{m['label']} {m['value']}" + (f"（{m['hint']}）" if m.get("hint") else "") for m in metrics]
    return {
        "headline": "接班复核 · " + (base.get("headline") or ""),
        "bullets": bullets[:8],
        "metrics": metrics[:8],
    }


def _candidates_takeover(db: Session, hotel_id: int, handover_id: int) -> tuple[dict, list[dict], list[str]]:
    tw = build_takeover_workspace(db, hotel_id, None)
    if not tw.get("ready"):
        raise InvalidStateError(tw.get("message") or "当前不可生成接班 AI 草稿")
    situation = _situation_from_takeover(tw)
    items: list[dict] = []
    reasons = [
        "接班要点/客情提醒/待办顺序须人工确认；资金与实盘数 AI 不改",
        "差异拟稿确认后上报店长；无差异时仍输出比对结论",
    ]

    fl = tw.get("float") or {}
    guests = tw.get("guest_situations") or []
    tasks = tw.get("tasks") or []
    carry = tw.get("carryover") or []
    unacked_guests = [g for g in guests if not g.get("acked")]
    unclaimed = [t for t in tasks if not t.get("claim_status")]
    pending_carry = [c for c in carry if c.get("pending") and not c.get("acked")]

    float_confirmed = bool(fl.get("confirmed"))
    float_match = bool(fl.get("match_outgoing"))
    asset_diffs = [a for a in (tw.get("assets") or []) if (a.get("diff_vs_outgoing") or 0) != 0]

    # ① 接班要点（始终有，确认后写入审计快照）
    brief_bits = [
        f"客情待知晓 {len(unacked_guests)}/{len(guests)}",
        f"待办未承接 {len(unclaimed)}/{len(tasks)}",
    ]
    if float_confirmed:
        brief_bits.append("备用金重盘" + ("一致" if float_match else "不符须上报"))
    else:
        brief_bits.append("备用金尚未重盘")
    if pending_carry:
        brief_bits.append(f"上轮遗留 {len(pending_carry)} 条")
    brief = (
        "接班请先核对钱物，再按客情与待办逐条承接。"
        + "；".join(brief_bits)
        + "。签字即代表你对本班数字负责，不符勿硬签。"
    )
    items.append(
        _item(
            category="takeover_brief",
            op="write_takeover_brief",
            label=t("接班要点（口述稿）"),
            reason=t("给接班人念一遍的开班话术"),
            source="system_events",
            confidence=0.9,
            payload={
                "brief": brief[:500],
                "subtitle": "接班口述",
                "note": brief[:120],
                "action": "可改写后再确认写入",
            },
            selected=True,
        )
    )

    # ② 备用金 / 实物比对结论（仅建议，不写实盘）
    if float_confirmed and float_match and not asset_diffs:
        items.append(
            _item(
                category="advice",
                op="write_advice",
                label=t("钱物比对结论：一致"),
                reason=t("重盘与交班人对平，可继续客情/待办复核"),
                source="system_events",
                payload={
                    "topic": "float_asset_match",
                    "note": "备用金重盘与交班人一致，实物未见复点差异。请继续完成客情已知晓与待办承接后再签字。",
                    "subtitle": "仅建议 · 不改数字",
                    "action": "确认后记入接班审计快照",
                },
                selected=True,
            )
        )
    elif not float_confirmed:
        items.append(
            _item(
                category="advice",
                op="write_advice",
                label=t("请先完成备用金重盘"),
                reason=t("未重盘无法出具比对结论"),
                source="system_events",
                payload={
                    "topic": "float_pending",
                    "note": "请先在「钱复核」完成备用金总额重盘；对平或差异后再让 AI 拟比对/上报稿。",
                    "subtitle": "仅建议",
                    "action": "重盘后再点重新生成",
                },
                selected=True,
            )
        )
    elif float_confirmed and not float_match:
        items.append(
            _item(
                category="advice",
                op="write_advice",
                label=t("备用金不符 · 勿硬签"),
                reason=t("短款/长款须差异上报"),
                source="system_events",
                payload={
                    "topic": "float_mismatch",
                    "note": "备用金重盘与交班人不符。请勾选下方差异拟稿上报，不要直接签字接收。",
                    "subtitle": "仅建议",
                    "action": "优先处理差异拟稿",
                },
                selected=True,
            )
        )

    # ③ 客情关注（未勾选「已知晓」的真实客情）
    for g in unacked_guests[:6]:
        card = _guest_card_fields(g)
        src = g.get("source") or _source_for_situation(g)
        items.append(
            _item(
                category="guest_focus",
                op="write_guest_focus",
                label=card["title"],
                reason=card["action"],
                source=src if src in VALID_SOURCES else "system_events",
                confidence=0.9 if g.get("type") in ("vip", "complaint") else 0.84,
                payload={
                    "key": g.get("key"),
                    "guest_id": str(g["guest_id"]) if g.get("guest_id") else None,
                    "order_id": g.get("order_id"),
                    "type": g.get("type"),
                    "type_label": card["type_label"],
                    "guest_token": card["who"],
                    "room_no": card["room_no"],
                    "subtitle": card["subtitle"],
                    "note": card["note"],
                    "action": card["action"],
                    "priority": "P0" if g.get("type") == "complaint" else "P1" if g.get("type") == "vip" else "P2",
                },
                selected=g.get("type") in ("vip", "complaint", "special"),
            )
        )

    # ④ 待办承接顺序（未承接，优先 P0/P1）
    ranked = sorted(
        unclaimed,
        key=lambda t: (0 if t.get("priority") == "P0" else 1 if t.get("priority") == "P1" else 2, t.get("index", 0)),
    )
    for task in ranked[:8]:
        pri = task.get("priority") or "P2"
        title = (task.get("content") or "待办")[:48]
        owner = task.get("owner_name") or "前台"
        action = "建议优先承接" if pri == "P0" else "本班请承接或升级"
        items.append(
            _item(
                category="claim_hint",
                op="write_claim_hint",
                label=title,
                reason=action,
                source="system_events",
                confidence=0.88 if pri == "P0" else 0.8,
                payload={
                    "task_index": task.get("index"),
                    "title": task.get("content"),
                    "priority": pri,
                    "owner": owner,
                    "subtitle": f"负责人：{owner} · {pri}",
                    "note": "确认后写入接班关注清单（不会自动点「承接」）",
                    "action": action,
                },
                selected=pri in ("P0", "P1"),
            )
        )

    # ⑤ 上轮遗留提醒
    for c in pending_carry[:4]:
        items.append(
            _item(
                category="claim_hint",
                op="write_claim_hint",
                label=(c.get("content") or "上轮遗留")[:48],
                reason=t("上轮遗留，请勾选已知晓"),
                source="system_events",
                payload={
                    "carryover_id": c.get("id"),
                    "title": c.get("content"),
                    "priority": "P1",
                    "subtitle": f"{c.get('shift_no') or ''} 班遗留",
                    "note": "遗留事项需接班人复核",
                    "action": "当面核对后勾选已知晓",
                },
                selected=True,
            )
        )

    # ⑥ 差异拟稿（有真实差才出，确认后写 shift_receive_diff）
    if float_confirmed and not float_match:
        diff = round(float(fl.get("received_actual") or 0) - float(fl.get("outgoing_actual") or 0), 2)
        items.append(
            _item(
                category="diff_draft",
                op="write_diff_draft",
                label=f"备用金重盘差异 ¥{abs(diff)}",
                reason=t("接班人重盘与交班人不符"),
                source="system_events",
                payload={
                    "item_type": "float",
                    "item_key": "total",
                    "diff_amount": diff,
                    "declared_val": float(fl.get("outgoing_actual") or 0),
                    "received_val": float(fl.get("received_actual") or 0),
                    "reason": "重盘发现差异，待核对找零/交接过程",
                    "suggestion": "追补" if diff < 0 else "交回",
                    "subtitle": "差异上报稿",
                    "note": "确认后写入差异台账并标记需店长审核",
                    "action": "追补" if diff < 0 else "交回",
                },
                selected=True,
            )
        )
    for a in asset_diffs:
        d = int(a.get("diff_vs_outgoing") or 0)
        items.append(
            _item(
                category="diff_draft",
                op="write_diff_draft",
                label=f"{a.get('name')} 复点差异 {d:+d}",
                reason=t("实物复点与交班人实盘不符"),
                source="inventory_sys",
                payload={
                    "item_type": "asset",
                    "item_key": str(a.get("id")),
                    "diff_amount": float(d),
                    "declared_val": float(a.get("outgoing_qty") or 0),
                    "received_val": float(a.get("received_qty") or 0),
                    "reason": f"{a.get('name')} 复点差 {abs(d)}，待核对",
                    "suggestion": "追补" if d < 0 else "交回",
                    "subtitle": "实物差异",
                    "note": "确认后上报，不改实盘数",
                    "action": "追补" if d < 0 else "交回",
                },
                selected=True,
            )
        )

    return situation, items, reasons


def _refine_with_llm(
    db: Session,
    *,
    scene: str,
    situation: dict,
    items: list[dict],
    reasons: list[str],
) -> tuple[list[dict], list[str], str, str | None, str, str | None, str | None]:
    if not items:
        return items, reasons, "", None, "unavailable", None, t("暂无事实可供模型分析")
    system = get_scene_prompt("shift", scene) or (SYSTEM_HANDOVER if scene == "handover" else SYSTEM_TAKEOVER)
    try:
        meta = get_shift_scene(scene)
        if not get_scene_prompt("shift", scene) and meta.get("system_prompt"):
            system = meta["system_prompt"]
    except InvalidStateError:
        pass
    system = compose_system(system)
    brief_items = [
        {
            "id": i["id"],
            "category": i["category"],
            "label": i["label"],
            "source": i.get("source"),
            "priority": (i.get("payload") or {}).get("priority"),
            "hint": (i.get("reason") or "")[:60],
        }
        for i in items
    ]
    brief = json.dumps({"situation": situation, "candidates": brief_items}, ensure_ascii=False)[:7000]
    if scene == "handover":
        user = (
            t("以下为本班真实候选（只能从中选 id）：")
            + f"\n{brief}\n\n"
            + t("请按系统规则筛选并生成交班摘要/叙事。只输出 JSON。")
            + " /no_think"
        )
    else:
        user = (
            t("以下为接班真实候选（只能从中选 id，禁止编造）：")
            + f"\n{brief}\n\n"
            + t("请生成接班要点 brief，并筛选客情关注/待办承接/比对结论/差异拟稿。只输出 JSON。")
            + " /no_think"
        )
    call = run_locale_llm_json(db, system=system, user=user)
    if call.error and not call.parsed:
        return [], reasons, "", None, "unavailable", None, call.error
    parsed = call.parsed
    try:
        cfg = load_llm_config(db)
        from extensions.llm.facade import resolve_model_name, resolve_provider_id

        provider = resolve_provider_id(cfg)
        model = call.model or resolve_model_name(cfg)
    except Exception:
        from extensions.llm.facade import resolve_model_name, resolve_provider_id

        provider = resolve_provider_id()
        model = call.model or resolve_model_name()

    if isinstance(parsed.get("selected_ids"), list):
        sel = set(str(x) for x in parsed["selected_ids"])
        for it in items:
            it["selected"] = it["id"] in sel

    n_sel = sum(1 for i in items if i.get("selected"))
    raw_sum = str(parsed.get("summary") or "").strip()
    summary = locale_text(raw_sum, "建议确认 {n} 项", 80) if raw_sum else t("建议确认 {n} 项", n=n_sel)
    if "{n}" in summary:
        summary = t("建议确认 {n} 项", n=n_sel)
    note = locale_optional(
        parsed.get("narrative") or parsed.get("situation_note") or parsed.get("brief"),
        500,
    )
    llm_reasons = locale_str_list(parsed.get("reasons"))
    if llm_reasons:
        reasons = llm_reasons

    if scene == "handover" and note:
        for it in items:
            if it["op"] == "write_narrative":
                it["payload"]["narrative"] = note[:500]
                it["selected"] = True

    if scene == "takeover":
        brief_txt = locale_optional(parsed.get("brief") or note, 500) or note
        if brief_txt:
            for it in items:
                if it["op"] == "write_takeover_brief":
                    it["payload"]["brief"] = brief_txt[:500]
                    it["payload"]["note"] = brief_txt[:120]
                    it["selected"] = True
        by_id = {it["id"]: it for it in items}
        for patch in parsed.get("guest_patches") or []:
            if not isinstance(patch, dict):
                continue
            it = by_id.get(str(patch.get("id") or ""))
            if not it or it.get("op") != "write_guest_focus":
                continue
            pnote = locale_optional(patch.get("note"), 120)
            if pnote:
                it["payload"]["note"] = pnote
            paction = locale_optional(patch.get("action"), 48)
            if paction:
                it["payload"]["action"] = paction
            it["selected"] = True
        for patch in parsed.get("claim_patches") or []:
            if not isinstance(patch, dict):
                continue
            it = by_id.get(str(patch.get("id") or ""))
            if not it or it.get("op") != "write_claim_hint":
                continue
            paction = locale_optional(patch.get("action"), 48)
            if paction:
                it["payload"]["action"] = paction
            it["selected"] = True
        for patch in parsed.get("advice_patches") or []:
            if not isinstance(patch, dict):
                continue
            it = by_id.get(str(patch.get("id") or ""))
            if not it or it.get("op") != "write_advice":
                continue
            pnote = locale_optional(patch.get("note"), 160)
            if pnote:
                it["payload"]["note"] = pnote
            it["selected"] = True
        for patch in parsed.get("diff_patches") or []:
            if not isinstance(patch, dict):
                continue
            it = by_id.get(str(patch.get("id") or ""))
            if not it or it.get("op") != "write_diff_draft":
                continue
            preason = locale_optional(patch.get("reason"), 120)
            if preason:
                it["payload"]["reason"] = preason
                it["payload"]["note"] = preason
            sug = str(patch.get("suggestion") or "").strip()
            if sug in ("追补", "交回"):
                it["payload"]["suggestion"] = sug
                it["payload"]["action"] = sug
            it["selected"] = True

    for it in items:
        if it.get("selected"):
            # 置信度与厂商无关（本地 Ollama / 硅基流动 / DeepSeek 一视同仁）
            it["confidence"] = 0.88

    source = "llm" if parsed else "unavailable"
    if source != "llm":
        return [], reasons, "", None, "unavailable", None, call.error
    return items, reasons, summary, note, source, model, call.error


def generate_shift_ai_draft(db: Session, hotel_id: int, handover_id: int, scene: str = "handover") -> dict:
    _ensure_shift_scenes_registered()
    scene = (scene or "handover").strip()
    get_shift_scene(scene)  # 校验
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    if row.status == "archived":
        raise InvalidStateError("已归档不可生成 AI 草稿")

    situation, items, reasons, title = build_shift_candidates(db, hotel_id, handover_id, scene)

    items, reasons, summary, _, source, model, llm_error = _refine_with_llm(
        db, scene=scene, situation=situation, items=items, reasons=reasons
    )
    session_id = f"shift-{uuid.uuid4().hex[:12]}"
    ident = {}
    if source == "llm":
        ident = llm_identity(load_llm_config(db), {"model": model} if model else None)
    plan = {
        "plan_id": f"shift-{scene}-{uuid.uuid4().hex[:10]}",
        "handover_id": handover_id,
        "hotel_id": hotel_id,
        "scene": scene,
        "title": title,
        "situation": situation,
        "summary": summary,
        "reasons": reasons,
        "items": items,
        "source": source,
        "llm_error": llm_error,
        "ai_session_id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "draft",
        "hint": t("勾选后填工号确认，才会写入交班记录并打 AI 审计标记；资金/实盘/签字 AI 不碰"),
        **ident,
    }
    row.ai_draft_json = _jsave(plan)
    row.ai_session_id = session_id
    _log(db, handover_id, hotel_id, "ai_draft_generate", None, "ai_agent", {"scene": scene, "count": len(items)})
    db.commit()
    return plan


def _exec_item(
    db: Session,
    hotel_id: int,
    handover_id: int,
    item: dict,
    *,
    approved_by: int | None,
    ai_session_id: str,
) -> dict:
    op = item.get("op")
    payload = item.get("payload") or {}
    source = item.get("source") or "system_events"
    row = db.get(ShiftHandover, handover_id)
    if not row:
        return {"ok": False, "error": "交班不存在"}

    if op == "write_guest_situation":
        if not payload.get("guest_id") and not payload.get("order_id"):
            return {"ok": False, "skipped": True, "error": "无 guest_id/order_id 来源"}
        if source not in VALID_SOURCES:
            return {"ok": False, "error": "无效 source"}
        return {"ok": True, "op": op, "payload": payload}

    if op == "write_task":
        db.add(
            ShiftHandoverTask(
                handover_id=handover_id,
                hotel_id=hotel_id,
                priority=payload.get("priority") or "P2",
                content=payload.get("title") or payload.get("content") or "待办",
                owner_name=payload.get("owner") or "前台",
                due_at=datetime.fromisoformat(payload["due"]) if payload.get("due") else None,
                status="open",
                linked_order_id=payload.get("linked_order_id"),
                task_type="normal",
                created_by="ai_agent",
                approved_by=approved_by,
                ai_session_id=ai_session_id,
                source=source,
            )
        )
        return {"ok": True, "op": op}

    if op == "write_replenish_task":
        db.add(
            ShiftHandoverTask(
                handover_id=handover_id,
                hotel_id=hotel_id,
                priority="P1",
                content=f"补货 · {payload.get('item')} ×{payload.get('qty')}",
                owner_name="采购",
                status="open",
                task_type="replenish",
                created_by="ai_agent",
                approved_by=approved_by,
                ai_session_id=ai_session_id,
                source="inventory_sys",
            )
        )
        return {"ok": True, "op": op}

    if op == "write_narrative":
        row.narrative = (payload.get("narrative") or "")[:2000]
        return {"ok": True, "op": op}

    if op == "write_takeover_brief":
        brief = (payload.get("brief") or payload.get("note") or "")[:2000]
        if not brief:
            return {"ok": False, "error": "接班要点为空"}
        return {"ok": True, "op": op, "brief": brief}

    if op == "write_guest_focus":
        if not payload.get("key") and not payload.get("guest_id") and not payload.get("order_id"):
            return {"ok": False, "skipped": True, "error": "无客情来源"}
        return {
            "ok": True,
            "op": op,
            "focus": {
                "key": payload.get("key"),
                "guest_id": payload.get("guest_id"),
                "type": payload.get("type"),
                "label": item.get("label"),
                "note": payload.get("note"),
                "action": payload.get("action"),
                "source": source,
            },
        }

    if op == "write_claim_hint":
        return {
            "ok": True,
            "op": op,
            "hint": {
                "task_index": payload.get("task_index"),
                "carryover_id": payload.get("carryover_id"),
                "title": payload.get("title") or item.get("label"),
                "priority": payload.get("priority"),
                "action": payload.get("action"),
                "source": source,
            },
        }

    if op == "write_advice":
        return {
            "ok": True,
            "op": op,
            "advice": {
                "topic": payload.get("topic") or "general",
                "note": payload.get("note") or item.get("label"),
                "source": source,
            },
        }

    if op == "write_diff_draft":
        db.add(
            ShiftReceiveDiff(
                handover_id=handover_id,
                hotel_id=hotel_id,
                item_type=payload.get("item_type") or "float",
                item_key=payload.get("item_key") or "",
                declared_val=payload.get("declared_val"),
                received_val=payload.get("received_val"),
                diff_val=payload.get("diff_amount"),
                reason=payload.get("reason") or "",
                suggestion=payload.get("suggestion"),
                reporter_user_id=approved_by,
                status="pending_manager",
            )
        )
        row.manager_required = True
        return {"ok": True, "op": op}

    return {"ok": False, "error": f"未知 op {op}"}


def confirm_shift_ai_draft(
    db: Session,
    hotel_id: int,
    *,
    plan: dict,
    approved_by: int,
    operator_name: str = "",
) -> dict:
    handover_id = int(plan.get("handover_id") or 0)
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    if row.status == "archived":
        raise InvalidStateError("已归档不可确认")

    ai_session_id = plan.get("ai_session_id") or row.ai_session_id or f"shift-{uuid.uuid4().hex[:8]}"
    selected = [it for it in (plan.get("items") or []) if it.get("selected")]
    if not selected:
        raise InvalidStateError("请至少勾选一项 AI 草稿")

    guest_items = []
    focus_items = []
    claim_hints = []
    advice_items = []
    takeover_brief = ""
    results = []
    for it in selected:
        res = _exec_item(
            db,
            hotel_id,
            handover_id,
            it,
            approved_by=approved_by,
            ai_session_id=ai_session_id,
        )
        results.append(res)
        if not res.get("ok"):
            continue
        if it.get("op") == "write_guest_situation":
            p = res.get("payload") or it.get("payload") or {}
            guest_items.append({**p, "ai_generated": True, "source": it.get("source"), "approved_by": approved_by})
        elif it.get("op") == "write_takeover_brief" and res.get("brief"):
            takeover_brief = res["brief"]
        elif it.get("op") == "write_guest_focus" and res.get("focus"):
            focus_items.append(res["focus"])
        elif it.get("op") == "write_claim_hint" and res.get("hint"):
            claim_hints.append(res["hint"])
        elif it.get("op") == "write_advice" and res.get("advice"):
            advice_items.append(res["advice"])

    approved_snapshot = _jload(row.ai_approved_json, {})
    if guest_items:
        approved_snapshot["guest_situations"] = guest_items
        row.guest_situations_snapshot = _jsave(guest_items)
    if row.narrative:
        approved_snapshot["narrative"] = row.narrative
    if takeover_brief:
        approved_snapshot["takeover_brief"] = takeover_brief
    if focus_items:
        approved_snapshot["takeover_guest_focus"] = focus_items
    if claim_hints:
        approved_snapshot["takeover_claim_hints"] = claim_hints
    if advice_items:
        approved_snapshot["takeover_advice"] = advice_items
    approved_snapshot["items"] = [
        {"id": it["id"], "op": it.get("op"), "label": it.get("label"), "source": it.get("source")} for it in selected
    ]
    approved_snapshot["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
    approved_snapshot["approved_by"] = approved_by
    approved_snapshot["ai_session_id"] = ai_session_id
    scene = plan.get("scene") or "handover"
    approved_snapshot["scene"] = scene

    row.ai_approved_json = _jsave(approved_snapshot)
    row.ai_draft_json = None
    row.ai_draft_confirmed_at = datetime.now()
    row.ai_draft_confirmed_by = approved_by
    row.ai_session_id = ai_session_id

    _log(
        db,
        handover_id,
        hotel_id,
        "ai_draft_confirm",
        approved_by,
        operator_name,
        {"count": len(selected), "ai_session_id": ai_session_id, "scene": scene},
    )
    db.commit()
    return {
        "ok": True,
        "message": f"已确认 {len(selected)} 项 AI 草稿并写入交班记录",
        "results": results,
        "ai_session_id": ai_session_id,
    }


def reject_shift_ai_draft(
    db: Session, hotel_id: int, handover_id: int, *, operator_id: int | None, reason: str = ""
) -> dict:
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    draft = _jload(row.ai_draft_json, {})
    _log(
        db,
        handover_id,
        hotel_id,
        "ai_draft_reject",
        operator_id,
        "",
        {"reason": reason[:200], "draft_id": draft.get("plan_id")},
    )
    row.ai_draft_json = None
    db.commit()
    return {"ok": True, "message": "AI 草稿已驳回"}


def ai_status_for_handover(row: ShiftHandover) -> dict:
    draft = _jload(row.ai_draft_json, None)
    approved = _jload(row.ai_approved_json, None)
    return {
        "has_draft": bool(draft),
        "has_approved": bool(approved),
        "draft": draft,
        "narrative": row.narrative or (approved or {}).get("narrative") or "",
        "takeover_brief": (approved or {}).get("takeover_brief") or "",
        "takeover_advice": (approved or {}).get("takeover_advice") or [],
        "takeover_guest_focus": (approved or {}).get("takeover_guest_focus") or [],
        "takeover_claim_hints": (approved or {}).get("takeover_claim_hints") or [],
        "confirmed_at": row.ai_draft_confirmed_at.isoformat(timespec="minutes") if row.ai_draft_confirmed_at else None,
        "ai_session_id": row.ai_session_id,
    }


from finance.shift_handover_service.task_service import (  # noqa: E402
    guest_situations_for_display,
    tasks_for_display,
)


def _ensure_shift_scenes_registered() -> None:
    if list_shift_scenes():
        return
    register_shift_scene(
        "handover",
        title="AI 交班草稿",
        builder=_candidates_handover,
        system_prompt=SYSTEM_HANDOVER,
    )
    register_shift_scene(
        "takeover",
        title="AI 接班草稿",
        builder=_candidates_takeover,
        system_prompt=SYSTEM_TAKEOVER,
    )


_ensure_shift_scenes_registered()
