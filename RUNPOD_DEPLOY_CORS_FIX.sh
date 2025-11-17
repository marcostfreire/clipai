#!/bin/bash
# Script de deploy da correção CORS no RunPod
# Execute via SSH: ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io < RUNPOD_DEPLOY_CORS_FIX.sh

set -e

echo "🚀 Iniciando deploy da correção CORS..."
echo ""

# 1. Navegar para o diretório do projeto
cd ~/clipai || { echo "❌ Diretório ~/clipai não encontrado"; exit 1; }
echo "✅ Diretório: $(pwd)"

# 2. Fazer backup do estado atual
echo "📦 Fazendo backup..."
git stash save "backup-before-cors-fix-$(date +%Y%m%d-%H%M%S)" || true

# 3. Pull das mudanças
echo "⬇️  Baixando código atualizado..."
git pull origin main || { echo "❌ Erro ao fazer git pull"; exit 1; }
echo "✅ Código atualizado"

# 4. Parar serviços
echo "⏸️  Parando serviços..."
pkill -f uvicorn || echo "⚠️  Uvicorn não estava rodando"
pkill -f celery || echo "⚠️  Celery não estava rodando"
sleep 2
echo "✅ Serviços parados"

# 5. Verificar ambiente virtual e dependências
echo "🐍 Verificando Python environment..."
cd backend
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment não encontrado, criando..."
    python3 -m venv .venv
fi

source .venv/bin/activate || { echo "❌ Erro ao ativar venv"; exit 1; }
echo "✅ Virtual environment ativado"

# 6. Instalar/atualizar dependências (se necessário)
echo "📦 Verificando dependências..."
pip list | grep -E "(fastapi|starlette|uvicorn)" || { echo "❌ Dependências ausentes"; exit 1; }
echo "✅ Dependências OK"

# 7. Voltar para raiz
cd ..

# 8. Iniciar Uvicorn com logging verbose
echo "🚀 Iniciando Uvicorn (modo debug)..."
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level debug \
  --app-dir backend \
  > uvicorn.log 2>&1 &

UVICORN_PID=$!
echo "✅ Uvicorn iniciado (PID: $UVICORN_PID)"

# 9. Iniciar Celery Worker
echo "🚀 Iniciando Celery Worker..."
nohup celery -A app.tasks.celery_tasks worker \
  --loglevel=info \
  --workdir=backend \
  > celery.log 2>&1 &

CELERY_PID=$!
echo "✅ Celery iniciado (PID: $CELERY_PID)"

# 10. Aguardar serviços subirem
echo "⏳ Aguardando serviços inicializarem..."
sleep 5

# 11. Verificar health
echo "🏥 Verificando health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API está respondendo!"
else
    echo "❌ API não está respondendo"
    echo "Últimas 20 linhas do log:"
    tail -20 uvicorn.log
    exit 1
fi

# 12. Testar endpoint CORS
echo "🔍 Testando endpoint CORS..."
CORS_RESPONSE=$(curl -s -X GET http://localhost:8000/health/cors \
  -H "Origin: https://frontend-xi-hazel-22.vercel.app" \
  -w "\n%{http_code}")

CORS_CODE=$(echo "$CORS_RESPONSE" | tail -1)
if [ "$CORS_CODE" = "200" ]; then
    echo "✅ Endpoint CORS respondendo"
else
    echo "⚠️  Endpoint CORS retornou código: $CORS_CODE"
fi

# 13. Mostrar status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Status dos Serviços:"
echo "  • Uvicorn PID: $UVICORN_PID"
echo "  • Celery PID: $CELERY_PID"
echo "  • Health: http://localhost:8000/health"
echo "  • CORS Test: http://localhost:8000/health/cors"
echo ""
echo "📝 Logs:"
echo "  • Backend: tail -f ~/clipai/uvicorn.log"
echo "  • Celery: tail -f ~/clipai/celery.log"
echo "  • CORS/Auth: tail -f ~/clipai/uvicorn.log | grep -E '(🔵|✅|❌|⚠️)'"
echo ""
echo "🧪 Teste no browser:"
echo "  1. Abrir https://frontend-xi-hazel-22.vercel.app/auth"
echo "  2. Tentar criar conta"
echo "  3. Verificar console do browser (F12)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
