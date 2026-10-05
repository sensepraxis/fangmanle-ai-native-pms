# SPDX-License-Identifier: Apache-2.0
"""私域总览 · 运营仪表盘聚合（只读，复用既有表）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from infra.currency import currency_symbol, format_money
from infra.i18n import t as _t
from models import (
    Guest,
    HotelMktSettings,
    MktCampaign,
    MktCoupon,
    MktCouponAutoRule,
    MktCouponAutoRuleTrigger,
    MktCouponGrant,
    MktGuestWallet,
    MktMemberLevel,
    WxLandingPage,
)


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _pct(n: float, d: float) -> float:
    if not d:
        return 0.0
    return round(n / d * 100, 1)


def _spark_from_counts(daily: list[int], height: int = 28) -> list[int]:
    """把日序列映射为 sparkline y 坐标（0=顶）。"""
    if not daily:
        return [height // 2] * 7
    mx = max(daily) or 1
    return [max(2, height - int(v / mx * (height - 4))) for v in daily]


def _last_7_days_counts(pairs: list[tuple[Optional[datetime], int]]) -> list[int]:
    today = datetime.utcnow().date()
    buckets = {today - timedelta(days=i): 0 for i in range(6, -1, -1)}
    for ts, n in pairs:
        if not ts:
            continue
        d = ts.date() if hasattr(ts, "date") else ts
        if d in buckets:
            buckets[d] += int(n or 1)
    return [buckets[today - timedelta(days=i)] for i in range(6, -1, -1)]


def _role_label(role: Optional[str], status: str) -> str:
    if status == "draft":
        return _t("草稿")
    return {
        "claim": _t("领券落地页"),
        "member": _t("会员落地页"),
        "returning": _t("回访落地页"),
    }.get(role or "claim", _t("落地页"))


_CAMPAIGN_STATUS_ZH = {
    "draft": "草稿",
    "pending": "待审批",
    "running": "进行中",
    "paused": "已暂停",
    "ended": "已结束",
    "archived": "已归档",
}


def _campaign_status_label(status: Optional[str]) -> str:
    key = str(status or "").strip().lower()
    return _t(_CAMPAIGN_STATUS_ZH.get(key, status or "活动"))


def _wow_pct(recent: list[int], prior: list[int]) -> Optional[float]:
    """近半段 vs 前半段环比（%）。"""
    a = sum(recent or [])
    b = sum(prior or [])
    if b <= 0:
        return None if a <= 0 else 100.0
    return round((a - b) / b * 100, 1)


def build_ai_ops(
    *,
    connected: bool,
    has_published: bool,
    published_n: int,
    draft_n: int,
    stale_draft_n: int,
    private_total: int,
    month_link: int,
    link_rate: float,
    month_active: int,
    dormant: int,
    redeem_rate: float,
    grants_total: int,
    used_total: int,
    unused_total: int,
    active_rules: int,
    has_levels: bool,
    receiver: str,
    grant_daily: list[int],
    used_daily: list[int],
    link_daily: list[int],
    access_score: int,
    growth_score: int,
    active_score: int,
    conv_score: int,
    score: int,
    channel_label: str = "",
    config_path: str = "/a-ai-core/private-channel",
    vendor: str = "wecom",
) -> dict[str, Any]:
    """
    私域总览 AI 能力（#1 诊断 / #2 本周作战 / #3 雷达）。
    基于真实指标的确定性推理，输出可一键跳转的动作，不依赖外部 LLM。
    """
    diagnosis: list[dict[str, Any]] = []
    week_plan: list[dict[str, Any]] = []
    radar: list[dict[str, Any]] = []
    ch_label = channel_label or _t("私域通道")
    cfg_path = config_path or "/a-ai-core/private-channel"

    def add_dx(
        severity: str,
        problem: str,
        cause: str,
        action: str,
        path: str,
        dim: str = "",
    ) -> None:
        diagnosis.append(
            {
                "id": f"dx-{len(diagnosis) + 1}",
                "severity": severity,  # bad | warn | info | ok
                "problem": problem,
                "cause": cause,
                "action": action,
                "path": path,
                "dim": dim,
            }
        )

    # —— #1 健康度诊断 ——
    if not connected:
        add_dx(
            "bad",
            _t("{label}尚未接入").format(label=ch_label),
            _t("私域建联与触达依赖当前消息通道，未启用则扫码/好友链路无法闭环"),
            _t("去配置私域通道"),
            cfg_path,
            "access",
        )
    if not has_published:
        add_dx(
            "bad" if not published_n else "warn",
            _t("缺少已发布落地页"),
            _t("到店扫码没有可打开的领券/会员入口，建联转化会卡在第一步"),
            _t("去装修发布"),
            "/acquisition/landing-pages",
            "attract",
        )
    if private_total > 0 and active_score < 55 and dormant >= 5:
        wake_est = max(1, int(round(dormant * 0.085)))
        add_dx(
            "warn",
            _t("约 {dormant} 位沉默客户").format(dormant=dormant),
            _t("近 30 天月活仅 {month_active}，占私域 {pct}%，互动不足").format(
                month_active=month_active,
                pct=_pct(month_active, max(private_total, 1)),
            ),
            _t("发起回归券（估唤醒 {wake_est} 人）").format(wake_est=wake_est),
            "/acquisition/coupons?tab=grant&sub=rules",
            "active",
        )
    if grants_total >= 8 and conv_score < 50:
        add_dx(
            "warn",
            _t("核销率 {redeem_rate}% 偏低").format(redeem_rate=redeem_rate),
            _t("面额/门槛与落地页引导可能不匹配，或发放对象过宽导致券沉睡"),
            _t("优化券与引导"),
            "/acquisition/coupons",
            "convert",
        )
    if active_rules <= 0:
        add_dx(
            "warn",
            _t("尚未启用自动发券规则"),
            _t("养客仍靠人工发放，难覆盖沉默唤醒、生日、退房回访等场景"),
            _t("配置自动规则"),
            "/acquisition/coupons?tab=grant&sub=rules",
            "convert",
        )
    if private_total > 0 and not has_levels:
        add_dx(
            "info",
            _t("会员等级体系未配置"),
            _t("私域客户已沉淀，但缺少等级/权益分层，难以做差异化养客"),
            _t("配置会员体系"),
            "/acquisition/members",
            "active",
        )
    if link_rate < 35:
        add_dx(
            "info",
            _t("建联率 {link_rate}% 仍有提升空间").format(link_rate=link_rate),
            _t("到店客未充分转入私域通道；领券页利益点或前台引导可能不足"),
            _t("优化领券页"),
            "/acquisition/landing-pages",
            "attract",
        )
    # 接待人主要为企微侧能力；其它 vendor 不强制
    if vendor == "wecom" and not str(receiver or "").strip():
        add_dx(
            "warn",
            _t("默认接待人未配置"),
            _t("新好友接入后可能无人接待，影响首触转化与信任"),
            _t("指定接待人"),
            cfg_path,
            "access",
        )

    if not diagnosis:
        add_dx(
            "ok",
            _t("私域运营整体健康"),
            _t("综合分 {score}，四维（接入/引流/活跃/转化）暂无明显短板").format(score=score),
            _t("查看本周计划"),
            "/acquisition",
            "",
        )

    # 严重度排序
    _sev_rank = {"bad": 0, "warn": 1, "info": 2, "ok": 3}
    diagnosis.sort(key=lambda x: _sev_rank.get(x["severity"], 9))
    diagnosis = diagnosis[:5]
    primary_advice = diagnosis[0]["problem"] + " → " + diagnosis[0]["action"]

    # —— #2 本周养客作战计划 ——
    candidates: list[tuple[int, dict[str, Any]]] = []

    def add_plan(prio: int, title: str, detail: str, action: str, path: str, tag: str) -> None:
        candidates.append(
            (
                prio,
                {
                    "id": f"plan-{len(candidates) + 1}",
                    "title": title,
                    "detail": detail,
                    "action": action,
                    "path": path,
                    "tag": tag,
                },
            )
        )

    if dormant >= 5:
        add_plan(
            10,
            _t("唤醒沉默私域客"),
            _t("锁定近 30 天低互动约 {dormant} 人，发回归券并配自动规则防漏触达").format(dormant=dormant),
            _t("去发券规则"),
            "/acquisition/coupons?tab=grant&sub=rules",
            _t("召回"),
        )
    if not has_published or draft_n > 0:
        add_plan(
            20 if not has_published else 45,
            _t("发布/打磨扫码落地页") if not has_published else _t("清理未发布草稿页"),
            (
                _t("补齐领券入口，保证到店扫码可建联")
                if not has_published
                else _t("仍有 {draft_n} 张草稿，优先发布领券或回访页").format(draft_n=draft_n)
            ),
            _t("去装修器"),
            "/acquisition/landing-pages",
            _t("获客"),
        )
    if active_rules <= 0:
        add_plan(
            15,
            _t("启用至少 1 条自动养客规则"),
            _t("建议优先：新加好友礼 / 退房回访 / 沉默唤醒，择一落地"),
            _t("配置规则"),
            "/acquisition/coupons?tab=grant&sub=rules",
            _t("自动化"),
        )
    if grants_total >= 8 and redeem_rate < 40:
        add_plan(
            25,
            _t("复盘低核销券批次"),
            _t("当前核销率 {redeem_rate}%，下调门槛或加强落地页利益点").format(redeem_rate=redeem_rate),
            _t("查看优惠券"),
            "/acquisition/coupons",
            _t("转化"),
        )
    if private_total > 0 and (not has_levels or active_score < 50):
        add_plan(
            35,
            _t("校准会员等级与权益"),
            _t("让活跃客看得见升级路径，用权益拉动再次到店"),
            _t("会员体系"),
            "/acquisition/members",
            _t("会员"),
        )
    if unused_total >= 15:
        add_plan(
            30,
            _t("清理未核销券堆积"),
            _t("未核销约 {unused_total} 张，可定向提醒或调整有效期策略").format(unused_total=unused_total),
            _t("看发放记录"),
            "/acquisition/coupons?tab=grant&sub=records",
            _t("库存"),
        )
    if month_link < 3 and has_published:
        add_plan(
            40,
            _t("加强到店扫码引导"),
            _t("本月新建联仅 {month_link}，检查前台话术与扫码物料曝光").format(month_link=month_link),
            _t("优化落地页"),
            "/acquisition/landing-pages",
            _t("获客"),
        )
    if score >= 75 and active_rules > 0:
        add_plan(
            50,
            _t("巩固积分兑换节奏"),
            _t("健康度良好，可用积分倍率/兑换券拉动周中到店"),
            _t("积分规则"),
            "/acquisition/points",
            _t("积分"),
        )

    candidates.sort(key=lambda x: x[0])
    week_plan = [c[1] for c in candidates[:5]]
    for i, p in enumerate(week_plan):
        p["id"] = f"plan-{i + 1}"
        p["order"] = i + 1

    if not week_plan:
        week_plan = [
            {
                "id": "plan-1",
                "order": 1,
                "title": _t("保持发券与核销节奏"),
                "detail": _t("本周无紧急短板，建议按既有规则巡检一次触发记录"),
                "action": _t("查看规则"),
                "path": "/acquisition/coupons?tab=grant&sub=rules",
                "tag": _t("巡检"),
            }
        ]

    # —— #3 异常与机会雷达 ——
    g_recent, g_prior = grant_daily[-3:], grant_daily[:4]
    u_recent, u_prior = used_daily[-3:], used_daily[:4]
    l_recent, l_prior = (link_daily or [0] * 7)[-3:], (link_daily or [0] * 7)[:4]
    grant_wow = _wow_pct(g_recent, g_prior)
    used_wow = _wow_pct(u_recent, u_prior)
    link_wow = _wow_pct(l_recent, l_prior)

    def add_radar(
        kind: str,
        severity: str,
        title: str,
        hypothesis: str,
        metric: str,
        path: str,
    ) -> None:
        radar.append(
            {
                "id": f"rd-{len(radar) + 1}",
                "kind": kind,  # alert | opportunity
                "severity": severity,
                "title": title,
                "hypothesis": hypothesis,
                "metric": metric,
                "path": path,
                "action": _t("去处理") if kind == "alert" else _t("去把握"),
            }
        )

    if used_wow is not None and used_wow <= -25 and sum(u_prior) >= 2:
        add_radar(
            "alert",
            "bad",
            _t("近几日核销明显下滑"),
            _t("可能原因：券吸引力下降、有效期集中到期、或到店客流偏弱"),
            _t("近 3 日核销环比 {used_wow}%").format(used_wow=used_wow),
            "/acquisition/coupons?tab=redeem",
        )
    if grant_wow is not None and grant_wow <= -30 and sum(g_prior) >= 3:
        add_radar(
            "alert",
            "warn",
            _t("发券节奏放缓"),
            _t("自动规则可能暂停，或人工发放减少，养客触达在减弱"),
            _t("近 3 日发放环比 {grant_wow}%").format(grant_wow=grant_wow),
            "/acquisition/coupons?tab=grant&sub=rules",
        )
    if link_wow is not None and link_wow <= -35 and sum(l_prior) >= 2:
        add_radar(
            "alert",
            "warn",
            _t("建联速度走弱"),
            _t("扫码入口曝光不足，或落地页未更新导致转化掉队"),
            _t("近 3 日建联环比 {link_wow}%").format(link_wow=link_wow),
            "/acquisition/landing-pages",
        )
    if unused_total >= max(20, int(grants_total * 0.55)) and grants_total >= 10:
        add_radar(
            "alert",
            "warn",
            _t("未核销券堆积"),
            _t("发放过宽或门槛偏高，券在客户钱包沉睡，占用营销预算"),
            _t("未核销 {unused_total} / 已发 {grants_total}").format(
                unused_total=unused_total, grants_total=grants_total
            ),
            "/acquisition/coupons?tab=grant&sub=records",
        )
    if stale_draft_n >= 2:
        add_radar(
            "alert",
            "info",
            _t("多张落地页长期草稿"),
            _t("装修未闭环，获客物料无法上线，影响扫码建联"),
            _t("滞留草稿 {stale_draft_n} 张").format(stale_draft_n=stale_draft_n),
            "/acquisition/landing-pages",
        )

    if dormant >= 8:
        add_radar(
            "opportunity",
            "info",
            _t("高价值沉默客可召回"),
            _t("私域池已有规模，定向回归券往往比广撒网更划算"),
            _t("沉默约 {dormant} 人").format(dormant=dormant),
            "/acquisition/coupons?tab=grant&sub=rules",
        )
    if redeem_rate >= 45 and active_rules <= 0 and private_total >= 10:
        add_radar(
            "opportunity",
            "info",
            _t("核销表现尚可，可放大自动规则"),
            _t("人工发券已验证吸引力，适合沉淀为自动触发以放大规模"),
            _t("核销率 {redeem_rate}% · 规则 0 条").format(redeem_rate=redeem_rate),
            "/acquisition/coupons?tab=grant&sub=rules",
        )
    if has_published and month_link >= 5 and not has_levels:
        add_radar(
            "opportunity",
            "info",
            _t("建联增长可叠加会员分层"),
            _t("本月建联活跃，补齐等级权益可提高复购与客单价"),
            _t("本月新建联 {month_link}").format(month_link=month_link),
            "/acquisition/members",
        )
    if score >= 80 and used_wow is not None and used_wow >= 15:
        add_radar(
            "opportunity",
            "ok",
            _t("核销动能上升"),
            _t("可顺势加投周中促销券或提高积分倍率，巩固势头"),
            _t("近 3 日核销环比 +{used_wow}%").format(used_wow=used_wow),
            "/acquisition/points",
        )

    if not radar:
        add_radar(
            "opportunity",
            "ok",
            _t("暂无显著异常"),
            _t("近一周发放/核销/建联波动平稳，保持巡检即可"),
            _t("健康度 {score}").format(score=score),
            "/acquisition",
        )

    return {
        "summary": primary_advice,
        "model": "rule-agent",
        "model_label": _t("私域运营 Agent"),
        "diagnosis": diagnosis,
        "week_plan": week_plan,
        "radar": radar,
    }


def private_overview(db: Session, hotel_id: int) -> dict[str, Any]:
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day30 = now - timedelta(days=30)
    day7 = now - timedelta(days=7)

    # —— 私域通道接入（防腐：不直接读 wecom SDK）——
    from extensions.messaging.facade import (
        CONFIG_PATH,
        channel_status,
        count_links_since,
        identity_source,
        link_daily_timestamps,
        private_guest_ids,
        vendor_label,
    )

    ch = channel_status(db)
    vendor = str(ch.get("vendor") or identity_source())
    ch_label = str(ch.get("label") or vendor_label(vendor))
    cfg_path = str(ch.get("config_path") or CONFIG_PATH)
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    connected = bool(ch.get("connected"))
    details = ch.get("details") if isinstance(ch.get("details"), dict) else {}
    receiver = (settings.default_receiver_userid if settings else None) or details.get("follow_userid") or ""

    # —— 落地页 ——
    pages = db.query(WxLandingPage).filter_by(hotel_id=hotel_id).all()
    published = [p for p in pages if p.status == "published"]
    drafts = [p for p in pages if p.status != "published"]
    has_published = len(published) > 0

    # —— 私域客户（当前 messaging vendor 身份 + 钱包）——
    private_ids = private_guest_ids(db, hotel_id=hotel_id)
    private_total = len(private_ids)

    # 本月新建联（linked_at）
    month_link = count_links_since(db, month_start) if private_ids else 0
    # 潜客粗估：本月有订单的客人 or 全量客人
    guests_total = db.query(Guest.id).count()
    link_rate = _pct(private_total, max(guests_total, 1))

    # 月活：近 30 天有发券/核销/钱包更新的私域客（无 last_active 字段时用代理）
    active_ids: set[int] = set()
    for gid, at in (
        db.query(MktCouponGrant.guest_id, MktCouponGrant.grant_at)
        .filter(MktCouponGrant.hotel_id == hotel_id, MktCouponGrant.grant_at >= day30)
        .all()
    ):
        if int(gid) in private_ids:
            active_ids.add(int(gid))
    for w in db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all():
        if w.updated_at and w.updated_at >= day30:
            active_ids.add(int(w.guest_id))
    month_active = (
        len(active_ids) if active_ids else min(private_total, max(1, private_total // 2)) if private_total else 0
    )

    # —— 券 ——
    coupons = db.query(MktCoupon).filter_by(hotel_id=hotel_id).all()
    grants = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id).all()
    active_batches = sum(1 for c in coupons if c.status == "active")
    grants_total = len(grants)
    used_total = sum(1 for g in grants if str(g.status or "").upper() in ("USED", "REDEEMED"))
    redeem_rate = _pct(used_total, grants_total)

    grants_month = [g for g in grants if g.grant_at and g.grant_at >= month_start]
    used_month = [
        g
        for g in grants
        if str(g.status or "").upper() in ("USED", "REDEEMED")
        and ((g.used_at and g.used_at >= month_start) or (g.grant_at and g.grant_at >= month_start))
    ]
    coupons_month = [c for c in coupons if c.created_at and c.created_at >= month_start]

    # 营销收益粗估：核销张数 × 面额均值（有 face_value 用，否则 50）
    face_vals = []
    for c in coupons:
        try:
            # face_json / amount 字段因模型而异
            v = getattr(c, "face_value", None) or getattr(c, "amount", None)
            if v is not None:
                face_vals.append(float(v))
        except Exception:
            pass
    avg_face = sum(face_vals) / len(face_vals) if face_vals else 50.0
    mkt_revenue = round(len(used_month) * avg_face, 0)

    # —— 自动发券规则 ——
    rules = db.query(MktCouponAutoRule).filter(MktCouponAutoRule.property_id == hotel_id).all()
    active_rules = sum(1 for r in rules if r.status == "active")

    # —— 健康度 ——
    access = (0.5 if connected else 0.0) + (0.5 if has_published else 0.0)
    access_score = round(access * 100)
    # 引流：私域占比映射
    growth_score = round(_clamp(link_rate * 1.1, 0, 100))
    active_score = round(_pct(month_active, max(private_total, 1)))
    conv_score = round(_clamp(redeem_rate * 1.3, 0, 100))
    score = round(access_score * 0.25 + growth_score * 0.25 + active_score * 0.25 + conv_score * 0.25)
    if score >= 80:
        level = _t("健康")
    elif score >= 60:
        level = _t("一般")
    else:
        level = _t("待改善")
    dormant = max(0, private_total - month_active)
    if active_score < 60 and dormant > 0:
        advice = _t("沉默客户约 {dormant} 位，建议发起「回归券」自动发券，预计唤醒约 8.5%。").format(dormant=dormant)
    elif conv_score < 45:
        advice = _t("核销率 {redeem_rate}% 偏低，建议优化券面额或落地页引导。").format(redeem_rate=redeem_rate)
    elif not has_published:
        advice = _t("尚未发布落地页，建议先装修并发布领券入口。")
    elif not connected:
        advice = _t("{label}尚未启用，请先完成私域通道配置。").format(label=ch_label)
    else:
        advice = _t("运营健康，保持发券与养客节奏。")

    # sparkline：近 7 日发券
    grant_daily = _last_7_days_counts([(g.grant_at, 1) for g in grants])
    used_daily = _last_7_days_counts(
        [(g.used_at or g.grant_at, 1) for g in grants if str(g.status or "").upper() in ("USED", "REDEEMED")]
    )
    link_daily = _last_7_days_counts([(ts, 1) for ts in link_daily_timestamps(db)])
    unused_total = max(0, grants_total - used_total)

    hero_kpis = [
        {
            "key": "private_cust",
            "label": _t("私域客户"),
            "value": private_total,
            "unit": "",
            "delta_pct": round(_pct(month_link, max(private_total - month_link, 1)), 1) if private_total else 0,
            "delta_label": _t("本月新建联 {month_link}").format(month_link=month_link),
            "trend": grant_daily,
            "spark_y": _spark_from_counts(grant_daily),
            "tone": "pri",
        },
        {
            "key": "link_rate",
            "label": _t("建联率"),
            "value": link_rate,
            "unit": "%",
            "delta_pct": 0,
            "delta_label": _t("私域 {private_total} / 客户 {guests_total}").format(
                private_total=private_total, guests_total=guests_total
            ),
            "trend": grant_daily,
            "spark_y": _spark_from_counts(grant_daily),
            "tone": "ok",
        },
        {
            "key": "month_active",
            "label": _t("月活客户"),
            "value": month_active,
            "unit": "",
            "delta_pct": round(_pct(month_active, max(private_total, 1)) - 50, 1),
            "delta_label": _t("占私域 {pct}%").format(pct=_pct(month_active, max(private_total, 1))),
            "trend": used_daily,
            "spark_y": _spark_from_counts(used_daily),
            "tone": "warn",
            "down": month_active < private_total * 0.4 if private_total else False,
        },
        {
            "key": "mkt_revenue",
            "label": _t("营销收益"),
            "value": int(mkt_revenue),
            "unit": currency_symbol(),
            "delta_pct": 0,
            "delta_label": _t("本月核销 {n} 张估").format(n=len(used_month)),
            "trend": used_daily,
            "spark_y": _spark_from_counts(used_daily),
            "tone": "pink",
        },
    ]

    # —— 闭环：到店扫码建联 → 沉淀会员 → 自动养客（均落在私域运营内）——
    has_levels = db.query(MktMemberLevel).filter_by(hotel_id=hotel_id).count() > 0

    stale_drafts = [p for p in drafts if not p.updated_at or p.updated_at < day7]
    ai_ops = build_ai_ops(
        connected=connected,
        has_published=has_published,
        published_n=len(published),
        draft_n=len(drafts),
        stale_draft_n=len(stale_drafts),
        private_total=private_total,
        month_link=month_link,
        link_rate=link_rate,
        month_active=month_active,
        dormant=dormant,
        redeem_rate=redeem_rate,
        grants_total=grants_total,
        used_total=used_total,
        unused_total=unused_total,
        active_rules=active_rules,
        has_levels=has_levels,
        receiver=str(receiver or ""),
        grant_daily=grant_daily,
        used_daily=used_daily,
        link_daily=link_daily,
        access_score=access_score,
        growth_score=growth_score,
        active_score=active_score,
        conv_score=conv_score,
        score=score,
        channel_label=ch_label,
        config_path=cfg_path,
        vendor=vendor,
    )
    advice = ai_ops.get("summary") or advice

    flow = [
        {
            "step": 1,
            "name": _t("到店扫码建联"),
            "status": "done" if has_published else ("warn" if pages else "bad"),
            "badge": (
                _t("已发布 {published} · 本月建联 {month_link}").format(published=len(published), month_link=month_link)
                if month_link
                else _t("已发布 {published} / 草稿 {drafts}").format(published=len(published), drafts=len(drafts))
            ),
            "path": "/acquisition/landing-pages",
        },
        {
            "step": 2,
            "name": _t("沉淀私域会员"),
            "status": "done" if (private_total > 0 and has_levels) else ("warn" if private_total > 0 else "bad"),
            "badge": (
                _t("私域客户 {private_total}").format(private_total=private_total)
                if private_total
                else _t("待配置会员体系")
            ),
            "path": "/acquisition/members",
        },
        {
            "step": 3,
            "name": _t("自动发券养客"),
            "status": "done" if active_rules > 0 else "warn",
            "badge": (
                _t("在跑 {active_rules} 条规则").format(active_rules=active_rules)
                if active_rules
                else _t("暂无启用规则")
            ),
            "path": "/acquisition/coupons?tab=grant&sub=rules",
        },
    ]

    # —— 最近动态 ——
    activities: list[dict] = []
    for g in sorted(grants, key=lambda x: x.grant_at or datetime.min, reverse=True)[:8]:
        c = db.get(MktCoupon, g.coupon_id)
        guest = db.get(Guest, g.guest_id)
        ts = g.grant_at.strftime("%m-%d %H:%M") if g.grant_at else "—"
        ch = str(getattr(g, "channel", None) or getattr(g, "source", None) or "")
        tag = _t("自动发券") if ch.startswith("auto") or ch in ("rule", "auto_rule") else _t("发放")
        cname = c.name if c else g.code
        gname = guest.name if guest else g.guest_id
        if str(g.status or "").upper() in ("USED", "REDEEMED"):
            activities.append(
                {
                    "ts": (g.used_at or g.grant_at).strftime("%m-%d %H:%M") if (g.used_at or g.grant_at) else ts,
                    "text": _t("核销「{name}」→ {guest}", name=cname, guest=gname),
                    "tag": _t("核销成功"),
                    "tag_kind": "use",
                }
            )
        else:
            activities.append(
                {
                    "ts": ts,
                    "text": _t("发放「{name}」→ {guest}", name=cname, guest=gname),
                    "tag": tag,
                    "tag_kind": "grant",
                }
            )
    for camp in (
        db.query(MktCampaign).filter_by(hotel_id=hotel_id).order_by(MktCampaign.updated_at.desc()).limit(3).all()
    ):
        st_label = _campaign_status_label(camp.status)
        activities.append(
            {
                "ts": camp.updated_at.strftime("%m-%d %H:%M") if camp.updated_at else "—",
                "text": _t("活动「{name}」状态 → {status}", name=camp.name, status=st_label),
                "tag": st_label,
                "tag_kind": "active",
            }
        )
    # 自动规则触发
    try:
        for tr in db.query(MktCouponAutoRuleTrigger).order_by(MktCouponAutoRuleTrigger.id.desc()).limit(5).all():
            rule = db.get(MktCouponAutoRule, tr.rule_id)
            if rule and rule.property_id != hotel_id:
                continue
            at = getattr(tr, "triggered_at", None) or getattr(tr, "created_at", None)
            activities.append(
                {
                    "ts": at.strftime("%m-%d %H:%M") if at else "—",
                    "text": _t("规则「{name}」触发发券", name=(rule.name if rule else tr.rule_id)),
                    "tag": _t("自动发券"),
                    "tag_kind": "grant",
                }
            )
    except Exception:
        pass
    activities = activities[:12]

    # —— 待办 ——
    todos: list[dict] = []
    if stale_drafts:
        names = "、".join((p.title or p.page_key or _t("未命名")) for p in stale_drafts[:3])
        todos.append(
            {
                "severity": "bad",
                "title": _t("{n} 张落地页未发布").format(n=len(stale_drafts)),
                "desc": _t("「{names}」等仍为草稿").format(names=names),
                "action": _t("去装修"),
                "path": "/acquisition/landing-pages",
            }
        )
    # 券临期：valid_to 字段
    expiring = []
    for c in coupons:
        vt = getattr(c, "valid_to", None) or getattr(c, "end_at", None)
        if vt and isinstance(vt, datetime) and now <= vt <= now + timedelta(hours=48) and c.status == "active":
            expiring.append(c)
    if expiring:
        todos.append(
            {
                "severity": "warn",
                "title": _t("{n} 张券 48h 内到期").format(n=len(expiring)),
                "desc": _t("含「{name}」等仍在投放").format(name=expiring[0].name),
                "action": _t("查看"),
                "path": "/acquisition/coupons",
            }
        )
    if vendor == "wecom" and not str(receiver).strip():
        todos.append(
            {
                "severity": "warn",
                "title": _t("默认接待人未配置"),
                "desc": _t("新客户加好友后可能无人接待，请指定兜底接待人"),
                "action": _t("设置"),
                "path": cfg_path,
            }
        )
    if dormant >= 5:
        todos.append(
            {
                "severity": "info",
                "title": _t("沉默客户唤醒建议"),
                "desc": _t("约 {dormant} 位近 30 天低互动私域客户，可发起回归券").format(dormant=dormant),
                "action": _t("发起"),
                "path": "/acquisition/coupons?tab=grant&sub=rules",
            }
        )
    todos.append(
        {
            "severity": "info",
            "title": _t("本月营销数据已汇总"),
            "desc": _t("发放 {grants} · 核销 {used} · 估收益 {rev}").format(
                grants=len(grants_month),
                used=len(used_month),
                rev=format_money(int(mkt_revenue)),
            ),
            "action": _t("查看"),
            "path": "/acquisition",
        }
    )

    # —— 看板 6 卡 ——
    board = [
        {
            "key": "active_batch",
            "label": _t("活跃券批次"),
            "value": active_batches,
            "delta": _t("共 {n} 批次").format(n=len(coupons)),
            "chart": "line",
            "tone": "pri",
        },
        {
            "key": "redeem_month",
            "label": _t("本月核销"),
            "value": len(used_month),
            "delta": _t("核销率 {redeem_rate}%").format(redeem_rate=redeem_rate),
            "chart": "line",
            "tone": "ok",
        },
        {
            "key": "landing",
            "label": _t("已发布落地页"),
            "value": len(published),
            "delta": _t("草稿 {n}").format(n=len(drafts)),
            "chart": "bar",
            "tone": "pri",
        },
        {
            "key": "grants",
            "label": _t("已发放券"),
            "value": grants_total,
            "delta": _t("私域发放累计"),
            "chart": "line",
            "tone": "violet",
        },
        {
            "key": "private",
            "label": _t("私域客户"),
            "value": private_total,
            "delta": _t("本月建联 {month_link}").format(month_link=month_link),
            "chart": "line",
            "tone": "pink",
        },
        {
            "key": "link",
            "label": _t("建联转化"),
            "value": link_rate,
            "unit": "%",
            "delta": _t("客户池 {guests_total}").format(guests_total=guests_total),
            "chart": "line",
            "tone": "cyan",
        },
    ]

    # —— 漏斗 ——
    create_n = max(len(coupons_month), len(coupons))
    grant_n = len(grants_month) if grants_month else grants_total
    claim_n = grant_n  # 本系统发放即领取
    redeem_n = len(used_month) if used_month else used_total
    repurchase_n = max(0, redeem_n // 2)  # 无复购订单链时保守估算，前端标注「估」
    base = max(create_n, 1)
    funnel = {
        "create": create_n,
        "grant": grant_n,
        "claim": claim_n,
        "redeem": redeem_n,
        "repurchase": repurchase_n,
        "rows": [
            {"key": "create", "name": _t("建券"), "value": create_n, "pct": 100},
            {"key": "grant", "name": _t("已发放"), "value": grant_n, "pct": _pct(grant_n, base)},
            {"key": "claim", "name": _t("客户领取"), "value": claim_n, "pct": _pct(claim_n, base)},
            {"key": "redeem", "name": _t("到店核销"), "value": redeem_n, "pct": _pct(redeem_n, base)},
            {"key": "repurchase", "name": _t("复购（估）"), "value": repurchase_n, "pct": _pct(repurchase_n, base)},
        ],
    }

    landing_pages = []
    for p in sorted(pages, key=lambda x: (0 if x.status == "published" else 1, -(x.id or 0)))[:8]:
        # 无访客字段：用页面 id 派生友好的 0 或按 grant 关联估
        visit = 0
        convert = 0.0
        landing_pages.append(
            {
                "id": p.id,
                "name": p.title or p.published_title or p.page_key or _t("页面#{id}").format(id=p.id),
                "type": _role_label(getattr(p, "page_role", None), p.status or "draft"),
                "status": p.status or "draft",
                "visit": visit,
                "convert": convert,
                "path": f"/acquisition/landing-pages?edit={p.id}",
            }
        )

    shortcuts = [
        {"icon": "web", "label": _t("页面编辑器"), "path": "/acquisition/landing-pages"},
        {"icon": "confirmation_number", "label": _t("优惠券中心"), "path": "/acquisition/coupons"},
        {"icon": "auto_awesome", "label": _t("自动发券规则"), "path": "/acquisition/coupons?tab=grant&sub=rules"},
        {"icon": "workspace_premium", "label": _t("会员体系设置"), "path": "/acquisition/members"},
        {"icon": "toll", "label": _t("积分规则"), "path": "/acquisition/points"},
        {"icon": "settings", "label": _t("私域通道"), "path": cfg_path},
    ]

    channel_payload = {
        "vendor": vendor,
        "label": ch_label,
        "enabled": connected,
        "status": ch.get("status") or ("enabled" if connected else "unconfigured"),
        "hint": ch.get("hint") or "",
        "corp_id_hint": ch.get("hint") or "",  # 兼容旧前端
        "default_receiver_userid": receiver or None,
        "config_path": cfg_path,
        "capabilities": ch.get("capabilities") or {},
    }

    return {
        "health": {
            "score": score,
            "level": level,
            "week_delta": 0,
            "dims": {
                "access": access_score,
                "attract": growth_score,
                "active": active_score,
                "convert": conv_score,
            },
            "advice": advice,
            "dormant": dormant,
        },
        "ai_ops": ai_ops,
        "hero_kpis": hero_kpis,
        "flow": flow,
        "activities": activities,
        "todos": todos,
        "board": board,
        "funnel": funnel,
        "landing_pages": landing_pages,
        "shortcuts": shortcuts,
        "channel": channel_payload,
        # 兼容旧前端字段名 wecom
        "wecom": channel_payload,
        # 兼容旧前端字段
        "kpi": {
            "coupon_batches_active": active_batches,
            "grants": grants_total,
            "used": used_total,
            "redeem_rate": redeem_rate,
            "landing_published": len(published),
            "private_customers": private_total,
        },
        "timeline": [{"at": a["ts"], "text": a["text"], "kind": a.get("tag_kind") or "grant"} for a in activities[:8]],
        "generated_at": now.isoformat() + "Z",
    }
