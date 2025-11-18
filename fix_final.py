#!/usr/bin/env python3
"""Script DEFINITIVO para corrigir bcrypt no pod RunPod."""

import paramiko
import time
import re
from pathlib import Path

POD_HOST = "ssh.runpod.io"
POD_USER = "qh3hpqrnck8ila-644113f7"
SSH_KEY_PATH = Path(r"C:\Users\Marcos\.ssh\id_ed25519_runpod")

def exec_command(ssh, cmd):
    """Executa comando e retorna apenas stdout limpo."""
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    output = stdout.read().decode('utf-8', errors='ignore')
    # Remover códigos ANSI e linhas de prompt
    ansi = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean = ansi.sub('', output)
    # Remover linhas com apenas prompt
    lines = [l for l in clean.split('\n') if l.strip() and not l.strip().startswith('root@')]
    return '\n'.join(lines)

print("=" * 80)
print("CORREÇÃO DEFINITIVA DO BCRYPT NO POD")
print("=" * 80)

# Conectar
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
private_key = paramiko.Ed25519Key.from_private_key_file(str(SSH_KEY_PATH))
ssh.connect(hostname=POD_HOST, username=POD_USER, pkey=private_key, timeout=30)
print("✓ Conectado\n")

try:
    # 1. Verificar versão bcrypt atual
    print("[1/6] Versão bcrypt atual:")
    out = exec_command(ssh, "cd /root/clipai/backend && source .venv/bin/activate && pip show bcrypt | grep Version")
    print(out or "  (não instalado)")
    
    # 2. Desinstalar bcrypt
    print("\n[2/6] Desinstalando bcrypt...")
    exec_command(ssh, "cd /root/clipai/backend && source .venv/bin/activate && pip uninstall -y bcrypt")
    print("  ✓ Desinstalado")
    
    # 3. Reinstalar bcrypt
    print("\n[3/6] Reinstalando bcrypt...")
    out = exec_command(ssh, "cd /root/clipai/backend && source .venv/bin/activate && pip install --no-cache-dir bcrypt 2>&1 | tail -5")
    print("  " + '\n  '.join(out.split('\n')[-3:]))
    
    # 4. Testar bcrypt
    print("\n[4/6] Testando bcrypt...")
    test_code = """
import bcrypt
pw = b'test12345678'
hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
ok = bcrypt.checkpw(pw, hashed)
print(f'Test: {'OK' if ok else 'FAIL'}')
print(f'Version: {bcrypt.__version__}')
"""
    out = exec_command(ssh, f"cd /root/clipai/backend && source .venv/bin/activate && python -c \"{test_code}\"")
    print("  " + out)
    
    # 5. Reiniciar uvicorn
    print("\n[5/6] Reiniciando uvicorn...")
    exec_command(ssh, "pkill -f uvicorn")
    time.sleep(1)
    exec_command(ssh, "cd /root/clipai/backend && source .venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /root/clipai/uvicorn.log 2>&1 &")
    print("  ✓ Uvicorn reiniciado")
    
    # 6. Verificar log
    print("\n[6/6] Verificando log (aguardando 4s)...")
    time.sleep(4)
    out = exec_command(ssh, "tail -15 /root/clipai/uvicorn.log")
    print("Últimas 15 linhas do log:")
    print("-" * 80)
    print(out)
    print("-" * 80)
    
finally:
    ssh.close()
    print("\n✓ Concluído!")
