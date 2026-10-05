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
from infra.i18n import t
from models import OneIdPhoneConflict

router = APIRouter(tags=["guests"])


@router.get("/guests/arrival-calendar")
def guest_arrival_calendar(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(7, ge=3, le=14),
    db: Session = Depends(get_db),
):
    """近 N 日到店人数（按订单 check_in），供全景列表迷你日历联动。"""
    from application.guests import build_guest_arrival_calendar

    return ok(build_guest_arrival_calendar(db, hotel_id, days=days))


@router.get("/guests")
def list_guests(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """客户全景列表：guests + 身份来源 + 标签 + 最近到访（本店订单）。"""
    from application.guests import build_guests_list

    return ok(build_guests_list(db, hotel_id))


@router.get("/guests/{guest_id}")
def guest_360(guest_id: int, db: Session = Depends(get_db)):
    from application.guests import build_guest_360

    return ok(build_guest_360(db, guest_id=guest_id))


class WecomCareDraftPayload(BaseModel):
    material: str = ""


@router.post("/guests/{guest_id}/wecom-care-draft")
def guest_wecom_care_draft(
    guest_id: int,
    payload: WecomCareDraftPayload = WecomCareDraftPayload(),
    db: Session = Depends(get_db),
):
    """根据人工素材 AI 生成企微关怀话术（可编辑后再 POST /api/wecom/send）。"""
    from application.wecom import draft_wecom_care_message

    return ok(draft_wecom_care_message(db, guest_id, payload.material))


@router.get("/guests/{guest_id}/oneid-audit")
def guest_oneid_audit(guest_id: int, db: Session = Depends(get_db)):
    """单客 OneID 归并审计：身份链路 + 持久化归并事件。"""
    from application.guests import build_guest_oneid_audit

    return ok(build_guest_oneid_audit(db, guest_id=guest_id))


# ---------------- 夜审 ----------------
class WecomSendPayload(BaseModel):
    guest_id: int
    content: str


@router.post("/guests/{guest_id}/wecom-care-send")
def guest_wecom_care_send(
    guest_id: int,
    payload: WecomSendPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """关怀话术 1:1 发送：走 messaging 通道（wecom/line/webhook），不绑死企微 SDK。"""
    if payload.guest_id != guest_id:
        raise HTTPException(422, "guest_id 不一致")
    from extensions.messaging.facade import current_vendor, send_text

    vendor = current_vendor()
    if vendor == "wecom":
        # 企微侧保留侧边栏/粘贴兜底语义
        from application.wecom import send_care_direct_message

        return ok(send_care_direct_message(db, hotel_id, guest_id, payload.content))
    return ok(
        send_text(
            hotel_id=hotel_id,
            content=payload.content,
            guest_id=guest_id,
            db=db,
        )
    )


@router.get("/oneid/conflicts")
def list_oneid_conflicts(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = Query("pending"),
    db: Session = Depends(get_db),
):
    from application.wecom import list_phone_conflicts

    return ok(list_phone_conflicts(db, hotel_id, status=status))


@router.get("/oneid/duplicate-phones")
def oneid_duplicate_phones(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """同号档案分组（归一化手机号相同且 ≥2）。"""
    from application.guests import list_duplicate_phone_groups

    return ok(list_duplicate_phone_groups(db, hotel_id))


@router.get("/oneid/merge-case")
def oneid_merge_case(
    conflict_id: Optional[int] = Query(None),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """Wizard 当前案例：待处理冲突或同号双档（数据来自数据库）。"""
    from application.guests import get_oneid_merge_case

    return ok(get_oneid_merge_case(db, hotel_id, conflict_id=conflict_id))


@router.get("/oneid/guests/{guest_id}/assets")
def oneid_guest_assets(guest_id: int, db: Session = Depends(get_db)):
    """合并后资产确认页数据。"""
    from application.guests import get_guest_asset_summary

    return ok(get_guest_asset_summary(db, guest_id))


class OneIdConflictResolve(BaseModel):
    guest_id: int
    operator: Optional[str] = "前台运营"


@router.post("/oneid/conflicts/{conflict_id}/resolve")
def resolve_oneid_conflict(
    conflict_id: int,
    payload: OneIdConflictResolve,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.wecom import resolve_phone_conflict
    from models import OneIdPhoneConflict

    row = db.get(OneIdPhoneConflict, conflict_id)
    if not row or row.hotel_id != hotel_id:
        raise HTTPException(404, "冲突记录不存在")
    return ok(resolve_phone_conflict(db, conflict_id, payload.guest_id, operator=payload.operator or "前台运营"))


class OneIdConflictDismiss(BaseModel):
    operator: Optional[str] = "前台运营"
    note: Optional[str] = ""


@router.post("/oneid/conflicts/{conflict_id}/dismiss")
def dismiss_oneid_conflict(
    conflict_id: int,
    payload: OneIdConflictDismiss = OneIdConflictDismiss(),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.wecom import dismiss_phone_conflict
    from models import OneIdPhoneConflict

    row = db.get(OneIdPhoneConflict, conflict_id)
    if not row or row.hotel_id != hotel_id:
        raise HTTPException(404, "冲突记录不存在")
    return ok(dismiss_phone_conflict(db, conflict_id, operator=payload.operator or "前台运营", note=payload.note or ""))


# ---------------- 长尾域：真实模型列表接口 ----------------
@router.get("/oneid")
def list_oneid(db: Session = Depends(get_db)):
    """身份链路：guest_identities + 客人主档字段。"""
    from application.guests import list_oneid as list_oneid_q

    return ok(list_oneid_q(db))


@router.get("/oneid/board")
def oneid_board(db: Session = Depends(get_db)):
    """OneID 作业台：多源身份客、低置信链路、待处理冲突统计。"""
    from application.guests import build_oneid_board

    return ok(build_oneid_board(db))


@router.get("/tags")
def list_tags(db: Session = Depends(get_db)):
    from application.guests import list_tags as list_tags_q

    return ok(list_tags_q(db))


@router.get("/segments")
def list_segments(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """客群分群：segments + segment_members 覆盖人数（缺成员时自动补种）。"""
    from application.guests import build_segments_list

    return ok(build_segments_list(db, hotel_id))


class SegmentCreatePayload(BaseModel):
    name: str
    filter_rule: Optional[str] = None
    guest_ids: Optional[list[int]] = None


@router.post("/segments")
def create_segment(
    payload: SegmentCreatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """创建或更新客群分群，并写入 segment_members。"""
    from application.guests import create_guest_segment

    return ok(create_guest_segment(db, hotel_id, payload=payload))


@router.delete("/segments/{segment_id}")
def delete_segment(
    segment_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """删除分群及其成员；默认分群删除后不会被自动种回。"""
    from application.guests import delete_guest_segment

    return ok(delete_guest_segment(db, hotel_id, segment_id))


class NlSegmentQueryPayload(BaseModel):
    query: str = ""


@router.post("/segments/nl-query")
def segments_nl_query(
    payload: NlSegmentQueryPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """
    自然语言客群查询（真查库）。
    流程：LLM 意图识别 → FilterSpec（标签表达式）→ 规则编译 SQL → 查库。
    LLM 失败则返回空结果并标明未能调用大模型；SQL 永不由模型直接生成。
    关联：orders.guest_id → guests.id；本店：orders.hotel_id。
    """
    from application.guests import query_nl_guests
    from application.mkt import resolve_filter_spec
    from bootstrap.ensure_nl_segment import seed_nl_cancel_demo

    q = (payload.query or "").strip()
    if not q:
        raise HTTPException(400, "请输入客群描述")

    seed_nl_cancel_demo(db, hotel_id)
    spec, intent_meta = resolve_filter_spec(db, q)
    if intent_meta.get("intent_source") != "llm":
        return ok(
            {
                "items": [],
                "total": 0,
                "query": q,
                "message": t("未能调用大模型，未生成客群意图。"),
                **intent_meta,
            }
        )
    result = query_nl_guests(db, hotel_id, q, spec=spec)
    result.update(intent_meta)
    return ok(result)


@router.post("/segments/nl-query/stream")
def segments_nl_query_stream(
    payload: NlSegmentQueryPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """AI 找人 SSE：意图识别流式输出 → 查库 → done。"""
    from application.mkt import stream_nl_segment_query

    q = (payload.query or "").strip()
    if not q:
        raise HTTPException(400, "请输入客群描述")

    def event_gen():
        for evt in stream_nl_segment_query(db, hotel_id, q):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class CrmTaskCreatePayload(BaseModel):
    task_type: str = "recall"
    title: Optional[str] = None
    guest_ids: Optional[list[int]] = None
    segment_id: Optional[int] = None
    payload: Optional[dict] = None


@router.get("/crm/tasks")
def list_crm_tasks(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from application.guests import list_crm_tasks as list_crm_tasks_q

    return ok(list_crm_tasks_q(db, hotel_id, status=status))


@router.post("/crm/tasks")
def create_crm_tasks(
    payload: CrmTaskCreatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.guests import create_crm_tasks

    return ok(create_crm_tasks(db, hotel_id, payload=payload))


@router.patch("/crm/tasks/{task_id}")
def patch_crm_task(
    task_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.guests import complete_crm_task

    return ok(complete_crm_task(db, hotel_id, task_id))


class TagUpsertPayload(BaseModel):
    code: Optional[str] = None
    name: str
    category: Optional[str] = None
    rule_expr: Optional[str] = None
    is_active: bool = True


@router.post("/tags")
def create_tag(payload: TagUpsertPayload, db: Session = Depends(get_db)):
    from application.guests import create_tag_definition

    return ok(
        create_tag_definition(
            db,
            name=payload.name,
            code=payload.code,
            category=payload.category,
            rule_expr=payload.rule_expr,
            is_active=payload.is_active,
        )
    )


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, payload: TagUpsertPayload, db: Session = Depends(get_db)):
    from application.guests import update_tag_definition

    return ok(
        update_tag_definition(
            db,
            tag_id,
            name=payload.name,
            category=payload.category,
            rule_expr=payload.rule_expr,
            is_active=payload.is_active,
        )
    )


@router.post("/tags/{tag_id}/apply")
def apply_tag(tag_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.guests import apply_tag_to_hotel_guests

    return ok(apply_tag_to_hotel_guests(db, hotel_id, tag_id))


class OneIdMergePayload(BaseModel):
    primary_guest_id: int
    secondary_guest_id: int


@router.post("/oneid/merge")
def merge_oneid_guests(payload: OneIdMergePayload, db: Session = Depends(get_db)):
    from application.guests import merge_oneid_guests

    return ok(merge_oneid_guests(db, payload=payload))


class GuestEventPayload(BaseModel):
    guest_id: int
    event_type: str = "iot_anomaly"
    note: Optional[str] = None


@router.post("/crm/guest-events")
def post_guest_event(
    payload: GuestEventPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """房务/IoT 信号写入客史（E3 占位）：自动打 iot_anomaly 标签并创建关怀任务。"""
    from application.guests import post_guest_event

    return ok(post_guest_event(db, hotel_id, payload=payload))


@router.get("/segments/compare")
def compare_segments(
    segment_a: str,
    segment_b: str,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.guests import compare_guest_segments

    return ok(compare_guest_segments(db, hotel_id, segment_a=segment_a, segment_b=segment_b))


@router.get("/segments/{segment_id}/export")
def export_segment(
    segment_id: int,
    plaintext: bool = Query(False, description="禁止：明文导出会被拒绝并记审计"),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """分群导出：默认脱敏手机号；拒绝一键明文导出。"""
    from application.guests import export_guest_segment

    return ok(export_guest_segment(db, hotel_id, segment_id=segment_id, plaintext=plaintext, ctx=ctx))
