# SPDX-License-Identifier: Apache-2.0
"""finance.shift subdomain routes."""

from __future__ import annotations

from routers.finance._common import (
    APIRouter,
    AppContext,
    Depends,
    HTTPException,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["finance"])


@router.get("/finance/shift-handover/workspace")
def shift_handover_workspace(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import build_workspace

    return ok(build_workspace(db, hotel_id, ctx.user_id))


@router.post("/finance/shift-handover/{handover_id}/float-count")
def shift_handover_float_count(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import save_float_count

    return ok(
        save_float_count(
            db,
            hotel_id,
            handover_id,
            payload.get("denominations") or [],
            diff_reason=str(payload.get("diff_reason") or ""),
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
            float_actual=payload.get("float_actual", payload.get("actual")),
        )
    )


@router.post("/finance/shift-handover/{handover_id}/asset-count")
def shift_handover_asset_count(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import save_asset_count

    return ok(
        save_asset_count(
            db,
            hotel_id,
            handover_id,
            payload.get("assets") or [],
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/sign")
def shift_handover_sign(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import sign_handover

    return ok(
        sign_handover(
            db,
            hotel_id,
            handover_id,
            str(payload.get("role") or "outgoing"),
            ctx.user_id,
            incoming_user_id=int(payload["incoming_user_id"]) if payload.get("incoming_user_id") else None,
            ack=payload.get("ack"),
            operator_name=ctx.full_name or ctx.username,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/complete")
def shift_handover_complete(
    handover_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import complete_handover

    return ok(
        complete_handover(
            db,
            hotel_id,
            handover_id,
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/escalate")
def shift_handover_escalate(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import escalate_task

    return ok(
        escalate_task(
            db,
            hotel_id,
            handover_id,
            int(payload.get("task_index") or 0),
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
        )
    )


# ---------- 班次接班（接收确认） ----------


@router.get("/finance/shift-handover/takeover/workspace")
def shift_takeover_workspace(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import build_takeover_workspace

    return ok(build_takeover_workspace(db, hotel_id, ctx.user_id))


@router.post("/finance/shift-handover/{handover_id}/takeover/revenue-ack")
def shift_takeover_revenue_ack(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import ack_takeover_revenue

    return ok(
        ack_takeover_revenue(db, hotel_id, handover_id, ok=bool(payload.get("ok", True)), operator_id=ctx.user_id)
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/deposit-ack")
def shift_takeover_deposit_ack(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import ack_takeover_deposit

    return ok(
        ack_takeover_deposit(db, hotel_id, handover_id, ok=bool(payload.get("ok", True)), operator_id=ctx.user_id)
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/float-recount")
def shift_takeover_float_recount(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import save_takeover_float_recount

    return ok(
        save_takeover_float_recount(
            db,
            hotel_id,
            handover_id,
            payload.get("denominations") or [],
            confirm=bool(payload.get("confirm")),
            operator_id=ctx.user_id,
            received_actual=payload.get("received_actual", payload.get("float_actual")),
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/asset-recount")
def shift_takeover_asset_recount(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import save_takeover_asset_recount

    return ok(
        save_takeover_asset_recount(
            db,
            hotel_id,
            handover_id,
            payload.get("assets") or [],
            confirm=bool(payload.get("confirm")),
            operator_id=ctx.user_id,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/guest-ack")
def shift_takeover_guest_ack(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import ack_takeover_guest

    return ok(
        ack_takeover_guest(
            db,
            hotel_id,
            handover_id,
            keys=payload.get("keys") or [],
            acked=bool(payload.get("acked", True)),
            operator_id=ctx.user_id,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/task-claim")
def shift_takeover_task_claim(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import claim_takeover_task

    return ok(
        claim_takeover_task(
            db,
            hotel_id,
            handover_id,
            task_index=int(payload.get("task_index") or 0),
            action=str(payload.get("action") or "claimed"),
            operator_id=ctx.user_id,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/carryover-ack")
def shift_takeover_carryover_ack(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import ack_takeover_carryover

    return ok(
        ack_takeover_carryover(
            db,
            hotel_id,
            handover_id,
            carryover_ids=[int(x) for x in (payload.get("carryover_ids") or [])],
            acked=bool(payload.get("acked", True)),
            operator_id=ctx.user_id,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/matters-confirm")
def shift_takeover_matters_confirm(
    handover_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import confirm_takeover_matters

    return ok(confirm_takeover_matters(db, hotel_id, handover_id, operator_id=ctx.user_id))


@router.post("/finance/shift-handover/{handover_id}/takeover/report-diff")
def shift_takeover_report_diff(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import report_receive_diff

    return ok(
        report_receive_diff(
            db,
            hotel_id,
            handover_id,
            item_type=str(payload.get("item_type") or "float"),
            item_key=str(payload.get("item_key") or ""),
            declared_val=float(payload.get("declared_val") or 0),
            received_val=float(payload.get("received_val") or 0),
            reason=str(payload.get("reason") or ""),
            operator_id=ctx.user_id,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/sign")
def shift_takeover_sign(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import sign_takeover_receive

    inc = payload.get("incoming_user_id")
    return ok(
        sign_takeover_receive(
            db,
            hotel_id,
            handover_id,
            incoming_user_id=int(inc) if inc else None,
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/takeover/complete")
def shift_takeover_complete(
    handover_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import complete_takeover_receive

    return ok(
        complete_takeover_receive(
            db,
            hotel_id,
            handover_id,
            operator_id=ctx.user_id,
            operator_name=ctx.full_name or ctx.username,
        )
    )


@router.post("/finance/shift-handover/{handover_id}/ai-draft/generate")
def shift_ai_draft_generate(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import generate_shift_ai_draft

    scene = str(payload.get("scene") or "handover")
    return ok(generate_shift_ai_draft(db, hotel_id, handover_id, scene))


@router.post("/finance/shift-handover/{handover_id}/ai-draft/confirm")
def shift_ai_draft_confirm(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import confirm_shift_ai_draft

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else payload
    staff_id = payload.get("approved_by_staff_id") or ctx.user_id
    try:
        staff_id = int(staff_id)
    except (TypeError, ValueError):
        raise HTTPException(400, "须填写有效工号")
    return ok(
        confirm_shift_ai_draft(
            db,
            hotel_id,
            plan=plan,
            approved_by=staff_id,
            operator_name=ctx.full_name or ctx.username or "",
        )
    )


@router.post("/finance/shift-handover/{handover_id}/ai-draft/reject")
def shift_ai_draft_reject(
    handover_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import reject_shift_ai_draft

    return ok(
        reject_shift_ai_draft(
            db,
            hotel_id,
            handover_id,
            operator_id=ctx.user_id,
            reason=str(payload.get("reason") or ""),
        )
    )
