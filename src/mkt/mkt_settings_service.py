# SPDX-License-Identifier: Apache-2.0
"""酒店营销设置。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from mkt._mkt_utils import _jdumps, _jloads
from models import HotelMktSettings, WxLandingPage


def _entry_ids(settings: Optional[HotelMktSettings]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    if not settings:
        return None, None, None
    return (
        settings.welcome_landing_page_id,
        getattr(settings, "member_landing_page_id", None),
        getattr(settings, "returning_landing_page_id", None),
    )


def get_mkt_settings(db: Session, hotel_id: int) -> dict:
    s = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    default_points = {
        "spend_per_point": 1,
        "checkin_bonus": 10,
        "review_bonus": 20,
        "birthday_multiplier": 2.0,
        "redeem_points_per_yuan": 100,
        "expire_months": 12,
        "rule_note": "积分仅限本店企微 H5 私域使用，与 PMS 全局会员积分无关。",
    }
    if not s:
        return {
            "default_receiver_userid": "",
            "welcome_text": "",
            "welcome_landing_page_id": None,
            "member_landing_page_id": None,
            "returning_landing_page_id": None,
            "points": default_points,
        }
    points = {**default_points, **(_jloads(getattr(s, "points_json", None), {}) or {})}
    return {
        "default_receiver_userid": s.default_receiver_userid or "",
        "welcome_text": s.welcome_text or "",
        "welcome_landing_page_id": s.welcome_landing_page_id,
        "member_landing_page_id": getattr(s, "member_landing_page_id", None),
        "returning_landing_page_id": getattr(s, "returning_landing_page_id", None),
        "points": points,
    }


def save_mkt_settings(db: Session, hotel_id: int, payload: dict) -> dict:
    s = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    if not s:
        s = HotelMktSettings(hotel_id=hotel_id)
        db.add(s)
    if "default_receiver_userid" in payload:
        s.default_receiver_userid = str(payload.get("default_receiver_userid") or "").strip() or None
    if "welcome_text" in payload:
        s.welcome_text = str(payload.get("welcome_text") or "")
    if "welcome_landing_page_id" in payload:
        raw = payload.get("welcome_landing_page_id")
        if raw in (None, "", 0, "0"):
            s.welcome_landing_page_id = None
        else:
            try:
                pid = int(raw)
            except (TypeError, ValueError):
                raise InvalidStateError('"welcome_landing_page_id 无效"')
            page = db.query(WxLandingPage).filter_by(id=pid, hotel_id=hotel_id).first()
            if not page:
                raise NotFoundError('"落地页不存在"')
            if page.status != "published":
                raise InvalidStateError('"请先发布落地页，再设为企微扫码领券页"')
            s.welcome_landing_page_id = pid
    if "member_landing_page_id" in payload:
        raw = payload.get("member_landing_page_id")
        if raw in (None, "", 0, "0"):
            s.member_landing_page_id = None
        else:
            try:
                pid = int(raw)
            except (TypeError, ValueError):
                raise InvalidStateError('"member_landing_page_id 无效"')
            page = db.query(WxLandingPage).filter_by(id=pid, hotel_id=hotel_id).first()
            if not page:
                raise NotFoundError('"落地页不存在"')
            if page.status != "published":
                raise InvalidStateError('"请先发布落地页，再设为企微会员中心页"')
            page.page_role = "member"
            s.member_landing_page_id = pid
    if "returning_landing_page_id" in payload:
        raw = payload.get("returning_landing_page_id")
        if raw in (None, "", 0, "0"):
            s.returning_landing_page_id = None
        else:
            try:
                pid = int(raw)
            except (TypeError, ValueError):
                raise InvalidStateError('"returning_landing_page_id 无效"')
            page = db.query(WxLandingPage).filter_by(id=pid, hotel_id=hotel_id).first()
            if not page:
                raise NotFoundError('"落地页不存在"')
            if page.status != "published":
                raise InvalidStateError('"请先发布落地页，再设为老客回访页"')
            page.page_role = "returning"
            s.returning_landing_page_id = pid
    if "points" in payload and isinstance(payload.get("points"), dict):
        s.points_json = _jdumps(payload["points"])
    db.commit()
    return get_mkt_settings(db, hotel_id)
