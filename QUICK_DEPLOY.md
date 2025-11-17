# 🚀 Quick Deploy - Correção CORS

## Deploy no RunPod (1 comando)

```bash
ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io 'bash -s' < RUNPOD_DEPLOY_CORS_FIX.sh
```

**OU** manual:

```bash
# 1. Conectar SSH
ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io

# 2. Deploy
cd ~/clipai
git pull
pkill -f uvicorn; pkill -f celery
cd backend && source .venv/bin/activate && cd ..
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug --app-dir backend > uvicorn.log 2>&1 &
nohup celery -A app.tasks.celery_tasks worker --loglevel=info --workdir=backend > celery.log 2>&1 &

# 3. Verificar
sleep 3
curl http://localhost:8000/health
tail -20 uvicorn.log
```

## Deploy Frontend (Vercel)

```bash
cd frontend
git add .
git commit -m "feat: aggressive CORS bypass with retry logic"
git push
# Vercel faz deploy automático em ~2min
```

## Teste Rápido

### No Browser
1. Abrir: `file:///c:/dev/clipai/cors-test-tool.html`
2. Clicar em "🚀 Executar Todos os Testes"
3. Verificar logs

### Via cURL
```bash
# Health básico
curl -X GET https://qh3hpqrnck8ila-8000.proxy.runpod.net/health

# CORS test
curl -X GET https://qh3hpqrnck8ila-8000.proxy.runpod.net/health/cors \
  -H "Origin: https://frontend-xi-hazel-22.vercel.app" \
  -v

# Preflight
curl -X OPTIONS https://qh3hpqrnck8ila-8000.proxy.runpod.net/api/auth/register \
  -H "Origin: https://frontend-xi-hazel-22.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

### No Frontend Real
1. Ir para: https://frontend-xi-hazel-22.vercel.app/auth
2. Criar conta com email teste
3. Abrir DevTools (F12) → Console
4. Verificar logs (emojis 🔵 ✅ ❌)

## Monitorar Logs

```bash
ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io

# Logs em tempo real
cd ~/clipai
tail -f uvicorn.log

# Filtrar CORS/Auth
tail -f uvicorn.log | grep -E "(🔵|✅|❌|⚠️|CORS|REGISTER|LOGIN)"
```

## Esperado ✅

- Sem erros CORS no console do browser
- POST `/auth/register` retorna 201
- Headers `access-control-allow-origin` presentes
- Logs mostram `✅ User registered successfully`

## Se Falhar ❌

1. **Verificar logs**: `tail -50 ~/clipai/uvicorn.log`
2. **Testar direto**: `curl http://localhost:8000/health`
3. **Verificar processos**: `ps aux | grep -E "(uvicorn|celery)"`
4. **Reiniciar**: Executar script de deploy novamente

## Rollback

```bash
ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io
cd ~/clipai
git stash pop  # Recuperar código anterior (se fez stash)
# OU
git reset --hard origin/main~1  # Voltar 1 commit
# Depois reiniciar serviços
```

---

**Tempo estimado**: 5-10 minutos  
**Risco**: Baixo (mudanças são não-destrutivas)
