# SPDX-License-Identifier: Apache-2.0
"""系统配置 · OTA 佣金：渠道默认佣金 + 按房型/价格代码覆盖。

合规：人工维护；价格助手只读引用；保存不触发改价。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import inspect, text
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
from finance.channel_catalog import CN_FINANCE_SEED, finance_archive_codes, finance_seed_rows
from models import Channel, ChannelCommission, RoomType

# 兼容旧引用：中国财务档案出厂值
OTA_COMMISSION_SEED = CN_FINANCE_SEED

# 运营订单渠道编码 ↔ 佣金档案编码（双向同步默认率）
CHANNEL_CODE_ALIASES = {
    "ota_ctrip": ["ctrip"],
    "ota_meituan": ["meituan"],
    "ota_fliggy": ["fliggy"],
    "ota_douyin": ["douyin"],
}

# 本模块展示顺序（随当前 pack 变化）
OTA_ARCHIVE_CODES = [r["code"] for r in OTA_COMMISSION_SEED]
# 运营侧别名编码不在「OTA 佣金」列表展示
_ALIAS_CODES = {a for aliases in CHANNEL_CODE_ALIASES.values() for a in aliases}
_COMMISSION_TYPES = {"ota", "direct", "membership", "custom", "longstay", "agreement", "booking"}

SETTLE_CYCLES = ("T+1", "T+7", "月结", "实时")
EDIT_ROLES = {"admin", "gm", "fin", "mgr", "owner", "boss", "finance"}  # 兼容旧码；主路径 admin/gm


def can_edit_commission(role: str | None) -> bool:
    r = (role or "").strip().lower()
    if not r:
        return True  # 开发态无角色时放行
    return r in EDIT_ROLES


def _ensure_column(engine, table: str, column: str, ddl: str) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if column in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_ota_commission_schema(engine) -> None:
    from models import Base

    Base.metadata.create_all(
        bind=engine,
        tables=[Channel.__table__, ChannelCommission.__table__],
    )
    _ensure_column(engine, "channels", "settle_cycle", "settle_cycle VARCHAR(16)")
    _ensure_column(engine, "channels", "note", "note VARCHAR(255)")
    _ensure_column(engine, "channels", "owner_role", "owner_role VARCHAR(32)")
    _ensure_column(engine, "channels", "updated_at", "updated_at TIMESTAMP")
    _ensure_column(engine, "channels", "updated_by", "updated_by VARCHAR(32)")


def ensure_ota_commission_seed(db: Session, *, force_rates: bool = False) -> dict:
    """按当前 pack 幂等写入 OTA 佣金档案；不覆盖用户已改过的佣金率（除非 force）。

    名称 / 备注 / 结算周期按 SEED_LOCALE 写入（英文启动 → 英文 seed）。
    """
    from seed.locale_pack import seed_text

    existing = {c.code: c for c in db.query(Channel).all()}
    created = 0
    updated = 0
    owner = seed_text("老板/财务")
    for row in finance_seed_rows():
        code = row["code"]
        name = seed_text(row["name"])
        settle = row["settle_cycle"]  # 稳定码：T+1/T+7/月结/实时；展示层 t()
        note = seed_text(row["note"])
        if code in existing:
            ch = existing[code]
            ch.name = name
            ch.type = row["type"]
            if force_rates or ch.commission_rate is None:
                ch.commission_rate = Decimal(str(row["commission_rate"]))
            if force_rates or not ch.settle_cycle:
                ch.settle_cycle = settle
            if force_rates or not ch.note:
                ch.note = note
            if not ch.owner_role:
                ch.owner_role = owner
            updated += 1
        else:
            ch = Channel(
                code=code,
                name=name,
                type=row["type"],
                commission_rate=Decimal(str(row["commission_rate"])),
                settle_cycle=settle,
                note=note,
                owner_role=owner,
                is_active=True,
            )
            db.add(ch)
            created += 1
        # 同步运营侧别名渠道的默认率（仅种子/重置时）
        if force_rates:
            for alias in CHANNEL_CODE_ALIASES.get(code, []):
                if alias in existing:
                    existing[alias].commission_rate = Decimal(str(row["commission_rate"]))
    db.commit()
    return {"created": created, "updated": updated}


def _pct_ok(rate: float) -> bool:
    return 0.0 <= rate <= 0.50


def channel_to_dict(ch: Channel) -> dict:
    from infra.i18n import t as _t

    rate = float(ch.commission_rate or 0)
    name = _t(ch.name or "") if ch.name else ""
    settle = ch.settle_cycle or "T+7"
    note = ch.note or ""
    owner = ch.owner_role or "老板/财务"
    return {
        "id": ch.id,
        "channel_code": ch.code,
        "code": ch.code,
        "channel_name": name,
        "name": name,
        "channel_type": ch.type,
        "commission_rate": rate,
        "commission_pct": round(rate * 100, 2),
        "settle_cycle": _t(settle),
        "is_enabled": bool(ch.is_active),
        "is_active": bool(ch.is_active),
        "note": _t(note) if note else "",
        "owner_role": _t(owner),
        "is_zero_commission": abs(rate) < 1e-9,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
        "updated_by": ch.updated_by,
    }


def list_ota_commission_channels(db: Session) -> list[dict]:
    """种子渠道优先，其后追加酒店自行新增的 OTA/直订等渠道（不含运营别名）。"""
    ensure_ota_commission_seed(db)
    by_code = {c.code: c for c in db.query(Channel).all()}
    out: list[dict] = []
    seen: set[str] = set()
    for code in finance_archive_codes():
        ch = by_code.get(code)
        if ch:
            out.append(channel_to_dict(ch))
            seen.add(code)
    extras = []
    for code, ch in by_code.items():
        if code in seen or code in _ALIAS_CODES:
            continue
        typ = (ch.type or "").strip().lower()
        if typ in _COMMISSION_TYPES or code.startswith("ota_"):
            extras.append(ch)
    extras.sort(key=lambda c: ((c.name or ""), c.code or ""))
    out.extend(channel_to_dict(ch) for ch in extras)
    return out


def _normalize_channel_code(raw: str) -> str:
    code = str(raw or "").strip().lower().replace(" ", "_")
    code = "".join(ch for ch in code if ch.isalnum() or ch in ("_", "-"))
    return code[:30]


def upsert_ota_commission_channel(
    db: Session,
    payload: dict,
    *,
    role: str | None = None,
    username: str | None = None,
    hotel_id: int | None = None,
) -> dict:
    """新增或编辑单个渠道佣金档案（对齐房型管理：弹窗保存即落库）。"""
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可编辑佣金率")

    code = _normalize_channel_code(payload.get("channel_code") or payload.get("code") or "")
    name = str(payload.get("channel_name") or payload.get("name") or "").strip()
    if not code:
        raise InvalidStateError("渠道编码必填")
    if code in _ALIAS_CODES:
        raise InvalidStateError(f"编码 {code} 为运营别名，请使用 ota_ 前缀档案编码")
    if not name:
        raise InvalidStateError("渠道名称必填")

    try:
        rate = (
            _parse_rate(payload)
            if (payload.get("commission_pct") is not None or payload.get("commission_rate") is not None)
            else 0.0
        )
    except (TypeError, ValueError):
        raise InvalidStateError("佣金率无效")
    if not _pct_ok(rate):
        raise InvalidStateError("佣金率须在 0%–50%")

    cycle = str(payload.get("settle_cycle") or "T+7").strip()
    if cycle not in SETTLE_CYCLES:
        raise InvalidStateError(f"结算周期无效: {cycle}")

    typ = str(payload.get("channel_type") or payload.get("type") or "ota").strip().lower() or "ota"
    if typ not in _COMMISSION_TYPES:
        typ = "custom"

    note = str(payload.get("note") or "")[:255]
    is_on = payload.get("is_enabled")
    if is_on is None:
        is_on = payload.get("is_active", True)

    existing = {c.code: c for c in db.query(Channel).all()}
    now = datetime.now()
    created = False
    if code in existing:
        ch = existing[code]
        ch.name = name
        ch.type = typ
        ch.commission_rate = Decimal(str(round(rate, 4)))
        ch.settle_cycle = cycle
        ch.note = note
        ch.is_active = bool(is_on)
        ch.updated_at = now
        ch.updated_by = (username or "")[:32] or None
    else:
        ch = Channel(
            code=code,
            name=name,
            type=typ,
            commission_rate=Decimal(str(round(rate, 4))),
            settle_cycle=cycle,
            note=note,
            owner_role="老板/财务",
            is_active=bool(is_on),
            updated_at=now,
            updated_by=(username or "")[:32] or None,
        )
        db.add(ch)
        created = True

    for alias in CHANNEL_CODE_ALIASES.get(code, []):
        if alias in existing:
            existing[alias].commission_rate = ch.commission_rate
            existing[alias].updated_at = now

    db.commit()
    db.refresh(ch)

    try:
        from pricing.pricing_assistant import sync_commission_from_channels

        if hotel_id:
            sync_commission_from_channels(db, int(hotel_id))
    except Exception:
        pass

    return {
        "ok": True,
        "created": created,
        "channel": channel_to_dict(ch),
        "channels": list_ota_commission_channels(db),
        "note": "已保存渠道；未触发改价或渠道推送",
    }


def set_ota_channel_enabled(
    db: Session,
    channel_code: str,
    enabled: bool,
    *,
    role: str | None = None,
    username: str | None = None,
    hotel_id: int | None = None,
) -> dict:
    """启用 / 禁用某个 OTA 渠道（软开关，不删行）。"""
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可启用或禁用渠道")
    code = _normalize_channel_code(channel_code)
    ch = db.query(Channel).filter_by(code=code).first()
    if not ch:
        raise NotFoundError(f"渠道不存在: {code}")
    ch.is_active = bool(enabled)
    ch.updated_at = datetime.now()
    ch.updated_by = (username or "")[:32] or None
    db.commit()

    try:
        from pricing.pricing_assistant import sync_commission_from_channels

        if hotel_id:
            sync_commission_from_channels(db, int(hotel_id))
    except Exception:
        pass

    return {
        "ok": True,
        "channel": channel_to_dict(ch),
        "channels": list_ota_commission_channels(db),
        "note": "已启用渠道" if enabled else "已禁用渠道（列表仍保留，可再启用）",
    }


def _parse_rate(payload: dict) -> float:
    """接受 commission_rate(小数) 或 commission_pct(百分比)。"""
    if payload.get("commission_pct") is not None and payload.get("commission_rate") is None:
        return float(payload["commission_pct"]) / 100.0
    rate = float(payload.get("commission_rate"))
    if rate > 1:
        return rate / 100.0
    return rate


def save_ota_commission_channels(
    db: Session,
    payload: dict,
    *,
    role: str | None = None,
    username: str | None = None,
) -> dict:
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可编辑佣金率")
    rows = payload.get("channels") or payload.get("items") or []
    if not isinstance(rows, list) or not rows:
        raise InvalidStateError("channels 不能为空")

    errors = []
    parsed: list[tuple[str, float, dict]] = []
    for r in rows:
        code = str(r.get("channel_code") or r.get("code") or "").strip()
        if not code:
            continue
        try:
            rate = _parse_rate(r)
        except (TypeError, ValueError):
            errors.append(f"{code}: 佣金率无效")
            continue
        if not _pct_ok(rate):
            errors.append(f"{code}: 佣金率须在 0%–50%")
            continue
        parsed.append((code, rate, r))
    if errors:
        raise InvalidStateError("；".join(errors))

    existing = {c.code: c for c in db.query(Channel).all()}
    now = datetime.now()
    saved = 0
    for code, rate, r in parsed:
        if code not in existing:
            continue
        ch = existing[code]
        ch.commission_rate = Decimal(str(round(rate, 4)))
        name = r.get("channel_name") or r.get("name")
        if name is not None and str(name).strip():
            ch.name = str(name).strip()[:80]
        if r.get("settle_cycle"):
            cycle = str(r["settle_cycle"])
            if cycle not in SETTLE_CYCLES:
                raise InvalidStateError(f"结算周期无效: {cycle}")
            ch.settle_cycle = cycle
        if "is_enabled" in r or "is_active" in r:
            on = r.get("is_enabled") if "is_enabled" in r else r.get("is_active")
            ch.is_active = bool(on)
        if r.get("note") is not None:
            ch.note = str(r.get("note") or "")[:255]
        ch.updated_at = now
        ch.updated_by = (username or "")[:32] or None
        for alias in CHANNEL_CODE_ALIASES.get(code, []):
            if alias in existing:
                existing[alias].commission_rate = ch.commission_rate
                existing[alias].updated_at = now
        saved += 1

    db.commit()

    try:
        from pricing.pricing_assistant import sync_commission_from_channels

        hotel_id = int(payload.get("hotel_id") or 0)
        if hotel_id:
            sync_commission_from_channels(db, hotel_id)
    except Exception:
        pass

    return {
        "saved": saved,
        "channels": list_ota_commission_channels(db),
        "note": "已保存渠道佣金；未触发任何改价或渠道推送",
    }


def reset_ota_commission_defaults(
    db: Session,
    *,
    role: str | None = None,
    username: str | None = None,
) -> dict:
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可重置佣金率")
    ensure_ota_commission_seed(db, force_rates=True)
    existing = {c.code: c for c in db.query(Channel).all()}
    now = datetime.now()
    for row in finance_seed_rows():
        ch = existing.get(row["code"])
        if not ch:
            continue
        ch.commission_rate = Decimal(str(row["commission_rate"]))
        ch.settle_cycle = row["settle_cycle"]
        ch.note = row["note"]
        ch.is_active = True
        ch.updated_at = now
        ch.updated_by = (username or "reset")[:32]
        for alias in CHANNEL_CODE_ALIASES.get(row["code"], []):
            if alias in existing:
                existing[alias].commission_rate = ch.commission_rate
    db.commit()
    return {"ok": True, "channels": list_ota_commission_channels(db)}


def resolve_commission_rate(
    db: Session,
    hotel_id: int,
    channel_code: str,
    *,
    room_type_id: Optional[int] = None,
    rate_code: Optional[str] = None,
    on_date: Optional[date] = None,
) -> float:
    """净价一致换算优先级：覆盖表命中 > channel 默认（含别名）。"""
    on_date = on_date or date.today()
    code = (channel_code or "").strip()
    codes = [code] if code else []
    for primary, aliases in CHANNEL_CODE_ALIASES.items():
        if code == primary or code in aliases:
            codes = [primary, *aliases]
            break
    # 去重保序
    seen: set[str] = set()
    uniq_codes = []
    for c in codes:
        if c and c not in seen:
            seen.add(c)
            uniq_codes.append(c)

    best = None
    best_score = -1
    for ccode in uniq_codes:
        q = db.query(ChannelCommission).filter_by(hotel_id=hotel_id, channel_code=ccode, is_enabled=True).all()
        for row in q:
            if row.effective_from and on_date < row.effective_from:
                continue
            if row.effective_to and on_date > row.effective_to:
                continue
            score = 0
            if row.room_type_id is not None:
                if room_type_id is None or int(row.room_type_id) != int(room_type_id):
                    continue
                score += 2
            if row.rate_code:
                if not rate_code or row.rate_code != rate_code:
                    continue
                score += 1
            if score > best_score:
                best_score = score
                best = row
    if best is not None:
        return float(best.commission_rate or 0)

    return rate_for_channel_code(db, code)


def channel_price_from_net(net_price: float, commission_rate: float) -> float:
    """§5.10 净价一致：channel_price = rate_plan.price / (1 − commission_rate)"""
    r = float(commission_rate or 0)
    if r >= 1:
        raise InvalidStateError("佣金率无效")
    return round(float(net_price) / (1 - r), 2) if r < 1 else float(net_price)


def net_from_channel_price(list_price: float, commission_rate: float) -> float:
    return round(float(list_price) * (1 - float(commission_rate or 0)), 2)


def list_commission_overrides(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(ChannelCommission)
        .filter_by(hotel_id=hotel_id)
        .order_by(ChannelCommission.channel_code, ChannelCommission.id)
        .all()
    )
    rt_names = {rt.id: rt.name for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}
    channels = {c.code: c for c in db.query(Channel).all()}
    out = []
    for r in rows:
        rate = float(r.commission_rate or 0)
        ch = channels.get(r.channel_code)
        base = float(ch.commission_rate or 0) if ch else None
        base_pct = round(base * 100, 2) if base is not None else None
        pct = round(rate * 100, 2)
        delta = round(pct - base_pct, 2) if base_pct is not None else None
        out.append(
            {
                "id": r.id,
                "hotel_id": r.hotel_id,
                "channel_code": r.channel_code,
                "channel_name": (ch.name if ch else r.channel_code),
                "room_type_id": r.room_type_id,
                "room_type_name": rt_names.get(r.room_type_id) if r.room_type_id else None,
                "rate_code": r.rate_code,
                "commission_rate": rate,
                "commission_pct": pct,
                "base_commission_pct": base_pct,
                "delta_pct": delta,
                "settle_cycle": r.settle_cycle,
                "is_enabled": bool(r.is_enabled),
                "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "note": r.note,
            }
        )
    return out


def upsert_commission_override(
    db: Session,
    hotel_id: int,
    payload: dict,
    *,
    role: str | None = None,
    username: str | None = None,
) -> dict:
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可编辑佣金覆盖")
    code = str(payload.get("channel_code") or "").strip()
    if not code:
        raise InvalidStateError("渠道必填")
    try:
        rate = _parse_rate(payload)
    except (TypeError, ValueError):
        raise InvalidStateError("佣金率无效")
    if not _pct_ok(rate):
        raise InvalidStateError("佣金率须在 0%–50%")

    rid = payload.get("id")
    row = None
    if rid:
        row = db.get(ChannelCommission, int(rid))
        if row and int(row.hotel_id) != int(hotel_id):
            raise NotFoundError("覆盖规则不存在")
        if not row:
            raise NotFoundError("覆盖规则不存在")
    if not row:
        row = ChannelCommission(hotel_id=hotel_id, channel_code=code)
        db.add(row)
    row.channel_code = code
    row.room_type_id = int(payload["room_type_id"]) if payload.get("room_type_id") else None
    row.rate_code = str(payload.get("rate_code") or "").strip() or None
    row.commission_rate = Decimal(str(round(rate, 4)))
    row.settle_cycle = payload.get("settle_cycle")
    row.is_enabled = bool(payload.get("is_enabled", True))
    ef = payload.get("effective_from")
    et = payload.get("effective_to")
    row.effective_from = date.fromisoformat(ef) if ef else None
    row.effective_to = date.fromisoformat(et) if et else None
    row.note = (payload.get("note") or "")[:255] or None
    row.owner_role = "老板/财务"
    row.updated_at = datetime.now()
    row.updated_by = (username or "")[:32] or None
    db.commit()
    return {"ok": True, "id": row.id, "overrides": list_commission_overrides(db, hotel_id)}


def delete_commission_override(
    db: Session,
    hotel_id: int,
    override_id: int,
    *,
    role: str | None = None,
) -> dict:
    if not can_edit_commission(role):
        raise AuthorizationError("仅老板 / 财务可删除佣金覆盖")
    row = db.query(ChannelCommission).filter_by(id=override_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError("覆盖规则不存在")
    db.delete(row)
    db.commit()
    return {"ok": True, "overrides": list_commission_overrides(db, hotel_id)}


def commission_map_for_pricing(db: Session) -> dict[str, float]:
    """渠道编码 → 默认佣金率（含别名双向展开）。禁用渠道仍保留费率，供历史结算。"""
    rates: dict[str, float] = {}
    for c in db.query(Channel).all():
        if not c.code:
            continue
        rates[c.code] = float(c.commission_rate or 0)
    for primary, aliases in CHANNEL_CODE_ALIASES.items():
        if primary in rates:
            for a in aliases:
                # 档案码优先：别名未单独维护时继承档案率
                rates.setdefault(a, rates[primary])
                # 若别名已有值但档案也有，以档案为准（OTA 佣金页写的是档案码）
                rates[a] = rates[primary]
        else:
            for a in aliases:
                if a in rates:
                    rates[primary] = rates[a]
                    for a2 in aliases:
                        rates.setdefault(a2, rates[a])
                    break
    return rates


def rate_for_channel_code(db: Session, code: str | None, *, rates: dict[str, float] | None = None) -> float:
    """按渠道编码查默认佣金率（小数）；支持 ota_* ↔ 运营别名。"""
    raw = (code or "").strip()
    if not raw:
        return 0.0
    m = rates if rates is not None else commission_map_for_pricing(db)
    if raw in m:
        return float(m[raw])
    low = raw.lower()
    if low in m:
        return float(m[low])
    return 0.0


def rate_for_channel(db: Session, ch: Channel | None, *, rates: dict[str, float] | None = None) -> float:
    """按 Channel 行查默认佣金率；优先别名对齐后的档案率。"""
    if not ch:
        return 0.0
    code = (ch.code or "").strip()
    m = rates if rates is not None else commission_map_for_pricing(db)
    if code and (code in m or code.lower() in m):
        return float(m.get(code, m.get(code.lower(), 0.0)))
    return float(ch.commission_rate or 0)


def list_channels_for_api(db: Session) -> list[dict]:
    """运营/收益侧渠道列表：仅启用；去重运营别名（与 OTA 佣金档案一致）。"""
    ensure_ota_commission_seed(db)
    rates = commission_map_for_pricing(db)
    by_code = {c.code: c for c in db.query(Channel).all() if c.code}
    out: list[dict] = []
    seen: set[str] = set()

    def _row(ch: Channel) -> dict:
        return {
            "id": ch.id,
            "code": ch.code,
            "name": ch.name,
            "type": ch.type,
            "commission_rate": rate_for_channel(db, ch, rates=rates),
            "is_active": bool(ch.is_active),
            "settle_cycle": ch.settle_cycle,
            "note": ch.note or "",
        }

    # 档案渠道优先排序（随当前 pack）
    for code in finance_archive_codes():
        ch = by_code.get(code)
        if not ch or not ch.is_active:
            continue
        out.append(_row(ch))
        seen.add(code)

    extras = []
    for code, ch in by_code.items():
        if code in seen or code in _ALIAS_CODES:
            continue
        if not ch.is_active:
            continue
        extras.append(ch)
    extras.sort(key=lambda c: ((c.name or ""), c.code or ""))
    for ch in extras:
        out.append(_row(ch))
    return out
