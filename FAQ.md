# FAQ

[简体中文](FAQ_zh.md)

## What is this software?

**Fangmanle PMS** is an **open-source**, **self-hosted**, **AI-native hotel PMS** for **one hotel per process**. Not multi-tenant SaaS. Overview: [README.md](README.md). Deploy: [INSTALL.md](INSTALL.md).

## Is there a live demo?

Yes: **[https://pms.sensepraxis.com/](https://pms.sensepraxis.com/)** — login `admin` / `admin123`. It runs the Docker seed stack (sample data; reset periodically). For your own machine use [INSTALL.md](INSTALL.md).

## Deploy / start failed

| Symptom | What to do |
|---------|------------|
| `module 'psycopg' not found` | `DATABASE_URL` prefix must match the installed driver (`postgresql+psycopg://` vs `psycopg2`). SQLite paths should not need psycopg. |
| Login “wrong password” but tables exist | You did not use the official seed. SQLite: `deploy/dev/start.*`. PostgreSQL: `deploy/docker` seed or prod compose. |
| Cannot connect to DB | Unset `DATABASE_URL` means `data/fml_demo.db`. Production must set a PostgreSQL URL. |
| SQLite HTTP 500 on some APIs | Those APIs need PG full-text / JSONB. Use PostgreSQL in production. |
| Compose up but empty UI | Wait for healthchecks; confirm port **8000** (Docker) vs **8081** (dev script). |

Start only via `deploy/dev/` and `deploy/docker/`. See [INSTALL.md](INSTALL.md).

## How do I contribute?

[CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, `ruff` + `pytest`, no router → `commercial` imports. Issues/PRs use `.github` templates.

## OpenCore vs commercial

| | OpenCore | Commercial Core |
|--|----------|-----------------|
| Path | `src/` except `commercial/` | `src/commercial/` |
| License | Apache-2.0 | BUSL-1.1 |
| What you get | PMS kernel, rule pricing, Ask catalog/SQL, shift todos | LLM sessions, narrative, Ask chat, shift AI draft, … |
| How to turn AI off | `FML_COMMERCIAL=0` or delete `src/commercial/` | N/A |

Details: [LICENSING.md](LICENSING.md). Sidebar Ask / LLM settings disappear when commercial is off.

## Can I run two hotels in one process?

No. Second hotel = second process + YAML + database. [docs/FORK_AND_NEW_HOTEL.md](docs/FORK_AND_NEW_HOTEL.md).

## May I keep the Fangmanle name on a fork?

No. [TRADEMARK.md](TRADEMARK.md).

## Where is Redis?

Not used. Do not expect a Redis service in compose.

## Where is the API spec?

Running app: `/docs` (Swagger UI) and `/openapi.json`. [docs/API.md](docs/API.md).

## Tests

```bash
DATABASE_URL="sqlite:///./tmp/ci_test.db" pytest src/tests -q
```

Coverage policy: [docs/COVERAGE.md](docs/COVERAGE.md).
