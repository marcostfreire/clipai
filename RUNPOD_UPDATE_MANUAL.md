# Manual RunPod Update Commands
# Open SSH connection first: ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io
# Then run these commands one by one:

# 1. Pull latest code
cd ~/clipai
git pull

# 2. Update backend .env with new price IDs
cd ~/clipai/backend
sed -i '/STRIPE_PRICE_FREE/d' .env
echo 'STRIPE_PRICE_FREE=price_1SUSZdCMwpJ5YuyfbFDEQh5A' >> .env
sed -i 's/STRIPE_PRICE_STARTER=.*/STRIPE_PRICE_STARTER=price_1SUSowCMwpJ5YuyfvZq5iXYZ/' .env
sed -i 's/STRIPE_PRICE_PRO=.*/STRIPE_PRICE_PRO=price_1SUSowCMwpJ5YuyfiRMdGv15/' .env

# 3. Verify .env changes
grep STRIPE_PRICE .env

# 4. Activate venv and ensure stripe is installed
source .venv/bin/activate
pip list | grep stripe

# 5. Stop running services
pkill -f uvicorn
pkill -f celery

# 6. Wait a moment
sleep 2

# 7. Start uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../uvicorn.log 2>&1 &

# 8. Start celery worker
nohup celery -A app.tasks.celery_tasks worker --loglevel=info > ../celery.log 2>&1 &

# 9. Verify health
sleep 3
curl http://localhost:8000/health

# 10. Check logs if needed
tail -20 ../uvicorn.log
