import random
import discord
from discord.ext import commands

intents = discord.Intents.default() # Подключаем "Разрешения"
intents.message_content = True

config = {
    'token': '',
    'prefix': '$',
}

bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

@bot.command()
@commands.has_role("Тест1") #команда teste с проверкой роли "тест1"
async def teste(ctx, *arg):
    await ctx.reply(random.randint(0, 105))

@bot.command()
@commands.has_role("Тест2")
async def testl(ctx, *arg):
    await ctx.reply(random.randint(100, 200))    

@bot.command() #комманда без проверки роли
async def testo(ctx, *arg):
    await ctx.reply(random.randint(1000, 2000))    

bot.run(config['token'])