# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)

router = APIRouter(tags=["housekeeping"])


@router.get("/housekeeping")
def list_housekeeping(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.hk import list_housekeeping_tasks

    return ok(list_housekeeping_tasks(db, hotel_id))


@router.get("/housekeeping/staffing")
def housekeeping_staffing(
    view: str = "week",
    start: Optional[str] = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """日/周/月排班 + 未来 7 天 AI 建议。"""
    from datetime import date as _date

    from application.hk import staffing_board_tx

    start_d = None
    if start:
        try:
            start_d = _date.fromisoformat(start[:10])
        except ValueError:
            start_d = None
    return ok(staffing_board_tx(db, hotel_id, view=view, start=start_d))


@router.post("/housekeeping/staffing/ai-apply")
def housekeeping_staffing_ai_apply(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """非破坏性写入 AI 建议。可单日 / 区间 / 显式 proposed。"""
    from datetime import date as _date

    from application.hk import apply_ai_adjustments_tx

    def _d(key):
        raw = payload.get(key)
        if not raw:
            return None
        try:
            return _date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None

    items = payload.get("proposed") if isinstance(payload.get("proposed"), list) else None
    return ok(
        apply_ai_adjustments_tx(
            db,
            hotel_id,
            items,
            day=_d("day") or _d("date"),
            date_from=_d("date_from") or _d("from"),
            date_to=_d("date_to") or _d("to"),
        )
    )


@router.post("/housekeeping/staffing/ai-refresh")
def housekeeping_staffing_ai_refresh(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """排班 AI 建议：规则事实 + 真实 LLM 包层（点击触发）。"""
    from application.hk import narrate_staffing_ai

    return ok(narrate_staffing_ai(db, hotel_id, payload or {}))


@router.post("/housekeeping/staffing/ai-narrate")
def housekeeping_staffing_ai_narrate(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """同 ai-refresh：显式命名的解读入口。"""
    from application.hk import narrate_staffing_ai

    return ok(narrate_staffing_ai(db, hotel_id, payload or {}))


@router.post("/housekeeping/ai-plan/generate")
def hk_ai_plan_generate(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """房务 AI Harness：生成可确认写操作草案（系统 LLM 可插拔，规则兜底）。"""
    from application.hk import generate_plan

    scene = str(payload.get("scene") or "dispatch_assign")
    return ok(generate_plan(db, hotel_id, scene))


@router.post("/housekeeping/ai-plan/confirm")
def hk_ai_plan_confirm(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
    hotel_id: int = Depends(hotel_scope),
):
    """确认写入：只执行勾选的 items，真正落库。"""
    from application.hk import confirm_plan_tx

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else payload
    return ok(confirm_plan_tx(db, hotel_id, plan=plan, operator_id=ctx.user_id))


@router.post("/housekeeping/staffing/shift")
def housekeeping_upsert_shift(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """主管手改一格（source=manual）。"""
    from datetime import date as _date

    from application.hk import upsert_staffing_shift

    try:
        uid = int(payload.get("user_id"))
        d = _date.fromisoformat(str(payload.get("date")))
    except (TypeError, ValueError):
        raise HTTPException(400, "请选择员工和日期")
    start = None
    if payload.get("start"):
        try:
            start = _date.fromisoformat(str(payload.get("start"))[:10])
        except ValueError:
            start = None
    return ok(
        upsert_staffing_shift(
            db,
            hotel_id,
            user_id=uid,
            shift_date=d,
            shift=str(payload.get("shift") or "morning"),
            view=str(payload.get("view") or "week"),
            start=start,
        )
    )


@router.post("/housekeeping/staffing/copy-week")
def housekeeping_copy_week(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    from datetime import date as _date

    from application.hk import copy_staffing_week
    from hk.staffing_service import _week_bounds

    raw = payload.get("start") or payload.get("week_start")
    try:
        start = _date.fromisoformat(str(raw)[:10]) if raw else _date.today()
    except ValueError:
        start = _date.today()
    week_start, _ = _week_bounds(start)
    return ok(
        copy_staffing_week(
            db,
            hotel_id,
            week_start=week_start,
            view=str(payload.get("view") or "week"),
        )
    )


@router.post("/housekeeping/staffing/save-template")
def housekeeping_save_template(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    from datetime import date as _date

    from application.hk import save_staffing_template
    from hk.staffing_service import _week_bounds

    raw = payload.get("start") or payload.get("week_start")
    try:
        start = _date.fromisoformat(str(raw)[:10]) if raw else _date.today()
    except ValueError:
        start = _date.today()
    week_start, _ = _week_bounds(start)
    return ok(
        save_staffing_template(
            db,
            hotel_id,
            week_start=week_start,
            name=str(payload.get("name") or "默认周模板"),
        )
    )


@router.post("/housekeeping/staffing/add-staff")
def housekeeping_add_staff(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    from datetime import date as _date

    from application.hk import add_staffing_member
    from hk.staffing_service import _parse_view_range

    try:
        uid = int(payload.get("user_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "请选择员工")
    start = None
    if payload.get("start"):
        try:
            start = _date.fromisoformat(str(payload.get("start"))[:10])
        except ValueError:
            start = None
    view = str(payload.get("view") or "week")
    _view, range_start, range_end = _parse_view_range(view, start)
    return ok(
        add_staffing_member(
            db,
            hotel_id,
            user_id=uid,
            range_start=range_start,
            range_end=range_end,
            view=_view,
        )
    )


@router.post("/housekeeping/staffing/requests/{rid}/decide")
def housekeeping_shift_request_decide(
    rid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    from datetime import date as _date

    from application.hk import decide_shift_request

    approved = payload.get("approved", True) is not False
    start = None
    if payload.get("start"):
        try:
            start = _date.fromisoformat(str(payload.get("start"))[:10])
        except ValueError:
            start = None
    return ok(
        decide_shift_request(
            db,
            hotel_id,
            rid,
            approved=approved,
            view=str(payload.get("view") or "week"),
            start=start,
        )
    )


@router.get("/housekeeping/ai-assistant")
def housekeeping_ai_assistant(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """客需 AI 助理会话列表（读库）。"""
    from application.hk import build_housekeeping_ai_assistant

    return ok(build_housekeeping_ai_assistant(db, hotel_id))


@router.get("/housekeeping/board")
def housekeeping_board(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    perf_range: str = Query("7d", description="week | 7d | 30d，人效复盘区间"),
):
    """房务作业台聚合：任务 / 员工负荷 / 客需 / 效能 / 质检。"""
    from application.hk import build_housekeeping_board

    return ok(build_housekeeping_board(db, hotel_id, perf_range=perf_range))


@router.get("/service-requests")
def list_service_requests(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.hk import list_service_requests as list_service_requests_uc

    return ok(list_service_requests_uc(db, hotel_id))


@router.post("/service-requests")
def create_service_request(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """客中请求一键录入（休息人员不可派）。"""
    from application.hk import create_guest_request_tx

    try:
        room_id = int(payload.get("room_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "请选择房间")
    aid = payload.get("assignee_id")
    try:
        aid = int(aid) if aid not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        aid = None
    return ok(
        create_guest_request_tx(
            db,
            hotel_id,
            room_id=room_id,
            content=str(payload.get("content") or payload.get("msg") or ""),
            assignee_id=aid,
            priority=int(payload.get("priority") or 3),
        )
    )


@router.post("/housekeeping/ai-suggest")
def hk_ai_suggest(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
    hotel_id: int = Depends(hotel_scope),
):
    """根据系统现状调用 LLM + 房务 MCP 工具生成派工建议；默认应用派工，待建任务需一键采纳。"""
    from application.hk import ai_suggest_dispatch, ai_suggest_dispatch_tx

    apply = payload.get("apply", True) is not False
    notify = payload.get("notify", True) is not False
    snapshot = payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else None
    fn = ai_suggest_dispatch_tx if apply else ai_suggest_dispatch
    return ok(
        fn(
            db,
            hotel_id,
            apply=apply,
            operator_id=ctx.user_id,
            notify=notify and apply,
            snapshot=snapshot,
        )
    )


@router.post("/housekeeping/tasks")
def hk_create_tasks(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
    hotel_id: int = Depends(hotel_scope),
):
    """新建保洁任务（单条或批量）。与 AI「一键采纳」共用。"""
    from application.hk import create_hk_tasks

    items = payload.get("tasks") if isinstance(payload.get("tasks"), list) else None
    if items is None:
        items = [payload]
    return ok(create_hk_tasks(db, hotel_id, items))


@router.post("/housekeeping/batch-dispatch")
def hk_batch_dispatch(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
    hotel_id: int = Depends(hotel_scope),
):
    """批量派单：single / by_floor / smart；preview=true 仅预览。"""
    from application.hk import batch_dispatch_hk

    task_ids = payload.get("task_ids") or payload.get("ids") or []
    if isinstance(task_ids, str):
        task_ids = [int(x) for x in task_ids.split(",") if x.strip().isdigit()]
    task_ids = [int(x) for x in task_ids if str(x).lstrip("-").isdigit() and int(x) > 0]
    return ok(
        batch_dispatch_hk(
            db,
            hotel_id,
            task_ids,
            mode=str(payload.get("mode") or "single"),
            assignee_id=payload.get("assignee_id"),
            preview=bool(payload.get("preview")),
            operator_id=ctx.user_id,
            notify=payload.get("notify", True) is not False,
        )
    )


@router.get("/housekeeping/dispatch-staff")
def hk_dispatch_staff(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """批量派单可选保洁（含楼层认领）。"""
    from application.hk import _on_duty_staff

    return ok(_on_duty_staff(db, hotel_id))


@router.post("/housekeeping/{tid}/start")
def hk_start(
    tid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.hk import start_hk_task

    return ok(
        start_hk_task(
            db,
            tid,
            operator_id=ctx.user_id,
            assignee_id=payload.get("assignee_id"),
            assignee_name=payload.get("assignee_name") or payload.get("assignee"),
        )
    )


@router.post("/housekeeping/{tid}/assign")
def hk_assign(
    tid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """指派 / 换执行人。"""
    from application.hk import assign_hk_task

    return ok(
        assign_hk_task(
            db,
            tid,
            assignee_id=payload.get("assignee_id"),
            assignee_name=payload.get("assignee_name") or payload.get("assignee"),
        )
    )


@router.post("/housekeeping/{tid}/ignore")
def hk_ignore(
    tid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """忽略待处理任务（写库 status=ignored）。"""
    from application.hk import ignore_hk_task

    return ok(
        ignore_hk_task(
            db,
            tid,
            reason=str(payload.get("reason") or ""),
            operator_id=ctx.user_id,
        )
    )


@router.post("/housekeeping/{tid}/urge")
def hk_urge(
    tid: int,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """催办：优先级提到紧急并收紧截止时间。"""
    from application.hk import urge_hk_task

    return ok(urge_hk_task(db, tid))


@router.post("/housekeeping/{tid}/done")
def finish_housekeeping(
    tid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """清洁完成 → 待查房；维修单完成则解除 OOO。"""
    from application.hk import finish_hk_task

    to_status = str(payload.get("to_status") or payload.get("room_status") or "VC")
    return ok(finish_hk_task(db, tid, to_status=to_status, operator_id=ctx.user_id))


@router.post("/housekeeping/{tid}/inspect")
def hk_inspect(
    tid: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """查房验收：通过则 VD→VC；不通过可带 fail_items。"""
    from application.hk import inspect_hk_task

    passed = bool(payload.get("passed", True))
    fail_items = payload.get("fail_items") or payload.get("items") or []
    if isinstance(fail_items, str):
        fail_items = [x.strip() for x in fail_items.split(",") if x.strip()]
    return ok(
        inspect_hk_task(
            db,
            tid,
            passed=passed,
            inspector_id=ctx.user_id,
            fail_reason=str(payload.get("fail_reason") or payload.get("reason") or ""),
            fail_items=fail_items if isinstance(fail_items, list) else [],
        )
    )
