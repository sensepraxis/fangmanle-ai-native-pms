# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""小红书聚光/开放平台 Webhook：多租户路由、验签、线索入库。"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
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
from models import AcquisitionLead, HotelChannelBinding, WebhookEventLog

ACCOUNT_ID_KEYS = (
    "ad_account_id",
    "advertiser_id",
    "account_id",
    "advertiserId",
    "adAccountId",
)
PROFESSIONAL_ID_KEYS = ("professional_id", "brand_id", "xhs_professional_id", "user_id")
EXTERNAL_ID_KEYS = ("lead_id", "clue_id", "external_id", "msg_id", "id", "event_id")
NICKNAME_KEYS = ("nick_name", "nickname", "user_name", "userName", "name")
PHONE_KEYS = ("phone", "mobile", "tel", "telephone", "contact_phone")
WECHAT_KEYS = ("wechat", "weixin", "wx", "wechat_id", "wechatId")
NOTE_TITLE_KEYS = ("note_title", "noteTitle", "title", "content_title")
NOTE_URL_KEYS = ("note_url", "noteUrl", "note_link", "noteLink", "source_note_url", "sourceNoteUrl")
PLAN_ID_KEYS = ("plan_id", "planId", "campaign_id", "campaignId", "ad_plan_id")
CREATIVE_ID_KEYS = ("creative_id", "creativeId", "ad_creative_id")
UNIT_ID_KEYS = ("unit_id", "unitId", "ad_unit_id")
INTENT_KEYS = ("intent", "lead_level", "quality", "clue_level", "lead_tag")
TYPE_KEYS = ("type", "event_type", "payload_type", "msg_type")
LEAD_TYPE_KEYS = ("lead_type", "leadType", "source_type", "clue_type", "channel")

UPDATE_TYPE_MARKERS = (
    "更新内容",
    "更新归因",
    "update_content",
    "update_attribution",
    "update",
    "updated",
)


def _first_str(data: dict, keys: tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = data.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    for nested_key in ("data", "lead", "clue", "payload"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            hit = _first_str(nested, keys)
            if hit:
                return hit
    return None


def _normalize_intent(raw: Optional[str]) -> str:
    if not raw:
        return "mid"
    s = str(raw).lower()
    if s in ("high", "a", "1", "高", "高意向", "留客资", "留资"):
        return "high"
    if s in ("low", "c", "3", "低", "低意向"):
        return "low"
    return "mid"


def _normalize_lead_type(raw: Optional[str], payload: dict) -> str:
    s = (raw or "").lower()
    if s in ("form", "landing", "表单", "落地页"):
        return "form"
    if s in ("manual", "手工", "hand"):
        return "manual"
    if "form" in json.dumps(payload, ensure_ascii=False).lower():
        return "form"
    return "dm"


def _normalize_payload_type(raw: Optional[str]) -> str:
    s = (raw or "new").strip()
    low = s.lower()
    if any(x in s for x in ("更新内容", "update_content")):
        return "update_content"
    if any(x in s for x in ("更新归因", "update_attribution", "归因")):
        return "update_attribution"
    if low in UPDATE_TYPE_MARKERS or low.startswith("update"):
        return "update_content"
    return "new"


def extract_signature(headers: dict[str, str]) -> Optional[str]:
    for key in (
        "X-Red-Signature",
        "x-red-signature",
        "X-XHS-Signature",
        "X-Webhook-Signature",
        "X-Signature",
        "signature",
    ):
        v = headers.get(key)
        if v:
            return v.strip()
    return None


def verify_webhook_signature(
    raw_body: bytes,
    secret: Optional[str],
    signature: Optional[str],
) -> None:
    """聚光 Token 验签：支持 X-Red-Signature / HMAC-SHA256(hex)。"""
    if not secret:
        return
    if not signature:
        raise AuthenticationError("缺少 Webhook 签名头")
    sig = signature.strip()
    if sig.startswith("sha256="):
        sig = sig[7:]
    expect = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expect, sig.lower()):
        return
    # 部分文档为 body+token 或 uppercase hex，再试一种常见变体
    expect2 = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest().upper()
    if hmac.compare_digest(expect2, sig.upper()):
        return
    raise AuthenticationError("Webhook 签名校验失败")


def resolve_binding(
    db: Session,
    *,
    binding_token: Optional[str] = None,
    payload: Optional[dict] = None,
) -> Optional[HotelChannelBinding]:
    if binding_token:
        row = db.query(HotelChannelBinding).filter_by(binding_token=binding_token.strip(), status="active").first()
        if row:
            return row
    if not payload:
        return None
    ad_id = _first_str(payload, ACCOUNT_ID_KEYS)
    pro_id = _first_str(payload, PROFESSIONAL_ID_KEYS)
    q = db.query(HotelChannelBinding).filter_by(channel="xiaohongshu", status="active")
    if ad_id:
        hit = q.filter_by(xhs_ad_account_id=ad_id).first()
        if hit:
            return hit
    if pro_id:
        hit = q.filter_by(xhs_professional_id=pro_id).first()
        if hit:
            return hit
    page_id = _first_str(payload, ("page_id", "pageId", "landing_page_id"))
    if page_id:
        for row in q.all():
            ids = (row.xhs_page_ids or "").replace("，", ",").split(",")
            if page_id in {x.strip() for x in ids if x.strip()}:
                return row
    return None


def parse_xhs_lead_payload(payload: dict) -> dict:
    ext = _first_str(payload, EXTERNAL_ID_KEYS)
    if not ext:
        ext = f"xhs_evt_{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]}"
    plan_id = _first_str(payload, PLAN_ID_KEYS)
    creative_id = _first_str(payload, CREATIVE_ID_KEYS)
    unit_id = _first_str(payload, UNIT_ID_KEYS)
    campaign = {
        "plan_id": plan_id,
        "creative_id": creative_id,
        "unit_id": unit_id,
        "channel": _first_str(payload, ("channel", "source", "source_channel")),
    }
    return {
        "external_id": ext,
        "nickname": _first_str(payload, NICKNAME_KEYS),
        "phone": _first_str(payload, PHONE_KEYS),
        "wechat": _first_str(payload, WECHAT_KEYS),
        "note_title": _first_str(payload, NOTE_TITLE_KEYS),
        "source_note_url": _first_str(payload, NOTE_URL_KEYS),
        "intent": _normalize_intent(_first_str(payload, INTENT_KEYS)),
        "lead_type": _normalize_lead_type(_first_str(payload, LEAD_TYPE_KEYS), payload),
        "payload_type": _normalize_payload_type(_first_str(payload, TYPE_KEYS)),
        "xhs_plan_id": plan_id,
        "xhs_creative_id": creative_id,
        "xhs_unit_id": unit_id,
        "campaign_json": json.dumps({k: v for k, v in campaign.items() if v}, ensure_ascii=False) or None,
        "xhs_ad_account_id": _first_str(payload, ACCOUNT_ID_KEYS),
        "xhs_professional_id": _first_str(payload, PROFESSIONAL_ID_KEYS),
    }


def apply_parsed_to_lead(lead: AcquisitionLead, parsed: dict) -> None:
    if parsed.get("nickname"):
        lead.nickname = parsed["nickname"]
    if parsed.get("phone"):
        lead.phone = parsed["phone"]
    if parsed.get("wechat"):
        lead.wechat = parsed["wechat"]
    if parsed.get("note_title"):
        lead.note_title = parsed["note_title"]
    if parsed.get("source_note_url"):
        lead.source_note_url = parsed["source_note_url"]
    if parsed.get("intent"):
        lead.intent = parsed["intent"]
    if parsed.get("lead_type"):
        lead.lead_type = parsed["lead_type"]
    if parsed.get("payload_type"):
        lead.payload_type = parsed["payload_type"]
    if parsed.get("xhs_plan_id"):
        lead.xhs_plan_id = parsed["xhs_plan_id"]
    if parsed.get("xhs_creative_id"):
        lead.xhs_creative_id = parsed["xhs_creative_id"]
    if parsed.get("xhs_unit_id"):
        lead.xhs_unit_id = parsed["xhs_unit_id"]
    if parsed.get("campaign_json"):
        lead.campaign_json = parsed["campaign_json"]


def create_manual_lead(
    db: Session,
    *,
    hotel_id: int,
    payload: dict,
) -> AcquisitionLead:
    parsed = parse_xhs_lead_payload(payload)
    parsed["lead_type"] = "manual"
    parsed["payload_type"] = "new"
    ext = payload.get("external_id") or f"manual_{hotel_id}_{int(time.time())}"
    parsed["external_id"] = str(ext)
    lead = AcquisitionLead(
        hotel_id=hotel_id,
        channel=payload.get("channel") or "xiaohongshu",
        external_id=parsed["external_id"],
        stage="new",
        remark=payload.get("remark") or "手工录入线索",
    )
    apply_parsed_to_lead(lead, parsed)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def ingest_xhs_webhook(
    db: Session,
    *,
    payload: dict,
    binding: Optional[HotelChannelBinding],
    raw_json: str,
) -> dict:
    parsed = parse_xhs_lead_payload(payload)
    ext = parsed["external_id"]
    log = WebhookEventLog(
        channel="xiaohongshu",
        external_event_id=ext,
        payload_json=raw_json[:8000],
        status="received",
    )
    if binding:
        log.hotel_id = binding.hotel_id
        log.binding_id = binding.id
    db.add(log)
    db.flush()

    if not binding:
        log.status = "unmapped"
        log.error_message = "无法匹配酒店绑定（请检查 binding_token 或广告账户 ID）"
        db.commit()
        return {
            "accepted": True,
            "mapped": False,
            "event_log_id": log.id,
            "message": log.error_message,
        }

    exists = (
        db.query(AcquisitionLead).filter_by(hotel_id=binding.hotel_id, channel="xiaohongshu", external_id=ext).first()
    )
    if exists:
        if parsed["payload_type"] in ("update_content", "update_attribution"):
            apply_parsed_to_lead(exists, parsed)
            exists.remark = f"Webhook 更新 · {parsed['payload_type']}"
            log.status = "updated"
            log.lead_id = exists.id
            db.commit()
            db.refresh(exists)
            return {
                "accepted": True,
                "mapped": True,
                "duplicate": False,
                "updated": True,
                "lead_id": exists.id,
                "event_log_id": log.id,
            }
        log.status = "duplicate"
        log.lead_id = exists.id
        log.error_message = "线索已存在，幂等跳过"
        db.commit()
        return {
            "accepted": True,
            "mapped": True,
            "duplicate": True,
            "lead_id": exists.id,
            "event_log_id": log.id,
        }

    lead = AcquisitionLead(
        hotel_id=binding.hotel_id,
        channel="xiaohongshu",
        external_id=ext,
        stage="new",
        remark=f"小红书 Webhook 入库 · 绑定 #{binding.id}",
    )
    apply_parsed_to_lead(lead, parsed)
    db.add(lead)
    db.flush()
    log.status = "processed"
    log.lead_id = lead.id
    db.commit()
    db.refresh(lead)
    return {
        "accepted": True,
        "mapped": True,
        "duplicate": False,
        "updated": False,
        "lead_id": lead.id,
        "hotel_id": binding.hotel_id,
        "event_log_id": log.id,
    }


def new_binding_token() -> str:
    return secrets.token_urlsafe(24)


def binding_webhook_path(binding_token: str) -> str:
    return f"/api/webhook/xhs/leads/{binding_token}"


def binding_public_urls(binding_token: str, base_url: Optional[str] = None) -> dict:
    base = (base_url or "").rstrip("/")
    path = binding_webhook_path(binding_token)
    return {
        "path": path,
        "url": f"{base}{path}" if base else path,
        "hint": "聚光后台「私信 API / 线索推送」填写完整 HTTPS URL",
    }
