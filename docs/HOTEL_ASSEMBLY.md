# 酒店组装式应用

差异化按**酒店 YAML**配置，不是按国情包。

## 目标

1. 内核稳定；可换能力走 `src/extensions`（共同 Interface + 多 Provider 实现）
2. 每个酒店一份 `config/hotels/<name>.yaml`
3. 业务只面向防腐层（地图 / LLM / IM / 税票 facade）

## 启动

```bat
deploy\dev\start.bat abc-hotel
```

等价于读取 `config/hotels/abc-hotel.yaml`。

## YAML 要点

```yaml
id: abc-hotel
locale: zh-CN
currency: CNY
channels_preset: cn          # 空库渠道出厂目录键
system:
  wecom: true                # false 藏「扩展能力 · 私域通道」（menu.system.wecom）
vendors:
  map: tianditu              # → config/extensions/maps.yaml（tianditu / gaode / baidu / google / noop）
  messaging: wecom           # wecom | line | webhook（海外可 line，无需企微）
  llm: ollama
  tax: fapiao                # → config/extensions/tax.yaml
features:
  invoice: true
```


## 代码入口

| 层 | 路径 |
|----|------|
| 读 YAML | `infra/hotel_config.py` |
| 组装 | `infra/hotel.py` → `ensure_hotel()` |
| 扩展 | `extensions/`（map / llm / messaging / tax） |

`src/packs` 已移除。旧名 `ensure_packs` / `FML_PACKS` 仍作兼容别名。

## 部署边界（开源必读）

- **单店单进程**：一次进程只激活一份酒店 YAML（`FML_HOTEL`）。
- **不是多租户 SaaS**：不要假设同一 API 进程可安全服务多家互不干扰的品牌。
- Fork 新酒店步骤：[FORK_AND_NEW_HOTEL.md](FORK_AND_NEW_HOTEL.md)。
- Vendor 能力深浅：[VENDOR_CAPABILITIES.md](VENDOR_CAPABILITIES.md)。
