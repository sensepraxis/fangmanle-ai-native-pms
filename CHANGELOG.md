# Changelog

Current version: **1.0.1**. Pair this file with git tag `v1.0.1` when that tag exists; until then, `main` is the source of truth.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Chinese copy: [CHANGELOG_zh.md](CHANGELOG_zh.md).

## [1.0.1] - 2026-10-07

### Fixed

- Docker frontend build: copy repo-root `locales/` into the Node stage so Vite `@locales` resolves during `npm run build`.
- Postgres seed init (`db/postgres/docker-init.sh`): default `FML_DB_ROOT` to `/db/postgres`, hash admin passwords without `python3` on Alpine, prefer `*.opensource.sql` when both dumps exist, and reset admin without broken `DO` + `:'var'` substitution.
- Compose seed/prod: set `FML_DB_ROOT=/db/postgres`; pass `FML_ADMIN_*` into the `pms` service as well as `db`.

### Added

- `run_prod`: bootstrap a loginable admin when SQL seed never created one.
- Live demo links and product screenshots in README / INSTALL / FAQ / website docs (`https://pms.sensepraxis.com/`).

## [1.0.0] - 2026-10-06

### Added

- Dual-license runnable PMS: Apache-2.0 OpenCore + BUSL-1.1 `src/commercial/`.
- Read-only Ask kernel: `analytics.ask_catalog` / `ask_domain` / `ask_queries` / `ask_playbook` / `ask_pii` / `ask_snapshot`.
- Extension points: `register_intent` / `register_query` / `register_shift_scene` / `register_pricing_rule_hook` ([docs/FRAMEWORK.md](docs/FRAMEWORK.md)).
- HTTP layering: routers must not import `commercial` (`tools/check_router_layer.py`).
- Shift guest-notes / todos via `finance.shift_handover_service.task_service` (not an empty list when commercial is off).
- Shift/takeover pages hide the AI draft panel when commercial is off (`commercialEnabled()`).
- CI: OpenCore smoke with `FML_COMMERCIAL=0`, `pytest -m "not commercial"`, Dependabot, frontend `commercialEnabled` gate.
- Community scaffolding: issue/PR templates, CODEOWNERS, NOTICE.

### Changed

- Pre-release tree cleanup: removed leftover extract files at `src/` root and the `mkt_coupon_ai` shim; `ddl/` is a pointer to `db/`.
- Community docs are English at the canonical filenames; Chinese copies use `*_zh.md`.
- README / FAQ lead with What / How to deploy / Why (open-source, self-hosted, AI-native hotel PMS).

### Notes for framework users

Follow this changelog and (after release) git tags. Do not hard-code a GitHub org path. After a fork, update `pyproject.toml` `[project.urls]`.
