# Test coverage

## Targets (policy)

| Surface | Goal |
|---------|------|
| Core domain packages (`orders`, `rooms`, `hk`, `finance`, `guests`, `application`) | **≥ 60%** line coverage |
| Public HTTP API (`src/routers/` + `src/api.py`) | **100%** unit tests over time |

These are **release goals**, not a hard CI fail-under on day one of 1.0.0. GitHub Actions runs `pytest --cov` and uploads `coverage.xml`. Raise `fail_under` in `[tool.coverage.report]` when the numbers are honest.

## Local

```bash
pip install pytest pytest-cov
DATABASE_URL="sqlite:///./tmp/ci_test.db" pytest src/tests --cov=src --cov-report=term-missing --cov-report=xml
```

HTML: `--cov-report=html` then open `htmlcov/index.html`.

`conftest.py` uses temp SQLite; no Postgres required. Tests marked `commercial` need `src/commercial/` and `FML_COMMERCIAL` not `0`.
