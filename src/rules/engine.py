# SPDX-License-Identifier: Apache-2.0
"""Rule Engine 实现：声明式规则 + 规则集合。

设计原则：
- **简单**：Rule 是 dataclass，when/then 是 Python callable；不引入 DSL。
- **可热更**：clear cache 即可生效；未来可从 DB 加载。
- **可观测**：apply() 返回执行轨迹（哪条规则命中、是否抛错）。
- **可扩展**：未来可加 Rule.from_dict() / Rule.to_dict() / RuleEngine.from_db()。

Rule 三要素：
- ``when(ctx) -> bool``：是否命中（predicate）
- ``then(ctx) -> None``：执行动作（side-effect）
- ``priority``：数字越大越先执行；命中后是否继续由 ``stop_on_match`` 控制

典型用法：
    rs = RuleSet("hk_dispatch")
    rs.register(Rule(
        id="R001",
        name="VIP 客人优先派单",
        when=lambda ctx: ctx.get("guest_vip") is True,
        then=lambda ctx: ctx.update({"assignee_id": 1}),
        priority=100,
    ))
    context = {"guest_vip": True}
    rs.apply(context)  # 执行命中规则，context 被修改
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

PredicateT = Callable[[dict], bool]
ActionT = Callable[[dict], None]


@dataclass
class Rule:
    """一条声明式业务规则。

    Attributes:
        id: 唯一标识（业务主键，如 "R001"）。
        name: 人类可读名称（前端展示）。
        priority: 数值越大越先执行；同优先级按注册顺序。
        when: 命中条件（predicate），返回 True 即命中。
        then: 命中动作（side-effect），可改 ctx 或触发外部系统。
        stop_on_match: 命中后是否终止后续规则（默认 True）。
        description: 详细说明。
    """

    id: str
    name: str
    when: PredicateT
    then: ActionT
    priority: int = 100
    stop_on_match: bool = True
    description: str = ""

    def matches(self, context: dict) -> bool:
        try:
            return bool(self.when(context))
        except Exception as e:
            log.warning("rule %s predicate failed: %s", self.id, e)
            return False

    def apply(self, context: dict) -> dict:
        try:
            self.then(context)
        except Exception as e:
            log.warning("rule %s action failed: %s", self.id, e)
        return context


@dataclass
class RuleExecutionTrace:
    """单条规则执行的轨迹（用于调试与审计）。"""

    rule_id: str
    rule_name: str
    matched: bool
    error: str | None = None


@dataclass
class RuleSet:
    """一组按 priority 排序的规则。"""

    name: str
    description: str = ""
    _rules: list[Rule] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def register(self, rule: Rule) -> Rule:
        """注册一条规则（重复 id 会覆盖）。"""
        with self._lock:
            self._rules = [r for r in self._rules if r.id != rule.id]
            self._rules.append(rule)
            self._rules.sort(key=lambda r: -r.priority)  # 高优先级先
        return rule

    def unregister(self, rule_id: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.id != rule_id]
            return len(self._rules) < before

    def clear(self) -> None:
        """清空所有规则（测试用）。"""
        with self._lock:
            self._rules.clear()

    def apply(self, context: dict) -> list[RuleExecutionTrace]:
        """按 priority 顺序执行规则，返回执行轨迹。"""
        with self._lock:
            rules = list(self._rules)
        traces = []
        for rule in rules:
            matched = rule.matches(context)
            trace = RuleExecutionTrace(rule_id=rule.id, rule_name=rule.name, matched=matched)
            if matched:
                rule.apply(context)
                traces.append(trace)
                if rule.stop_on_match:
                    break
            else:
                traces.append(trace)
        return traces

    def list_rules(self) -> list[Rule]:
        """返回当前所有规则（按 priority 倒序）。"""
        with self._lock:
            return list(self._rules)


# 全局注册表：按 name 索引 RuleSet
_GLOBAL_RULESETS: dict[str, RuleSet] = {}
_GLOBAL_LOCK = threading.RLock()


def register_rule_set(ruleset: RuleSet) -> RuleSet:
    with _GLOBAL_LOCK:
        _GLOBAL_RULESETS[ruleset.name] = ruleset
    return ruleset


def get_rule_set(name: str) -> Optional[RuleSet]:
    with _GLOBAL_LOCK:
        return _GLOBAL_RULESETS.get(name)


def apply(ruleset_name: str, context: dict) -> list[RuleExecutionTrace]:
    """便捷函数：按 name 取出规则集并执行。

    若规则集不存在，返回空轨迹。
    """
    rs = get_rule_set(ruleset_name)
    if rs is None:
        log.debug("ruleset not found: %s", ruleset_name)
        return []
    return rs.apply(context)
