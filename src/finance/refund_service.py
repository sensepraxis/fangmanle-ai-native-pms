# SPDX-License-Identifier: Apache-2.0
"""退改与反结账领域服务：工单 / 阈值 / 审计 / 三类提交。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

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
from infra.i18n import TranslatingMap, t
from models import (
    Guest,
    NightAuditLog,
    Order,
    Payment,
    PmsCheckin,
    PmsFolio,
    PmsFolioEntry,
    RefundAdjustAudit,
    RefundAdjustConfig,
    RefundAdjustTicket,
)

STATUS_LABEL = TranslatingMap(
    {
        "pending_approval": "待审批",
        "pending_dual_auth": "待双授权",
        "approved": "已通过",
        "done": "已完成",
        "rejected": "已拒绝",
        "failed": "失败",
    }
)

OP_LABEL = TranslatingMap(
    {
        "refund": "退款",
        "adjust": "改账·红冲",
        "reverse": "反结账",
    }
)

PAY_CHANNEL_LABEL = TranslatingMap(
    {
        "wechat": "微信",
        "wechat_pos": "微信",
        "alipay": "支付宝",
        "alipay_pos": "支付宝",
        "card": "银行卡",
        "cash": "现金",
        "pos": "收银机",
        "transfer": "转账",
        "ar": "协议挂账",
        "on_account": "协议挂账",
        "deposit_offset": "押金冲减",
    }
)

# 可退款的订单状态（排除已取消；已关单但仍有可退余额的 checked_out 保留）
REFUNDABLE_ORDER_STATUSES = {
    "confirmed",
    "pending",
    "checked_in",
    "partial_extend",
    "checked_out",
}


def _mask_name(name: str | None) -> str:
    n = (name or "客人").strip()
    if len(n) <= 1:
        return n + "**"
    return n[0] + "**"


def yuan(cents: int | None) -> float:
    return round((cents or 0) / 100.0, 2)


def to_cents(amount: Any) -> int:
    try:
        return int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return 0


def get_config(db: Session, hotel_id: int) -> RefundAdjustConfig:
    cfg = db.get(RefundAdjustConfig, hotel_id)
    if not cfg:
        cfg = RefundAdjustConfig(hotel_id=hotel_id, refund_threshold_yuan=2000)
        db.add(cfg)
        db.flush()
    return cfg


def update_threshold(db: Session, hotel_id: int, threshold_yuan: int, actor: str) -> dict:
    if threshold_yuan < 0 or threshold_yuan > 1_000_000:
        raise InvalidStateError("阈值须在 0～1000000 元")
    cfg = get_config(db, hotel_id)
    before = cfg.refund_threshold_yuan
    cfg.refund_threshold_yuan = int(threshold_yuan)
    cfg.updated_at = datetime.now()
    _audit(
        db,
        hotel_id,
        None,
        "THRESHOLD_UPDATE",
        actor,
        f"大额退款线 {before} → {threshold_yuan}",
        before={"refund_threshold_yuan": before},
        after={"refund_threshold_yuan": threshold_yuan},
    )
    db.flush()
    return {"refund_threshold_yuan": cfg.refund_threshold_yuan}


def _audit(
    db: Session,
    hotel_id: int,
    ticket_id: int | None,
    event: str,
    actor: str,
    memo: str = "",
    before: Any = None,
    after: Any = None,
) -> None:
    db.add(
        RefundAdjustAudit(
            hotel_id=hotel_id,
            ticket_id=ticket_id,
            event=event,
            actor_id=actor,
            memo=memo[:255] if memo else None,
            before_json=json.dumps(before, ensure_ascii=False) if before is not None else None,
            after_json=json.dumps(after, ensure_ascii=False) if after is not None else None,
        )
    )


def _loc_ticket_text(raw: str | None) -> str:
    """工单 title/detail/reason：优先整句 msgid；动态拼接则翻前缀。"""
    from infra.i18n import get_locale, t

    s = (raw or "").strip()
    if not s:
        return ""
    hit = t(s)
    if hit != s or str(get_locale()).startswith("zh"):
        return hit
    prefixes = (
        ("反结账 · ", "Folio reverse · "),
        ("部分退款 · ", "Partial refund · "),
        ("全额退款 · ", "Full refund · "),
        ("冲正 · ", "Adjustment · "),
        ("发票红冲 · ", "Invoice credit note · "),
    )
    for zh, en in prefixes:
        if s.startswith(zh):
            return en + s[len(zh) :]
    suffixes = (
        (" · 待双授权", " · pending dual auth"),
        (" · 待审批", " · pending approval"),
    )
    for zh, en in suffixes:
        if s.endswith(zh):
            return s[: -len(zh)] + en
    return s


def _serialize_ticket(t: RefundAdjustTicket) -> dict[str, Any]:
    return {
        "id": t.id,
        "ticket_no": t.ticket_no,
        "op_type": t.op_type,
        "op_label": OP_LABEL.get(t.op_type or "", t.op_type),
        "status": t.status,
        "status_label": STATUS_LABEL.get(t.status or "", t.status),
        "title": _loc_ticket_text(t.title),
        "detail": _loc_ticket_text(t.detail),
        "order_id": t.order_id,
        "order_no": t.order_no,
        "guest_name_masked": t.guest_name_masked,
        "amount_yuan": yuan(t.amount_cents),
        "reason": _loc_ticket_text(t.reason),
        "refund_method": t.refund_method,
        "auth_mgr_done": bool(t.auth_mgr_done),
        "auth_fin_done": bool(t.auth_fin_done),
        "auth_mgr_by": t.auth_mgr_by,
        "auth_fin_by": t.auth_fin_by,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _next_ticket_no(db: Session, hotel_id: int, prefix: str) -> str:
    day = datetime.now().strftime("%Y%m%d")
    base = f"RA-{prefix}-{day}-"
    last = (
        db.query(RefundAdjustTicket)
        .filter(
            RefundAdjustTicket.hotel_id == hotel_id,
            RefundAdjustTicket.ticket_no.like(f"{base}%"),
        )
        .order_by(RefundAdjustTicket.ticket_no.desc())
        .first()
    )
    seq = 1
    if last and last.ticket_no:
        try:
            seq = int(last.ticket_no.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f"{base}{seq:04d}"


def board(db: Session, hotel_id: int) -> dict[str, Any]:
    cfg = get_config(db, hotel_id)
    tickets = (
        db.query(RefundAdjustTicket)
        .filter(RefundAdjustTicket.hotel_id == hotel_id)
        .order_by(RefundAdjustTicket.id.desc())
        .limit(40)
        .all()
    )
    pending = [t for t in tickets if t.status in ("pending_approval", "pending_dual_auth")]
    audits = (
        db.query(RefundAdjustAudit)
        .filter(RefundAdjustAudit.hotel_id == hotel_id)
        .order_by(RefundAdjustAudit.id.desc())
        .limit(20)
        .all()
    )
    return {
        "config": {
            "refund_threshold_yuan": cfg.refund_threshold_yuan,
            "reverse_requires_dual_auth": True,
        },
        "tickets": [_serialize_ticket(t) for t in tickets],
        "my_pending": [_serialize_ticket(t) for t in pending],
        "recent_audits": [
            {
                "id": a.id,
                "ticket_id": a.ticket_id,
                "event": a.event,
                "actor_id": a.actor_id,
                "memo": a.memo,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in audits
        ],
    }


def lookup_order_for_refund(db: Session, hotel_id: int, q: str) -> dict[str, Any]:
    """兼容旧入口：按订单号/房号定位后返回单笔详情。"""
    key = (q or "").strip()
    if not key:
        raise InvalidStateError("请输入手机号、订单号或房号")
    digits = "".join(ch for ch in key if ch.isdigit())
    if len(digits) >= 3 and (len(digits) == len(key) or key.startswith(digits[:3])):
        # 纯数字/手机号走手机主路径
        if len(digits) >= 3 and not any(c.isalpha() for c in key.replace(".", "")):
            phone_res = lookup_refund_by_phone(db, hotel_id, digits)
            if phone_res.get("matched") and phone_res.get("auto_select_order_id"):
                return build_refund_order_detail(db, hotel_id, phone_res["auto_select_order_id"])
            return phone_res

    o = _find_order_by_key(db, hotel_id, key)
    if not o:
        # 兜底 No.8821
        if key.replace(".", "").upper() in ("NO8821", "8821", "NO.8821"):
            return _demo_refund_8821()
        raise NotFoundError("未找到可退订单")
    return build_refund_order_detail(db, hotel_id, o.id)


def lookup_refund_by_phone(db: Session, hotel_id: int, phone: str) -> dict[str, Any]:
    """退款主路径：手机号 → OneID → 可退订单列表（复用押金找客）。"""
    from finance.deposit_service import lookup_by_phone

    base = lookup_by_phone(db, hotel_id, phone)
    if not base.get("matched"):
        return {
            "matched": False,
            "hint": base.get("hint") or "继续输入以定位客人",
            "guest": base.get("guest"),
            "candidates": base.get("candidates") or [],
            "orders": [],
            "order_count": 0,
        }

    guest = base.get("guest") or {}
    # 在有效订单基础上再筛「可退」：有收款、非取消、非已全额退
    seen: set[int] = set()
    orders_out = []
    for row in base.get("orders") or []:
        oid = int(row["order_id"])
        detail = build_refund_order_detail(db, hotel_id, oid, light=True)
        if not detail.get("refundable"):
            continue
        seen.add(oid)
        orders_out.append({**row, **detail.get("card", {}), "payment_lock": detail.get("payment_lock")})

    # 补扫同客历史可退单（已退房仍可退；不限于押金「有效在住」）
    if guest.get("guest_id"):
        more = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.guest_id == int(guest["guest_id"]),
                Order.status.in_(list(REFUNDABLE_ORDER_STATUSES)),
            )
            .order_by(Order.id.desc())
            .limit(20)
            .all()
        )
        for o in more:
            if o.id in seen:
                continue
            detail = build_refund_order_detail(db, hotel_id, o.id, light=True)
            if detail.get("refundable"):
                seen.add(o.id)
                orders_out.append(detail["card"])

    auto = orders_out[0]["order_id"] if len(orders_out) == 1 else None
    return {
        "matched": True,
        "guest": {
            **guest,
            "confirm_hint": guest.get("confirm_hint") or f"口头核验：您是{guest.get('name_masked', '客人')}吗？",
        },
        "candidates": base.get("candidates") or [],
        "orders": orders_out,
        "order_count": len(orders_out),
        "auto_select_order_id": auto,
        "empty_action": None
        if orders_out
        else {
            "message": "该手机号下暂无可退订单（已关单全额退/取消已过滤）",
            "actions": [{"label": "查看历史客档", "path": "/b-data/global-guest-directory"}],
        },
    }


def _find_order_by_key(db: Session, hotel_id: int, key: str) -> Order | None:
    o = db.query(Order).filter(Order.hotel_id == hotel_id, Order.order_no == key).first()
    if o:
        return o
    o = (
        db.query(Order)
        .filter(Order.hotel_id == hotel_id, Order.order_no.ilike(f"%{key}%"))
        .order_by(Order.id.desc())
        .first()
    )
    if o:
        return o
    ck = (
        db.query(PmsCheckin)
        .filter(PmsCheckin.hotel_id == hotel_id, PmsCheckin.room_no == key)
        .order_by(PmsCheckin.id.desc())
        .first()
    )
    if ck and ck.order_id:
        return db.get(Order, ck.order_id)
    return None


def _payment_lock(db: Session, order_id: int) -> dict[str, Any]:
    """系统锁定原路：取最近一笔实收支付。"""
    pays = db.query(Payment).filter(Payment.order_id == order_id).order_by(Payment.id.desc()).all()
    # 跳过退款类（amount < 0）若有
    pay = None
    for p in pays:
        if float(p.received_amount or p.amount or 0) > 0:
            pay = p
            break
    if not pay:
        return {
            "locked": True,
            "pay_channel": "wechat_pos",
            "pay_channel_label": "微信",
            "transaction_id": None,
            "method_display": "原路退回（微信）· 按原支付渠道锁定",
            "allow_cash_special": True,
            "demo_fallback": True,
        }
    ch = (pay.method or "wechat_pos").lower()
    label = PAY_CHANNEL_LABEL.get(ch, ch)
    txn = pay.pos_slip_no or f"TXN-{pay.id:08d}"
    return {
        "locked": True,
        "pay_channel": ch,
        "pay_channel_label": label,
        "transaction_id": txn,
        "payment_id": pay.id,
        "paid_yuan": round(float(pay.received_amount or pay.amount or 0), 2),
        "method_display": f"原路退回（{label}）· 流水 {txn}",
        "allow_cash_special": ch != "cash",
        "is_cash_original": ch == "cash",
    }


def _folio_lines(db: Session, order_id: int) -> tuple[list[dict], float, str | None]:
    folio = db.query(PmsFolio).filter_by(order_id=order_id).order_by(PmsFolio.id.desc()).first()
    lines: list[dict] = []
    room_no = None
    if folio:
        entries = (
            db.query(PmsFolioEntry).filter(PmsFolioEntry.folio_id == folio.id).order_by(PmsFolioEntry.id.asc()).all()
        )
        refunded = sum(abs(float(e.amount or 0)) for e in entries if float(e.amount or 0) < 0)
        for e in entries:
            amt = float(e.amount or 0)
            if amt <= 0:
                continue
            lines.append(
                {
                    "id": f"E{e.id}",
                    "label": e.description or e.entry_type or "账目",
                    "amount_yuan": round(amt, 2),
                    "checked": e.entry_type in ("room", "room_charge", "night_audit"),
                    "entry_type": e.entry_type,
                    "payment_id": None,
                }
            )
        paid = float(folio.payment_total or 0)
        # 已全额退：已退合计 >= 已收
        if paid > 0 and refunded >= paid - 0.01:
            return [], paid, room_no
        return lines, paid, room_no

    o = db.get(Order, order_id)
    total = float(o.total_amount or 0) if o else 0
    if total > 0:
        lines = [
            {
                "id": "ALL",
                "label": "房费合计",
                "amount_yuan": round(total, 2),
                "checked": True,
                "entry_type": "room",
            }
        ]
    return lines, total, room_no


def build_refund_order_detail(
    db: Session,
    hotel_id: int,
    order_id: int,
    *,
    light: bool = False,
) -> dict[str, Any]:
    o = db.get(Order, order_id)
    if not o or o.hotel_id != hotel_id:
        raise NotFoundError("订单不存在")
    if o.status == "cancelled":
        return {"refundable": False, "reason": "已取消"}

    g = db.get(Guest, o.guest_id) if o.guest_id else None
    ck = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
    room_no = (ck.room_no if ck else None) or "—"
    lines, paid, _ = _folio_lines(db, o.id)
    lock = _payment_lock(db, o.id)

    # 无可退分录且无收款 → 不可退
    refundable = bool(lines) and paid > 0.009
    if not refundable and not lines and paid <= 0:
        # 仍允许：checked_in 且有 total
        if o.status == "checked_in" and float(o.total_amount or 0) > 0:
            lines, paid, _ = _folio_lines(db, o.id)
            if not lines:
                lines = [
                    {
                        "id": "ALL",
                        "label": "房费合计",
                        "amount_yuan": round(float(o.total_amount or 0), 2),
                        "checked": True,
                        "entry_type": "room",
                    }
                ]
                paid = float(o.total_amount or 0)
            refundable = True

    card = {
        "order_id": o.id,
        "order_no": o.order_no,
        "status": o.status,
        "status_label": {
            "checked_in": "在住",
            "checked_out": "已退房",
            "confirmed": "已确认",
            "pending": "待确认",
        }.get(o.status or "", o.status),
        "guest_name_masked": _mask_name(g.name if g else None),
        "phone_mask": (g.phone_mask if g else None) or "—",
        "room_no": room_no,
        "check_in": o.check_in.isoformat() if o.check_in else None,
        "check_out": o.check_out.isoformat() if o.check_out else None,
        "received_yuan": round(paid, 2),
        "payment_lock": lock,
    }
    if light:
        return {"refundable": refundable, "card": card, "payment_lock": lock}

    if not refundable:
        raise InvalidStateError("该订单无可退金额（可能已全额退或未收款）")

    return {
        "matched": True,
        "refundable": True,
        "order_id": o.id,
        "order_no": o.order_no,
        "guest_id": o.guest_id,
        "guest_name_masked": card["guest_name_masked"],
        "phone_mask": card["phone_mask"],
        "room_no": room_no,
        "check_in": card["check_in"],
        "check_out": card["check_out"],
        "received_yuan": card["received_yuan"],
        "lines": lines,
        "payment_lock": lock,
        "confirm_hint": f"口头核验：您是{card['guest_name_masked']}，住{room_no}房吗？",
        "status": o.status,
    }


def _demo_refund_8821() -> dict[str, Any]:
    return {
        "matched": True,
        "demo": True,
        "refundable": True,
        "order_id": None,
        "order_no": "No.8821",
        "guest_name_masked": "王**",
        "phone_mask": "138****8821",
        "room_no": "1203",
        "check_in": "2026-08-28",
        "check_out": "2026-08-30",
        "received_yuan": 1004,
        "lines": [
            {"id": "L1", "label": "第 2 晚房费", "amount_yuan": 428, "checked": True, "entry_type": "room"},
            {"id": "L2", "label": "早餐", "amount_yuan": 76, "checked": False, "entry_type": "fnb"},
            {"id": "L3", "label": "押金", "amount_yuan": 500, "checked": False, "entry_type": "deposit"},
        ],
        "payment_lock": {
            "locked": True,
            "pay_channel": "wechat_pos",
            "pay_channel_label": "微信",
            "transaction_id": "WX2026082918821",
            "method_display": "原路退回（微信）· 流水 WX2026082918821",
            "allow_cash_special": True,
            "is_cash_original": False,
        },
        "confirm_hint": "口头核验：您是王**，住 1203 房吗？",
    }


def list_adjust_entries(db: Session, hotel_id: int) -> list[dict]:
    """改账可选账目：近期 Folio 正数分录 + 项。"""
    out: list[dict] = []
    folios = db.query(PmsFolio).filter(PmsFolio.hotel_id == hotel_id).order_by(PmsFolio.id.desc()).limit(30).all()
    for f in folios:
        for e in (
            db.query(PmsFolioEntry)
            .filter(PmsFolioEntry.folio_id == f.id)
            .order_by(PmsFolioEntry.id.desc())
            .limit(8)
            .all()
        ):
            amt = float(e.amount or 0)
            if amt <= 0:
                continue
            out.append(
                {
                    "id": f"E{e.id}",
                    "label": f"{f.folio_no} · {e.description or e.entry_type} ¥{amt:.0f}",
                    "amount_yuan": round(amt, 2),
                    "folio_id": f.id,
                    "order_id": f.order_id,
                    "entry_id": e.id,
                }
            )
            if len(out) >= 20:
                break
        if len(out) >= 20:
            break
    out.insert(
        0,
        {
            "id": "DEMO-AR76",
            "label": t("AR-0829 协议挂账早餐 ¥76"),
            "amount_yuan": 76,
            "folio_id": None,
            "order_id": None,
            "entry_id": None,
            "demo": True,
        },
    )
    return out


def list_reverse_targets(db: Session, hotel_id: int) -> list[dict]:
    """反结账：已日结营业日 + 账单。"""
    logs = (
        db.query(NightAuditLog)
        .filter(NightAuditLog.hotel_id == hotel_id)
        .order_by(NightAuditLog.biz_date.desc())
        .limit(14)
        .all()
    )
    out = []
    for lg in logs:
        d = lg.biz_date.isoformat() if lg.biz_date else "—"
        out.append(
            {
                "id": f"NA-{lg.id}",
                "label": t("{date} · 夜审已结", date=d),
                "biz_date": d,
                "snapshot": t("日结已封存 · 日志 #{id}", id=lg.id),
                "impact_yuan": 0,
            }
        )
    out.insert(
        0,
        {
            "id": "DEMO-PY1108",
            "label": t("2026-08-29 · PY-0829-1108（房 1108）"),
            "biz_date": "2026-08-29",
            "snapshot": t("房费 ¥856 · 已结清 · 影响当日营收 -¥856"),
            "impact_yuan": 856,
            "demo": True,
        },
    )
    return out


def submit_refund(
    db: Session,
    hotel_id: int,
    payload: dict,
    actor: str,
) -> dict[str, Any]:
    if not payload.get("face_confirmed"):
        raise InvalidStateError("须勾选「已当面核对身份与退款金额」")

    lock = payload.get("payment_lock") or {}
    locked_channel = (lock.get("pay_channel") or "").strip().lower()
    txn = (lock.get("transaction_id") or payload.get("transaction_id") or "").strip()
    mode = (payload.get("refund_mode") or "original").strip()  # original | cash_special

    if mode == "cash_special":
        if not payload.get("special_approval"):
            raise InvalidStateError("现金特批退属二清高风险，须勾选财务经理特批")
        method = "cash_special"
        method_note = "非原路现金特批"
    else:
        if not locked_channel:
            raise InvalidStateError("缺少原路支付锁定信息，请重新定位源单")
        if not txn and not payload.get("demo"):
            # 允许无流水；真实单应有 transaction_id
            pass
        method = f"original:{locked_channel}"
        method_note = lock.get("method_display") or f"原路退回（{locked_channel}）"

    lines = payload.get("lines") or []
    selected = [x for x in lines if x.get("checked")]
    if not selected:
        raise InvalidStateError("请至少勾选一项退款范围")
    refund_yuan = sum(float(x.get("amount_yuan") or 0) for x in selected)
    fee_yuan = float(payload.get("fee_yuan") or 0)
    net_yuan = max(0.0, refund_yuan - fee_yuan)
    cents = to_cents(net_yuan)

    cfg = get_config(db, hotel_id)
    need_auth = net_yuan > float(cfg.refund_threshold_yuan) or mode == "cash_special"
    status = "pending_approval" if need_auth else "done"
    order_no = payload.get("order_no") or "—"
    guest = payload.get("guest_name_masked") or "客人**"

    t = RefundAdjustTicket(
        ticket_no=_next_ticket_no(db, hotel_id, "REF"),
        hotel_id=hotel_id,
        op_type="refund",
        status=status,
        title=f"{'部分' if len(selected) < len(lines) else '全额'}退款 · {order_no}",
        detail=f"应退 ¥{net_yuan:.0f} · {method_note}" + (" · 待经理授权" if need_auth else " · 已原路发起"),
        order_id=payload.get("order_id"),
        order_no=order_no,
        guest_name_masked=guest,
        amount_cents=cents,
        reason=payload.get("reason") or "退款",
        refund_method=method,
        applicant_id=actor,
        payload_json=json.dumps(
            {**payload, "transaction_id": txn, "refund_mode": mode},
            ensure_ascii=False,
        ),
    )
    db.add(t)
    db.flush()
    _audit(
        db,
        hotel_id,
        t.id,
        "REFUND_SUBMIT",
        actor,
        f"退款 {net_yuan} 元 · {method} · txn={txn or '-'}",
        after=_serialize_ticket(t),
    )
    db.flush()
    if status == "done":
        try:
            from events import emit

            emit(
                "refund.succeeded",
                {
                    "ticket_id": t.id,
                    "ticket_no": t.ticket_no,
                    "hotel_id": hotel_id,
                    "order_id": t.order_id,
                    "order_no": order_no,
                    "amount_yuan": net_yuan,
                    "method": method,
                    "actor": actor,
                },
            )
        except Exception:
            pass
    return {
        "ticket": _serialize_ticket(t),
        "need_manager_auth": need_auth,
        "payment_lock": lock,
        "message": "已提交，等待经理扫码授权" if need_auth else "原路退款已受理（按支付流水锁定渠道）",
    }


def submit_adjust(db: Session, hotel_id: int, payload: dict, actor: str) -> dict[str, Any]:
    if not payload.get("face_confirmed"):
        raise InvalidStateError("须二次确认后提交")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise InvalidStateError("原因必填")
    entry = payload.get("entry") or {}
    action = payload.get("action") or "reverse"
    amt = float(entry.get("amount_yuan") or 0)
    t = RefundAdjustTicket(
        ticket_no=_next_ticket_no(db, hotel_id, "ADJ"),
        hotel_id=hotel_id,
        op_type="adjust",
        status="pending_approval",
        title=f"{'发票红冲' if action == 'invoice_red' else '冲正'} · {entry.get('label') or '账目'}",
        detail=reason[:200],
        order_id=entry.get("order_id"),
        order_no=str(entry.get("label") or "")[:40],
        guest_name_masked="—",
        amount_cents=to_cents(amt),
        reason=reason,
        applicant_id=actor,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(t)
    db.flush()
    _audit(db, hotel_id, t.id, "ADJUST_SUBMIT", actor, reason, after=_serialize_ticket(t))
    db.flush()
    return {
        "ticket": _serialize_ticket(t),
        "message": "改账已提交，待财务授权",
    }


def submit_reverse(db: Session, hotel_id: int, payload: dict, actor: str) -> dict[str, Any]:
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise InvalidStateError("原因必填")
    target = payload.get("target") or {}
    t = RefundAdjustTicket(
        ticket_no=_next_ticket_no(db, hotel_id, "REV"),
        hotel_id=hotel_id,
        op_type="reverse",
        status="pending_dual_auth",
        title=f"反结账 · {target.get('label') or '营业日'}",
        detail=f"{reason} · 待双授权",
        order_no=str(target.get("label") or "")[:40],
        guest_name_masked="—",
        amount_cents=to_cents(target.get("impact_yuan") or 0),
        reason=reason,
        applicant_id=actor,
        auth_mgr_done=0,
        auth_fin_done=0,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(t)
    db.flush()
    _audit(
        db,
        hotel_id,
        t.id,
        "REVERSE_SUBMIT",
        actor,
        "反结账申请 · 强制双授权",
        after=_serialize_ticket(t),
    )
    db.flush()
    return {
        "ticket": _serialize_ticket(t),
        "message": "反结账已申请，请店长与财务经理分别扫码授权",
    }


def dual_auth(
    db: Session,
    hotel_id: int,
    ticket_id: int,
    role: str,
    actor: str,
) -> dict[str, Any]:
    from finance.dual_auth_chain import apply_dual_auth_role

    t = db.get(RefundAdjustTicket, ticket_id)
    if not t or t.hotel_id != hotel_id:
        raise NotFoundError("工单不存在")
    if t.op_type != "reverse":
        raise InvalidStateError("仅反结账工单支持双授权")
    if t.status not in ("pending_dual_auth", "pending_approval"):
        raise InvalidStateError(f"当前状态不可授权：{t.status}")

    before = _serialize_ticket(t)
    ev = apply_dual_auth_role(t, role, actor)

    if t.auth_mgr_done and t.auth_fin_done:
        t.status = "done"
        t.detail = ((t.detail or "") + " · 双授权完成，账单已重开").strip(" ·")
    t.updated_at = datetime.now()
    _audit(db, hotel_id, t.id, ev, actor, f"{role} 扫码授权", before=before, after=_serialize_ticket(t))
    db.flush()
    if t.status == "done" and t.op_type == "reverse":
        try:
            from events import emit

            emit(
                "refund.succeeded",
                {
                    "ticket_id": t.id,
                    "ticket_no": t.ticket_no,
                    "hotel_id": hotel_id,
                    "op_type": t.op_type,
                    "amount_cents": t.amount_cents,
                    "actor": actor,
                    "via": "dual_auth",
                },
            )
        except Exception:
            pass
    return {"ticket": _serialize_ticket(t)}
