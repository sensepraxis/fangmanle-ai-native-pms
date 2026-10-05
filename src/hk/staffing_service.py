# SPDX-License-Identifier: Apache-2.0
"""
排班：人 × 日 × 班次。不创建房务任务。

标准班次：早班 08-16 / 中班 12-20 / 晚班 16-24 / 休息。
旧值 hourly 一律视为中班。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Optional

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
from infra.i18n import get_locale
from infra.i18n import t as _t
from models import Order, Role, StaffRosterTemplate, StaffShift, StaffShiftRequest, User

SHIFT_META = {
    "morning": {"code": "morning", "label": "早班", "hours": "08-16", "cell": "早班\n08-16"},
    "afternoon": {"code": "afternoon", "label": "中班", "hours": "12-20", "cell": "中班\n12-20"},
    "night": {"code": "night", "label": "晚班", "hours": "16-24", "cell": "晚班\n16-24"},
    "off": {"code": "off", "label": "休息", "hours": "", "cell": "休息"},
}
SHIFT_ALIASES = {
    "hourly": "afternoon",
    "evening": "night",
    "mid": "afternoon",
    "late": "night",
    "rest": "off",
    "早班": "morning",
    "中班": "afternoon",
    "晚班": "night",
    "夜班": "night",
    "休息": "off",
    "小时工": "afternoon",
}
ON_DUTY = ("morning", "afternoon", "night")
CN_WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def canon_shift(raw: Optional[str]) -> str:
    s = (raw or "morning").strip().lower()
    s = SHIFT_ALIASES.get(s, s)
    return s if s in SHIFT_META else "morning"


def shift_label(raw: Optional[str]) -> str:
    return _t(SHIFT_META[canon_shift(raw)]["label"])


def _shift_cell_label(code: str) -> str:
    meta = SHIFT_META[canon_shift(code)]
    name = _t(meta["label"])
    hours = meta["hours"]
    return f"{name}\n{hours}" if hours else name


def migrate_hourly_shifts(db: Session, hotel_id: Optional[int] = None) -> int:
    q = db.query(StaffShift).filter(StaffShift.shift == "hourly")
    if hotel_id:
        q = q.filter(StaffShift.hotel_id == hotel_id)
    n = q.update({StaffShift.shift: "afternoon"}, synchronize_session=False)
    if n:
        db.flush()
    return n or 0


def ensure_staffing_schema(engine) -> None:
    """补 source 列 + 周模板表。"""
    from sqlalchemy import inspect, text

    from models import Base

    Base.metadata.create_all(engine, tables=[StaffRosterTemplate.__table__])
    insp = inspect(engine)
    if "staff_shifts" not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns("staff_shifts")}
    if "source" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE staff_shifts ADD COLUMN source VARCHAR(20) DEFAULT 'auto'"))


def _row_source(row: Optional[StaffShift]) -> str:
    if not row:
        return ""
    raw = (getattr(row, "source", None) or "").strip().lower()
    if raw in ("manual", "ai", "auto"):
        return raw
    note = row.handover_note or ""
    if note.startswith("[AI]") or note == "AI 调班":
        return "ai"
    if note.startswith("[手改]") or "请假" in note or "换班" in note:
        return "manual"
    return "auto"


def _locked_manual(row: Optional[StaffShift]) -> bool:
    return _row_source(row) == "manual"


def _week_bounds(today: Optional[date] = None) -> tuple[date, date]:
    today = today or date.today()
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def _hk_users(db: Session, hotel_id: int) -> list[User]:
    hk = db.query(Role).filter_by(code="hk").first()
    q = db.query(User).filter(
        User.is_active == True,  # noqa: E712
        (User.hotel_id == hotel_id) | (User.hotel_id.is_(None)),
    )
    if hk:
        q = q.filter(User.role_id == hk.id)
    return q.order_by(User.id.asc()).all()


def upsert_shift(
    db: Session,
    hotel_id: int,
    *,
    user_id: int,
    shift_date: date,
    shift: str,
    note: Optional[str] = None,
    source: str = "manual",
    protect_manual: bool = False,
) -> tuple[StaffShift, bool]:
    """写入一格。protect_manual=True 时不覆盖主管手改。返回 (row, written)。"""
    u = db.get(User, int(user_id))
    if not u or (u.hotel_id is not None and u.hotel_id != hotel_id):
        raise InvalidStateError("员工不存在或不属于本店")
    code = canon_shift(shift)
    src = source if source in ("auto", "manual", "ai") else "manual"
    row = (
        db.query(StaffShift)
        .filter_by(hotel_id=hotel_id, user_id=u.id, shift_date=shift_date)
        .order_by(StaffShift.id.desc())
        .first()
    )
    if row and protect_manual and _locked_manual(row):
        return row, False
    if row:
        row.shift = code
        if note is not None:
            row.handover_note = note
        if hasattr(row, "source"):
            row.source = src
    else:
        row = StaffShift(
            hotel_id=hotel_id,
            user_id=u.id,
            shift_date=shift_date,
            shift=code,
            handover_note=note or "",
            source=src,
        )
        db.add(row)
    db.flush()
    return row, True


def mcp_list_week_shifts(db: Session, hotel_id: int, week_start: date) -> list[dict]:
    week_end = week_start + timedelta(days=6)
    rows = (
        db.query(StaffShift)
        .filter(
            StaffShift.hotel_id == hotel_id,
            StaffShift.shift_date >= week_start,
            StaffShift.shift_date <= week_end,
        )
        .all()
    )
    users = {u.id: u for u in _hk_users(db, hotel_id)}
    out = []
    for s in rows:
        u = users.get(s.user_id) or db.get(User, s.user_id)
        out.append(
            {
                "user_id": s.user_id,
                "name": (u.full_name or u.username) if u else str(s.user_id),
                "date": s.shift_date.isoformat() if s.shift_date else None,
                "shift": canon_shift(s.shift),
                "label": shift_label(s.shift),
                "source": _row_source(s),
            }
        )
    return out


def mcp_forecast_departures(db: Session, hotel_id: int, day: date) -> dict:
    """MCP：次日预离房量。退房高峰按酒店惯例落在 10:00-12:00。"""
    stayish = ("checked_in", "confirmed", "reserved", "booked", "arrived", "in_house")
    q = db.query(Order).filter(Order.hotel_id == hotel_id, Order.check_out == day)
    rows = q.all()
    booked = [o for o in rows if (o.status or "") not in ("cancelled", "canceled", "no_show")]
    in_house = [o for o in booked if (o.status or "") in stayish]
    rooms = sum(max(1, int(o.rooms or 1)) for o in (in_house or booked))
    return {
        "date": day.isoformat(),
        "window": "10:00-12:00",
        "orders": len(in_house or booked),
        "rooms": rooms,
        "source": "orders.check_out",
    }


def _count_shifts_on(rows: list[dict], day: date) -> dict[str, int]:
    key = day.isoformat()
    c = Counter(r["shift"] for r in rows if r.get("date") == key)
    return {k: int(c.get(k, 0)) for k in ("morning", "afternoon", "night", "off")}


def mcp_draft_shift_adjustments(
    db: Session,
    hotel_id: int,
    *,
    week_start: date,
    target_day: date,
    need_clean: int,
) -> list[dict]:
    """只改未锁格子：manual 不碰。补早班/中班缺口。"""
    week = mcp_list_week_shifts(db, hotel_id, week_start)
    counts = _count_shifts_on(week, target_day)
    n_staff = max(1, len(_hk_users(db, hotel_id)))
    want = _want_staff(need_clean, n_staff)
    gap_m = max(0, want["morning"] - counts.get("morning", 0))
    gap_a = max(0, want["afternoon"] - counts.get("afternoon", 0))

    day_key = target_day.isoformat()
    day_rows = [r for r in week if r.get("date") == day_key]
    by_uid = {r["user_id"]: r for r in day_rows}
    users = _hk_users(db, hotel_id)
    drafts: list[dict] = []

    def unlocked(u: User) -> Optional[dict]:
        row = by_uid.get(u.id)
        if row and row.get("source") == "manual":
            return None
        cur = row["shift"] if row else ""
        return {
            "user_id": u.id,
            "name": u.full_name or u.username,
            "from_shift": cur or "off",
            "source": (row or {}).get("source") or "",
        }

    def fill(to_shift: str, gap: int, reason: str):
        if gap <= 0:
            return
        pool = []
        for u in users:
            item = unlocked(u)
            if not item:
                continue
            if item["from_shift"] == to_shift:
                continue
            # 优先休息/未排，其次其它自动班
            pri = 0 if item["from_shift"] in ("off", "") else 1
            pool.append((pri, item))
        pool.sort(key=lambda x: x[0])
        taken = 0
        for _, item in pool:
            if taken >= gap:
                break
            if any(d["user_id"] == item["user_id"] for d in drafts):
                continue
            drafts.append(
                {
                    **item,
                    "date": day_key,
                    "to_shift": to_shift,
                    "reason": reason,
                }
            )
            taken += 1

    fill("morning", gap_m, _t("补早班顶退房高峰"))
    fill("afternoon", gap_a, _t("补中班顶退房高峰"))
    return drafts


def _serialize_request(db: Session, r: StaffShiftRequest) -> dict:
    u = db.get(User, r.user_id)
    su = db.get(User, r.swap_user_id) if r.swap_user_id else None
    kind_label = _t("请假") if r.kind == "leave" else _t("换班")
    st_label = {
        "pending": _t("待批"),
        "approved": _t("已通过"),
        "rejected": _t("已驳回"),
    }.get(r.status, r.status)
    staff = (u.full_name or u.username) if u else str(r.user_id)
    swap_staff = (su.full_name or su.username) if su else None
    if r.kind == "leave":
        detail = _t(r.note) if r.note else _t("{shift} → 休息", shift=shift_label(r.from_shift))
    elif r.kind == "swap" and swap_staff:
        detail = _t("与 {name} 对调班次", name=swap_staff)
    else:
        detail = _t(r.note) if r.note else ""
    return {
        "id": r.id,
        "kind": r.kind,
        "kind_label": kind_label,
        "user_id": r.user_id,
        "staff": staff,
        "swap_user_id": r.swap_user_id,
        "swap_staff": swap_staff,
        "date": r.shift_date.isoformat() if r.shift_date else None,
        "from_shift": canon_shift(r.from_shift) if r.from_shift else None,
        "to_shift": canon_shift(r.to_shift) if r.to_shift else None,
        "status": r.status,
        "status_label": st_label,
        "note": detail,
    }


def list_shift_requests(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(StaffShiftRequest)
        .filter(StaffShiftRequest.hotel_id == hotel_id)
        .order_by(StaffShiftRequest.status.asc(), StaffShiftRequest.id.desc())
        .limit(20)
        .all()
    )
    return [_serialize_request(db, r) for r in rows]


def decide_shift_request(db: Session, hotel_id: int, req_id: int, *, approved: bool) -> dict:
    r = db.get(StaffShiftRequest, int(req_id))
    if not r or r.hotel_id != hotel_id:
        raise NotFoundError("申请不存在")
    if r.status != "pending":
        raise InvalidStateError("该申请已处理")
    if not approved:
        r.status = "rejected"
        db.flush()
        return _serialize_request(db, r)
    if r.kind == "leave":
        upsert_shift(db, hotel_id, user_id=r.user_id, shift_date=r.shift_date, shift="off", note="请假已批")
    elif r.kind == "swap":
        if not r.swap_user_id:
            raise InvalidStateError("换班申请缺少对调人")
        a = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=r.user_id, shift_date=r.shift_date).first()
        b = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=r.swap_user_id, shift_date=r.shift_date).first()
        sa = canon_shift(a.shift) if a else "off"
        sb = canon_shift(b.shift) if b else "off"
        upsert_shift(db, hotel_id, user_id=r.user_id, shift_date=r.shift_date, shift=sb, note="换班已批")
        upsert_shift(db, hotel_id, user_id=r.swap_user_id, shift_date=r.shift_date, shift=sa, note="换班已批")
    r.status = "approved"
    db.flush()
    return _serialize_request(db, r)


def ensure_demo_requests(db: Session, hotel_id: int, users: list[User], week_start: date) -> None:
    if not users:
        return
    exists = db.query(StaffShiftRequest).filter_by(hotel_id=hotel_id).first()
    if exists:
        return
    tomorrow = date.today() + timedelta(days=1)
    friday = week_start + timedelta(days=4)
    a, b = users[0], users[1] if len(users) > 1 else users[0]
    db.add(
        StaffShiftRequest(
            hotel_id=hotel_id,
            user_id=users[-1].id,
            kind="leave",
            shift_date=tomorrow,
            from_shift="morning",
            to_shift="off",
            status="pending",
            note="家中有事，申请明日休息",
        )
    )
    db.add(
        StaffShiftRequest(
            hotel_id=hotel_id,
            user_id=a.id,
            kind="swap",
            shift_date=friday,
            from_shift="morning",
            to_shift="afternoon",
            swap_user_id=b.id,
            status="pending",
            note=f"与{b.full_name or b.username}对调周五班次",
        )
    )
    db.flush()


def ensure_week_shifts(db: Session, hotel_id: int, users: list[User], week_start: date) -> None:
    """展示周若还没有班次，按早/中/晚/休写满一格（不编小时工）。"""
    if not users:
        return
    week_end = week_start + timedelta(days=6)
    exists = (
        db.query(StaffShift)
        .filter(
            StaffShift.hotel_id == hotel_id,
            StaffShift.shift_date >= week_start,
            StaffShift.shift_date <= week_end,
        )
        .first()
    )
    if exists:
        return
    cycle = ["morning", "morning", "afternoon", "afternoon", "night", "off", "morning"]
    notes = ["1-2 楼退房高峰", "VIP 优先", "支援 2 楼", "布草交接", "晚班巡查", "高峰支援", "轮休"]
    for i, u in enumerate(users):
        for d_off in range(7):
            d = week_start + timedelta(days=d_off)
            sh = cycle[(i + d_off) % len(cycle)]
            if d.weekday() >= 5 and sh == "night":
                sh = "off" if i % 2 == 0 else "morning"
            db.add(
                StaffShift(
                    hotel_id=hotel_id,
                    user_id=u.id,
                    shift_date=d,
                    shift=sh,
                    handover_note=notes[(i + d_off) % len(notes)],
                    source="auto",
                )
            )
    db.flush()


def _want_staff(need_clean: int, n_staff: int) -> dict[str, int]:
    return {
        "morning": min(n_staff, max(2, (need_clean + 3) // 6)),
        "afternoon": min(n_staff, max(1, (need_clean + 7) // 10)),
        "night": 1 if n_staff else 0,
    }


def _day_card(db: Session, hotel_id: int, day: date) -> dict:
    """未来某一天的预测 + 非破坏性建议。"""
    week_start, _ = _week_bounds(day)
    ensure_week_shifts(db, hotel_id, _hk_users(db, hotel_id), week_start)
    fc = mcp_forecast_departures(db, hotel_id, day)
    need = int(fc.get("rooms") or 0)
    week = mcp_list_week_shifts(db, hotel_id, week_start)
    counts = _count_shifts_on(week, day)
    n_staff = max(1, len(_hk_users(db, hotel_id)))
    want = _want_staff(need, n_staff)
    drafts = mcp_draft_shift_adjustments(db, hotel_id, week_start=week_start, target_day=day, need_clean=need)
    d_m = max(0, want["morning"] - counts.get("morning", 0))
    d_a = max(0, want["afternoon"] - counts.get("afternoon", 0))
    bits = []
    if d_m:
        bits.append(_t("早班 +{n}（共 {total}）", n=d_m, total=want["morning"]))
    if d_a:
        bits.append(_t("中班 +{n}（共 {total}）", n=d_a, total=want["afternoon"]))
    sep = "、" if get_locale().startswith("zh") else "; "
    suggest = sep.join(bits) if bits else _t("人力足够，无需改班")
    gap_bit = _t("，缺口约 {n} 人。", n=d_m + d_a) if (d_m + d_a) else _t("。")
    reason = _t(
        "预计退房 {need} 间。当前早班 {m} 人、中班 {a} 人{gap}",
        need=need,
        m=counts.get("morning", 0),
        a=counts.get("afternoon", 0),
        gap=gap_bit,
    )
    return {
        "date": day.isoformat(),
        "label": _t(
            "{m}月{d}日（{wd}）",
            m=day.month,
            d=f"{day.day:02d}",
            wd=_t(CN_WD[day.weekday()]),
        ),
        "short": f"{day.month}/{day.day:02d}",
        "need_clean": need,
        "window": "10:00-12:00",
        "counts": counts,
        "want": want,
        "delta": {"morning": d_m, "afternoon": d_a},
        "reason": reason,
        "suggest": suggest,
        "proposed": drafts,
        "has_gap": bool(drafts),
    }


def build_ai_forecast(db: Session, hotel_id: int, days: int = 7) -> dict:
    """右侧面板：从今天起未来 7 天。"""
    users = _hk_users(db, hotel_id)
    start = date.today()
    cards = []
    for i in range(max(1, min(int(days), 14))):
        d = start + timedelta(days=i)
        week_start, _ = _week_bounds(d)
        ensure_week_shifts(db, hotel_id, users, week_start)
        cards.append(_day_card(db, hotel_id, d))
    actionable = [c for c in cards if c.get("has_gap")]
    first = actionable[0]["date"] if actionable else None
    last = actionable[-1]["date"] if actionable else None
    return {
        "title": _t("AI 排班建议"),
        "subtitle": _t("未来 {n} 天退房预测 · 建议≠强制，确认后才写入", n=len(cards)),
        "days": cards,
        "apply_from": first,
        "apply_to": last,
        "apply_count": sum(len(c.get("proposed") or []) for c in actionable),
        "disclaimer": _t("AI 只填空闲/自动铺班格子，不会覆盖你已手改的班次。"),
    }


def build_ai_alert(db: Session, hotel_id: int, week_start: date, *, use_llm: bool = False) -> dict:
    """兼容旧调用：返回未来 7 天面板。"""
    return build_ai_forecast(db, hotel_id, days=7)


def apply_ai_adjustments(
    db: Session,
    hotel_id: int,
    items: Optional[list[dict]] = None,
    *,
    day: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """非破坏性写入。可按单日、区间或显式 proposed。"""
    users = _hk_users(db, hotel_id)
    proposed: list[dict] = list(items or [])
    if not proposed:
        if day:
            week_start, _ = _week_bounds(day)
            ensure_week_shifts(db, hotel_id, users, week_start)
            proposed = _day_card(db, hotel_id, day).get("proposed") or []
        elif date_from and date_to:
            d = date_from
            while d <= date_to:
                week_start, _ = _week_bounds(d)
                ensure_week_shifts(db, hotel_id, users, week_start)
                proposed.extend(_day_card(db, hotel_id, d).get("proposed") or [])
                d += timedelta(days=1)
        else:
            fc = build_ai_forecast(db, hotel_id)
            for c in fc.get("days") or []:
                proposed.extend(c.get("proposed") or [])
    applied, skipped = [], 0
    for row in proposed:
        try:
            uid = int(row.get("user_id"))
            d = date.fromisoformat(str(row.get("date")))
            to_shift = canon_shift(row.get("to_shift") or "afternoon")
        except (TypeError, ValueError):
            continue
        _row, written = upsert_shift(
            db,
            hotel_id,
            user_id=uid,
            shift_date=d,
            shift=to_shift,
            note="[AI] 预测调班",
            source="ai",
            protect_manual=True,
        )
        if written:
            applied.append({**row, "to_shift": to_shift, "date": d.isoformat()})
        else:
            skipped += 1
    jump = None
    if applied:
        ds = sorted({x["date"] for x in applied})
        jump = ds[0]
    return {
        "applied": len(applied),
        "skipped": skipped,
        "changes": applied,
        "jump_date": jump,
        "forecast": build_ai_forecast(db, hotel_id),
    }


def copy_prev_week(db: Session, hotel_id: int, week_start: date) -> dict:
    """把上一周班次套到本周；跳过本周已手改的格子。"""
    users = _hk_users(db, hotel_id)
    src_start = week_start - timedelta(days=7)
    ensure_week_shifts(db, hotel_id, users, src_start)
    ensure_week_shifts(db, hotel_id, users, week_start)
    copied, skipped = 0, 0
    for u in users:
        for i in range(7):
            src_d = src_start + timedelta(days=i)
            dst_d = week_start + timedelta(days=i)
            src = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=u.id, shift_date=src_d).first()
            if not src:
                continue
            _row, written = upsert_shift(
                db,
                hotel_id,
                user_id=u.id,
                shift_date=dst_d,
                shift=canon_shift(src.shift),
                note=src.handover_note or "复制上周",
                source="auto",
                protect_manual=True,
            )
            copied += int(written)
            skipped += int(not written)
    return {"copied": copied, "skipped": skipped}


def save_week_template(db: Session, hotel_id: int, week_start: date, name: str = "默认周模板") -> dict:
    users = _hk_users(db, hotel_id)
    payload = []
    for u in users:
        codes = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            row = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=u.id, shift_date=d).first()
            codes.append(canon_shift(row.shift) if row else "off")
        payload.append({"user_id": u.id, "name": u.full_name or u.username, "shifts": codes})
    row = db.query(StaffRosterTemplate).filter_by(hotel_id=hotel_id, name=name.strip() or "默认周模板").first()
    blob = json.dumps(payload, ensure_ascii=False)
    if row:
        row.payload_json = blob
    else:
        row = StaffRosterTemplate(hotel_id=hotel_id, name=name.strip() or "默认周模板", payload_json=blob)
        db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name, "staff": len(payload)}


def add_staff_to_roster(
    db: Session,
    hotel_id: int,
    user_id: int,
    range_start: date,
    range_end: date,
) -> dict:
    """把一名在职员工铺进当前可见日期（缺格才写，不覆盖已有班）。"""
    u = db.get(User, int(user_id))
    if not u or (u.hotel_id is not None and u.hotel_id != hotel_id):
        raise InvalidStateError("员工不存在或不属于本店")
    added = 0
    d = range_start
    while d <= range_end:
        exists = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=u.id, shift_date=d).first()
        if not exists:
            sh = "off" if d.weekday() >= 5 else "morning"
            upsert_shift(
                db,
                hotel_id,
                user_id=u.id,
                shift_date=d,
                shift=sh,
                note="加入排班",
                source="auto",
            )
            added += 1
        d += timedelta(days=1)
    return {"user_id": u.id, "name": u.full_name or u.username, "added_days": added}


def _parse_view_range(view: str, start: Optional[date]) -> tuple[str, date, date]:
    today = date.today()
    view = (view or "week").strip().lower()
    if view not in ("day", "week", "month"):
        view = "week"
    if start:
        anchor = start
    elif view in ("week", "month") and today.weekday() == 6:
        # 周日打开周/月视图时落到下一周，方便排远期
        anchor = today + timedelta(days=1)
    else:
        anchor = today
    if view == "day":
        return view, anchor, anchor
    week_start, week_end = _week_bounds(anchor)
    if view == "week":
        return view, week_start, week_end
    # month = 4 weeks
    return view, week_start, week_start + timedelta(days=27)


def _hk_users_fallback(db: Session, hotel_id: int) -> list[User]:
    users = _hk_users(db, hotel_id)
    if users:
        return users
    return (
        db.query(User)
        .filter(User.is_active == True, (User.hotel_id == hotel_id) | (User.hotel_id.is_(None)))  # noqa: E712
        .order_by(User.id.asc())
        .limit(6)
        .all()
    )


def _cell_dict(row: Optional[StaffShift]) -> dict:
    if not row:
        return {
            "shift": "",
            "type": "empty",
            "label": "未排",
            "name": "未排",
            "hours": "",
            "source": "",
            "ai": False,
            "manual": False,
        }
    code = canon_shift(row.shift)
    meta = SHIFT_META[code]
    src = _row_source(row)
    return {
        "shift": code,
        "type": code,
        "label": _shift_cell_label(code),
        "name": _t(meta["label"]),
        "hours": meta["hours"],
        "source": src,
        "ai": src == "ai",
        "manual": src == "manual",
    }


def staffing_board(
    db: Session,
    hotel_id: int,
    *,
    view: str = "week",
    start: Optional[date] = None,
) -> dict:
    migrate_hourly_shifts(db, hotel_id)
    try:
        ensure_staffing_schema(db.get_bind())
    except Exception:
        pass
    today = date.today()
    view, range_start, range_end = _parse_view_range(view, start)
    users = _hk_users_fallback(db, hotel_id)
    d = range_start - timedelta(days=range_start.weekday())
    while d <= range_end:
        ensure_week_shifts(db, hotel_id, users, d)
        d += timedelta(days=7)
    ensure_demo_requests(db, hotel_id, users, _week_bounds(today)[0])

    rows = (
        db.query(StaffShift)
        .filter(
            StaffShift.hotel_id == hotel_id,
            StaffShift.shift_date >= range_start,
            StaffShift.shift_date <= range_end,
        )
        .all()
    )
    by_key: dict[tuple[int, str], StaffShift] = {}
    for s in rows:
        by_key[(s.user_id, s.shift_date.isoformat())] = s
    seen = {u.id for u in users}
    for s in rows:
        if s.user_id in seen:
            continue
        extra_u = db.get(User, s.user_id)
        if extra_u:
            users.append(extra_u)
            seen.add(extra_u.id)

    days = []
    n_days = (range_end - range_start).days + 1
    for i in range(n_days):
        dd = range_start + timedelta(days=i)
        days.append(
            {
                "label": f"{_t(CN_WD[dd.weekday()])} {dd.month}/{dd.day}",
                "date": dd.isoformat(),
                "is_today": dd == today,
                "weekday": dd.weekday(),
            }
        )

    roles = {r.id: r.name for r in db.query(Role).all()}
    staff_grid = []
    for idx, u in enumerate(users[:12]):
        shifts = [_cell_dict(by_key.get((u.id, days[i]["date"]))) for i in range(n_days)]
        role_name = roles.get(u.role_id) or "保洁员"
        if idx == 0 and "主管" not in role_name:
            role_name = "房务主管"
        elif role_name in ("客房", "hk"):
            role_name = "保洁员"
        staff_grid.append(
            {
                "id": u.id,
                "name": u.full_name or u.username,
                "initial": (u.full_name or u.username or _t("员"))[:1],
                "type": "internal",
                "role": _t(role_name),
                "shifts": shifts,
            }
        )

    weeks = []
    if view == "month":
        for w in range(4):
            chunk = days[w * 7 : (w + 1) * 7]
            weeks.append(
                {
                    "label": f"{chunk[0]['label']} – {chunk[-1]['label']}" if chunk else "",
                    "days": chunk,
                    "offset": w * 7,
                }
            )

    extra = (
        db.query(User)
        .filter(User.is_active == True, (User.hotel_id == hotel_id) | (User.hotel_id.is_(None)))  # noqa: E712
        .all()
    )
    on_ids = {s["id"] for s in staff_grid}
    candidates = [{"id": u.id, "name": u.full_name or u.username} for u in extra if u.id not in on_ids]

    saved = db.query(StaffRosterTemplate).filter_by(hotel_id=hotel_id).order_by(StaffRosterTemplate.id.desc()).all()
    shift_defs = [
        {
            "code": k,
            "label": _t(SHIFT_META[k]["label"]),
            "hours": SHIFT_META[k]["hours"],
            "cell": _shift_cell_label(k),
        }
        for k in ("morning", "afternoon", "night", "off")
    ]
    fc = build_ai_forecast(db, hotel_id)
    first_gap = next((c for c in (fc.get("days") or []) if c.get("has_gap")), None)
    return {
        "view": view,
        "week_label": f"{range_start.month:02d}-{range_start.day:02d} ~ {range_end.month:02d}-{range_end.day:02d}",
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "week_start": range_start.isoformat(),
        "week_end": range_end.isoformat(),
        "days": days,
        "weeks": weeks,
        "today": today.isoformat(),
        "today_index": next((i for i, x in enumerate(days) if x["is_today"]), -1),
        "staff": staff_grid,
        "forecast": fc,
        "alert": {
            "title": fc.get("title") or _t("AI 排班建议"),
            "desc": (first_gap or {}).get("reason") or fc.get("subtitle"),
            "proposed": (first_gap or {}).get("proposed") or [],
            "suggest_hourly": 0,
        },
        "shift_defs": shift_defs,
        "templates": shift_defs,
        "saved_templates": [{"id": t.id, "name": t.name} for t in saved],
        "applications": list_shift_requests(db, hotel_id),
        "assignees": [{"id": s["id"], "name": s["name"]} for s in staff_grid],
        "addable": candidates[:20],
    }
