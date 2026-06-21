"""Настройка прокси для Discord"""

import asyncio
import logging

import aiohttp
import discord.http as dhttp
import discord.webhook.async_ as dwh_async
from aiohttp import BasicAuth

from utils.bootstrap_settings import load_bootstrap_settings

proxy = None
proxy_auth = None


def setup_proxy():
    """Настраивает прокси для всех Discord запросов"""
    global proxy, proxy_auth

    settings = load_bootstrap_settings()

    if settings.discord_proxy_enabled:
        proxy = settings.discord_proxy_url
        user = settings.discord_proxy_user
        pwd = settings.discord_proxy_pass
        if user and pwd and proxy and "@" not in proxy:
            proxy_auth = BasicAuth(user, pwd)

    _orig_wh_request = dwh_async.AsyncWebhookAdapter.request

    async def _proxied_wh_request(self, route, *args, **kwargs):
        if proxy:
            kwargs["proxy"] = proxy
            if proxy_auth:
                kwargs["proxy_auth"] = proxy_auth
        return await _orig_wh_request(self, route, *args, **kwargs)

    dwh_async.AsyncWebhookAdapter.request = _proxied_wh_request

    _orig_request = dhttp.HTTPClient.request

    async def _proxied_request(self, route, **kwargs):
        kwargs["timeout"] = kwargs.get("timeout") or aiohttp.ClientTimeout(total=70, connect=60, sock_connect=60, sock_read=60)

        if proxy:
            kwargs["proxy"] = proxy
            if proxy_auth:
                kwargs["proxy_auth"] = proxy_auth

        attempt = 0
        last_exc = None
        while attempt < 3:
            attempt += 1
            logging.debug(
                "REST %s %s proxy=%s attempt=%s",
                route.method,
                route.url,
                kwargs.get("proxy"),
                attempt,
            )
            try:
                return await _orig_request(self, route, **kwargs)
            except (
                aiohttp.ClientConnectorError,
                aiohttp.ServerDisconnectedError,
                asyncio.TimeoutError,
                aiohttp.ClientOSError,
            ) as e:
                last_exc = e
                logging.error("Discord HTTP error on %s %s: %r", route.method, route.url, e)
                await asyncio.sleep(min(5 * attempt, 10))
            except Exception:
                logging.exception("Discord HTTP fatal on %s %s", route.method, route.url)
                raise
        raise last_exc

    dhttp.HTTPClient.request = _proxied_request

    _orig_ws_connect = dhttp.HTTPClient.ws_connect

    async def _proxied_ws_connect(self, url, **kwargs):
        kwargs["autoping"] = True
        kwargs["heartbeat"] = 30.0
        kwargs["timeout"] = aiohttp.ClientWSTimeout(ws_close=60.0, ws_receive=75.0)

        if proxy:
            kwargs["proxy"] = proxy
            if proxy_auth:
                kwargs["proxy_auth"] = proxy_auth

        try:
            session = getattr(self, "_HTTPClient__session", None)
            if isinstance(session, aiohttp.ClientSession):
                return await session.ws_connect(url, **kwargs)
            return await _orig_ws_connect(self, url, **kwargs)
        except Exception:
            logging.exception("Discord WS error connect to %s", url)
            raise

    dhttp.HTTPClient.ws_connect = _proxied_ws_connect


def get_proxy():
    """Возвращает прокси и auth для использования в других модулях"""
    return proxy, proxy_auth
