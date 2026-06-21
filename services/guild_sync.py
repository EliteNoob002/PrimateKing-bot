"""Синхронизация bot_guild_settings с Discord (название сервера и т.д.)."""

import asyncio
import logging

from models.guild_setting import GuildSetting
from utils.database import get_session

logger = logging.getLogger(__name__)


def sync_guild_names_from_discord(bot) -> None:
    """Обновляет guild_name в bot_guild_settings для всех серверов, где есть бот."""
    if not bot.guilds:
        logger.debug("sync_guild_names: у бота нет guilds")
        return

    with get_session() as session:
        for guild in bot.guilds:
            row = session.query(GuildSetting).filter_by(guild_id=guild.id).first()
            if row is None:
                session.add(
                    GuildSetting(
                        guild_id=guild.id,
                        guild_name=guild.name,
                    )
                )
                logger.info(
                    "bot_guild_settings: создана запись guild_id=%s guild_name=%r",
                    guild.id,
                    guild.name,
                )
            elif row.guild_name != guild.name:
                row.guild_name = guild.name
                logger.info(
                    "bot_guild_settings: обновлено guild_name=%r для guild_id=%s",
                    guild.name,
                    guild.id,
                )


def setup_guild_sync_events(bot):
    """События для актуализации guild_name при переименовании сервера."""

    @bot.event
    async def on_guild_update(before, after):
        if before.name == after.name:
            return

        def _update_name():
            with get_session() as session:
                row = session.query(GuildSetting).filter_by(guild_id=after.id).first()
                if row is None:
                    session.add(
                        GuildSetting(
                            guild_id=after.id,
                            guild_name=after.name,
                        )
                    )
                else:
                    row.guild_name = after.name
            logger.info(
                "bot_guild_settings: guild_id=%s переименован в %r",
                after.id,
                after.name,
            )

        await asyncio.to_thread(_update_name)

    @bot.event
    async def on_guild_join(guild):
        def _insert():
            with get_session() as session:
                row = session.query(GuildSetting).filter_by(guild_id=guild.id).first()
                if row is None:
                    session.add(
                        GuildSetting(
                            guild_id=guild.id,
                            guild_name=guild.name,
                        )
                    )
                else:
                    row.guild_name = guild.name

        await asyncio.to_thread(_insert)
        logger.info("bot_guild_settings: бот добавлен на сервер %r (%s)", guild.name, guild.id)
