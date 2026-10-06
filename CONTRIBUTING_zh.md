# 贡献指南（CONTRIBUTING）

[English](CONTRIBUTING.md) · **简体中文**

感谢你关注 **房满乐 PMS（开源版）**！本仓库是 AI 原生酒店 PMS，欢迎以 Issue / Pull Request 形式参与贡献。新 PR 的标题与说明请用英文 Conventional Commits（见英文版第 4 节）。参与社区请遵守 [行为准则](CODE_OF_CONDUCT_zh.md)（[English](CODE_OF_CONDUCT.md)）。

---

本仓库是 **可运行应用**，不是 Python SDK（`pyproject.toml` 中 `packages = []`）。开发把 `src` 加进 `PYTHONPATH`，不要指望 `import fangmanle`。

## 1. 开发环境

推荐虚拟环境：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements-prod.txt
# 或仅 SQLite 核心：pip install -e ".[dev]"
# PostgreSQL：pip install -e ".[postgres,dev]"
```

项目支持 **SQLite / PostgreSQL 双后端**。本地开发只走官方入口：

```bat
pip install -r requirements-prod.txt
deploy\dev\start.bat demo-sg
```

Linux / macOS：`bash deploy/dev/start.sh demo-sg`。PostgreSQL 用 `deploy/docker/`（见 [INSTALL.md](INSTALL.md)、[deploy/README.md](deploy/README.md)）。

---

## 2. 本地验证

提交前请至少跑通 lint 与单测：

```bash
ruff check src
ruff format --check src tools
python tools/check_router_layer.py
python tools/check_spdx.py
DATABASE_URL="sqlite:///./tmp/ci_test.db" pytest src/tests -q
FML_COMMERCIAL=0 python tools/ci_opencore_smoke.py
FML_COMMERCIAL=0 pytest src/tests -q -m "not commercial"
cd frontend && npm run lint && npm run format:check && npm run typecheck
```

- 版本跟踪看根目录 [CHANGELOG_zh.md](CHANGELOG_zh.md)（当前 **1.0.0**）；发布时打 git tag `v1.0.0`。
- 依赖漏洞扫描走 GitHub Dependabot（`.github/dependabot.yml`）。
- Issue / PR 请用 `.github` 模板。Fork 后改 `pyproject.toml` `[project.urls]` 与 `.github/CODEOWNERS`。

- `conftest.py` 会在测试会话启动时把 `DATABASE_URL` 锁到 SQLite 临时库并灌最小种子，**无需数据库服务**即可跑通。
- `test_flow.py` 等需要真实后端的集成用例，在无服务时自动 `pytest.skip`，不阻断 CI。
- CI 的 pytest 步骤是**硬性校验**：任何单测失败都会阻断合并，**不要**再用 `continue-on-error` 规避。

---

## 3. 代码与文档规范

- **分层**：`router → application.* → service`。禁止在 `src/routers/` 里 `import commercial` 或调 `commercial_pack`。扩开展点见 [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md)。
- **目录 / 文件命名**：源码一律英文；若从原型（中文截图 / 中文文件名）抽取页面，请**翻译为有意义的英文文件名**后再并入 `新工程`。
- **语言**：**默认英文。** 新 PR 标题、说明、review、代码注释用英文（酒店术语可括注中文，如 night audit / 夜审）。存量中文注释可保留，改到那一块再改成英文；不要中英各写一遍。给人读的文档：英文正本 + `*_zh.md`。用户可见文案见下条 i18n。
- **代码风格**：Python 用 **Ruff**（检查 + 与 Black 兼容的格式化），不用 Black。前端用 **ESLint + Prettier**。无 Go。CI 会跑 `ruff format --check`、`npm run lint`、`npm run format:check`。
- **SPDX**：新源文件顶部加 `SPDX-License-Identifier: Apache-2.0`；`src/commercial/` 用 `BUSL-1.1`。检查：`python tools/check_spdx.py`（`--fix` 可批量补）。
- **用户可见文案（i18n）**：只改仓库根 [`locales/`](locales/)（`python tools/i18n_catalog.py` 同步镜像）。展示字符串必须走 `t()` 或稳定 key（见 [`docs/I18N.md`](docs/I18N.md)）。禁止在新 Vue 模板 / toast 里写死中文或英文。禁止 `t('交班')+t('人')` 这类碎片拼接。交班差异术语：长款 = Overage、短款 = Shortage、对平 = Balanced（key：`finance.shift.*`）。新 AI scene 须同时更新 `src/commercial/ai_core/prompt_packs/zh-CN.json` 与 `en.json`。精翻优先改 `tools/i18n_priority_translate.py` 的 `HAND` 后运行该脚本。
- **功能取舍**：不要无脑堆功能。每个改动先讲清「为什么」（正确性 / 性能 / 可测试性），再给做法。
- **安全红线**：绝不提交密钥、证书、`.env` 中的真实口令；敏感字段（证件号等）走字段级加密（见 `cryptography` / 可选 `gmssl`）。

---

## 4. 分支与提交流程

1. 从 `main` 切出特性分支：`feat/xxx`、`fix/xxx`、`docs/xxx`。
2. 小步提交，信息用英文 **[Conventional Commits](https://www.conventionalcommits.org/)**（与英文版第 4 节相同），例如 `feat: add AR/AP workbench filter`、`fix: block takeover when guest notes are unconfirmed`。
3. 提交前自测 lint + pytest。
4. 每条 commit 必须带 DCO `Signed-off-by`：`git commit -s`（见下一节）。
5. 开 Pull Request 到 `main`，用英文写 **why / scope / how verified**；CI 全绿后方可合并。PR 模板：`.github/PULL_REQUEST_TEMPLATE.md`。

---

## 5. 贡献者声明（DCO）

本仓库**不签 CLA**。贡献用 [Developer Certificate of Origin](https://developercertificate.org/)（1.1）：你声明有权按本项目许可提交该改动。

每条 commit 末尾须有与 `git config user.name` / `user.email` 一致的行：

```
Signed-off-by: Your Name <you@example.com>
```

Git 可自动追加：

```bash
git commit -s -m "feat: add AR/AP workbench filter"
```

若已经推上去但漏了 `-s`：

```bash
git rebase HEAD~N --signoff
git push --force-with-lease
```

缺少该行的 PR 会在 **DCO** 检查失败（`.github/workflows/dco.yml`）。Dependabot 等 bot 提交豁免。

---

## 6. 提交 Issue

请用 `.github/ISSUE_TEMPLATE/` 三类模板（Bug、Feature、Question）。安全问题见 [SECURITY.md](SECURITY.md)。

- Bug：附复现步骤、期望 / 实际、日志片段、数据库后端（SQLite / PostgreSQL）。
- 需求 / 讨论：先说业务场景与约束，再提方案；方案类问题建议给出**全量选项谱**供选择，而非单一收窄结论。
- Question：说明想做什么、已读文档或已尝试命令；不要当缺陷或新功能提。

---

## 7. 许可

本项目采用 **双许可**：开源版为 **Apache-2.0**，商业版核心为 **BUSL 1.1**（见 [`LICENSING_zh.md`](LICENSING_zh.md)、[`LICENSE`](LICENSE)、[`LICENSE-BUSL`](LICENSE-BUSL)）。

- 向开源版路径提交的贡献，默认按 **Apache-2.0** 授权。
- 向 `src/commercial/` 或标注 `SPDX-License-Identifier: BUSL-1.1` 的路径提交的贡献，同意适用 **BUSL-1.1**（及其 Change Date 后的 Change License）。
