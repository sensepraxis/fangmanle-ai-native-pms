# 限界上下文与跨域依赖（Anti-Corruption）

开源贡献者改代码前先看本文件，避免 service↔service 横向乱引。

## 部署边界

- **单店单进程**：`FML_HOTEL` / `config/hotels/<id>.yaml` 组装一家酒店。  
- **不是** SaaS 多租户。DB 的 `hotel_id` 是业务归属字段，不表示同一进程隔离多家品牌。开第二家店 = **另一个进程 + 另一份 YAML + 另一套库**。  
- 详见 [FORK_AND_NEW_HOTEL.md](FORK_AND_NEW_HOTEL.md)。

## 上下文一览

| 上下文 | 包 | 对外稳定入口 |
|--------|-----|--------------|
| 订单 / 入住 / Folio | `orders/` | `application.orders` |
| 财务（AR/押金/退款/夜审） | `finance/` | `application.finance` |
| 房态 / 库存 | `rooms/` | `application.rooms` |
| 房务 | `hk/` | `application.hk` |
| 营销 / 券 | `mkt/` | `application.mkt` |
| 私域消息 | `messaging/`、`extensions/messaging` | `extensions.messaging.facade` / `messaging.get_channel()` |
| 企微适配器 | `wecom/` | **仅**企微专属（JS-SDK/回调）；业务勿直连 |
| 客人 / CRM | `guests/` | `application.guests` |

## 允许的跨域方式

1. **Application Facade 编排**（首选）：`application/orders` 调 `finance.payment` 结算。
2. **领域事件**：A 写完 `emit("x.y")`，B 订阅；禁止 B 直接改 A 表。
3. **只读 Query Object**：如 `hk.queries.OpenServiceRequestsQuery`（看板共用）。

## 已知耦合与约定

| 耦合 | 约定 |
|------|------|
| `orders` → `finance.payment` / deposit | 仅退房结算、押金展示；写路径经 orders facade |
| `orders.pms_domain` → `finance.ar_ap` | 挂账入账；勿反向 import orders 写 AR |
| `wecom` → `mkt.wallet_service` | 仅读券钱包 / 核销；发消息走 `messaging.get_channel()` |
| `finance.night_audit` → `orders.pms_ops` / `rooms.room_ops` | 夜审 Template Method 步骤内调用，不散落 router |
| HK RuleSet vs 营销规则 | 见 `docs/RULE_ENGINES.md` |

## 禁止

- Router **禁止** `from commercial import …` / `infra.commercial_pack`（CI：`python tools/check_router_layer.py`）。商业能力只经 `application.*` 的 bind。
- Router 直接 `from finance.xxx import` 写库（应走 `application.*`）。
- `mkt` / `guests` / `hk` **禁止** `from wecom import …`；企微专属走 `application.wecom`，通用私域走 `extensions.messaging.facade`。
- 新功能在 God Service 里再堆 200 行；优先 [FRAMEWORK.md](FRAMEWORK.md) 的注册点。

## 已知遗留（请勿照抄）

拆 API 时部分 router 仍带 `from models import *`，以及 `system.py` / `orders.py` / `finance/reports.py` 里少量 `db.query`。**新接口不要复制这套样板**；能迁就迁到 `application.*`。

扩开展点（问数 `register_intent` / `register_query`、交班 `register_shift_scene`、定价 `register_pricing_rule_hook`）见 [FRAMEWORK.md](FRAMEWORK.md)。

## OpenCore vs Commercial

| 层 | 路径 | 许可 |
|----|------|------|
| OpenCore | `src/` 除 `commercial/` | Apache-2.0 |
| Commercial Core | `src/commercial/`（`ai_core` + analytics/finance/hk/mkt/assets/orders/pricing AI 场景） | BUSL-1.1 |

域内核（写库、房态、记账、**规则型定价助手、经营快照、问数目录/SQL、交班规则客情与待办**）留在 OpenCore；**LLM 场景**与基座在 `commercial.*`。OpenCore 经 `infra.commercial_pack` / `application.*` / `extensions.llm.facade` 惰性调用；去掉 `src/commercial/` 或设 `FML_COMMERCIAL=0` 后 API 仍可启动，AI 对话接口不可用。

许可边界图见 [`LICENSING.md`](../LICENSING.md) / [`LICENSING_zh.md`](../LICENSING_zh.md)（仓库根目录，GitHub 可渲染 mermaid）。

## 酒店组装 vs Kernel

内核（`orders` / `guests` / `finance` AR / `rooms` / `hk`）不绑定中国图商、税控或企微 SDK。地区差异经 **酒店 YAML + Extensions** 在启动时组装：

| 端口 | 内核入口 | 示例 |
|------|----------|------|
| 私域消息 | `extensions.messaging.facade` / `messaging.get_channel()` | cn=wecom；sg=line；intl=webhook |
| 地图 | `extensions.map.facade` | cn=tianditu；intl=google（见能力矩阵） |
| 税控凭证 | `finance.tax.registry.get_tax_provider()` | cn=fapiao；sg=simple_vat(GST) |
| LLM | `extensions.llm.facade` | ollama / siliconflow / deepseek… |
| 渠道种子 | `hotel_channel_seeds()` | cn / sea / uk / intl |

见 [HOTEL_ASSEMBLY.md](HOTEL_ASSEMBLY.md)、[EXTENSIONS.md](EXTENSIONS.md)、[VENDOR_CAPABILITIES.md](VENDOR_CAPABILITIES.md)。

约定：

- **AR 挂账留在内核**；税控开票/红冲才是 extension。
- 未设置 `FML_HOTEL` 时默认 `demo-cn`（本地开发）或镜像内 `demo-intl`（容器）。
