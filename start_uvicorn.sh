#!/bin/bash
# Script para iniciar uvicorn com limite de upload de 250MB

cd /root/clipai/backend
source .venv/bin/activate

# Matar processo antigo
pkill -f uvicorn

# Iniciar uvicorn com limite de 250MB
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --limit-max-requests 1000 \
  --timeout-keep-alive 300 \
  --limit-concurrency 100 \
  > /root/clipai/uvicorn.log 2>&1 &

echo "Uvicorn iniciado com PID $!"
sleep 2
tail -20 /root/clipai/uvicorn.log
