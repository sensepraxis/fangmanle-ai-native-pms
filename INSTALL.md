# Install and deploy

Official start paths for this **self-hosted** hotel PMS are **only** `deploy/dev/` (SQLite) and `deploy/docker/` (PostgreSQL).  
Chinese offline-pack handbook: [docs/DEPLOY_zh.md](docs/DEPLOY_zh.md) (optional extra tooling, not the default).  
Operator notes: [deploy/README.md](deploy/README.md).

**Live demo (no install):** [https://pms.sensepraxis.com/](https://pms.sensepraxis.com/) — login `admin` / `admin123` (public seed data; reset periodically).

---

## 1. Docker one-command (PostgreSQL)

From the **repository root**. Compose files contain demo defaults; **no root `.env` is required**.

```bash
# Sample data (db/postgres/03_demo)
docker compose -f deploy/docker/docker-compose.seed.yml up -d --build

# Empty store: DDL + admin only
docker compose -f deploy/docker/docker-compose.prod.yml up -d --build
```

- App: http://127.0.0.1:8000/ — `admin` / `admin123`
- OpenAPI UI: http://127.0.0.1:8000/docs
- Postgres published at `127.0.0.1:5432` (see compose)

Change hotel, passwords, JWT, ports, and map keys **in the compose file** (`FML_HOTEL`, `POSTGRES_PASSWORD`, `FML_JWT_SECRET`, `FML_ADMIN_PASSWORD`).

Image:

```bash
docker build -f deploy/docker/Dockerfile -t fangmanle-pms:1.0.0 .
```

### What is in Compose

| Service | Role |
|---------|------|
| `db` | PostgreSQL 16 |
| `pms` | App image (Vue build + FastAPI) |

**Redis is not a runtime dependency** and is not started. Optional LLM / map vendors are **external** (`base_url` / API keys in system settings or env), not sidecar containers.

---

## 2. Source / local (SQLite)

Prereqs: Python 3.11+, Node 20+.

```bat
pip install -r requirements-prod.txt
deploy\dev\start.bat demo-sg
```

```bash
pip install -r requirements-prod.txt
bash deploy/dev/start.sh demo-sg
```

http://127.0.0.1:8081/ — `admin` / `admin123`. OpenCore-only: `start-opencore.*`.

Unset `DATABASE_URL` → SQLite file `data/fml_demo.db`. Driver prefixes for PostgreSQL: `postgresql+psycopg://` (psycopg3) vs `postgresql+psycopg2://`.

Hot reload after the first successful start: [docs/DEV.md](docs/DEV.md).

---

## 3. Production

1. Use `deploy/docker/docker-compose.prod.yml` (or an equivalent PG + app pair).
2. Replace demo JWT and passwords. Restrict `5432` if you do not need host access.
3. Set `FML_HOTEL` to your `config/hotels/<id>.yaml`.
4. Point `DATABASE_URL` at PostgreSQL. SQLite is a schema subset; some PG-only APIs fail or degrade on SQLite.
5. Configure LLM in **System → LLM** when commercial is on, or run OpenCore with `FML_COMMERCIAL=0`.
6. Do not treat `python src/run_prod.py` as the product entry; Compose/`run_prod` inside the image is the supported path.

Offline tarball install (Windows pack tool + `install.sh`) is optional and documented in [docs/DEPLOY_zh.md](docs/DEPLOY_zh.md).
