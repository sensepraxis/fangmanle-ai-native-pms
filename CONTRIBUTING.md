# Contributing

Thanks for looking at **Fangmanle PMS (open source)**. This repo is a **runnable application**, not a Python SDK (`packages = []` in `pyproject.toml`). Put `src` on `PYTHONPATH`; do not `import fangmanle`.

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md) ([中文](CODE_OF_CONDUCT_zh.md)).

[简体中文](CONTRIBUTING_zh.md)

---

## 1. Dev environment

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements-prod.txt
# SQLite-only extras: pip install -e ".[dev]"
# PostgreSQL:         pip install -e ".[postgres,dev]"
```

Use the official start path:

```bat
deploy\dev\start.bat demo-sg
```

Linux / macOS: `bash deploy/dev/start.sh demo-sg`. PostgreSQL: `deploy/docker/` — [INSTALL.md](INSTALL.md).

---

## 2. Local checks

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

- Versioning: [CHANGELOG.md](CHANGELOG.md) (now **1.0.1**); release tag `v1.0.1`.
- Dependency alerts: GitHub Dependabot (`.github/dependabot.yml`).
- After a fork, update `pyproject.toml` `[project.urls]` and `.github/CODEOWNERS`.
- `conftest.py` pins tests to a temp SQLite DB and seeds a minimal hotel. No database server required.
- HTTP integration tests (`test_flow.py` and similar) `pytest.skip` when no server is up.
- CI pytest is **blocking**. Do not re-enable `continue-on-error`.

Coverage targets: [docs/COVERAGE.md](docs/COVERAGE.md).

---

## 3. Code and docs

- **Layers:** `router → application.* → service`. No `import commercial` or `commercial_pack` from `src/routers/`. Extension points: [docs/FRAMEWORK.md](docs/FRAMEWORK.md).
- **Names:** source paths in English.
- **Language:** new PR titles, review comments, and code comments in **English**. Existing Chinese comments may stay until that code is touched; do not add bilingual duplicates. Community docs: English canonical files plus `*_zh.md`. User-visible copy goes through root [`locales/`](locales/) (`python tools/i18n_catalog.py`). Do not hard-code Chinese or English in new Vue templates/toasts. Do not concatenate fragments like `t('Handover')+t('staff')`. Shift cash terms: Overage / Shortage / Balanced (`finance.shift.*`). New AI scenes must update both `src/commercial/ai_core/prompt_packs/zh-CN.json` and `en.json`.
- **Style:** Python is **Ruff** (lint + Black-compatible format), not Black. Frontend is **ESLint** + **Prettier**. There is no Go. CI fails on `ruff format --check`, `npm run lint`, and `npm run format:check`.
- **SPDX:** new source files start with `SPDX-License-Identifier: Apache-2.0`, or `BUSL-1.1` under `src/commercial/`. `python tools/check_spdx.py` (`--fix` to insert).
- **Product:** argue why (correctness / performance / testability) before how.
- **Secrets:** never commit keys, certs, or real `.env` passwords. PII fields use field-level encryption (`cryptography` / optional `gmssl`).

---

## 4. Branch and PR workflow

1. Branch from `main`: `feat/…`, `fix/…`, `docs/…`.
2. Small commits using **[Conventional Commits](https://www.conventionalcommits.org/)**:
   - `feat: add AR/AP workbench filter`
   - `fix: block takeover when guest notes are unconfirmed`
   - `docs: add INSTALL.md`
   - `test: cover wecom callback enqueue`
   - `chore: bump ruff`
3. Run lint + pytest locally.
4. Every commit must carry a DCO `Signed-off-by` trailer: `git commit -s` (see below).
5. Open a PR to `main`. Describe **why**, **scope**, and **how you verified**. Merge only when CI is green.

PR template: `.github/PULL_REQUEST_TEMPLATE.md`.

---

## 5. Developer Certificate of Origin (DCO)

There is **no CLA to sign**. Contributions are certified with the [Developer Certificate of Origin](https://developercertificate.org/) (version 1.1): you assert you have the right to submit the work under this project's licenses.

Each commit must end with a trailer that matches `git config user.name` and `user.email`:

```
Signed-off-by: Your Name <you@example.com>
```

Git can add it:

```bash
git commit -s -m "feat: add AR/AP workbench filter"
```

If a commit was pushed without `-s`:

```bash
git rebase HEAD~N --signoff   # N = number of commits to fix
git push --force-with-lease
```

PRs without a valid trailer fail the **DCO** GitHub Action (`.github/workflows/dco.yml`). Bot commits such as Dependabot are exempt.

---

## 6. Issues

Use `.github/ISSUE_TEMPLATE/` (Bug, Feature, Question). Security: [SECURITY.md](SECURITY.md).

- Bugs: repro steps, expected vs actual, log excerpt, backend (SQLite / PostgreSQL).
- Features: business scenario and constraints first; list options when the design is open.
- Questions: what you are trying to do, docs or commands you already tried; not a defect or a feature request.

---

## 7. License of contributions

Dual license: OpenCore **Apache-2.0**, `src/commercial/` **BUSL-1.1** — [LICENSING.md](LICENSING.md), [LICENSE](LICENSE), [LICENSE-BUSL](LICENSE-BUSL).

- Contributions to OpenCore paths are Apache-2.0 by default.
- Contributions under `src/commercial/` or `SPDX-License-Identifier: BUSL-1.1` are BUSL-1.1 (and the Change License after the Change Date).
