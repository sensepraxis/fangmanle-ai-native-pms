# SPDX-License-Identifier: Apache-2.0
"""OneID 身份仿真 / 事件生成 helper。

从原 `bootstrap.ensure_oneid_audit` 抽离；ensure_oneid_audit_schema /
create_realistic_identities / rebuild_events_for_guest / backfill_guest_identities /
ensure_oneid_audit_realism 仍在 `bootstrap.ensure_oneid_audit` 里。
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from guests.i18n_cn import MERGE_METHOD_CN, SRC_CN, merge_method_cn, source_cn
from models import Guest, Order


def enrich_identity_dict(d: dict) -> dict:
    """给 identity 行补 source_cn / merge_method_cn，供 API 直接返回。"""
    out = dict(d)
    out["source_cn"] = source_cn(out.get("source"))
    out["merge_method_cn"] = merge_method_cn(out.get("merge_method"))
    return out


def _rng(guest_id: int, salt: str = "") -> random.Random:
    h = hashlib.md5(f"{guest_id}:{salt}".encode()).hexdigest()
    return random.Random(int(h[:8], 16))


def realistic_external_id(source: str, guest: Guest, idx: int = 0) -> str:
    src = (source or "direct").lower()
    phone = "".join(c for c in str(guest.phone or "") if c.isdigit())[-4:] or f"{guest.id:04d}"
    gid = guest.id or 0
    if src == "xiaohongshu":
        return f"xhs_open_{gid:05d}{idx}"
    if src == "wechat":
        return f"wx_union_{phone}{gid % 97:02d}"
    if src == "douyin":
        return f"dy_uid_{gid * 17 + idx}"
    if src in ("ota", "ctrip"):
        return f"ctrip_{gid:06d}{phone}"
    if src == "meituan":
        return f"mt_user_{gid:06d}"
    if src == "fliggy":
        return f"fliggy_{gid:06d}"
    if src == "direct":
        return f"member_{gid:06d}"
    if src == "agreement":
        return f"corp_{gid:05d}"
    return f"{src}_{gid:05d}{idx}"


def infer_merge_method(confidence: float, is_primary: bool) -> str:
    if is_primary:
        return "primary_bind"
    if confidence >= 0.98:
        return "phone_exact"
    if confidence >= 0.90:
        return "order_match"
    if confidence >= 0.80:
        return "ai_fuzzy"
    return "manual_review"


def infer_operator(method: str) -> str:
    if method == "primary_bind":
        return "系统自动"
    if method == "phone_exact":
        return "规则引擎"
    if method == "order_match":
        return "订单对账服务"
    if method == "ai_fuzzy":
        return "OneID AI 引擎"
    return "前台运营"


def realistic_confidence(rng: random.Random, is_primary: bool) -> float:
    if is_primary:
        return 1.0
    roll = rng.random()
    if roll < 0.35:
        return round(rng.uniform(0.96, 0.99), 2)
    if roll < 0.75:
        return round(rng.uniform(0.88, 0.95), 2)
    if roll < 0.92:
        return round(rng.uniform(0.80, 0.87), 2)
    return round(rng.uniform(0.72, 0.79), 2)


def guest_timeline_anchor(db: Session, guest: Guest) -> datetime:
    """按客人首单 check_in 倒推一个时间锚点（无首单则取 60 天前）。"""
    first_order = db.query(Order).filter_by(guest_id=guest.id).order_by(Order.check_in.asc(), Order.id.asc()).first()
    rng = _rng(guest.id, "anchor")
    if first_order and first_order.check_in:
        try:
            ci = first_order.check_in
            if hasattr(ci, "year"):
                base = datetime(ci.year, ci.month, ci.day, 10, rng.randint(0, 59))
            else:
                base = datetime.fromisoformat(str(ci)[:10] + f" {rng.randint(9, 11):02d}:00:00")
            return base - timedelta(days=rng.randint(3, 45), hours=rng.randint(0, 8))
        except Exception:
            pass
    days_ago = 60 + (guest.id % 540)
    return datetime.now().replace(microsecond=0) - timedelta(days=days_ago, hours=rng.randint(0, 12))


def build_event_note(action: str, guest: Guest, source: str, external_id: str, confidence: float, method: str) -> str:
    from infra.i18n import t

    src = (source or "").strip().lower()
    src_cn = t(SRC_CN.get(src, source or "未知渠道"))
    method_cn = t(MERGE_METHOD_CN.get(method, method or "—"))
    pct = int(confidence * 100)
    if action == "oneid_born":
        return t(
            "为客人「{name}」签发统一身份 {one_id}，作为全渠道画像主键。",
            name=guest.name or "",
            one_id=guest.one_id or "",
        )
    if action == "primary_bind":
        return t(
            "首次触达渠道 {src}，以外部账号 {external_id} 建立主档锚点（{method}）。",
            src=src_cn,
            external_id=external_id or "—",
            method=method_cn,
        )
    if method == "manual_review":
        return t(
            "运营复核后将 {src} 账号 {external_id} 并入 OneID（置信度 {pct}%，{method}）。",
            src=src_cn,
            external_id=external_id or "—",
            pct=pct,
            method=method_cn,
        )
    return t(
        "OneID 引擎将 {src} 外部账号 {external_id} 归并至本档案（置信度 {pct}%，{method}）。",
        src=src_cn,
        external_id=external_id or "—",
        pct=pct,
        method=method_cn,
    )
