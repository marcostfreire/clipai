#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

log() { printf '[%s] %s\n' "$(date +'%H:%M:%S')" "$*"; }

log "Installing system dependencies"
apt-get update -qq
apt-get install -y -qq git python3.12 python3.12-venv python3-pip ffmpeg curl wget unzip build-essential > /dev/null

cd /root
log "Refreshing repo"
rm -rf clipai clipai.zip clipai-main
curl -fsSL -o clipai.zip https://github.com/marcostfreire/clipai/archive/refs/heads/main.zip
unzip -q clipai.zip
mv clipai-main clipai

cd clipai/backend
log "Creating virtualenv"
python3.12 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip wheel
pip install --quiet -r requirements.txt

log "Running migrations"
alembic upgrade head

log "Seeding env vars"
cp .env.example .env
sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://clipai-frontend.marcosfreire.vercel.app|" ../frontend/.env.local || true

log "Starting services"
pkill -f "celery" || true
pkill -f "uvicorn" || true
nohup celery -A app.tasks.celery_tasks worker --loglevel=INFO > /tmp/celery.log 2>&1 &
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &

log "Done. Tail /tmp/api.log or /tmp/celery.log for status."
