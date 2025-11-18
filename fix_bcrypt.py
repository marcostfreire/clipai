#!/usr/bin/env python3
"""Script para diagnosticar e corrigir bcrypt no pod RunPod via SSH com Paramiko."""

import paramiko
import sys
import time
from pathlib import Path

POD_HOST = "ssh.runpod.io"
POD_USER = "qh3hpqrnck8ila-644113f7"
SSH_KEY_PATH = Path(r"C:\Users\Marcos\.ssh\id_ed25519_runpod")


def run_ssh_command(ssh_client, command, timeout=60):
    """Executa comando SSH e retorna stdout, stderr e código de retorno."""
    try:
        transport = ssh_client.get_transport()
        channel = transport.open_session()
        channel.settimeout(timeout)

        # SOLICITAR PTY - OBRIGATÓRIO PARA RUNPOD!
        channel.get_pty()

        channel.exec_command(command)

        # Ler saída completa
        stdout_data = channel.makefile("r").read()
        stderr_data = channel.makefile_stderr("r").read()
        exit_code = channel.recv_exit_status()
        channel.close()

        # Limpar caracteres de controle ANSI/PTY
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        stdout_clean = ansi_escape.sub("", stdout_data)

        return stdout_clean, stderr_data, exit_code
    except Exception as e:
        return "", str(e), 1


def connect_ssh():
    """Conecta ao pod via SSH usando paramiko."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        private_key = paramiko.Ed25519Key.from_private_key_file(str(SSH_KEY_PATH))
        ssh.connect(
            hostname=POD_HOST,
            username=POD_USER,
            pkey=private_key,
            timeout=30,
            banner_timeout=30,
        )
        print("✓ Conectado ao pod com sucesso\n")
        return ssh
    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        sys.exit(1)


def main():
    print("=" * 80)
    print("DIAGNÓSTICO E CORREÇÃO DO BCRYPT NO POD RUNPOD")
    print("=" * 80)

    ssh = connect_ssh()

    try:
        # 1. Verificar versão do bcrypt instalado
        print("[1/7] Verificando versão do bcrypt instalado...")
        stdout, stderr, code = run_ssh_command(
            ssh,
            "cd /root/clipai/backend && source .venv/bin/activate && pip show bcrypt | grep -E '(Name|Version|Location)'",
        )
        print(stdout)
        if stderr:
            print(f"Stderr: {stderr}")

        # 2. Verificar se bcrypt está usando extensão C
        print("\n[2/7] Verificando se bcrypt está usando extensão C...")
        stdout, stderr, code = run_ssh_command(
            ssh,
            """cd /root/clipai/backend && source .venv/bin/activate && python -c "
import bcrypt
import sys
print('Version:', bcrypt.__version__)
print('File:', bcrypt.__file__)
try:
    import _bcrypt
    print('Has _bcrypt module: YES')
except ImportError:
    print('Has _bcrypt module: NO (usando fallback Python puro)')
" """,
        )
        print(stdout)
        if stderr:
            print(f"Stderr: {stderr}")

        # 3. Verificar dependências de compilação
        print("\n[3/7] Verificando dependências de compilação...")
        stdout, stderr, code = run_ssh_command(ssh, "which gcc && which make")
        print(stdout if stdout else "GCC/Make não encontrados")

        # 4. Reinstalar bcrypt com compilação nativa
        print("\n[4/7] Reinstalando bcrypt com compilação nativa...")
        print("    Desinstalando bcrypt antigo...")
        run_ssh_command(
            ssh,
            "cd /root/clipai/backend && source .venv/bin/activate && pip uninstall -y bcrypt",
            timeout=120,
        )

        print("    Instalando bcrypt novo...")
        stdout, stderr, code = run_ssh_command(
            ssh,
            "cd /root/clipai/backend && source .venv/bin/activate && pip install --no-cache-dir bcrypt",
            timeout=120,
        )
        # Mostrar últimas linhas da instalação
        lines = stdout.split("\n")
        print("\n".join(lines[-10:]))
        if stderr and "error" in stderr.lower():
            print(f"Stderr: {stderr[-500:]}")

        # 5. Testar bcrypt após reinstalação
        print("\n[5/7] Testando bcrypt após reinstalação...")
        stdout, stderr, code = run_ssh_command(
            ssh,
            """cd /root/clipai/backend && source .venv/bin/activate && python -c "
import bcrypt
print('Version:', bcrypt.__version__)
pw = b'test123'
hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
result = bcrypt.checkpw(pw, hashed)
print('Hash test:', 'OK' if result else 'FAIL')
print('Hash gerado:', hashed[:20], '...')
" """,
        )
        print(stdout)
        if stderr:
            print(f"Stderr: {stderr}")

        # 6. Matar processo uvicorn antigo
        print("\n[6/7] Matando processo uvicorn antigo...")
        run_ssh_command(ssh, "pkill -f uvicorn")
        time.sleep(2)
        print("Processo uvicorn terminado")

        # 7. Iniciar uvicorn em background
        print("\n[7/7] Iniciando uvicorn...")
        run_ssh_command(
            ssh,
            "cd /root/clipai/backend && source .venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /root/clipai/uvicorn.log 2>&1 &",
        )
        print("Uvicorn iniciado em background")

        # Aguardar 3 segundos e verificar se iniciou
        print("\nAguardando 3 segundos para verificar inicialização...")
        time.sleep(3)

        stdout, stderr, code = run_ssh_command(
            ssh, "tail -n 30 /root/clipai/uvicorn.log"
        )
        print("\nÚltimas 30 linhas do log:")
        print(stdout)

        print("\n" + "=" * 80)
        print("DIAGNÓSTICO COMPLETO")
        print("=" * 80)

    finally:
        ssh.close()
        print("\n✓ Conexão SSH fechada")


if __name__ == "__main__":
    main()
