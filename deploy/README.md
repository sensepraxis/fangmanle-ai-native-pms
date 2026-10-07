# Start and deploy

Official entry: [INSTALL.md](../INSTALL.md). Dockerfile and compose live under this directory, not the repo root.

| Mode | Directory | Notes |
|------|-----------|--------|
| Local dev (SQLite demo, default 8081) | [`dev/`](dev/) | Windows `start.bat` · Linux/macOS `start.sh` |
| Docker (PostgreSQL) | [`docker/`](docker/) | Seeded and non-seeded compose files |

Legacy root `deploy/install.sh` / `deploy/pack.ps1` were offline-pack leftovers (expected `images/*.tar` and a removed `fangmanle-demo` SourceRoot). They **cannot** start this repo from source. Offline packaging still goes through [`tools/build_tool.py`](../tools/build_tool.py) (looks for `deploy/offline/pack.ps1`; not shipped in this open-source tree).

## 1. Local development

Port is `FML_PORT` inside the script (default **8081**). Do not put the port in the filename. Override by editing the script or setting `FML_PORT` before start.

**Pick commercial on/off by script, not by remembering env vars:**

| Script | Commercial AI (`src/commercial/`) |
|--------|-----------------------------------|
| `start.bat` / `start.sh` | **On** (default `FML_COMMERCIAL=1`) |
| `start-opencore.bat` / `start-opencore.sh` | **Off** (forced `FML_COMMERCIAL=0`) |

```bat
REM Full product (AI Ask / LLM settings / shift AI draft, etc.)
deploy\dev\start.bat demo-sg

REM OpenCore only (no Ask / no LLM settings in the sidebar)
deploy\dev\start-opencore.bat demo-sg
```

```bash
bash deploy/dev/start.sh demo-sg
bash deploy/dev/start-opencore.sh demo-sg
```

The start banner prints `Commercial: 1` or `0`. Login `admin` / `admin123`.

## 2. Docker

Run from the **repo root**. Defaults live in the compose file (no `.env` required):

```bash
# With 03_demo sample data
docker compose -f deploy/docker/docker-compose.seed.yml up -d --build

# DDL + initial admin only (empty store / production)
docker compose -f deploy/docker/docker-compose.prod.yml up -d --build
```

**Change hotel / passwords / ports / map keys:** edit the compose file (`pms.environment.FML_HOTEL`, `POSTGRES_PASSWORD`, `FML_JWT_SECRET`, `FML_ADMIN_PASSWORD`, ports).  
Do not use a root `.env` for hotel selection.

Image build: `docker build -f deploy/docker/Dockerfile -t fangmanle-pms:1.0.1 .`  
App port default **8000**. For local OpenCore-only, use `start-opencore.*`.
