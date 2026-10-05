# SPDX-License-Identifier: Apache-2.0
"""mkt.ai subdomain routes."""

from __future__ import annotations

from routers.mkt._common import APIRouter, Body, Depends, Session, StreamingResponse, get_db, hotel_scope, json, ok

router = APIRouter(tags=["mkt"])


@router.post("/mkt/ai-ops/diagnosis")
def mkt_ai_ops_diagnosis(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """私域健康度诊断：格式化文案 + 可写操作。"""
    from application.mkt import narrate_mkt_ai

    return ok(narrate_mkt_ai(db, hotel_id, "diagnosis"))


@router.post("/mkt/ai-ops/week_plan")
def mkt_ai_ops_week_plan(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import narrate_mkt_ai

    return ok(narrate_mkt_ai(db, hotel_id, "week_plan"))


@router.post("/mkt/ai-ops/radar")
def mkt_ai_ops_radar(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import narrate_mkt_ai

    return ok(narrate_mkt_ai(db, hotel_id, "radar"))


@router.post("/mkt/ai-ops/execute")
def mkt_ai_ops_execute(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """执行私域 AI 写操作按钮。"""
    from application.mkt import execute_mkt_diagnosis_action

    action = (payload or {}).get("action") or payload or {}
    return ok(execute_mkt_diagnosis_action(db, hotel_id, action))


@router.post("/mkt/points-ai/execute")
def mkt_points_ai_execute(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """执行积分规则 AI 写操作 / 试算。"""
    from application.mkt import execute_points_ai_action

    action = (payload or {}).get("action") or payload or {}
    return ok(execute_points_ai_action(db, hotel_id, action))


@router.post("/mkt/points-ai/{kind}")
def mkt_points_ai_narrate(
    kind: str,
    payload: dict = Body(default={}),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """积分规则 AI：rate_suggest|expire_wakeup|scenario_nl。"""
    from application.mkt import narrate_points_ai

    return ok(narrate_points_ai(db, hotel_id, kind, payload or {}))


@router.post("/mkt/member-ai/execute")
def mkt_member_ai_execute(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """执行会员体系 AI 写操作。"""
    from application.mkt import execute_member_ai_action

    action = (payload or {}).get("action") or payload or {}
    return ok(execute_member_ai_action(db, hotel_id, action))


@router.post("/mkt/member-ai/{kind}")
def mkt_member_ai_narrate(
    kind: str,
    payload: dict = Body(default={}),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """会员体系 AI：threshold_calibrate|benefit_pack。"""
    from application.mkt import narrate_member_ai

    return ok(narrate_member_ai(db, hotel_id, kind, payload or {}))


@router.post("/mkt/coupon-ai/execute")
def mkt_coupon_ai_execute(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """执行优惠券 AI 写操作 / 回填动作。"""
    from application.mkt import execute_coupon_ai_action

    action = (payload or {}).get("action") or payload or {}
    return ok(execute_coupon_ai_action(db, hotel_id, action))


@router.post("/mkt/coupon-ai/{kind}")
def mkt_coupon_ai_narrate(
    kind: str,
    payload: dict = Body(default={}),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """优惠券中心 AI：smart_create|audience|rule_recommend|budget|redeem_insight。"""
    from application.mkt import narrate_coupon_ai

    return ok(narrate_coupon_ai(db, hotel_id, kind, payload or {}))


@router.post("/mkt/ai-ops/{kind}/stream")
def mkt_ai_ops_stream(
    kind: str,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """兼容旧流式路径：内部改为格式化结果一次性返回（不再吐 JSON token）。"""
    from application.mkt import stream_mkt_ai_ops

    def event_gen():
        for evt in stream_mkt_ai_ops(db, hotel_id, kind):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
