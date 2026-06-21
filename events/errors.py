"""Обработчики ошибок"""
import logging

import discord
import requests
from discord import app_commands
from discord.ext import commands

from services.api_sync import API_URL
from services.telegram import schedule_notify_api_panel_unreachable


def setup_error_handlers(bot):
    """Регистрирует обработчики ошибок"""
    # Хранилище для отслеживания уже отправленных сообщений об ошибках
    sent_error_messages = set()

    @bot.check
    async def global_command_check(ctx: commands.Context):
        """Глобальная проверка для prefix команд"""
        if ctx.interaction:  # Слэш-команды обрабатываются отдельно
            return True

        try:
            # Проверяем команду по имени без префикса (как в API)
            clean_name = (
                ctx.command.name.lstrip("$") if ctx.command else "unknown"
            )
            response = requests.get(f"{API_URL}/bot/commands/prefix/{clean_name}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if not data.get('enabled', True):
                    # Не отправляем сообщение здесь, это будет сделано в on_command_error
                    return False
            return True
        except Exception as e:
            logging.error(f"Command check error: {e}")
            schedule_notify_api_panel_unreachable(
                "errors:prefix_check",
                clean_name,
                e,
                API_URL,
            )
            return True

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        """Обработка ошибок prefix команд"""
        if isinstance(error, commands.CheckFailure):
            # Команда была отключена через API проверку
            # Используем уникальный ключ для предотвращения дублирования сообщений
            error_key = (ctx.message.id, ctx.command.name if ctx.command else None)
            if error_key not in sent_error_messages:
                sent_error_messages.add(error_key)
                await ctx.reply("🚫 Эта команда временно отключена")
                # Очищаем старые записи (оставляем только последние 100)
                if len(sent_error_messages) > 100:
                    sent_error_messages.clear()
            return
        # Остальные ошибки не обрабатываем здесь, пусть discord.py обрабатывает их сам

    @bot.tree.error
    async def on_slash_error(interaction: discord.Interaction, error):
        """Обработка ошибок slash команд"""
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message(
                    "🚫 Эта команда временно отключена",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "🚫 Эта команда временно отключена",
                    ephemeral=True
                )
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

