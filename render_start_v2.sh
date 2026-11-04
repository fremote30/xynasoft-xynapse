#!/usr/bin/env sh
set -eu

exec uvicorn render_preview:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}"
