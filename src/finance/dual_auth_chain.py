# SPDX-License-Identifier: Apache-2.0
"""反结账双授权 · Chain of Responsibility。

店长侧 / 财务侧各自为 Handler；链上依次尝试匹配 role，命中则记账并可选短路。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from domain import InvalidStateError


@dataclass
class DualAuthContext:
    ticket: Any
    role: str
    actor: str
    event: Optional[str] = None
    handled: bool = False


class DualAuthHandler(ABC):
    def __init__(self, nxt: Optional["DualAuthHandler"] = None) -> None:
        self._next = nxt

    def handle(self, ctx: DualAuthContext) -> DualAuthContext:
        if self.matches(ctx):
            self.apply(ctx)
            ctx.handled = True
            return ctx
        if self._next is not None:
            return self._next.handle(ctx)
        raise InvalidStateError("role 须为 gm/admin（店长侧）或 fin（财务侧）")

    @abstractmethod
    def matches(self, ctx: DualAuthContext) -> bool: ...

    @abstractmethod
    def apply(self, ctx: DualAuthContext) -> None: ...


class ManagerAuthHandler(DualAuthHandler):
    _ROLES = frozenset({"mgr", "manager", "store", "gm", "admin"})

    def matches(self, ctx: DualAuthContext) -> bool:
        return (ctx.role or "").lower() in self._ROLES

    def apply(self, ctx: DualAuthContext) -> None:
        t = ctx.ticket
        t.auth_mgr_done = 1
        t.auth_mgr_by = ctx.actor
        ctx.event = "AUTH_MGR"


class FinanceAuthHandler(DualAuthHandler):
    _ROLES = frozenset({"fin", "finance"})

    def matches(self, ctx: DualAuthContext) -> bool:
        return (ctx.role or "").lower() in self._ROLES

    def apply(self, ctx: DualAuthContext) -> None:
        t = ctx.ticket
        t.auth_fin_done = 1
        t.auth_fin_by = ctx.actor
        ctx.event = "AUTH_FIN"


def build_default_dual_auth_chain() -> DualAuthHandler:
    """店长 → 财务；未匹配则抛 InvalidStateError。"""
    return ManagerAuthHandler(FinanceAuthHandler())


def apply_dual_auth_role(ticket: Any, role: str, actor: str) -> str:
    """对 ticket 应用一条授权；返回 audit event 名。"""
    chain = build_default_dual_auth_chain()
    ctx = DualAuthContext(ticket=ticket, role=role, actor=actor)
    chain.handle(ctx)
    return ctx.event or "AUTH"


__all__ = [
    "DualAuthContext",
    "DualAuthHandler",
    "ManagerAuthHandler",
    "FinanceAuthHandler",
    "build_default_dual_auth_chain",
    "apply_dual_auth_role",
]
