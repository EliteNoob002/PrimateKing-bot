"""Динамический prefix из ConfigCache."""


async def get_prefix(bot, message):
    if not message.guild:
        return "$"

    cache = getattr(bot, "config_cache", None)
    if cache is None:
        return "$"

    return cache.get_prefix(message.guild.id)
