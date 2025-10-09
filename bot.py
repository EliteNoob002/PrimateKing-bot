import random
import discord
from discord.ext import commands, tasks
import yaml
import logging
from discord import app_commands
import myconnutils
import paramiko
from asyncio import sleep 
from discord_webhook import DiscordWebhook
from openai import AsyncOpenAI
from typing import Optional
import aiohttp
import asyncio
import yandexgpt
import yandexgptart
import requests
import json
import inspect
from datetime import datetime, timezone
import functools
from io import StringIO
from aiohttp import BasicAuth, ClientConnectionError
import discord.http as dhttp

logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",encoding='utf-8',
                    format="%(asctime)s %(levelname)s %(message)s")
logging.debug("A DEBUG Message")
logging.info("An INFO")
logging.warning("A WARNING")
logging.error("An ERROR")
logging.critical("A message of CRITICAL severity")

description = '''PrimateKing'''

with open("config.yml", encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader,)


# --- Прокси из конфига---
proxy = None
proxy_auth = None
if config.get('discord_proxy_enabled'):
    proxy = config.get('discord_proxy_url')
    user = config.get('discord_proxy_user')
    pwd  = config.get('discord_proxy_pass')
    if user and pwd and proxy and "@" not in proxy:
        proxy_auth = BasicAuth(user, pwd)

# --- Принудительный прокси для всех REST-запросов discord.py ---
_orig_request = dhttp.HTTPClient.request

async def _proxied_request(self, route, **kwargs):
    # таймаут по умолчанию
    kwargs.setdefault("timeout", aiohttp.ClientTimeout(total=20))
    # чуть стабильности с некоторыми проксями
    headers = kwargs.setdefault("headers", {})
    headers.setdefault("Connection", "close")
    # прокси (если включён)
    if proxy:
        kwargs.setdefault("proxy", proxy)
        if proxy_auth:
            kwargs.setdefault("proxy_auth", proxy_auth)
    try:
        return await _orig_request(self, route, **kwargs)
    except Exception:
        logging.exception("Discord HTTP error on %s %s", route.method, route.url)
        raise

dhttp.HTTPClient.request = _proxied_request

# --- Принудительный прокси для WebSocket-подключений (gateway) ---

_orig_ws_connect = dhttp.HTTPClient.ws_connect

async def _proxied_ws_connect(self, url, **kwargs):
    # Задаём heartbeat/autoping и новые таймауты через ClientWSTimeout
    kwargs.setdefault("autoping", True)
    kwargs.setdefault("heartbeat", 30.0)
    ws_timeout = aiohttp.ClientWSTimeout(ws_close=60.0, ws_receive=75.0)
    kwargs["timeout"] = ws_timeout

    try:
        session = getattr(self, "_HTTPClient__session", None)
        if isinstance(session, aiohttp.ClientSession):
            return await session.ws_connect(url, **kwargs)
        return await _orig_ws_connect(self, url, **kwargs)
    except Exception:
        logging.exception("Discord WS error connect to %s", url)
        raise

dhttp.HTTPClient.ws_connect = _proxied_ws_connect

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=config['prefix'],
    owner_id=config['admin'],
    intents=intents,
)


host_ssh = config['host_ssh']
user_ssh = config['user_ssh']
secret_ssh = config['password_ssh']
port_ssh = config['port_ssh']

client_ssh = paramiko.SSHClient()
client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Подключение к API OpenAI
client_openai = AsyncOpenAI(
  api_key=config['openai_key'],
)


TG_BOT_TOKEN = config['tg_bot_token']
TG_CHAT_ID = config['tg_chat_id']

GIF_URLS = config['gif_urls']  # Список GIF-ссылок, на которые реагируем

API_URL = config['my_api_url']

def function_enabled_check(function_name: str):
    def decorator(callback):
        @functools.wraps(callback)
        async def wrapper(*args, **kwargs):
            try:
                response = requests.get(
                    f"{API_URL}/bot/commands/function/{function_name}",
                    timeout=3
                )
                data = response.json()
                if response.status_code == 200 and not data.get('enabled', True):
                    return 
            except Exception as e:
                logging.error(f"[Decorator] Ошибка проверки для {function_name}: {e}")
                return
            return await callback(*args, **kwargs)
        return wrapper
    return decorator


async def _post_discord_webhook(url: str, content: str):
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        kw = {}
        # Если прокси включён — гоняем вебхуки через него (это тоже Discord)
        if proxy and ("discord.com" in url or "discordapp.com" in url):
            kw["proxy"] = proxy
            if proxy_auth:
                kw["proxy_auth"] = proxy_auth
        await s.post(url, json={"content": content}, **kw)

# Класс View с кнопками
class ImageView(discord.ui.View):
    def __init__(self, image_url: str, prompt: str):
        # timeout=None – view не будет отключаться автоматически
        super().__init__(timeout=None)
        self.image_url = image_url
        self.prompt = prompt

    @discord.ui.button(label="Скачать изображение", style=discord.ButtonStyle.green, custom_id="download_image")
    async def download_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Вы можете скачать изображение по [ссылке]({self.image_url}).", ephemeral=True
        )

    @discord.ui.button(label="Скопировать промт", style=discord.ButtonStyle.blurple, custom_id="copy_prompt")
    async def copy_prompt_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Промт для копирования: `{self.prompt}`", ephemeral=True
        )

    @discord.ui.button(label="Сгенерировать снова", style=discord.ButtonStyle.red, row=1, custom_id="regenerate_image")
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("Генерация изображения, пожалуйста, подождите...", ephemeral=True)
            logging.info(f"Повторная генерация картинки по промту: {self.prompt}")
            new_gpt_img = await yandexgptart.generate_and_save_image(self.prompt, interaction.user.name)
            new_embed = discord.Embed(
                title="Сгенерированное изображение",
                description="Вот изображение, созданное на основе вашего запроса:",
                color=discord.Color.blue()
            )
            new_embed.set_image(url=new_gpt_img)
            new_view = ImageView(new_gpt_img, self.prompt)
            await interaction.followup.send(embed=new_embed, view=new_view)
            bot.add_view(new_view)  # Регистрация нового постоянного view
        except Exception as e:
            logging.error(f"Ошибка при повторной генерации изображения: {str(e)}")
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


@tasks.loop(seconds=None)
async def rotate_status():
    await bot.wait_until_ready()

    pools = (
        (discord.ActivityType.playing,  config['status_playing']),
        (discord.ActivityType.watching, config['status_watching']),
        (discord.ActivityType.listening, config['status_listening']),
    )

    act_type, names = random.choice(pools)
    name = random.choice(names)

    try:
        if not bot.is_ready() or bot.ws is None or getattr(bot.ws, "_closed", False):
            return
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(name=name, type=act_type)
        )
    except (ConnectionResetError, ClientConnectionError, discord.ConnectionClosed):
        logging.critical("Потеря соединения при смене статуса", exc_info=True)

    await asyncio.sleep(int(config['time_sleep']))


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    # синхронизация команд
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)
    print('------')

    tasks = []
    for url in (config.get('webhook_dev'), config.get('webhook_pk')):
        if url:
            tasks.append(_post_discord_webhook(url, f'Бот {bot.user} запущен'))

    if tasks:
        async def _fanout():
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logging.error("Webhook send failed: %s", r)
        asyncio.create_task(_fanout())

    # старт фонового таска статусов
    if not rotate_status.is_running():
        rotate_status.start()

    async def _sync_api():
        try:
            await asyncio.sleep(1)
            await asyncio.to_thread(send_commands_to_api)
        except Exception:
            logging.exception("Ошибка при синхронизации команд с API")
    asyncio.create_task(_sync_api())
        
def slash_command_check():
    async def predicate(interaction: discord.Interaction):
        command_name = interaction.command.name
        try:
            response = requests.get(
                f"{API_URL}/bot/commands/slash/{command_name}",
                timeout=3
            )
            if response.status_code == 200:
                return response.json()['enabled']
            return True
        except Exception as e:
            logging.error(f"Slash check error: {e}")
            return True
    return app_commands.check(predicate)

@bot.command()
@commands.has_role("Тест1") #команда teste с проверкой роли "тест1"
async def teste(ctx, *arg):
    client_ssh.connect(hostname=config['host_ssh'], username=config['user_ssh'], password=config['password_ssh'], port=config['port'])
    stdin, stdout, stderr = client_ssh.exec_command('ls -l \n')
    data = stdout.read() + stderr.read()
    client_ssh.close()
    await ctx.reply(f'Ответ ssh: {data}')

@bot.command()
@commands.has_role("Тест2")
async def testl(ctx, *arg):
    await ctx.reply(random.randint(100, 200)) 

@bot.tree.command(name="sas", description="Хочешь посасать?")
@slash_command_check()
async def sas(interaction: discord.Interaction):
    author = interaction.user
    logging.info(f'{author.mention} {author.name} использовал команду sas')
    await interaction.response.send_message(f'{author.mention} соси') 

@bot.command(pass_context = True) #только admin
@commands.is_owner()
async def say(ctx):
    await ctx.send('your code...')    

@bot.tree.command(name="count", description="Узнать сколько раз кто-то был послан на хуй")
@slash_command_check()
@app_commands.describe(target='Выберите цель')
async def count(interaction: discord.Interaction, target: discord.Member):
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду count')
        connection = myconnutils.getConnection()
        cursor = connection.cursor(dictionary=True)
        if interaction.user == target:
            member = interaction.user
            cursor.execute(f"SELECT id FROM user WHERE id = {member.id}")
            exist= cursor.fetchone()
            if exist is None:
                embed = discord.Embed(
                    title=(f'Тебя ещё ни разу не посылали нахуй'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await interaction.response.send_message(embed=embed)
            else:    
                cursor.execute(f'SELECT count FROM user WHERE id = {member.id}') 
                count = cursor.fetchone()
                count = count["count"]
                embed = discord.Embed(
                    title=(f'Тебя послали нахуй {count} раз'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await interaction.response.send_message(embed=embed)
            connection.close()
        elif target.id == config['bot_id']:
                embed = discord.Embed(
                    title=(f'Его невозможно послать'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=target.avatar)
                await interaction.response.send_message(embed=embed)        
        else:
            cursor.execute(f"SELECT id FROM user WHERE id = {target.id}")
            exist= cursor.fetchone()
            if exist is None:
                embed = discord.Embed(
                    title=(f'{target.name} ещё ни разу не был послан нахуй '),
                    color=0xff0000
                )
                embed.set_thumbnail(url=target.avatar)
                await interaction.response.send_message(embed=embed)
            else:
                cursor.execute(f'SELECT count FROM user WHERE id = {target.id}') 
                count = cursor.fetchone()
                count = count["count"]
                embed = discord.Embed(
                    title=(f'{target.name} был послан нахуй {count} раз'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=target.avatar)
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="С помощью этой команды можно получить аватарку участников сервера")
@slash_command_check()
@app_commands.describe(target='Выберите цель')
async def avatar(interaction: discord.Interaction, target: discord.Member):
    logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду avatar')
    if target == None:#если не упоминать участника тогда выводит аватар автора сообщения
        target = interaction.user.id
    embed = discord.Embed(color = 0x22ff00, title = f"Аватар участника - {target.name}", description = f"[Нажмите что бы скачать аватар]({target.avatar})")
    embed.set_image(url = target.avatar)
    await interaction.response.send_message(embed = embed)      

@bot.event
async def on_message(message): # при слове "primateking1488" посылае нахуй с упоминанием
    if 'primateking1488' in message.content.lower():
        connection = myconnutils.getConnection()
        cursor = connection.cursor(dictionary=True) 
        cursor.execute(f"SELECT id FROM user WHERE id = {message.author.id}")
        exist = cursor.fetchone()
        
        if exist is None:
            val = (message.author.name, message.author.id, 1, "0")
            sql = (f"INSERT INTO `user` (name, id , count, admin) VALUES {val}")
            cursor.execute(sql)
            connection.commit()
            await message.channel.send(f'{message.author.mention} Пошёл нахуй!')
        else:
            cursor.execute(f'SELECT count FROM user WHERE id = {message.author.id}')
            count = cursor.fetchone()
            count = count["count"]
            plus = 1
            sql = ("UPDATE `user` SET count = %s WHERE id = %s")
            val = (count + int(plus), message.author.id)
            cursor.execute(sql,val)
            connection.commit()
            await message.channel.send(f'{message.author.mention} Пошёл нахуй!')
        connection.close()
    await bot.process_commands(message)


@bot.tree.command(name="poslat", description="Можно полать кого то на хуй")
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
        connection = myconnutils.getConnection()
        cursor = connection.cursor(dictionary=True)         
        sql_reality = f"SELECT id FROM user WHERE id = {target_id}"
        cursor.execute(sql_reality)
        exist = cursor.fetchone()
        if exist is None:
            val = (target_name, target_id, 1, "0")
            sql = (f"INSERT INTO `user` (name, id , count, admin) VALUES {val}")
            cursor.execute(sql)
            connection.commit()
            embed = discord.Embed(title=f"{target.name} был послан нахуй",
                        description=f"{target.mention} тебя послал {interaction.user.mention}",
                        color=0xff0000)  # Embed
            embed.set_thumbnail(url=interaction.user.avatar)
            #await ctx.channel.send(f"{ctx.author.mention} послал {member.mention}") 
            await interaction.response.send_message(embed=embed) 
        else:
            cursor.execute(f'SELECT count FROM user WHERE id = {target_id}')
            count = cursor.fetchone()
            count = count["count"]
            plus = 1
            count = count + int(plus)
            sql = (f"UPDATE `user` SET count = {count} WHERE id = {target_id}")
            cursor.execute(sql)
            connection.commit()   
            embed = discord.Embed(title=f"{target.name} был послан нахуй",
                        description=f"{target.mention} тебя послал {interaction.user.mention}",
                        color=0xff0000)  # Embed
            embed.set_thumbnail(url=interaction.user.avatar)
            await interaction.response.send_message(embed=embed)
            connection.close() 

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
        client_ssh.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
        stdin, stdout, stderr = client_ssh.exec_command('systemctl restart botdis.service')
        data = stdout.read().decode()
        stdin.close()
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
    await interaction.response.defer(ephemeral=True)  # <-- добавляем defer сразу

    if interaction.user.id == config['admin']:
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду update')
        send_telegram_notification(
            f"\u2705 *Успех:* {interaction.user.mention} ({interaction.user.name}) использовал команду /update"
        )

        client_ssh.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
        stdin, stdout, stderr = client_ssh.exec_command('cd PrimateKing-bot \n git pull')
        data = stdout.read().decode()
        stdin.close()

        await interaction.followup.send(  # <- send через followup после defer
            f'Эй {interaction.user.mention}! Вот результат:\n```bash\n{data}\n```',
            ephemeral=True
        )

    else:
        logging.info(f'{interaction.user.mention} {interaction.user.name} попытался использовать команду update')
        send_telegram_notification(
            f"\u26a0 *Попытка доступа:* {interaction.user.mention} ({interaction.user.name}) попытался использовать команду /update без прав."
        )

        await interaction.followup.send(  # тоже через followup
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
            # Форматируем имя команды
            if cmd['type'] == 'slash':
                display_name = f"/{cmd['name'].lstrip('/')}"
            else:
                display_name = cmd['name']  # Префикс уже в базе

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
        # Выполнение функции отправки сообщения
        await interaction.response.defer()
        answer = await yandexgpt.yandexgpt(user_input)
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
        gpt_img = await yandexgptart.generate_and_save_image(user_input, user)
        embed = discord.Embed(
            title="Сгенерированное изображение",
            description="Вот изображение, созданное на основе вашего запроса:",
            color=discord.Color.blue()
        )
        embed.set_image(url=gpt_img)
        view = ImageView(image_url=gpt_img, prompt=user_input)
        await interaction.followup.send(embed=embed, view=view)
        bot.add_view(view)  # Регистрируем view для постоянного отслеживания
    except ValueError as ve:
        await interaction.followup.send(f'Ошибка при получении URL изображения: {str(ve)}', ephemeral=True)
        logging.error(str(ve))
    except Exception as e:
        from yandexgptart import translate_yandex_error  # если функция в другом файле
        translated = translate_yandex_error(str(e))
        await interaction.followup.send(f'❗ {translated}', ephemeral=True)
        logging.error(f"Ошибка YandexGPT ART: {str(e)}")

async def check_image(url: str) -> bool:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logging.error(f"Ошибка при проверке изображения: {e}")
            return False


# Функция, отправки сообщения
async def send_blin(target_user: discord.User, channel: discord.TextChannel, user: discord.User, text: Optional[str] = None):
    logging.info(f'Выполнение функции send_blin начато')
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
        if ValueError:
            logging.error(f'Картинка блина по URL {image_url} не доступна')
        else:
            logging.error("Ошибка при выполнении функции send_blin ", exc_info=True)
        raise
        
    logging.info(f'Функция send_blin выполнена')

@bot.tree.command(name="send_blin", description="Отправить блин с говном")
@slash_command_check()
@app_commands.describe(target='Выберите цель')
@app_commands.describe(text='Сообщение под картинкой. Необязательно')
async def send_message_command(interaction: discord.Interaction, target: discord.User, text: Optional[str] = None):
    if text:
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду send_blin. Цель: {target.mention} {target.name}. Сообщение {text}')
    else:
        logging.info(f'{interaction.user.mention} {interaction.user.name} использовал команду send_blin. Цель: {target.mention} {target.name}')
    # Получение канала, откуда была вызвана команда
    channel = interaction.channel
    user = interaction.user

    try:
        # Выполнение функции отправки сообщения
        await send_blin(target, channel, user, text)
        await interaction.response.send_message(f'Посылка для {target.mention} доставлена', ephemeral=True)
    except ValueError as e:
        await interaction.response.send_message(f'Ошибка: {e}', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'Произошла ошибка при отправке блина', ephemeral=True)
        logging.error(f'Произошла ошибка: {e}')

    logging.info(f'Комманда send_blin выполнена')

async def on_message_gifs(message):
    if message.author == bot.user:
        return  # Игнорируем сообщения бота

    # Проверяем ссылки в тексте сообщения
    for gif_url in GIF_URLS:
        if gif_url in message.content:
            await message.reply(gif_url)
            return

    # Проверяем вложенные файлы
    for attachment in message.attachments:
        if attachment.url.endswith(".gif") and attachment.url in GIF_URLS:
            await message.reply(attachment.url)
            return

    await bot.process_commands(message)
decorated_on_message = function_enabled_check("on_message_gifs")(on_message_gifs)
bot.add_listener(decorated_on_message, "on_message")


# Функция для отправки уведомлений в Telegram
def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    formatted_message = (
        f"📢 **Уведомление бота**\n\n"
        f"{message}\n\n"
        f"_Время уведомления: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
    )
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": formatted_message,
        "parse_mode": "Markdown",
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        logging.error(f"Ошибка отправки сообщения в Telegram: {response.status_code} - {response.text}")

# Функция для получения команд из базы
def get_commands_from_api():
    try:
        url = f"{API_URL}/bot/items"
        response = requests.get(url)
        response.raise_for_status()
        
        commands_dict = {}
        for item in response.json():
            # Убираем префиксы для ключей словаря
            clean_name = item['name']
            if item['type'] == 'prefix':
                clean_name = clean_name.lstrip('$')
            elif item['type'] == 'function':
                clean_name = clean_name.removeprefix('func_')
            
            commands_dict[(item['type'], clean_name)] = {
                'status': item.get('enabled', False),
                'description': item.get('description', '')
            }
        return commands_dict
    except Exception as e:
        logging.error(f"API Error: {str(e)}")
        return {}


# Функция для парсинга команд и функций
def parse_commands_and_functions():
    try:
        response = requests.get(f"{API_URL}/bot/commands")
        api_data = response.json()
        # Преобразуем в словарь для быстрого поиска
        api_commands = {
            (item['type'], item['name']): item 
            for item in api_data
        }
    except Exception as e:
        logging.error(f"API error: {e}")
        api_commands = {}

    commands_list = []

    # Обработка слэш-команд
    for command in bot.tree.walk_commands():
        if isinstance(command, discord.app_commands.Command):
            key = ('slash', command.name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': command.name,
                'type': 'slash',
                'enabled': api_entry.get('enabled', True),
                'description': command.description or ''
            })

    # Обработка префиксных команд
    for command in bot.commands:
        if isinstance(command, commands.Command):
            # Убираем префикс, если он есть
            clean_name = command.name.lstrip('$')
            key = ('prefix', clean_name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': f'${clean_name}',
                'type': 'prefix',
                'enabled': api_entry.get('enabled', True),
                'description': command.help or ''
            })

    # Обработка функций (если есть)
    for func_name, func in globals().items():
        if inspect.isfunction(func) or inspect.iscoroutinefunction(func):
            # Если имя функции начинается с "func_", убираем этот префикс
            clean_name = func_name.removeprefix('func_')
            key = ('function', clean_name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': f'func_{clean_name}',
                'type': 'function',
                'enabled': api_entry.get('enabled', True),
                'description': func.__doc__.strip() if func.__doc__ else ''
            })

    return commands_list

# Функция для отправки команд в API
def send_commands_to_api():
    url = f"{API_URL}/bot/items"
    headers = {"Content-Type": "application/json"}

    try:
        commands_list = parse_commands_and_functions()
    except Exception as e:
        logging.error("parse_commands_and_functions() failed: %s", e, exc_info=True)
        return

    # Получаем существующие команды
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        existing_commands = {item["name"] for item in resp.json()}
    except Exception as e:
        logging.warning("API %s недоступен: %s — пропускаю синхронизацию.", url, e)
        return

    # Фильтруем новые
    new_commands = [
        {
            "name": cmd['name'],
            "type": cmd['type'],
            "enabled": cmd.get('enabled', True),
            "description": cmd.get('description', '')
        }
        for cmd in commands_list
        if cmd["name"] not in existing_commands
    ]

    if not new_commands:
        logging.info("Нет новых команд для отправки в API.")
        return

    # Отправляем новые
    try:
        resp = requests.post(url, json=new_commands, headers=headers, timeout=10)
        resp.raise_for_status()
        logging.info("Команды успешно отправлены в API (%d шт).", len(new_commands))
    except Exception as e:
        logging.error("Не удалось отправить команды в API: %s", e)
        logging.debug("Payload отправки: %s", new_commands)

@bot.check
async def global_command_check(ctx: commands.Context):
    if ctx.interaction:  # Слэш-команды обрабатываются отдельно
        return True

    try:
        response = requests.get(f"{API_URL}/bot/commands/prefix/{ctx.command.name}")
        if response.status_code == 200:
            data = response.json()
            if not data['enabled']:
                await ctx.reply("🚫 Эта команда временно отключена")
                return False
        return True
    except Exception as e:
        logging.error(f"Command check error: {e}")
        return True


@bot.tree.error
async def on_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "🚫 Эта команда временно отключена",
            ephemeral=True
        )
    else:
        logging.error(f"Slash error: {error}")

@poslat.error
async def info_error(ctx, error): # если $послать юзер не найден
    if isinstance(error, commands.BadArgument):
        await ctx.reply('Такого долбоёба нет на сервере')


@count.error
async def info_error(ctx, error): # если $послать юзер не найден
    if isinstance(error, commands.BadArgument):
        await ctx.reply('Такого долбоёба нет на сервере')

@bot.command() #комманда без проверки роли
async def testo(ctx, *arg):
    await ctx.reply(random.randint(1000, 2000))

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return

    log_channel = bot.get_channel(1396859532222660789)
    if not log_channel:
        logging.warning("Не удалось найти канал логов удалённых сообщений.")
        return

    # Информация
    author_info = f"{message.author} (ID: {message.author.id})"
    channel_info = f"#{message.channel.name} (ID: {message.channel.id})"
    created_info = str(message.created_at)
    message_id = message.id
    attachments = "\n               ".join([att.url for att in message.attachments]) if message.attachments else "Нет"
    text = message.content or ""

    # Создаём embed
    embed = discord.Embed(
        title="🗑️ Сообщение удалено",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Автор", value=author_info, inline=False)
    embed.add_field(name="Канал", value=channel_info, inline=False)
    embed.add_field(name="Вложения", value=attachments, inline=False)
    embed.set_footer(text=f"ID сообщения: {message_id}")

    # 1. Короткое сообщение — в embed
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

    # 2. Длинное сообщение — embed + txt в отдельном сообщении
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

    # 3. Сообщение без текста
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

bot.run(config['token'])