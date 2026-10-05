# SPDX-License-Identifier: Apache-2.0
"""财务对账：按库内订单 + 收款记录重建 recon_batches / recon_items。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from infra.i18n import get_locale
from infra.i18n import t as _t
from models import Channel, Guest, Order, Payment, ReconBatch, ReconItem

# 支付方式仅作「订单无渠道」时的兜底；有订单渠道时一律用订单渠道中文名
METHOD_FALLBACK_LABEL = {
    "alipay": ("alipay", "支付宝"),
    "alipay_pos": ("alipay", "支付宝"),
    "wechat": ("wechat", "微信支付"),
    "wechat_pos": ("wechat", "微信支付"),
    "cash": ("cash", "现金"),
    "card": ("pos", "POS"),
    "direct": ("direct", "散客直订"),
    "agreement": ("agreement", "协议客户"),
    "ar": ("agreement", "协议客户"),
    "transfer": ("bank", "银行转账"),
    "douyin": ("douyin", "抖音团购"),
    "xiaohongshu": ("xiaohongshu", "小红书"),
    "ctrip": ("ctrip", "携程"),
    "meituan": ("meituan", "美团酒店"),
    "fliggy": ("fliggy", "飞猪"),
    # 历史笼统 ota 不再作为展示名
    "ota": ("other_booking", "其他预订渠道"),
}

RECON_STATUSES = {"confirmed", "checked_in", "checked_out", "pending"}
PAY_OK = {"paid", "partial", "on_account"}


def _d(v) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _f(v) -> float:
    if v is None:
        return 0.0
    return float(v)


def _money(v: float) -> Decimal:
    return Decimal(str(round(v, 2)))


def channel_display(ch: Optional[Channel], db: Optional[Session] = None) -> tuple[str, str, float]:
    """返回 (code, 中文展示名, 佣金率)。禁止笼统 OTA。"""
    if not ch:
        return "direct", "散客直订", 0.0
    code = (ch.code or "direct").lower()
    name = (ch.name or code).strip()
    if code == "ota" or name.upper().startswith("OTA") or "OTA" in name:
        code = "other_booking"
        name = "其他预订渠道"
    rate = _f(ch.commission_rate)
    if db is not None:
        try:
            from finance.ota_commission_service import rate_for_channel

            rate = rate_for_channel(db, ch)
        except Exception:
            pass
    return code, name, rate


def resolve_batch_channel(
    order_ch: Optional[Channel],
    payment_method: Optional[str] = None,
    db: Optional[Session] = None,
) -> tuple[str, str, float]:
    """
    批次渠道：优先订单 channels 表中文名（携程/美团酒店/飞猪等）。
    仅无订单渠道且仅有收款方式时，才用支付方式兜底。
    """
    if order_ch:
        return channel_display(order_ch, db)
    m = (payment_method or "").lower()
    if m in METHOD_FALLBACK_LABEL:
        code, label = METHOD_FALLBACK_LABEL[m]
        return code, label, 0.0
    if m.endswith("_pos"):
        if "alipay" in m:
            return "alipay", "支付宝", 0.0
        if "wechat" in m:
            return "wechat", "微信支付", 0.0
        return "pos", "POS", 0.0
    return "direct", "散客直订", 0.0


def rebuild_recon_from_orders(
    db: Session,
    hotel_id: int,
    *,
    days: int = 14,
    as_of: Optional[date] = None,
) -> dict[str, Any]:
    """
    删除该门店既有对账批次，按订单 check_in 日 + 具体渠道（中文名）重建。
    PMS 应收 = 订单 total_amount；渠道实收优先取收款 received_amount，
    无收款明细时按渠道佣金率推算结算净额。
    """
    as_of = as_of or date.today()
    start = as_of - timedelta(days=max(1, days) - 1)

    channels = {c.id: c for c in db.query(Channel).all()}

    old_ids = [r.id for r in db.query(ReconBatch.id).filter_by(hotel_id=hotel_id).all()]
    if old_ids:
        db.query(ReconItem).filter(ReconItem.batch_id.in_(old_ids)).delete(synchronize_session=False)
        db.query(ReconBatch).filter(ReconBatch.id.in_(old_ids)).delete(synchronize_session=False)
        db.flush()

    pay_order_ids = {
        int(r[0])
        for r in db.query(Payment.order_id).filter(Payment.hotel_id == hotel_id, Payment.order_id.isnot(None)).all()
        if r[0] is not None
    }
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(tuple(RECON_STATUSES)),
            Order.check_in >= start,
            Order.check_in <= as_of,
            Order.payment_status.in_(tuple(PAY_OK)),
        )
        .all()
    )
    known = {o.id for o in orders}
    extra = []
    need = pay_order_ids - known
    if need:
        extra = (
            db.query(Order)
            .filter(Order.hotel_id == hotel_id, Order.id.in_(need), Order.status.in_(tuple(RECON_STATUSES)))
            .all()
        )
    all_orders = list(orders) + list(extra)

    pays_by_order: dict[int, list[Payment]] = defaultdict(list)
    for p in db.query(Payment).filter(Payment.hotel_id == hotel_id, Payment.order_id.isnot(None)).all():
        pays_by_order[int(p.order_id)].append(p)

    groups: dict[tuple[date, str], list[dict[str, Any]]] = defaultdict(list)

    for o in all_orders:
        biz = _d(o.check_in)
        if not biz:
            continue
        has_pay = o.id in pays_by_order
        if not (start <= biz <= as_of or has_pay):
            continue
        if biz > as_of + timedelta(days=90):
            continue
        if biz > as_of and not has_pay:
            continue

        order_ch = channels.get(o.channel_id) if o.channel_id else None
        pays = pays_by_order.get(o.id, [])

        if pays:
            code, label, commission = resolve_batch_channel(order_ch, pays[0].method if pays else None, db)
            recv = sum(_f(p.received_amount if p.received_amount is not None else p.amount) for p in pays)
            use_biz = biz if start <= biz <= as_of else (_d(pays[0].paid_at) or biz)
            groups[(use_biz, label)].append(
                {
                    "order": o,
                    "channel_code": code,
                    "channel_label": label,
                    "commission": commission,
                    "pms": _f(o.total_amount),
                    "channel": recv,
                    "pays": list(pays),
                    "from_payment": True,
                }
            )
        else:
            pms = _f(o.total_amount)
            if (o.payment_status or "") == "on_account":
                code, label, commission = "agreement", "协议客户", 0.0
                if order_ch:
                    code, label, commission = channel_display(order_ch, db)
                channel_amt = pms
            else:
                code, label, commission = resolve_batch_channel(order_ch, None, db)
                channel_amt = round(pms * (1.0 - commission), 2)
            if not (start <= biz <= as_of):
                continue
            groups[(biz, label)].append(
                {
                    "order": o,
                    "channel_code": code,
                    "channel_label": label,
                    "commission": commission,
                    "pms": pms,
                    "channel": channel_amt,
                    "pays": [],
                    "from_payment": False,
                }
            )

    created = 0
    item_count = 0
    for (biz, label), rows in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        merged: dict[int, dict[str, Any]] = {}
        for r in rows:
            oid = r["order"].id
            if oid not in merged:
                merged[oid] = dict(r)
                merged[oid]["pays"] = list(r["pays"])
            else:
                merged[oid]["channel"] = _f(merged[oid]["channel"]) + _f(r["channel"])
                if r["from_payment"] and not merged[oid]["from_payment"]:
                    merged[oid]["pms"] = r["pms"]
                    merged[oid]["from_payment"] = True
                elif r["from_payment"] and merged[oid]["from_payment"]:
                    merged[oid]["pms"] = _f(r["order"].total_amount)
                merged[oid]["pays"].extend(r["pays"])

        items = list(merged.values())
        if not items:
            continue
        for x in items:
            if x["from_payment"] and len(x["pays"]) > 1:
                x["pms"] = _f(x["order"].total_amount)
                x["channel"] = sum(
                    _f(p.received_amount if p.received_amount is not None else p.amount) for p in x["pays"]
                )

        pms_total = round(sum(_f(x["pms"]) for x in items), 2)
        channel_total = round(sum(_f(x["channel"]) for x in items), 2)
        variance = round(pms_total - channel_total, 2)
        abs_v = abs(variance)
        if abs_v < 0.01:
            status = "matched"
        elif abs_v < 200:
            status = "open"
        else:
            status = "conflict"

        ch_code = items[0].get("channel_code") or "direct"
        guest_hint = ""
        first = items[0]["order"]
        if first.guest_id:
            g = db.get(Guest, first.guest_id)
            if g and g.name:
                guest_hint = g.name
        note = _t(
            "{ch} · {date} · {n} 单",
            ch=label,
            date=biz.isoformat(),
            n=len(items),
        )
        if guest_hint and len(items) == 1:
            note = f"{items[0]['order'].order_no} · {guest_hint}"

        batch = ReconBatch(
            hotel_id=hotel_id,
            biz_date=biz,
            channel=label[:40],
            status=status,
            pms_total=_money(pms_total),
            channel_total=_money(channel_total),
            variance=_money(variance),
            note=note[:200],
        )
        db.add(batch)
        db.flush()
        created += 1

        for x in items:
            o = x["order"]
            ms = "matched"
            line_var = round(_f(x["pms"]) - _f(x["channel"]), 2)
            if abs(line_var) >= 0.01:
                ms = "conflict" if abs(line_var) >= 200 else "unmatched"
            db.add(
                ReconItem(
                    batch_id=batch.id,
                    hotel_id=hotel_id,
                    side="pms",
                    ref_no=o.order_no,
                    amount=_money(_f(x["pms"])),
                    match_status=ms,
                    note=(
                        f"渠道实收 {_f(x['channel']):.2f}"
                        + ("" if x["from_payment"] else f"；按佣金 {x['commission'] * 100:.1f}% 推算")
                    )[:200],
                    order_id=o.id,
                )
            )
            item_count += 1
            for p in x["pays"]:
                db.add(
                    ReconItem(
                        batch_id=batch.id,
                        hotel_id=hotel_id,
                        side="channel",
                        ref_no=p.pos_slip_no or f"PAY-{p.id}",
                        amount=_money(_f(p.received_amount if p.received_amount is not None else p.amount)),
                        match_status="matched" if abs(line_var) < 0.01 else ms,
                        note=(p.method or ch_code)[:200],
                        order_id=o.id,
                    )
                )
                item_count += 1

    db.commit()
    return {
        "hotel_id": hotel_id,
        "from": start.isoformat(),
        "to": as_of.isoformat(),
        "batches": created,
        "items": item_count,
    }


def _pct_text(rate: float) -> str:
    pct = round(float(rate or 0) * 100, 2)
    return f"{pct:.2f}".rstrip("0").rstrip(".")


def commission_info_for_channel_label(db: Session, channel_label: str | None) -> dict[str, Any]:
    """按批次渠道展示名匹配 OTA 佣金档案，返回配置费率。"""
    from finance.ota_commission_service import rate_for_channel

    label = (channel_label or "").strip()
    if not label:
        return {
            "commission_rate": 0.0,
            "commission_pct": 0.0,
            "commission_pct_text": "0",
            "commission_label": None,
            "channel_code": None,
            "channel_name": None,
        }

    channels = db.query(Channel).all()
    ch: Optional[Channel] = None
    # 精确匹配名称
    for c in channels:
        if (c.name or "").strip() == label:
            ch = c
            break
    # 名称包含 / 被包含
    if not ch:
        for c in channels:
            n = (c.name or "").strip()
            if n and (n in label or label in n):
                ch = c
                break
    # 编码出现在标签中（少见）
    if not ch:
        for c in channels:
            code = (c.code or "").strip().lower()
            if code and code in label.lower():
                ch = c
                break

    rate = rate_for_channel(db, ch) if ch else 0.0
    pct_s = _pct_text(rate)
    name = (ch.name if ch else label) or "渠道"
    return {
        "commission_rate": rate,
        "commission_pct": round(rate * 100, 2),
        "commission_pct_text": pct_s,
        "commission_label": _t("{name}佣金 {pct}%", name=name, pct=pct_s),
        "channel_code": ch.code if ch else None,
        "channel_name": ch.name if ch else label,
    }


def serialize_recon_batch(db: Session, batch: ReconBatch) -> dict[str, Any]:
    info = commission_info_for_channel_label(db, batch.channel)
    pms = _f(batch.pms_total)
    rate = float(info["commission_rate"] or 0)
    expected_cut = round(pms * rate, 2) if pms and rate else 0.0
    expected_net = round(pms * (1 - rate), 2) if pms else 0.0
    return {
        "id": batch.id,
        "hotel_id": batch.hotel_id,
        "biz_date": batch.biz_date.isoformat() if batch.biz_date else None,
        "channel": batch.channel,
        "status": batch.status,
        "pms_total": pms,
        "channel_total": _f(batch.channel_total),
        "variance": _f(batch.variance),
        "note": batch.note,
        "commission_rate": info["commission_rate"],
        "commission_pct": info["commission_pct"],
        "commission_pct_text": info["commission_pct_text"],
        "commission_label": info["commission_label"],
        "channel_code": info["channel_code"],
        "expected_commission": expected_cut,
        "expected_net": expected_net,
        "commission_formula": (
            f"¥{pms:,.2f} × (1 - {info['commission_label']}) = ¥{expected_net:,.2f}"
            if info.get("commission_label") and pms > 0
            else None
        ),
    }


def list_recon_batches_enriched(db: Session, hotel_id: int, *, limit: int = 80) -> list[dict[str, Any]]:
    rows = (
        db.query(ReconBatch)
        .filter_by(hotel_id=hotel_id)
        .order_by(ReconBatch.biz_date.desc(), ReconBatch.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_recon_batch(db, r) for r in rows]


def batch_detail_enriched(db: Session, bid: int) -> dict[str, Any] | None:
    batch = db.get(ReconBatch, bid)
    if not batch:
        return None
    items = db.query(ReconItem).filter_by(batch_id=bid).order_by(ReconItem.side.asc(), ReconItem.id.asc()).all()
    out_items = []
    for it in items:
        d = {
            "id": it.id,
            "batch_id": it.batch_id,
            "hotel_id": it.hotel_id,
            "side": it.side,
            "ref_no": it.ref_no,
            "amount": _f(it.amount),
            "match_status": it.match_status,
            "note": it.note,
            "order_id": it.order_id,
        }
        if it.order_id:
            o = db.get(Order, it.order_id)
            if o:
                gname = None
                if o.guest_id:
                    g = db.get(Guest, o.guest_id)
                    gname = g.name if g else None
                d["order"] = {
                    "id": o.id,
                    "order_no": o.order_no,
                    "guest_name": gname or o.guest_phone,
                    "status": o.status,
                    "payment_status": o.payment_status,
                    "total_amount": _f(o.total_amount),
                    "check_in": o.check_in.isoformat() if o.check_in else None,
                    "check_out": o.check_out.isoformat() if o.check_out else None,
                }
        out_items.append(d)
    return {
        "batch": serialize_recon_batch(db, batch),
        "items": out_items,
    }


def explain_recon_batch(db: Session, bid: int) -> dict[str, Any]:
    """
    基于库内对账明细调用 LLM：先陈述真实查询事实，再给出差异归因。
    返回 facts（结构化事实）、cause（归因文案）、confidence、raw。
    """
    import json
    import re

    from extensions.llm.facade import chat as llm_chat
    from extensions.llm.facade import llm_identity, load_llm_config

    data = batch_detail_enriched(db, bid)
    if not data:
        raise ValueError("batch not found")

    batch = data["batch"]
    pms_lines = []
    channel_lines = []
    for it in data["items"]:
        row = {
            "side": it.get("side"),
            "ref_no": it.get("ref_no"),
            "amount": it.get("amount"),
            "match_status": it.get("match_status"),
            "note": it.get("note"),
            "order_id": it.get("order_id"),
        }
        o = it.get("order")
        if o:
            row["order_no"] = o.get("order_no")
            row["guest_name"] = o.get("guest_name")
            row["order_status"] = o.get("status")
            row["payment_status"] = o.get("payment_status")
            row["order_total"] = o.get("total_amount")
            row["check_in"] = o.get("check_in")
            row["check_out"] = o.get("check_out")
        if it.get("side") == "pms":
            pms_lines.append(row)
        else:
            channel_lines.append(row)

    facts = {
        "batch_id": batch["id"],
        "biz_date": batch["biz_date"],
        "channel": batch["channel"],
        "status": batch["status"],
        "pms_total": batch["pms_total"],
        "channel_total": batch["channel_total"],
        "variance": batch["variance"],
        "variance_formula": "PMS应收 − 渠道实收",
        "note": batch["note"],
        "order_lines": pms_lines,
        "payment_lines": channel_lines,
        "order_count": len(pms_lines),
    }

    wants_en = str(get_locale() or "").lower().startswith("en")
    if wants_en:
        system = (
            "You are a hotel finance reconciliation assistant. The user provides a batch JSON from the database "
            "(real data — do not invent).\n"
            "Output exactly two English sections (plain text, minimal formatting):\n"
            "[1. Facts from ledger] Bullet: business date, channel, PMS receivable total, channel collected total, "
            "variance (signed), order count; then list each order no, guest, receivable, match status "
            "(aligned / to verify). Amounts to 2 decimals in CNY. Use only fields in the JSON. "
            "Use specific channel names (Ctrip/Meituan/Fliggy), never generic OTA.\n"
            "[2. Variance attribution] In 2–4 sentences, most likely causes (commission, partial payment, fees, "
            "refund timing) and actionable checks. If variance ≈ 0, say it can be closed.\n"
            "Final line: Confidence: NN% (NN integer 50–95).\n"
            "All user-visible text MUST be English. No Chinese except unavoidable proper nouns."
        )
        user = "Analyze this reconciliation batch (all from DB query):\n" + json.dumps(
            facts, ensure_ascii=False, default=str
        )
    else:
        system = (
            "你是酒店财务对账助手。用户会提供从数据库查出的对账批次 JSON（真实数据，不可编造）。\n"
            "请严格按两段输出纯中文（不要 Markdown 标题符号以外的花哨格式）：\n"
            "【一、库内事实】用条目列出：营业日、渠道、PMS应收合计、渠道实收合计、差额（含正负）、"
            "本批订单数；再逐单写出订单号、客人、应收金额、匹配状态（已对齐/待核）。金额保留两位小数，单位元。"
            "只陈述 JSON 中已有字段，不得虚构订单或金额。渠道请使用具体名称（如携程/美团/飞猪），不要写笼统的 OTA。\n"
            "【二、差异归因】基于上述事实，用 2～4 句说明最可能原因（如渠道佣金、部分收款、手续费、退款时点等），"
            "并给出可执行核对建议。若差额≈0，说明已对齐可关账。\n"
            "最后单独一行：置信度: NN%（NN 为 50～95 的整数）。"
        )
        user = "请分析以下对账批次（全部来自数据库查询结果）：\n" + json.dumps(facts, ensure_ascii=False, default=str)

    resp = llm_chat(db, [{"role": "user", "content": user}], system)
    raw = (resp.get("content") or "").strip()
    if wants_en and re.search(r"[\u4e00-\u9fff]", raw):
        # 模型仍吐中文时给英文规则兜底
        raw = (
            f"[1. Facts from ledger]\n"
            f"- Business date: {batch.get('biz_date')}\n"
            f"- Channel: {batch.get('channel')}\n"
            f"- PMS receivable: ¥{float(batch.get('pms_total') or 0):,.2f}\n"
            f"- Channel collected: ¥{float(batch.get('channel_total') or 0):,.2f}\n"
            f"- Variance: ¥{float(batch.get('variance') or 0):,.2f}\n"
            f"- Orders in batch: {facts.get('order_count')}\n\n"
            f"[2. Variance attribution]\n"
            f"Likely drivers include configured OTA commission, settlement lag (T+1), or partial/refund timing. "
            f"Drill into unmatched order lines and compare PMS receivable vs channel collected before closing.\n"
            f"Confidence: 72%"
        )

    confidence = 78
    m = re.search(r"(?:置信度|Confidence)\s*[:：]?\s*(\d{1,3})\s*%?", raw, re.I)
    if m:
        confidence = max(50, min(95, int(m.group(1))))

    cfg = load_llm_config(db)
    identity = llm_identity(cfg, resp if isinstance(resp, dict) else None)
    return {
        "batch_id": bid,
        "facts": facts,
        "cause": raw,
        "confidence": confidence,
        **identity,
    }
