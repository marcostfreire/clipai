#!/bin/bash

echo "RAILWAY_SERVICE_NAME is: $RAILWAY_SERVICE_NAME"

# Decide what to run based on RAILWAY_SERVICE_NAME (case insensitive)
SERVICE_NAME_LOWER=$(echo "$RAILWAY_SERVICE_NAME" | tr '[:upper:]' '[:lower:]')

if [[ "$SERVICE_NAME_LOWER" == *"worker"* ]] || [[ "$SERVICE_NAME_LOWER" == "clipai" ]]; then
    echo "Starting Celery worker with healthcheck server..."
    exec python worker_main.py
else
    echo "Running database migrations..."
    alembic upgrade head
    echo "Starting API server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 100
fi
