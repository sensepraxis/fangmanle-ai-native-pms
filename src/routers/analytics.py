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

router = APIRouter(tags=["analytics"])


class AnalyticsActionExecPayload(BaseModel):
    action: dict


@router.get("/analytics/ai-actions")
def analytics_ai_actions(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """经营分析 AI 行动中枢：简报 + 可执行建议 + 订单风险标签。"""
    from application.analytics import generate_analytics_actions

    return ok(generate_analytics_actions(db, hotel_id))


@router.post("/analytics/ai-actions/execute")
def analytics_ai_actions_execute(
    payload: AnalyticsActionExecPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.analytics import execute_analytics_action

    return ok(execute_analytics_action(db, hotel_id, payload.action or {}))


@router.get("/insights/workspace")
def insights_workspace(
    hotel_id: int = Depends(hotel_scope),
    period: str = Query("month"),
    compare: str = Query("yoy"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    olap_dim: str = Query("channel"),
    db: Session = Depends(get_db),
):
    from application.analytics import build_workspace

    return ok(
        build_workspace(
            db,
            hotel_id,
            period=period,
            compare=compare,
            start=start,
            end=end,
            olap_dim=olap_dim,
        )
    )


@router.get("/insights/olap")
def insights_olap(
    hotel_id: int = Depends(hotel_scope),
    period: str = Query("month"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    dim: str = Query("channel"),
    db: Session = Depends(get_db),
):
    from analytics.insight_service import build_olap, build_workspace

    ws = build_workspace(db, hotel_id, period=period, start=start, end=end, olap_dim=dim)
    d0 = date.fromisoformat(ws["range"]["start"])
    d1 = date.fromisoformat(ws["range"]["end"])
    return ok(build_olap(db, hotel_id, d0, d1, dim=dim))


@router.post("/insights/ask")
def insights_ask(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.analytics import run_ask

    try:
        return ok(
            run_ask(
                db,
                hotel_id,
                question=str(payload.get("question") or ""),
                growth_factor=float(payload.get("growth_factor") or 1.0),
                period=str(payload.get("period") or "month"),
                compare=str(payload.get("compare") or "yoy"),
                start=payload.get("start"),
                end=payload.get("end"),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"智能问数失败：{e}") from e


@router.post("/insights/ask/stream")
def insights_ask_stream(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.analytics import stream_ask

    q = str(payload.get("question") or "")
    gf = max(0.5, min(2.0, float(payload.get("growth_factor") or 1.0)))
    period = str(payload.get("period") or "month")
    compare = str(payload.get("compare") or "yoy")
    start = payload.get("start")
    end = payload.get("end")

    def event_gen():
        try:
            for evt in stream_ask(
                db,
                hotel_id,
                question=q,
                growth_factor=gf,
                period=period,
                compare=compare,
                start=start,
                end=end,
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/insights/chat")
def insights_chat(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.analytics import chat_reply

    try:
        return ok(
            chat_reply(
                db,
                hotel_id,
                message=str(payload.get("message") or ""),
                history=payload.get("history") or [],
            )
        )
    except Exception as e:
        raise HTTPException(503, f"对话问数失败：{e}") from e


@router.get("/insights/ai-ask/catalog")
def insights_ai_ask_catalog(hotel_id: int = Depends(hotel_scope)):
    from application.analytics import catalog_payload

    return ok(catalog_payload())


@router.post("/insights/ai-ask/route")
def insights_ai_ask_route(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """阶段①→②：意图路由 + 澄清闸门（确认前不查库）。"""
    from application.analytics import route_question

    try:
        return ok(
            route_question(
                db,
                hotel_id,
                question=str(payload.get("question") or ""),
                period_preset=str(payload.get("period") or payload.get("period_preset") or "本月"),
                baseline=str(payload.get("baseline") or payload.get("compare") or "同比"),
                session_id=payload.get("session_id"),
                clarify_round=int(payload.get("clarify_round") or 0),
            )
        )
    except Exception as e:
        raise HTTPException(503, f"意图路由失败：{e}") from e


@router.post("/insights/ai-ask/clarify")
def insights_ai_ask_clarify(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """澄清选择回填（仍不查库，返回 confirm）。"""
    from application.analytics import apply_clarify_choice

    try:
        return ok(
            apply_clarify_choice(
                db,
                hotel_id,
                query_id=int(payload.get("query_id") or 0),
                question=str(payload.get("question") or ""),
                intent_id=payload.get("intent_id"),
                slot=payload.get("slot"),
                slot_value=payload.get("slot_value"),
                period_preset=str(payload.get("period") or "本月"),
                baseline=str(payload.get("baseline") or "同比"),
                clarify_round=int(payload.get("clarify_round") or 0),
            )
        )
    except Exception as e:
        raise HTTPException(503, f"澄清失败：{e}") from e


@router.post("/insights/ai-ask/confirm")
def insights_ai_ask_confirm(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """阶段③→④：用户确认后确定性查库 + 总结。"""
    from application.analytics import confirm_and_execute

    try:
        return ok(
            confirm_and_execute(
                db,
                hotel_id,
                query_id=int(payload.get("query_id") or 0),
                confirmed=bool(payload.get("confirmed", True)),
                intent_id=payload.get("intent_id"),
                slots=payload.get("slots") if isinstance(payload.get("slots"), dict) else None,
                period_preset=str(payload.get("period") or "本月"),
                baseline=str(payload.get("baseline") or "同比"),
                start=payload.get("start"),
                end=payload.get("end"),
                role=getattr(ctx, "role", None),
            )
        )
    except Exception as e:
        raise HTTPException(503, f"问数执行失败：{e}") from e


@router.post("/insights/ai-ask/confirm/stream")
def insights_ai_ask_confirm_stream(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """确认后流式：查库阶段事件 + AI token + 最终结构化结果。"""
    from application.analytics import stream_confirm_and_execute

    role = getattr(ctx, "role", None)

    def event_gen():
        try:
            for evt in stream_confirm_and_execute(
                db,
                hotel_id,
                query_id=int(payload.get("query_id") or 0),
                confirmed=bool(payload.get("confirmed", True)),
                intent_id=payload.get("intent_id"),
                slots=payload.get("slots") if isinstance(payload.get("slots"), dict) else None,
                period_preset=str(payload.get("period") or "本月"),
                baseline=str(payload.get("baseline") or "同比"),
                start=payload.get("start"),
                end=payload.get("end"),
                role=role,
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/insights/ai-ask/pii-ack")
def insights_ai_ask_pii_ack(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """v1.3 D7/D8：隐私二次确认后展示客户明细（审计留痕）。"""
    from application.analytics import ack_pii

    try:
        return ok(
            ack_pii(
                db,
                hotel_id,
                query_id=int(payload.get("query_id") or 0),
                ack_by=str(payload.get("ack_by") or payload.get("staff_no") or ""),
                role=getattr(ctx, "role", None),
                period_preset=str(payload.get("period") or "本月"),
                baseline=str(payload.get("baseline") or "同比"),
                start=payload.get("start"),
                end=payload.get("end"),
            )
        )
    except Exception as e:
        raise HTTPException(503, f"隐私确认失败：{e}") from e


@router.post("/board-ai/execute")
def board_ai_execute(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """看板 AI 可执行动作（open_path / 订单风险处置等）。"""
    from application.analytics import execute_board_ai_action

    action = (payload or {}).get("action") or payload or {}
    return ok(execute_board_ai_action(db, hotel_id, action))


@router.post("/board-ai/{kind}")
def board_ai_narrate(
    kind: str,
    payload: dict = Body(default={}),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """看板 AI 包层：order_risks|profit_insights|pricing_compare。"""
    from application.analytics import narrate_board_ai

    return ok(narrate_board_ai(db, hotel_id, kind, payload or {}))


@router.get("/ai-commands")
def list_ai_commands(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.analytics import list_ai_commands as _list_ai_commands

    return ok(_list_ai_commands(db, hotel_id))
