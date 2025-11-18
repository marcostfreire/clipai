#!/bin/bash
# Script para diagnosticar e corrigir bcrypt no pod RunPod

echo "========================================="
echo "DIAGNÓSTICO E CORREÇÃO DO BCRYPT"
echo "========================================="

cd /root/clipai/backend || exit 1

# Ativar ambiente virtual
source .venv/bin/activate

echo ""
echo "[1/7] Verificando versão do bcrypt instalado..."
pip show bcrypt | grep -E "(Name|Version|Location)"

echo ""
echo "[2/7] Verificando se bcrypt está usando extensão C..."
python -c "
import bcrypt
import sys
print('Version:', bcrypt.__version__)
print('File:', bcrypt.__file__)
try:
    import _bcrypt
    print('Has _bcrypt module: YES')
except ImportError:
    print('Has _bcrypt module: NO (usando fallback Python puro)')
"

echo ""
echo "[3/7] Verificando dependências de compilação..."
which gcc || echo "GCC não encontrado"
which make || echo "Make não encontrado"

echo ""
echo "[4/7] Reinstalando bcrypt com compilação nativa..."
pip uninstall -y bcrypt
pip install --no-cache-dir bcrypt

echo ""
echo "[5/7] Testando bcrypt após reinstalação..."
python -c "
import bcrypt
print('Version:', bcrypt.__version__)
pw = b'test123'
hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
result = bcrypt.checkpw(pw, hashed)
print('Hash test:', 'OK' if result else 'FAIL')
print('Hash gerado:', hashed[:20], '...')
"

echo ""
echo "[6/7] Matando processo uvicorn antigo..."
pkill -f uvicorn
sleep 2

echo ""
echo "[7/7] Iniciando uvicorn..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /root/clipai/uvicorn.log 2>&1 &

echo ""
echo "Aguardando 3 segundos..."
sleep 3

echo ""
echo "Últimas 20 linhas do log:"
tail -n 20 /root/clipai/uvicorn.log

echo ""
echo "========================================="
echo "DIAGNÓSTICO COMPLETO"
echo "========================================="
