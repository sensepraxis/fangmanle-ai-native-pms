# SPDX-License-Identifier: Apache-2.0
"""房务派单规则集（HK 域 Rule Engine 演示）。

这是把 ``hk/housekeeping_service.py`` 里硬编码的 if/elif 链
（321 个分支）逐步替换到 RuleSet 的**第一步**。

未来扩展（按 ROI 排序）：
- 派单规则（VIP 优先、楼层匹配、夜班升级）
- 任务紧急度自动升级规则
- 巡检通过/不通过的判定规则
- 客需响应时长 SLA 规则

使用：
    from rules import apply
    ctx = {"task_id": 42, "guest_vip": True, "hour": 23}
    apply("hk_dispatch", ctx)  # 命中 R001 VIP 优先派单
"""

from __future__ import annotations

from rules import Rule, RuleSet, register_rule_set

HK_DISPATCH_RULESET = RuleSet(
    "hk_dispatch",
    description="房务派单规则集（演示骨架）",
)


def _set_flag(ctx: dict, key: str, value) -> None:
    """规则 then 通用 setter：ctx[key] = value。"""
    ctx[key] = value


# R001: VIP 客人客需 → 强制指定 1 号（演示）派单员 + priority_boost
HK_DISPATCH_RULESET.register(
    Rule(
        id="R001",
        name="VIP 客人客需优先派单",
        description="VIP 客人客需单 → priority_boost=True 且 assignee_id=1",
        when=lambda ctx: ctx.get("guest_vip") is True,
        then=lambda ctx: (
            _set_flag(ctx, "priority_boost", True),
            _set_flag(ctx, "assignee_id", 1),
            _set_flag(ctx, "dispatch_reason", "R001: VIP 优先"),
        ),
        priority=100,
    )
)


# R002: 凌晨任务（0~6 点）→ 升级到夜班组
HK_DISPATCH_RULESET.register(
    Rule(
        id="R002",
        name="凌晨任务升级到夜班组",
        description="0~6 点派单 → escalation='night_team'",
        when=lambda ctx: 0 <= ctx.get("hour", 12) <= 6,
        then=lambda ctx: (_set_flag(ctx, "escalation", "night_team"),),
        priority=90,
    )
)


# R003: 同楼层任务 → 优先派给同楼层员工
HK_DISPATCH_RULESET.register(
    Rule(
        id="R003",
        name="同楼层任务优先派同楼层员工",
        description="房间楼层与员工楼层匹配 → priority_boost",
        when=lambda ctx: ctx.get("room_floor") == ctx.get("staff_floor"),
        then=lambda ctx: (
            _set_flag(ctx, "priority_boost", True),
            _set_flag(ctx, "dispatch_reason", "R003: 同楼层匹配"),
        ),
        priority=80,
    )
)


# R004: 客需紧急度 1（最高）→ 立即派单 + 通知
HK_DISPATCH_RULESET.register(
    Rule(
        id="R004",
        name="最高紧急度客需立即派单",
        description="urgency=1 → immediate=True",
        when=lambda ctx: ctx.get("urgency") == 1,
        then=lambda ctx: (
            _set_flag(ctx, "immediate", True),
            _set_flag(ctx, "notify_supervisor", True),
        ),
        priority=110,
        stop_on_match=False,  # 与其他规则组合生效
    )
)


# 注册到全局注册表（启动时由 run_prod.py / conftest.py / uvicorn 加载本模块时注册）
register_rule_set(HK_DISPATCH_RULESET)

__all__ = ["HK_DISPATCH_RULESET"]
