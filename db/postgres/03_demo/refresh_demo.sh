#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# ============================================================================
# 房满乐 PMS · 重新生成 Demo 的 DDL 与样例数据（零 SQLite 依赖）
#
# 原理：本地 PostgreSQL 容器里已有单租户 demo 数据（fml_seed），
#       再 pg_dump 成仓库内 SQL；与应用运行时 ensure_single_hotel_schema 完全一致。
#
# 前置：
#   1) Docker Desktop 已启动；存在 fml-pg 容器（postgres:16-alpine，
#      账号 fml:fmlpass，监听 localhost:5432，fml 为 superuser）。
#   2) fml_seed 库已创建（若无：docker exec fml-pg psql -U fml -c 'CREATE DATABASE fml_seed;'）。
#   3) fml_seed 中已有演示数据（可用 deploy/docker/docker-compose.seed.yml 灌库后 dump，
#      或手工对 fml_seed 灌 03_demo）。本脚本只负责 dump，不启动服务。
#
# 用法：
#   cd <fangmanle-demo 仓库根>
#   FML_PG_CONTAINER=fml-pg FML_SEED_DB=fml_seed bash db/postgres/03_demo/refresh_demo.sh
#
# 产出：
#   db/postgres/01_ddl/001_core_schema.sql     (--schema-only)
#   db/postgres/03_demo/010_full_demo_data.sql (--data-only --column-inserts)
# ============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

PG_CONTAINER="${FML_PG_CONTAINER:-fml-pg}"
PG_DB="${FML_SEED_DB:-fml_seed}"
PG_USER="${FML_PG_USER:-fml}"

DDL_OUT="$REPO_ROOT/db/postgres/01_ddl/001_core_schema.sql"
DATA_OUT="$REPO_ROOT/db/postgres/03_demo/010_full_demo_data.sql"

echo "[refresh_demo] 容器=$PG_CONTAINER 库=$PG_DB 用户=$PG_USER"

if ! docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
  echo "[refresh_demo] 错误：未找到运行中的容器 $PG_CONTAINER" >&2
  exit 1
fi
if ! docker exec "$PG_CONTAINER" psql -U "$PG_USER" -tAc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" | grep -qx 1; then
  echo "[refresh_demo] 错误：库 $PG_DB 不存在，请先 CREATE DATABASE 并灌入 demo 数据" >&2
  exit 1
fi

# 1) Schema-only dump -> 01_ddl/001_core_schema.sql
{
  cat <<'SQL'
-- ============================================================================
-- 房满乐 PMS · 生产数据库 Schema (PostgreSQL 16, 单租户)
--
-- 本文件由本地 fml_seed 容器 (postgres:16) 经 pg_dump --schema-only 生成，
-- 与运行时 ensure_single_hotel_schema 产出的单租户 schema 完全一致（零 SQLite 依赖）。
-- 生成命令: docker exec fml-pg pg_dump -U fml -d fml_seed --schema-only --no-owner --no-privileges
-- 重新生成: 修改 demo 数据后运行 db/postgres/03_demo/refresh_demo.sh
-- ============================================================================

SQL
  docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" --schema-only --no-owner --no-privileges
} > "$DDL_OUT"

# 2) Data-only column-inserts dump -> 03_demo/010_full_demo_data.sql
{
  cat <<'SQL'
-- ======================================================================
-- 房满乐 PMS · Demo 样例数据（PostgreSQL 原生 column-inserts dump，零 SQLite 依赖）
-- 生成: docker exec fml-pg pg_dump -U fml -d fml_seed --data-only --column-inserts --no-owner --no-privileges --disable-triggers
-- 源库: 本地 fml_seed 容器 (postgresql:16)；schema 由 db/postgres/01_ddl 创建（单租户，与应用运行时一致）
-- 重导: db/postgres/03_demo/refresh_demo.sh 可基于 fml_seed 重新生成
-- 注意: 密钥字段已脱敏 (api_key/app_secret/token 等为空串)
-- ======================================================================

SQL
  docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
    --data-only --column-inserts --no-owner --no-privileges --disable-triggers
} > "$DATA_OUT"

echo "[refresh_demo] 完成："
echo "  $DDL_OUT"
echo "  $DATA_OUT"
echo "[refresh_demo] 请 git diff 复核变更后提交（注意 002-004/006 为 stub，请勿覆盖）。"
