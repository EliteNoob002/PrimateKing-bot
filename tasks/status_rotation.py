"""Ротация статусов бота"""

import asyncio
import logging
import random

import discord
from discord import ActivityType, Status
from discord.ext import tasks


def create_rotate_status_task(bot):
    """Создаёт задачу ротации статуса для конкретного бота"""

    @tasks.loop(seconds=None)
    async def rotate_status():
        await bot.wait_until_ready()

        cache = getattr(bot, "config_cache", None)
        if cache is None:
            await asyncio.sleep(5)
            return

        pools = (
            (ActivityType.playing, cache.get_bot_setting("status_playing", [])),
            (ActivityType.watching, cache.get_bot_setting("status_watching", [])),
            (ActivityType.listening, cache.get_bot_setting("status_listening", [])),
        )

        valid_pools = [(t, names) for t, names in pools if names]
        if not valid_pools:
            await asyncio.sleep(int(cache.get_bot_setting("time_sleep", 5)))
            return

        act_type, names = random.choice(valid_pools)
        name = random.choice(names)

        try:
            if not bot.is_ready() or bot.ws is None or getattr(bot.ws, "_closed", False):
                return
            await bot.change_presence(status=Status.online, activity=discord.Activity(name=name, type=act_type))
        except (ConnectionResetError, Exception):
            logging.critical("Потеря соединения при смене статуса", exc_info=True)

        await asyncio.sleep(int(cache.get_bot_setting("time_sleep", 5)))

    return rotate_status
