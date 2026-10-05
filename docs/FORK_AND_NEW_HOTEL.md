# Fork → 新酒店 YAML → 上线（一步清单）

> **部署模型：单店单进程。** 用 `FML_HOTEL`（或 YAML id）选定**一家**酒店组装配置。  
> 本仓库**不是** SaaS 多租户：`hotel_id` 列用于订单归属，不代表同一进程服务多家互不干扰的品牌。

中文 / English 同页。

---

## 中文

### 1. 复制酒店配置

```bash
cp config/hotels/demo-intl.yaml config/hotels/my-hotel.yaml
# 编辑 id / locale / currency / vendors / system / tax
```

关键字段：

| 字段 | 含义 |
|------|------|
| `id` | 酒店 id（= `FML_HOTEL`） |
| `locale` | `zh-CN` / `en`（第三语言后续扩展） |
| `currency` | `CNY` / `SGD` / `USD`… → 前端金额符号 |
| `vendors.map` | `tianditu` / `google` / … |
| `vendors.messaging` | `wecom` / `line` / `webhook` |
| `vendors.llm` | `ollama` / `siliconflow` / `deepseek` / … |
| `vendors.tax` | `fapiao` / `simple_vat` / `noop` |
| `system.wecom` | `false` 隐藏「私域通道」System Tab |

详见 [HOTEL_ASSEMBLY.md](HOTEL_ASSEMBLY.md)、[EXTENSIONS.md](EXTENSIONS.md)、[VENDOR_CAPABILITIES.md](VENDOR_CAPABILITIES.md)。

### 2. 本地启动（SQLite）

```bat
deploy\dev\start.bat my-hotel
```

Linux / macOS：`bash deploy/dev/start.sh my-hotel`。  
验收：`GET /api/v1/system/branding` 应含 `currency`、`private_channel_vendor`、`deployment_mode=single_hotel`。

### 3. Docker Compose

```bash
# 密码 / JWT / 酒店：改 compose（deploy/docker/docker-compose.seed.yml → pms.environment）
docker compose -f deploy/docker/docker-compose.seed.yml up -d --build
```

镜像已包含 `config/` 与 `locales/`；compose 另挂载 `./config` 便于热改 YAML。

### 4. 白标（可选）

```env
FML_APP_NAME=StarStay
FML_PRIMARY=#0B5FFF
FML_LOGO_URL=/branding/logo.svg
```

---

## English

### 1. Copy a hotel profile

```bash
cp config/hotels/demo-intl.yaml config/hotels/my-hotel.yaml
```

Edit `id`, `locale`, `currency`, `vendors.*`, `system.*`, `tax`.

**Deployment model: one hotel per process** (`FML_HOTEL`). Not multi-tenant SaaS.

### 2. Run locally (SQLite)

```bash
bash deploy/dev/start.sh my-hotel
```

Windows: `deploy\dev\start.bat my-hotel`.  
Check `GET /api/v1/system/branding` for `currency` and `deployment_mode`.

### 3. Docker Compose

```bash
# Secrets and hotel id: edit the compose file
docker compose -f deploy/docker/docker-compose.seed.yml up -d --build
```

### 4. Optional white-label

`FML_APP_NAME` / `FML_PRIMARY` / `FML_LOGO_URL` in hotel YAML or compose `environment`.
