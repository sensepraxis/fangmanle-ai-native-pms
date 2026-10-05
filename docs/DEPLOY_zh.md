# 房满乐 PMS · 离线物料包构建与部署运行手册

> **开源读者请先看**：日常安装用仓库根 [INSTALL.md](../INSTALL.md) 与 [`deploy/docker`](../deploy/README.md)（改 compose 里的密码与 `FML_HOTEL`）与 [FORK_AND_NEW_HOTEL.md](FORK_AND_NEW_HOTEL.md)。  
> 本文描述的是**可选**离线物料包流程（需额外构建工具仓库时），**不是**开源默认路径。  
> 两种模式：**demo**（含样例数据）/ **hotel**（仅 DDL + 初始化）。  
> **单店单进程**：用 `FML_HOTEL` 选定酒店 YAML。

---

> 历史私有部署地址与构建机路径已从文档移除；请把 `source_root` 换成你本机的本仓库路径。

## 0. 前置条件

**本机（构建机，Windows + PowerShell + Docker Desktop）**
- Docker Desktop 已启动（构建需要 `docker build` + `docker save`）。
- Python 3.12/3.13/3.14，且含 `PyYAML`（构建工具不使用 venv，直接调系统 Python）。
- 构建工具 `fangmanle-docker-build-tool` 与源码 `fangmanle-ai-native-pms` 同级目录。
- 无任何商业 License 校验逻辑（已从 OpenCore 仓移除）。

**目标服务器（Ubuntu）**
- 已安装 `docker-ce` + `docker-compose-plugin`（**本产品只支持 Compose V2**）。
- `install.sh` 在缺失时会打印安装指引；未装时：`sudo apt-get install -y docker-compose-plugin`。

---

## 1. 构建配置 `build_config.yaml`

构建参数全部来自此文件；CLI 的 `--mode` 会覆盖文件里的 `mode`。常用字段：

```yaml
# ============================================================
# 房满乐 · 离线构建工具配置
# 运行： python build_tool.py --config build_config.yaml --mode demo
# 说明： 所有路径支持 / 或 \\；本机运行（Windows + PowerShell）。
# ============================================================
project:
  # 源码根目录（fangmanle-ai-native-pms）。可写绝对路径，也可写相对本配置文件的路径。
  source_root: "../fangmanle-ai-native-pms"   # 改成你的本仓库路径
  # 应用镜像名与版本号（docker build -t <image_name>:<image_tag> .）
  image_name: "fangmanle-pms"
  image_tag: "1.0.0"
  # Postgres 离线镜像（与镜像内 Dockerfile / compose 一致）
  postgres_image: "postgres:16-alpine"
# 默认模式：demo（含样例数据）或 hotel（仅 DDL + 初始化）。CLI 的 --mode 会覆盖此项。
mode: "demo"
# 打包相关
pack:
  # 是否调用本仓库 deploy/offline/pack.ps1 组装离线目录（步骤 5，db 源来自 project.source_root）
  use_pack_ps1: true
  # true  => 工具传 -SkipSave 给 pack.ps1（只组目录），再由工具自己 docker save 导出镜像 tar
  # false => 直接交给 pack.ps1 执行 docker save / docker pull（需要 Docker 与网络）
  export_images: true
# 部署目标平台（影响安装入口脚本）
# auto   => 同时生成 install.sh(bash) 与 install.ps1(PowerShell)，部署时按目标平台挑一个跑
# linux  => 仅生成 install.sh
# windows=> 仅生成 install.ps1（Windows Docker Desktop 原生 PowerShell）
# 说明：docker-compose.yml 本身已跨平台（named volume + 相对 bind mount），与 OS 无关。
deploy:
  target: "auto"
# 输出
output:
  # 最终物料包目录。留空 => 使用 pack.ps1 的产出位置：<构建工具>/deploy/offline-dist/<mode>
  # （deploy 已迁移至构建工具仓库，不再放在源码工程 fangmanle-ai-native-pms 下）
  dir: ""
  # 构建报告文件名（写到物料包目录内）
  report: "build_report.md"
  manifest: "build_manifest.json"
```

> 想换模式时**两种做法二选一**：
> 1. CLI 显式指定：`python build_tool.py --config build_config.yaml --mode hotel`
> 2. 改 `build_config.yaml` 里的 `mode: "hotel"`，然后 `python build_tool.py --config build_config.yaml`（省略 `--mode` 即回退文件里的 `mode`）。

---

## 2. 本地构建（12 步流程）

### 2.1 命令

```powershell
cd E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-docker-build-tool

# 方式 A：PowerShell 一键入口（自动带 --config build_config.yaml）
.\run.ps1 -Mode demo          # 等价于 python build_tool.py --config build_config.yaml --mode demo
.\run.ps1 -Mode hotel

# 方式 B：直接调 Python（素材中实际使用的写法）
python build_tool.py --config build_config.yaml --mode demo
python build_tool.py --config build_config.yaml --mode hotel

# 常用开关（run.ps1 同名开关，或传给 build_tool.py 的双横杠）
#   --yes          非交互直删物料包目录（CI 用；否则 STEP 1 会等待输入 yes）
#   --no-clean     跳过 STEP 1 清理
#   --skip-build   跳过 docker build
#   --skip-images  跳过 docker save（已有 tar 时复用）
```

### 2.2 12 步详解

| # | 步骤 | 行为 | demo | hotel |
|---|------|------|------|-------|
| 1 | 清理物料包目录(带确认) | 删除 `deploy/offline-dist/<mode>`（不可恢复，需输入 `yes`；CI 用 `--yes`） | 执行 | 执行 |
| 2 | 构建应用镜像 | `docker build -f deploy/docker/Dockerfile -t fangmanle-pms:1.0.0 .`（在 `source_root` 内） | 执行 | 执行 |
| 3 | 校验样例数据 SQL | 检查 `fangmanle-ai-native-pms/db/postgres/03_demo/010_full_demo_data.sql` 已随仓库提交（**零 SQLite 依赖**） | 校验 | **[SKIP]** 不含样例数据 |
| 4 | 打包离线目录 | `pack.ps1 -Edition <mode> -Tag 1.0.0 -SkipSave`（复制 `db/` 与模板） | 执行 | 执行 |
| 5 | 导出应用镜像 tar | `docker save` → `images/fangmanle-pms_1.0.0.tar` | 执行 | 执行 |
| 6 | 导出 Postgres 镜像 tar | `docker save` → `images/postgres_16-alpine.tar` | 执行 | 执行 |
| 7 | 生成 docker-compose.yml | 按模式生成（`FML_DB_SKIP_DEMO` 不同） | 执行 | 执行 |
| 8 | 生成安装脚本 | `install.{sh,ps1}`（`target=auto` 时两者都生成） | 执行 | 执行 |
| 9 | 全包换行符规范化(LF) | 物料包内文本文件统一 LF | 执行 | 执行 |
| 10 | 检查物料包目录结构 | 必需项 16 · 缺失 0 | 执行 | 执行 |

> 产出目录：`deploy/offline-dist/<mode>/`，内含 `docker-compose.yml`、`.env.example`、`install.sh`、`install.ps1`、`README.md`、`db/`、`images/`、`build_report.md`、`build_manifest.json`。

### 2.3 demo 模式实测日志节选（构建机，2026-09-13 14:47）

```text
PS E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-docker-build-tool> python build_tool.py --config build_config.yaml
=== 房满乐离线构建 · 模式=demo · 镜像=fangmanle-pms:1.0.0 ===
源码根: E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-ai-native-pms
物料包: E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-docker-build-tool\deploy\offline-dist\demo
──── STEP 1  清理物料包目录(带确认) ────────────
[SKIP] 目录不存在，无需清理: ...\deploy\offline-dist\demo
──── STEP 2  构建应用镜像 ─────────────────────
$ docker build -f deploy/docker/Dockerfile -t fangmanle-pms:1.0.0 .
   #19 CACHED
   #20 exporting to image
   #20 exporting layers done
   #20 naming to docker.io/library/fangmanle-pms:1.0.0 done
   #20 unpacking to docker.io/library/fangmanle-pms:1.0.0 done
   #20 DONE 0.1s
[OK] 构建应用镜像 完成（2026-09-13 14:47:45）
──── STEP 3  校验样例数据 SQL ───────────────────
$ check E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-ai-native-pms\db\postgres\03_demo\010_full_demo_data.sql
[OK] 校验样例数据 SQL 完成（2026-09-13 14:47:45）
──── STEP 4  打包离线目录 ─────────────────────
$ pack.ps1 -Edition demo -Tag 1.0.0 -SkipSave
   ======== pack demo (with_demo=True) ========
   All done. Upload the folder to server (no app source needed).
[OK] 打包离线目录 完成（2026-09-13 14:47:45）
──── STEP 5  导出应用镜像 tar ───────────────────
$ docker save -o ...\demo\images\fangmanle-pms_1.0.0.tar
[OK] 导出应用镜像 tar 完成（2026-09-13 14:47:46）
──── STEP 7  导出 Postgres 镜像 tar ───────────
$ docker save -o ...\demo\images\postgres_16-alpine.tar
[OK] 导出 Postgres 镜像 tar 完成（2026-09-13 14:47:47）
──── STEP 7  生成 docker-compose.yml ───────
[OK] 生成 docker-compose.yml 完成（2026-09-13 14:47:47）
──── STEP 8  生成安装脚本 ───────────────────────
$ write ...\demo/install.{sh,ps1} (target=auto)
[OK] 生成安装脚本 完成（2026-09-13 14:47:47）
──── STEP 9  全包换行符规范化(LF) ────────────────
[OK] 全包换行符规范化(LF) 完成（2026-09-13 14:47:48）
──── STEP 10 检查物料包目录结构 ────────────────────
   [x] docker-compose.yml   # 编排文件（按模式生成）
   [x] .env.example         # 环境变量模板
   [x] install.sh / install.ps1
   [x] README.md
   [x] db/01_ddl/  db/02_init/  db/03_demo/
   [x] images/fangmanle-pms_1.0.0.tar  images/postgres_16-alpine.tar
   必需项 16 · 缺失 0
[OK] 检查物料包目录结构 完成（2026-09-13 14:47:48）
=== 完成。物料包目录：...\deploy\offline-dist\demo ===
```

> 首次构建时 STEP 1 会打印警告并要求输入 `yes` 才删除旧物料包目录；非交互用 `.\run.ps1 -Mode demo -Yes`。

### 2.4 hotel 模式实测日志节选（对比，2026-09-13 14:35）

```text
=== 房满乐离线构建 · 模式=hotel · 镜像=fangmanle-pms:1.0.0 ===
──── STEP 3  校验样例数据 SQL ────
[SKIP] hotel 模式不含样例数据（仅 DDL + 初始化）
──── STEP 5  打包离线目录 ─────────────────────
$ pack.ps1 -Edition hotel -Tag 1.0.0 -SkipSave
   ======== pack hotel (with_demo=False) ========
──── STEP 12 检查物料包目录结构 ────────────────────
   必需项 16 · 缺失 0
=== 完成。物料包目录：...\deploy\offline-dist\hotel ===
```

> hotel 与 demo 的唯一实质差异：**STEP 4 跳过样例数据校验**，且 `docker-compose.yml` 中 `FML_DB_SKIP_DEMO: "1"`。两种模式都会写入 `db/02_init/005_init_hotel_admin.sql`（admin/admin123 初始账号），所以 hotel 部署后也能用 admin/admin123 登录，只是没有演示业务数据。

---

## 3. 上传到服务器（scp 注意点）

⚠️ **常见坑**：物料包在 `deploy/offline-dist/<mode>/`，**不在构建工具根目录**。从根目录直接 `scp -r demo ...` 会报 `stat local "demo": No such file or directory`。必须先 `cd` 进 `offline-dist`：

```powershell
cd E:\Workspace\AI-Native-PMS-OpenSource\fangmanle-ai-native-pms-docker-build-tool\deploy\offline-dist

# demo
scp -r demo gwzx@123.206.203.128:/home/gwzx/fangmanle/
# hotel
scp -r hotel gwzx@123.206.203.128:/home/gwzx/fangmanle/
```

**demo 模式 scp 文件清单（节选，含样例数据）**

```text
.env.example                                          100%  429
build_manifest.json                                   100% 4356
build_report.md                                       100% 2962
001_core_schema.sql                                   100% 194KB
002_pms_core.sql ... 006_seed_parity_tables.sql
001_roles.sql ... 004_channels_catalog.sql
005_init_hotel_admin.sql                              100% 1258   ← admin/admin123 初始账号（两模式都有）
000_prepare.sql                                       100% 3517
010_full_demo_data.sql                               100% 2243KB  ← 样例业务数据（demo 才有）
011_system_config.sql                                100%   11KB   ← 系统配置种子（demo 才有）
refresh_demo.sh
docker-init.sh
docker-compose.yml
fangmanle-pms_1.0.0.tar                              100%  82MB
postgres_16-alpine.tar                               100% 111MB
install.ps1  install.sh
README.md
```

**hotel 模式 scp 文件清单（节选，无样例数据）**

```text
.env.example  build_manifest.json  build_report.md
001_core_schema.sql ... 006_seed_parity_tables.sql
001_roles.sql ... 004_channels_catalog.sql
005_init_hotel_admin.sql                              100% 1258   ← 仅此初始化种子，无 010/011
docker-init.sh  docker-compose.yml
fangmanle-pms_1.0.0.tar  postgres_16-alpine.tar
install.ps1  install.sh  README.md
# 注意：hotel 包里没有 000_prepare.sql / 010_full_demo_data.sql / 011_system_config.sql
```

---

## 4. 服务器部署（`install.sh`）

```bash
ssh gwzx@123.206.203.128
cd ~/fangmanle/demo        # 或 ~/fangmanle/hotel
bash install.sh
```

### 4.1 demo 模式 `install.sh` 实测（2026-09-13）

```text
gwzx@VM-16-9-ubuntu:~/fangmanle/demo$ sudo bash install.sh
✅ 已生成 .env 并自动填入强随机密码 / JWT 密钥（无需手动修改）。
   如需查看：grep -E 'POSTGRES_PASSWORD|FML_JWT_SECRET' .env
docker load -i images/fangmanle-pms_1.0.0.tar
Loaded image: fangmanle-pms:1.0.0
docker load -i images/postgres_16-alpine.tar
Loaded image: postgres:16-alpine
[compose] 使用系统 docker compose (V2 插件)
[compose] 预清理旧部署：docker compose down --remove-orphans -v
[compose] 启动服务 ...
[+] up 4/4
 ✔ Network demo_default         Created
 ✔ Volume demo_pgdata_demo      Created
 ✔ Container fangmanle-ai-native-pms-db  Healthy
 ✔ Container fangmanle-ai-native-pms-pms Started
NAME                 IMAGE                 COMMAND                  SERVICE   STATUS          PORTS
fangmanle-ai-native-pms-db    postgres:16-alpine    "docker-entrypoint.s…"   db        Up 6s (healthy) 127.0.0.1:5432->5432/tcp
fangmanle-ai-native-pms-pms   fangmanle-pms:1.0.0   "python /app/src/run…"   pms       Up (starting)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
✅ 完成。默认端口见 .env 中 PMS_PORT（一般为 8000）
```

`install.sh` 自动完成：
1. 无 `.env` 时复制 `.env.example`，并用强随机值自动填充 `POSTGRES_PASSWORD` / `FML_JWT_SECRET`（**无需手工改密码**）。
3. `docker load` 两个镜像 tar。
4. 检测 Docker Compose **V2**（仅 V2，旧 V1 不兼容）。
5. `docker compose down -v`（清旧数据卷 → 用当前 `.env` 密码重新初始化）→ `up -d`。

> ⚠️ **PostgreSQL 密码只在空卷首次 `initdb` 时生效**。一旦卷有数据，改 `.env` 里的 `POSTGRES_PASSWORD` 无效。要换密码必须 `docker compose down -v` 删卷重建（数据会丢，初始无业务数据无所谓）；想保留数据改密码需进容器 `ALTER USER`。这也就是 hotel 部署失败报 `password authentication failed` 的常见根因——旧卷密码与当前 `.env` 不一致。

### 4.2 hotel 模式差异

- `FML_DB_SKIP_DEMO: "1"` → 跳过整个 `03_demo` 目录（不加载 `010` 样例数据、`011` 系统配置）。
- 仍加载 `02_init/005_init_hotel_admin.sql` → **admin/admin123 可登录**，但库里只有这一个账号，无演示业务数据、无预填系统配置。
- 部署后进入「系统配置」页手填 LLM / 天地图 / 财务参数等（密钥占位 `__DEMO_FILL__*` 仅供 demo 演示，生产不应带默认密钥）。

### 4.3 系统配置种子（demo 专属：LLM / 地图 / 财务参数）

- 文件：`fangmanle-ai-native-pms/db/postgres/03_demo/011_system_config.sql`（**随仓库提交、手维护**）。
- 内容：`app_settings` 的 `llm`（DeepSeek + 硅基流动 Qwen3-8B 双 provider）与 `map`（天地图）；财务 6 表 `finance_float_carry` / `finance_tax_configs` / `finance_payment_terms` / `finance_acquiring_channels` / `finance_credit_customers` / `finance_bad_debt_rates` + 审计 `finance_param_audits`。
- 加载规则（零代码改动）：`011` 在 `03_demo` 内，`FML_DB_SKIP_DEMO != 1` 时整目录加载。
  - **demo**：`03_demo` 全加载 → 配置入库，演示完整功能。
  - **hotel**：`FML_DB_SKIP_DEMO=1` 跳过 → 配置不入库，由酒店自填。
- 密钥占位：LLM `api_key`、天地图 `tianditu_tk` / `tianditu_js_tk` 为 `__DEMO_FILL__*`，**部署后请在「系统配置」页补填真实密钥**（`run_prod.py` 不写种子，不会覆盖）。
- 重生成 demo 业务数据用 `refresh_demo.sh`（只重建 `001` / `010`，**不会动 `011`**）；改演示配置直接编辑 `011` 后重新构建。
