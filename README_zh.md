# 房满乐 PMS · AI 原生开源酒店 PMS（可自托管）

[English](README.md) · **简体中文**

**房满乐 PMS** 是一套 **AI 原生（AI-native）酒店 PMS**： **开源（open source）**、**可自托管（self-hosted）**、一个进程服务一家店。用 **酒店 YAML + 可插拔 Extensions**（地图 / LLM / 私域通道 / 税票）组装前台与运营。版本 **1.0.0** — [CHANGELOG_zh.md](CHANGELOG_zh.md)。

## 这是什么？（What is Fangmanle PMS?）

面向**单店**的自托管酒店管理系统：房态、订单、客房、财务、客人，以及可选的商业 LLM 场景。OpenCore（`src/` 除 `commercial/`）为 [Apache-2.0](LICENSE)；问数 / 交班 AI 等在 `src/commercial/`，适用 [BUSL-1.1](LICENSE-BUSL)。这是**你自己跑的酒店管理软件**，不是多租户云 PMS。

`FML_HOTEL` 选一份 YAML。`hotel_id` 只是归属字段，**不能**在同一进程里隔开第二家品牌。第二家店需要另一个进程、另一份 YAML、另一套 `DATABASE_URL`。见 [docs/FORK_AND_NEW_HOTEL.md](docs/FORK_AND_NEW_HOTEL.md)。

## 如何部署？（How to deploy Fangmanle PMS?）

本地演示用 SQLite，不需要数据库服务：Python 3.11+、Node 20+。

```bat
deploy\dev\start.bat demo-sg
```

```bash
bash deploy/dev/start.sh demo-sg
```

打开 http://127.0.0.1:8081/ ，账号 **`admin` / `admin123`**。生产请 **自托管 PostgreSQL**：`deploy/docker/` — [INSTALL.md](INSTALL.md)。启动**只认** `deploy/dev/` 与 `deploy/docker/`。

## 为什么用？（Why use Fangmanle PMS?）

- **开源酒店 PMS**，可 fork、在自己的机器上跑（**self-hosted**）；界面中英走 [`locales/`](locales/)。
- **AI-native**：LLM / 消息 / 地图 / 税票可换厂商；`FML_COMMERCIAL=0` 时 OpenCore 仍能启动。
- 订单 / 房态 / 客房 / 财务内核在 Apache OpenCore，运营核心不必锁进托管 SaaS。

> 仓库主页以你 clone 的 Git remote 为准。`pyproject.toml` `[project.urls]` 是上游默认值；fork 后请改成自己的地址，避免首页/元数据链到空仓库。

| 想做什么 | 文档 |
|----------|------|
| Fork 出新酒店 | [docs/FORK_AND_NEW_HOTEL.md](docs/FORK_AND_NEW_HOTEL.md) |
| 扩开展点（问数/交班/定价，勿改超大文件） | [docs/FRAMEWORK.md](docs/FRAMEWORK.md) |
| 酒店 YAML 字段 | [docs/HOTEL_ASSEMBLY.md](docs/HOTEL_ASSEMBLY.md) |
| 可换厂商能力 | [docs/EXTENSIONS.md](docs/EXTENSIONS.md) · [VENDOR_CAPABILITIES.md](docs/VENDOR_CAPABILITIES.md) |
| Docker 一键 | [INSTALL.md](INSTALL.md) · [deploy/README.md](deploy/README.md)；酒店写在 compose 的 `FML_HOTEL` |
| 架构 / FAQ | [ARCHITECTURE.md](ARCHITECTURE.md) · [FAQ_zh.md](FAQ_zh.md) |
| 贡献 | [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md) · [行为准则](CODE_OF_CONDUCT_zh.md) |

### 仓库怎么读

| 路径 | 作用 |
|------|------|
| `config/hotels/` | 一家店一份 YAML |
| `src/`（除 `commercial/`） | OpenCore · Apache-2.0 域内核 |
| `src/commercial/` | 商业 AI · BUSL-1.1 |
| `frontend/` | 管理端 UI |
| `deploy/` | 常规开发（SQLite）与 Docker 编排 |
| `tools/` | CI 门禁、i18n、SPDX、离线构建 |
| `db/postgres/` | 生产 PostgreSQL 脚本（不要用根目录 `ddl/`） |
| `locales/` | 中英词表正式源 |

`src/locales/` 与 `frontend/src/locales/` 是生成镜像，只改根 `locales/`。词表健康检查见 [docs/I18N.md](docs/I18N.md)。

---

## 本地启动指南（SQLite 快速体验 / PostgreSQL 生产）

房满乐 PMS 采用 **双数据库后端** 设计，通过环境变量 `DATABASE_URL` 切换，**同一套 SQLAlchemy 2.0 模型代码**：

| 后端 | 适用场景 | 依赖 |
|---|---|---|
| **SQLite**（默认、零依赖） | 本地快速体验、日常开发、CI 单测、新人本机起服务看效果 | 无需任何数据库服务 |
| **PostgreSQL**（生产） | 生产部署、完整业务（全文检索 / JSONB 查询等） | 需 Docker 或自有 PG 实例 |

> ⚠️ 版本对齐说明（开源读者注意）：早期文档曾写「默认 PostgreSQL、不再依赖 SQLite」，与开发脚本 / CI 实际用法矛盾。
> 实际现状是：**仓库同时支持两种后端**。开发、演示与 CI 默认走 **SQLite**（零依赖、开箱即用）；**PostgreSQL** 作为生产部署后端。
> 两者通过 `DATABASE_URL` 选择，业务代码不区分。

- `database.py` 在未设置 `DATABASE_URL` 时默认仓库根 **SQLite**（`data/fml_demo.db`），不连本机 Postgres。
- 生产 / Docker 必须显式设置 `DATABASE_URL` 指向 PostgreSQL。
- 启动命令行 / CI 亦可覆盖为任意 `sqlite:///...`。
- **生产部署务必用 PostgreSQL**：SQLite 是 schema 子集，涉及 PG 专属能力（全文检索 / JSONB）的接口在 SQLite 上会降级或返回 500。

---

## 1. 前置条件

- Python 3.11+（建议 `.venv` 隔离依赖，见 CONTRIBUTING）
- 依赖：`fastapi`、`uvicorn`、`sqlalchemy>=2.0`、`pydantic>=2`、`cryptography`、`httpx`
  - SQLite 路径**不需要** `psycopg`（`pip install -e .` 即可；`requirements-prod.txt` 仍为 Docker 全量锁）
  - PostgreSQL：`pip install -e ".[postgres]"`，驱动前缀见下表
  - 证件国密 SM4：`pip install -e ".[gmssl]"`（未装则 AES）
- PostgreSQL 路径另需 Docker（或自有 PG 实例）

> 连接串驱动前缀要与已装驱动一致：
> - psycopg2（v2）→ `postgresql+psycopg2://...`
> - psycopg（v3）→ `postgresql+psycopg://...`
> 前缀写错会报 `module not found` 或连接失败。

---

## 2. 默认启动（请只走这一条）

Windows 看**带业务数据的完整界面**（交班客情、订单、渠道），用这一条：

```bat
deploy\dev\start.bat demo-sg
```

中文店把 `demo-sg` 换成 `demo-cn`。脚本会：按酒店 YAML 灌 SQLite demo → 构建前端 → 在 **8081** 起服务。

打开 http://127.0.0.1:8081/ ，账号 **`admin` / `admin123`**。

| 你想做的 | 怎么做 |
|----------|--------|
| 关商业 AI（侧栏无问数、交班无 AI 草稿） | 用 `deploy\dev\start-opencore.bat demo-sg`（脚本内写死关闭，不必记环境变量） |
| 只热更新代码 | 先用本节脚本起过一次，再看 [docs/DEV.md](docs/DEV.md)；不要当第一次启动指南 |
| Docker / PostgreSQL | [deploy/README.md](deploy/README.md) · `deploy/docker/` |

启动与部署**只认** `deploy/dev/` 与 `deploy/docker/`，没有其它旁路脚本。

---

## 3. PostgreSQL（生产后端）

### 3.1 启动本地 PostgreSQL（Docker）

```bash
docker run -d --name fml-pg -p 5432:5432 \
  -e POSTGRES_USER=fml \
  -e POSTGRES_PASSWORD=fmlpass \
  -e POSTGRES_DB=fml \
  -v fml-pg-data:/var/lib/postgresql/data \
  postgres:16-alpine
```

`fml-pg-data` 是 Docker 卷，容器重建 / 重启不丢数据。
验证：`docker logs fml-pg` 看到 `database system is ready to accept connections` 即成功。

### 3.2 设置数据库连接串

```powershell
# PowerShell
$env:DATABASE_URL="postgresql+psycopg2://fml:fmlpass@localhost:5432/fml"
# CMD
set DATABASE_URL=postgresql+psycopg2://fml:fmlpass@localhost:5432/fml
# Git Bash / Linux
export DATABASE_URL="postgresql+psycopg2://fml:fmlpass@localhost:5432/fml"
```

> `database.py` 在 import 时即读取 `DATABASE_URL`，必须在启动 Python 之前设好。
> **不设置时默认是仓库 SQLite**（`data/fml_demo.db`），不是本机 Postgres。生产 / Docker 必须显式写 PostgreSQL URL。

---

## 4. 准备数据（首次）

不要手搓 uvicorn / 旁路 seed。数据随官方启动入口一起进来：

- **SQLite 完整 demo**：第 2 节 `deploy/dev/start.bat`（或 `start.sh`），含 admin + 业务样例。
- **PostgreSQL 带样例**：`docker compose -f deploy/docker/docker-compose.seed.yml up -d --build`（容器 init 会跑 `db/postgres/03_demo`）。
- **PostgreSQL 空店（仅 DDL + admin）**：`docker compose -f deploy/docker/docker-compose.prod.yml up -d --build`。

详见 [deploy/README.md](deploy/README.md)。

---

## 5. 启动应用

**SQLite（开发 / 快速体验）**：第 2 节 `deploy/dev/`（默认 8081，带 demo）。

**PostgreSQL**：`deploy/docker/` 两份 compose，不要直接 `python run_prod.py` 当产品入口。

---

## 6. 访问

- 本地 SQLite demo：`http://127.0.0.1:8081/`（`deploy/dev/`）
- Docker / PostgreSQL：`http://127.0.0.1:8000/`（`deploy/docker/`，端口写在 compose）
- 管理员账号：`admin` / `admin123`

---

## 7. 配置大模型（AI 功能）

AI 能力（客房排班、定价助手、AI 问数、客情关怀等）依赖外部 LLM，需单独配置：

对话与问数会话在商业包 `src/commercial/`。OpenCore 只保留厂商目录与 `extensions.llm.facade` 选型。  
关掉商业包：启动前设 `FML_COMMERCIAL=0`（或删掉该目录）。此时 `/system/branding` 的 `commercial_enabled` 为 false，前端隐藏「AI 问数」、「大语言模型」配置，以及交班/接班 **AI 草稿面板**。

进入 **系统配置 → 大语言模型**（商业包启用时），二选一：

- **自托管 Qwen（OpenAI 兼容端点，推荐）**：`base_url` 填你的推理服务地址，`model` 填模型名，无需 key 留空
- **云端（如硅基流动）**：填对应 `base_url` / `model` / `api_key`

> 云端模型响应可能较慢（实测偶有 11–15 秒），建议把 `timeout_sec` 调到 **180 及以上**。
> 模型不可达时，AI 功能会**标明「AI 暂不可用」**，并保留查询数据；规则摘录只进入 prompt 当素材，**不会**用规则模板冒充 AI 结论。其余 PMS 功能不受影响。

---

## 8. 本地跑测试（pytest，SQLite）

`src/tests` 下是真正的 pytest 单测（unittest.TestCase 风格 + 函数式集成测试）。

`conftest.py` 在**测试会话启动时**把 `DATABASE_URL` 锁到 SQLite 临时库并灌最小种子（hotel / 四类 RBAC 账号 / 双审 finance·manager / 备用金 ¥2000 / 财务参数 / 会员体系 / 房型·房间·物资 / 协议客户），**无需任何外部依赖即可跑通**。

```bash
# 推荐：显式指定 SQLite（CI 也用同样方式）
DATABASE_URL="sqlite:///./tmp/ci_test.db" pytest src/tests -q

# 无服务时，需要真实后端的集成用例（test_flow.py 等）会自动 pytest.skip，不阻断 CI
```

> 早期版本 `src/tests` 是「脚本式冒烟测试」（直接打运行中的 127.0.0.1:8000、无断言）。
> 现已改造为带断言的 pytest 单测；CI 的 pytest 步骤为**硬性校验**（不再 `continue-on-error`）。

---

## 9. 生产部署

生产镜像由 `fangmanle-docker-build-tool` 构建，目标后端为 **PostgreSQL**。
本地若用 PG 起服务，部署时直接复用生产物料包即可（无需 SQLite→PG 方言转换）。

---

## 10. 常见问题

见 [FAQ_zh.md](FAQ_zh.md)。

---

## 11. 许可 · License

本仓库采用 **双许可**：

| 范围 | 许可证 |
|------|--------|
| 开源版（仓库默认主体） | [Apache License 2.0](LICENSE) |
| 商业版核心 | [Business Source License 1.1](LICENSE-BUSL) |

说明、范围划分与边界图见 [`LICENSING_zh.md`](LICENSING_zh.md)。  
商业版核心代码在 [`src/commercial/`](src/commercial/)（LLM 基座 + 各域 AI 场景）。fork 可去掉该目录后单独启动 OpenCore。  
「房满乐」等商标政策见 [`TRADEMARK_zh.md`](TRADEMARK_zh.md)（协议只管代码，不管商标；**fork 不可沿用「房满乐」品牌**）。  
商业授权：`commercial@fangmanle.com`。
