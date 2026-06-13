#!/usr/bin/env sh
set -eu

redis-server --daemonize yes --bind 127.0.0.1 --port 6379

until redis-cli -h 127.0.0.1 -p 6379 ping | grep -q PONG; do
  sleep 0.2
done

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
