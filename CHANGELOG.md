# Changelog

Current version: **0.1.0-alpha**. Pair this file with git tag `v0.1.0-alpha` when that tag exists; until then, `main` is the source of truth.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Chinese copy: [CHANGELOG_zh.md](CHANGELOG_zh.md).

## [0.1.0-alpha] - 2026-10-04

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
