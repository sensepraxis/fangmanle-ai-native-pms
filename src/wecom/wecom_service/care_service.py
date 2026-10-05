# SPDX-License-Identifier: Apache-2.0
"""企业微信客户联系：配置、同步外部联系人、一对一消息任务。"""

from __future__ import annotations

import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from bootstrap.ensure_wecom import DEFAULT_WECOM_CONFIG, WECOM_SETTING_KEY
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from guests.i18n_cn import source_cn
from guests.phone_utils import (
    _digits,
    _normalize_cn_mobile,
    _normalize_phone_storage,
    _phone_last4,
    _phone_last6,
    find_guests_by_phone_exact,
    find_guests_by_phone_last4,
    find_guests_by_phone_last6,
)
from infra.branding import brand_text
from infra.i18n import t
from mkt.wallet_service import (
    _coupon_offer_public,
    _coupon_to_public,
    _is_private_domain_coupon,
    build_member_coupon_wallet,
    list_guest_coupons,
    lookup_coupon_by_code,
    redeem_guest_coupon,
)
from models import (
    AppSetting,
    Guest,
    GuestCoupon,
    GuestIdentity,
    GuestTag,
    Hotel,
    MktCouponGrant,
    OneIdMergeEvent,
    OneIdPhoneConflict,
    Order,
    Review,
    RoomType,
    TagDefinition,
    WecomBindTicket,
    WecomCallbackEvent,
    WecomMsgTask,
)

QYAPI = "https://qyapi.weixin.qq.com/cgi-bin"
VIP_LABEL_CN: dict[str, str] = {
    "normal": "普通会员",
    "silver": "白银会员",
    "gold": "黄金会员",
    "platinum": "铂金会员",
    "普通": "普通会员",
}
ROOM_PREF_RE = re.compile(
    "安静|静音|无烟|高楼|高层|低楼|低层|景观|山景|江景|海景|枕头|乳胶|硬枕|软枕|荞麦|矿泉水|夜床|开夜床|管家|亲子|家庭|儿童|加床|无障碍"
)
MARKETING_TAG_RE = re.compile("抖音|小红书|种草|粉丝|直播|投放|获客")


def _vip_label(level: str | None) -> str:
    raw = (level or "normal").strip().lower()
    return t(VIP_LABEL_CN.get(raw, raw or "普通会员"))


def _birthday_window_label(bday: date | None, today: date | None = None) -> str | None:
    if not bday:
        return None
    today = today or date.today()
    try:
        next_b = bday.replace(year=today.year)
    except ValueError:
        next_b = date(today.year, bday.month, 28)
    if next_b < today:
        try:
            next_b = bday.replace(year=today.year + 1)
        except ValueError:
            next_b = date(today.year + 1, bday.month, 28)
    days = (next_b - today).days
    if days <= 30:
        return t("{month}月{day}日前后", month=bday.month, day=bday.day)
    return None


def _order_brief(db: Session, order: Order) -> dict:
    rt_name = None
    if order.room_type_id:
        rt = db.get(RoomType, order.room_type_id)
        rt_name = rt.name if rt else None
    nights = order.nights
    if not nights and order.check_in and order.check_out:
        nights = max(1, (order.check_out - order.check_in).days)
    return {
        "check_in": str(order.check_in) if order.check_in else None,
        "check_out": str(order.check_out) if order.check_out else None,
        "nights": int(nights or 1),
        "room_type": rt_name,
        "status": str(order.status or ""),
    }


def build_guest_care_profile(db: Session, guest_id: int) -> dict:
    """组装关怀话术可用的 PMS 客人画像（有则写入、无则省略）。"""
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")
    tag_rows = (
        db.query(GuestTag, TagDefinition.name, TagDefinition.category)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id == guest_id)
        .all()
    )
    room_preferences: list[str] = []
    persona_tags: list[str] = []
    for _gt, name, category in tag_rows:
        n = str(name or "").strip()
        if not n or MARKETING_TAG_RE.search(n):
            continue
        if ROOM_PREF_RE.search(n):
            if n not in room_preferences:
                room_preferences.append(n)
        elif str(category or "") == "画像" or category in ("偏好", "行为"):
            if n not in persona_tags:
                persona_tags.append(n)
    orders = db.query(Order).filter_by(guest_id=guest_id).order_by(Order.check_in.desc()).all()
    stay_count = len(orders)
    upcoming = next((o for o in orders if str(o.status or "") in ("pending", "confirmed", "checked_in")), None)
    last_stayed = next((o for o in orders if str(o.status or "") == "checked_out"), None)
    active_coupons: list[dict] = []
    for c in list_guest_coupons(db, guest_id):
        if str(c.get("status") or "") == "active":
            active_coupons.append(
                {
                    "name": c.get("name"),
                    "discount_label": c.get("discount_label"),
                    "valid_until": str(c.get("valid_until") or "")[:10] or None,
                }
            )
    reviews = db.query(Review).filter_by(guest_id=guest_id).order_by(Review.created_at.desc()).limit(5).all()
    review_sentiment = None
    if reviews:
        avg = sum(float(r.rating or 0) for r in reviews) / len(reviews)
        if avg >= 4:
            review_sentiment = t("正面")
        elif avg >= 3:
            review_sentiment = t("中性")
        else:
            review_sentiment = t("需关怀")
    idents = db.query(GuestIdentity).filter_by(guest_id=guest_id).all()
    channels: list[str] = []
    for ident in idents:
        src = source_cn(ident.source)
        if src and src not in channels:
            channels.append(src)
    vip_raw = (guest.vip_level or "").strip().lower()
    ltv = float(guest.ltv or 0)
    churn = float(guest.churn_risk) if guest.churn_risk is not None else None
    bday_label = _birthday_window_label(guest.birthday)
    member: dict[str, Any] = {}
    if vip_raw and vip_raw not in ("normal", "普通"):
        member["vip_level"] = guest.vip_level
        member["vip_label"] = _vip_label(guest.vip_level)
    if guest.city:
        member["city"] = guest.city
    if ltv > 0:
        member["ltv"] = round(ltv, 0)
    if stay_count > 0:
        member["stay_count"] = stay_count
    if churn is not None:
        member["churn_risk_pct"] = round(churn * 100)
    if bday_label:
        member["birthday_window"] = bday_label
    profile: dict[str, Any] = {
        "has_profile": False,
        "member": member or None,
        "room_preferences": room_preferences[:5] or None,
        "persona_tags": persona_tags[:5] or None,
        "upcoming_stay": _order_brief(db, upcoming) if upcoming else None,
        "last_stay": _order_brief(db, last_stayed) if last_stayed else None,
        "coupons": active_coupons[:3] or None,
        "review_sentiment": review_sentiment,
        "channels": channels[:4] or None,
    }
    profile["has_profile"] = bool(
        member
        or profile["room_preferences"]
        or profile["persona_tags"]
        or profile["upcoming_stay"]
        or profile["last_stay"]
        or profile["coupons"]
        or review_sentiment
    )
    return profile


def format_profile_for_prompt(profile: dict) -> str:
    """将画像转为 LLM 可读文本块。"""
    from infra.i18n import get_locale

    wants_en = str(get_locale() or "").lower().startswith("en")
    if not profile.get("has_profile"):
        return "has_profile: false\n" + t("该客人暂无足够 PMS 画像数据，请勿引用会员/订单/偏好等未提供信息")
    joiner = ", " if wants_en else "，"
    list_join = ", " if wants_en else "、"
    lines = ["has_profile: true"]
    member = profile.get("member") or {}
    member_bits: list[str] = []
    if member.get("vip_label"):
        member_bits.append(str(member["vip_label"]))
    if member.get("ltv"):
        member_bits.append(t("累计消费 ¥{amt}", amt=int(member["ltv"])))
    if member.get("stay_count"):
        member_bits.append(t("{n} 次入住", n=member["stay_count"]))
    if member.get("city"):
        member_bits.append(t("常住城市 {city}", city=member["city"]))
    if member.get("churn_risk_pct") is not None:
        risk = member["churn_risk_pct"]
        member_bits.append(t("流失风险低") if risk < 35 else t("流失风险中") if risk < 65 else t("流失风险偏高"))
    if member.get("birthday_window"):
        member_bits.append(t("生日窗口 {window}", window=member["birthday_window"]))
    if member_bits:
        lines.append(t("会员：{bits}", bits=joiner.join(member_bits)))
    upcoming = profile.get("upcoming_stay")
    if upcoming and upcoming.get("check_in"):
        seg = t("即将入住：{date}", date=upcoming["check_in"])
        if upcoming.get("check_out"):
            seg += t(" 至 {date}", date=upcoming["check_out"])
        if upcoming.get("nights"):
            seg += t("（{n} 晚）", n=upcoming["nights"])
        if upcoming.get("room_type"):
            seg += t("，房型 {room}", room=upcoming["room_type"])
        lines.append(seg)
    last = profile.get("last_stay")
    if last and last.get("check_in") and (not upcoming):
        seg = t("最近入住：{date}", date=last["check_in"])
        if last.get("check_out"):
            seg += t(" 至 {date}", date=last["check_out"])
        lines.append(seg)
    coupons = profile.get("coupons") or []
    if coupons:
        c_parts = []
        for c in coupons:
            label = c.get("discount_label") or c.get("name") or t("优惠券")
            until = c.get("valid_until")
            c_parts.append(f"{label}" + (t("（至 {until}）", until=until) if until else ""))
        lines.append(t("有效券：{items}", items=("; " if wants_en else "；").join(c_parts)))
    prefs = profile.get("room_preferences") or []
    if prefs:
        lines.append(t("客房偏好：{items}", items=list_join.join(prefs)))
    persona = profile.get("persona_tags") or []
    if persona:
        lines.append(t("画像标签：{items}", items=list_join.join(persona)))
    if profile.get("review_sentiment"):
        lines.append(t("历史点评情感：{sent}", sent=profile["review_sentiment"]))
    return "\n".join(lines)


def build_profile_summary(profile: dict) -> str:
    """供前端展示：本次 AI 参考了哪些画像维度。"""
    if not profile.get("has_profile"):
        return ""
    bits: list[str] = []
    member = profile.get("member") or {}
    if member.get("vip_label"):
        bits.append(str(member["vip_label"]))
    if member.get("stay_count"):
        bits.append(t("{n} 次入住", n=member["stay_count"]))
    if profile.get("upcoming_stay"):
        bits.append(t("即将入住"))
    if profile.get("room_preferences"):
        bits.append(t("客房偏好"))
    if profile.get("coupons"):
        bits.append(t("有效券"))
    if profile.get("persona_tags"):
        bits.append(t("画像标签"))
    return " · ".join(bits[:5])


def _build_care_template(salutation: str, material_text: str, profile: dict) -> str:
    """LLM 不可用时的智能模板兜底。"""
    from infra.i18n import get_locale

    wants_en = str(get_locale() or "").lower().startswith("en")
    parts = [t("{salutation}，我是本店专属管家 {name}。", salutation=salutation, name="WangWeiWei")]
    upcoming = profile.get("upcoming_stay")
    if upcoming and upcoming.get("check_in"):
        seg = t("看到您预订了 {check_in} 入住", check_in=upcoming["check_in"])
        if upcoming.get("check_out"):
            seg += t(" 至 {date}", date=upcoming["check_out"])
        parts.append(seg + (". " if wants_en else "，"))
    coupons = profile.get("coupons") or []
    if coupons:
        c0 = coupons[0]
        name = c0.get("name") or t("专属优惠")
        until = c0.get("valid_until")
        if until:
            parts.append(t("您账户里的{name}（有效至 {until}）仍可使用。", name=name, until=until))
        else:
            parts.append(t("您账户里的{name}仍可使用。", name=name))
    prefs = profile.get("room_preferences") or []
    if prefs:
        parts.append(t("会按您偏好的「{pref}」提前安排。", pref=prefs[0]))
    punct = "." if wants_en else "。"
    parts.append(material_text.rstrip("。，.! ") + punct)
    parts.append(t("如有房型偏好或到店时间，可直接回复我，我会为您提前安排。"))
    text = " ".join(p.strip() for p in parts if str(p).strip()) if wants_en else "".join(parts)
    return text.replace("。，", "，").replace("，。", "。")


_CARE_SYSTEM_PROMPT = brand_text("""你是「{APP_NAME}」酒店私域管家，负责企微 1:1 关怀话术。
要求：
1. 开头必须使用用户消息中给出的指定称呼。
2. 人工素材必须自然体现，不得忽略、不得改写成无关主题。
3. 客人画像仅作参考，禁止编造订单号、金额、券码、房型库存。
4. 自称本店专属管家，口吻亲切、短句、可直接发送；不要 Markdown、不要解释、不要标题。
5. 全文不超过 400 字。用户可见文案须与请求语言一致。
""")


def draft_wecom_care_message(db: Session, guest_id: int, material: str = "") -> dict:
    """根据人工素材 + PMS 客人画像生成企微关怀话术（优先 LLM，失败则模板）。"""
    # lazy cross-import 避开循环
    from infra.commercial_pack import load_module
    from infra.i18n import get_locale
    from wecom.wecom_service import _common as _wecom_common
    from wecom.wecom_service import portal_service as _wecom_portal_service

    wants_en = str(get_locale() or "").lower().startswith("en")
    locale_mod = load_module("commercial.ai_core.locale_llm")
    pack_mod = load_module("commercial.ai_core.prompt_packs")
    if locale_mod:
        wants_en = locale_mod.wants_en()
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")
    wecom = _wecom_portal_service.guest_wecom_summary(db, guest_id)
    profile = build_guest_care_profile(db, guest_id)
    profile_text = format_profile_for_prompt(profile)
    profile_summary = build_profile_summary(profile)
    salutation = _wecom_common._care_salutation(guest)
    material_text = (material or "").strip()
    if not material_text:
        raise ValidationError("请先填写关怀素材")
    template = _build_care_template(salutation, material_text, profile)
    scene = (pack_mod.get_scene_prompt("wecom", "care") if pack_mod else None) or _CARE_SYSTEM_PROMPT
    if locale_mod:
        system_hint = locale_mod.compose_system(scene)
        cjk_re = locale_mod.CJK_RE
    else:
        system_hint = scene
        cjk_re = None
    if wants_en:
        user_prompt = (
            f"[Must include this brief]\n{material_text}\n\n"
            f"[Required greeting — start with this]\n{salutation}\n\n"
            f"[Guest profile — reference only; do not invent ids, amounts, or coupon codes]\n{profile_text}\n\n"
            "[Output]\nWrite one WeCom 1:1 care message. Body only, no explanation. "
            "English except proper nouns (guest name, room type names). "
            f"\n\n[Rule draft as material only — rewrite, do not copy]\n{template}"
        )
    else:
        user_prompt = (
            f"【人工素材（必须体现）】\n{material_text}\n\n"
            f"【指定称呼（开头必须使用）】\n{salutation}\n\n"
            f"【客人画像（仅供参考）】\n{profile_text}\n\n"
            f"【规则草稿·仅素材，须重写】\n{template}\n\n"
            f"【输出】\n生成一条可直接发送到企微 1:1 会话的关怀消息。只输出正文，不要解释。"
        )
    source = "unavailable"
    content = ""
    llm_note = None
    identity: dict = {}
    try:
        import re as _re

        from extensions.llm.facade import chat as llm_chat
        from extensions.llm.facade import llm_identity, load_llm_config

        cfg = load_llm_config(db)
        identity = llm_identity(cfg)
        if cfg.get("enabled", True):
            out = llm_chat(db, [{"role": "user", "content": user_prompt}], system_hint)
            raw_out = str((out.get("content") or out.get("reply") or "") if isinstance(out, dict) else out)
            text = _re.sub(r"<think>[\s\S]*?</think>", "", raw_out, flags=_re.I).strip()
            if text:
                clipped = text[:600]
                if wants_en and cjk_re is not None and cjk_re.search(clipped):
                    llm_note = t("模型输出语言不符")
                else:
                    content = clipped
                    source = "llm"
                    identity = llm_identity(cfg, out if isinstance(out, dict) else None)
    except Exception as e:
        llm_note = str(e)[:120]
    hint = (
        t("确认话术后点击「发送到当前会话」即可直发（不走群发助手）。")
        if wecom and wecom.get("bound")
        else t("该客人尚未绑定企微，无法真正推送。")
    )
    if profile_summary:
        hint = t("本次已参考画像：{summary}。{hint}", summary=profile_summary, hint=hint)
    if source != "llm":
        identity = {}
    return {
        "guest_id": guest_id,
        "guest_name": guest.name,
        "phone_last4": _phone_last4(guest.phone),
        "salutation": salutation,
        "material": material_text,
        "content": content,
        "source": source,
        "source_cn": t("AI 生成") if source == "llm" else t("未能调用大模型"),
        "profile_used": bool(profile.get("has_profile")),
        "profile_summary": profile_summary or None,
        "wecom_bound": bool(wecom and wecom.get("bound")),
        "external_userid": (wecom or {}).get("external_userid"),
        "llm_fallback_note": llm_note,
        "hint": hint,
        **identity,
    }
