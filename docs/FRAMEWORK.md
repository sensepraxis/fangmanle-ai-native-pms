# 框架扩开展点（给外部 PR 用）

不要在交班 / 定价助手 / 问数的超大模块里加 `if hotel == …` 分支。先注册，再实现。

| 要加什么 | 注册点 | 实现放哪 |
|----------|--------|----------|
| 问数新意图 | `analytics.ask_catalog.register_intent` | 元数据字典；SQL 用下一行 |
| 问数确定性查询 | `analytics.ask_queries.register_query` | 纯函数 `(db, hotel_id, d0, d1, …) -> pack` |
| 交班/接班场景 | `finance.shift_scene_registry.register_shift_scene` | `builder(db, hotel_id, handover_id)` |
| 定价额外规则 | `pricing.pricing_assistant.rule_hooks.register_pricing_rule_hook` | 钩子自行 `db.add(PricingRecommendation)`，返回新建条数 |
| 可换厂商（地图/LLM/私域/税） | 酒店 YAML + `extensions.*.facade` | 见 [EXTENSIONS.md](EXTENSIONS.md) |
| LLM 对话场景 | `src/commercial/`（BUSL） | 不要写进 OpenCore 必依赖 |

HTTP：**新接口只走 `application.*`**。`src/routers/` 禁止 `import commercial` / `commercial_pack`（CI：`python tools/check_router_layer.py`）。

分层：`router → application.* → domain service`。`from models import *` 是拆 router 时的遗留样板，新文件不要复制。
