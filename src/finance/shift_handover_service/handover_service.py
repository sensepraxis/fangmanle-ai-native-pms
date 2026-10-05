# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: handover_service。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

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

# 同包 cross-import（拆分后必须显式 import）
# 注意：使用 from-import 会把符号绑到本模块局部名，导致 unittest.mock.patch
# "finance.shift_handover_service._xxx" 失效。所以**全部通过子模块名调用**，
# 走 `xxx_sub_module._xxx()` 形式，确保 patch 命中子模块的属性。
from finance.shift_handover_service import _common as _c
from finance.shift_handover_service import asset_service as _as
from finance.shift_handover_service import float_service as _fl
from finance.shift_handover_service import revenue_service as _rv
from finance.shift_handover_service import shift_window_service as _sw
from finance.shift_handover_service import task_service as _tk
from finance.shift_handover_service.task_service import (
    _build_tasks,
    _carryover_tasks,
    _guest_situations,
)
from infra.i18n import t
from models import (
    Channel,
    Deposit,
    DepositLedgerEntry,
    FinanceReport,
    Guest,
    GuestTag,
    Order,
    Payment,
    Reservation,
    Room,
    ServiceRequest,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    Supply,
    TagDefinition,
    User,
)


def get_or_create_handover(db: Session, hotel_id: int, user_id: int | None = None) -> ShiftHandover:
    shift_no, start, end, scheduled, _ = _sw._current_shift()
    row = (
        db.query(ShiftHandover)
        .filter(
            ShiftHandover.hotel_id == hotel_id,
            ShiftHandover.shift_date == start.date(),
            ShiftHandover.shift_no == shift_no,
            ShiftHandover.status.in_(("in_progress", "pending_acknowledgment", "signed", "manager_review")),
        )
        .order_by(ShiftHandover.id.desc())
        .first()
    )
    if row:
        return row
    expected = _fl._float_expected(db, hotel_id)
    row = ShiftHandover(
        hotel_id=hotel_id,
        shift_no=shift_no,
        shift_date=start.date(),
        start_at=start,
        end_at=end,
        scheduled_handover_at=scheduled,
        outgoing_user_id=user_id,
        status="in_progress",
        float_expected=_c._money(expected),
    )
    db.add(row)
    db.flush()
    for item in _fl._float_breakdown_expected(expected, db, hotel_id):
        db.add(
            ShiftFloatCount(
                handover_id=row.id,
                denom=_c._money(item["denom"]),
                label=item["label"],
                expected_qty=item["expected_qty"],
                actual_qty=0,
            )
        )
    for item in _as._build_asset_inventory(db, hotel_id):
        db.add(
            ShiftAssetCount(
                handover_id=row.id,
                asset_type=item["asset_type"],
                asset_name=item["asset_name"],
                hint=item.get("hint"),
                expected_qty=item["expected_qty"],
                actual_qty=None,
                supply_id=item.get("supply_id"),
                reorder_triggered=item.get("reorder_triggered", False),
            )
        )
    db.commit()
    db.refresh(row)
    return row


def build_workspace(db: Session, hotel_id: int, user_id: int | None = None) -> dict[str, Any]:
    handover = get_or_create_handover(db, hotel_id, user_id)
    if not handover.float_confirmed:
        latest_expected = _fl._float_expected(db, hotel_id)
        if float(handover.float_expected or 0) != latest_expected:
            handover.float_expected = _c._money(latest_expected)
    _as._purge_legacy_assets(db, handover)
    _as._normalize_unconfirmed_assets(db, handover)
    _fl._sync_float_breakdown(db, handover)
    _as._sync_assets_from_inventory(db, handover)
    db.flush()
    shift_no, start, end, scheduled, shift_label = _sw._current_shift()
    now = datetime.now()
    elapsed = now - (handover.start_at or start)
    remain = (handover.scheduled_handover_at or scheduled) - now
    elapsed_str = f"{int(elapsed.total_seconds() // 3600)}:{int(elapsed.total_seconds() % 3600 // 60):02d}"
    remain_str = f"{max(0, int(remain.total_seconds() // 3600))}:{max(0, int(remain.total_seconds() % 3600 // 60)):02d}"
    win_start, win_end = _sw._shift_window(handover, now)
    duration = win_end - win_start
    y_start = win_start - timedelta(days=1)
    y_end = y_start + duration
    channels = _rv._channel_revenue(db, hotel_id, win_start, win_end)
    channels = _rv._merge_yesterday(channels, _rv._channel_revenue(db, hotel_id, y_start, y_end))
    total_rev = round(sum(c["amount"] for c in channels), 2)
    y_total = round(sum(c.get("yesterday_amount", 0) for c in channels), 2)
    target = _rv._revenue_target(db, hotel_id, handover.shift_date or start.date())
    target_pct = round(100 * total_rev / target, 1) if target else None
    dep = _rv._deposit_handover(db, hotel_id, win_start, win_end)
    handover.total_revenue = _c._money(total_rev)
    handover.deposit_collected = _c._money(dep["collected"])
    handover.deposit_refunded = _c._money(dep["refunded"])
    handover.deposit_net = _c._money(dep["net"])
    handover.deposit_collected_count = dep["collected_count"]
    handover.deposit_refunded_count = dep["refunded_count"]
    outgoing = db.get(User, handover.outgoing_user_id) if handover.outgoing_user_id else None
    incoming = db.get(User, handover.incoming_user_id) if handover.incoming_user_id else None
    float_rows = (
        db.query(ShiftFloatCount).filter_by(handover_id=handover.id).order_by(ShiftFloatCount.denom.desc()).all()
    )
    float_rows = [r for r in float_rows if float(r.denom or 0) >= 1]
    asset_rows = db.query(ShiftAssetCount).filter_by(handover_id=handover.id).all()
    from finance.shift_handover_service._common import (
        ai_status_for_handover,
        guest_situations_for_display,
        tasks_for_display,
    )

    situations = guest_situations_for_display(db, hotel_id, handover)
    tasks = tasks_for_display(db, hotel_id, handover)
    ai_block = ai_status_for_handover(handover)
    carryover = _tk._carryover_tasks(db, hotel_id, handover.id)
    history = _fl._float_history(db, hotel_id)
    p0 = sum(1 for t in tasks if t["priority"] == "P0" and t["status"] != "done")
    alerts = []
    float_expected_val = float(handover.float_expected or 0)
    from finance.finance_float_service import get_active_float_carry_amount

    float_carry_source = (
        "finance_params"
        if get_active_float_carry_amount(db, hotel_id) > 0
        else "finance_report"
        if float_expected_val > 0
        else "none"
    )
    if float_expected_val <= 0:
        alerts.append(
            {"level": "warn", "text": t("未配置备用金底数，请在「系统设置 → 财务参数 → 门店备用金」中维护。")}
        )
    if not incoming:
        alerts.append({"level": "warn", "text": t("接班人未指定，需在计划交班时间前到岗并完成 3 项必读确认。")})
    if p0:
        alerts.append({"level": "warn", "text": t("本班还有 {n} 条 P0 待办需在交班前关闭或转交。", n=p0)})
    low_supply = [a for a in asset_rows if a.reorder_triggered and a.actual_qty is not None]
    if low_supply:
        alerts.append(
            {
                "level": "crit",
                "text": t(
                    "{name} 触发自动补货申请（实盘 {qty}，低于阈值）。",
                    name=low_supply[0].asset_name,
                    qty=low_supply[0].actual_qty,
                ),
            }
        )
    denom_sum = round(sum(float(r.denom) * int(r.actual_qty or 0) for r in float_rows), 2)
    if handover.float_actual is not None:
        float_actual = float(handover.float_actual)
    else:
        float_actual = denom_sum
    float_expected = float_expected_val
    float_diff = round(float_actual - float_expected, 2)
    if abs(float_diff) < 0.01:
        diff_type = "flat"
    elif float_diff > 0:
        diff_type = "long"
    else:
        diff_type = "short"
    if handover.float_confirmed:
        handover.float_diff = _c._money(float_diff)
        handover.diff_type = handover.diff_type or diff_type
    manager_required = (
        abs(float_diff) >= 5
        or p0 > 0
        or any(
            a
            for a in asset_rows
            if a.actual_qty is not None
            and (a.actual_qty or 0) != (a.expected_qty or 0)
            and (not (a.diff_reason or "").strip())
        )
    )
    handover.manager_required = manager_required
    db.commit()
    return {
        "handover_id": handover.id,
        "status": handover.status,
        "banner": {
            "shift_no": shift_no,
            "shift_label": shift_label,
            "shift_time": f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}",
            "elapsed": elapsed_str,
            "remain": remain_str,
            "scheduled_handover": (handover.scheduled_handover_at or scheduled).strftime("%H:%M"),
            "total_revenue": total_rev,
            "payment_count": sum(c["count"] for c in channels),
            "channel_count": len(channels),
            "outgoing_name": outgoing.full_name or outgoing.username if outgoing else None,
            "outgoing_meta": (t("工号 {id}", id=outgoing.id) if outgoing else t("未指定交班人")),
            "incoming_name": incoming.full_name or incoming.username if incoming else None,
            "incoming_meta": (t("工号 {id}", id=incoming.id) if incoming else t("本班次尚未指定接班人")),
        },
        "alerts": alerts,
        "revenue": {
            "total": total_rev,
            "yesterday_total": y_total,
            "target": target,
            "target_pct": target_pct,
            "channels": channels,
        },
        "float": {
            "expected": float_expected,
            "actual": float_actual,
            "diff": float_diff,
            "diff_type": diff_type,
            "diff_type_label": present_diff_type_label(diff_type),
            "diff_reason": handover.diff_reason or "",
            "confirmed": handover.float_confirmed,
            "carry_source": float_carry_source,
            "denominations": [
                {
                    "denom": float(r.denom),
                    "label": r.label,
                    "expected_qty": r.expected_qty,
                    "actual_qty": r.actual_qty,
                    "subtotal": round(float(r.denom) * int(r.actual_qty or 0), 2),
                }
                for r in float_rows
            ],
        },
        "deposit": dep,
        "assets": [
            {
                "id": a.id,
                "asset_type": a.asset_type,
                "name": a.asset_name,
                "hint": a.hint,
                "expected_qty": a.expected_qty,
                "actual_qty": a.actual_qty,
                "diff": a.actual_qty - a.expected_qty if a.actual_qty is not None else None,
                "diff_reason": a.diff_reason or "",
                "reorder_triggered": a.reorder_triggered,
            }
            for a in asset_rows
        ],
        "guest_situations": situations,
        "tasks": tasks,
        "carryover": carryover,
        "ai": ai_block,
        "signatures": {
            "outgoing_signed": bool(handover.outgoing_signed_at),
            "outgoing_signed_at": handover.outgoing_signed_at.isoformat(timespec="minutes")
            if handover.outgoing_signed_at
            else None,
            "outgoing_name": outgoing.full_name or outgoing.username if outgoing else None,
            "incoming_signed": bool(handover.incoming_signed_at),
            "incoming_signed_at": handover.incoming_signed_at.isoformat(timespec="minutes")
            if handover.incoming_signed_at
            else None,
            "incoming_name": incoming.full_name or incoming.username if incoming else None,
            "manager_signed": bool(handover.manager_signed_at),
            "manager_required": manager_required,
            "incoming_ack_money": handover.incoming_ack_money,
            "incoming_ack_assets": handover.incoming_ack_assets,
            "incoming_ack_tasks": handover.incoming_ack_tasks,
        },
        "float_history": history,
        "footnote": "",
    }


def sign_handover(
    db: Session,
    hotel_id: int,
    handover_id: int,
    role: str,
    user_id: int,
    incoming_user_id: int | None = None,
    ack: dict | None = None,
    operator_name: str = "",
) -> dict:
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    now = datetime.now()
    user = db.get(User, user_id)
    name = operator_name or (user.full_name if user else "") or (user.username if user else "")
    if role == "outgoing":
        if not row.float_confirmed:
            raise InvalidStateError("请先完成备用金盘库确认")
        if not row.assets_confirmed:
            raise InvalidStateError("请先完成实物盘库")
        row.outgoing_signed_at = now
        row.outgoing_user_id = user_id
        row.status = "pending_acknowledgment"
    elif role == "incoming":
        ack = ack or {}
        if not all(ack.get(k) for k in ("money", "assets", "tasks")):
            raise InvalidStateError("接班人必须完成钱/物/事 3 项必读确认")
        inc_id = incoming_user_id or user_id
        inc = db.get(User, inc_id)
        if not inc:
            raise InvalidStateError("接班人工号无效")
        row.incoming_user_id = inc_id
        row.incoming_signed_at = now
        row.incoming_ack_money = True
        row.incoming_ack_assets = True
        row.incoming_ack_tasks = True
        if row.manager_required and (not row.manager_signed_at):
            row.status = "manager_review"
        else:
            row.status = "signed"
    elif role == "manager":
        row.manager_user_id = user_id
        row.manager_signed_at = now
        row.status = "signed"
    else:
        raise InvalidStateError("无效签字角色")
    _c._log(db, handover_id, hotel_id, f"sign_{role}", user_id, name, ack or {})
    db.commit()
    return {"status": row.status}


def complete_handover(
    db: Session, hotel_id: int, handover_id: int, operator_id: int | None = None, operator_name: str = ""
) -> dict:
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    if not row.outgoing_signed_at or not row.incoming_signed_at:
        raise InvalidStateError("交班人与接班人均须签字后才能完成交班")
    if row.manager_required and (not row.manager_signed_at):
        raise InvalidStateError("存在差异或 P0 事件，须店长审核签字")
    if not row.float_confirmed or not row.assets_confirmed:
        raise InvalidStateError("钱/物盘库未完成")
    row.status = "archived"
    row.completed_at = datetime.now()
    row.archived_at = datetime.now()
    _c._log(db, handover_id, hotel_id, "complete", operator_id, operator_name, {})
    db.commit()
    from events import emit

    emit(
        "shift.handover_completed",
        {
            "hotel_id": hotel_id,
            "handover_id": handover_id,
            "operator_id": operator_id,
        },
    )
    return {"status": "archived", "archived_at": row.archived_at.isoformat()}
