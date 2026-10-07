# Changelog

[English](CHANGELOG.md) · **简体中文**

本仓库当前版本：**1.0.1**。以 git tag `v1.0.1`（发布时打上）与本文件对照；未打 tag 前以 `main` 最新提交为准。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.0.1] - 2026-10-07

### Fixed

- Docker 前端构建：在 Node 阶段拷贝仓库根 `locales/`，避免 Vite `@locales` 在 `npm run build` 时 ENOENT。
- Postgres 灌库脚本（`db/postgres/docker-init.sh`）：默认 `FML_DB_ROOT=/db/postgres`；Alpine 用 `sha256sum` 算管理员密码；同时存在时优先 `*.opensource.sql`；去掉 `DO` 块内无效的 `:'var'` 替换。
- Compose seed/prod：`FML_DB_ROOT=/db/postgres`；`pms` 与 `db` 均传入 `FML_ADMIN_*`。

### Added

- `run_prod`：种子未写入可登录 admin 时启动补建。
- README / INSTALL / FAQ / 文档站补充在线演示与产品截图（`https://pms.sensepraxis.com/`）。

## [1.0.0] - 2026-10-06

### Added

- Apache-2.0 OpenCore + BUSL-1.1 `src/commercial/` 双许可可运行 PMS 框架。
- 问数只读内核：`analytics.ask_catalog` / `ask_domain` / `ask_queries` / `ask_playbook` / `ask_pii` / `ask_snapshot`。
- 扩开展点：`register_intent` / `register_query` / `register_shift_scene` / `register_pricing_rule_hook`（见 `docs/FRAMEWORK.md`）。
- HTTP 分层：router 禁止直连 `commercial`（`tools/check_router_layer.py`）。
- 交班客情/待办规则展示：`finance.shift_handover_service.task_service`（关商业包不为空列表）。
- 关商业包时交班/接班页不渲染 AI 草稿面板（`commercialEnabled()`）。
- CI：`FML_COMMERCIAL=0` OpenCore 冒烟 + `pytest -m "not commercial"`；Dependabot；前端 `commercialEnabled` 门控检查。
- 社区脚手架：Issue / PR 模板、CODEOWNERS、NOTICE。

### Changed

- 发版前目录精简：去掉 `src/` 根抽取残留与 `mkt_coupon_ai` 兼容层；`ddl/` 仅保留指向 `db/` 的说明。
- 对外文档以英文文件名为准，中文副本为 `*_zh.md`。
- README / FAQ 开头补 What / 如何部署 / 为什么用（开源、自托管、AI 原生酒店 PMS）。

### Notes for framework users

跟版本请看本 CHANGELOG 与（发布后的）git tag，不要依赖写死的 GitHub 组织路径。Fork 后改 `pyproject.toml` `[project.urls]`。
