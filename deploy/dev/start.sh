#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Dev start (SQLite full demo). Default: commercial AI on (FML_COMMERCIAL=1).
# OpenCore only: use start-opencore.sh in this folder (forces FML_COMMERCIAL=0).
# Port: FML_PORT in this script (default 8081). Override via env. Do not put port in the filename.
#
#   bash deploy/dev/start.sh
#   bash deploy/dev/start.sh demo-sg
#   bash deploy/dev/start.sh /path/to/hotel.yaml
set -euo pipefail

FML_PORT="${FML_PORT:-8081}"
# Product default: commercial on. OpenCore entry exports FML_COMMERCIAL=0 before exec.
export FML_COMMERCIAL="${FML_COMMERCIAL:-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$REPO_DIR/src"
FE_DIR="$REPO_DIR/frontend"

if [[ -n "${FML_PYTHON:-}" ]]; then
  PYTHON="$FML_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

export FML_REPO_DIR="$REPO_DIR"
export PYTHONPATH="$SRC_DIR"
export FML_PORT

if [[ -n "${1:-}" ]]; then
  export FML_HOTEL_FILE="$1"
fi
export FML_HOTEL_FILE="${FML_HOTEL_FILE:-demo-cn}"
export FML_DEPLOY_FILE="$FML_HOTEL_FILE"

eval "$("$PYTHON" "$REPO_DIR/deploy/dev/print_deploy_env.py" --sh)"

if [[ -z "${FML_HOTEL:-}" && -n "${FML_PACKS:-}" ]]; then
  export FML_HOTEL="$FML_PACKS"
fi
export FML_HOTEL="${FML_HOTEL:-demo-cn}"
export FML_PACKS="${FML_PACKS:-$FML_HOTEL}"
export SEED_LOCALE="${SEED_LOCALE:-en}"
export FML_DEFAULT_LOCALE="${FML_DEFAULT_LOCALE:-$SEED_LOCALE}"

if [[ -z "${DB_PATH:-}" ]]; then
  DB_PATH="${TMPDIR:-/tmp}/fml_demo_${FML_PORT}_${FML_HOTEL}.db"
fi
export DB_PATH
export DATABASE_URL="sqlite:///${DB_PATH}"

echo "============================================"
echo "Fangmanle PMS"
echo "Port:       $FML_PORT"
echo "Hotel:      $FML_HOTEL"
echo "Hotel config loaded from: ${FML_HOTEL_YAML:-$FML_HOTEL_FILE}"
echo "Locale:     $SEED_LOCALE"
echo "Commercial: $FML_COMMERCIAL  [1=on / 0=OpenCore only]"
echo "DB:         $DB_PATH"
echo "============================================"
echo

if [[ "${SKIP_FE_BUILD:-}" == "1" ]]; then
  echo "[skip] Frontend build skipped (SKIP_FE_BUILD=1)"
else
  echo "[1/3] Sync locales -> frontend/src/locales ..."
  if [[ -f "$REPO_DIR/locales/en.json" ]]; then
    cp -f "$REPO_DIR/locales/en.json" "$FE_DIR/src/locales/en.json"
  fi
  if [[ -f "$REPO_DIR/locales/zh-CN.json" ]]; then
    cp -f "$REPO_DIR/locales/zh-CN.json" "$FE_DIR/src/locales/zh-CN.json"
  fi
  echo "[2/3] Building frontend ..."
  cd "$FE_DIR"
  npm run build
fi

echo "[3/3] Bootstrap demo + uvicorn 127.0.0.1:${FML_PORT} ..."
"$PYTHON" "$REPO_DIR/deploy/dev/bootstrap_demo.py"

echo
echo "Open http://127.0.0.1:${FML_PORT}/  (Ctrl+C to stop)"
echo

cd "$SRC_DIR"
exec "$PYTHON" -m uvicorn api:app --host 127.0.0.1 --port "$FML_PORT" --log-level info
