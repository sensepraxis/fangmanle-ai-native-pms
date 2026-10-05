# HTTP API

The backend is **FastAPI**. The spec is **generated at runtime**, not maintained by hand.

| URL | What |
|-----|------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI 3 document |

After [INSTALL.md](INSTALL.md):

- Local SQLite demo: `http://127.0.0.1:8081/docs`
- Docker: `http://127.0.0.1:8000/docs`

Title comes from `infra.branding.product_title()`. Routers live under `src/routers/` and are mounted from `src/api.py`.

Export a snapshot (needs `PYTHONPATH=src` and a harmless `DATABASE_URL`):

```bash
python tools/export_openapi.py
```

Writes `docs/openapi.json` (gitignored if large/local; CI may upload it as an artifact). There is no separate Sphinx or TypeDoc site for the Python/Vue trees; TypeScript is checked with `vue-tsc` in CI.
