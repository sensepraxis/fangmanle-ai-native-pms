# Extensions：可换厂商能力域

酒店 YAML 选型 + 共同 Interface + 多实现类。业务只依赖防腐层。

## 分工

| 类型 | 放哪 | 例子 |
|------|------|------|
| **酒店配置** | `config/hotels/<hotel>.yaml` | vendors / system Tab / locale |
| **Extensions** | `src/extensions/` + System「扩展能力」 | 地图、LLM、私域、税票 |
| **系统参数** | System 菜单 | 财务参数、房型、房间、用户、RBAC |

## 目录

```
config/extensions/
  maps.yaml                 # id → 地图实现类
  tax.yaml                  # id → 税票实现类

src/extensions/
  map/                      # IMap：TiandituMap / GaodeMap / GoogleMap / BaiduMap / NoopMap
  llm/                      # LlmProvider 目录
  messaging/                # PrivateChannel：wecom / line / whatsapp / webhook (+ sms/email 兜底)
  tax/                      # ITax：FapiaoTax / SimpleVatTax / NoopTax
  bootstrap.py              # 按酒店 YAML vendors 激活
```

## 酒店 YAML

```yaml
vendors:
  map: google
  messaging: line
  llm: deepseek
  tax: simple_vat
tax:
  name: gst
  rate: 0.09
```

## 新增地图 Provider

1. 实现 `extensions.map.port.IMap`（含可选 `fetch_tile` 同源瓦片代理）
2. 在 `config/extensions/maps.yaml` 登记 class
3. 酒店 YAML：`vendors.map: your_id`

瓦片代理：`GET /api/v1/system/map-tile/{layer}/{z}/{y}/{x}` 只调 `extensions.map.facade.proxy_map_tile`，  
由当前 IMap 实现（天地图 / 高德 / Google…）各自拼上游 URL；百度可在 `BaiduMap.fetch_tile` 补全。

## 业务防腐

- 地图：`extensions.map.facade`（价格助手禁止 import 图商 SDK）
- LLM：`extensions.llm.facade`（`chat` / `resolve_model_name` / `llm_identity`）；**厂商目录可插拔，禁止业务写死 ollama·qwen3:8b**。
  - `resolve_*` / `list_providers` 在 OpenCore，可展示 YAML `vendors.llm`。
  - **`chat` / `load_llm_config` 由商业包 `commercial.ai_core.llm_service` 执行**。去掉 `src/commercial/` 或 `FML_COMMERCIAL=0` 时，`/system/branding` 的 `commercial_enabled=false`，前端隐藏问数与「大语言模型」配置；调用 chat 返回业务错误「商业 AI 能力未启用」。
- IM：`extensions.messaging.facade`（看板 / 建联 / 发信）+ `messaging.get_channel()`。企微实现在 OpenCore `src/wecom/`（无单独 pip extra；依赖已有 `httpx`）。
- 税票：`finance.tax.registry.get_tax_provider()`（由 tax extension 注入）

能力深浅见 [VENDOR_CAPABILITIES.md](VENDOR_CAPABILITIES.md)；Fork 新酒店见 [FORK_AND_NEW_HOTEL.md](FORK_AND_NEW_HOTEL.md)。

### 私域通道（messaging）

两层：`private_ops_core`（全球：分群/发券/规则/看板）+ 可选 `wecom_deep`（仅企微侧边栏等）。

| 能力 | 入口 | 说明 |
|------|------|------|
| 状态 / 身份 source | `extensions.messaging.facade` | 用 `guest_channel_reachable`；禁止 `source=="wecom"` 硬编码 |
| 主通道发信 | `messaging.get_channel()` | wecom / line / whatsapp / webhook |
| 触达兜底 | `resolve_fallback` + `send_text(use_fallback=…)` | sms / email 骨架 |
| System 配置页 | `/a-ai-core/private-channel` | 选型 + 兜底；企微密钥进 `/wecom-integration` |
| 国内示例 | `demo-cn.yaml` → `primary: wecom` + `wecom_deep` | |
| 海外示例 | `demo-sg` LINE；`demo-intl` / `demo-gb` WhatsApp | `system.private_channel: true` |
