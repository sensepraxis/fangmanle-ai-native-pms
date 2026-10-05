# SPDX-License-Identifier: Apache-2.0
"""营销活动 CRUD / 审批 / 模板。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from mkt._mkt_utils import _dt, _jdumps, _jloads
from mkt.campaign_templates import CAMPAIGN_TEMPLATES
from models import MktCampaign, MktCoupon

CAMPAIGN_STATUSES = ("draft", "pending", "running", "paused", "ended", "archived")
CAMPAIGN_TRANSITIONS = {
    "draft": {"pending", "archived"},
    "pending": {"running", "draft"},  # approve / reject
    "running": {"paused", "ended"},
    "paused": {"running", "ended"},
    "ended": {"archived"},
    "archived": set(),
}


def campaign_to_dict(c: MktCampaign, db: Optional[Session] = None) -> dict:
    cfg = _jloads(c.config_json, {})
    strategy = cfg.get("strategy") or {}
    mode = strategy.get("mode") or ("coupon" if cfg.get("coupon_ids") else "none")
    coupon_ids = strategy.get("coupon_ids") or cfg.get("coupon_ids") or []
    coupon_labels: list[str] = []
    if db is not None and coupon_ids:
        for cid in coupon_ids:
            row = db.get(MktCoupon, int(cid))
            if row:
                coupon_labels.append(f"{row.batch_no} {row.name}")
    metric = cfg.get("metric") or {}
    return {
        "id": c.id,
        "name": c.name,
        "type": c.type,
        "status": c.status,
        "start_at": c.start_at.isoformat() if c.start_at else None,
        "end_at": c.end_at.isoformat() if c.end_at else None,
        "template_id": c.template_id,
        "goal": cfg.get("goal") or "",
        "config": cfg,
        "strategy_mode": mode,
        "coupon_ids": coupon_ids,
        "coupon_labels": coupon_labels,
        "channels": cfg.get("channels") or [],
        "audience": cfg.get("audience") or {},
        "metric": {
            "reach": int(metric.get("reach") or 0),
            "conv": int(metric.get("conv") or 0),
            "gmv": float(metric.get("gmv") or 0),
        },
        "created_by": c.created_by,
        "approved_by": c.approved_by,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def list_campaign_templates() -> list[dict]:
    return CAMPAIGN_TEMPLATES


def list_campaigns(db: Session, hotel_id: int, status: Optional[str] = None) -> list[dict]:
    q = db.query(MktCampaign).filter_by(hotel_id=hotel_id)
    if status:
        q = q.filter_by(status=status)
    return [campaign_to_dict(c, db) for c in q.order_by(MktCampaign.id.desc()).all()]


def create_campaign(db: Session, hotel_id: int, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise InvalidStateError('"请填写活动名称"')
    status = str(payload.get("status") or "draft")
    if status not in ("draft", "pending"):
        status = "draft"
    cfg = dict(payload.get("config") or {})
    # 兼容架构文档 strategy_json / channels_json / audience_json
    if payload.get("strategy_json"):
        cfg["strategy"] = payload["strategy_json"]
    elif payload.get("strategy"):
        cfg["strategy"] = payload["strategy"]
    strategy = cfg.get("strategy") or {}
    if not strategy and ("coupon_ids" in cfg or "mode" in payload):
        mode = payload.get("mode") or cfg.get("mode") or ("coupon" if cfg.get("coupon_ids") else "none")
        strategy = {
            "mode": mode,
            "coupon_ids": cfg.get("coupon_ids") or payload.get("coupon_ids") or [],
            "discount_rate": payload.get("discount_rate") or cfg.get("discount_rate"),
            "apply_rooms": payload.get("apply_rooms") or cfg.get("apply_rooms") or [],
            "price_policy": payload.get("price_policy") or cfg.get("price_policy"),
        }
        cfg["strategy"] = strategy
    if strategy.get("mode") == "coupon" and status == "pending":
        ids = strategy.get("coupon_ids") or []
        if not ids:
            raise InvalidStateError('"发券模式请至少绑定一个券批次"')
    if payload.get("channels_json") is not None:
        cfg["channels"] = payload["channels_json"]
    elif payload.get("channels") is not None:
        cfg["channels"] = payload["channels"]
    if payload.get("audience_json") is not None:
        cfg["audience"] = payload["audience_json"]
    elif payload.get("audience") is not None:
        cfg["audience"] = payload["audience"]
    if payload.get("goal"):
        cfg["goal"] = payload["goal"]
    if payload.get("desc") or payload.get("description"):
        cfg["desc"] = payload.get("desc") or payload.get("description")
    # 扁平兼容：旧前端只传 config.coupon_ids
    if strategy.get("coupon_ids") and "coupon_ids" not in cfg:
        cfg["coupon_ids"] = strategy["coupon_ids"]
    row = MktCampaign(
        hotel_id=hotel_id,
        name=name,
        type=str(payload.get("type") or "custom"),
        status=status,
        start_at=_dt(payload.get("start_at")),
        end_at=_dt(payload.get("end_at")),
        template_id=payload.get("template_id"),
        config_json=_jdumps(cfg),
        created_by=str(payload.get("created_by") or "manager"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return campaign_to_dict(row, db)


def patch_campaign_status(db: Session, hotel_id: int, campaign_id: int, status: str, *, approved_by: str = "") -> dict:
    row = db.query(MktCampaign).filter_by(id=campaign_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"活动不存在"')
    cur = row.status or "draft"
    allowed = CAMPAIGN_TRANSITIONS.get(cur, set())
    if status not in allowed and not (cur == "pending" and status == "running"):
        raise InvalidStateError('f"不可从 {cur} 流转到 {status}"')
    if status == "running" and cur == "pending":
        row.approved_by = approved_by or "manager"
    row.status = status
    db.commit()
    return campaign_to_dict(row, db)


def approve_campaign(db: Session, hotel_id: int, campaign_id: int, approved_by: str = "manager") -> dict:
    row = db.query(MktCampaign).filter_by(id=campaign_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"活动不存在"')
    if row.status not in ("draft", "pending"):
        raise InvalidStateError('"仅草稿/待审批可审批通过"')
    row.status = "running"
    row.approved_by = approved_by
    db.commit()
    return campaign_to_dict(row, db)


def reject_campaign(db: Session, hotel_id: int, campaign_id: int) -> dict:
    return patch_campaign_status(db, hotel_id, campaign_id, "draft")
