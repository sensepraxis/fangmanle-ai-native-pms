# CI / CD

## GitHub Actions

Workflows under `.github/workflows/`:

| File | When | Jobs |
|------|------|------|
| `ci.yml` | push/PR to `main` | Ruff check+format, router/SPDX/i18n, pytest + coverage, OpenCore matrix, ESLint/Prettier, vue-tsc/build, OpenAPI artifact |
| `docs.yml` | push/PR to `main` | MkDocs Material → GitHub Pages (`website/` + sync from `INSTALL` / `ARCHITECTURE` / `FAQ`) |
| `dco.yml` | PR to `main` | Each commit has a DCO `Signed-off-by` trailer |
| `release.yml` | tags `v*` | GitHub Release notes from CHANGELOG |

Dependabot: `.github/dependabot.yml`. Contributions: DCO, not a CLA — [CONTRIBUTING.md](../CONTRIBUTING.md).

## GitLab CI

[`.gitlab-ci.yml`](../.gitlab-ci.yml) mirrors lint, pytest (OpenCore marker), and frontend build. No GitLab-specific registry push is configured.

## Local parity

```bash
ruff check src
ruff format --check src tools
python tools/check_router_layer.py
python tools/check_spdx.py
DATABASE_URL="sqlite:///./tmp/ci_test.db" pytest src/tests -q
FML_COMMERCIAL=0 python tools/ci_opencore_smoke.py
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm run build
```

See [CONTRIBUTING.md](../CONTRIBUTING.md).
