# 常见问题

[English](FAQ.md)

## 这是什么软件？

**房满乐 PMS** 是 **开源、可自托管、AI 原生的酒店 PMS**：**一个进程一家店**，不是多租户 SaaS。概述见 [README_zh.md](README_zh.md)，部署见 [INSTALL.md](INSTALL.md)。

## 有在线演示吗？

有：**[https://pms.sensepraxis.com/](https://pms.sensepraxis.com/)**，账号 `admin` / `admin123`。对应 Docker seed 样例数据，会定期重灌。本机部署见 [INSTALL.md](INSTALL.md)。

## 部署 / 启动失败

| 现象 | 处理 |
|------|------|
| `module 'psycopg' not found` | `DATABASE_URL` 驱动前缀与已装驱动不一致（`postgresql+psycopg://` / `psycopg2`）。SQLite 路径不必装 psycopg |
| 表在但登录「账号或密码错误」 | 未走官方灌库。SQLite 用 `deploy/dev/start.*`；PG 用 `deploy/docker` 的 seed 或 prod compose |
| 数据库连不上 | 未设 `DATABASE_URL` 时默认 `data/fml_demo.db`。生产必须显式 PostgreSQL |
| SQLite 上部分接口 500 | 依赖 PG 全文检索 / JSONB，生产请用 PostgreSQL |
| Compose 起来界面空 | 等 healthcheck；Docker 端口 **8000**，本地脚本 **8081** |

启动只认 `deploy/dev/` 与 `deploy/docker/`。见 [INSTALL.md](INSTALL.md)。

## 如何贡献

见 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md)。英文流程与 Conventional Commits：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 开源版和商业版差别

| | OpenCore | 商业核心 |
|--|----------|----------|
| 路径 | `src/` 除 `commercial/` | `src/commercial/` |
| 许可 | Apache-2.0 | BUSL-1.1 |
| 能力 | 域内核、规则定价、问数目录/SQL、交班待办 | LLM 会话、白话、问数对话、交班 AI 草稿等 |
| 关闭 AI | `FML_COMMERCIAL=0` 或删除 `src/commercial/` | — |

详见 [LICENSING_zh.md](LICENSING_zh.md)。关商业包后侧栏无「问数 / 大语言模型」。

## 一个进程开两家店？

不行。第二家店 = 另一进程 + YAML + 数据库。[docs/FORK_AND_NEW_HOTEL.md](docs/FORK_AND_NEW_HOTEL.md)。

## Fork 能否继续用「房满乐」品牌？

不能。[TRADEMARK_zh.md](TRADEMARK_zh.md)。

## 有没有 Redis？

运行时不用 Redis，compose 里也没有。

## API 文档？

运行中的 `/docs` 与 `/openapi.json`。[docs/API.md](docs/API.md)。
