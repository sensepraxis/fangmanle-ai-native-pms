# SPDX-License-Identifier: Apache-2.0
"""报表期间解析与金额/对比辅助。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def resolve_period(
    period: str = "month",
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    as_of: Optional[date] = None,
) -> tuple[date, date, str]:
    today = as_of or date.today()
    p = (period or "month").lower()
    if p == "custom":
        d0 = _parse_date(start) or today.replace(day=1)
        d1 = _parse_date(end) or today
        if d0 > d1:
            d0, d1 = d1, d0
        return d0, d1, f"{d0.isoformat()} ~ {d1.isoformat()}"
    if p == "today":
        return today, today, today.isoformat()
    if p == "week":
        d0 = today - timedelta(days=today.weekday())
        return d0, today, f"{d0.isoformat()} ~ {today.isoformat()}"
    if p == "year":
        d0 = date(today.year, 1, 1)
        return d0, today, f"{d0.isoformat()} ~ {today.isoformat()}"
    d0 = today.replace(day=1)
    return d0, today, f"{d0.isoformat()} ~ {today.isoformat()}"


def _money(n: float) -> float:
    return round(float(n or 0), 2)


def _pct(n: float) -> float:
    return round(float(n or 0), 1)


def _as_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return _parse_date(str(v))


def _dt_range(d0: date, d1: date) -> tuple[datetime, datetime]:
    return datetime.combine(d0, datetime.min.time()), datetime.combine(d1 + timedelta(days=1), datetime.min.time())


def _yoy_range(d0: date, d1: date) -> tuple[date, date]:
    try:
        return d0.replace(year=d0.year - 1), d1.replace(year=d1.year - 1)
    except ValueError:
        return d0.replace(year=d0.year - 1, day=28), d1.replace(year=d1.year - 1, day=28)


def _mom_range(d0: date, d1: date) -> tuple[date, date]:
    span = (d1 - d0).days + 1
    end = d0 - timedelta(days=1)
    start = end - timedelta(days=span - 1)
    return start, end


def _compare_range(d0: date, d1: date, compare: str) -> Optional[tuple[date, date, str]]:
    from infra.i18n import t

    c = (compare or "yoy").lower()
    if c == "none" or c == "budget":
        return None
    if c == "mom":
        a, b = _mom_range(d0, d1)
        return a, b, t("环比")
    a, b = _yoy_range(d0, d1)
    return a, b, t("同比")


def _delta_pct(cur: float, prev: float, label: str = "同比") -> dict[str, Any]:
    from infra.i18n import t

    lab = t(label) if label in ("同比", "环比") else label
    if prev is None or prev <= 0:
        return {"pct": None, "label": "—", "tone": "flat"}
    pct = round((cur - prev) / abs(prev) * 100, 1)
    if pct > 0:
        return {"pct": pct, "label": t("▲ +{pct}% {label}", pct=pct, label=lab), "tone": "up"}
    if pct < 0:
        return {"pct": pct, "label": t("▼ {pct}% {label}", pct=pct, label=lab), "tone": "down"}
    return {"pct": 0, "label": t("持平 {label}", label=lab), "tone": "flat"}
