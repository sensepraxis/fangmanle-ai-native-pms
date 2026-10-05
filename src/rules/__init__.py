# SPDX-License-Identifier: Apache-2.0
"""Rule Engine：声明式业务规则基础设施。

背景：开源 SaaS 的标配（Odoo Record Rule / Saleor Promotion Rule / Metabase Question Model）。
把"业务规则"从 if/elif 链抽到可注册的规则集——支持：
- 配置化（未来可放数据库，前端可编辑）
- 热更新（clear cache 即可生效）
- A/B 测试（同一 context 跑两套规则）
- 审计（规则执行可记录）

本模块是**轻量级骨架**（不重不重 DSL）：
- ``Rule`` dataclass：id / name / priority / when / then
- ``RuleSet``：规则集合，按 priority 排序，命中即停或继续
- ``apply(context)``：执行规则集

**当前埋点**：
- ``hk_dispatch``：房务智能派单（见 ``hk/hk_rules.py`` + dispatch smart 模式）

**与营销规则的边界**：见仓库根 ``docs/RULE_ENGINES.md``（勿与 ``mkt_auto_rules`` 混淆）。

使用：
    from rules import RuleSet, Rule

    rs = RuleSet("hk_dispatch")
    rs.register(Rule(
        id="R001",
        name="VIP 客人优先派单",
        when=lambda ctx: ctx.get("guest_vip"),
        then=lambda ctx: ctx["assignee_id"] = 1,
        priority=100,
    ))

    context = {"guest_vip": True, "task_id": 42}
    rs.apply(context)
"""

from __future__ import annotations

from rules.engine import Rule, RuleSet, apply, get_rule_set, register_rule_set

__all__ = [
    "Rule",
    "RuleSet",
    "apply",
    "register_rule_set",
    "get_rule_set",
]
