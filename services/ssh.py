"""SSH операции"""
import paramiko
import logging
from utils.config import get_config

host_ssh = get_config('host_ssh')
user_ssh = get_config('user_ssh')
secret_ssh = get_config('password_ssh')
port_ssh = get_config('port_ssh')

client_ssh = paramiko.SSHClient()
client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def get_ssh_client():
    """Возвращает SSH клиент"""
    return client_ssh

def execute_ssh_command(command):
    """Выполняет команду по SSH"""
    try:
        client_ssh.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
        stdin, stdout, stderr = client_ssh.exec_command(command)
        data = stdout.read().decode()
        stdin.close()
        return data
    except Exception as e:
        logging.error(f"Ошибка выполнения SSH команды: {e}")
        raise

