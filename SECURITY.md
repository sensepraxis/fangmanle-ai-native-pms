# Security policy

**Fangmanle PMS (open source)** handles hotel operations and guest PII. Report vulnerabilities privately.

[简体中文](SECURITY_zh.md)

---

## 1. Supported versions

| Version | Status |
|---------|--------|
| Latest `main` | Security fixes |
| Historical tags / other branches | Not maintained |

Fixes land on `main` first and ship with the next release.

---

## 2. Reporting a vulnerability (private)

**Do not** open a public issue for an unpatched vulnerability.

- Email: **contact@sensepraxis.com** (fallback: GitHub private security advisory / maintainer DM)
- Include: affected version and backend (SQLite / PostgreSQL), repro steps, impact, suggested fix if you have one

We acknowledge within **72 hours** and share a timeline after we confirm the issue. We stay in contact until a fix is published.

---

## 3. Sensitive data (developers)

- **PII** (ID numbers, phones): field-level encryption (`cryptography` / optional `gmssl`). Store hashes/ciphertext; do not log or return plaintext.
- **Secrets:** never commit real `.env` values. Inject via environment; CI uses a secret store.
- **JWT:** set `FML_JWT_SECRET` to a random value in production. Compose/code demo default is `please-change-this-jwt-secret`; keeping it lets anyone forge sessions.
- **Passwords:** new hashes are salted PBKDF2-SHA256; legacy bare SHA-256 hex upgrades on successful login. Demo `admin` / `admin123` stays for local try-out.
- **Database:** unset `DATABASE_URL` uses repo SQLite `data/fml_demo.db`. Production must use PostgreSQL, a strong password, and a tight network path.

---

## 4. Compliance (production)

OpenCore does **not** ship China crypto-evaluation (密评) or MLPS (等保) work products. Those are a separate commercial engagement.

---

## 5. Dependencies

Pin via `requirements-prod.txt` / `pyproject.toml`. Run `pip-audit` (or similar) on a schedule and upgrade promptly.
