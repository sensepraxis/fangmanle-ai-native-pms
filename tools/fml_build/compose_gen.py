# SPDX-License-Identifier: Apache-2.0
"""按模式生成 docker-compose.yml（步骤 6）。

两种模式的唯一差异：
- FML_DB_SKIP_DEMO：hotel=1（跳过样例数据），demo=0（加载样例数据）
- 容器名 / 数据库卷名 区分，避免同机误冲突
数据库表一律用 volume 挂载（./db:/db:ro），初始化脚本挂到 initdb.d。
其它（镜像、环境变量、端口）保持一致。
"""

from __future__ import annotations

# 模板中的占位符由 format 替换；为安全起见用命名占位 + .format_map
_COMPOSE_TPL = """\
# 房满乐 PMS · {edition_cn}（数据库 + 初始化数据{extra_cn}）
# 由 fangmanle-docker-build-tool 生成（模式: {mode}）
#
# 启动：docker load … && docker compose up -d
# 访问：http://服务器IP:{app_port}

services:
  db:
    image: ${{POSTGRES_IMAGE:-{postgres_image}}}
    container_name: {db_container}
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${{POSTGRES_USER:-fangmanle}}
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD:-change-me}}
      POSTGRES_DB: ${{POSTGRES_DB:-fangmanle}}
      # Offline pack flattens SQL under ./db; repo compose uses /db/postgres.
      FML_DB_ROOT: /db
      # {mode} 版{skip_note}
      FML_DB_SKIP_DEMO: "{skip_demo}"
      TZ: Asia/Shanghai
    volumes:
      - {pg_volume}:/var/lib/postgresql/data
      - ./db:/db:ro
      - ./db/docker-init.sh:/docker-entrypoint-initdb.d/01_apply.sh:ro
    ports:
      - "${{POSTGRES_PORT:-127.0.0.1:5432}}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 20

  pms:
    image: ${{PMS_IMAGE:-{image_ref}}}
    container_name: {pms_container}
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg://${{POSTGRES_USER:-fangmanle}}:${{POSTGRES_PASSWORD:-change-me}}@db:5432/${{POSTGRES_DB:-fangmanle}}
      FML_DEPLOY: container
      FML_JWT_SECRET: ${{FML_JWT_SECRET:-please-change-this-jwt-secret}}
      FML_HOST: 0.0.0.0
      FML_PORT: 8000
      TZ: Asia/Shanghai
    ports:
      - "${{PMS_PORT:-{app_port}}}:8000"

volumes:
  {pg_volume}:
"""


def generate_compose(
    *,
    mode: str,
    image_name: str,
    image_tag: str,
    postgres_image: str,
    app_port: int = 8000,
) -> str:
    mode = mode.lower()
    if mode == "hotel":
        skip_demo = "1"
        skip_note = "强制跳过演示样例数据"
        edition_cn = "酒店生产版"
        extra_cn = "，无样例业务数据"
        db_container = "fangmanle-hotel-db"
        pms_container = "fangmanle-hotel-pms"
        pg_volume = "pgdata_hotel"
    else:
        skip_demo = "0"
        skip_note = "强制加载 03_demo 样例数据"
        edition_cn = "演示版"
        extra_cn = "，含丰满样例数据"
        db_container = "fangmanle-demo-db"
        pms_container = "fangmanle-demo-pms"
        pg_volume = "pgdata_demo"

    return _COMPOSE_TPL.format_map(
        {
            "mode": mode,
            "image_ref": f"{image_name}:{image_tag}",
            "postgres_image": postgres_image,
            "app_port": app_port,
            "skip_demo": skip_demo,
            "skip_note": skip_note,
            "edition_cn": edition_cn,
            "extra_cn": extra_cn,
            "db_container": db_container,
            "pms_container": pms_container,
            "pg_volume": pg_volume,
        }
    )
