import random
import discord
from discord.ext import commands
import yaml
import logging
from discord import app_commands
import myconnutils
import paramiko
from asyncio import sleep 
from discord_webhook import DiscordWebhook
import openai
import asyncio


logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
logging.debug("A DEBUG Message")
logging.info("An INFO")
logging.warning("A WARNING")
logging.error("An ERROR")
logging.critical("A message of CRITICAL severity")

description = '''PrimateKing'''

with open("config.yml", encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader,)


intents = discord.Intents.default() # Подключаем "Разрешения"
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


host_ssh = config['host_ssh']
user_ssh = config['user_ssh']
secret_ssh = config['password_ssh']
port_ssh = config['port_ssh']

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Подключение к API OpenAI
openai.api_key = config['openai_key']

bot = commands.Bot(command_prefix=config['prefix'], owner_id=config['admin'] , intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)
    print('------')
    webhook1 = DiscordWebhook(url=config['webhook_dev'], content=f'Бот {bot.user} запущен')
    response = webhook1.execute()
    webhook2 = DiscordWebhook(url=config['webhook_pk'], content=f'Бот {bot.user} запущен')
    response = webhook2.execute()
    while True:
        try:
            await bot.change_presence(status = discord.Status.online, activity = discord.Activity(name = random.choice(config['status_playing']), type = discord.ActivityType.playing))
            await sleep(config['time_sleep'])
            await bot.change_presence(status = discord.Status.online, activity = discord.Activity(name = random.choice(config['status_watching']), type = discord.ActivityType.watching))
            await sleep(config['time_sleep'])
            await bot.change_presence(status = discord.Status.online, activity = discord.Activity(name = random.choice(config['status_listening']), type = discord.ActivityType.listening))
            await sleep(config['time_sleep'])
        except Exception as e:
            logging.critical("Что-то отъебнуло в статусах ", e)

@bot.command()
@commands.has_role("Тест1") #команда teste с проверкой роли "тест1"
async def teste(ctx, *arg):
    client.connect(hostname=config['host_ssh'], username=config['user_ssh'], password=config['password_ssh'], port=config['port'])
    stdin, stdout, stderr = client.exec_command('ls -l \n')
    data = stdout.read() + stderr.read()
    client.close()
    await ctx.reply(f'Ответ ssh: {data}')

@bot.command()
@commands.has_role("Тест2")
async def testl(ctx, *arg):
    await ctx.reply(random.randint(100, 200)) 

@bot.tree.command(name="sas", description="Хочешь посасать?")
async def sas(interaction: discord.Interaction):
    author = interaction.user
    await interaction.response.send_message(f'{author.mention} соси') 

@bot.command(pass_context = True) #только admin
@commands.is_owner()
async def say(ctx):
    await ctx.send('your code...')    

@bot.tree.command(name="count", description="Узнать сколько раз кто-то был послан на хуй")
@app_commands.describe(target='Выберите цель')
async def count(interaction: discord.Interaction, target: discord.Member):
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
@app_commands.describe(target='Выберите цель')
async def avatar(interaction: discord.Interaction, target: discord.Member):
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
@app_commands.describe(target='Выберите цель')
async def poslat(interaction: discord.Interaction, target: discord.Member):
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
async def restart(interaction: discord.Interaction):
    if interaction.user.id == config['admin']:
        await interaction.response.send_message(f' Эй {interaction.user.mention}! Команда на перезапуск бота отправлена',
        ephemeral=True) 
        client.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
        stdin, stdout, stderr = client.exec_command('systemctl restart botdis.service')
        data = stdout.read().decode()
        stdin.close()
    else:
        await interaction.response.send_message(f'У тебя нет доступа к этой команде',
        ephemeral=True) 

@bot.tree.command(name="update", description="Обновление файлов бота")
async def update(interaction: discord.Interaction):
    if interaction.user.id == config['admin']:
        client.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
        stdin, stdout, stderr = client.exec_command('cd PrimateKing-bot \n git pull')
        data = stdout.read().decode()
        stdin.close()
        await interaction.response.send_message(f' Эй {interaction.user.mention}! Вот результат {data}',
        ephemeral=True) 
    else:
        await interaction.response.send_message(f'У тебя нет доступа к этой команде',
        ephemeral=True)

@bot.tree.command(name="help", description="Список доступных команд")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(color = 0x22ff00, title = f"Список доступных команд", description = f"/poslat - Послать кого-то на хуй \n /count - Узнать сколько раз кто-то был послан \n /avatar - Получить аватарку участиника сервера\n /sas - Бот предложит отсасать \n /help - Получить информацию о командах")
    #embed.set_image(url = '')
    await interaction.response.send_message(embed = embed)  

@bot.tree.command(name="gpt", description="GPT Запрос")
@app_commands.describe(user_input='Введите запрос')
async def gpt(interaction: discord.Interaction, user_input: str):

    # Генерация ответа с помощью GPT модели
    await interaction.response.defer()
    # Определите параметры запроса для GPT модели
    prompt = f"User: {user_input}\nAI: "
    temperature = 1  # Параметр температуры для вариации ответов
    
    # Запрос к GPT модели
    response = openai.Completion.create(
        engine='text-davinci-003',
        prompt=prompt,
        max_tokens= 2000,
        temperature=temperature,
        n=1,
        stop=None
    )
    await asyncio.sleep(4)
    # Извлечение ответа из ответа модели
    model_response = response.choices[0].text.strip()
    # Отправка ответа в тот же канал
    await interaction.followup.send(model_response)  


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

bot.run(config['token'])