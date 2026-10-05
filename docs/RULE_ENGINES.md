# 双规则引擎边界（Anti-Corruption / 贡献者指南）
#
# 本仓库刻意保留两套「规则」能力，**不要合并成一个引擎**。
# 混淆时先看本文件，再改代码。

## 总览

| 维度 | A. 进程内 RuleSet | B. 营销 DB 规则 |
|------|-------------------|-----------------|
| 包路径 | `rules/`、`hk/hk_rules.py` | `mkt/mkt_auto_rules.py`、`mkt/mkt_rule_engine.py` |
| 存储 | 内存注册表（代码 `register_rule_set`） | DB 表（条件树 + 动作），可运营配置 |
| 调用 | `rules.apply("hk_dispatch", ctx)` | 自动发券 / 客群 / 营销编排入口 |
| 典型域 | 房务派单、未来 pricing/finance 热路径 | 优惠券、标签、自动授权 |
| 扩展入口 | 域内 `register_rule_set` / 代码注册 | **不要**经 `rules.register_rule_set`；走 mkt facade / 表 CRUD |
| 测试 | `tests/test_rule_engine.py` | mkt / auto_grant 相关测试 |

## 何时用哪套

**用 A（RuleSet）当：**

- 规则是**开发者**交付的（版本随代码走）
- 需要毫秒级、无 DB 往返（如派单打分前）
- 上下文是临时 dict（`guest_vip` / `hour` / `room_floor`）

**用 B（营销 DB 规则）当：**

- 规则由**酒店运营**在后台改（不发版）
- 需要审计、生效期、酒店维度隔离
- 动作是发券 / 打标 / 私域触达

## Anti-Corruption 约定

1. **命名**：对外文档写「进程内 RuleSet」与「营销规则引擎」，避免笼统说 RuleEngine。
2. **禁止**：在 `mkt_coupon_engine` 里 `from rules import apply` 替代 DB 规则；反之亦然。
3. **桥接（可选，未来）**：若营销命中后要影响派单，应 `emit("mkt.rule_fired", …)` 再由 HK 订阅改 context，**不要**让 mkt 直接改 `HousekeepingTask`。
4. **扩展**：可换厂商能力走 `src/extensions`；营销扩展用现有 mkt API / 新表，不要塞进 `rules._GLOBAL_RULESETS`。

## 相关代码

- 注册：`rules/engine.py` → `register_rule_set` / `apply`
- 生产加载：`api.py` import `hk.hk_rules`
- 营销：`mkt/mkt_auto_rules.py`、`application/mkt.py`（注意 auto_grant vs auto_rules 命名）

## 变更策略

短期只维护边界文档。中长期若要统一体验，优先做 **Facade 文档 + 事件桥**，而不是硬合并两套执行器。
