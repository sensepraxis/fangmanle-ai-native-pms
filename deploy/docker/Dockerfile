# Fangmanle PMS · application image
# Build from repo root:
#   docker build -f deploy/docker/Dockerfile -t fangmanle-pms:1.0.1 .

# vite.config.ts aliases @locales -> ../locales (repo root). Keep that layout
# inside the image so `npm run build` can resolve locales/*.json.
FROM node:20-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend/ ./
COPY locales/ /build/locales/
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    FML_DEPLOY=container \
    FML_HOST=0.0.0.0 \
    FML_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt /app/requirements-prod.txt
RUN pip install --no-cache-dir -r /app/requirements-prod.txt

COPY src/ /app/src/
COPY config/ /app/config/
COPY locales/ /app/locales/
COPY --from=frontend /build/frontend/dist/ /app/frontend/dist/

ENV FML_HOTEL=demo-intl \
    FML_TZ=UTC

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/docs || exit 1

CMD ["python", "/app/src/run_prod.py", "--host", "0.0.0.0", "--port", "8000"]
