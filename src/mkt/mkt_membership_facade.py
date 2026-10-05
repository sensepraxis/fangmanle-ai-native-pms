# SPDX-License-Identifier: Apache-2.0
"""会员等级 / 钱包 / H5 会员资产门面。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import BusinessError, InvalidStateError, NotFoundError
from mkt._mkt_utils import _jdumps, _jloads
from models import Guest, MktGuestWallet, MktMemberLevel


def list_member_levels(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(MktMemberLevel)
        .filter_by(hotel_id=hotel_id)
        .order_by(MktMemberLevel.sort_order.asc(), MktMemberLevel.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "level_code": r.level_code,
            "level_name": r.level_name,
            "upgrade_type": r.upgrade_type,
            "upgrade_value": r.upgrade_value,
            "retention_type": r.retention_type,
            "retention_value": r.retention_value,
            "benefits": _jloads(r.benefits_json, []),
            "sort_order": r.sort_order,
            "is_active": bool(r.is_active),
        }
        for r in rows
    ]


def upsert_member_level(db: Session, hotel_id: int, payload: dict) -> dict:
    code = str(payload.get("level_code") or "").strip()
    name = str(payload.get("level_name") or "").strip()
    if not code or not name:
        raise InvalidStateError('"请填写等级编码与名称"')
    row = None
    if payload.get("id"):
        row = db.query(MktMemberLevel).filter_by(id=int(payload["id"]), hotel_id=hotel_id).first()
    if not row:
        row = db.query(MktMemberLevel).filter_by(hotel_id=hotel_id, level_code=code).first()
    if not row:
        row = MktMemberLevel(hotel_id=hotel_id, level_code=code)
        db.add(row)
    row.level_code = code
    row.level_name = name
    row.upgrade_type = str(payload.get("upgrade_type") or "nights")
    row.upgrade_value = int(payload.get("upgrade_value") or 0)
    row.retention_type = str(payload.get("retention_type") or "nights")
    row.retention_value = int(payload.get("retention_value") or 0)
    row.benefits_json = _jdumps(payload.get("benefits") or [])
    row.sort_order = int(payload.get("sort_order") or 0)
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(row)
    return next(x for x in list_member_levels(db, hotel_id) if x["id"] == row.id)


def delete_member_level(db: Session, hotel_id: int, level_id: int) -> dict:
    row = db.query(MktMemberLevel).filter_by(id=level_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"等级不存在"')
    db.delete(row)
    db.commit()
    return {"ok": True}


def list_stored_plans(db: Session, hotel_id: int) -> list[dict]:
    """储值档位已下线（合规）。"""
    return []


def upsert_stored_plan(db: Session, hotel_id: int, payload: dict) -> dict:
    raise BusinessError('"储值档位已下线"')


def delete_stored_plan(db: Session, hotel_id: int, plan_id: int) -> dict:
    raise BusinessError('"储值档位已下线"')


def member_bundle(db: Session, hotel_id: int) -> dict:
    levels = list_member_levels(db, hotel_id)
    from mkt.mkt_settings_service import get_mkt_settings

    points = get_mkt_settings(db, hotel_id).get("points") or {}
    wallets = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all()
    by_level: dict[str, int] = {}
    total_points = 0
    for w in wallets:
        code = (w.level_code or "silver").strip() or "silver"
        by_level[code] = by_level.get(code, 0) + 1
        total_points += int(w.points_balance or 0)
    level_dist = []
    for lv in levels:
        level_dist.append(
            {
                "level_code": lv["level_code"],
                "level_name": lv["level_name"],
                "members": by_level.get(lv["level_code"], 0),
            }
        )
    return {
        "levels": levels,
        "plans": [],
        "points": points,
        "overview": {
            "wallet_members": len(wallets),
            "total_points": total_points,
            "level_dist": level_dist,
            "active_levels": sum(1 for lv in levels if lv.get("is_active")),
            "active_plans": 0,
        },
        "h5_preview": {
            "level_name": (
                levels[1]["level_name"] if len(levels) > 1 else (levels[0]["level_name"] if levels else "金卡")
            ),
            "level_code": (
                levels[1]["level_code"] if len(levels) > 1 else (levels[0]["level_code"] if levels else "gold")
            ),
            "points_balance": 2680,
            "benefits": (levels[1]["benefits"] if len(levels) > 1 else (levels[0]["benefits"] if levels else [])),
        },
    }


def _normalize_benefits(raw: Any) -> list[dict]:
    items = raw if isinstance(raw, list) else []
    out = []
    for it in items:
        if isinstance(it, dict):
            title = str(it.get("title") or it.get("name") or "").strip()
            if not title:
                continue
            out.append({"title": title, "desc": str(it.get("desc") or it.get("description") or "本店私域 H5 会员权益")})
        else:
            title = str(it or "").strip()
            if title:
                out.append({"title": title, "desc": "本店私域 H5 会员权益"})
    return out


def _map_vip_to_h5_level(vip: str | None, levels: list[dict]) -> str:
    codes = {str(lv.get("level_code") or "") for lv in levels}
    v = (vip or "").strip().lower()
    if v in codes:
        return v
    if "silver" in codes:
        return "silver"
    return next(iter(codes), "silver")


def ensure_mkt_guest_wallet(
    db: Session, hotel_id: int, guest_id: int, *, create: bool = True
) -> Optional[MktGuestWallet]:
    row = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id, guest_id=guest_id).first()
    if row or not create:
        return row
    guest = db.get(Guest, guest_id)
    levels = list_member_levels(db, hotel_id)
    code = _map_vip_to_h5_level(guest.vip_level if guest else None, levels)
    # 轻量余额：按等级给不同默认值
    defaults = {
        "silver": (480, 0, 2, 1600),
        "gold": (1680, 500, 6, 8800),
        "platinum": (4200, 2000, 12, 22000),
        "diamond": (8600, 8000, 20, 48000),
    }
    pts, stored, nights, spend = defaults.get(code, (300, 0, 1, 800))
    row = MktGuestWallet(
        hotel_id=hotel_id,
        guest_id=guest_id,
        level_code=code,
        points_balance=pts,
        stored_balance=0,
        nights_ytd=nights,
        spend_ytd=spend,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_guest_h5_membership(db: Session, hotel_id: int, guest_id: int, *, ensure: bool = False) -> Optional[dict]:
    """客户 360 / H5 共用：私域会员资产（与 PMS 全局会员相互独立）。"""
    wallet = ensure_mkt_guest_wallet(db, hotel_id, guest_id, create=ensure)
    if not wallet:
        return None
    levels = list_member_levels(db, hotel_id)
    level = next((lv for lv in levels if lv["level_code"] == wallet.level_code), None)
    if not level and levels:
        level = levels[0]
    from mkt.mkt_settings_service import get_mkt_settings

    points = get_mkt_settings(db, hotel_id).get("points") or {}
    # 下一等级进度
    next_level = None
    progress = None
    if level and levels:
        ordered = sorted(levels, key=lambda x: int(x.get("sort_order") or 0))
        idx = next((i for i, lv in enumerate(ordered) if lv["level_code"] == level["level_code"]), -1)
        if idx >= 0 and idx + 1 < len(ordered):
            next_level = ordered[idx + 1]
            ut = next_level.get("upgrade_type") or "nights"
            need = float(next_level.get("upgrade_value") or 0)
            if ut == "amount":
                cur = float(wallet.spend_ytd or 0)
            else:
                # nights / 历史 stored 条件均按入住晚数展示（已下线储值升级）
                cur = float(wallet.nights_ytd or 0)
            progress = {
                "metric": ut if ut in ("nights", "amount") else "nights",
                "current": cur,
                "need": need,
                "pct": min(100, round(cur / need * 100, 1)) if need > 0 else 100,
                "next_level_name": next_level.get("level_name"),
                "next_level_code": next_level.get("level_code"),
            }
    benefits = _normalize_benefits(level.get("benefits") if level else [])
    return {
        "source": "h5_private_domain",
        # 客户 360 用语；H5 页面自行使用短文案「会员等级 / 积分」
        "labels": {
            "level": "私域会员等级",
            "points": "私域积分",
        },
        "level_code": wallet.level_code,
        "level_name": (level or {}).get("level_name") or wallet.level_code,
        "points_balance": int(wallet.points_balance or 0),
        "nights_ytd": int(wallet.nights_ytd or 0),
        "spend_ytd": float(wallet.spend_ytd or 0),
        "benefits": benefits,
        "points_rules": points,
        "progress": progress,
        "hint": "以下为企微私域会员资产，与 PMS 全局会员等级/积分相互独立。",
    }
