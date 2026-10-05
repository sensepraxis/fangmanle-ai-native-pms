# SPDX-License-Identifier: Apache-2.0
"""发券 / 领券 / 核销 / 落地页发券。"""

from __future__ import annotations

import secrets
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from bootstrap.ensure_member_crm import segment_msgid
from domain import InvalidStateError, NotFoundError
from infra.i18n import t as _t
from mkt._mkt_utils import _jdumps, _jloads
from mkt.coupon_batch_service import _coupon_label
from models import (
    Guest,
    GuestCoupon,
    GuestIdentity,
    MktCoupon,
    MktCouponGrant,
    Segment,
    SegmentMember,
    WxLandingPage,
)

CHANNEL_CN = {
    "manual": "手动发码",
    "campaign": "活动绑定",
    "landing_page": "领券落地页",
    "tag": "按客户标签",
    "all": "全员推送",
    "segment": "客群发放",
    "guest": "指定客人",
    "claim": "自助领取",
    "level": "会员等级",
    "wecom": "企微",
    "h5": "H5朋友圈",
}

# 推送型发券：全局客群 ∩ 当前私域通道可达客人
# 不再维护独立私域客群清单


def guest_channel_reachable(db: Session, guest_id: int) -> bool:
    """是否私域可达：当前主 IM（及兼容历史企微身份）已建联。"""
    from extensions.messaging.facade import guest_channel_reachable as _reachable

    return _reachable(db, guest_id)


def guest_private_bound(db: Session, hotel_id: int, guest_id: int) -> bool:
    """推送发券门禁：须私域建联（与客户360私域口径一致）。"""
    return guest_channel_reachable(db, guest_id)


# --- 历史别名（勿在新代码使用）---
def guest_in_wecom_private(db: Session, guest_id: int) -> bool:
    return guest_channel_reachable(db, guest_id)


def _guest_h5_ready(db: Session, hotel_id: int, guest_id: int) -> bool:
    return guest_private_bound(db, hotel_id, guest_id)


def list_grant_segments(db: Session, hotel_id: int) -> list[dict]:
    """发券可选客群 = 全局分群；附带私域可达人数。"""
    from bootstrap.ensure_member_crm import ensure_member_crm

    ensure_member_crm(db, hotel_id)
    segs = db.query(Segment).filter(Segment.hotel_id == hotel_id).order_by(Segment.id.asc()).all()
    if not segs:
        return []
    seg_ids = [s.id for s in segs]
    members_by_seg: dict[int, list[int]] = {sid: [] for sid in seg_ids}
    for sid, gid in (
        db.query(SegmentMember.segment_id, SegmentMember.guest_id).filter(SegmentMember.segment_id.in_(seg_ids)).all()
    ):
        members_by_seg.setdefault(sid, []).append(int(gid))

    # 批量查当前通道私域身份（含历史 wecom 兼容）
    from extensions.messaging.facade import identity_sources_for_reachability, vendor_label

    sources = identity_sources_for_reachability()
    all_gids = {gid for ids in members_by_seg.values() for gid in ids}
    private_ids: set[int] = set()
    if all_gids:
        private_ids = {
            int(r[0])
            for r in db.query(GuestIdentity.guest_id)
            .filter(
                GuestIdentity.guest_id.in_(list(all_gids)),
                GuestIdentity.source.in_(list(sources)),
            )
            .distinct()
            .all()
        }

    out = []
    for s in segs:
        gids = members_by_seg.get(s.id) or []
        reachable = [gid for gid in gids if gid in private_ids]
        total = len(gids)
        reach_n = len(reachable)
        pct = round(reach_n * 100 / total, 1) if total else 0
        msgid = segment_msgid(s)
        out.append(
            {
                "key": str(s.id),
                "segment_id": s.id,
                "label": _t(msgid),
                "name": _t(msgid),
                "desc": _t("全局分群 {n} 人 · {channel}私域可达 {m} 人（{p}%）").format(
                    n=total, m=reach_n, p=pct, channel=vendor_label()
                ),
                "member_count": total,
                "reachable_count": reach_n,
                "unreachable_count": max(0, total - reach_n),
                "reach_pct": pct,
                "rule": s.filter_rule,
            }
        )
    return out


def resolve_grant_segment_guest_ids(db: Session, hotel_id: int, segment: str) -> list[int]:
    """全局分群成员 ∩ 当前私域通道可达客人。"""
    raw = (segment or "").strip()
    if not raw:
        raise InvalidStateError('"请选择客群"')
    try:
        seg_id = int(raw)
    except (TypeError, ValueError):
        raise InvalidStateError('"客群无效，请选择会员中心/客群运营中的全局分群"')
    seg = db.query(Segment).filter_by(id=seg_id, hotel_id=hotel_id).first()
    if not seg:
        raise NotFoundError('"客群不存在"')
    gids = [int(r[0]) for r in db.query(SegmentMember.guest_id).filter(SegmentMember.segment_id == seg_id).all()]
    if not gids:
        return []
    return [gid for gid in gids if guest_channel_reachable(db, gid)]


def preview_grant_audience(
    db: Session,
    hotel_id: int,
    *,
    mode: str,
    segment: Optional[str] = None,
    guest_ids: Optional[list[int]] = None,
) -> dict:
    mode = (mode or "guest").strip()
    segment_count = None
    if mode == "segment":
        raw = (segment or "").strip()
        try:
            seg_id = int(raw)
        except (TypeError, ValueError):
            raise InvalidStateError('"请选择客群"')
        segment_count = db.query(func.count(SegmentMember.id)).filter(SegmentMember.segment_id == seg_id).scalar() or 0
        ids = resolve_grant_segment_guest_ids(db, hotel_id, raw)
    elif mode == "guest":
        ids = []
        for gid in guest_ids or []:
            try:
                gid_i = int(gid)
            except (TypeError, ValueError):
                continue
            if guest_channel_reachable(db, gid_i):
                ids.append(gid_i)
    else:
        raise InvalidStateError('"预览仅支持 guest / segment"')
    samples = []
    for gid in ids[:8]:
        g = db.get(Guest, gid)
        if g:
            samples.append({"guest_id": g.id, "name": g.name, "phone": g.phone_mask or g.phone})
    reach_n = len(ids)
    unreachable = max(0, int(segment_count or 0) - reach_n) if segment_count is not None else None
    return {
        "count": reach_n,
        "guest_ids": ids,
        "samples": samples,
        "segment_count": int(segment_count) if segment_count is not None else None,
        "reachable_count": reach_n,
        "unreachable_count": unreachable,
        "filter": "channel_reachable",
    }


def list_claim_landing_options(db: Session, hotel_id: int, coupon_id: Optional[int] = None) -> list[dict]:
    """自助领取入口：已发布的领券页。"""
    rows = (
        db.query(WxLandingPage).filter_by(hotel_id=hotel_id, status="published").order_by(WxLandingPage.id.desc()).all()
    )
    out = []
    for p in rows:
        role = (getattr(p, "page_role", None) or "claim").strip() or "claim"
        if role != "claim":
            continue
        cid = getattr(p, "published_coupon_id", None) or p.coupon_id
        out.append(
            {
                "id": p.id,
                "page_key": p.page_key,
                "title": p.title or p.page_key,
                "coupon_id": cid,
                "bound": bool(coupon_id and cid and int(cid) == int(coupon_id)),
                "url": p.published_url or f"/wecom/landing/{p.page_key}",
            }
        )
    return out


def bind_coupon_to_claim_landing(db: Session, hotel_id: int, page_id: int, coupon_id: int) -> dict:
    page = db.query(WxLandingPage).filter_by(id=page_id, hotel_id=hotel_id).first()
    if not page:
        raise NotFoundError('"落地页不存在"')
    role = (getattr(page, "page_role", None) or "claim").strip() or "claim"
    if role != "claim":
        raise InvalidStateError('"仅领券页可绑定券批次"')
    coupon = db.query(MktCoupon).filter_by(id=coupon_id, hotel_id=hotel_id).first()
    if not coupon:
        raise NotFoundError('"券批次不存在"')
    if coupon.status != "active":
        raise InvalidStateError('"请先投放（active）该券批次"')
    page.coupon_id = coupon_id
    page.page_role = "claim"
    # 已发布页同步线上快照，客人立刻可领
    if (page.status or "") == "published":
        page.published_coupon_id = coupon_id
        blocks = _jloads(page.blocks_json, [])
        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "coupon_card":
                b.setdefault("props", {})["coupon_id"] = coupon_id
        page.blocks_json = _jdumps(blocks)
        if getattr(page, "published_blocks_json", None) is not None:
            pub_blocks = _jloads(page.published_blocks_json, []) or blocks
            for b in pub_blocks:
                if isinstance(b, dict) and b.get("type") == "coupon_card":
                    b.setdefault("props", {})["coupon_id"] = coupon_id
            page.published_blocks_json = _jdumps(pub_blocks)
    db.commit()
    return {
        "ok": True,
        "page_id": page.id,
        "page_key": page.page_key,
        "coupon_id": coupon_id,
        "url": page.published_url or f"/wecom/landing/{page.page_key}",
    }


def list_grants(db: Session, hotel_id: int, coupon_id: Optional[int] = None) -> list[dict]:
    q = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id)
    if coupon_id:
        q = q.filter_by(coupon_id=coupon_id)
    out = []
    for g in q.order_by(MktCouponGrant.id.desc()).limit(200).all():
        c = db.get(MktCoupon, g.coupon_id)
        guest = db.get(Guest, g.guest_id)
        phone = ""
        if guest and getattr(guest, "phone", None):
            p = str(guest.phone)
            phone = f"{p[:3]}****{p[-4:]}" if len(p) >= 7 else p
        used_amount = None
        st = (g.status or "").upper()
        if st in ("USED", "used") and c:
            from mkt.mkt_coupon_engine import normalize_instance_status, resolve_batch_benefit_fields

            fields = resolve_batch_benefit_fields(c)
            if fields["coupon_type"] in ("CASH_ROOM", "CASH_ALL"):
                used_amount = float(fields["reduce_amount"] or 0)
            elif getattr(g, "used_amount", None) is not None:
                used_amount = float(g.used_amount)
        from mkt.mkt_coupon_engine import instance_to_dict, normalize_instance_status

        item = instance_to_dict(g, c)
        out.append(
            {
                "id": g.id,
                "code": g.code,
                "coupon_code": g.code,
                "coupon_id": g.coupon_id,
                "coupon_name": c.name if c else "",
                "batch_no": c.batch_no if c else "",
                "discount_label": _coupon_label(c) if c else "",
                "face_text": item.get("face_text"),
                "guest_id": g.guest_id,
                "guest_name": guest.name if guest else "",
                "guest_phone": phone,
                "grant_channel": g.grant_channel,
                "grant_event": getattr(g, "grant_event", None),
                "grant_channel_label": CHANNEL_CN.get(g.grant_channel or "", g.grant_channel or ""),
                "grant_at": g.grant_at.isoformat() if g.grant_at else None,
                "used_at": g.used_at.isoformat() if g.used_at else None,
                "used_order_id": g.used_order_id,
                "used_amount": used_amount if used_amount is not None else item.get("used_amount"),
                "status": normalize_instance_status(g.status),
                "valid_from": item.get("valid_from"),
                "valid_to": item.get("valid_to"),
            }
        )
    return out


def grant_coupon(
    db: Session,
    hotel_id: int,
    coupon_id: int,
    *,
    guest_ids: Optional[list[int]] = None,
    channel: str = "manual",
    mode: str = "guest",
    segment: Optional[str] = None,
    require_h5: bool = True,
    grant_event: str = "manual",
    auto_claim: bool = True,
    allow_over_limit: bool = False,
    over_limit_reason: Optional[str] = None,
) -> dict:
    """推送发券：指定客人或客群。自助领取不走此接口。

    allow_over_limit：补偿强制发（可超每人限领），须带 over_limit_reason。
    """
    from mkt.mkt_coupon_engine import guest_batch_ownership, issue_instance

    coupon = db.query(MktCoupon).filter_by(id=coupon_id, hotel_id=hotel_id).first()
    if not coupon:
        raise NotFoundError('"券批次不存在"')
    if coupon.status != "active":
        raise InvalidStateError('"仅 active 批次可发放"')

    allow_over_limit = bool(allow_over_limit)
    reason = (over_limit_reason or "").strip()
    if allow_over_limit and not reason:
        raise InvalidStateError('"补偿强制发放须填写原因"')

    mode = (mode or "guest").strip()
    if mode == "segment":
        if allow_over_limit:
            raise InvalidStateError('"按客群发放不支持补偿超限，请用指定客人发放"')
        target_ids = resolve_grant_segment_guest_ids(db, hotel_id, str(segment or ""))
        channel = channel if channel and channel != "manual" else "segment"
        require_h5 = False
    elif mode == "guest":
        target_ids = []
        for x in guest_ids or []:
            try:
                target_ids.append(int(x))
            except (TypeError, ValueError):
                continue
        target_ids = [gid for gid in target_ids if guest_channel_reachable(db, gid)]
        channel = channel if channel and channel != "manual" else "guest"
        require_h5 = False
    else:
        raise InvalidStateError('"发放模式仅支持 guest / segment（自助领取请配置落地页）"')

    if not target_ids:
        raise InvalidStateError('"没有可发放的客人：请检查全局客群与企微私域交集，或勾选已建联客人"')

    ok_n = 0
    skip = 0
    skipped_already = 0
    skipped_no_h5 = 0
    compensated = 0
    created = []
    for gid in target_ids:
        guest = db.get(Guest, gid)
        if not guest:
            skip += 1
            continue
        if require_h5 and not guest_private_bound(db, hotel_id, gid):
            skipped_no_h5 += 1
            skip += 1
            continue
        own = guest_batch_ownership(db, coupon, gid)
        if own["at_limit"] and not allow_over_limit:
            skipped_already += 1
            skip += 1
            continue
        try:
            g = issue_instance(
                db,
                coupon,
                gid,
                grant_event=grant_event,
                grant_channel=channel,
                auto_claim=auto_claim,
                allow_over_limit=allow_over_limit and own["at_limit"],
                over_limit_reason=reason if allow_over_limit else None,
                raise_on_limit=True,
            )
            ok_n += 1
            created.append(g.code)
            if allow_over_limit and own["at_limit"]:
                compensated += 1
        except HTTPException as e:
            detail = str(e.detail or "")
            if "限领" in detail:
                skipped_already += 1
                skip += 1
                continue
            if "发完" in detail:
                raise InvalidStateError('f"券已发完（成功 {ok_n} 张后库存不足）"')
            raise
    db.commit()
    return {
        "granted": ok_n,
        "skipped": skip,
        "skipped_already": skipped_already,
        "skipped_no_h5": skipped_no_h5,
        "compensated": compensated,
        "codes": created,
        "mode": mode,
        "segment": segment,
        "target_count": len(target_ids),
        "allow_over_limit": allow_over_limit,
    }


def list_coupon_guest_ownership(
    db: Session,
    hotel_id: int,
    coupon_id: int,
    guest_ids: Optional[list[int]] = None,
) -> dict:
    """查询一批客人对某券批次的持有/限领状态（指定发放 UI 用）。"""
    from mkt.mkt_coupon_engine import guest_batch_ownership

    coupon = db.query(MktCoupon).filter_by(id=coupon_id, hotel_id=hotel_id).first()
    if not coupon:
        raise NotFoundError('"券批次不存在"')
    ids: list[int] = []
    if guest_ids:
        for x in guest_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
    else:
        # 默认：当前私域通道已建联客人
        from extensions.messaging.facade import identity_source
        from models import GuestIdentity

        src = identity_source()
        ids = [int(r[0]) for r in db.query(GuestIdentity.guest_id).filter(GuestIdentity.source == src).distinct().all()]
        if src != "wecom":
            ids = list(
                {
                    *ids,
                    *[
                        int(r[0])
                        for r in db.query(GuestIdentity.guest_id)
                        .filter(GuestIdentity.source == "wecom")
                        .distinct()
                        .all()
                    ],
                }
            )
        # 再过滤有本店订单或钱包的（与 mktCustomers 大致一致）
        ids = [gid for gid in ids if guest_channel_reachable(db, gid)]

    per = max(1, int(coupon.per_user_qty or 1))
    items = []
    at_limit_n = 0
    for gid in ids:
        info = guest_batch_ownership(db, coupon, gid)
        items.append(info)
        if info["at_limit"]:
            at_limit_n += 1
    return {
        "coupon_id": coupon.id,
        "batch_no": coupon.batch_no,
        "name": coupon.name,
        "per_user_qty": per,
        "guest_count": len(items),
        "at_limit_count": at_limit_n,
        "grantable_count": len(items) - at_limit_n,
        "items": items,
    }


def verify_coupon(db: Session, hotel_id: int, code: str, order_id: Optional[int] = None) -> dict:
    from mkt.mkt_coupon_engine import redeem_instance

    return redeem_instance(
        db,
        hotel_id,
        code=code,
        order_id=int(order_id) if order_id else None,
        cashier="mkt_verify",
    )


def resolve_landing_coupon(db: Session, page: Any, *, live: bool = False) -> Optional[MktCoupon]:
    """live=True 读线上快照（客人正式链接）；否则读编辑区工作稿。"""
    from mkt.landing_service import _live_blocks, _live_coupon_id

    if live:
        cid = _live_coupon_id(page)
        if cid:
            return db.get(MktCoupon, cid)
        for b in _live_blocks(page):
            if b.get("type") == "coupon_card":
                c2 = (b.get("props") or {}).get("coupon_id")
                if c2:
                    return db.get(MktCoupon, int(c2))
        return None
    if getattr(page, "coupon_id", None):
        return db.get(MktCoupon, page.coupon_id)
    for b in _jloads(getattr(page, "blocks_json", None), []):
        if b.get("type") == "coupon_card":
            cid = (b.get("props") or {}).get("coupon_id")
            if cid:
                return db.get(MktCoupon, int(cid))
    return None


def grant_from_landing(db: Session, hotel_id: int, guest_id: int, coupon: MktCoupon) -> MktCouponGrant:
    """落地页/扫码领券：写实例 + GuestCoupon 投影。"""
    from mkt.mkt_coupon_engine import issue_instance

    return issue_instance(
        db,
        coupon,
        guest_id,
        grant_event="manual",
        grant_channel="landing_page",
        auto_claim=True,
    )


def _ensure_guest_coupon_from_mkt(
    db: Session,
    hotel_id: int,
    guest_id: int,
    coupon: MktCoupon,
    grant: MktCouponGrant,
) -> Optional["GuestCoupon"]:
    from mkt.mkt_coupon_engine import _project_guest_coupon

    return _project_guest_coupon(db, hotel_id, guest_id, coupon, grant)


def mkt_grant_to_public_coupon(db: Session, grant: MktCouponGrant) -> Optional[dict]:
    """H5 成功态：优先返回 GuestCoupon 公共结构，并补全批次文案标签。"""
    from mkt.wallet_service import _coupon_to_public

    coupon = db.get(MktCoupon, grant.coupon_id)
    label = _coupon_label(coupon) if coupon else ""
    gc = db.query(GuestCoupon).filter_by(code=grant.code).first()
    if gc:
        guest = db.get(Guest, gc.guest_id)
        pub = _coupon_to_public(gc, guest=guest)
        if label:
            pub["discount_label"] = label
        if coupon and coupon.name:
            pub["name"] = coupon.name
        return pub
    return {
        "id": grant.id,
        "code": grant.code,
        "name": coupon.name if coupon else "优惠券",
        "discount_label": label or "优惠券",
        "valid_until": coupon.valid_to.isoformat(sep=" ", timespec="seconds") if coupon and coupon.valid_to else None,
        "valid_to": coupon.valid_to.isoformat(sep=" ", timespec="seconds") if coupon and coupon.valid_to else None,
        "status": grant.status,
        "source": f"mkt_{grant.coupon_id}",
    }


def public_claim_without_token(db: Session, hotel_id: int, page_key: str, phone: str) -> dict:
    """无企微票据时的领券（装修器预览/分享链接）。"""
    from guests.phone_utils import _digits
    from mkt.landing_service import get_published_landing

    page = get_published_landing(db, page_key, hotel_id=hotel_id)
    coupon = resolve_landing_coupon(db, page, live=True)
    if not coupon:
        raise InvalidStateError('"落地页未绑定券批次"')
    digits = _digits(phone)
    if len(digits) < 11:
        raise InvalidStateError('"请输入有效手机号"')
    # 简化：按脱敏尾号找客，否则新建客
    guest = db.query(Guest).filter(Guest.phone_mask.isnot(None), Guest.phone_mask.contains(digits[-4:])).first()
    if not guest:
        guest = Guest(
            one_id=f"MKT-{secrets.token_hex(4).upper()}",
            name=f"领券客…{digits[-4:]}",
            phone_mask=f"{digits[:3]}****{digits[-4:]}",
        )
        db.add(guest)
        db.flush()
    grant = grant_from_landing(db, hotel_id, guest.id, coupon)
    db.commit()
    pub = mkt_grant_to_public_coupon(db, grant) or {
        "code": grant.code,
        "name": coupon.name,
        "discount_label": _coupon_label(coupon),
        "valid_until": coupon.valid_to.isoformat() if coupon.valid_to else None,
        "valid_to": coupon.valid_to.isoformat() if coupon.valid_to else None,
    }
    return {
        "ok": True,
        "message": "您已完成领取，可关闭此页",
        "guest_id": guest.id,
        "grant": pub,
        "coupon": pub,
    }
