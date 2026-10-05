# SPDX-License-Identifier: Apache-2.0
"""定价建议扩开展点。

fork / PR 请 ``register_pricing_rule_hook``，不要在 ``recommendation_service.generate_recommendations``
主循环里加分支。钩子返回新建条数（自行 ``db.add(PricingRecommendation)``）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

PricingRuleHook = Callable[[Session, int, dict[str, Any]], int]

_HOOKS: list[tuple[str, PricingRuleHook]] = []


def register_pricing_rule_hook(name: str, fn: PricingRuleHook) -> None:
    key = (name or "").strip()
    if not key:
        raise ValueError("pricing rule hook name required")
    _HOOKS.append((key, fn))


def list_pricing_rule_hooks() -> tuple[str, ...]:
    return tuple(n for n, _ in _HOOKS)


def run_extra_recommendation_hooks(db: Session, hotel_id: int, ctx: dict[str, Any]) -> int:
    created = 0
    for _name, fn in _HOOKS:
        created += int(fn(db, hotel_id, ctx) or 0)
    return created
