#!/usr/bin/env python3
"""Перенос runtime-настроек из .env в MySQL (общая БД с web-панелью).

Порядок:
  1. alembic upgrade head — миграции бота (таблица alembic_version_bot, не alembic_version панели)
  2. ensure_bot_schema — create_all для отсутствующих таблиц
  3. seed bot_guild_settings / bot_settings из переменных .env
"""

import json
import logging
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.bot_setting import BotSetting  # noqa: E402
from models.guild_setting import GuildSetting  # noqa: E402
from utils.bootstrap_settings import load_bootstrap_settings  # noqa: E402
from utils.database import ensure_bot_schema, get_session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ENV_TO_BOT_SETTING = {
    "TIME_SLEEP": ("time_sleep", int),
    "STATUS_PLAYING": ("status_playing", json.loads),
    "STATUS_WATCHING": ("status_watching", json.loads),
    "STATUS_LISTENING": ("status_listening", json.loads),
    "GIF_URLS": ("gif_urls", json.loads),
    "PANCAKE_URL": ("pancake_url", json.loads),
    "API_TOKENS": ("api_tokens", int),
}


def _read_bot_settings_from_env() -> dict:
    settings = {}
    for env_key, (db_key, cast) in ENV_TO_BOT_SETTING.items():
        raw = os.getenv(env_key)
        if raw is None or raw.strip() == "":
            continue
        try:
            settings[db_key] = cast(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Некорректное значение {env_key}: {exc}") from exc
    return settings


def upgrade_database() -> None:
    """Миграции бота в общей MySQL (отдельная alembic_version_bot)."""
    alembic_ini = ROOT / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Не найден {alembic_ini}")

    logger.info("Применяю миграции бота: alembic upgrade head (alembic_version_bot)")
    alembic_cfg = Config(str(alembic_ini))
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Миграции бота применены")
    except Exception as exc:
        logger.warning(
            "Alembic upgrade завершился с ошибкой (часто при общей БД с панелью): %s",
            exc,
        )

    logger.info("Проверяю наличие таблиц бота (create_all)")
    ensure_bot_schema()
    logger.info("Схема бота актуальна")


def seed_guild_settings(prefix: str, guild_id: int) -> None:
    with get_session() as session:
        existing = session.query(GuildSetting).filter_by(guild_id=guild_id).first()
        if existing:
            existing.prefix = prefix
            logger.info("bot_guild_settings: обновлён prefix=%s для guild_id=%s", prefix, guild_id)
        else:
            session.add(GuildSetting(guild_id=guild_id, prefix=prefix))
            logger.info("bot_guild_settings: создан prefix=%s для guild_id=%s", prefix, guild_id)


def seed_bot_settings(values: dict) -> None:
    with get_session() as session:
        for key, value in values.items():
            existing = session.query(BotSetting).filter_by(setting_key=key).first()
            if existing:
                existing.value_json = value
                logger.info("bot_settings: обновлён %s", key)
            else:
                session.add(BotSetting(setting_key=key, value_json=value))
                logger.info("bot_settings: создан %s", key)


def main() -> None:
    load_dotenv(ROOT / ".env")

    upgrade_database()
    settings = load_bootstrap_settings()

    guild_id = settings.primary_guild_id
    if guild_id is None:
        raise SystemExit("Задайте PRIMARY_GUILD_ID в .env для seed bot_guild_settings")

    prefix = os.getenv("PREFIX", "$")
    bot_settings = _read_bot_settings_from_env()

    seed_guild_settings(prefix, guild_id)
    if bot_settings:
        seed_bot_settings(bot_settings)

    logger.info("Seed из .env завершён успешно")


if __name__ == "__main__":
    main()
