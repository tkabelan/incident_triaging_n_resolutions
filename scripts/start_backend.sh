#!/usr/bin/env bash

set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
WORKER_TIMEOUT="${WORKER_TIMEOUT:-300}"
GRACEFUL_TIMEOUT="${GRACEFUL_TIMEOUT:-30}"
KEEP_ALIVE="${KEEP_ALIVE:-5}"

exec gunicorn \
  --workers "${WEB_CONCURRENCY}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout "${WORKER_TIMEOUT}" \
  --graceful-timeout "${GRACEFUL_TIMEOUT}" \
  --keep-alive "${KEEP_ALIVE}" \
  --bind "${HOST}:${PORT}" \
  app.main:app
