"""Обработчики ошибок"""

import logging

import discord
from discord import app_commands
from discord.ext import commands


def setup_error_handlers(bot):
    """Регистрирует обработчики ошибок"""
    sent_error_messages = set()

    @bot.check
    async def global_command_check(ctx: commands.Context):
        """Глобальная проверка для prefix команд через ConfigCache."""
        if ctx.interaction:
            return True

        cache = getattr(bot, "config_cache", None)
        if cache is None or ctx.command is None:
            return True

        clean_name = ctx.command.name.lstrip("$")
        guild_id = ctx.guild.id if ctx.guild else None
        return cache.is_command_enabled(guild_id, "prefix", clean_name)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        """Обработка ошибок prefix команд"""
        if isinstance(error, commands.CheckFailure):
            error_key = (ctx.message.id, ctx.command.name if ctx.command else None)
            if error_key not in sent_error_messages:
                sent_error_messages.add(error_key)
                await ctx.reply("🚫 Эта команда временно отключена")
                if len(sent_error_messages) > 100:
                    sent_error_messages.clear()
            return

    @bot.tree.error
    async def on_slash_error(interaction: discord.Interaction, error):
        """Обработка ошибок slash команд"""
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("🚫 Эта команда временно отключена", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("🚫 Эта команда временно отключена", ephemeral=True)
            return

        original = getattr(error, "original", None)

        if original is not None:
            logging.error(
                "Slash error in command %s: %r",
                getattr(interaction.command, "name", "unknown"),
                original,
                exc_info=original,
            )
        else:
            logging.error(
                "Slash error (wrapper): %r",
                error,
                exc_info=True,
            )
