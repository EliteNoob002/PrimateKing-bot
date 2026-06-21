"""SSH операции"""

import logging

import paramiko

from utils.bootstrap_settings import load_bootstrap_settings

client_ssh = paramiko.SSHClient()
client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def get_ssh_client():
    """Возвращает SSH клиент"""
    return client_ssh


def execute_ssh_command(command):
    """Выполняет команду по SSH"""
    settings = load_bootstrap_settings()
    if not settings.ssh_host or not settings.ssh_user:
        raise RuntimeError("SSH не настроен: задайте SSH_HOST и SSH_USER в .env")

    try:
        client_ssh.connect(
            hostname=settings.ssh_host,
            username=settings.ssh_user,
            password=settings.ssh_password,
            port=settings.ssh_port,
        )
        stdin, stdout, stderr = client_ssh.exec_command(command)
        data = stdout.read().decode()
        stdin.close()
        return data
    except Exception as e:
        logging.error(f"Ошибка выполнения SSH команды: {e}")
        raise
