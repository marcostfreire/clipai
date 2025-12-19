#!/bin/bash

echo "RAILWAY_SERVICE_NAME is: $RAILWAY_SERVICE_NAME"

# Decide what to run based on RAILWAY_SERVICE_NAME (case insensitive)
SERVICE_NAME_LOWER=$(echo "$RAILWAY_SERVICE_NAME" | tr '[:upper:]' '[:lower:]')

if [[ "$SERVICE_NAME_LOWER" == *"worker"* ]]; then
    echo "Starting Celery worker..."
    exec celery -A app.tasks.celery_tasks worker --loglevel=info --concurrency=1 --pool=solo --prefetch-multiplier=1
else
    echo "Starting API server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 50 --limit-max-requests 200
fi
