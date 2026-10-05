# Vendor 能力矩阵（诚实标注）

酒店 YAML 的 `vendors.*` 选型后，**不要假定**每个厂商都有同等深度。下表供国际 fork 预期管理。

| 域 | Provider | 可用能力 | 限制 / 现状 |
|----|----------|----------|-------------|
| Map | `tianditu` | geocode / nearby / tile proxy | 中国场景主路径 |
| Map | `gaode` | geocode / nearby（需 Key） | 中国 |
| Map | `google` | **tile proxy**；JS Maps（需 `GOOGLE_MAPS_API_KEY`） | **geocode/nearby 仍为手工模式（Noop）**；status.mode=`manual` 当无 Key |
| Map | `noop` | 手工坐标 | 演示 / 离线 |
| Tax | `fapiao` | 数电票 issue/void | 中国 |
| Tax | `simple_vat` | **价税拆分** `split_amounts` | **不对税局开票**（`issue_to_authority=false`） |
| Tax | `noop` | 关闭税控单据 | 国际无票场景 |
| Messaging | `wecom` | 完整：回调 / 绑定票 / 关怀侧边栏 / 外部联系人（`wecom_deep`） | 腾讯企微；中国默认 |
| Messaging | `line` | Push 文本（需 token）；无 token → **demo 发送**；`bind_ticket` 占位 | 日韩台 / 部分东南亚 |
| Messaging | `whatsapp` | Cloud API 文本（需 token + phone_number_id）；无密钥 → **demo** | 东南亚 / 欧美酒店主通道 |
| Messaging | `webhook` | 事件回执骨架 | ISV 自建中间件 |
| Messaging fallback | `sms` / `email` | 触达降级骨架（demo 记日志） | 国际几乎必开；可接 Twilio / SMTP |
| LLM | catalog 各 id | chat / stream（OpenAI 兼容或 Ollama） | 模型名来自配置/目录，不写死 qwen |

## 私域两层

| Pack | 含义 | 何时启用 |
|------|------|----------|
| `private_ops_core` | 分群 / 发券 / 规则 / 看板 / 建联可达 | **全球默认** |
| `wecom_deep` | 侧边栏 / 外部联系人全量同步 / 群发助手 | 仅 `primary: wecom` |

YAML 示例：

```yaml
vendors:
  messaging:
    primary: whatsapp   # 或 line / wecom / webhook
    fallback: [sms, email]
    packs: [private_ops_core]
```

业务应读 `status.capabilities` / `channel_status()`，勿硬编码厂商名做功能开关。
可达性语义用 `guest_channel_reachable` / `channel_reachable`（历史名 `guest_in_wecom_private` / `in_wecom_private` 仅作兼容别名）。
