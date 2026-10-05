# SPDX-License-Identifier: Apache-2.0
"""落地页 CRUD / 发布 / 渲染。"""

from __future__ import annotations

import json
import secrets
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from mkt._mkt_utils import _jdumps, _jloads
from mkt.mkt_settings_service import _entry_ids
from models import HotelMktSettings, MktCoupon, WxLandingPage, WxLandingTemplate

PAGE_ROLES = ("claim", "member", "returning")
CLAIM_BLOCK_TYPES = {"banner", "coupon_card", "button", "text", "image", "form_phone", "countdown", "cs"}
MEMBER_BLOCK_TYPES = {
    "banner",
    "text",
    "image",
    "button",
    "cs",
    "member_header",
    "coupon_wallet",
    "order_list",
    "benefit_list",
    "nav_tabs",
}
# 老客扫码中间页：欢迎回来 + 券包 + 进会员中心（对标原 renderWallet 效果）
RETURNING_BLOCK_TYPES = {
    "banner",
    "text",
    "image",
    "button",
    "cs",
    "member_header",
    "coupon_wallet",
}
ALL_BLOCK_TYPES = CLAIM_BLOCK_TYPES | MEMBER_BLOCK_TYPES | RETURNING_BLOCK_TYPES


def _allowed_blocks_for_role(role: str) -> set[str]:
    if role == "member":
        return MEMBER_BLOCK_TYPES
    if role == "returning":
        return RETURNING_BLOCK_TYPES
    return CLAIM_BLOCK_TYPES


def landing_to_dict(
    p: WxLandingPage,
    *,
    is_welcome: bool = False,
    is_member: bool = False,
    is_returning: bool = False,
) -> dict:
    role = (getattr(p, "page_role", None) or "claim").strip() or "claim"
    status = p.status or "draft"
    has_unpublished = _has_unpublished_changes(p)
    return {
        "id": p.id,
        "page_key": p.page_key,
        "title": p.title,
        "template_id": p.template_id,
        "page_role": role,
        "blocks": _jloads(p.blocks_json, []),
        "coupon_id": p.coupon_id,
        "status": status,
        "published_url": p.published_url,
        "has_unpublished_changes": has_unpublished,
        "is_welcome_landing": bool(is_welcome),
        "is_member_landing": bool(is_member),
        "is_returning_landing": bool(is_returning),
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "updated_by": p.updated_by,
    }


def _norm_json_text(raw: Any) -> str:
    """规范化 JSON 文本便于比较草稿与线上快照。"""
    data = _jloads(raw, [])
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _has_unpublished_changes(p: WxLandingPage) -> bool:
    if (p.status or "") != "published":
        return False
    pub_blocks = getattr(p, "published_blocks_json", None)
    if not pub_blocks:
        return True
    if _norm_json_text(p.blocks_json) != _norm_json_text(pub_blocks):
        return True
    if (p.title or "") != (getattr(p, "published_title", None) or ""):
        return True
    if (p.coupon_id or None) != (getattr(p, "published_coupon_id", None) or None):
        return True
    return False


def _live_blocks(page: WxLandingPage) -> list:
    if (page.status or "") == "published" and getattr(page, "published_blocks_json", None):
        return _jloads(page.published_blocks_json, [])
    return _jloads(page.blocks_json, [])


def _live_title(page: WxLandingPage) -> str:
    if (page.status or "") == "published" and getattr(page, "published_title", None):
        return str(page.published_title)
    return str(page.title or "")


def _live_coupon_id(page: WxLandingPage) -> Optional[int]:
    if (page.status or "") == "published":
        cid = getattr(page, "published_coupon_id", None)
        if cid:
            return int(cid)
    if page.coupon_id:
        return int(page.coupon_id)
    return None


def _sync_published_snapshot(row: WxLandingPage) -> None:
    """把编辑区内容推到线上快照（仅发布时调用）。"""
    row.published_blocks_json = row.blocks_json
    row.published_title = row.title
    row.published_coupon_id = row.coupon_id


def list_landing_templates(db: Session) -> list[dict]:
    from infra.i18n import t as _t

    rows = db.query(WxLandingTemplate).order_by(WxLandingTemplate.id).all()
    return [
        {
            "id": row.id,
            "template_key": row.template_key,
            "name": _t(row.name or ""),
            "category": row.category,
            "blocks": _jloads(row.blocks_json, []),
            "is_system": bool(row.is_system),
        }
        for row in rows
    ]


def list_landing_pages(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(WxLandingPage).filter_by(hotel_id=hotel_id).order_by(WxLandingPage.id.desc()).all()
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    welcome_id, member_id, returning_id = _entry_ids(settings)
    return [
        landing_to_dict(
            p,
            is_welcome=(p.id == welcome_id),
            is_member=(p.id == member_id),
            is_returning=(p.id == returning_id),
        )
        for p in rows
    ]


def create_landing_page(db: Session, hotel_id: int, payload: dict) -> dict:
    key = str(payload.get("page_key") or "").strip() or f"page_{secrets.token_hex(3)}"
    if db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key=key).first():
        raise InvalidStateError('"page_key 已存在"')
    role = str(payload.get("page_role") or "claim").strip() or "claim"
    if role not in PAGE_ROLES:
        raise InvalidStateError('"page_role 仅支持 claim / member / returning"')
    blocks = payload.get("blocks")
    tpl_id = payload.get("template_id")
    if not blocks and tpl_id:
        tpl = db.query(WxLandingTemplate).filter_by(template_key=str(tpl_id)).first()
        if tpl:
            blocks = _jloads(tpl.blocks_json, [])
            cat = (tpl.category or "").strip()
            if str(tpl_id) == "tpl_member_center" or cat == "member":
                role = "member"
            elif str(tpl_id) == "tpl_returning" or cat == "returning":
                role = "returning"
    coupon_id = payload.get("coupon_id")
    if coupon_id and role == "claim":
        c = db.query(MktCoupon).filter_by(id=int(coupon_id), hotel_id=hotel_id).first()
        if not c:
            raise InvalidStateError('"绑定的券批次不存在"')
        blocks = blocks or []
        for b in blocks:
            if b.get("type") == "coupon_card":
                b.setdefault("props", {})["coupon_id"] = int(coupon_id)
    allowed = _allowed_blocks_for_role(role)
    blocks = [b for b in (blocks or []) if isinstance(b, dict) and b.get("type") in allowed]
    title_default = {"member": "会员中心", "returning": "老客回访"}.get(role, "领券落地页")
    row = WxLandingPage(
        hotel_id=hotel_id,
        page_key=key,
        title=str(payload.get("title") or title_default),
        template_id=str(tpl_id) if tpl_id else None,
        page_role=role,
        blocks_json=_jdumps(blocks),
        coupon_id=int(coupon_id) if coupon_id and role == "claim" else None,
        status="draft",
        updated_by=str(payload.get("updated_by") or "manager"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return landing_to_dict(row)


def update_landing_page(db: Session, hotel_id: int, page_id: int, payload: dict) -> dict:
    row = db.query(WxLandingPage).filter_by(id=page_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"落地页不存在"')
    if "title" in payload:
        row.title = str(payload.get("title") or row.title)
    if "page_role" in payload:
        role = str(payload.get("page_role") or row.page_role or "claim").strip()
        if role not in PAGE_ROLES:
            raise InvalidStateError('"page_role 仅支持 claim / member / returning"')
        row.page_role = role
    role = (row.page_role or "claim").strip() or "claim"
    if "blocks" in payload:
        allowed = _allowed_blocks_for_role(role)
        blocks = []
        for b in payload.get("blocks") or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") not in allowed:
                continue
            blocks.append(b)
        row.blocks_json = _jdumps(blocks)
    if "coupon_id" in payload and role == "claim":
        cid = payload.get("coupon_id")
        if cid:
            c = db.query(MktCoupon).filter_by(id=int(cid), hotel_id=hotel_id).first()
            if not c:
                raise InvalidStateError('"券批次不存在"')
            row.coupon_id = int(cid)
        else:
            row.coupon_id = None
    row.updated_by = str(payload.get("updated_by") or row.updated_by or "manager")
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    welcome_id, member_id, returning_id = _entry_ids(settings)
    db.commit()
    return landing_to_dict(
        row,
        is_welcome=(row.id == welcome_id),
        is_member=(row.id == member_id),
        is_returning=(row.id == returning_id),
    )


def publish_landing_page(db: Session, hotel_id: int, page_id: int, public_base: str = "") -> dict:
    row = db.query(WxLandingPage).filter_by(id=page_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"落地页不存在"')
    role = (getattr(row, "page_role", None) or "claim").strip() or "claim"
    if role == "claim":
        if not row.coupon_id:
            for b in _jloads(row.blocks_json, []):
                if b.get("type") == "coupon_card" and (b.get("props") or {}).get("coupon_id"):
                    row.coupon_id = int(b["props"]["coupon_id"])
                    break
        if not row.coupon_id:
            raise InvalidStateError('"发布前请绑定券池批次"')
    base = (public_base or "").rstrip("/")
    path = f"/wecom/landing/{row.page_key}"
    _sync_published_snapshot(row)
    row.status = "published"
    row.published_url = f"{base}{path}" if base else path
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    welcome_id, member_id, returning_id = _entry_ids(settings)
    db.commit()
    return landing_to_dict(
        row,
        is_welcome=(row.id == welcome_id),
        is_member=(row.id == member_id),
        is_returning=(row.id == returning_id),
    )


def unpublish_landing_page(db: Session, hotel_id: int, page_id: int) -> dict:
    """下架：改回 draft；若该页是扫码/会员/回访入口则一并清空入口设置。"""
    row = db.query(WxLandingPage).filter_by(id=page_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"落地页不存在"')
    if (row.status or "") != "published":
        raise InvalidStateError('"仅已发布页面可下架"')
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    if settings:
        if settings.welcome_landing_page_id == page_id:
            settings.welcome_landing_page_id = None
        if getattr(settings, "member_landing_page_id", None) == page_id:
            settings.member_landing_page_id = None
        if getattr(settings, "returning_landing_page_id", None) == page_id:
            settings.returning_landing_page_id = None
    row.status = "draft"
    row.published_url = None
    db.commit()
    return landing_to_dict(row, is_welcome=False, is_member=False, is_returning=False)


def get_landing_page(db: Session, hotel_id: int, page_id: int) -> WxLandingPage:
    row = db.query(WxLandingPage).filter_by(id=page_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"落地页不存在"')
    return row


def preview_landing_html(
    db: Session,
    hotel_id: int,
    *,
    page_id: Optional[int] = None,
    payload: Optional[dict] = None,
    demo: bool = True,
) -> str:
    """装修器真预览：可渲染草稿，或用画布未保存的 blocks；会员页默认数据。"""
    from types import SimpleNamespace

    from mkt.mkt_page_render import render_decorated_page

    payload = payload or {}
    if page_id:
        src = get_landing_page(db, hotel_id, page_id)
        role = str(payload.get("page_role") or getattr(src, "page_role", None) or "claim")
        title = str(payload.get("title") or src.title or "预览")
        coupon_id = payload.get("coupon_id") if "coupon_id" in payload else src.coupon_id
        status = src.status or "draft"
        page_key = src.page_key or "preview"
        base_blocks = _jloads(src.blocks_json, [])
    else:
        role = str(payload.get("page_role") or "claim")
        title = str(payload.get("title") or "预览")
        coupon_id = payload.get("coupon_id")
        status = "draft"
        page_key = "preview"
        base_blocks = []

    if role not in PAGE_ROLES:
        role = "claim"
    allowed = _allowed_blocks_for_role(role)
    if "blocks" in payload and payload.get("blocks") is not None:
        blocks = [b for b in (payload.get("blocks") or []) if isinstance(b, dict) and b.get("type") in allowed]
    else:
        blocks = [b for b in base_blocks if isinstance(b, dict) and b.get("type") in allowed]

    row = SimpleNamespace(
        hotel_id=hotel_id,
        page_key=page_key,
        title=title,
        page_role=role,
        blocks_json=_jdumps(blocks),
        coupon_id=int(coupon_id) if coupon_id else None,
        status=status,
    )
    use_demo = bool(demo) if role in ("member", "returning") else False
    return render_decorated_page(
        db,
        row,  # type: ignore[arg-type]
        token="",
        demo=use_demo,
        preview=True,
        blocks_override=blocks,
    )


def get_published_landing(db: Session, page_key: str, hotel_id: Optional[int] = None) -> WxLandingPage:
    q = db.query(WxLandingPage).filter_by(page_key=page_key, status="published")
    if hotel_id:
        q = q.filter_by(hotel_id=hotel_id)
    row = q.order_by(WxLandingPage.id.desc()).first()
    if not row:
        raise NotFoundError('"落地页未发布或不存在"')
    return row


def render_landing_html(db: Session, page: WxLandingPage, token: str = "") -> str:
    """服务端按装修块渲染 H5。正式已发布链接用线上快照，保存草稿不影响客人。

    领券页 + 企微 token：若识别为老客，改为渲染装修器「老客回访」页；
    客人点「进入专属会员中心」后再进会员中心。无回访页时仍渲染领券页并由前端兜底。
    """
    from types import SimpleNamespace

    from mkt.mkt_page_render import render_decorated_page

    render_src = page
    role = (getattr(page, "page_role", None) or "claim").strip() or "claim"
    if token and role == "claim":
        try:
            from application.wecom import _resolve_returning_landing_page_key, get_bind_ticket_public

            info = get_bind_ticket_public(db, token)
            if info.get("mode") == "wallet" or info.get("status") in ("bound", "member"):
                rkey = _resolve_returning_landing_page_key(db, page.hotel_id)
                if rkey:
                    try:
                        render_src = get_published_landing(db, rkey, hotel_id=page.hotel_id)
                    except Exception:
                        render_src = page
        except HTTPException:
            pass
        except Exception:
            pass

    live = (render_src.status or "") == "published"
    view = SimpleNamespace(
        id=render_src.id,
        hotel_id=render_src.hotel_id,
        page_key=render_src.page_key,
        title=_live_title(render_src) if live else (render_src.title or ""),
        page_role=getattr(render_src, "page_role", None) or "claim",
        blocks_json=_jdumps(_live_blocks(render_src)) if live else render_src.blocks_json,
        coupon_id=_live_coupon_id(render_src) if live else render_src.coupon_id,
        published_blocks_json=getattr(render_src, "published_blocks_json", None),
        published_title=getattr(render_src, "published_title", None),
        published_coupon_id=getattr(render_src, "published_coupon_id", None),
        status=render_src.status,
    )
    return render_decorated_page(db, view, token=token)


def _esc(s: Any) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
