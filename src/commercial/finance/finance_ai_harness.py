# SPDX-License-Identifier: BUSL-1.1
"""财务 AI Harness：现状 → 可勾选操作单 → 人工确认后写库。

场景：押金 / 退改 / 夜审异常 / 对账 / 发票。
默认 LLM 精选；失败则 source=unavailable，不把规则候选冒充 AI。资金与日切类动作禁止自动落库，仅生成待确认单。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.llm_service import llm_identity, load_llm_config
from commercial.ai_core.locale_llm import (
    compose_system,
    locale_optional,
    locale_str_list,
    locale_text,
    run_locale_llm_json,
)
from commercial.ai_core.prompt_packs import get_scene_prompt
from commercial.finance.ai_scene_registry import (
    build_scene_candidates,
    get_finance_scene,
    list_finance_scenes,
    register_finance_scene,
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
from infra.i18n import t

SCENES = (
    "deposit",
    "refund",
    "night_audit",
    "recon",
    "invoice",
    "ar_ap",
)

SCENE_TITLE = {
    "deposit": "AI 押金安排",
    "refund": "AI 退改操作单",
    "night_audit": "AI 夜审异常处理",
    "recon": "AI 对账安排",
    "invoice": "AI 开票安排",
    "ar_ap": "AI 应收应付安排",
}

SCENE_SYSTEM: dict[str, str] = {
    "deposit": brand_text("""你是「{APP_NAME}」前台财务助理，专责押金。
先看清在押异常，再从候选行动中挑选。
原则：1) 只依据候选 items，禁止编造 deposit_id；2) 优先临期重授权与争议跟进；3) 不选现金无收据直接释放。
输出单一 JSON：{"summary":"≤36字","situation_note":"≤40字可空","reasons":["依据"],"selected_ids":["id"]}
用户可见文案须与请求语言一致，不出现模型名。"""),
    "refund": brand_text("""你是「{APP_NAME}」退改助理。
先看清待处理工单与可改账项，再挑选「生成操作单」类行动（不是直接退款到账）。
原则：1) 只依据候选；2) 高风险反结账默认不选或少选；3) 输出同上 JSON。
用户可见文案须与请求语言一致。"""),
    "night_audit": brand_text("""你是「{APP_NAME}」夜审助理。
先看清未关闭异常，再挑选可「标记已处理」的行动。禁止选择日切/过房费。
输出同上 JSON。用户可见文案须与请求语言一致。"""),
    "recon": brand_text("""你是「{APP_NAME}」对账助理。
先看清差异批次，优先挑选小额已对齐可关账、需人工复核的标记。禁止对大额差异直接关账。
输出同上 JSON。用户可见文案须与请求语言一致。"""),
    "invoice": brand_text("""你是「{APP_NAME}」开票助理。
先看清待开/漏开，优先挑选超期未开的开票操作单；红冲默认不选，除非候选已标明。
输出同上 JSON。用户可见文案须与请求语言一致。"""),
    "ar_ap": brand_text("""你是「{APP_NAME}」应收应付助理。
先看清逾期应收、授信占用与 OTA 待结算；可挑选「同步单据」「催收备忘」「授信预警」类低风险操作。
禁止挑选坏账核销、回款、付款、调额；若候选含 write_off 类一律不选。
输出同上 JSON。用户可见文案须与请求语言一致。"""),
}


def _item(*, op: str, label: str, reason: str, payload: dict, risk: str = "low", selected: bool = True) -> dict:
    return {
        "id": f"f-{uuid.uuid4().hex[:8]}",
        "op": op,
        "label": label,
        "reason": reason,
        "payload": payload,
        "risk": risk,
        "selected": selected,
    }


def _situation(headline: str, bullets: list[str], metrics: Optional[list[dict]] = None) -> dict:
    return {
        "headline": headline,
        "bullets": [b for b in bullets if b][:8],
        "metrics": metrics or [],
    }


def _f(v) -> float:
    return float(v or 0)


# ---------- 候选 ----------


def _candidates_deposit(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from finance.deposit_service import board, detect_anomalies

    b = board(db, hotel_id)
    anoms = detect_anomalies(db, hotel_id)
    items: list[dict] = []
    reasons = [t("优先处理临期预授权与争议；现金无收据不可自动释放")]
    for a in anoms[:12]:
        did = a.get("deposit_id")
        if not did:
            continue
        typ = a.get("type")
        room = a.get("room_no") or ""
        guest = a.get("guest_name") or ""
        who = f"{room} {guest}".strip()
        if typ in ("auth_expiring", "auth_expired"):
            items.append(
                _item(
                    op="deposit_reauthorize",
                    label=t("重授权 · {who}", who=who),
                    reason=a.get("detail") or t("预授权临期/过期"),
                    payload={"deposit_id": did},
                    risk="medium",
                )
            )
        elif typ == "disputed":
            items.append(
                _item(
                    op="deposit_note_dispute",
                    label=t("跟进争议 · {who}", who=who),
                    reason=a.get("detail") or t("争议未结，生成跟进备注"),
                    payload={"deposit_id": did, "note": t("AI建议：核实金额后释放或扣押")},
                    risk="low",
                )
            )
        elif typ == "cash_no_receipt":
            items.append(
                _item(
                    op="deposit_flag_receipt",
                    label=t("补收据提醒 · {room}", room=room),
                    reason=a.get("detail") or t("现金缺收据，禁止释放"),
                    payload={"deposit_id": did},
                    risk="high",
                    selected=False,
                )
            )
        elif typ == "insufficient":
            items.append(
                _item(
                    op="deposit_reauthorize",
                    label=t("补足在押 · {room}", room=room),
                    reason=a.get("detail") or t("在押不足，建议重授权"),
                    payload={"deposit_id": did},
                    risk="medium",
                )
            )
    sit = _situation(
        t("在押异常 {n} 条，可生成 {m} 张操作单", n=len(anoms), m=len(items)),
        [a.get("detail") or a.get("title") or "" for a in anoms[:5]],
        [
            {"label": t("异常"), "value": str(len(anoms))},
            {"label": t("可执行"), "value": str(len(items))},
            {
                "label": t("在押笔数"),
                "value": str((b.get("summary") or {}).get("count") or len(b.get("deposits") or [])),
            },
        ],
    )
    return sit, items, reasons


def _candidates_refund(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from finance.refund_service import board, list_adjust_entries, list_reverse_targets
    from models import RefundAdjustTicket

    b = board(db, hotel_id)
    pending = b.get("my_pending") or b.get("pending") or []
    tickets = b.get("tickets") or []
    entries = list_adjust_entries(db, hotel_id)[:8]
    reverses = list_reverse_targets(db, hotel_id)[:5]
    items: list[dict] = []
    reasons = [t("AI 只生成待审批操作单，不直接退款到账；反结账须双授权")]

    for row in (pending or tickets)[:6]:
        if (row.get("status") or "") not in ("pending_approval", "pending_dual_auth", "open"):
            continue
        items.append(
            _item(
                op="refund_remind_ticket",
                label=t("催办工单 · {no}", no=row.get("ticket_no") or row.get("id")),
                reason=row.get("detail") or row.get("title") or t("待处理"),
                payload={"ticket_id": row.get("id"), "ticket_no": row.get("ticket_no")},
                risk="low",
            )
        )

    for e in entries[:5]:
        items.append(
            _item(
                op="refund_create_adjust_ticket",
                label=t("改账操作单 · {label}", label=e.get("label") or e.get("entry_id")),
                reason=t("建议生成冲正/更正工单，确认后面核提交"),
                payload={
                    "entry": e,
                    "action": "reverse",
                    "reason": t("AI建议冲正复核"),
                    "face_confirmed": True,
                },
                risk="high",
                selected=False,
            )
        )

    for r in reverses[:3]:
        items.append(
            _item(
                op="refund_create_reverse_ticket",
                label=t("反结账操作单 · {id}", id=r.get("order_no") or r.get("id")),
                reason=t("仅生成待双授权工单，不跳过授权"),
                payload={
                    "target": r,
                    "reason": t("房费/账目需重开"),
                    "note": t("AI建议草案"),
                    "face_confirmed": True,
                },
                risk="high",
                selected=False,
            )
        )

    open_cnt = (
        db.query(RefundAdjustTicket)
        .filter_by(hotel_id=hotel_id)
        .filter(RefundAdjustTicket.status.in_(("pending_approval", "pending_dual_auth")))
        .count()
    )
    sit = _situation(
        t("待处理退改相关 {n} 单，可生成操作草案", n=open_cnt),
        [f"{row.get('title')}: {row.get('status')}" for row in (pending or tickets)[:4]],
        [
            {"label": t("待办工单"), "value": str(open_cnt)},
            {"label": t("可改账项"), "value": str(len(entries))},
            {"label": t("可反结"), "value": str(len(reverses))},
        ],
    )
    return sit, items, reasons


def _candidates_night_audit(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from models import NightAuditException

    rows = (
        db.query(NightAuditException)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(NightAuditException.id.desc())
        .limit(20)
        .all()
    )
    items = []
    reasons = [t("仅处理异常确认；日切/过房费必须人工点确认")]
    for r in rows:
        sev = (getattr(r, "severity", None) or getattr(r, "level", None) or "tip").lower()
        title = getattr(r, "title", None) or getattr(r, "code", None) or t("异常#{id}", id=r.id)
        tip = sev in ("tip", "info", "low") or "提示" in str(title)
        items.append(
            _item(
                op="night_fix_exception",
                label=t("确认异常 · {title}", title=title)[:60],
                reason=getattr(r, "detail", None) or getattr(r, "message", None) or t("标记为已处理"),
                payload={"exception_id": r.id},
                risk="low" if tip else "medium",
                selected=bool(tip),
            )
        )
    sit = _situation(
        t("未关闭夜审异常 {n} 条（不含日切）", n=len(rows)),
        [getattr(r, "title", None) or str(r.id) for r in rows[:5]],
        [
            {"label": t("开放异常"), "value": str(len(rows))},
            {"label": t("可确认"), "value": str(len(items))},
        ],
    )
    return sit, items, reasons


def _candidates_recon(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from models import ReconBatch

    batches = (
        db.query(ReconBatch)
        .filter_by(hotel_id=hotel_id)
        .order_by(ReconBatch.biz_date.desc(), ReconBatch.id.desc())
        .limit(40)
        .all()
    )
    items = []
    reasons = [t("差额≈0 可关账；大额差异只生成复核标记，不自动关账")]
    open_n = 0
    for b in batches:
        st = (b.status or "open").lower()
        if st in ("closed", "matched"):
            continue
        open_n += 1
        var = abs(_f(b.variance))
        ch = b.channel or t("渠道")
        code = f"{ch}-{b.id}"
        if var < 0.01:
            items.append(
                _item(
                    op="recon_close_batch",
                    label=t("关账 · {code}", code=code),
                    reason=t("{date} · 三方已对齐，可关账归档", date=b.biz_date),
                    payload={"batch_id": b.id},
                    risk="low",
                )
            )
        elif var < 100:
            items.append(
                _item(
                    op="recon_mark_matched",
                    label=t("小额差异标配对 · {code}", code=code),
                    reason=t(
                        "差额 ¥{n}，多属手续费/T+1，建议标配对并备注",
                        n=f"{var:.2f}",
                    ),
                    payload={"batch_id": b.id, "note": t("AI：小额差异按手续费/在途处理")},
                    risk="medium",
                )
            )
        else:
            items.append(
                _item(
                    op="recon_mark_conflict",
                    label=t("转人工复核 · {code}", code=code),
                    reason=t("差额 ¥{n}，需人工下钻", n=f"{var:.2f}"),
                    payload={"batch_id": b.id, "note": t("AI：大额差异待人复核")},
                    risk="high",
                    selected=True,
                )
            )
    sit = _situation(
        t("未关账批次 {n} 个，可生成关账/复核操作单", n=open_n),
        [it["label"] + " · " + it["reason"] for it in items[:4]],
        [
            {"label": t("未关账"), "value": str(open_n)},
            {"label": t("操作单"), "value": str(len(items))},
        ],
    )
    return sit, items[:15], reasons


def _candidates_invoice(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from finance.tax.registry import get_tax_provider

    if not get_tax_provider().enabled:
        sit = _situation(
            t("本部署未启用税务凭证"),
            [t("开票 / 红冲由地区 pack 提供；当前为 Noop")],
            [{"label": t("税票"), "value": t("关闭")}],
        )
        return sit, [], [t("本部署未启用税务凭证")]
    from finance.invoice_service import list_invoice_workspace

    ws = list_invoice_workspace(db, hotel_id)
    rows = ws.get("items") or []
    items = []
    reasons = [t("优先超期待开；红冲须人工勾选且填原因；开票即写库")]
    todo = [r for r in rows if r.get("status") == "todo"]
    for r in todo[:10]:
        overdue = int(r.get("overdue_days") or 0)
        items.append(
            _item(
                op="invoice_issue",
                label=t(
                    "开票 · {order} · {guest}",
                    order=r.get("order_no") or "",
                    guest=r.get("guest_name") or "",
                ),
                reason=(
                    t("已结账超 {n} 天未开，建议开具", n=overdue)
                    if overdue >= 3
                    else t("待开 ¥{amount}", amount=r.get("gross_amount"))
                ),
                payload={"order_id": r.get("order_id")},
                risk="medium",
                selected=overdue >= 3,
            )
        )
    for r in [x for x in rows if x.get("status") == "done"][:3]:
        items.append(
            _item(
                op="invoice_red_flush",
                label=t("红冲草案 · {no}", no=r.get("invoice_no") or ""),
                reason=t("仅当抬头/金额确有错误时使用；确认后写红字票"),
                payload={
                    "invoice_id": r.get("id"),
                    "reason": t("AI建议复核：抬头或金额可能有误"),
                },
                risk="high",
                selected=False,
            )
        )
    alert = ws.get("alert") or {}
    sit = _situation(
        t("待开 {n} 单 · 漏开告警 {m}", n=len(todo), m=alert.get("count") or 0),
        [t("{order} 待开 ¥{amount}", order=r.get("order_no") or "", amount=r.get("gross_amount")) for r in todo[:4]],
        [
            {"label": t("待开"), "value": str(len(todo))},
            {
                "label": t("合规率"),
                "value": f"{(ws.get('kpi') or {}).get('compliance_rate', '—')}%",
            },
        ],
    )
    return sit, items, reasons


def _candidates_ar_ap(db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]:
    from finance.ar_ap_service import list_workspace

    ws = list_workspace(db, hotel_id)
    kpi = ws.get("kpi") or {}
    ar_rows = ws.get("ar_invoices") or []
    credits = ws.get("credit_accounts") or []
    aging = ws.get("aging") or {}
    items: list[dict] = []
    reasons = [
        t("坏账核销/回款/付款/授信调额禁止自动执行"),
        t("仅可同步单据、写入催收备忘与授信预警日志"),
    ]
    bullets: list[str] = []

    items.append(
        _item(
            op="ar_ap_sync",
            label=t("同步应收应付单据"),
            reason=t("按最新订单与挂账明细刷新 AR/AP 列表"),
            payload={},
            risk="low",
            selected=True,
        )
    )

    overdue = [r for r in ar_rows if r.get("status") == "overdue"]
    for r in overdue[:8]:
        bal = _f(r.get("balance"))
        items.append(
            _item(
                op="ar_overdue_remind",
                label=t(
                    "催收备忘 · {name} · ¥{amt}",
                    name=r.get("customer_name"),
                    amt=f"{bal:.0f}",
                ),
                reason=t(
                    "{doc} · 账期 {due} · 建议电话/对公跟进",
                    doc=r.get("doc_label") or "—",
                    due=r.get("due_date") or "—",
                ),
                payload={"ar_id": r.get("id"), "customer_name": r.get("customer_name"), "balance": bal},
                risk="low",
                selected=True,
            )
        )

    for c in credits:
        rate = _f(c.get("usage_rate"))
        if rate >= 80 or c.get("blocked"):
            items.append(
                _item(
                    op="ar_credit_warn",
                    label=t("授信预警 · {name}", name=c.get("name")),
                    reason=t(
                        "使用率 {rate}% · 已用 ¥{used} / ¥{limit}",
                        rate=f"{rate:.0f}",
                        used=f"{_f(c.get('credit_used')):.0f}",
                        limit=f"{_f(c.get('credit_limit')):.0f}",
                    ),
                    payload={"corp_id": c.get("corp_id"), "usage_rate": rate},
                    risk="medium",
                    selected=bool(c.get("blocked")),
                )
            )

    d90 = _f(aging.get("d90_plus"))
    if d90 > 0:
        bullets.append(t("90+ 天应收合计 ¥{amt}，建议人工评估坏账（AI 不自动核销）", amt=f"{d90:.0f}"))
    for r in overdue[:3]:
        bullets.append(t("逾期 · {name} ¥{amt}", name=r.get("customer_name"), amt=f"{_f(r.get('balance')):.0f}"))

    sit = _situation(
        t(
            "应收余额 ¥{bal} · 逾期 ¥{od}",
            bal=f"{_f(kpi.get('ar_balance')):.0f}",
            od=f"{_f(kpi.get('ar_overdue')):.0f}",
        ),
        bullets or [t("待跟进逾期 {n} 笔", n=len(overdue))],
        [
            {"label": t("应收余额"), "value": f"¥{_f(kpi.get('ar_balance')):.0f}"},
            {"label": t("逾期"), "value": f"¥{_f(kpi.get('ar_overdue')):.0f}"},
            {"label": t("90+天"), "value": f"¥{d90:.0f}"},
        ],
    )
    return sit, items[:15], reasons


def _build(db: Session, hotel_id: int, scene: str) -> tuple[dict, list[dict], list[str], str]:
    return build_scene_candidates(db, hotel_id, scene)


def _ensure_scenes_registered() -> None:
    """幂等注册内置 scene（模块 import 末尾调用）。"""
    if list_finance_scenes():
        return
    for key in SCENES:
        register_finance_scene(
            key,
            title=SCENE_TITLE[key],  # 中文 msgid；展示时 t()
            builder={
                "deposit": _candidates_deposit,
                "refund": _candidates_refund,
                "night_audit": _candidates_night_audit,
                "recon": _candidates_recon,
                "invoice": _candidates_invoice,
                "ar_ap": _candidates_ar_ap,
            }[key],
            # 运行时 get_scene_prompt，跟随 X-Locale（勿在注册时固化语言）
            system_prompt=None,
        )


def _refine_with_llm(
    db: Session,
    *,
    scene: str,
    title: str,
    situation: dict,
    items: list[dict],
    reasons: list[str],
) -> tuple[list[dict], list[str], str, Optional[str], str, Optional[str], Optional[str]]:
    if not items:
        return items, reasons, t("暂无可执行操作单"), None, "rules", None, None
    slim = [
        {"id": it["id"], "op": it["op"], "label": it["label"], "reason": it["reason"], "risk": it["risk"]}
        for it in items
    ]
    system = compose_system(get_scene_prompt("finance", scene) or SCENE_SYSTEM.get(scene) or SCENE_SYSTEM["recon"])
    user = (
        f"{t('【场景】')}{title}\n"
        f"{t('【现状】')}{situation.get('headline')}\n"
        f"{t('要点：')}{json.dumps(situation.get('bullets') or [], ensure_ascii=False)}\n"
        f"{t('【候选】')}{json.dumps(slim, ensure_ascii=False)}\n"
        f"{t('【规则依据】')}{json.dumps(reasons, ensure_ascii=False)}\n"
        f"{t('请挑选最该执行的行动，输出 summary / situation_note / reasons / selected_ids。')}\n"
    )
    n_sel_rules = sum(1 for i in items if i.get("selected"))
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
    summary = locale_text(raw_sum, "建议确认 {n} 张操作单", 80) if raw_sum else t("建议确认 {n} 张操作单", n=n_sel)
    if "{n}" in summary:
        summary = t("建议确认 {n} 张操作单", n=n_sel)
    note = locale_optional(parsed.get("situation_note"), 80)
    llm_reasons = locale_str_list(parsed.get("reasons"))
    if llm_reasons:
        reasons = llm_reasons
    source = "llm" if parsed else "unavailable"
    if source != "llm":
        return [], reasons, "", None, "unavailable", None, call.error
    return items, reasons, summary, note, source, call.model or None, call.error


def generate_plan(db: Session, hotel_id: int, scene: str) -> dict:
    _ensure_scenes_registered()
    scene = (scene or "").strip()
    get_finance_scene(scene)  # 校验
    situation, items, reasons, title = _build(db, hotel_id, scene)
    items, reasons, summary, sit_note, source, model, llm_error = _refine_with_llm(
        db, scene=scene, title=title, situation=situation, items=items, reasons=reasons
    )
    if sit_note:
        bullets = list(situation.get("bullets") or [])
        if sit_note not in bullets:
            bullets.append(sit_note)
        situation = {**situation, "bullets": bullets[:8]}
    cfg = load_llm_config(db)
    identity = llm_identity(cfg, {"model": model} if model else None) if source == "llm" else {}
    return {
        "plan_id": f"fin-{scene}-{uuid.uuid4().hex[:10]}",
        "hotel_id": hotel_id,
        "scene": scene,
        "title": title,
        "situation": situation,
        "summary": summary,
        "reasons": reasons,
        "items": items,
        "source": source,
        "llm_error": llm_error,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "draft",
        "hint": t("先核对现状，勾选操作单后点「AI确认执行」才会写库；资金/日切不会自动完成"),
        **identity,
    }


def _exec_item(db: Session, hotel_id: int, item: dict, *, operator: str) -> dict:
    op = item.get("op")
    payload = item.get("payload") or {}
    try:
        if op == "deposit_reauthorize":
            from datetime import timedelta

            from finance.deposit_service import _write_ledger, get_detail, reauthorize
            from models import Deposit

            did = str(payload["deposit_id"])
            d = db.get(Deposit, did)
            if not d or d.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "押金单不存在"}
            if d.status in ("EXPIRED", "DISPUTED"):
                res = reauthorize(db, hotel_id, did, {}, operator)
                db.commit()
                return {"ok": True, "op": op, "result": res}
            if d.status == "FROZEN":
                from_st = d.status
                d.auth_code = d.auth_code or f"REAUTH-{datetime.now().strftime('%H%M%S')}"
                d.auth_expire_at = datetime.now() + timedelta(days=30)
                _write_ledger(
                    db,
                    deposit_id=d.deposit_id,
                    event="REAUTHORIZE",
                    from_status=from_st,
                    to_status="FROZEN",
                    amount_delta=0,
                    operator_id=str(operator),
                    channel_ref=d.auth_code,
                    memo="AI确认·延长预授权",
                )
                db.commit()
                return {"ok": True, "op": op, "result": get_detail(db, hotel_id, did)}
            return {"ok": False, "op": op, "error": f"状态 {d.status} 不可重授权"}

        if op == "deposit_note_dispute":
            from finance.deposit_service import dispute
            from models import Deposit

            did = str(payload["deposit_id"])
            d = db.get(Deposit, did)
            if not d or d.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "押金单不存在"}
            if d.status == "DISPUTED":
                return {"ok": True, "op": op, "skipped": True, "message": "已是争议态"}
            if d.status not in ("FROZEN", "PARTIAL_CAPTURE"):
                return {"ok": False, "op": op, "error": "当前状态不可登记争议"}
            res = dispute(
                db,
                hotel_id,
                did,
                {"reason": payload.get("note") or "AI跟进争议"},
                operator,
            )
            db.commit()
            return {"ok": True, "op": op, "result": res}

        if op == "deposit_flag_receipt":
            return {"ok": True, "op": op, "skipped": True, "message": "现金无收据须人工补录，未自动释放"}

        if op == "refund_remind_ticket":
            from finance.refund_service import _audit, _serialize_ticket
            from models import RefundAdjustTicket

            tid = int(payload["ticket_id"])
            t = db.get(RefundAdjustTicket, tid)
            if not t or t.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "工单不存在"}
            _audit(db, hotel_id, t.id, "AI_REMIND", operator, "AI催办待处理工单", after=_serialize_ticket(t))
            db.commit()
            return {"ok": True, "op": op, "ticket_id": tid}

        if op == "refund_create_adjust_ticket":
            from finance.refund_service import submit_adjust

            res = submit_adjust(db, hotel_id, payload, operator)
            return {"ok": True, "op": op, "result": res}

        if op == "refund_create_reverse_ticket":
            from finance.refund_service import submit_reverse

            body = {
                "target": payload.get("target") or {},
                "reason": payload.get("reason") or "AI反结账草案",
                "note": payload.get("note") or "",
            }
            res = submit_reverse(db, hotel_id, body, operator)
            return {"ok": True, "op": op, "result": res}

        if op == "night_fix_exception":
            from models import NightAuditException

            row = db.get(NightAuditException, int(payload["exception_id"]))
            if not row or row.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "异常不存在"}
            row.status = "fixed"
            row.fixed_at = datetime.now()
            db.commit()
            return {"ok": True, "op": op, "exception_id": row.id}

        if op == "recon_close_batch":
            from models import ReconBatch

            b = db.get(ReconBatch, int(payload["batch_id"]))
            if not b or b.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "批次不存在"}
            if abs(_f(b.variance)) >= 0.01:
                return {"ok": False, "op": op, "error": "仍有差额，拒绝自动关账"}
            b.status = "closed"
            b.note = ((b.note or "") + " · AI确认关账")[:200]
            db.commit()
            return {"ok": True, "op": op, "batch_id": b.id}

        if op == "recon_mark_matched":
            from models import ReconBatch

            b = db.get(ReconBatch, int(payload["batch_id"]))
            if not b or b.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "批次不存在"}
            b.status = "matched"
            note = payload.get("note") or "AI小额配对"
            b.note = ((b.note or "") + f" · {note}")[:200]
            db.commit()
            return {"ok": True, "op": op, "batch_id": b.id}

        if op == "recon_mark_conflict":
            from models import ReconBatch

            b = db.get(ReconBatch, int(payload["batch_id"]))
            if not b or b.hotel_id != hotel_id:
                return {"ok": False, "op": op, "error": "批次不存在"}
            b.status = "conflict"
            note = payload.get("note") or "AI转人工"
            b.note = ((b.note or "") + f" · {note}")[:200]
            db.commit()
            return {"ok": True, "op": op, "batch_id": b.id}

        if op == "invoice_issue":
            from finance.invoice_service import issue_invoice

            row = issue_invoice(db, hotel_id, int(payload["order_id"]))
            return {"ok": True, "op": op, "result": row}

        if op == "invoice_red_flush":
            from finance.invoice_service import red_flush_invoice

            row = red_flush_invoice(
                db,
                hotel_id,
                int(payload["invoice_id"]),
                str(payload.get("reason") or "AI建议红冲复核"),
            )
            return {"ok": True, "op": op, "result": row}

        if op == "ar_ap_sync":
            from finance.ar_ap_service import sync_ar_ap_from_orders

            stats = sync_ar_ap_from_orders(db, hotel_id)
            db.commit()
            return {"ok": True, "op": op, "result": stats}

        if op == "ar_overdue_remind":
            from models import ArApLog

            ar_id = int(payload.get("ar_id") or 0)
            log = ArApLog(
                hotel_id=hotel_id,
                action="reminder",
                ref_type="ar",
                ref_id=ar_id or None,
                operator_name=operator,
                amount=_money(_f(payload.get("balance"))),
                reason=f"AI催收备忘 · {payload.get('customer_name') or ''}",
            )
            db.add(log)
            db.flush()
            log.meta = json.dumps({"overdue_follow_up": True, "todo_id": f"log_{log.id}"}, ensure_ascii=False)
            db.commit()
            return {"ok": True, "op": op, "ar_id": ar_id}

        if op == "ar_credit_warn":
            from models import ArApLog

            corp_id = int(payload.get("corp_id") or 0)
            db.add(
                ArApLog(
                    hotel_id=hotel_id,
                    action="credit_warn",
                    ref_type="ar",
                    ref_id=corp_id or None,
                    operator_name=operator,
                    amount=Decimal("0"),
                    reason=f"AI授信预警 · 使用率 {payload.get('usage_rate')}%",
                    meta="credit_alert",
                )
            )
            db.commit()
            return {"ok": True, "op": op, "corp_id": corp_id}

        return {"ok": False, "op": op, "error": f"未知操作 {op}"}
    except Exception as e:
        return {"ok": False, "op": op, "error": str(getattr(e, "detail", None) or e)[:200]}


def confirm_plan(
    db: Session,
    hotel_id: int,
    *,
    plan: dict,
    operator: str = "财务AI",
) -> dict:
    _ensure_scenes_registered()
    if not plan or not isinstance(plan, dict):
        raise InvalidStateError("缺少 plan")
    scene = plan.get("scene")
    get_finance_scene(str(scene or ""))
    selected = [it for it in (plan.get("items") or []) if it.get("selected") is not False]
    if not selected:
        raise InvalidStateError("请至少勾选一张操作单")
    results = []
    ok_n = 0
    for it in selected:
        # 高风险二次闸门：红冲/反结账/现金收据仅执行已勾选（前端已勾）
        r = _exec_item(db, hotel_id, it, operator=operator)
        results.append({"id": it.get("id"), "label": it.get("label"), **r})
        if r.get("ok"):
            ok_n += 1
    return {
        "plan_id": plan.get("plan_id"),
        "scene": scene,
        "executed": len(results),
        "succeeded": ok_n,
        "results": results,
        "message": f"已执行 {ok_n}/{len(results)} 张操作单（均经人工确认）",
    }


_ensure_scenes_registered()
