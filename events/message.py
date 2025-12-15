"""Обработчики событий сообщений"""
import discord
import logging
from datetime import datetime, timezone
from io import StringIO
from utils.database import get_session
from models.user import User
from utils.decorators import function_enabled_check
from utils.config import get_config

GIF_URLS = get_config('gif_urls')

def setup_message_events(bot):
    """Регистрирует события сообщений"""
    
    @bot.event
    async def on_message(message):
        """Обработка сообщений с упоминанием 'primateking1488'"""
        if 'primateking1488' in message.content.lower():
            with get_session() as session:
                user = session.query(User).filter(User.id == message.author.id).first()
                if user is None:
                    user = User(
                        id=message.author.id,
                        name=message.author.name,
                        count=1,
                        admin="0"
                    )
                    session.add(user)
                    await message.channel.send(f'{message.author.mention} Пошёл нахуй!')
                else:
                    user.count += 1
                    await message.channel.send(f'{message.author.mention} Пошёл нахуй!')
        await bot.process_commands(message)

    async def on_message_gifs(message):
        """Обработка сообщений с GIF"""
        if message.author == bot.user:
            return

        for gif_url in GIF_URLS:
            if gif_url in message.content:
                await message.reply(gif_url)
                return

        for attachment in message.attachments:
            if attachment.url.endswith(".gif") and attachment.url in GIF_URLS:
                await message.reply(attachment.url)
                return

        # Не вызываем bot.process_commands здесь, так как он уже вызывается в основном on_message

    decorated_on_message = function_enabled_check("on_message_gifs")(on_message_gifs)
    bot.add_listener(decorated_on_message, "on_message")

    @bot.event
    async def on_message_delete(message):
        """Логирование удалённых сообщений"""
        if message.author.bot:
            return

        log_channel = bot.get_channel(1396859532222660789)
        if not log_channel:
            logging.warning("Не удалось найти канал логов удалённых сообщений.")
            return

        author_info = f"{message.author} (ID: {message.author.id})"
        channel_info = f"#{message.channel.name} (ID: {message.channel.id})"
        created_info = str(message.created_at)
        message_id = message.id
        attachments = "\n               ".join([att.url for att in message.attachments]) if message.attachments else "Нет"
        text = message.content or ""

        embed = discord.Embed(
            title="🗑️ Сообщение удалено",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Автор", value=author_info, inline=False)
        embed.add_field(name="Канал", value=channel_info, inline=False)
        embed.add_field(name="Вложения", value=attachments, inline=False)
        embed.set_footer(text=f"ID сообщения: {message_id}")

        if 0 < len(text) <= 1000:
            embed.add_field(name="Содержимое", value=text, inline=False)
            await log_channel.send(embed=embed)

            logging.info(
                f"Удалено сообщение от {author_info} в {channel_info}\n"
                f"────────────────────────────────────────────────────────\n"
                f"Время:        {created_info}\n"
                f"Содержимое:   {repr(text)}\n"
                f"Вложения:     {attachments}\n"
                f"────────────────────────────────────────────────────────"
            )

        elif len(text) > 1000:
            await log_channel.send(embed=embed)

            file_buffer = StringIO(text)
            file = discord.File(fp=file_buffer, filename=f"deleted_message_{message_id}.txt")
            await log_channel.send(file=file)

            logging.info(
                f"Удалено длинное сообщение от {author_info} в {channel_info}\n"
                f"────────────────────────────────────────────────────────\n"
                f"Время:        {created_info}\n"
                f"Содержимое:   [сохранено как файл deleted_message_{message_id}.txt]\n"
                f"Вложения:     {attachments}\n"
                f"────────────────────────────────────────────────────────"
            )

        else:
            await log_channel.send(embed=embed)

            logging.info(
                f"Удалено сообщение без текста от {author_info} в {channel_info}\n"
                f"────────────────────────────────────────────────────────\n"
                f"Время:        {created_info}\n"
                f"Содержимое:   [нет текста]\n"
                f"Вложения:     {attachments}\n"
                f"────────────────────────────────────────────────────────"
            )

