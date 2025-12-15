"""Ротация статусов бота"""
import random
import asyncio
import logging
import discord
from discord.ext import tasks
from discord import ActivityType, Status
from utils.config import get_config

def create_rotate_status_task(bot):
    """Создаёт задачу ротации статуса для конкретного бота"""
    
    @tasks.loop(seconds=None)
    async def rotate_status():
        await bot.wait_until_ready()

        pools = (
            (ActivityType.playing,  get_config('status_playing')),
            (ActivityType.watching, get_config('status_watching')),
            (ActivityType.listening, get_config('status_listening')),
        )

        act_type, names = random.choice(pools)
        name = random.choice(names)

        try:
            if not bot.is_ready() or bot.ws is None or getattr(bot.ws, "_closed", False):
                return
            await bot.change_presence(
                status=Status.online,
                activity=discord.Activity(name=name, type=act_type)
            )
        except (ConnectionResetError, Exception) as e:
            logging.critical("Потеря соединения при смене статуса", exc_info=True)

        await asyncio.sleep(int(get_config('time_sleep')))
    
    return rotate_status

