#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Mounted by the official postgres image as /docker-entrypoint-initdb.d/01_apply.sh
# Runs in order: 01_ddl -> 02_init -> 03_demo (optional skip)
#
# Env:
#   FML_DB_ROOT                Script root (default /db)
#   FML_DB_SKIP_DEMO           1/true/yes skips 03_demo (recommended for production)
#   FML_ADMIN_USERNAME         Admin username (default admin)
#   FML_ADMIN_PASSWORD         Admin password (default admin123)
#                              Hash: SHA-256 (same as infra/auth_local.py hash_password)
#                              After SQL apply, UPDATE users resets this account password.

set -euo pipefail

ROOT="${FML_DB_ROOT:-/db}"
SKIP_DEMO="$(echo "${FML_DB_SKIP_DEMO:-}" | tr '[:upper:]' '[:lower:]')"
ADMIN_USER="${FML_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${FML_ADMIN_PASSWORD:-admin123}"

# SHA-256 of admin password (matches infra/auth_local.py)
sha256_of() {
  python3 -c "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode('utf-8')).hexdigest())" "$1"
}
ADMIN_HASH="$(sha256_of "$ADMIN_PASS")"

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
    found=1
    echo "[fangmanle-db] applying $(basename "$f") ..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
  done
  if [[ "$found" -eq 0 ]]; then
    echo "[fangmanle-db] no *.sql in $dir"
  fi
}

echo "[fangmanle-db] root=$ROOT skip_demo=$SKIP_DEMO admin_user=$ADMIN_USER"

# --- 1) Apply 01_ddl / 02_init / 03_demo ---
run_dir "$ROOT/01_ddl"
run_dir "$ROOT/02_init"

if [[ "$SKIP_DEMO" == "1" || "$SKIP_DEMO" == "true" || "$SKIP_DEMO" == "yes" ]]; then
  echo "[fangmanle-db] FML_DB_SKIP_DEMO set — skip 03_demo"
else
  run_dir "$ROOT/03_demo"
fi

# --- 2) Reset admin password (after demo so seed data cannot overwrite it) ---
# Single-quoted heredoc avoids bash expanding $$; admin vars are passed via -v.
DELETE_OLD_ADMIN='false'
if [[ "$ADMIN_USER" != "admin" ]]; then
  DELETE_OLD_ADMIN='true'
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v admin_user="$ADMIN_USER" -v admin_hash="$ADMIN_HASH" -v delete_old="$DELETE_OLD_ADMIN" <<'SQL'
-- Ensure admin user exists
INSERT INTO public.users (hotel_id, role_id, username, password_hash, full_name, is_active)
SELECT 1,
       (SELECT id FROM public.roles WHERE code = 'admin' LIMIT 1),
       :'admin_user',
       :'admin_hash',
       'System Administrator',
       TRUE
ON CONFLICT (username) DO NOTHING;
-- Update password hash (override 005_init_hotel_admin.sql / demo hashes)
UPDATE public.users
   SET password_hash = :'admin_hash'
 WHERE username = :'admin_user';
-- If FML_ADMIN_USERNAME differs from default, drop legacy admin placeholder
DO $_$
BEGIN
  IF :'delete_old' = 'true' THEN
    DELETE FROM public.users
     WHERE username = 'admin'
       AND NOT EXISTS (SELECT 1 FROM public.users WHERE username = :'admin_user');
  END IF;
END$_$;
SQL

echo "[fangmanle-db] admin ready: $ADMIN_USER (password length=${#ADMIN_PASS})"
echo "[fangmanle-db] done"
