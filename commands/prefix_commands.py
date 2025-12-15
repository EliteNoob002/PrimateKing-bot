"""Prefix команды бота"""
import discord
from discord.ext import commands
import random
import logging

from services.ssh import execute_ssh_command

def setup_prefix_commands(bot):
    """Регистрирует все prefix команды"""
    
    @bot.command()
    @commands.has_role("Тест1")
    async def teste(ctx, *arg):
        data = execute_ssh_command('ls -l \n')
        await ctx.reply(f'Ответ ssh: {data}')

    @bot.command()
    @commands.has_role("Тест2")
    async def testl(ctx, *arg):
        await ctx.reply(random.randint(100, 200))

    @bot.command(pass_context=True)
    @commands.is_owner()
    async def say(ctx):
        await ctx.send('your code...')

    @bot.command()
    async def testo(ctx, *arg):
        await ctx.reply(random.randint(1000, 2000))

