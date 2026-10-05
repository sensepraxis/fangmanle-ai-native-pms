# SPDX-License-Identifier: Apache-2.0
"""报表中心 / 报表正文构建。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from finance.reports.metrics import (
    REV_STATUSES,
    _order_nights,
    _order_room_amount,
    _overlap_room_nights,
    _room_count,
    _sum_payments,
    _tax_rate,
    build_kpis,
    period_ops_kpis,
    period_revenue,
    period_room_revenue,
)
from finance.reports.period import (
    _compare_range,
    _delta_pct,
    _dt_range,
    _money,
    _parse_date,
    _pct,
    resolve_period,
)
from models import (
    Channel,
    ChannelAttribution,
    Invoice,
    LedgerEntry,
    NightAuditException,
    NightAuditLog,
    Order,
    Payment,
    Room,
    RoomType,
)

DEFAULT_FORMAT = {
    "vat_summary": "pdf",
    "tax_exempt": "pdf",
    "p_l": "pdf",
    "balance_sheet": "pdf",
    "cash_flow": "pdf",
    "trial_balance": "pdf",
    "adr_revpar_trend": "csv",
}

CATALOG: list[dict[str, Any]] = [
    {
        "key": "ops",
        "label": "日常运营",
        "reports": [
            {"code": "daily_operations", "name": "每日运营报告", "schedule": "日"},
            {"code": "manager_flash", "name": "经理快讯（Manager Flash）", "schedule": "日"},
            {"code": "mis", "name": "MIS 报告", "schedule": "月"},
        ],
    },
    {
        "key": "revenue",
        "label": "收入分析",
        "reports": [
            {"code": "revenue_summary", "name": "收入汇总", "schedule": "月"},
            {"code": "channel_sales", "name": "渠道销售分析", "schedule": "月"},
            {"code": "adr_revpar_trend", "name": "ADR/RevPAR 趋势", "schedule": "日"},
        ],
    },
    {
        "key": "usali",
        "label": "财务报表（USALI）",
        "reports": [
            {"code": "p_l", "name": "利润表 P&L", "schedule": "月"},
            {"code": "balance_sheet", "name": "资产负债表", "schedule": "月"},
            {"code": "cash_flow", "name": "现金流量表", "schedule": "月"},
            {"code": "trial_balance", "name": "试算平衡表", "schedule": "月"},
        ],
    },
    {
        "key": "ar_ap",
        "label": "应收应付",
        "reports": [
            {"code": "ar_aging", "name": "应收账龄（City Ledger）", "schedule": "日"},
            {"code": "ar_ap_summary", "name": "AR / AP 汇总", "schedule": "日"},
        ],
    },
    {
        "key": "tax",
        "label": "税务合规",
        "reports": [
            {"code": "vat_summary", "name": "增值税汇总", "schedule": "月"},
            {"code": "tax_exempt", "name": "免税收入", "schedule": "月"},
        ],
    },
    {
        "key": "night",
        "label": "夜审核查",
        "reports": [
            {"code": "night_daily", "name": "夜审日报", "schedule": "日", "link": "/c9-finance/night-audit"},
            {
                "code": "night_exceptions",
                "name": "夜审异常",
                "schedule": "日",
                "link": "/c9-finance/night-audit",
                "badge_from": "open_exceptions",
            },
        ],
    },
]

REPORT_META = {
    r["code"]: {**r, "category": c["label"], "category_key": c["key"]} for c in CATALOG for r in c["reports"]
}

from infra.i18n import TranslatingMap

METHOD_CN = TranslatingMap(
    {
        "wechat": "微信支付",
        "wechat_pos": "微信 POS",
        "alipay": "支付宝",
        "alipay_pos": "支付宝 POS",
        "ota": "OTA 预付",
        "card": "银行卡 / POS",
        "cash": "现金",
        "bank": "银行转账",
        "ar": "协议挂账",
        "deposit_offset": "押金冲抵",
        "direct": "直付",
    }
)

SOURCE_CN = TranslatingMap(
    {
        "ota": "OTA",
        "direct": "直销",
        "member": "会员",
        "corp": "协议",
        "wechat": "企微",
        "walkin": "散客上门",
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "ctrip": "携程",
        "meituan": "美团",
        "fliggy": "飞猪",
    }
)


def _section_table(title: str, columns: list[dict], rows: list[dict], note: str = "") -> dict:
    from infra.i18n import t

    cols = [{**c, "label": t(c.get("label") or "")} for c in columns]
    return {
        "type": "table",
        "title": t(title) if title else "",
        "columns": cols,
        "rows": rows,
        "note": t(note) if note else "",
    }


def _section_stats(title: str, items: list[dict]) -> dict:
    from infra.i18n import t

    its = [{**it, "lab": t(it.get("lab") or "")} for it in (items or [])]
    return {"type": "stats", "title": t(title) if title else "", "items": its}


def _empty_note(msg: str = "本期暂无库内数据") -> str:
    from infra.i18n import t

    return t(msg)


def _nav_with_badges(db: Session, hotel_id: int) -> list[dict]:
    from infra.i18n import t

    open_exc = db.query(NightAuditException).filter_by(hotel_id=hotel_id, status="open").count()
    cats = []
    for c in CATALOG:
        items = []
        for r in c["reports"]:
            sch = r.get("schedule")
            item = {
                "code": r["code"],
                "name": t(r["name"]),
                "schedule": t(sch) if sch else None,
                "link": r.get("link"),
                "badge": None,
            }
            if r.get("badge_from") == "open_exceptions" and open_exc > 0:
                item["badge"] = open_exc
            items.append(item)
        cats.append({"key": c["key"], "label": t(c["label"]), "reports": items})
    return cats


def build_center(
    db: Session,
    hotel_id: int,
    *,
    period: str = "month",
    start: Optional[str] = None,
    end: Optional[str] = None,
    compare: str = "yoy",
) -> dict:
    d0, d1, label = resolve_period(period, start=start, end=end)
    return {
        "period": period,
        "period_start": d0.isoformat(),
        "period_end": d1.isoformat(),
        "period_label": label,
        "compare": compare,
        "kpis": build_kpis(db, hotel_id, d0, d1, compare, period=period),
        "categories": _nav_with_badges(db, hotel_id),
        "default_report": "manager_flash",
        "readonly": True,
        "data_policy": "real_db_only",
    }


# ── 报表构建 ─────────────────────────────────────────────────────────


def _payment_rows(db: Session, hotel_id: int, d0: date, d1: date) -> list[dict]:
    start, end = _dt_range(d0, d1)
    rows = (
        db.query(Payment.method, func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id))
        .filter(Payment.hotel_id == hotel_id, Payment.paid_at >= start, Payment.paid_at < end)
        .group_by(Payment.method)
        .all()
    )
    total = sum(float(a or 0) for _, a, _ in rows) or 0.0
    out = []
    for method, amt, cnt in rows:
        a = _money(amt)
        out.append(
            {
                "method": METHOD_CN.get(method or "", method or "其他"),
                "amount": a,
                "share": f"{(a / total * 100):.1f}%" if total else "—",
                "count": int(cnt or 0),
                "fee": "—",
            }
        )
    out.sort(key=lambda x: -float(x["amount"] or 0))
    return out


def _room_status_stats(db: Session, hotel_id: int, d0: date, d1: date) -> list[dict]:
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    total = len(rooms)
    occ = sum(1 for r in rooms if (r.status or "").lower() in ("occupied", "occ", "dirty"))
    avail = max(0, total - occ)
    pending = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["pending", "confirmed", "reserved"]),
            Order.check_in >= d0,
            Order.check_in <= d1,
        )
        .count()
    )
    cancelled = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["cancelled", "canceled", "no_show"]),
            Order.check_in >= d0,
            Order.check_in <= d1,
        )
        .count()
    )
    comps = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in >= d0,
            Order.check_in <= d1,
            or_(Order.total_amount == 0, Order.total_amount.is_(None)),
            Order.status.in_(list(REV_STATUSES)),
        )
        .count()
    )
    return [
        {"lab": "可用房", "v": str(avail), "small": f"/ {total}"},
        {"lab": "已占用", "v": str(occ)},
        {"lab": "已预订未到", "v": str(pending)},
        {"lab": "取消 / 应到未到", "v": str(cancelled)},
        {"lab": "零房价单", "v": str(comps)},
    ]  # lab 经 _section_stats → t()


def _kpi_metric_rows(db: Session, hotel_id: int, d0: date, d1: date, compare: str) -> list[dict]:
    """关键指标：ADR/OCC/RevPAR 只用客房收入，不含 other_amount / 全店收款。"""
    cur = period_ops_kpis(db, hotel_id, d0, d1)
    rooms_n = cur["rooms"]
    occ_pct = cur["occ_pct"]
    adr = cur["adr"]
    revpar = cur["revpar"]
    sold = cur["sold_nights"]
    has_room = cur["room_revenue"] > 0 and sold > 0

    # MTD = 月初至今
    m0 = d1.replace(day=1)
    mtd = period_ops_kpis(db, hotel_id, m0, d1)
    mtd_adr = mtd["adr"]
    mtd_occ = mtd["occ_pct"]
    mtd_revpar = mtd["revpar"]
    mtd_ok = mtd["room_revenue"] > 0 and mtd["sold_nights"] > 0

    cmp = _compare_range(d0, d1, compare)
    ly_occ = ly_adr = ly_revpar = None
    if cmp:
        p0, p1, _ = cmp
        ly = period_ops_kpis(db, hotel_id, p0, p1)
        if ly["room_revenue"] > 0 and ly["sold_nights"] > 0:
            ly_adr = ly["adr"]
            ly_occ = ly["occ_pct"]
            ly_revpar = ly["revpar"]

    from infra.i18n import t

    def yoy_pt(cur_v: float, prev: Optional[float], unit: str = "%") -> tuple[str, str]:
        if prev is None:
            return "—", "flat"
        diff = round(cur_v - prev, 1)
        if unit == "pt":
            if diff > 0:
                return f"▲ +{diff}pt", "up"
            if diff < 0:
                return f"▼ {diff}pt", "down"
            return t("持平"), "flat"
        return _delta_pct(cur_v, prev)["label"], _delta_pct(cur_v, prev)["tone"]

    occ_yoy, occ_tone = yoy_pt(occ_pct, ly_occ, "pt")
    adr_yoy, adr_tone = (
        ("—", "flat") if ly_adr is None else (_delta_pct(adr, ly_adr)["label"], _delta_pct(adr, ly_adr)["tone"])
    )
    rp_yoy, rp_tone = (
        ("—", "flat")
        if ly_revpar is None
        else (_delta_pct(revpar, ly_revpar)["label"], _delta_pct(revpar, ly_revpar)["tone"])
    )

    src_note = ""
    if cur["source"] == "night_audit_proxy":
        src_note = t("（夜审未拆非房，ADR 以夜审营收作客房代理）")
    elif cur["source"] == "orders":
        src_note = t("（客房=订单总额−other_amount）")

    return [
        {
            "metric": t("出租率 OCC"),
            "today": f"{occ_pct}%" if sold else "—",
            "mtd": f"{mtd_occ}%" if mtd["sold_nights"] else "—",
            "ly": f"{ly_occ}%" if ly_occ is not None else "—",
            "yoy": occ_yoy,
            "yoy_tone": occ_tone,
        },
        {
            "metric": t("平均房价 ADR"),
            "today": f"¥{adr:,.2f}" if has_room else "—",
            "mtd": f"¥{mtd_adr:,.2f}" if mtd_ok else "—",
            "ly": f"¥{ly_adr:,.2f}" if ly_adr is not None else "—",
            "yoy": adr_yoy if has_room else (src_note or t("无客房收入")),
            "yoy_tone": adr_tone if has_room else "flat",
        },
        {
            "metric": "RevPAR",
            "today": f"¥{revpar:,.2f}" if rooms_n and has_room else "—",
            "mtd": f"¥{mtd_revpar:,.2f}" if rooms_n and mtd_ok else "—",
            "ly": f"¥{ly_revpar:,.2f}" if ly_revpar is not None else "—",
            "yoy": rp_yoy if has_room else "—",
            "yoy_tone": rp_tone if has_room else "flat",
        },
        {
            "metric": t("GOP 毛利率"),
            "today": "—",
            "mtd": "—",
            "ly": "—",
            "yoy": t("成本科目未接入"),
            "yoy_tone": "flat",
        },
    ]


def _income_rows(db: Session, hotel_id: int, d0: date, d1: date, compare: str) -> list[dict]:
    """收入侧：客房/其他与 period_room_revenue 同源（按重叠间夜分摊）；成本列留空。"""
    rr = period_room_revenue(db, hotel_id, d0, d1)
    rooms_rev = float(rr["amount"] or 0)
    other_rev = float(rr.get("other") or 0)
    if rooms_rev <= 0 and other_rev <= 0 and rr.get("source") == "empty":
        # 无订单重叠时：期间总营收整记为客房代理
        rooms_rev = period_revenue(db, hotel_id, d0, d1)["amount"]

    cmp = _compare_range(d0, d1, compare)
    prev_rooms = prev_other = 0.0
    if cmp:
        p0, p1, _ = cmp
        pr = period_room_revenue(db, hotel_id, p0, p1)
        prev_rooms = float(pr["amount"] or 0)
        prev_other = float(pr.get("other") or 0)
        if prev_rooms <= 0 and prev_other <= 0 and pr.get("source") == "empty":
            prev_rooms = period_revenue(db, hotel_id, p0, p1)["amount"]

    def row(name: str, rev: float, prev: float) -> dict:
        d = _delta_pct(rev, prev) if prev > 0 else {"label": "—", "tone": "flat"}
        return {
            "dept": name,
            "revenue": rev,
            "cost": "—",
            "profit": "—",
            "yoy": d["label"],
            "yoy_tone": d["tone"],
            "_row": "normal",
        }

    from infra.i18n import t

    rows = [
        row(t("客房 Rooms"), rooms_rev, prev_rooms),
        row(t("其他 Other（订单 other_amount）"), other_rev, prev_other),
    ]
    tot = _money(rooms_rev + other_rev)
    prev_tot = _money(prev_rooms + prev_other)
    d = _delta_pct(tot, prev_tot) if prev_tot > 0 else {"label": "—", "tone": "flat"}
    rows.append(
        {
            "dept": t("合计 Total"),
            "revenue": tot,
            "cost": "—",
            "profit": "—",
            "yoy": d["label"],
            "yoy_tone": d["tone"],
            "_row": "total",
        }
    )
    return rows


def _room_type_rows(db: Session, hotel_id: int, d0: date, d1: date) -> list[dict]:
    rows = []
    days = max(1, (d1 - d0).days + 1)
    for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all():
        avail = db.query(Room).filter_by(hotel_id=hotel_id, room_type_id=rt.id).count()
        orders = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.room_type_id == rt.id,
                Order.status.in_(list(REV_STATUSES)),
                Order.check_in.isnot(None),
                Order.check_out.isnot(None),
                Order.check_in <= d1,
                Order.check_out > d0,
            )
            .all()
        )
        rev = 0.0
        nights = 0
        for o in orders:
            n = _overlap_room_nights(o, d0, d1)
            if n <= 0:
                continue
            stay = max(1, (o.check_out - o.check_in).days) * max(1, int(o.rooms or 1))
            rev += _order_room_amount(o) * (n / stay)
            nights += n
        rev = _money(rev)
        adr = _money(rev / nights) if nights else _money(float(rt.base_price or 0))
        capacity = max(1, avail * days) if avail else 0
        occ = _pct(nights / capacity * 100) if capacity and nights else 0.0
        revpar = _money(rev / capacity) if capacity and rev else 0.0
        rows.append(
            {
                "room_type": rt.name,
                "avail": avail,
                "occ": f"{occ}%",
                "adr": f"¥{adr:,.2f}",
                "revpar": f"¥{revpar:,.2f}",
            }
        )
    return rows


def _build_manager_flash(db: Session, hotel_id: int, d0: date, d1: date, compare: str) -> tuple[list[dict], dict]:
    from infra.i18n import t

    rev = period_revenue(db, hotel_id, d0, d1)
    pay_list = _payment_rows(db, hotel_id, d0, d1)
    income = _income_rows(db, hotel_id, d0, d1, compare)
    metrics = _kpi_metric_rows(db, hotel_id, d0, d1, compare)
    rooms_n = _room_count(db, hotel_id)
    occ = db.query(Room).filter_by(hotel_id=hotel_id, status="occupied").count()

    sections = [
        _section_stats(
            t("房间状态（截至 {date}）", date=d1.isoformat()),
            _room_status_stats(db, hotel_id, d0, d1),
        ),
        _section_table(
            "期间收入（按订单拆分；成本未接入）",
            [
                {"key": "dept", "label": "部门"},
                {"key": "revenue", "label": "收入（¥）", "align": "num"},
                {"key": "cost", "label": "部门成本", "align": "num"},
                {"key": "profit", "label": "部门利润", "align": "num"},
                {"key": "yoy", "label": "对比", "align": "num"},
            ],
            income,
            note="",
        ),
        _section_table(
            "关键指标（KPIs）",
            [
                {"key": "metric", "label": "指标"},
                {"key": "today", "label": "本期", "align": "num"},
                {"key": "mtd", "label": "MTD", "align": "num"},
                {"key": "ly", "label": "对比期", "align": "num"},
                {"key": "yoy", "label": "涨跌", "align": "num"},
            ],
            metrics,
            note="",
        ),
        _section_table(
            "收银方式拆分（Payment）",
            [
                {"key": "method", "label": "支付方式"},
                {"key": "amount", "label": "金额（¥）", "align": "num"},
                {"key": "share", "label": "占比", "align": "num"},
                {"key": "count", "label": "笔数", "align": "num"},
                {"key": "fee", "label": "手续费", "align": "num"},
            ],
            pay_list or [],
            note=_empty_note("本期无收款记录") if not pay_list else "",
        ),
    ]
    return sections, {
        "rooms": {"total": rooms_n, "occupied": occ},
        "revenue": rev["amount"],
        "revenue_source": rev["source"],
    }


def _build_trial_balance(db: Session, hotel_id: int, d0: date, d1: date) -> tuple[list[dict], dict]:
    from infra.i18n import t

    rows_db = (
        db.query(
            LedgerEntry.account,
            func.coalesce(func.sum(LedgerEntry.debit), 0),
            func.coalesce(func.sum(LedgerEntry.credit), 0),
        )
        .filter(LedgerEntry.hotel_id == hotel_id, LedgerEntry.biz_date >= d0, LedgerEntry.biz_date <= d1)
        .group_by(LedgerEntry.account)
        .order_by(LedgerEntry.account.asc())
        .all()
    )
    rows = []
    debit = credit = 0.0
    for acc, d, c in rows_db:
        dv, cv = _money(d), _money(c)
        debit += dv
        credit += cv
        rows.append(
            {
                "code": "",
                "name": acc or t("未命名科目"),
                "debit": dv if dv else "—",
                "credit": cv if cv else "—",
                "_row": "normal",
            }
        )
    if rows:
        rows.append({"code": "", "name": t("合计"), "debit": _money(debit), "credit": _money(credit), "_row": "total"})
    balanced = abs(debit - credit) < 0.01 and bool(rows)
    note = "" if rows else _empty_note("本期无 ledger_entries 分录")
    status = t("借贷已平衡") if balanced else t("基于真实分录")
    sections = [
        _section_table(
            t("试算平衡表（{status}）", status=status),
            [
                {"key": "code", "label": "科目编码"},
                {"key": "name", "label": "科目名称"},
                {"key": "debit", "label": "借方", "align": "num"},
                {"key": "credit", "label": "贷方", "align": "num"},
            ],
            rows,
            note=note,
        )
    ]
    return sections, {"debit": debit, "credit": credit, "balanced": balanced, "rows": len(rows_db)}


def _build_p_l(db: Session, hotel_id: int, d0: date, d1: date) -> tuple[list[dict], dict]:
    from infra.i18n import t

    rr = period_room_revenue(db, hotel_id, d0, d1)
    rooms = float(rr["amount"] or 0)
    other = float(rr.get("other") or 0)
    if rooms <= 0 and other <= 0 and rr.get("source") == "empty":
        rooms = period_revenue(db, hotel_id, d0, d1)["amount"]
    rev = _money(rooms + other)
    rows = [
        {"item": t("客房收入 Rooms"), "amount": rooms, "_row": "normal"},
        {"item": t("其他收入（other_amount）"), "amount": other, "_row": "normal"},
        {"item": t("营业收入合计"), "amount": rev, "_row": "subtotal"},
        {"item": t("减：营业成本"), "amount": "—", "_row": "normal"},
        {"item": t("减：人工成本"), "amount": "—", "_row": "normal"},
        {"item": t("减：运营费用"), "amount": "—", "_row": "normal"},
        {"item": t("部门经营利润 GOP"), "amount": "—", "_row": "subtotal"},
        {"item": t("营业净利润 NOI"), "amount": "—", "_row": "total"},
    ]
    return [
        _section_table(
            "利润表（收入侧 · 成本未接入）",
            [{"key": "item", "label": "项目"}, {"key": "amount", "label": "金额（¥）", "align": "num"}],
            rows,
            note="",
        )
    ], {"revenue": rev, "gop": None, "noi": None}


def _channel_rows(db: Session, hotel_id: int, d0: date, d1: date) -> tuple[list[dict], float]:
    q = (
        db.query(
            ChannelAttribution.source,
            func.coalesce(func.sum(ChannelAttribution.attributed_rev), 0),
            func.count(ChannelAttribution.id),
        )
        .outerjoin(Order, Order.id == ChannelAttribution.order_id)
        .filter(ChannelAttribution.hotel_id == hotel_id)
        .filter(
            or_(
                and_(Order.check_in >= d0, Order.check_in <= d1),
                and_(
                    Order.id.is_(None),
                    ChannelAttribution.created_at >= datetime.combine(d0, datetime.min.time()),
                    ChannelAttribution.created_at < datetime.combine(d1 + timedelta(days=1), datetime.min.time()),
                ),
            )
        )
        .group_by(ChannelAttribution.source)
        .all()
    )
    rates: dict[str, float] = {}
    try:
        from finance.ota_commission_service import commission_map_for_pricing, rate_for_channel_code

        rates = commission_map_for_pricing(db)
    except Exception:
        rate_for_channel_code = None  # type: ignore
        rates = {c.code: float(c.commission_rate or 0) for c in db.query(Channel).all() if c.code}

    def _rate_for_source(src: str) -> float:
        if not src:
            return 0.0
        if rate_for_channel_code is not None:
            r = float(rate_for_channel_code(db, src, rates=rates) or 0)
            if r > 0:
                return r
            # 归因桶「ota」：取启用档案 OTA 均佣
            if src.lower() == "ota":
                otas = [float(v) for k, v in rates.items() if str(k).startswith("ota_") and float(v or 0) > 0]
                if otas:
                    return sum(otas) / len(otas)
            return 0.0
        return float(rates.get(src, rates.get(src.lower(), 0.0)) or 0.0)

    def _pct_text(rate: float) -> str:
        pct = round(rate * 10000) / 100
        return f"{pct:.2f}".rstrip("0").rstrip(".")

    def _yen(n: float) -> str:
        return f"¥{n:,.2f}"

    data, total = [], 0.0
    for s, a, c in q:
        total += float(a or 0)
    for s, a, c in q:
        amt = _money(a)
        order_ids = [
            r[0]
            for r in db.query(ChannelAttribution.order_id)
            .filter(ChannelAttribution.hotel_id == hotel_id, ChannelAttribution.source == s)
            .all()
            if r[0]
        ]
        nights = 0
        if order_ids:
            ords = db.query(Order).filter(Order.id.in_(order_ids), Order.check_in >= d0, Order.check_in <= d1).all()
            nights = _order_nights(ords)
        src = s or ""
        ch_label = SOURCE_CN.get(src, src or "其他")
        rate = _rate_for_source(src)
        comm = _money(amt * rate) if rate else 0.0
        if rate > 0:
            formula = f"{_yen(amt)} × {ch_label}佣金 {_pct_text(rate)}% = {_yen(comm)}"
        else:
            formula = "零佣金 / 直订"
        data.append(
            {
                "channel": ch_label,
                "revenue": amt,
                "nights": nights,
                "commission_formula": formula,
                "commission": comm,
                "share": f"{(amt / total * 100):.1f}%" if total else "—",
            }
        )
    data.sort(key=lambda x: -float(x["revenue"] or 0))
    return data, _money(total)


def _ar_aging_rows(db: Session, hotel_id: int) -> tuple[list[dict], dict]:
    from finance.ar_ap_service import list_workspace

    ws = list_workspace(db, hotel_id)
    today = date.today()
    buckets: dict[str, dict[str, float]] = {}
    for inv in ws.get("ar_invoices") or []:
        if inv.get("status") in ("settled", "bad_debt"):
            continue
        bal = float(inv.get("balance") or 0)
        if bal <= 0:
            continue
        name = inv.get("customer_name") or "未命名客户"
        due = _parse_date(inv.get("due_date"))
        days = (today - due).days if due else 0
        b = buckets.setdefault(name, {"d0_30": 0.0, "d31_60": 0.0, "d61_90": 0.0, "d90": 0.0, "total": 0.0})
        if days < 30:
            b["d0_30"] += bal
        elif days < 60:
            b["d31_60"] += bal
        elif days < 90:
            b["d61_90"] += bal
        else:
            b["d90"] += bal
        b["total"] += bal

    rows = []
    totals = {"d0_30": 0.0, "d31_60": 0.0, "d61_90": 0.0, "d90": 0.0, "total": 0.0}
    for name, b in sorted(buckets.items(), key=lambda x: -x[1]["total"]):
        row = {"customer": name, **{k: _money(v) for k, v in b.items()}}
        rows.append(row)
        for k in totals:
            totals[k] += b[k]
    if rows:
        from infra.i18n import t

        rows.append({"customer": t("合计"), **{k: _money(v) for k, v in totals.items()}, "_row": "total"})
    return rows, {"total": _money(totals["total"]), "aging": ws.get("aging") or {}}


# code -> builder(db, hotel_id, d0, d1, compare, *, code, rev) -> (sections, snap, link_override|None)
ReportBuilderFn = Callable[..., tuple[list[dict], dict[str, Any], Optional[str]]]
REPORT_BUILDERS: dict[str, ReportBuilderFn] = {}


def register_report_builder(*codes: str):
    def deco(fn: ReportBuilderFn):
        for c in codes:
            REPORT_BUILDERS[c] = fn
        return fn

    return deco


@register_report_builder("manager_flash", "daily_operations", "mis")
def _rb_ops_flash(db, hotel_id, d0, d1, compare, *, code, rev):
    sections, snap = _build_manager_flash(db, hotel_id, d0, d1, compare)
    if code == "daily_operations":
        rt_rows = _room_type_rows(db, hotel_id, d0, d1)
        sections = [
            sections[0],
            _section_table(
                "按房型运营指标",
                [
                    {"key": "room_type", "label": "房型"},
                    {"key": "avail", "label": "可用房", "align": "num"},
                    {"key": "occ", "label": "OCC", "align": "num"},
                    {"key": "adr", "label": "ADR", "align": "num"},
                    {"key": "revpar", "label": "RevPAR", "align": "num"},
                ],
                rt_rows,
                note=_empty_note("无房型主数据") if not rt_rows else "",
            ),
            sections[2],
        ]
    if code == "mis":
        today = date.today()
        day_rev = period_revenue(db, hotel_id, today, today)["amount"]
        y0 = date(today.year, 1, 1)
        ytd = period_revenue(db, hotel_id, y0, today)["amount"]
        cmp = _compare_range(d0, d1, compare)
        yoy_txt = "—"
        if cmp:
            p0, p1, lab = cmp
            prev = period_revenue(db, hotel_id, p0, p1)["amount"]
            if prev > 0:
                yoy_txt = _delta_pct(rev, prev, lab)["label"]
        sections.insert(
            0,
            _section_stats(
                "MIS 摘要（今日 / MTD / YTD）",
                [
                    {"lab": "今日营收", "v": f"¥{day_rev:,.0f}"},
                    {"lab": "MTD", "v": f"¥{rev:,.0f}"},
                    {"lab": "YTD", "v": f"¥{ytd:,.0f}"},
                    {"lab": "对比", "v": yoy_txt},
                ],
            ),
        )
    return sections, snap, None


@register_report_builder("channel_sales")
def _rb_channel_sales(db, hotel_id, d0, d1, compare, *, code, rev):
    data, total = _channel_rows(db, hotel_id, d0, d1)
    sections = [
        _section_table(
            "渠道销售分析",
            [
                {"key": "channel", "label": "渠道"},
                {"key": "revenue", "label": "收入（¥）", "align": "num"},
                {"key": "nights", "label": "间夜", "align": "num"},
                {"key": "commission_formula", "label": "计算过程"},
                {"key": "commission", "label": "佣金", "align": "num"},
                {"key": "share", "label": "收入占比", "align": "num"},
            ],
            data,
            note=_empty_note("本期无渠道归因记录") if not data else "",
        )
    ]
    return sections, {"channels": data, "total": total}, None


@register_report_builder("revenue_summary", "p_l")
def _rb_p_l(db, hotel_id, d0, d1, compare, *, code, rev):
    from infra.i18n import t

    sections, snap = _build_p_l(db, hotel_id, d0, d1)
    if code == "revenue_summary":
        sections[0]["title"] = t("收入汇总（订单口径）")
    return sections, snap, None


@register_report_builder("trial_balance")
def _rb_trial_balance(db, hotel_id, d0, d1, compare, *, code, rev):
    return (*_build_trial_balance(db, hotel_id, d0, d1), None)


@register_report_builder("balance_sheet")
def _rb_balance_sheet(db, hotel_id, d0, d1, compare, *, code, rev):
    sections = [
        _section_table(
            "资产负债表",
            [{"key": "item", "label": "项目"}, {"key": "amount", "label": "金额（¥）", "align": "num"}],
            [],
            note="",
        )
    ]
    return sections, {"assets": None}, None


@register_report_builder("cash_flow")
def _rb_cash_flow(db, hotel_id, d0, d1, compare, *, code, rev):
    from infra.i18n import t

    pay = _sum_payments(db, hotel_id, d0, d1)
    sections = [
        _section_table(
            "现金流量表（仅已接入的收款）",
            [{"key": "item", "label": "项目"}, {"key": "amount", "label": "金额（¥）", "align": "num"}],
            [
                {"item": t("经营活动现金流入（收款合计）"), "amount": pay, "_row": "subtotal"},
                {"item": t("投资活动现金流净额"), "amount": "—"},
                {"item": t("筹资活动现金流净额"), "amount": "—"},
                {"item": t("本期收款净额（可观测）"), "amount": pay, "_row": "total"},
            ],
            note="",
        )
    ]
    return sections, {"net": pay}, None


@register_report_builder("ar_aging")
def _rb_ar_aging(db, hotel_id, d0, d1, compare, *, code, rev):
    rows, info = _ar_aging_rows(db, hotel_id)
    sections = [
        _section_table(
            "应收账款账龄（City Ledger）",
            [
                {"key": "customer", "label": "客户"},
                {"key": "d0_30", "label": "0-30 天", "align": "num"},
                {"key": "d31_60", "label": "31-60 天", "align": "num"},
                {"key": "d61_90", "label": "61-90 天", "align": "num"},
                {"key": "d90", "label": ">90 天", "align": "num"},
                {"key": "total", "label": "合计", "align": "num"},
            ],
            rows,
            note=_empty_note("暂无未结应收单据") if not rows else "",
        )
    ]
    return sections, info, None


@register_report_builder("ar_ap_summary")
def _rb_ar_ap_summary(db, hotel_id, d0, d1, compare, *, code, rev):
    from finance.ar_ap_service import list_workspace
    from infra.i18n import t

    ws = list_workspace(db, hotel_id)
    kpi = ws.get("kpi") or {}
    aging = ws.get("aging") or {}
    ar = float(kpi.get("ar_balance") or 0)
    ap = float(kpi.get("ap_balance") or 0)
    sections = [
        _section_table(
            "AR / AP 汇总",
            [{"key": "item", "label": "项目"}, {"key": "amount", "label": "金额（¥）", "align": "num"}],
            [
                {"item": t("应收账款合计"), "amount": ar},
                {"item": t("其中 0-30 天"), "amount": float(aging.get("d0_30") or 0)},
                {"item": t("应付账款合计"), "amount": ap},
                {"item": t("净应收（AR-AP）"), "amount": _money(ar - ap), "_row": "total"},
            ],
            note="",
        )
    ]
    return sections, {"ar": ar, "ap": ap}, None


@register_report_builder("vat_summary")
def _rb_vat_summary(db, hotel_id, d0, d1, compare, *, code, rev):
    from infra.i18n import t

    rate = _tax_rate(db, hotel_id)
    start, end = _dt_range(d0, d1)
    inv_tax = (
        db.query(func.coalesce(func.sum(Invoice.tax), 0), func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.hotel_id == hotel_id, Invoice.issued_at >= start, Invoice.issued_at < end)
        .first()
    )
    tax_sum = _money(inv_tax[0] if inv_tax else 0)
    amt_sum = _money(inv_tax[1] if inv_tax else 0)
    if tax_sum > 0 or amt_sum > 0:
        taxable = _money(amt_sum - tax_sum) if amt_sum >= tax_sum else amt_sum
        vat = tax_sum
        gross = amt_sum
        note = t("来源：invoices.amount / tax（开票期间）。")
        rows = [
            {"item": t("应税销售额（不含税）"), "rate": f"{rate * 100:.2f}%", "amount": taxable},
            {"item": t("销项税额"), "rate": f"{rate * 100:.2f}%", "amount": vat},
            {"item": t("含税收入合计"), "rate": "—", "amount": gross, "_row": "total"},
        ]
    else:
        taxable = vat = gross = 0.0
        note = ""
        rows = []
    sections = [
        _section_table(
            t("增值税汇总（配置主税率 {rate}%）", rate=f"{rate * 100:.2f}"),
            [
                {"key": "item", "label": "项目"},
                {"key": "rate", "label": "税率", "align": "ctr"},
                {"key": "amount", "label": "金额（¥）", "align": "num"},
            ],
            rows,
            note=note,
        )
    ]
    return sections, {"vat": vat, "gross": gross, "rate": rate}, None


@register_report_builder("tax_exempt")
def _rb_tax_exempt(db, hotel_id, d0, d1, compare, *, code, rev):
    sections = [
        _section_table(
            "免税收入明细",
            [
                {"key": "type", "label": "免税类型"},
                {"key": "amount", "label": "金额（¥）", "align": "num"},
                {"key": "note", "label": "说明"},
            ],
            [],
            note="",
        )
    ]
    return sections, {"exempt": 0}, None


@register_report_builder("adr_revpar_trend")
def _rb_adr_revpar_trend(db, hotel_id, d0, d1, compare, *, code, rev):
    rooms_n = _room_count(db, hotel_id) or 1
    audits = (
        db.query(NightAuditLog)
        .filter(NightAuditLog.hotel_id == hotel_id, NightAuditLog.biz_date >= d0, NightAuditLog.biz_date <= d1)
        .order_by(NightAuditLog.biz_date.asc())
        .all()
    )
    rows = []
    for a in audits:
        day = a.biz_date
        if not day:
            continue
        day_kpi = period_ops_kpis(db, hotel_id, day, day)
        nights = day_kpi["sold_nights"] or int(a.room_nights or 0)
        room_rev = day_kpi["room_revenue"]
        if room_rev <= 0:
            room_rev = float(a.revenue or 0)
        adr = _money(room_rev / nights) if nights else 0.0
        occ = _pct(nights / rooms_n * 100) if nights else 0.0
        rows.append(
            {
                "date": day.isoformat(),
                "occ": f"{occ}%",
                "adr": adr,
                "revpar": _money(room_rev / rooms_n) if rooms_n and room_rev else 0.0,
                "room_revenue": _money(room_rev),
                "revenue": float(a.revenue or 0),
            }
        )
    sections = [
        _section_table(
            "ADR / OCC / RevPAR 趋势（按日）",
            [
                {"key": "date", "label": "日期"},
                {"key": "occ", "label": "OCC", "align": "num"},
                {"key": "adr", "label": "ADR", "align": "num"},
                {"key": "revpar", "label": "RevPAR", "align": "num"},
                {"key": "room_revenue", "label": "客房收入", "align": "num"},
                {"key": "revenue", "label": "夜审营收", "align": "num"},
            ],
            rows,
            note=_empty_note("所选期间无夜审日志") if not rows else "",
        )
    ]
    return sections, {"days": len(rows)}, None


@register_report_builder("night_exceptions")
def _rb_night_exceptions(db, hotel_id, d0, d1, compare, *, code, rev):
    from infra.i18n import t

    rows_db = (
        db.query(NightAuditException)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(NightAuditException.id.desc())
        .limit(50)
        .all()
    )
    rows = [
        {
            "biz_date": e.biz_date.isoformat() if e.biz_date else "—",
            "code": e.code or "—",
            "title": t(e.title) if e.title else t("异常"),
            "severity": e.severity or "mid",
            "status": e.status or "open",
        }
        for e in rows_db
    ]
    sections = [
        _section_table(
            "夜审异常列表",
            [
                {"key": "biz_date", "label": "营业日"},
                {"key": "code", "label": "代码"},
                {"key": "title", "label": "异常说明"},
                {"key": "severity", "label": "严重度", "align": "ctr"},
                {"key": "status", "label": "状态", "align": "ctr"},
            ],
            rows,
            note=_empty_note("当前无开放夜审异常") if not rows else "",
        )
    ]
    return sections, {"count": len(rows)}, "/c9-finance/night-audit"


@register_report_builder("night_daily")
def _rb_night_daily(db, hotel_id, d0, d1, compare, *, code, rev):
    audits = (
        db.query(NightAuditLog)
        .filter(NightAuditLog.hotel_id == hotel_id, NightAuditLog.biz_date >= d0, NightAuditLog.biz_date <= d1)
        .order_by(NightAuditLog.biz_date.desc())
        .limit(31)
        .all()
    )
    if not audits:
        audits = (
            db.query(NightAuditLog).filter_by(hotel_id=hotel_id).order_by(NightAuditLog.biz_date.desc()).limit(10).all()
        )
    rows = [
        {
            "biz_date": a.biz_date.isoformat() if a.biz_date else "—",
            "revenue": float(a.revenue or 0),
            "room_nights": int(a.room_nights or 0),
            "exceptions": int(a.exceptions or 0),
        }
        for a in audits
    ]
    sections = [
        _section_table(
            "夜审日报归档",
            [
                {"key": "biz_date", "label": "营业日"},
                {"key": "revenue", "label": "营收", "align": "num"},
                {"key": "room_nights", "label": "间夜", "align": "num"},
                {"key": "exceptions", "label": "异常数", "align": "num"},
            ],
            rows,
            note=_empty_note("暂无夜审日志") if not rows else "",
        )
    ]
    return sections, {"rows": len(rows)}, "/c9-finance/night-audit"


def build_report(
    db: Session,
    hotel_id: int,
    code: str,
    *,
    period: str = "month",
    start: Optional[str] = None,
    end: Optional[str] = None,
    compare: str = "yoy",
) -> dict:
    from infra.i18n import t

    d0, d1, label = resolve_period(period, start=start, end=end)
    meta = REPORT_META.get(code) or {"code": code, "name": code, "category": "其他", "schedule": "自定义"}
    rev_info = period_revenue(db, hotel_id, d0, d1)
    rev = rev_info["amount"]
    link = meta.get("link")
    sections: list[dict] = []
    snap: dict[str, Any] = {"revenue": rev, "revenue_source": rev_info["source"]}

    fn = REPORT_BUILDERS.get(code) or REPORT_BUILDERS.get("night_daily")
    if fn:
        sections, snap, link_ov = fn(db, hotel_id, d0, d1, compare, code=code, rev=rev)
        if link_ov:
            link = link_ov

    cmp_map = {
        "yoy": t("同比去年"),
        "mom": t("环比上期"),
        "budget": t("预算（未接入）"),
        "none": t("不对比"),
    }
    return {
        "code": code,
        "name": t(meta.get("name") or code),
        "category": t(meta.get("category") or ""),
        "schedule": t(meta.get("schedule") or ""),
        "period_start": d0.isoformat(),
        "period_end": d1.isoformat(),
        "period_label": label,
        "compare": compare,
        "compare_label": cmp_map.get(compare, t("同比去年")),
        "default_format": DEFAULT_FORMAT.get(code, "xlsx"),
        "link": link,
        "sections": sections,
        "snapshot": snap,
        "meta": "",
        "readonly": True,
        "data_policy": "real_db_only",
    }
