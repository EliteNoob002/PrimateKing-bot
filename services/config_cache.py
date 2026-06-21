"""Кэш runtime-настроек из MySQL.

Бот и web-панель используют одну БД: панель пишет в таблицы настроек,
бот перечитывает их с TTL (см. CONFIG_CACHE_TTL_SECONDS).
"""

import time
from dataclasses import dataclass, field
from typing import Any

from models.bot_setting import BotSetting
from models.command_setting import CommandSetting
from models.function_setting import FunctionSetting
from models.guild_setting import GuildSetting
from utils.database import get_session

DEFAULT_PREFIX = "$"

DEFAULT_BOT_SETTINGS: dict[str, Any] = {
    "time_sleep": 5,
    "status_playing": ["очко", "мафию", "экивоки", "дурака", "покер"],
    "status_watching": ["как Артём дрочит на самокаты", "как Артём бухает"],
    "status_listening": [
        "ахуенные истории от Артёма",
        "псевдоахуенные истории от Артёма",
        "как Артём любит деньги",
    ],
    "gif_urls": [],
    "pancake_url": [],
    "api_tokens": 500,
}

_global_cache: "ConfigCache | None" = None


def set_global_config_cache(cache: "ConfigCache") -> None:
    global _global_cache
    _global_cache = cache


def get_global_config_cache() -> "ConfigCache | None":
    return _global_cache


@dataclass
class RuntimeConfig:
    guild_prefixes: dict[int, str] = field(default_factory=dict)
    command_enabled: dict[str, bool] = field(default_factory=dict)
    function_enabled: dict[str, bool] = field(default_factory=dict)
    bot_settings: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_BOT_SETTINGS))


class ConfigCache:
    def __init__(self, ttl_seconds: int = 10):
        self.ttl_seconds = ttl_seconds
        self._config = RuntimeConfig()
        self._loaded_at = 0.0

    def get_config(self) -> RuntimeConfig:
        now = time.monotonic()
        if now - self._loaded_at > self.ttl_seconds:
            self.reload()
        return self._config

    def reload(self) -> None:
        with get_session() as session:
            guild_rows = session.query(GuildSetting).all()
            command_rows = session.query(CommandSetting).all()
            function_rows = session.query(FunctionSetting).all()
            bot_rows = session.query(BotSetting).all()

            guild_prefixes = {row.guild_id: row.prefix for row in guild_rows}

            command_enabled = {
                self._make_command_key(row.guild_id, row.command_type, row.command_name): row.enabled for row in command_rows
            }

            function_enabled = {self._make_function_key(row.guild_id, row.function_name): row.enabled for row in function_rows}

            bot_settings = dict(DEFAULT_BOT_SETTINGS)
            for row in bot_rows:
                bot_settings[row.setting_key] = row.value_json

        self._config = RuntimeConfig(
            guild_prefixes=guild_prefixes,
            command_enabled=command_enabled,
            function_enabled=function_enabled,
            bot_settings=bot_settings,
        )
        self._loaded_at = time.monotonic()

    def get_prefix(self, guild_id: int | None) -> str:
        config = self.get_config()
        if guild_id is None:
            return DEFAULT_PREFIX
        return config.guild_prefixes.get(guild_id, DEFAULT_PREFIX)

    def get_bot_setting(self, key: str, default: Any = None) -> Any:
        config = self.get_config()
        if key in config.bot_settings:
            return config.bot_settings[key]
        return DEFAULT_BOT_SETTINGS.get(key, default)

    def is_command_enabled(
        self,
        guild_id: int | None,
        command_type: str,
        command_name: str,
    ) -> bool:
        config = self.get_config()
        guild_key = self._make_command_key(guild_id, command_type, command_name)
        global_key = self._make_command_key(None, command_type, command_name)

        if guild_key in config.command_enabled:
            return config.command_enabled[guild_key]
        if global_key in config.command_enabled:
            return config.command_enabled[global_key]
        return True

    def is_function_enabled(self, guild_id: int | None, function_name: str) -> bool:
        config = self.get_config()
        guild_key = self._make_function_key(guild_id, function_name)
        global_key = self._make_function_key(None, function_name)

        if guild_key in config.function_enabled:
            return config.function_enabled[guild_key]
        if global_key in config.function_enabled:
            return config.function_enabled[global_key]
        return True

    @staticmethod
    def _make_command_key(guild_id: int | None, command_type: str, command_name: str) -> str:
        return f"{guild_id if guild_id is not None else 'global'}:{command_type}:{command_name}"

    @staticmethod
    def _make_function_key(guild_id: int | None, function_name: str) -> str:
        return f"{guild_id if guild_id is not None else 'global'}:{function_name}"
