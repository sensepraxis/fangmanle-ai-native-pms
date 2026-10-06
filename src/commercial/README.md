# 商业版核心 · Commercial Core

**SPDX-License-Identifier: BUSL-1.1**

本目录适用 [Business Source License 1.1](../../LICENSE-BUSL)。  
许可总览见 [`LICENSING.md`](../../LICENSING.md) / [`LICENSING_zh.md`](../../LICENSING_zh.md)；商标见 [`TRADEMARK.md`](../../TRADEMARK.md)。

## 目录边界

| 路径 | 说明 |
|------|------|
| `src/`（**除**本目录） | **OpenCore**，Apache-2.0 |
| `src/commercial/` | **Commercial Core**，BUSL-1.1 |

## 当前纳入

| 子包 | 内容 |
|------|------|
| `ai_core/` | LLM 调用、harness 基座、叙事、prompt packs |
| `analytics/` | AI 问数 **路由/会话/回答**、看板 AI、经营分析叙事、ask_data **LLM 诊断**（目录/SQL/playbook/PII 在 OpenCore `analytics.ask_*`） |
| `finance/` | 交班/接班 AI、财务 AI harness、报表 AI 解读 |
| `hk/` | 房务 AI harness、排班 AI、房务派工 AI |
| `mkt/` | 券/会员/积分/私域 AI、分群 NL 意图 |
| `assets/` | 资产 AI、损耗归因 AI |
| `orders/` | 上门/散客 AI |
| `pricing/llm_service.py` | 价格助手 **白话 LLM**（规则层在 OpenCore `pricing.pricing_assistant`） |

经营快照、意图目录、确定性查询与规则 anomalies 在 OpenCore `analytics.ask_*`。交班客情/待办规则展示在 OpenCore `finance.shift_handover_service.task_service`。OpenCore 经 `infra.commercial_pack` 惰性加载本包；无本目录时 API 仍可启动。

生产使用前请联系：`contact@sensepraxis.com`
