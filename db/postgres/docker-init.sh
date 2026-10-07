#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Mounted by the official postgres image as /docker-entrypoint-initdb.d/01_apply.sh
# Runs in order: 01_ddl -> 02_init -> 03_demo (optional skip)
#
# Env:
#   FML_DB_ROOT                SQL root containing 01_ddl / 02_init / 03_demo
#                              (default /db/postgres; also accepts /db with nested postgres/)
#   FML_DB_SKIP_DEMO           1/true/yes skips 03_demo (recommended for production)
#   FML_ADMIN_USERNAME         Admin username (default admin)
#   FML_ADMIN_PASSWORD         Admin password (default admin123)
#                              Hash: SHA-256 hex (legacy verify in infra/auth_local.py)
#                              After SQL apply, UPDATE users resets this account password.

set -euo pipefail

ROOT="${FML_DB_ROOT:-/db/postgres}"
# Compose historically mounted ../../db at /db while SQL lives under postgres/.
if [[ ! -d "$ROOT/01_ddl" && -d "$ROOT/postgres/01_ddl" ]]; then
  ROOT="$ROOT/postgres"
fi
if [[ ! -d "$ROOT/01_ddl" ]]; then
  echo "[fangmanle-db] ERROR: 01_ddl not found under FML_DB_ROOT=$ROOT" >&2
  echo "[fangmanle-db] HINT: set FML_DB_ROOT=/db/postgres when mounting repo db/ at /db" >&2
  exit 1
fi

SKIP_DEMO="$(echo "${FML_DB_SKIP_DEMO:-}" | tr '[:upper:]' '[:lower:]')"
ADMIN_USER="${FML_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${FML_ADMIN_PASSWORD:-admin123}"

# Known hash for the documented demo password (admin123).
ADMIN123_HASH='240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'

# SHA-256 of admin password (legacy hex; postgres:alpine has no python3)
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$1" | sha256sum | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    printf '%s' "$1" | openssl dgst -sha256 | awk '{print $NF}'
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode('utf-8')).hexdigest())" "$1"
  else
    return 1
  fi
}

if [[ "$ADMIN_PASS" == "admin123" ]]; then
  ADMIN_HASH="$ADMIN123_HASH"
else
  ADMIN_HASH="$(sha256_of "$ADMIN_PASS")" || {
    echo "[fangmanle-db] ERROR: need sha256sum, openssl, or python3 to hash FML_ADMIN_PASSWORD" >&2
    exit 1
  }
fi

# Prefer FOO.opensource.sql over FOO.sql when both exist (open-source + local PII dump).
should_apply_sql() {
  local f="$1"
  local base dir twin
  base="$(basename "$f")"
  dir="$(dirname "$f")"
  if [[ "$base" != *.opensource.sql ]]; then
    twin="${dir}/${base%.sql}.opensource.sql"
    if [[ -f "$twin" ]]; then
      echo "[fangmanle-db] skip $(basename "$f") (prefer $(basename "$twin"))"
      return 1
    fi
  fi
  return 0
}

run_dir() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "[fangmanle-db] skip missing: $dir"
    return 0
  fi
  local f
  local found=0
  for f in "$dir"/*.sql; do
    [[ -e "$f" ]] || continue
    should_apply_sql "$f" || continue
    found=1
    echo "[fangmanle-db] applying $(basename "$f") ..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
  done
  if [[ "$found" -eq 0 ]]; then
    echo "[fangmanle-db] no *.sql applied in $dir"
  fi
}

reset_admin() {
  # Note: psql :'vars' are NOT expanded inside dollar-quoted DO blocks.
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v admin_user="$ADMIN_USER" -v admin_hash="$ADMIN_HASH" <<'SQL'
INSERT INTO public.users (hotel_id, role_id, username, password_hash, full_name, is_active)
SELECT 1,
       (SELECT id FROM public.roles WHERE code = 'admin' LIMIT 1),
       :'admin_user',
       :'admin_hash',
       'System Administrator',
       TRUE
ON CONFLICT (username) DO NOTHING;
UPDATE public.users
   SET password_hash = :'admin_hash',
       is_active = TRUE
 WHERE username = :'admin_user';
SQL
  if [[ "$ADMIN_USER" != "admin" ]]; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      -v admin_user="$ADMIN_USER" <<'SQL'
DELETE FROM public.users
 WHERE username = 'admin'
   AND EXISTS (SELECT 1 FROM public.users WHERE username = :'admin_user');
SQL
  fi
  echo "[fangmanle-db] admin ready: $ADMIN_USER (password length=${#ADMIN_PASS})"
}

echo "[fangmanle-db] root=$ROOT skip_demo=$SKIP_DEMO admin_user=$ADMIN_USER"

run_dir "$ROOT/01_ddl"
run_dir "$ROOT/02_init"

if [[ "$SKIP_DEMO" == "1" || "$SKIP_DEMO" == "true" || "$SKIP_DEMO" == "yes" ]]; then
  echo "[fangmanle-db] FML_DB_SKIP_DEMO set — skip 03_demo"
else
  # Demo may fail (duplicate dumps); still ensure admin afterwards.
  set +e
  run_dir "$ROOT/03_demo"
  demo_rc=$?
  set -e
  if [[ "$demo_rc" -ne 0 ]]; then
    echo "[fangmanle-db] WARN: 03_demo failed (rc=$demo_rc); continuing to reset admin" >&2
  fi
fi

reset_admin
echo "[fangmanle-db] done"
