# SPDX-License-Identifier: Apache-2.0
"""自动发券 · 事件匹配 Strategy 注册表。

新增事件类型：``register_event_matcher(event_type, fn)``，不必改 ``_event_match`` if 链。
``fn(params, ctx, event_key) -> (ok, text)``。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

EventMatcherFn = Callable[[dict, dict, Optional[str]], tuple[bool, str]]

EVENT_MATCHERS: dict[str, EventMatcherFn] = {}


def register_event_matcher(*event_types: str):
    def deco(fn: EventMatcherFn):
        for et in event_types:
            EVENT_MATCHERS[et] = fn
        return fn

    return deco


def get_event_matcher(event_type: str) -> EventMatcherFn | None:
    return EVENT_MATCHERS.get(event_type)


@register_event_matcher("NEW_WECHAT_MEMBER")
def _match_new_wechat(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    if event_key and event_key != "NEW_WECHAT_MEMBER":
        return False, "事件不匹配"
    return bool(ctx.get("channel_reachable") or ctx.get("in_wecom_private")), "新客加入私域"


@register_event_matcher("REG_DAYS")
def _match_reg_days(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    n = int(params.get("reg_days") or 30)
    return ctx.get("registered_days") == n, f"注册满 {n} 天"


@register_event_matcher("CHECKOUT_DAYS")
def _match_checkout_days(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    n = int(params.get("checkout_days") or params.get("days") or 7)
    return ctx.get("last_stay_days") == n, f"退房后 {n} 天"


@register_event_matcher("SILENT_DAYS", "DORMANT")
def _match_silent(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    n = int(params.get("silent_days") or params.get("dormant_days") or 60)
    ld = ctx.get("last_stay_days")
    ok = (ld is not None and ld >= n) or (ld is None and (ctx.get("registered_days") or 0) >= n)
    return ok, f"沉默 ≥ {n} 天"


@register_event_matcher("BIRTHDAY")
def _match_birthday(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    # Demo：无生日字段时用注册日对齐
    ahead = int(params.get("ahead_days") or 7)
    reg = ctx.get("registered_days")
    return reg is not None and reg % 365 == (365 - ahead) % 365, f"生日提前 {ahead} 天"


@register_event_matcher("HOLIDAY")
def _match_holiday(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    return False, f"节假日 {params.get('holiday') or ''}（非节日日不触发）"


@register_event_matcher("HIGH_VALUE_NEW")
def _match_high_value(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    mn = float(params.get("min_avg_order") or 600)
    return (
        (ctx.get("stay_records") or 0) <= 1 and (ctx.get("avg_order_value") or 0) >= mn,
        f"高价值新客 ≥{mn}",
    )


@register_event_matcher("CUSTOM")
def _match_custom(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    key = str(params.get("event_key") or "")
    return bool(event_key and event_key == key), f"自定义 {key}"


@register_event_matcher("PMS_EVENT")
def _match_pms(params: dict, ctx: dict, event_key: Optional[str]) -> tuple[bool, str]:
    pe = str(params.get("pms_event") or "")
    return bool(event_key and event_key == pe), f"PMS {pe}"


__all__ = [
    "EVENT_MATCHERS",
    "register_event_matcher",
    "get_event_matcher",
]
