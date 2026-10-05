# 房满乐 PMS · 热更开发流（DEV）

> **第一次把产品跑起来：只看仓库根 [README.md Quick Start](../README.md) / [README_zh.md 第 2 节](../README_zh.md)**（`deploy\dev\start.bat`，端口 8081，带 SQLite demo）。
> **本文不是入门指南**，只写已经能登录之后如何 `--reload` / Vite HMR，避免每次 `docker build`。

---

## 为什么不用 `docker compose up` 改代码？

每次整栈 build 要数分钟。热更时三件脱离 docker：SQLite（或已有 PG）+ `uvicorn --reload` + `npm run dev`。
生产 / 给客户演示整栈：才用 README 里的 Compose。

---

## 三条路径（不要把 B 当成新人默认）

| 路径 | 适合谁 | 说明 |
|---|---|---|
| **README 第 2 节 bat（8081）** | **所有人的第一次** | 灌 demo、build 前端、看完整界面 |
| **A. SQLite + reload** | 已跑通过、改后端 | 沿用 `deploy/dev` 灌过的 sqlite 文件 |
| **B. 已有 PG + reload** | 本来就在调 PG 专属接口 | 不是 fork 默认 |
| **C. docker compose** | 部署 / 对齐生产 | 见 README Compose |

---

## 路径 A：SQLite 热更

适用：已经用 README 的 bat 看过界面，现在改 `src/`。

```powershell
$env:DATABASE_URL = "sqlite:///$PWD/data/fml_demo.db"
cd src
python -m uvicorn api:app --reload --reload-dir . --host 127.0.0.1 --port 8000
```

```bash
DATABASE_URL='sqlite:///./data/fml_demo.db' python -m uvicorn api:app --reload --reload-dir . --port 8000
```

账号 `admin / admin123`。库必须先由 `deploy/dev/start.bat`（或 `start.sh`）灌过完整 demo；没有旁路瘦库脚本。

### SQLite vs PG

| 维度 | SQLite | PG |
|---|---|---|
| 登录 / RBAC / 菜单 | 可用 | 可用 |
| 订单 / 客房 / 会员 / 财务 CRUD | 大部分可用 | 可用 |
| LLM 对话 | 走外部 API（需商业包） | 同左 |
| PG 专属（全文检索 / JSONB 等） | **会降级或 500** | 完整 |
| 并发写 | 单写者 | MVCC |

**何时用 PG**：生产、并发、依赖 JSONB/检索的报表。不是「SQLite 100% 兼容」。

---

## 路径 B：已有 PostgreSQL 时的热更

（仅当你已经在跑 PG。新人请停在 README 第 2 节。）

### 一次性准备（首次约 10 分钟）

#### 1. 启 PostgreSQL（docker 容器，长期运行）

```bash
docker run -d --name fml-pg -p 5432:5432 \
  -e POSTGRES_USER=fangmanle -e POSTGRES_PASSWORD=fmlpass -e POSTGRES_DB=fangmanle \
  -v fml-pg-data:/var/lib/postgresql/data \
  postgres:16-alpine
```

> **重要**：把 `-e POSTGRES_PASSWORD` 设成与 compose 里相同的值；否则后端连不上。

#### 2. 密码与 JWT

官方 Docker 入口：直接改 `deploy/docker/docker-compose.*.yml`（`POSTGRES_PASSWORD` / `FML_JWT_SECRET` / `FML_ADMIN_PASSWORD`）。
生产必须改掉演示默认值。

#### 3. 一次性数据库初始化

PG 官方镜像只在**空 volume** 上跑 `/docker-entrypoint-initdb.d/*.sh`。两种灌库方式：

- **方式 A**：用 psql 客户端手工跑
  ```bash
  cd db/postgres
  psql "postgresql://fangmanle:fmlpass@localhost:5432/fangmanle" -f 01_ddl/*.sql
  psql ... -f 02_init/*.sql
  psql ... -f 03_demo/*.sql  # 含 demo 数据；想要干净版本可跳过
  ```
- **方式 B**：用 docker compose 完整跑一次
  ```bash
  docker compose up -d
  # 看 db 日志确认 admin 密码已重置：
  docker compose logs db | tail -30
  ```
  ⚠️ **如果 `fangmanle-ai-native-pms_pgdata` volume 之前存在过，docker-init.sh 不会重跑**（PG 官方镜像设计）。这时用手动 INSERT：
  ```powershell
  docker exec fml-db psql -U fangmanle -d fangmanle -c "INSERT INTO public.roles (code, name, is_system) SELECT 'admin', '系统管理员', TRUE WHERE NOT EXISTS (SELECT 1 FROM public.roles WHERE code='admin');"
  docker exec fml-db psql -U fangmanle -d fangmanle -c "INSERT INTO public.hotels (id, code, name, timezone, currency, star_rating, is_active) SELECT 1, 'LOCAL', '本店', 'Asia/Shanghai', 'CNY', 4, TRUE WHERE NOT EXISTS (SELECT 1 FROM public.hotels WHERE id=1);"
  docker exec fml-db psql -U fangmanle -d fangmanle -c "INSERT INTO public.users (hotel_id, role_id, username, password_hash, full_name, is_active) SELECT 1, (SELECT id FROM public.roles WHERE code='admin'), 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '系统管理员', TRUE WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE username='admin');"
  ```

### 日常开发（热更）

完整 demo 启动请用 [`deploy/dev`](../deploy/dev)（见 [deploy/README.md](../deploy/README.md)）。

改代码时拆开跑：

```powershell
# Terminal 1 — API with reload (reuse the SQLite file from deploy/dev)
$env:DATABASE_URL = "sqlite:///$PWD/data/fml_demo.db"
cd src
python -m uvicorn api:app --reload --reload-dir . --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2 — Vite HMR
cd frontend
npm run dev
```

- API / Swagger: http://127.0.0.1:8000/docs  
- Vite (if used): http://127.0.0.1:5173  
- Login: `admin` / `admin123` (or `FML_ADMIN_PASSWORD` in the compose file for Docker PG)

---

## 路径 C：docker compose（**生产**）

```bash
cd <REPO>
# Edit deploy/docker/docker-compose.prod.yml for passwords / JWT / hotel
docker compose -f deploy/docker/docker-compose.prod.yml build --no-cache
docker compose -f deploy/docker/docker-compose.prod.yml up -d
```

Open http://localhost:8000/ ，账号 `admin / admin123`。

⚠️ **源码改了 → 必须 `--no-cache` 重 build**（docker layer cache 会冻住旧代码）。

---

## 文件变更触发的工作流

| 改的文件 | 自动行为 | 体验 |
|---|---|---|
| `src/**/*.py`（后端代码） | uvicorn `--reload` 检测文件变化 → **自动重启后端进程**（通常 1~2 秒） | 立即刷浏览器看效果 |
| `frontend/src/**/*.{vue,ts,css}`（前端） | vite HMR **热更前端模块**（毫秒级） | 浏览器立即看新 UI，**不需要刷新** |
| `frontend/tailwind.config.js` | vite HMR 全屏刷新 | 1~2 秒 |
| `requirements-prod.txt`（新增 Python 包） | ⚠️ 需手动：`pip install -r requirements-prod.txt` 后 uvicorn 才会加载 | 一次安装 |
| `package.json`（新增 Node 包） | ⚠️ 需手动：`cd frontend && npm install` 后 vite dev 才会加载 | 一次安装 |
| `.env`（改环境变量） | ⚠️ 需手动重启 dev 栈 | 一次 |
| `docker-compose.yml` | ⚠️ 需手动重启 docker compose | 偶发 |
| `db/postgres/**`（改 schema） | ⚠️ 需重建 PG 数据卷：`docker compose down -v && docker compose up -d` | 偶发 |

---

## 改代码验证流程（举例：改 src/api.py 的某个响应）

```
[uvicorn --reload + npm run dev 已跑]

1. 改 src/api.py:31 的 title
2. 保存
3. 看 .dev-logs/backend.log: uvicorn 打印 "Detected change in 'src/api.py', reloading"
4. 浏览器刷 http://127.0.0.1:5173/
   → Swagger 上 title 已更新
   → vite HMR 不需要重新加载前端（前端没改）
```

总耗时：**1~2 秒**。

---

## 为什么这样可行？

| 担心 | 解释 |
|---|---|
| 数据库表不变，但代码假设新表？ | uvicorn 启动时 `Base.metadata.create_all(engine)` 会**自动建新增的表**（但不改列、不删表）—— schema 演进安全。如果改了既有列类型，需手动 migration。 |
| vite HMR 后端没改也会跟着刷新？ | 不会。vite 监听 `frontend/src/**`；后端 `--reload` 监听 `src/**`（通过 `--reload-dir` 限定）。两者完全独立。 |
| 前端代理到后端？ | `vite.config.ts` 配了 `server.proxy['/api'] -> http://127.0.0.1:8766`（dev 环境）。浏览器从 vite 5173 访问 `/api/...` 会代理到 uvicorn 8766，**避免 CORS 问题**。 |
| 数据库 PG 怎么知道代码改了？ | 不知道。代码改的是 SQLAlchemy ORM 层的 query 逻辑（Python 文件），PG 不感知；PG 数据不变。 |

---

## 调试技巧

### 看后端日志
```powershell
Get-Content .\.dev-logs\backend.log -Wait    # PowerShell 实时跟随
# 或
tail -f .dev-logs/backend.log               # Git Bash
```

### 看前端日志
```powershell
Get-Content .\.dev-logs\frontend.log -Wait
```

### 手动重启某一边（不全部停）
- 后端：Ctrl+C 停掉 uvicorn，再重新 `python -m uvicorn ...`
- 前端：Ctrl+C 停掉 vite，再 `npm run dev`

### 调试 SQL（用 psql 直接查）
```bash
psql "postgresql://fangmanle:fmlpass@localhost:5432/fangmanle" -c "\dt"
psql ... -c "SELECT * FROM users LIMIT 3;"
```

### 调前端 devtools
浏览器 F12 → Console / Network → vite HMR 自动热更会在 Console 打印 `[vite] hmr update`。

---

## 与生产部署（docker compose up）的关系

| 场景 | 用什么 |
|---|---|
| 改 src/frontend/ 内部逻辑 | uvicorn --reload / vite HMR（秒级） |
| 加新 Python 包（`requirements-prod.txt`） | `pip install -r ...` 后重启 uvicorn（分钟级） |
| 加新数据库表 / 改 schema | reload + 手动 psql 或重建 PG 卷 |
| 加 Docker 层（volume / network / multi-stage build） | docker compose（看效果，但只偶尔） |
| **正式给客户部署** | docker compose up（最终交付） |

---

## 常见坑

| 现象 | 排查 |
|---|---|
| 后端 reload 失败 500 | 看 `.dev-logs/backend.log` 找栈跟踪 |
| 前端 vite 启动慢/失败 | `cd frontend && npm install` 重新装包 |
| vite HMR 报 "WebSocket connection failed" | 检查后端 8766 是否可达；可能 vite proxy 配错 |
| PG 连不上 | `docker ps` 看 PG 容器；`docker logs fml-pg` 看启动错误；.env 里 `POSTGRES_PASSWORD` 是否与 docker run 时一致 |
| admin 登录失败 | 看 `.dev-logs/db/postgres-init.log` 或 `.dev-logs/db/init.log`（docker-init.sh 输出）确认 FML_ADMIN_PASSWORD UPDATE 是否成功 |
| docker compose 起来后报旧 license 错误 | 旧镜像缓存了改源码前的代码，`docker compose build --no-cache pms && docker compose up -d` |

---

## 进阶：vscode 集成

1. 装 Python 扩展 + Pylint
2. 装 Volar（Vue Language Features） + ESLint
3. .vscode/launch.json 配置：
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Backend (uvicorn --reload)",
         "type": "debugpy",
         "request": "launch",
         "module": "uvicorn",
         "args": ["api:app", "--reload", "--port", "8766", "--reload-dir", "src"],
         "cwd": "${workspaceFolder}/src",
         "envFile": "${workspaceFolder}/.env"
       }
     ]
   }
   ```
4. 在 `src/api.py` 打断点 → F5 → 浏览器访问 → 单步调试

---

## FAQ

**Q：要不要把 .dev-logs/ .dev-pids/ 加入 .gitignore？**
A：已经加入（脚本创建后会被根 .gitignore 自动忽略）。

**Q：能不能后台跑热更栈，但日志输出到终端？**
A：前台开两个终端分别跑 uvicorn / vite 最直观；需要后台时用 `nohup ... > log 2>&1 &`，再用 `tail -f` 看日志。

**Q：SQLite 路径下，业务接口报 500 怎么办？**
A：先用 SQLite 看 UI/交互/菜单。涉及 PG JSONB / tsvector / 物化视图的端点切回 PG 路径跑。

**Q：怎么选 A/B/C？**
- 只想看效果 / 新人首次跑 / 单店本地 → A（SQLite / `deploy/dev`）
- 日常改代码 → B（uvicorn --reload + vite）
- 给客户部署 → C（docker compose）

---

*快速迭代心法：*
- **SQLite 30 秒看效果** → A
- **改 src/ → 等 2 秒刷浏览器** → B
- **改 frontend/src/ → vite HMR 自动** → B
- **改 schema / 加包** → B + 偶发手动
- **生产部署** → C