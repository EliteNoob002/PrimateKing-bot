import random
import mysql.connector
import bestconfig
import discord
from discord.ext import commands
from bestconfig import Config
import logging
from discord import app_commands
import myconnutils
import paramiko 

logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
logging.debug("A DEBUG Message")
logging.info("An INFO")
logging.warning("A WARNING")
logging.error("An ERROR")
logging.critical("A message of CRITICAL severity")

description = '''PrimateKing'''

config = Config() #config['version']


intents = discord.Intents.default() # Подключаем "Разрешения"
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


host_ssh = config['host_ssh']
user_ssh = config['user_ssh']
secret_ssh = config['password_ssh']
port_ssh = config['port_ssh']

connection = myconnutils.getConnection()    

cursor = connection.cursor(dictionary=True) 

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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

#@bot.command()
#async def set(ctx):
#    val = (ctx.author.name, ctx.author.id, "0", "0")
#    sql = (f"INSERT INTO `user` (name, id , count, admin) VALUES {val}")
#    cursor.execute(sql)
#    mydb.commit()
#    await ctx.reply('done')

@bot.tree.command(name="test", description="Тестовая слеш команда")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f' Эй {interaction.user.mention}! Это тестовая слеш команда',
    ephemeral=True)

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

@bot.tree.command(name="sas", description="тестовый sas")
async def sas(interaction: discord.Interaction):
    author = interaction.user
    await interaction.response.send_message(f'{author.mention} соси') 

@bot.command(pass_context = True) #только admin
@commands.is_owner()
async def say(ctx):
    await ctx.send('your code...')    

@bot.command()
async def count(ctx, member: discord.Member  = None):
        if member == None:
            member = ctx.author
            cursor.execute(f"SELECT id FROM user WHERE id = {member.id}")
            exist= cursor.fetchone()
            if exist is None:
                embed = discord.Embed(
                    title=(f'Тебя ещё ни разу не посылали нахуй'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await ctx.reply(embed=embed)
            else:    
                cursor.execute(f'SELECT count FROM user WHERE id = {member.id}') 
                count = cursor.fetchone()
                count = count["count"]
                embed = discord.Embed(
                    title=(f'Тебя послали нахуй {count} раз'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await ctx.reply(embed=embed)
            connection.close()
        elif member.id == config['bot_id']:
                embed = discord.Embed(
                    title=(f'Его невозможно послать'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await ctx.reply(embed=embed)        
        else:
            cursor.execute(f"SELECT id FROM user WHERE id = {member.id}")
            exist= cursor.fetchone()
            if exist is None:
                embed = discord.Embed(
                    title=(f'{member.name} ещё ни разу не был послан нахуй '),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await ctx.reply(embed=embed)
            else:
                cursor.execute(f'SELECT count FROM user WHERE id = {member.id}') 
                count = cursor.fetchone()
                count = count["count"]
                embed = discord.Embed(
                    title=(f'{member.name} был послан нахуй {count} раз'),
                    color=0xff0000
                )
                embed.set_thumbnail(url=member.avatar)
                await ctx.reply(embed=embed)
            connection.close()

@bot.command()
async def avatar(ctx, member: discord.Member  = None):
    if member == None:#если не упоминать участника тогда выводит аватар автора сообщения
        member = ctx.author
    embed = discord.Embed(color = 0x22ff00, title = f"Аватар участника - {member.name}", description = f"[Нажмите что бы скачать аватар]({member.avatar})")
    embed.set_image(url = member.avatar)
    await ctx.send(embed = embed)      

@bot.event
async def on_message(message): # при слове "primateking1488" посылае нахуй с упоминанием
    if 'primateking1488' in message.content.lower():
        cursor.execute(f"SELECT id FROM user WHERE id = {message.author.id}")
        exist = cursor.fetchone()
        
        if exist is None:
            val = (message.author.name, message.author.id, "1", "0")
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
    await bot.process_commands(message)

@bot.command()
async def posl(ctx, member: discord.Member = None):
    target_id = member.id
    target_name = member.name
    if member == None:
            await ctx.reply('Еблан, ты никого не указал')
    elif member.id == config['bot_id']:
            embed = discord.Embed(
                title=(f'Не был послан нахуй'),
                description=f"{ctx.author.mention} себя пошли нахуй",
                color=0xff0000
            )
            embed.set_thumbnail(url=ctx.author.avatar)
            await ctx.reply(embed=embed) 
    else:
        cursor.execute(f"SELECT id FROM user WHERE id = {target_id}")
        exist = cursor.fetchone()
        if exist is None:
            val = (target_name, target_id, "1", "0")
            sql = (f"INSERT INTO `user` (name, id , count, admin) VALUES {val}")
            cursor.execute(sql)
            connection.commit()
            embed = discord.Embed(title=f"Вы были посланы нахуй",
                        description=f"{member.mention} тебя послал {ctx.author.mention}",
                        color=0xff0000)  # Embed
            embed.set_thumbnail(url=ctx.author.avatar)
            #await ctx.channel.send(f"{ctx.author.mention} послал {member.mention}") 
            await ctx.send(embed=embed) 
        else:
            cursor.execute(f'SELECT count FROM user WHERE id = {target_id}')
            count = cursor.fetchone()
            count = count["count"]
            plus = 1
            count = count + int(plus)
            sql = (f"UPDATE `user` SET count = {count} WHERE id = {target_id}")
            cursor.execute(sql)
            connection.commit()   
            embed = discord.Embed(title=f"Вы были посланы нахуй",
                        description=f"{member.mention} тебя послал {ctx.author.mention}",
                        color=0xff0000)  # Embed
            embed.set_thumbnail(url=ctx.author.avatar)
            await ctx.send(embed=embed) 
        connection.close()

@bot.tree.command(name="restartbot", description="Перезапуск бота")
@commands.is_owner()
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message(f' Эй {interaction.user.mention}! Команда на перезапуск бота отправелена',
    ephemeral=True) 
    client.connect(hostname=host_ssh, username=user_ssh, password=secret_ssh, port=port_ssh)
    stdin, stdout, stderr = client.exec_command('systemctl restart botdis.service')
    data = stdout.read().decode()
    stdin.close()
       

@posl.error
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