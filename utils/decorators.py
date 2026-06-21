"""Декораторы для команд"""

import functools
import logging

from discord import app_commands


def _get_bot_from_args(*args, **kwargs):
    if args:
        first = args[0]
        if hasattr(first, "client"):
            return first.client
        if hasattr(first, "bot"):
            return first.bot
        if hasattr(first, "config_cache"):
            return first
    return None


def _get_guild_id_from_args(*args, **kwargs) -> int | None:
    if not args:
        return None
    first = args[0]
    guild = getattr(first, "guild", None)
    if guild is not None:
        return guild.id
    return None


def function_enabled_check(function_name: str):
    """Декоратор для проверки, включена ли функция через ConfigCache."""

    def decorator(callback):
        @functools.wraps(callback)
        async def wrapper(*args, **kwargs):
            bot = _get_bot_from_args(*args, **kwargs)
            if bot is None:
                return await callback(*args, **kwargs)

            cache = getattr(bot, "config_cache", None)
            if cache is None:
                return await callback(*args, **kwargs)

            guild_id = _get_guild_id_from_args(*args, **kwargs)
            if not cache.is_function_enabled(guild_id, function_name):
                logging.debug("Function %s disabled for guild %s", function_name, guild_id)
                return

            return await callback(*args, **kwargs)

        return wrapper

    return decorator


def slash_command_check():
    """Проверка для slash-команд через ConfigCache."""

    async def predicate(interaction):
        cache = getattr(interaction.client, "config_cache", None)
        if cache is None:
            return True

        guild_id = interaction.guild.id if interaction.guild else None
        command_name = interaction.command.name
        enabled = cache.is_command_enabled(guild_id, "slash", command_name)
        if not enabled:
            logging.debug("Slash command %s disabled for guild %s", command_name, guild_id)
        return enabled

    return app_commands.check(predicate)
