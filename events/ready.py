"""Событие on_ready"""
import asyncio
import logging
import aiohttp
import socket
from utils.config import load_config
from utils.proxy import get_proxy
from services.api_sync import send_commands_to_api
from tasks.status_rotation import create_rotate_status_task

async def _ensure_http_session(client):
    """Обеспечивает наличие HTTP сессии с правильными настройками"""
    sess = getattr(client.http, "_HTTPClient__session", None)
    if (not isinstance(sess, aiohttp.ClientSession)) or getattr(sess, "closed", True):
        connector = aiohttp.TCPConnector(
            family=socket.AF_INET,
            ttl_dns_cache=300,
            force_close=False,
        )
        default_timeout = aiohttp.ClientTimeout(
            total=None,
            connect=60,
            sock_connect=60,
            sock_read=60,
        )
        client.http._HTTPClient__session = aiohttp.ClientSession(
            connector=connector,
            timeout=default_timeout,
        )

async def _post_discord_webhook(url: str, content: str):
    """Отправляет сообщение в Discord webhook"""
    timeout = aiohttp.ClientTimeout(total=8)
    proxy, proxy_auth = get_proxy()
    async with aiohttp.ClientSession(timeout=timeout) as s:
        kw = {}
        if proxy and ("discord.com" in url or "discordapp.com" in url):
            kw["proxy"] = proxy
            if proxy_auth:
                kw["proxy_auth"] = proxy_auth
        await s.post(url, json={"content": content}, **kw)

def setup_ready_event(bot):
    """Регистрирует событие on_ready"""
    
    @bot.event
    async def on_ready():
        await _ensure_http_session(bot)
        print(f'Logged in as {bot.user} (ID: {bot.user.id})')

        # синхронизация команд
        try:
            synced = await bot.tree.sync()
            print(f'Synced {len(synced)} command(s)')
        except Exception as e:
            print(e)
        print('------')

        config = load_config()
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
        rotate_status = create_rotate_status_task(bot)
        if not rotate_status.is_running():
            rotate_status.start()

        async def _sync_api():
            try:
                await asyncio.sleep(1)
                await asyncio.to_thread(send_commands_to_api, bot)
            except Exception:
                logging.exception("Ошибка при синхронизации команд с API")
        asyncio.create_task(_sync_api())

