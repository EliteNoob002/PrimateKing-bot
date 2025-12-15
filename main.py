"""Точка входа Discord бота PrimateKing"""
import logging
import discord
from discord.ext import commands

from utils.config import load_config
from utils.proxy import setup_proxy
from utils.database import init_db
from commands.slash_commands import setup_slash_commands
from commands.prefix_commands import setup_prefix_commands
from events.ready import setup_ready_event
from events.message import setup_message_events
from events.errors import setup_error_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    filename="py_log.log",
    filemode="w",
    encoding='utf-8',
    format="%(asctime)s %(levelname)s %(message)s"
)
logging.debug("A DEBUG Message")
logging.info("An INFO")
logging.warning("A WARNING")
logging.error("An ERROR")
logging.critical("A message of CRITICAL severity")

# Загрузка конфигурации
config = load_config()

# Настройка прокси ДО создания бота
setup_proxy()

# Инициализация базы данных
init_db()

# Создание бота
description = '''PrimateKing'''

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=config['prefix'],
    owner_id=config['admin'],
    intents=intents,
)

# Регистрация компонентов
setup_slash_commands(bot)
setup_prefix_commands(bot)
setup_ready_event(bot)
setup_message_events(bot)
setup_error_handlers(bot)

# Запуск бота
if __name__ == "__main__":
    bot.run(config['token'])

