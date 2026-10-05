# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""客人流失风险：可解释规则分（Demo / 运营可用，非 ML 训练模型）。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Optional

from infra.i18n import t


def _as_date(v) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date) and not hasattr(v, "hour"):
        return v
    if hasattr(v, "date") and callable(v.date):
        try:
            return v.date()
        except Exception:
            pass
    s = str(v)[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def compute_churn_risk(
    *,
    orders: Iterable[Any],
    reviews: Iterable[Any] = (),
    wecom_bound: bool = False,
    today: Optional[date] = None,
) -> dict[str, Any]:
    """
    基于 RFM 思想 + 口碑/私域触点的规则打分，输出 0~1。

    因子（越高越易流失）：
    - 距上次离店/入住越久
    - 近 12 个月入住次数越少
    - 无未来预订
    - 历史评分偏低
    - 未企微建联（触达弱）
    """
    today = today or date.today()
    order_list = list(orders or [])
    review_list = list(reviews or [])
    factors: list[str] = []
    score = 0.28  # 基线：未知客略偏中性偏低

    # ---- 入住日期 ----
    stay_dates: list[date] = []
    future = False
    for o in order_list:
        if isinstance(o, dict):
            cin = _as_date(o.get("check_in"))
            cout = _as_date(o.get("check_out")) or cin
            st = (o.get("status") or "").lower()
        else:
            cin = _as_date(getattr(o, "check_in", None))
            cout = _as_date(getattr(o, "check_out", None)) or cin
            st = (getattr(o, "status", None) or "").lower()
        if cin and cin > today and st in ("pending", "confirmed", "checked_in", ""):
            future = True
        # 用离店日衡量「上次住完多久」；无则用入住日
        ref = cout or cin
        if ref and ref <= today:
            stay_dates.append(ref)
        elif cin and cin <= today:
            stay_dates.append(cin)

    stay_dates.sort()
    last_stay = stay_dates[-1] if stay_dates else None
    days_since = (today - last_stay).days if last_stay else None

    year_ago = today - timedelta(days=365)
    stays_12m = sum(1 for d in stay_dates if d >= year_ago)
    total_stays = len(stay_dates)

    if total_stays == 0:
        score += 0.22
        factors.append(t("暂无入住记录，活跃度未知"))
    elif days_since is not None:
        if days_since <= 30:
            score -= 0.16
            factors.append(t("近 {days} 天内有入住，粘性较好", days=days_since))
        elif days_since <= 90:
            score -= 0.06
            factors.append(t("距上次入住 {days} 天，仍较活跃", days=days_since))
        elif days_since <= 180:
            score += 0.10
            factors.append(t("距上次入住 {days} 天，活跃开始下降", days=days_since))
        elif days_since <= 365:
            score += 0.22
            factors.append(t("距上次入住 {days} 天，沉默风险上升", days=days_since))
        else:
            score += 0.34
            factors.append(t("距上次入住超过一年，流失风险偏高"))

    if total_stays > 0:
        if stays_12m == 0:
            score += 0.14
            factors.append(t("近 12 个月无入住"))
        elif stays_12m == 1:
            score += 0.06
            factors.append(t("近 12 个月仅 1 次入住"))
        elif stays_12m >= 4:
            score -= 0.12
            factors.append(t("近 12 个月入住 {n} 次，复购稳定", n=stays_12m))
        else:
            score -= 0.05
            factors.append(t("近 12 个月入住 {n} 次", n=stays_12m))

    if future:
        score -= 0.22
        factors.append(t("已有未来预订，短期流失风险低"))
    elif total_stays > 0:
        score += 0.06
        factors.append(t("暂无未来预订"))

    # ---- 评价 ----
    ratings: list[float] = []
    for r in review_list:
        if isinstance(r, dict):
            raw = r.get("rating")
        else:
            raw = getattr(r, "rating", None)
        try:
            if raw is not None:
                ratings.append(float(raw))
        except (TypeError, ValueError):
            continue
    if ratings:
        avg = sum(ratings) / len(ratings)
        if avg <= 3.0:
            score += 0.14
            factors.append(t("历史评分偏低（均分 {avg}）", avg=f"{avg:.1f}"))
        elif avg < 4.0:
            score += 0.05
            factors.append(t("历史评分一般（均分 {avg}）", avg=f"{avg:.1f}"))
        else:
            score -= 0.04
            factors.append(t("历史评分较好（均分 {avg}）", avg=f"{avg:.1f}"))

    # ---- 私域触达 ----
    if wecom_bound:
        score -= 0.07
        factors.append(t("已企微建联，可触达召回"))
    else:
        score += 0.05
        factors.append(t("未企微建联，召回通道较弱"))

    risk = round(min(0.95, max(0.05, score)), 2)
    return {
        "churn_risk": risk,
        "churn_method": "rule_v1",
        "churn_factors": factors[:6],
        "churn_inputs": {
            "days_since_last_stay": days_since,
            "stays_12m": stays_12m,
            "total_stays": total_stays,
            "has_future_booking": future,
            "wecom_bound": bool(wecom_bound),
            "review_avg": round(sum(ratings) / len(ratings), 2) if ratings else None,
        },
    }
