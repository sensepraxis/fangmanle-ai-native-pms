# Fangmanle PMS

**Self-hosted**, **AI-native** hotel property management system. One process per hotel — not multi-tenant SaaS.

| | |
|--|--|
| **Live demo** | [pms.sensepraxis.com](https://pms.sensepraxis.com/) — `admin` / `admin123` |
| **OpenCore** | Apache-2.0 (`src/` except `commercial/`) |
| **Commercial AI** | BUSL-1.1 (`src/commercial/`) — optional; turn off with `FML_COMMERCIAL=0` |
| **Source** | [github.com/sensepraxis/fangmanle-ai-native-pms](https://github.com/sensepraxis/fangmanle-ai-native-pms) |

## Try it first

Open **[https://pms.sensepraxis.com/](https://pms.sensepraxis.com/)** for a hosted seed hotel (rooms, guests, orders). Demo credentials: **`admin` / `admin123`**. Public instance only — rotate secrets before production.

## Start here

1. [Quick Start](quick-start.md) — live demo link, local SQLite, or Docker / PostgreSQL
2. [Architecture](architecture.md) — process model, modules, HTTP layering
3. [FAQ](faq.md) — OpenCore vs commercial, Redis, trademarks, common failures

Canonical Markdown in the git tree: `INSTALL.md`, `ARCHITECTURE.md`, `FAQ.md`. This site is rebuilt from those files on every push to `main`.
