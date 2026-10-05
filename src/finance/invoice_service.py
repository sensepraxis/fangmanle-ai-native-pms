# SPDX-License-Identifier: Apache-2.0
"""发票管理：工作台聚合（待开/已开/红冲/失败）+ 开票/红冲动作。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
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
from finance.tax.registry import get_tax_provider
from infra.i18n import get_locale, t
from models import Channel, CorpAccount, Guest, Hotel, Invoice, Order


def _f(v) -> float:
    return float(v or 0)


def _money(v: float) -> Decimal:
    return Decimal(str(round(v, 2)))


def _buyer_for_order(db: Session, o: Order, ch: Optional[Channel]) -> dict[str, str]:
    """抬头：由 TaxDocumentProvider 决定（CN 数电票 vs Noop）。"""
    return get_tax_provider().buyer_for_order(db, o, ch)


def _channel_label(ch: Optional[Channel], o: Order) -> tuple[str, str]:
    if (o.payment_status or "") == "on_account":
        return t("挂账"), "bank"
    if not ch:
        return t("散客直订"), "direct"
    name = (ch.name or ch.code or t("渠道")).strip()
    if ch.name:
        name = t(ch.name)
    if "OTA" in name.upper():
        name = t("其他预订渠道")
    code = (ch.code or "direct").lower()
    cls = "booking"
    if code in ("wechat", "wecom"):
        cls = "wechat"
    elif code.startswith("alipay"):
        cls = "alipay"
    elif code in ("direct", "agreement", "longstay"):
        cls = "bank"
    elif code in ("ctrip", "meituan", "fliggy", "douyin", "xiaohongshu", "meituan_voucher"):
        cls = "booking"
    return name, cls


def _amounts(gross: float, commission_rate: float) -> dict[str, float]:
    return get_tax_provider().split_amounts(gross, commission_rate)


def _map_status(raw: str) -> str:
    s = (raw or "open").lower()
    if s in ("issued", "done", "sent"):
        return "done"
    if s in ("red", "red_flush", "voiding"):
        return "red"
    if s in ("voided", "void"):
        return "red"  # 已冲蓝字在列表侧并入红冲语义，避免仍显示已开
    if s in ("failed", "error", "push_failed"):
        return "fail"
    if s in ("draft",):
        return "draft"
    return "todo"  # open / pending


def build_invoice_row(
    db: Session,
    *,
    inv: Optional[Invoice],
    order: Order,
    kind: str = "invoice",
) -> dict[str, Any]:
    ch = db.get(Channel, order.channel_id) if order.channel_id else None
    ch_label, ch_cls = _channel_label(ch, order)
    buyer = _buyer_for_order(db, order, ch)
    from finance.ota_commission_service import rate_for_channel, resolve_commission_rate

    commission = 0.0
    if ch:
        code = (ch.code or "").strip()
        if code and order.hotel_id:
            try:
                commission = float(
                    resolve_commission_rate(
                        db,
                        int(order.hotel_id),
                        code,
                        room_type_id=order.room_type_id,
                        on_date=order.check_in,
                    )
                    or 0
                )
            except Exception:
                commission = rate_for_channel(db, ch)
        else:
            commission = rate_for_channel(db, ch)
    gross = _f(inv.amount if inv and inv.amount is not None else order.total_amount)
    amts = _amounts(gross, commission if ch_cls == "booking" else 0.0)
    fee = float(amts.get("platform_fee") or 0)
    net_amt = float(amts.get("net_amount") or 0)
    pct_s = f"{round(commission * 100, 2):.2f}".rstrip("0").rstrip(".")
    formula = (
        t(
            "¥{gross} × (1 − {ch}佣金 {pct}%) = ¥{net}；平台佣金 = ¥{gross} × {pct}% = ¥{fee}",
            gross=f"{gross:,.2f}",
            ch=ch_label or t("渠道"),
            pct=pct_s,
            net=f"{net_amt:,.2f}",
            fee=f"{fee:,.2f}",
        )
        if fee > 0
        else None
    )
    if inv and inv.tax is not None and _f(inv.tax) > 0:
        amts["tax_amount"] = _f(inv.tax)
        amts["amount_excl_tax"] = round(gross - amts["tax_amount"], 2)

    status = _map_status(inv.status if inv else "open")
    if kind == "pending":
        status = "todo"

    gname = None
    if order.guest_id:
        g = db.get(Guest, order.guest_id)
        gname = g.name if g else None

    issued = inv.issued_at.isoformat(sep=" ", timespec="minutes") if inv and inv.issued_at else None
    overdue_days = 0
    if status == "todo":
        base = order.check_out if order.check_out else None
        if base:
            from datetime import date as date_cls

            today = date_cls.today()
            if hasattr(base, "isoformat"):
                d = base
            else:
                d = date_cls.fromisoformat(str(base)[:10])
            overdue_days = max(0, (today - d).days)

    push = "none"
    # 无独立推送表：不臆造「已推送」

    return {
        "id": inv.id if inv else None,
        "key": f"inv-{inv.id}" if inv else f"pending-{order.id}",
        "kind": kind,
        "order_id": order.id,
        "order_no": order.order_no,
        "guest_name": gname or order.guest_phone or "—",
        "channel": ch_label,
        "channel_cls": ch_cls,
        "title_type": buyer["title_type"],
        "buyer_name": buyer["buyer_name"],
        "tax_no": buyer["tax_no"],
        "invoice_no": (inv.invoice_no if inv and status != "todo" else None),
        "display_no": inv.invoice_no if inv else None,
        "status": status,
        "issued_at": issued,
        "overdue_days": overdue_days,
        "push_status": push,
        "nights": int(order.nights or 0),
        "check_in": order.check_in.isoformat() if order.check_in else None,
        "check_out": order.check_out.isoformat() if order.check_out else None,
        **amts,
        "commission_rate": commission if ch_cls == "booking" else 0.0,
        "commission_pct": round(commission * 100, 2) if ch_cls == "booking" else 0.0,
        "commission_formula": formula,
        "original_invoice_no": None,
        "note": order.note,
    }


def list_invoice_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    hotel = db.get(Hotel, hotel_id)
    # 清理早期污染：failed 态；源票仍为 issued 的自动红冲样例
    restored = False
    for inv in db.query(Invoice).filter_by(hotel_id=hotel_id, status="failed").all():
        inv.status = "issued"
        restored = True
    for red in db.query(Invoice).filter_by(hotel_id=hotel_id, status="red").all():
        no = red.invoice_no or ""
        if not no.startswith("R-"):
            continue
        src = db.query(Invoice).filter_by(hotel_id=hotel_id, invoice_no=no[2:]).first()
        # 旧插入红字时未作废源票；真实红冲会把源票标为 voided
        if src and (src.status or "") == "issued":
            db.delete(red)
            restored = True
    if restored:
        db.commit()

    invoices = db.query(Invoice).filter_by(hotel_id=hotel_id).order_by(Invoice.id.desc()).limit(80).all()

    rows: list[dict[str, Any]] = []
    for inv in invoices:
        if not inv.order_id:
            continue
        o = db.get(Order, inv.order_id)
        if not o:
            continue
        row = build_invoice_row(db, inv=inv, order=o, kind="invoice")
        if (inv.invoice_no or "").startswith("R-") or (inv.status or "") == "red":
            row["status"] = "red"
            src_no = inv.invoice_no or ""
            row["original_invoice_no"] = src_no[2:] if src_no.startswith("R-") else None
            row["push_status"] = "none"
        rows.append(row)

    # 待开池：已付/挂账且无「有效蓝字票」的近期离店或在住单
    active_invoiced = set()
    for inv in invoices:
        st = (inv.status or "").lower()
        if not inv.order_id:
            continue
        if (inv.invoice_no or "").startswith("R-"):
            continue
        if st in ("issued", "done", "sent", "failed", "open", "draft"):
            active_invoiced.add(inv.order_id)

    pending_orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.payment_status.in_(("paid", "partial", "on_account")),
            Order.status.in_(("checked_out", "checked_in", "confirmed")),
        )
        .order_by(Order.id.desc())
        .limit(40)
        .all()
    )
    for o in pending_orders:
        if o.id in active_invoiced:
            continue
        if _f(o.total_amount) <= 0:
            continue
        rows.append(build_invoice_row(db, inv=None, order=o, kind="pending"))

    # 排序：待开优先，再按时间
    rank = {"todo": 0, "fail": 1, "red": 2, "draft": 3, "done": 4}
    rows.sort(key=lambda r: (rank.get(r["status"], 9), -(r.get("order_id") or 0)))

    todo = [r for r in rows if r["status"] == "todo"]
    done = [r for r in rows if r["status"] == "done"]
    red = [r for r in rows if r["status"] == "red"]
    fail = [r for r in rows if r["status"] == "fail"]
    draft = [r for r in rows if r["status"] == "draft"]

    todo_amt = round(sum(r["gross_amount"] for r in todo), 2)
    done_amt = round(sum(r["gross_amount"] for r in done), 2)
    leak = [r for r in todo if r.get("overdue_days", 0) >= 3]
    should = len(todo) + len(done) + len(fail)
    compliance = round((len(done) / should) * 100, 1) if should else 100.0

    # 销项税额来自库内已开发票；进项未建表，不臆造可抵扣额
    output_tax = round(sum(r["tax_amount"] for r in done if r["tax_amount"] > 0), 2)
    input_est = 0.0
    payable = output_tax

    titles = _title_library(rows)
    history = _compliance_history(rows)

    leak_n = len(leak)
    leak_amt = round(sum(r["gross_amount"] for r in leak), 2)
    alert_rows = leak if leak else todo[:5]
    ch_names = list({r["channel"] for r in alert_rows})
    alert_msg = None
    if alert_rows:
        sep = ", " if str(get_locale() or "").lower().startswith("en") else "、"
        ch_txt = sep.join(ch_names[:3]) if ch_names else t("多渠道")
        if leak_n:
            alert_msg = t(
                "涉及 {ch}。有客人已结账仍未拿到发票，其中 {n} 单已超 3 天；建议优先开票。",
                ch=ch_txt,
                n=leak_n,
            )
        else:
            alert_msg = t(
                "涉及 {ch}。有客人已结账仍未拿到发票；建议优先开票。",
                ch=ch_txt,
            )

    out = {
        "kpi": {
            "pending_amount": todo_amt,
            "pending_count": len(todo),
            "pending_vs": t("{n} 单待开", n=len(todo)),
            "issued_count": len(done),
            "issued_amount": done_amt,
            "issued_vs": t("本月已开 {n} 张", n=len(done)),
            "leak_count": leak_n,
            "leak_amount": leak_amt,
            "leak_vs": t("超 3 天未开 {n} 单", n=leak_n) if leak_n else t("无超期漏开"),
            "compliance_rate": compliance,
            "compliance_vs": t("已开 / 应开"),
        },
        "alert": {
            "count": leak_n or len(todo),
            "amount": round(sum(r["gross_amount"] for r in alert_rows), 2) if alert_rows else 0,
            "channels": ch_names,
            "message": alert_msg,
        },
        "tax_estimate": {
            "period": datetime.now().strftime("%Y-%m"),
            "payable": payable,
            "output_tax": output_tax,
            "input_credit": input_est,
            "refund_risk": "—",
            "disclaimer": t("销项按本页已开发票汇总；进项未录入故为 0，最终以税局核定为准"),
            "note": t("不含加计抵减（该政策已到期）"),
        },
        "counts": {
            "all": len(rows),
            "todo": len(todo),
            "done": len(done),
            "red": len(red),
            "fail": len(fail),
            "draft": len(draft),
        },
        "items": rows,
        "titles": titles,
        "history": history,
        "seller": {
            "name": (hotel.name if hotel else "") or "—",
            "tax_no": "",
            "address": (hotel.address if hotel else "") or "",
            "city": (hotel.city if hotel else "") or "",
        },
    }
    out.update(get_tax_provider().workspace(db, hotel_id))
    return out


def _title_library(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for r in rows:
        key = (r.get("buyer_name"), r.get("tax_no"))
        if key in seen or not r.get("buyer_name"):
            continue
        seen.add(key)
        tax = (r.get("tax_no") or "").strip()
        out.append(
            {
                "buyer_name": r["buyer_name"],
                "tax_no": tax,
                "title_type": r.get("title_type") or "personal",
                # 仅有真实税号时标记「有税号」；不做虚构校验通过
                "tax_validated": bool(tax),
            }
        )
    return out[:20]


def _compliance_history(rows: list[dict]) -> list[dict]:
    """合规时间线：仅由库内发票开具/红冲记录聚合，不插入虚构巡检。"""
    items: list[dict] = []
    for r in rows:
        if not r.get("issued_at"):
            continue
        if r.get("status") == "red":
            reason = (r.get("note") or "").replace("红冲原因：", "").replace("Red-flush reason: ", "").strip()
            text = t("对 {order} 红冲", order=r.get("order_no"))
            if reason:
                text = t("对 {order} 红冲（{reason}）", order=r.get("order_no"), reason=reason)
            items.append(
                {
                    "time": (r.get("issued_at") or "")[5:16],
                    "who": "",
                    "text": text,
                    "kind": "red",
                }
            )
        elif r.get("status") == "done":
            items.append(
                {
                    "time": (r.get("issued_at") or "")[5:16],
                    "who": "",
                    "text": t(
                        "对 {order}（{buyer} ¥{amount}）开具发票 {invoice}",
                        order=r.get("order_no"),
                        buyer=r.get("buyer_name") or "—",
                        amount=f"{r.get('gross_amount') or 0:,.2f}",
                        invoice=r.get("invoice_no") or "",
                    ).strip(),
                    "kind": "issue",
                }
            )
        elif r.get("status") == "fail":
            items.append(
                {
                    "time": (r.get("issued_at") or "")[5:16],
                    "who": "",
                    "text": t("对 {order} 开票/推送失败", order=r.get("order_no")),
                    "kind": "fail",
                }
            )
    items.sort(key=lambda h: h.get("time") or "", reverse=True)
    seen = set()
    out = []
    for h in items:
        k = (h["time"], h["text"])
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
        if len(out) >= 12:
            break
    return out


def issue_invoice(db: Session, hotel_id: int, order_id: int) -> dict[str, Any]:
    get_tax_provider().issue(db, hotel_id, order_id)
    o = db.get(Order, order_id)
    if not o or o.hotel_id != hotel_id:
        raise NotFoundError("订单不存在")
    existing = (
        db.query(Invoice)
        .filter(
            Invoice.hotel_id == hotel_id,
            Invoice.order_id == order_id,
            ~Invoice.invoice_no.startswith("R-"),
        )
        .order_by(Invoice.id.desc())
        .first()
    )
    if existing and (existing.status or "") not in ("failed", "open", "voided"):
        # 已红冲的蓝字票允许重开一张新蓝字
        red = (
            db.query(Invoice)
            .filter(
                Invoice.hotel_id == hotel_id,
                Invoice.order_id == order_id,
                Invoice.invoice_no == f"R-{existing.invoice_no}",
            )
            .first()
        )
        if not red:
            raise InvalidStateError("该订单已有发票，请走红冲后重开")
        existing = None  # 新建一张
    amts = _amounts(_f(o.total_amount), 0)
    inv = existing or Invoice(hotel_id=hotel_id, order_id=order_id)
    inv.invoice_no = inv.invoice_no or f"INV-{order_id:06d}-{int(datetime.now().timestamp()) % 10000}"
    if not existing:
        inv.invoice_no = f"INV-{order_id:06d}-{int(datetime.now().timestamp()) % 10000}"
    inv.amount = _money(amts["gross_amount"])
    inv.tax = _money(amts["tax_amount"])
    inv.status = "issued"
    inv.issued_at = datetime.now()
    if not existing:
        db.add(inv)
    db.commit()
    db.refresh(inv)
    return build_invoice_row(db, inv=inv, order=o)


def red_flush_invoice(db: Session, hotel_id: int, invoice_id: int, reason: str) -> dict[str, Any]:
    get_tax_provider().void(db, hotel_id, invoice_id, reason)
    if not (reason or "").strip():
        raise ValidationError("红冲必须填写原因（审计留痕）")
    src = db.get(Invoice, invoice_id)
    if not src or src.hotel_id != hotel_id:
        raise NotFoundError("发票不存在")
    if (src.status or "") == "red":
        raise InvalidStateError("该票已是红字发票")
    if (src.status or "") not in ("issued", "done", "sent"):
        # 兼容 open 以外的已开
        if (src.status or "") != "issued":
            raise InvalidStateError("仅已开发票可红冲")
    red_no = f"R-{src.invoice_no}"
    if db.query(Invoice).filter_by(hotel_id=hotel_id, invoice_no=red_no).first():
        raise InvalidStateError("已存在对应红字发票")
    # 跨月提示由前端展示；此处只落库
    red = Invoice(
        hotel_id=hotel_id,
        order_id=src.order_id,
        invoice_no=red_no,
        amount=-abs(_f(src.amount)),
        tax=-abs(_f(src.tax)),
        status="red",
        issued_at=datetime.now(),
    )
    db.add(red)
    # 原蓝字标记为已冲（不可再当有效票使用）
    src.status = "voided"
    db.commit()
    o = db.get(Order, src.order_id) if src.order_id else None
    if not o:
        return {"ok": True, "red_invoice_no": red_no, "reason": reason.strip()}
    row = build_invoice_row(db, inv=red, order=o)
    row["status"] = "red"
    row["original_invoice_no"] = src.invoice_no
    row["note"] = f"红冲原因：{reason.strip()}"
    return row
