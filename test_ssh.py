#!/usr/bin/env python3
"""Teste simples de conexão SSH."""

import paramiko
from pathlib import Path

POD_HOST = "ssh.runpod.io"
POD_USER = "qh3hpqrnck8ila-644113f7"
SSH_KEY_PATH = Path(r"C:\Users\Marcos\.ssh\id_ed25519_runpod")


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        private_key = paramiko.Ed25519Key.from_private_key_file(str(SSH_KEY_PATH))
        ssh.connect(hostname=POD_HOST, username=POD_USER, pkey=private_key, timeout=30)
        print("✓ Conectado\n")

        transport = ssh.get_transport()

        # Teste 1: comando simples COM PTY
        print("Teste 1: ls /root (com PTY)")
        channel = transport.open_session()
        channel.get_pty()  # SOLICITAR PTY!
        channel.exec_command("ls /root")
        stdout = channel.makefile("r").read().decode()
        stderr = channel.makefile_stderr("r").read().decode()
        print(f"Stdout: {stdout[:500]}")
        print(f"Stderr: {stderr}")
        channel.close()

        # Teste 2: comando com source COM PTY
        print("\nTeste 2: source venv (com PTY)")
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(
            "cd /root/clipai/backend && source .venv/bin/activate && which python"
        )
        stdout = channel.makefile("r").read().decode()
        stderr = channel.makefile_stderr("r").read().decode()
        print(f"Stdout: {stdout[:500]}")
        print(f"Stderr: {stderr}")
        channel.close()

        # Teste 3: cat arquivo de log COM PTY
        print("\nTeste 3: cat log (com PTY)")
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command("cat /root/clipai/uvicorn.log | tail -20")
        stdout = channel.makefile("r").read().decode()
        stderr = channel.makefile_stderr("r").read().decode()
        print(f"Stdout: {stdout[:1000]}")
        print(f"Stderr: {stderr}")
        channel.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
