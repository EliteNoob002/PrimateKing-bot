"""Bootstrap-настройки из .env (секреты и параметры запуска)."""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_optional_int(key: str) -> int | None:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return None
    return int(raw)


def _env_log_level(key: str, default: str = "INFO") -> int:
    raw = os.getenv(key, default).strip().upper()
    level = getattr(logging, raw, None)
    if not isinstance(level, int):
        return logging.INFO
    return level


@dataclass(frozen=True)
class BootstrapSettings:
    app_env: str
    discord_token: str
    database_url: str
    discord_owner_id: int
    bot_id: int
    primary_guild_id: int | None
    panel_api_url: str | None
    panel_api_token: str | None
    webhook_dev: str | None
    webhook_pk: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    yandex_api_key: str | None
    yandex_folder_id: str | None
    openai_api_key: str | None
    openai_api_url: str | None
    webupload_base: str | None
    webupload_api_key: str | None
    ssh_host: str | None
    ssh_user: str | None
    ssh_password: str | None
    ssh_port: int
    discord_proxy_enabled: bool
    discord_proxy_url: str | None
    discord_proxy_user: str | None
    discord_proxy_pass: str | None
    config_cache_ttl_seconds: int
    log_level: int


@lru_cache(maxsize=1)
def load_bootstrap_settings() -> BootstrapSettings:
    return BootstrapSettings(
        app_env=os.getenv("APP_ENV", "development"),
        discord_token=os.environ["DISCORD_TOKEN"],
        database_url=os.environ["DATABASE_URL"],
        discord_owner_id=int(os.environ["DISCORD_OWNER_ID"]),
        bot_id=int(os.environ["BOT_ID"]),
        primary_guild_id=_env_optional_int("PRIMARY_GUILD_ID"),
        panel_api_url=os.getenv("PANEL_API_URL"),
        panel_api_token=os.getenv("PANEL_API_TOKEN"),
        webhook_dev=os.getenv("WEBHOOK_DEV"),
        webhook_pk=os.getenv("WEBHOOK_PK"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        yandex_api_key=os.getenv("YANDEX_API_KEY"),
        yandex_folder_id=os.getenv("YANDEX_FOLDER_ID"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_url=os.getenv("OPENAI_API_URL"),
        webupload_base=os.getenv("WEBUPLOAD_BASE"),
        webupload_api_key=os.getenv("WEBUPLOAD_API_KEY"),
        ssh_host=os.getenv("SSH_HOST"),
        ssh_user=os.getenv("SSH_USER"),
        ssh_password=os.getenv("SSH_PASSWORD"),
        ssh_port=_env_int("SSH_PORT", 22),
        discord_proxy_enabled=_env_bool("DISCORD_PROXY_ENABLED", False),
        discord_proxy_url=os.getenv("DISCORD_PROXY_URL"),
        discord_proxy_user=os.getenv("DISCORD_PROXY_USER"),
        discord_proxy_pass=os.getenv("DISCORD_PROXY_PASS"),
        config_cache_ttl_seconds=_env_int("CONFIG_CACHE_TTL_SECONDS", 10),
        log_level=_env_log_level("LOG_LEVEL", "INFO"),
    )
