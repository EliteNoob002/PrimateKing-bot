"""Точка входа Discord бота PrimateKing"""

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord
from discord.ext import commands

from commands.prefix_commands import setup_prefix_commands
from commands.slash_commands import setup_slash_commands
from events.errors import setup_error_handlers
from events.message import setup_message_events
from events.ready import setup_ready_event
from services.config_cache import ConfigCache, set_global_config_cache
from services.guild_sync import setup_guild_sync_events
from utils.bootstrap_settings import load_bootstrap_settings
from utils.database import init_db
from utils.prefix import get_prefix
from utils.proxy import setup_proxy


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["stacktrace"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
handler = RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
handler.setFormatter(JsonLogFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("bot")

settings = load_bootstrap_settings()

setup_proxy()

init_db()

description = """PrimateKing"""

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=get_prefix,
    owner_id=settings.discord_owner_id,
    intents=intents,
)

config_cache = ConfigCache(ttl_seconds=settings.config_cache_ttl_seconds)
try:
    config_cache.reload()
except Exception:
    logger.exception("Initial ConfigCache reload failed")
bot.config_cache = config_cache
set_global_config_cache(config_cache)

setup_slash_commands(bot)
setup_prefix_commands(bot)
setup_ready_event(bot)
setup_guild_sync_events(bot)
setup_message_events(bot)
setup_error_handlers(bot)

if __name__ == "__main__":
    bot.run(settings.discord_token)
