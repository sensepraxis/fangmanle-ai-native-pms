# SPDX-License-Identifier: Apache-2.0
"""班次接班（接收确认）：与交班共用 shift_handover 记录。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from finance.doc_identity import present_diff_type_label
from finance.shift_handover_service import (
    _build_tasks,
    _carryover_tasks,
    _channel_revenue,
    _float_expected,
    _guest_situations,
    _log,
    _merge_yesterday,
    _money,
    _shift_window,
    complete_handover,
    sign_handover,
)
from infra.i18n import t
from models import ShiftAssetCount, ShiftFloatCount, ShiftHandover, ShiftReceiveDiff, User


def _jload(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _jsave(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def _localize_asset_hint(hint: str | None) -> str:
    import re

    s = str(hint or "").strip()
    if not s:
        return s
    m = re.match(r"库存单位\s+(.+?)\s*·\s*安全库存\s+(\d+)", s)
    if m:
        return t("库存单位 {unit} · 安全库存 {safe}", unit=t(m.group(1)), safe=m.group(2))
    return t(s)


def _find_takeover_handover(db: Session, hotel_id: int) -> ShiftHandover | None:
    return (
        db.query(ShiftHandover)
        .filter(
            ShiftHandover.hotel_id == hotel_id,
            ShiftHandover.outgoing_signed_at.isnot(None),
            ShiftHandover.status.in_(("pending_acknowledgment", "manager_review", "signed")),
        )
        .order_by(ShiftHandover.id.desc())
        .first()
    )


def _user_display(user: User | None) -> str | None:
    if not user:
        return None
    return user.full_name or user.username or None


def build_takeover_workspace(db: Session, hotel_id: int, user_id: int | None = None) -> dict[str, Any]:
    handover = _find_takeover_handover(db, hotel_id)
    if not handover:
        return {
            "ready": False,
            "message": t("暂无待接班确认的交班单。请等待交班人完成盘库并签字提交。"),
            "handover_id": None,
        }
    if not handover.float_confirmed or not handover.assets_confirmed:
        return {
            "ready": False,
            "message": t("交班人尚未完成钱/物盘库确认，暂不可接班。"),
            "handover_id": handover.id,
        }

    now = datetime.now()
    win_start, win_end = _shift_window(handover, now)
    duration = win_end - win_start
    y_start = win_start - timedelta(days=1)
    y_end = y_start + duration
    channels = _channel_revenue(db, hotel_id, win_start, win_end)
    channels = _merge_yesterday(channels, _channel_revenue(db, hotel_id, y_start, y_end))
    total_rev = round(float(handover.total_revenue or 0) or sum(c["amount"] for c in channels), 2)
    y_total = round(sum(c.get("yesterday_amount", 0) for c in channels), 2)

    outgoing = db.get(User, handover.outgoing_user_id) if handover.outgoing_user_id else None
    incoming = db.get(User, handover.incoming_user_id) if handover.incoming_user_id else None
    current_user = db.get(User, user_id) if user_id else None

    float_rows = [
        r
        for r in db.query(ShiftFloatCount)
        .filter_by(handover_id=handover.id)
        .order_by(ShiftFloatCount.denom.desc())
        .all()
        if float(r.denom or 0) >= 1
    ]
    asset_rows = db.query(ShiftAssetCount).filter_by(handover_id=handover.id).all()

    outgoing_float_total = (
        float(handover.float_actual)
        if handover.float_actual is not None
        else round(sum(float(r.denom) * int(r.actual_qty or 0) for r in float_rows), 2)
    )
    denom_items = []
    denom_recv_sum = 0.0
    for r in float_rows:
        declared = int(r.actual_qty or 0)
        recv = r.received_qty if r.received_qty is not None else None
        if recv is not None:
            denom_recv_sum += float(r.denom) * int(recv)
        denom_items.append(
            {
                "denom": float(r.denom),
                "label": r.label,
                "outgoing_qty": declared,
                "received_qty": recv if recv is not None else "",
                "subtotal": round(float(r.denom) * int(recv or 0), 2) if recv is not None else 0,
            }
        )
    if handover.received_float_actual is not None:
        received_total = float(handover.received_float_actual)
    else:
        received_total = (
            round(denom_recv_sum, 2) if any(r.received_qty is not None for r in float_rows) else outgoing_float_total
        )
    float_match = abs(received_total - outgoing_float_total) < 0.01

    assets = []
    for a in asset_rows:
        out_qty = a.actual_qty
        recv = a.received_qty if a.received_qty is not None else out_qty
        diff_vs_out = None
        if recv is not None and out_qty is not None:
            diff_vs_out = int(recv) - int(out_qty)
        assets.append(
            {
                "id": a.id,
                "name": t(a.asset_name or ""),
                "hint": _localize_asset_hint(a.hint),
                "expected_qty": a.expected_qty,
                "outgoing_qty": out_qty,
                "received_qty": recv,
                "diff_vs_outgoing": diff_vs_out,
                "received_ack": bool(a.received_ack),
                "outgoing_diff_reason": a.diff_reason or "",
            }
        )

    from finance.shift_handover_service._common import (
        ai_status_for_handover,
        guest_situations_for_display,
        tasks_for_display,
    )

    situations = guest_situations_for_display(db, hotel_id, handover)
    ai_block = ai_status_for_handover(handover)
    guest_acks = set(_jload(handover.guest_situation_acks, []))
    guest_items = []
    for s in situations:
        key = s.get("key") or str(len(guest_items))
        guest_items.append({**s, "key": key, "acked": key in guest_acks})

    tasks = tasks_for_display(db, hotel_id, handover)
    task_claims = _jload(handover.task_claims, {})
    task_items = []
    for i, task in enumerate(tasks):
        claim = task_claims.get(str(i), "")
        task_items.append({**task, "index": i, "claim_status": claim})

    carryover = _carryover_tasks(db, hotel_id, handover.id)
    carry_acks = set(str(x) for x in _jload(handover.carryover_acks, []))
    carry_items = []
    for c in carryover:
        cid = str(c.get("id", ""))
        carry_items.append({**c, "acked": cid in carry_acks})

    receive_diffs = (
        db.query(ShiftReceiveDiff)
        .filter_by(handover_id=handover.id)
        .order_by(ShiftReceiveDiff.id.desc())
        .limit(10)
        .all()
    )

    sig = handover
    loop = [
        {
            "key": "outgoing",
            "label": t("交班人已签"),
            "sub": _fmt_user_time(outgoing, sig.outgoing_signed_at),
            "state": "done",
        },
        {
            "key": "incoming",
            "label": t("接班人签字接收"),
            "sub": t("（你 · 待完成）")
            if not sig.incoming_signed_at
            else _fmt_user_time(incoming or current_user, sig.incoming_signed_at),
            "state": "done" if sig.incoming_signed_at else "cur",
        },
        {
            "key": "manager",
            "label": t("店长审核"),
            "sub": t("（有阻断时）") if not sig.manager_signed_at else t("已审核"),
            "state": "done"
            if sig.manager_signed_at
            else ("cur" if sig.manager_required and sig.incoming_signed_at else "future"),
        },
        {
            "key": "archive",
            "label": t("归档"),
            "sub": t("保存 3 年"),
            "state": "done" if sig.status == "archived" else "future",
        },
    ]

    guest_total = len(guest_items)
    guest_acked = sum(1 for g in guest_items if g["acked"])
    task_claimed = sum(1 for t in task_items if t.get("claim_status") in ("claimed", "escalated"))
    carry_acked = sum(1 for c in carry_items if c.get("acked"))

    can_sign = (
        bool(handover.received_revenue_ok)
        and bool(handover.deposit_ack)
        and bool(handover.float_received_confirmed)
        and bool(handover.assets_received_confirmed)
        and bool(handover.matters_confirmed)
        and not handover.incoming_signed_at
    )
    can_complete = (
        bool(handover.incoming_signed_at)
        and bool(handover.outgoing_signed_at)
        and (not handover.manager_required or bool(handover.manager_signed_at))
        and handover.status != "archived"
    )

    return {
        "ready": True,
        "handover_id": handover.id,
        "status": handover.status,
        "message": None,
        "banner": {
            "shift_label": t("{n} 班", n=handover.shift_no),
            "outgoing_name": (outgoing.full_name or outgoing.username) if outgoing else "—",
            "outgoing_signed_at": handover.outgoing_signed_at.isoformat(timespec="minutes")
            if handover.outgoing_signed_at
            else None,
            "incoming_name": _user_display(incoming) or _user_display(current_user),
            "incoming_user_id": handover.incoming_user_id or user_id,
            "total_revenue": total_rev,
            "payment_count": sum(c["count"] for c in channels),
            "channel_count": len(channels),
            "state_tag": t("接收确认中") if not handover.incoming_signed_at else t("已签字接收"),
        },
        "loop": loop,
        "revenue": {
            "total": total_rev,
            "yesterday_total": y_total,
            "channels": channels,
            "acknowledged": bool(handover.received_revenue_ok),
        },
        "float": {
            "expected": float(handover.float_expected or _float_expected(db, hotel_id)),
            "outgoing_actual": outgoing_float_total,
            "outgoing_diff": float(handover.float_diff or 0),
            "outgoing_diff_type": handover.diff_type,
            "outgoing_diff_type_label": present_diff_type_label(handover.diff_type),
            "outgoing_diff_reason": handover.diff_reason or "",
            "received_actual": received_total,
            "match_outgoing": float_match,
            "confirmed": bool(handover.float_received_confirmed),
            "denominations": denom_items,
        },
        "deposit": {
            "collected": float(handover.deposit_collected or 0),
            "collected_count": handover.deposit_collected_count or 0,
            "refunded": float(handover.deposit_refunded or 0),
            "refunded_count": handover.deposit_refunded_count or 0,
            "net": float(handover.deposit_net or 0),
            "acknowledged": bool(handover.deposit_ack),
        },
        "assets": assets,
        "guest_situations": guest_items,
        "guest_progress": {"done": guest_acked, "total": guest_total},
        "tasks": task_items,
        "task_progress": {"done": task_claimed, "total": len(task_items)},
        "carryover": carry_items,
        "carryover_progress": {"done": carry_acked, "total": len(carry_items)},
        "receive_diffs": [
            {
                "id": d.id,
                "item_type": d.item_type,
                "item_key": d.item_key,
                "declared_val": float(d.declared_val or 0),
                "received_val": float(d.received_val or 0),
                "diff_val": float(d.diff_val or 0),
                "reason": d.reason,
                "suggestion": getattr(d, "suggestion", None),
                "status": d.status,
                "created_at": d.created_at.isoformat(timespec="minutes") if d.created_at else None,
            }
            for d in receive_diffs
        ],
        "ai": ai_block,
        "signatures": {
            "outgoing_signed": bool(handover.outgoing_signed_at),
            "incoming_signed": bool(handover.incoming_signed_at),
            "manager_signed": bool(handover.manager_signed_at),
            "manager_required": bool(handover.manager_required),
        },
        "flags": {
            "can_sign": can_sign,
            "can_complete": can_complete,
            "matters_confirmed": bool(handover.matters_confirmed),
            "float_received_confirmed": bool(handover.float_received_confirmed),
            "assets_received_confirmed": bool(handover.assets_received_confirmed),
        },
        "footnote": "",
    }


def _fmt_user_time(user: User | None, dt: datetime | None) -> str:
    if not dt:
        return "—"
    name = (user.full_name or user.username) if user else "—"
    return f"{name} {dt.strftime('%H:%M')}"


def _get_takeover_row(db: Session, hotel_id: int, handover_id: int) -> ShiftHandover:
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    if not row.outgoing_signed_at:
        raise InvalidStateError("交班人尚未签字，无法接班")
    return row


def ack_takeover_revenue(
    db: Session, hotel_id: int, handover_id: int, *, ok: bool, operator_id: int | None = None
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    if not ok:
        raise InvalidStateError("须确认营收与交班单一致")
    row.received_revenue_ok = True
    _log(db, handover_id, hotel_id, "takeover_revenue_ack", operator_id, "", {})
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def ack_takeover_deposit(
    db: Session, hotel_id: int, handover_id: int, *, ok: bool, operator_id: int | None = None
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    if not ok:
        raise InvalidStateError("须确认承接押金转交压力")
    row.deposit_ack = True
    _log(db, handover_id, hotel_id, "takeover_deposit_ack", operator_id, "", {"net": float(row.deposit_net or 0)})
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def save_takeover_float_recount(
    db: Session,
    hotel_id: int,
    handover_id: int,
    denominations: list[dict] | None = None,
    *,
    confirm: bool = False,
    operator_id: int | None = None,
    received_actual: float | None = None,
) -> dict:
    """接班人备用金重盘：以「你重盘总额」为主，与交班人实点比对；面额明细选填。"""
    row = _get_takeover_row(db, hotel_id, handover_id)
    denominations = denominations or []
    float_rows = [
        r for r in db.query(ShiftFloatCount).filter_by(handover_id=handover_id).all() if float(r.denom or 0) >= 1
    ]
    for r in db.query(ShiftFloatCount).filter_by(handover_id=handover_id).all():
        if float(r.denom or 0) < 1:
            db.delete(r)

    outgoing_total = (
        float(row.float_actual)
        if row.float_actual is not None
        else round(sum(float(r.denom) * int(r.actual_qty or 0) for r in float_rows), 2)
    )

    detail_sum = None
    if denominations:
        by_denom = {float(d["denom"]): d for d in denominations if float(d.get("denom") or 0) >= 1}
        detail_sum = 0.0
        for r in float_rows:
            d = by_denom.get(float(r.denom))
            declared = int(r.actual_qty or 0)
            if d is not None:
                r.received_qty = int(d.get("received_qty") or 0)
            elif r.received_qty is None:
                r.received_qty = declared
            detail_sum += float(r.denom) * int(r.received_qty or 0)
        detail_sum = round(detail_sum, 2)

    if received_actual is None:
        if detail_sum is None:
            raise InvalidStateError("请填写你重盘总额")
        received_total = detail_sum
    else:
        received_total = round(float(received_actual), 2)
        if detail_sum is not None and abs(detail_sum - received_total) >= 0.01:
            raise InvalidStateError(f"明细合计 ¥{detail_sum:.2f} 与重盘总额 ¥{received_total:.2f} 不一致")

    row.received_float_actual = _money(received_total)
    row.received_float_match_outgoing = abs(received_total - outgoing_total) < 0.01
    if confirm:
        row.float_received_confirmed = True
    _log(
        db,
        handover_id,
        hotel_id,
        "takeover_float_recount",
        operator_id,
        "",
        {"outgoing": outgoing_total, "received": received_total, "match": row.received_float_match_outgoing},
    )
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def save_takeover_asset_recount(
    db: Session,
    hotel_id: int,
    handover_id: int,
    assets: list[dict],
    *,
    confirm: bool = False,
    operator_id: int | None = None,
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    by_id = {int(a["id"]): a for a in assets if a.get("id")}
    rows = db.query(ShiftAssetCount).filter_by(handover_id=handover_id).all()
    for r in rows:
        payload = by_id.get(r.id)
        if not payload:
            continue
        if payload.get("received_qty") is None:
            raise InvalidStateError(f"{r.asset_name} 须录入复点数量")
        r.received_qty = int(payload.get("received_qty"))
        r.received_ack = bool(payload.get("received_ack"))
        if r.received_qty != r.actual_qty and not r.received_ack:
            raise InvalidStateError(f"{r.asset_name} 与交班人实盘不符，须勾选「差异已知晓」")
    if confirm:
        for r in rows:
            if r.received_qty is None:
                raise InvalidStateError(f"{r.asset_name} 须完成复点")
            if r.received_qty != r.actual_qty and not r.received_ack:
                raise InvalidStateError(f"{r.asset_name} 差异须确认已知晓")
        row.assets_received_confirmed = True
    _log(db, handover_id, hotel_id, "takeover_asset_recount", operator_id, "", {"confirm": confirm})
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def ack_takeover_guest(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    keys: list[str],
    acked: bool = True,
    operator_id: int | None = None,
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    merged = set(_jload(row.guest_situation_acks, []))
    key_set = {str(k) for k in keys}
    if acked:
        merged.update(key_set)
    else:
        merged -= key_set
    row.guest_situation_acks = _jsave(sorted(merged))
    _log(
        db,
        handover_id,
        hotel_id,
        "takeover_guest_ack",
        operator_id,
        "",
        {"keys": list(merged), "acked": acked, "changed": list(key_set)},
    )
    db.commit()
    return {"ok": True, "acked_keys": sorted(merged)}


def claim_takeover_task(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    task_index: int,
    action: str,
    operator_id: int | None = None,
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    claims = _jload(row.task_claims, {})
    if action not in ("claimed", "escalated"):
        raise InvalidStateError("无效操作")
    claims[str(task_index)] = action
    row.task_claims = _jsave(claims)
    _log(db, handover_id, hotel_id, "takeover_task_claim", operator_id, "", {"index": task_index, "action": action})
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def ack_takeover_carryover(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    carryover_ids: list[int],
    acked: bool = True,
    operator_id: int | None = None,
) -> dict:
    row = _get_takeover_row(db, hotel_id, handover_id)
    merged = set(str(x) for x in _jload(row.carryover_acks, []))
    id_set = {str(i) for i in carryover_ids}
    if acked:
        merged.update(id_set)
    else:
        merged -= id_set
    row.carryover_acks = _jsave(sorted(merged, key=lambda x: int(x) if x.isdigit() else 0))
    _log(
        db,
        handover_id,
        hotel_id,
        "takeover_carryover_ack",
        operator_id,
        "",
        {"ids": list(merged), "acked": acked},
    )
    db.commit()
    return {"ok": True, "acked_ids": sorted(merged)}


def confirm_takeover_matters(db: Session, hotel_id: int, handover_id: int, *, operator_id: int | None = None) -> dict:
    ws = build_takeover_workspace(db, hotel_id, operator_id)
    if not ws.get("ready"):
        raise InvalidStateError(ws.get("message") or "不可确认")
    gp = ws["guest_progress"]
    tp = ws["task_progress"]
    cp = ws["carryover_progress"]
    if gp["total"] and gp["done"] < gp["total"]:
        raise InvalidStateError("客情卡须逐条「已知晓」")
    if tp["total"] and tp["done"] < tp["total"]:
        raise InvalidStateError("待办须全部承接或升级")
    if cp["total"] and cp["done"] < cp["total"]:
        raise InvalidStateError("上轮遗留须全部「已了解」")
    row = _get_takeover_row(db, hotel_id, handover_id)
    row.matters_confirmed = True
    _log(db, handover_id, hotel_id, "takeover_matters_confirmed", operator_id, "", {})
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def report_receive_diff(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    item_type: str,
    item_key: str,
    declared_val: float,
    received_val: float,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("差异原因不少于 4 字")
    row = _get_takeover_row(db, hotel_id, handover_id)
    diff = round(received_val - declared_val, 2)
    db.add(
        ShiftReceiveDiff(
            handover_id=handover_id,
            hotel_id=hotel_id,
            item_type=item_type,
            item_key=item_key,
            declared_val=_money(declared_val),
            received_val=_money(received_val),
            diff_val=_money(diff),
            reason=reason,
            reporter_user_id=operator_id,
            status="pending_manager",
        )
    )
    row.manager_required = True
    _log(
        db,
        handover_id,
        hotel_id,
        "takeover_diff_report",
        operator_id,
        "",
        {"type": item_type, "key": item_key, "diff": diff, "reason": reason},
    )
    db.commit()
    return build_takeover_workspace(db, hotel_id, operator_id)


def sign_takeover_receive(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    incoming_user_id: int | None,
    operator_id: int,
    operator_name: str = "",
) -> dict:
    ws = build_takeover_workspace(db, hotel_id, operator_id)
    if not ws.get("flags", {}).get("can_sign"):
        raise InvalidStateError("请先完成钱/物/事复核与 3 项必读确认")
    sign_handover(
        db,
        hotel_id,
        handover_id,
        "incoming",
        operator_id,
        incoming_user_id=incoming_user_id or operator_id,
        ack={"money": True, "assets": True, "tasks": True},
        operator_name=operator_name,
    )
    return build_takeover_workspace(db, hotel_id, operator_id)


def complete_takeover_receive(
    db: Session,
    hotel_id: int,
    handover_id: int,
    *,
    operator_id: int | None = None,
    operator_name: str = "",
) -> dict:
    complete_handover(db, hotel_id, handover_id, operator_id, operator_name)
    ws = build_takeover_workspace(db, hotel_id, operator_id)
    if ws.get("ready"):
        ws["completed"] = True
        ws["message"] = "交接完成 · 本班责任已转移 · 归档保存 3 年"
    return ws
