#!/bin/sh
# entrypoint.sh — runs on every container start (Render redeploys included).
# Applies any pending Alembic migrations, then starts the API server.
# If migrations fail, the container exits non-zero and Render will show
# the failure in the deploy logs instead of silently serving a stale schema.

set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
