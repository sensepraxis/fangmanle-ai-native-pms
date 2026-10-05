# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""装修页块级 H5 渲染（领券页 / 老客回访 / 会员中心）。"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import Guest, Hotel, Order, RoomType, WecomBindTicket, WxLandingPage


def _esc(s: Any) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _sub_guest_name(text: Any, guest_name: str) -> str:
    return str(text or "").replace("{guest_name}", guest_name or "贵宾")


def _jloads(raw: Any, default: Any):
    if not raw:
        return default
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or default)
    except Exception:
        return default


def resolve_member_ctx(db: Session, token: str, hotel_id: int, *, demo: bool = False) -> dict:
    """从企微票据解析会员数据（供数据块渲染）。demo=True 时用数据（装修预览）。"""
    from guests.order_status_labels import ORDER_ST_CN_H5
    from guests.phone_utils import _digits
    from mkt.mkt_service import _normalize_benefits, get_guest_h5_membership, member_bundle
    from mkt.wallet_service import build_member_coupon_wallet
    from models import GuestIdentity

    empty = {
        "ready": False,
        "guest": None,
        "wallet": {
            "coupons": [],
            "unused": [],
            "used": [],
            "expired": [],
            "summary": {"total": 0, "unused": 0, "used": 0, "expired": 0},
        },
        "orders": [],
        "benefits": [],
        "h5": None,
        "message": "请先完成手机号绑定与领券",
    }
    if demo:
        bundle = member_bundle(db, hotel_id)
        preview = bundle.get("h5_preview") or {}
        h5 = {
            "source": "h5_private_domain",
            "labels": {"level": "会员等级", "points": "积分"},
            "level_code": preview.get("level_code") or "gold",
            "level_name": preview.get("level_name") or "金卡",
            "points_balance": int(preview.get("points_balance") or 2680),
            "benefits": _normalize_benefits(preview.get("benefits") or ["房费 95 折", "免费早餐", "延迟退房 2h"]),
            "points_rules": bundle.get("points") or {},
            "progress": {"metric": "nights", "current": 6, "need": 8, "pct": 75, "next_level_name": "白金卡"},
            "hint": "以下为企微私域会员资产，与 PMS 全局会员等级/积分相互独立。",
        }
        return {
            "ready": True,
            "guest": {
                "id": 0,
                "name": "预览客",
                "phone_mask": "138****0000",
                "vip_level": "gold",
                "vip_label": h5["level_name"],
                "ltv": 12800,
                "stay_count": 6,
                "one_id": "ONE-PREVIEW",
                "nickname": "预览客",
            },
            "wallet": {
                "coupons": [],
                "unused": [
                    {
                        "code": "PREVIEW-OK-01",
                        "name": " · 房费7折券",
                        "discount_label": "7折",
                        "channel": "企业微信",
                        "valid_until": "2027-12-31",
                        "can_redeem": True,
                        "status": "active",
                        "redeem_status": "unused",
                    }
                ],
                "used": [
                    {
                        "code": "PREVIEW-USED-01",
                        "name": " · 已核销券",
                        "discount_label": "减50",
                        "channel": "企业微信",
                        "valid_until": "2026-06-30",
                        "can_redeem": False,
                        "status": "used",
                        "redeem_status": "redeemed",
                    }
                ],
                "expired": [
                    {
                        "code": "PREVIEW-EXP-01",
                        "name": " · 已过期券",
                        "discount_label": "8折",
                        "channel": "落地页",
                        "valid_until": "2025-01-01",
                        "can_redeem": False,
                        "status": "expired",
                        "redeem_status": "unused",
                    }
                ],
                "summary": {"total": 3, "unused": 1, "used": 1, "expired": 1},
            },
            "orders": [
                {
                    "order_no": "PV-20260301",
                    "check_in": "2026-03-01",
                    "check_out": "2026-03-03",
                    "nights": 2,
                    "room_type": "高级大床房",
                    "total_amount": 1288,
                    "status": "checked_out",
                    "status_cn": ORDER_ST_CN_H5.get("checked_out", "已离店"),
                }
            ],
            "benefits": h5["benefits"],
            "h5": h5,
            "message": "",
        }
    if not (token or "").strip():
        return empty
    ticket = db.query(WecomBindTicket).filter_by(token=token.strip()).first()
    if not ticket:
        empty["message"] = "链接无效或已失效"
        return empty
    guest_id = ticket.guest_id
    if not guest_id and ticket.external_userid:
        from extensions.messaging.facade import identity_source

        src = identity_source()
        ident = (
            db.query(GuestIdentity)
            .filter_by(source=src, external_id=ticket.external_userid)
            .order_by(GuestIdentity.linked_at.desc())
            .first()
        )
        if ident is None and src != "wecom":
            ident = (
                db.query(GuestIdentity)
                .filter_by(source="wecom", external_id=ticket.external_userid)
                .order_by(GuestIdentity.linked_at.desc())
                .first()
            )
        if ident:
            guest_id = ident.guest_id
    if not guest_id:
        return empty
    guest = db.get(Guest, guest_id)
    if not guest:
        return empty
    phone = _digits(guest.phone)
    phone_mask = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else (guest.phone or "—")
    vip = (guest.vip_level or "normal").strip()
    stay_total = db.query(Order).filter_by(guest_id=guest.id).count()
    wallet = build_member_coupon_wallet(db, guest.id)
    hid = hotel_id or getattr(ticket, "hotel_id", None) or 1
    h5 = get_guest_h5_membership(db, int(hid), guest.id, ensure=True)
    orders = []
    for o in db.query(Order).filter_by(guest_id=guest.id).order_by(Order.check_in.desc()).limit(12).all():
        rt_name = None
        if o.room_type_id:
            rt = db.get(RoomType, o.room_type_id)
            rt_name = rt.name if rt else None
        orders.append(
            {
                "order_no": o.order_no,
                "check_in": str(o.check_in) if o.check_in else None,
                "check_out": str(o.check_out) if o.check_out else None,
                "nights": int(o.nights or 1),
                "room_type": rt_name,
                "total_amount": float(o.total_amount or 0),
                "status": o.status,
                "status_cn": ORDER_ST_CN_H5.get(str(o.status or ""), o.status or "—"),
            }
        )
    return {
        "ready": True,
        "guest": {
            "id": guest.id,
            "name": guest.name,
            "phone_mask": phone_mask,
            "vip_level": vip,
            "vip_label": (h5 or {}).get("level_name") or "会员",
            "ltv": float(guest.ltv or 0),
            "stay_count": stay_total,
            "one_id": guest.one_id,
            "nickname": ticket.nickname or guest.name,
        },
        "wallet": wallet,
        "orders": orders,
        "benefits": (h5 or {}).get("benefits") or [],
        "h5": h5,
        "message": "",
    }


def _render_coupon_items(items: list[dict], kind: str) -> str:
    if not items:
        return ""
    title = {"unused": "可使用", "used": "已核销", "expired": "已过期"}.get(kind, "")
    pill = {"unused": "ok", "used": "used", "expired": "exp"}.get(kind, "")
    label = {"unused": "可使用", "used": "已核销", "expired": "已过期"}.get(kind, "")
    parts = [f'<div class="wallet-sec"><h3>{_esc(title)}</h3>']
    for c in items:
        qr = ""
        if kind == "unused" and c.get("code"):
            qr = (
                '<img class="qr" alt="qr" src="https://api.qrserver.com/v1/create-qr-code/'
                f'?size=120x120&amp;margin=6&amp;data={_esc(c.get("code"))}"/>'
            )
        parts.append(
            f'<div class="w-item {pill}">'
            f"{qr}"
            f'<div class="t">{_esc(c.get("discount_label"))} · {_esc(c.get("name") or "优惠券")} '
            f'<span class="pill {pill}">{label}</span></div>'
            f'<div class="c">券码 {_esc(c.get("code") or "—")}</div>'
            f'<div class="m"><span>{_esc(c.get("channel") or "企业微信")}</span>'
            f"<span>至 {_esc(str(c.get('valid_until') or '—')[:10])}</span></div>"
            f"</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def render_block_html(
    b: dict,
    *,
    ctx: dict,
    coupon: Any,
    coupon_label: str,
    coupon_name: str,
    coupon_desc: str,
    page_role: str,
) -> str:
    typ = b.get("type")
    props = b.get("props") or {}
    tab = props.get("tab") or ""
    tab_attr = f' data-tab="{_esc(tab)}"' if tab else ""
    panel_cls = " panel" if tab else ""

    if typ == "banner":
        guest_name = "贵宾"
        if ctx.get("ready") and isinstance(ctx.get("guest"), dict):
            g = ctx["guest"]
            guest_name = g.get("name") or g.get("nickname") or "贵宾"
        badge = props.get("badge") or (
            "欢迎回来" if page_role == "returning" else ("专属会员中心" if page_role == "member" else "专属管家")
        )
        title = props.get("title") or (
            "{guest_name}，您的私域礼遇"
            if page_role == "returning"
            else ("我的会员中心" if page_role == "member" else "领取优惠券")
        )
        subtitle = props.get("subtitle") or (
            "欢迎回来！以下是您在本店私域领取的全部优惠券" if page_role == "returning" else ""
        )
        return (
            f'<div class="hero{" returning" if page_role == "returning" else ""}">'
            f'<div class="badge">{_esc(badge)}</div>'
            f"<h1>{_esc(_sub_guest_name(title, guest_name))}</h1>"
            f"<p>{_esc(_sub_guest_name(subtitle, guest_name))}</p>"
            f"</div>"
        )
    if typ == "coupon_card":
        return (
            f'<div class="card offer">'
            f'<div class="rate">{_esc(coupon_label)}</div>'
            f'<div class="name">{_esc(coupon_name)}</div>'
            f'<div class="desc">{_esc(coupon_desc)}</div>'
            f"</div>"
        )
    if typ == "form_phone":
        return (
            f'<div class="card" id="formPanel">'
            f'<label for="phone">{_esc(props.get("label") or "手机号")}</label>'
            f'<input id="phone" type="tel" inputmode="numeric" placeholder="{_esc(props.get("placeholder") or "请输入手机号")}" autocomplete="tel"/>'
            f"</div>"
        )
    if typ == "button":
        action = (props.get("action") or "").strip()
        if not action:
            if page_role == "claim":
                action = "submit_bind"
            elif page_role == "returning":
                action = "go_portal"
            else:
                action = "reload"
        text = props.get("text") or (
            "进入专属会员中心" if action == "go_portal" else ("提交并领取" if page_role == "claim" else "刷新")
        )
        if page_role == "claim" and action == "submit_bind":
            return f'<div class="card tight"><button id="btn" type="button">{_esc(text)}</button></div>'
        if action == "go_portal":
            url = ctx.get("portal_url") or "#"
            return f'<div class="card tight"><a class="portal-btn" href="{_esc(url)}">{_esc(text)}</a></div>'
        return f'<div class="card tight"><button type="button" onclick="location.reload()">{_esc(text)}</button></div>'
    if typ == "text" or typ == "cs":
        return f'<p class="tips">{_esc(props.get("text") or "")}</p>'
    if typ == "image":
        src = props.get("src") or ""
        if not src:
            return f'<div class="card"><div class="empty">图片占位 · {_esc(props.get("alt") or "")}</div></div>'
        return f'<div class="card"><img class="img" src="{_esc(src)}" alt="{_esc(props.get("alt") or "")}"/></div>'
    if typ == "countdown":
        return f'<div class="card"><div class="empty">倒计时 · {_esc(props.get("text") or "活动进行中")}</div></div>'

    if typ == "member_header":
        if not ctx.get("ready"):
            return f'<div class="card"><div class="empty">{_esc(ctx.get("message") or "请先完成领券绑定")}</div></div>'
        g = ctx["guest"]
        h5 = ctx.get("h5") or {}
        show_stats = props.get("show_stats", True)
        level_name = h5.get("level_name") or g.get("vip_label") or "会员"
        stats = ""
        if show_stats:
            wsum = (ctx.get("wallet") or {}).get("summary") or {}
            stats = (
                f'<div class="stats three">'
                f'<div class="stat"><div class="n">{int(h5.get("points_balance") or 0)}</div><div class="l">积分</div></div>'
                f'<div class="stat"><div class="n">{int(wsum.get("unused") or 0)}</div><div class="l">可用券</div></div>'
                f'<div class="stat"><div class="n">{int(g.get("stay_count") or 0)}</div><div class="l">入住</div></div>'
                f"</div>"
            )
            prog = h5.get("progress") or {}
            if prog:
                stats += (
                    f'<div class="progress"><div class="p-lab">距{_esc(prog.get("next_level_name") or "下一等级")} '
                    f"{float(prog.get('current') or 0):.0f}/{float(prog.get('need') or 0):.0f}</div>"
                    f'<div class="p-bar"><i style="width:{float(prog.get("pct") or 0)}%"></i></div></div>'
                )
        return (
            f'<div class="card">'
            f'<div class="member">'
            f'<div><p class="name">{_esc(g.get("name") or g.get("nickname") or "贵宾")}</p>'
            f'<p class="meta">手机 {_esc(g.get("phone_mask"))}<br/>OneID {_esc(g.get("one_id") or "—")}</p></div>'
            f'<div class="vip"><div class="lv">{_esc(level_name)}</div>'
            f'<div class="sub">会员等级</div></div></div>{stats}</div>'
        )

    if typ == "nav_tabs":
        tabs = props.get("tabs") or [
            {"key": "coupon", "label": "我的券"},
            {"key": "order", "label": "历史订单"},
            {"key": "benefit", "label": "权益中心"},
        ]
        btns = []
        for i, t in enumerate(tabs):
            on = " on" if i == 0 else ""
            btns.append(
                f'<button type="button" class="tab{on}" data-tab="{_esc(t.get("key"))}" '
                f"onclick=\"showTab('{_esc(t.get('key'))}')\">{_esc(t.get('label') or t.get('key'))}</button>"
            )
        return f'<div class="tabs">{"".join(btns)}</div>'

    if typ == "coupon_wallet":
        title = props.get("title") or "私域优惠券"
        returning_style = page_role == "returning" or props.get("sum_style") == "returning"
        inner = f"<h2>{_esc(title)}</h2>" if not returning_style else ""
        if not ctx.get("ready"):
            inner += f'<div class="empty">{_esc(ctx.get("message") or "暂无数据")}</div>'
        else:
            w = ctx.get("wallet") or {}
            s = w.get("summary") or {}
            if returning_style:
                inner += (
                    f'<p class="sum">私域券共 <strong>{int(s.get("total") or 0)}</strong> 张'
                    f" · 可使用 {int(s.get('unused') or 0)}"
                    f" · 已核销 {int(s.get('used') or 0)} · 已过期 {int(s.get('expired') or 0)}</p>"
                )
                # 老客回访页：简化列表，贴近原 renderWallet
                parts = []
                for kind, items in (
                    ("unused", w.get("unused") or []),
                    ("used", w.get("used") or []),
                    ("expired", w.get("expired") or []),
                ):
                    pill = {"unused": ("ok", "可使用"), "used": ("used", "已核销"), "expired": ("exp", "已过期")}[kind]
                    for c in items:
                        parts.append(
                            f'<div class="w-item {pill[0] if kind == "unused" else "used"}">'
                            f'<div class="t">{_esc(c.get("discount_label") or "")} · '
                            f"{_esc(c.get('name') or '优惠券')} "
                            f'<span class="pill {pill[0]}">{pill[1]}</span></div>'
                            f'<div class="c">券码 {_esc(c.get("code") or "—")}</div></div>'
                        )
                inner += "".join(parts) or '<div class="empty">暂无私域优惠券</div>'
            else:
                inner += (
                    f'<p class="sum">共 {int(s.get("total") or 0)} 张 · 可使用 {int(s.get("unused") or 0)}'
                    f" · 已核销 {int(s.get('used') or 0)} · 已过期 {int(s.get('expired') or 0)}</p>"
                )
                parts = (
                    _render_coupon_items(w.get("unused") or [], "unused")
                    + _render_coupon_items(w.get("used") or [], "used")
                    + _render_coupon_items(w.get("expired") or [], "expired")
                )
                inner += parts or '<div class="empty">暂无私域优惠券</div>'
        hidden = ' style="display:none"' if tab and tab != "coupon" else ""
        # first panel default: if tab set and not coupon, hide; if no tab show always
        if tab:
            on = " on" if tab == "coupon" else ""
            return f'<div class="card{panel_cls}{on}" id="p-{_esc(tab)}"{tab_attr}>{inner}</div>'
        return f'<div class="card"{tab_attr}>{inner}</div>'

    if typ == "order_list":
        title = props.get("title") or "历史订单"
        inner = f"<h2>{_esc(title)}</h2>"
        if not ctx.get("ready"):
            inner += f'<div class="empty">{_esc(ctx.get("message") or "暂无数据")}</div>'
        else:
            orders = ctx.get("orders") or []
            if not orders:
                inner += '<div class="empty">暂无订单记录</div>'
            else:
                for o in orders:
                    amt = float(o.get("total_amount") or 0)
                    inner += (
                        f'<div class="order"><div class="top"><span class="no">{_esc(o.get("order_no"))}</span>'
                        f'<span class="pill">{_esc(o.get("status_cn") or o.get("status"))}</span></div>'
                        f'<div class="dates">{_esc(o.get("check_in") or "—")} ~ {_esc(o.get("check_out") or "—")}</div>'
                        f'<div class="sub">{_esc(o.get("room_type") or "客房")} · {int(o.get("nights") or 1)} 晚 · ¥{amt:,.0f}</div></div>'
                    )
        if tab:
            on = " on" if tab == "order" else ""
            style = "" if tab == "order" else ' style="display:none"'
            return f'<div class="card panel{on}" id="p-{_esc(tab)}"{tab_attr}{style}>{inner}</div>'
        return f'<div class="card">{inner}</div>'

    if typ == "benefit_list":
        title = props.get("title") or "权益中心"
        inner = f"<h2>{_esc(title)}</h2>"
        if not ctx.get("ready"):
            inner += f'<div class="empty">{_esc(ctx.get("message") or "暂无数据")}</div>'
        else:
            h5 = ctx.get("h5") or {}
            benefits = ctx.get("benefits") or h5.get("benefits") or []
            if not benefits:
                inner += '<div class="empty">暂无权益说明</div>'
            else:
                for bft in benefits:
                    inner += (
                        f'<div class="benefit"><div class="dot"></div><div>'
                        f'<p class="t">{_esc(bft.get("title"))}</p>'
                        f'<p class="d">{_esc(bft.get("desc"))}</p></div></div>'
                    )
            pr = h5.get("points_rules") or {}
            if pr:
                inner += (
                    f'<div class="rule-box"><div class="rb-t">积分规则</div>'
                    f'<div class="rb-d">消费 {_esc(pr.get("spend_per_point") or 1)} 元 = 1 分 · '
                    f"签到 +{_esc(pr.get('checkin_bonus') or 0)} · 评价 +{_esc(pr.get('review_bonus') or 0)} · "
                    f"{_esc(pr.get('redeem_points_per_yuan') or 100)} 分抵 1 元</div></div>"
                )
        if tab:
            on = " on" if tab == "benefit" else ""
            style = "" if tab == "benefit" else ' style="display:none"'
            return f'<div class="card panel{on}" id="p-{_esc(tab)}"{tab_attr}{style}>{inner}</div>'
        return f'<div class="card">{inner}</div>'

    return ""


def render_decorated_page(
    db: Session,
    page: WxLandingPage,
    token: str = "",
    *,
    demo: bool = False,
    preview: bool = False,
    blocks_override: list | None = None,
) -> str:
    from mkt.mkt_service import _coupon_label, resolve_landing_coupon

    hotel = db.get(Hotel, page.hotel_id)
    page_role = (getattr(page, "page_role", None) or "claim").strip() or "claim"
    blocks = blocks_override if blocks_override is not None else _jloads(page.blocks_json, [])
    coupon = resolve_landing_coupon(db, page) if page_role == "claim" else None
    offer_name = coupon.name if coupon else "优惠券"
    offer_label = _coupon_label(coupon) if coupon else "礼遇"
    offer_desc = ""
    if coupon:
        if coupon.type == "discount":
            offer_desc = f"本店房费{offer_label}，自领取日起有效"
        elif coupon.type == "reduction":
            offer_desc = f"满{int(float(coupon.threshold or 0))}减{int(float(coupon.face_value or 0))}"
        else:
            offer_desc = coupon.name

    if demo or token or page_role in ("member", "returning"):
        ctx = resolve_member_ctx(db, token, page.hotel_id, demo=demo)
    else:
        ctx = {
            "ready": False,
            "guest": None,
            "wallet": {"summary": {}},
            "orders": [],
            "benefits": [],
            "message": "",
        }

    if page_role in ("member", "returning"):
        try:
            from application.wecom import _portal_url, load_wecom_config

            if token:
                cfg = load_wecom_config(db)
                ctx["portal_url"] = _portal_url(cfg, token, db=db, hotel_id=page.hotel_id)
            elif demo:
                ctx["portal_url"] = f"/wecom/landing/member?hotel_id={int(page.hotel_id)}&demo=1"
        except Exception:
            ctx.setdefault("portal_url", "#")

    # claim 页：装修块包一层，老客进券包时整页隐藏，避免「领券表单 + 券包」叠层
    body_parts = []
    if preview:
        body_parts.append(
            '<div class="preview-banner">预览模式 · 非正式客人链接'
            + (" · 会员数据为" if demo else "")
            + ((" · " + _esc(page.status or "draft")) if getattr(page, "status", None) else "")
            + "</div>"
        )

    decor_parts: list[str] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        html = render_block_html(
            b,
            ctx=ctx,
            coupon=coupon,
            coupon_label=offer_label,
            coupon_name=offer_name,
            coupon_desc=offer_desc,
            page_role=page_role,
        )
        if html:
            decor_parts.append(html)

    if page_role == "claim":
        # 有 token 时先藏装修块，等 bind/info 判定新客/老客，避免老客先闪「填手机号」页
        decor_style = ' style="display:none"' if token else ""
        body_parts.append(f'<div id="decorPanel"{decor_style}>{"".join(decor_parts)}</div>')
        if token:
            body_parts.append('<div id="bootLoading" class="card tight boot-loading">正在识别身份…</div>')
        body_parts.append('<div id="msg" class="msg"></div><div id="couponBox" class="coupon-box"></div>')
        body_parts.append(
            '<div id="walletPanel" style="display:none"></div>'
            '<div id="claimPanel" style="display:none">'
            '<p class="sum" id="claimHint"></p>'
            '<label for="phone2">手机号</label>'
            '<input id="phone2" type="tel" inputmode="numeric" placeholder="请输入手机号"/>'
            '<button id="btnClaim" type="button">领取本页礼遇</button></div>'
        )
    else:
        body_parts.extend(decor_parts)

    token_js = json.dumps(token or "")
    page_key_js = json.dumps(page.page_key)
    coupon_id_js = json.dumps(coupon.id if coupon else None)
    page_role_js = json.dumps(page_role)
    hotel_name = _esc(hotel.name if hotel else "")

    claim_script = ""
    if page_role == "claim":
        claim_script = f"""
<script>
const token = {token_js};
const pageKey = {page_key_js};
const couponId = {coupon_id_js};
const msgEl = document.getElementById('msg');
const btn = document.getElementById('btn');
const phoneEl = document.getElementById('phone');
const couponBox = document.getElementById('couponBox');
function esc(s) {{
  return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function hideBootLoading() {{
  const el = document.getElementById('bootLoading');
  if (el) el.style.display = 'none';
}}
function showDecor() {{
  hideBootLoading();
  const decor = document.getElementById('decorPanel');
  if (decor) decor.style.display = 'block';
}}
function showCoupon(c) {{
  if (!c || !couponBox) return;
  couponBox.style.display = 'block';
  couponBox.innerHTML = '<strong>券码 ' + esc(c.code || '') + '</strong><br/>'
    + esc(c.name || '') + ' · ' + esc(c.discount_label || '') + '<br/>'
    + '有效期至 ' + esc(c.valid_until || c.valid_to || '—');
}}
function itemHtml(c, kind) {{
  const pill = kind === 'unused' ? '<span class="pill ok">可使用</span>'
    : (kind === 'used' ? '<span class="pill used">已核销</span>' : '<span class="pill exp">已过期</span>');
  return '<div class="w-item ' + (kind === 'unused' ? 'ok' : 'used') + '">'
    + '<div class="t">' + esc(c.discount_label || '') + ' · ' + esc(c.name || '优惠券') + ' ' + pill + '</div>'
    + '<div class="c">券码 ' + esc(c.code || '—') + '</div></div>';
}}
function renderWallet(d) {{
  hideBootLoading();
  const decor = document.getElementById('decorPanel');
  if (decor) decor.style.display = 'none';
  const form = document.getElementById('formPanel');
  if (form) form.style.display = 'none';
  if (btn) {{
    btn.style.display = 'none';
    const btnCard = btn.closest('.card');
    if (btnCard) btnCard.style.display = 'none';
  }}
  document.querySelectorAll('.offer').forEach(el => el.style.display = 'none');
  const nick = esc(d.guest_name || d.nickname || '贵宾');
  let html = '<div class="hero returning"><div class="badge">欢迎回来</div>'
    + '<h1>' + nick + '，您的私域礼遇</h1>'
    + '<p>' + esc(d.message || '以下是您在本店已领取的优惠券') + '</p></div>';
  const w = d.wallet || {{}};
  const sum = w.summary || {{}};
  html += '<div class="card"><p class="sum">私域券共 <strong>' + (sum.total || 0) + '</strong> 张'
    + ' · 可使用 ' + (sum.unused || 0) + ' · 已核销 ' + (sum.used || 0)
    + ' · 已过期 ' + (sum.expired || 0) + '</p>';
  (w.unused || []).forEach(c => {{ html += itemHtml(c,'unused'); }});
  (w.used || []).forEach(c => {{ html += itemHtml(c,'used'); }});
  (w.expired || []).forEach(c => {{ html += itemHtml(c,'expired'); }});
  if (!(w.unused || []).length && !(w.used || []).length && !(w.expired || []).length) {{
    html += '<div class="empty">暂无私域优惠券</div>';
  }}
  if (d.portal_url) html += '<a class="portal-btn" href="' + esc(d.portal_url) + '">进入专属会员中心</a>';
  html += '</div>';
  const wp = document.getElementById('walletPanel');
  if (wp) {{ wp.style.display = 'block'; wp.innerHTML = html; }}
  const cp = document.getElementById('claimPanel');
  if (cp) {{
    if (d.can_claim) {{ cp.style.display = 'block'; document.getElementById('claimHint').textContent = d.claim_hint || ''; }}
    else cp.style.display = 'none';
  }}
}}
async function boot() {{
  if (!token) {{ showDecor(); return; }}
  try {{
    const r = await fetch('/api/wecom/bind/info?t=' + encodeURIComponent(token), {{ credentials:'include' }});
    const j = await r.json();
    if (!r.ok) {{ showDecor(); return; }}
    const d = j.data || j;
    // 老客：优先跳装修器「老客回访」页；无回访页 URL 时才用本地券包兜底
    if (d.mode === 'wallet' || d.status === 'bound' || d.status === 'member') {{
      if (d.returning_url) {{ location.replace(d.returning_url); return; }}
      renderWallet(d);
      return;
    }}
    showDecor();
  }} catch (e) {{
    showDecor();
  }}
}}
async function doClaim(phoneInput, button) {{
  if (!phoneInput || !button) return;
  msgEl.textContent = '';
  const phone = (phoneInput.value || '').trim();
  if (!phone) {{ msgEl.className='msg err'; msgEl.textContent='请输入手机号'; return; }}
  button.disabled = true;
  try {{
    const url = token ? '/api/wecom/bind/submit' : '/api/mkt/landing-pages/claim';
    const body = token ? {{ t: token, phone }} : {{ page_key: pageKey, phone, coupon_id: couponId }};
    const r = await fetch(url, {{ method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'include', body: JSON.stringify(body) }});
    const j = await r.json();
    if (!r.ok || j.ok === false) throw new Error(typeof j.detail === 'string' ? j.detail : (j.message || '提交失败'));
    const d = j.data || {{}};
    msgEl.className = 'msg ok';
    msgEl.textContent = d.message || '领取成功';
    if (d.returning_url) setTimeout(function(){{ location.href = d.returning_url; }}, 800);
    else if (d.wallet) renderWallet(Object.assign({{ can_claim:false }}, d));
    else if (d.portal_url) setTimeout(function(){{ location.href = d.portal_url; }}, 1200);
    else showCoupon(d.coupon || d.grant);
  }} catch (e) {{
    msgEl.className = 'msg err';
    msgEl.textContent = e.message || String(e);
    button.disabled = false;
  }}
}}
if (btn && phoneEl) btn.addEventListener('click', () => doClaim(phoneEl, btn));
const btnClaim = document.getElementById('btnClaim');
if (btnClaim) btnClaim.addEventListener('click', () => doClaim(document.getElementById('phone2'), btnClaim));
boot();
</script>
"""

    member_script = """
<script>
function showTab(key) {
  document.querySelectorAll('.tab').forEach(el => {
    el.classList.toggle('on', el.getAttribute('data-tab') === key);
  });
  document.querySelectorAll('.panel').forEach(el => {
    const on = el.id === ('p-' + key);
    el.classList.toggle('on', on);
    el.style.display = on ? 'block' : 'none';
  });
}
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"/>
<title>{_esc(page.title or offer_name)}</title>
<style>
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
    background:linear-gradient(165deg,#0f3d2e 0%,#1a5c45 42%,#f4f7f5 42%,#eef3f0 100%); min-height:100vh; color:#14241c; }}
  .wrap {{ max-width:420px; margin:0 auto; padding:28px 18px 48px; }}
  .hero {{ color:#ecf8f1; margin-bottom:14px; }}
  .hero .badge {{ display:inline-block; font-size:11px; font-weight:700; padding:4px 10px; border-radius:999px; background:rgba(255,255,255,.14); margin-bottom:10px; }}
  .hero h1 {{ font-size:24px; margin:0 0 8px; line-height:1.3; font-weight:750; }}
  .hero p {{ margin:0; font-size:13px; line-height:1.55; opacity:.88; }}
  .hotel {{ font-size:12px; opacity:.75; margin-top:8px; color:#ecf8f1; }}
  .card {{ background:#fff; border-radius:16px; padding:16px; margin-bottom:12px; box-shadow:0 10px 28px rgba(15,61,46,.12); }}
  .card.tight {{ padding:12px 16px; }}
  .card h2 {{ margin:0 0 10px; font-size:15px; }}
  .offer {{ background:linear-gradient(135deg,#ecfdf3,#f0fdf4); border:1px solid #abefc6; }}
  .offer .rate {{ font-size:34px; font-weight:800; color:#099250; line-height:1; }}
  .offer .name {{ font-size:14px; font-weight:700; margin-top:6px; color:#085d3a; }}
  .offer .desc {{ font-size:12px; color:#3f6b56; margin-top:4px; }}
  label {{ display:block; font-size:12px; font-weight:650; color:#475467; margin-bottom:6px; }}
  input {{ width:100%; box-sizing:border-box; padding:12px 14px; border:1px solid #d0d5dd; border-radius:10px; font-size:16px; }}
  button {{ width:100%; margin-top:8px; padding:13px; border:none; border-radius:10px; background:#099250; color:#fff; font-size:15px; font-weight:700; cursor:pointer; }}
  button:disabled {{ opacity:.55; }}
  .msg {{ margin:10px 0; font-size:13px; line-height:1.55; }}
  .ok {{ color:#027a48; }} .err {{ color:#b42318; }}
  .coupon-box {{ margin:8px 0; padding:12px; border-radius:12px; background:#f8fafc; border:1px dashed #cbd5e1; font-size:12px; display:none; }}
  .tips {{ margin:8px 0 0; font-size:11px; color:#667085; line-height:1.5; }}
  .member {{ display:flex; justify-content:space-between; gap:12px; }}
  .name {{ font-size:18px; font-weight:750; margin:0 0 4px; }}
  .meta {{ font-size:12px; color:#667085; margin:0; line-height:1.5; }}
  .vip {{ background:linear-gradient(135deg,#fef7c3,#fef3c7); border:1px solid #fde68a; border-radius:12px; padding:8px 12px; text-align:center; min-width:84px; color:#854d0e; }}
  .vip .lv {{ font-size:13px; font-weight:800; }} .vip .sub {{ font-size:10px; margin-top:2px; }}
  .stats {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:12px; }}
  .stats.three {{ grid-template-columns:1fr 1fr 1fr; }}
  .stats.four {{ grid-template-columns:1fr 1fr 1fr; }}
  .progress {{ margin-top:10px; }}
  .progress .p-lab {{ font-size:11px; color:#667085; margin-bottom:4px; }}
  .progress .p-bar {{ height:6px; background:#eef2f6; border-radius:999px; overflow:hidden; }}
  .progress .p-bar i {{ display:block; height:100%; background:linear-gradient(90deg,#5b6cff,#34d399); border-radius:999px; }}
  .stat {{ background:#f8fafc; border-radius:10px; padding:10px 8px; text-align:center; }}
  .stat .n {{ font-size:15px; font-weight:750; color:#099250; }} .stat .l {{ font-size:11px; color:#667085; margin-top:2px; }}
  .tabs {{ display:flex; gap:6px; margin:0 0 10px; }}
  .tab {{ flex:1; padding:10px 6px; border-radius:10px; border:1px solid #e4e7ec; background:#fff; color:#475467; font-size:12px; font-weight:650; width:auto; margin:0; }}
  .tab.on {{ background:#099250; color:#fff; border-color:#099250; }}
  .panel {{ display:none; }} .panel.on {{ display:block; }}
  .wallet-sec {{ margin-top:10px; }} .wallet-sec h3 {{ margin:0 0 8px; font-size:13px; color:#344054; }}
  .w-item {{ border:1px solid #e4e7ec; border-radius:12px; padding:12px; margin-bottom:8px; background:#fafafa; display:flex; gap:10px; }}
  .w-item.ok {{ border-color:#abefc6; background:#f6fef9; }} .w-item.used {{ opacity:.72; }}
  .w-item .t {{ font-weight:700; font-size:13px; color:#085d3a; }} .w-item .c {{ font-size:12px; color:#475467; margin-top:4px; }}
  .w-item .m {{ font-size:11px; color:#667085; margin-top:4px; display:flex; justify-content:space-between; }}
  .pill {{ display:inline-block; font-size:10px; font-weight:700; padding:2px 8px; border-radius:999px; background:#e4e7ec; }}
  .pill.ok {{ background:#dcfae6; color:#027a48; }} .pill.used {{ background:#f2f4f7; color:#667085; }} .pill.exp {{ background:#fef3f2; color:#b42318; }}
  .sum {{ font-size:12px; color:#475467; margin:0 0 8px; }}
  .order {{ border-top:1px solid #f2f4f7; padding:10px 0; }} .order:first-of-type {{ border-top:none; }}
  .order .top {{ display:flex; justify-content:space-between; gap:8px; }} .order .no {{ font-weight:700; font-size:13px; }}
  .order .dates,.order .sub {{ font-size:12px; color:#667085; margin-top:4px; }}
  .benefit {{ display:flex; gap:10px; padding:10px 0; border-top:1px solid #f2f4f7; }}
  .benefit:first-of-type {{ border-top:none; }} .dot {{ width:8px; height:8px; border-radius:50%; background:#099250; margin-top:6px; flex-shrink:0; }}
  .benefit .t {{ margin:0; font-size:13px; font-weight:700; }} .benefit .d {{ margin:4px 0 0; font-size:12px; color:#667085; }}
  .rule-box {{ margin-top:12px; padding:10px 12px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; }}
  .rule-box .rb-t {{ font-size:12px; font-weight:800; color:#344054; margin-bottom:4px; }}
  .rule-box .rb-d {{ font-size:11px; color:#667085; line-height:1.5; }}
  .empty {{ font-size:13px; color:#667085; padding:8px 0; }}
  .img {{ width:100%; border-radius:10px; display:block; }}
  .qr {{ width:72px; height:72px; border-radius:8px; background:#fff; flex-shrink:0; }}
  .portal-btn {{ display:block; text-align:center; margin-top:12px; padding:12px; border-radius:10px; background:#14241c; color:#fff; font-weight:700; text-decoration:none; font-size:14px; }}
  #claimPanel {{ margin-top:12px; padding:14px; background:#fff; border-radius:16px; }}
  .boot-loading {{ text-align:center; color:#667085; font-size:13px; }}
  .hero.returning {{ margin-bottom:14px; }}
  .preview-banner {{ background:#fef3c7; color:#92400e; font-size:12px; font-weight:700; text-align:center;
    padding:8px 10px; border-radius:10px; margin-bottom:12px; border:1px solid #fde68a; }}
</style>
</head>
<body>
<div class="wrap">
  <p class="hotel">{hotel_name}</p>
  {"".join(body_parts)}
</div>
{claim_script if page_role == "claim" else member_script}
</body>
</html>"""
