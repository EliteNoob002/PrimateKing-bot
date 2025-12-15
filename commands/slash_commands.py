"""Slash команды бота"""
import discord
from discord import app_commands
import logging
import random
import aiohttp
import io
import time
import uuid
import re
import os
from urllib.parse import urlparse
from typing import Optional

from utils.config import load_config
from utils.decorators import slash_command_check
from utils.database import get_session
from models.user import User
from services.yandex_gpt import yandexgpt
from services.yandex_gpt_art import generate_and_save_image
from services.telegram import send_telegram_notification
from services.ssh import execute_ssh_command
from services.api_sync import API_URL
from utils.errors import translate_yandex_error
from ui.views import ImageView
import requests

config = load_config()

async def check_image(url: str) -> bool:
    """Проверяет доступность изображения по URL"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logging.error(f"Ошибка при проверке изображения: {e}")
            return False

async def send_blin(target_user: discord.User, channel: discord.TextChannel, user: discord.User, text: Optional[str] = None):
    """Отправляет блин с говном"""
    logging.info(f'Выполнение функции send_blin начато')
    image_url = None
    try:
        image_url = random.choice(config['pancake_url'])

        if not await check_image(image_url):
            raise ValueError(f"Картинка блина по URL не доступна")
            
        await channel.send(content=f'{target_user.mention}, вам пришёл блин с говном от {user.mention} ')

        embed = discord.Embed()
        embed.set_image(url=image_url)
        if text:
            embed.set_footer(text=text)
        await channel.send(embed=embed)
    except Exception as e:
        if isinstance(e, ValueError):
            if image_url:
                logging.error(f'Картинка блина по URL {image_url} не доступна')
            else:
                logging.error('Картинка блина не доступна: список pancake_url пуст или произошла ошибка при выборе URL')
        else:
            logging.error("Ошибка при выполнении функции send_blin ", exc_info=True)
        raise
        
    logging.info(f'Функция send_blin выполнена')

def setup_slash_commands(bot):
    """Регистрирует все slash команды"""
    
    @bot.tree.command(name="sas", description="Хочешь посасать?")
    @slash_command_check()
    async def sas(interaction: discord.Interaction):
        author = interaction.user
        logging.info(f'{author.mention} {author.name} использовал команду sas')
        await interaction.response.send_message(f'{author.mention} соси')

    @bot.tree.command(name="count", description="Узнать сколько раз кто-то был послан на хуй")
    @slash_command_check()
    @app_commands.describe(target='Выберите цель')
    async def count(interaction: discord.Interaction, target: discord.Member):
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду count')
        if interaction.user == target:
            member = interaction.user
            with get_session() as session:
                user = session.query(User).filter(User.id == member.id).first()
                if user is None:
                    embed = discord.Embed(
                        title=(f'Тебя ещё ни разу не посылали нахуй'),
                        color=0xff0000
                    )
                    embed.set_thumbnail(url=member.avatar)
                    await interaction.response.send_message(embed=embed)
                else:    
                    embed = discord.Embed(
                        title=(f'Тебя послали нахуй {user.count} раз'),
                        color=0xff0000
                    )
                    embed.set_thumbnail(url=member.avatar)
                    await interaction.response.send_message(embed=embed)
        elif target.id == config['bot_id']:
            embed = discord.Embed(
                title=(f'Его невозможно послать'),
                color=0xff0000
            )
            embed.set_thumbnail(url=target.avatar)
            await interaction.response.send_message(embed=embed)        
        else:
            with get_session() as session:
                user = session.query(User).filter(User.id == target.id).first()
                if user is None:
                    embed = discord.Embed(
                        title=(f'{target.name} ещё ни разу не был послан нахуй '),
                        color=0xff0000
                    )
                    embed.set_thumbnail(url=target.avatar)
                    await interaction.response.send_message(embed=embed)
                else:
                    embed = discord.Embed(
                        title=(f'{target.name} был послан нахуй {user.count} раз'),
                        color=0xff0000
                    )
                    embed.set_thumbnail(url=target.avatar)
                    await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="avatar", description="С помощью этой команды можно получить аватарку участников сервера")
    @slash_command_check()
    @app_commands.describe(target='Выберите цель')
    async def avatar(interaction: discord.Interaction, target: discord.Member):
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду avatar')
        if target is None:
            target = interaction.user
        embed = discord.Embed(color = 0x22ff00, title = f"Аватар участника - {target.name}", description = f"[Нажмите что бы скачать аватар]({target.avatar})")
        embed.set_image(url = target.avatar)
        await interaction.response.send_message(embed = embed)

    @bot.tree.command(name="poslat", description="Можно послать кого то на хуй")
    @slash_command_check()
    @app_commands.describe(target='Выберите цель')
    async def poslat(interaction: discord.Interaction, target: discord.Member):
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду poslat')
        target_id = str(target.id)
        target_name = target.name
        if target.id == config['bot_id']:
            embed = discord.Embed(
                title=(f'Не был послан нахуй'),
                description=f"{interaction.user.mention} себя пошли нахуй",
                color=0xff0000
            )
            embed.set_thumbnail(url=interaction.user.avatar)
            await interaction.response.send_message(embed=embed) 
        else:
            with get_session() as session:
                user = session.query(User).filter(User.id == target.id).first()
                if user is None:
                    user = User(
                        id=target.id,
                        name=target_name,
                        count=1,
                        admin="0"
                    )
                    session.add(user)
                    embed = discord.Embed(title=f"{target.name} был послан нахуй",
                                description=f"{target.mention} тебя послал {interaction.user.mention}",
                                color=0xff0000)
                    embed.set_thumbnail(url=interaction.user.avatar)
                    await interaction.response.send_message(embed=embed) 
                else:
                    user.count += 1
                    embed = discord.Embed(title=f"{target.name} был послан нахуй",
                                description=f"{target.mention} тебя послал {interaction.user.mention}",
                                color=0xff0000)
                    embed.set_thumbnail(url=interaction.user.avatar)
                    await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="restartbot", description="Перезапуск бота")
    @slash_command_check()
    async def restart(interaction: discord.Interaction):
        if interaction.user.id == config['admin']:
            logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду restartbot')
            send_telegram_notification(
                f"\u2705 *Успех:* {interaction.user.mention} ({interaction.user.name}) использовал команду /restartbot"
            )
            await interaction.response.send_message(
                f'Эй {interaction.user.mention}! Команда на перезапуск бота отправлена',
                ephemeral=True
            )
            data = execute_ssh_command('systemctl restart botdis.service')
        else:
            logging.info(f'{interaction.user.mention} {interaction.user.name} попытался использовать команду restart')
            send_telegram_notification(
                f"\u26a0 *Попытка доступа:* {interaction.user.mention} ({interaction.user.name}) попытался использовать команду /restartbot без прав."
            )
            await interaction.response.send_message(
                f'У тебя нет доступа к этой команде',
                ephemeral=True
            )

    @bot.tree.command(name="update", description="Обновление файлов бота")
    @slash_command_check()
    async def update(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id == config['admin']:
            logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду update')
            send_telegram_notification(
                f"\u2705 *Успех:* {interaction.user.mention} ({interaction.user.name}) использовал команду /update"
            )

            data = execute_ssh_command('cd PrimateKing-bot \n git pull')

            await interaction.followup.send(
                f'Эй {interaction.user.mention}! Вот результат:\n```bash\n{data}\n```',
                ephemeral=True
            )

        else:
            logging.info(f'{interaction.user.mention} {interaction.user.name} попытался использовать команду update')
            send_telegram_notification(
                f"\u26a0 *Попытка доступа:* {interaction.user.mention} ({interaction.user.name}) попытался использовать команду /update без прав."
            )

            await interaction.followup.send(
                f'⛔ У тебя нет доступа к этой команде.',
                ephemeral=True
            )

    @bot.tree.command(name="help", description="Список доступных команд")
    @slash_command_check()
    async def help_command(interaction: discord.Interaction):
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду help')
        try:
            response = requests.get(f"{API_URL}/bot/active_commands")
            response.raise_for_status()
            commands_data = response.json()

            command_list = []
            for cmd in commands_data:
                if cmd['type'] == 'slash':
                    display_name = f"/{cmd['name'].lstrip('/')}"
                else:
                    display_name = cmd['name']

                command_list.append(f"{display_name} - {cmd['description']}")

            embed = discord.Embed(
                title="📜 Доступные команды",
                description="\n".join(command_list) or "Нет доступных команд",
                color=0x00ff00
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logging.error(f"Help command error: {e}")
            await interaction.response.send_message(
                "⚠️ Не удалось загрузить список команд",
                ephemeral=True
            )

    @bot.tree.command(name="gpt", description="GPT Запрос")
    @slash_command_check()
    @app_commands.describe(user_input='Введите запрос')
    async def gpt(interaction: discord.Interaction, user_input: str):
        user = interaction.user

        try:
            await interaction.response.defer()
            answer = await yandexgpt(user_input)
            if len(answer) > 2000:
                parts = [answer[i:i+2000] for i in range(0, len(answer), 2000)]
                for part in parts:
                    await interaction.followup.send(part)
            else:
                await interaction.followup.send(f'{user.mention} спросил "{user_input}"\n\nОтвет GPT: \n\n{answer}')
        except Exception as e:
            await interaction.followup.send(f'Произошла ошибка при обращении к функции YandexGPT')
            logging.error(f'Произошла ошибка при обращении к функции YandexGPT: {e}')

    @bot.tree.command(name="gpt_art", description="Генерация картинки")
    @slash_command_check()
    @app_commands.describe(user_input='Введите промт')
    async def gpt_art(interaction: discord.Interaction, user_input: str):
        user = interaction.user.name
        try:
            await interaction.response.defer()
            logging.info(f"Начата генерация картинки. Промт: {user_input}")

            gpt_img_url = await generate_and_save_image(user_input, user)
            logging.info(f"Ссылка на сгенерированное изображение: {gpt_img_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(gpt_img_url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Не удалось скачать изображение: HTTP {resp.status}")
                    image_bytes = await resp.read()

            parsed = urlparse(gpt_img_url)
            basename = os.path.basename(parsed.path)
            _, ext = os.path.splitext(basename)
            if not ext:
                ext = ".jpeg"

            safe_user = re.sub(r"[^a-zA-Z0-9]+", "", user.lower()) or "user"
            timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            rand = uuid.uuid4().hex[:6]
            attachment_filename = f"gptart-{safe_user}-{timestamp}-{rand}{ext}"

            file = discord.File(
                fp=io.BytesIO(image_bytes),
                filename=attachment_filename
            )

            embed = discord.Embed(
                title="Сгенерированное изображение",
                description="Вот изображение, созданное на основе вашего запроса:",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{attachment_filename}")

            view = ImageView(image_url=gpt_img_url, prompt=user_input, bot=bot)
            await interaction.followup.send(embed=embed, file=file, view=view)
            bot.add_view(view)

        except Exception as e:
            translated = translate_yandex_error(str(e))
            await interaction.followup.send(f'❗ {translated}', ephemeral=True)
            logging.error(f"Ошибка YandexGPT ART: {str(e)}", exc_info=True)

    @bot.tree.command(name="send_blin", description="Отправить блин с говном")
    @slash_command_check()
    @app_commands.describe(target='Выберите цель')
    @app_commands.describe(text='Сообщение под картинкой. Необязательно')
    async def send_message_command(interaction: discord.Interaction, target: discord.User, text: Optional[str] = None):
        if text:
            logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду send_blin. Цель: {target.mention} {target.name}. Сообщение {text}')
        else:
            logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду send_blin. Цель: {target.mention} {target.name}')
        channel = interaction.channel
        user = interaction.user

        try:
            await send_blin(target, channel, user, text)
            await interaction.response.send_message(f'Посылка для {target.mention} доставлена', ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(f'Ошибка: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'Произошла ошибка при отправке блина', ephemeral=True)
            logging.error(f'Произошла ошибка: {e}')

        logging.info(f'Комманда send_blin выполнена')

