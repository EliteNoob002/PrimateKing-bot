"""Декораторы для команд"""
import functools
import requests
import logging
from discord import app_commands
from utils.config import get_config

API_URL = get_config('my_api_url')

def function_enabled_check(function_name: str):
    """Декоратор для проверки, включена ли функция через API"""
    def decorator(callback):
        @functools.wraps(callback)
        async def wrapper(*args, **kwargs):
            try:
                response = requests.get(
                    f"{API_URL}/bot/commands/function/{function_name}",
                    timeout=3
                )

                try:
                    data = response.json()
                except ValueError:
                    logging.error(
                        f"[Decorator] Некорректный JSON от API для {function_name}: "
                        f"status={response.status_code}, text={response.text[:200]!r}"
                    )
                    return await callback(*args, **kwargs)

                if response.status_code == 200 and not data.get('enabled', True):
                    return

            except Exception as e:
                logging.error(f"[Decorator] Ошибка проверки для {function_name}: {e}")
                return await callback(*args, **kwargs)

            return await callback(*args, **kwargs)
        return wrapper
    return decorator


def slash_command_check():
    """Проверка для slash-команд через API"""
    async def predicate(interaction):
        command_name = interaction.command.name
        try:
            response = requests.get(
                f"{API_URL}/bot/commands/slash/{command_name}",
                timeout=3
            )
            if response.status_code == 200:
                return response.json()['enabled']
            return True
        except Exception as e:
            logging.error(f"Slash check error: {e}")
            return True
    return app_commands.check(predicate)

