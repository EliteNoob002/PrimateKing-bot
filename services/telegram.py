"""Уведомления в Telegram"""

import asyncio
import html
import logging
import ssl
import time
from datetime import datetime
from functools import partial
from typing import Optional
from urllib.parse import quote, urlparse, urlunparse

import requests

from utils.bootstrap_settings import load_bootstrap_settings
from utils.proxy import get_proxy

_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 15
_REQUEST_TIMEOUT = (_CONNECT_TIMEOUT, _READ_TIMEOUT)

_API_ALERT_THROTTLE_SEC = 900.0
_last_api_alert_at: dict[str, float] = {}


def _requests_proxies() -> Optional[dict[str, str]]:
    settings = load_bootstrap_settings()
    if not settings.discord_proxy_enabled:
        return None
    proxy_url, proxy_auth = get_proxy()
    if not proxy_url:
        return None
    if proxy_auth is not None:
        p = urlparse(proxy_url)
        user = quote(proxy_auth.login, safe="")
        password = quote(proxy_auth.password or "", safe="")
        host = p.hostname or ""
        netloc = f"{user}:{password}@{host}"
        if p.port:
            netloc += f":{p.port}"
        proxy_for_requests = urlunparse((p.scheme, netloc, p.path or "", p.params, p.query, p.fragment))
    else:
        proxy_for_requests = proxy_url
    return {"http": proxy_for_requests, "https": proxy_for_requests}


def _tg_credentials_ok() -> bool:
    settings = load_bootstrap_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logging.debug("Telegram: пропуск — не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False
    return True


def _format_notification_html(title: str, body_lines: list[str]) -> str:
    safe_title = html.escape(title)
    safe_body = "\n".join(html.escape(line) for line in body_lines)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"<b>{safe_title}</b>\n\n{safe_body}\n\n<i>Время: {html.escape(now)}</i>"


def _post_html_message(html_text: str) -> None:
    if not _tg_credentials_ok():
        return
    settings = load_bootstrap_settings()
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    proxies = _requests_proxies()
    try:
        response = requests.post(
            url,
            json=payload,
            proxies=proxies,
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            logging.debug("Telegram: сообщение отправлено")
        else:
            logging.error(
                "Telegram: HTTP %s — %s",
                response.status_code,
                response.text[:800],
            )
    except requests.RequestException as exc:
        logging.error("Telegram: ошибка запроса: %s", exc, exc_info=True)


def send_telegram_notification(message: str, *, title: str = "Уведомление бота") -> None:
    """Синхронная отправка: message и title трактуются как обычный текст (экранируются)."""
    text = _format_notification_html(title, [message])
    _post_html_message(text)


def _hint_for_exception(exc: BaseException) -> str:
    text = str(exc)
    low = text.lower()
    if "certificate verify failed" in low or "certificate has expired" in low:
        return "Подсказка: проверьте срок действия SSL-сертификата на хосте панели API."
    if isinstance(exc, ssl.SSLError) or "ssl" in low:
        return "Подсказка: ошибка TLS/SSL при обращении к панели."
    if "timeout" in low or "timed out" in low:
        return "Подсказка: таймаут сети до панели."
    if "connection refused" in low or "name or service not known" in low:
        return "Подсказка: хост недоступен или DNS не резолвится."
    return "Подсказка: проверьте доступность API, прокси и маршрут до панели."


def notify_api_panel_unreachable(
    context: str,
    name: str,
    exc: BaseException,
    api_base_url: str,
    *,
    throttle_seconds: float = _API_ALERT_THROTTLE_SEC,
) -> None:
    """Одно уведомление в Telegram на ключ не чаще чем раз в throttle_seconds."""
    key = f"{context}:{name}"
    now = time.monotonic()
    prev = _last_api_alert_at.get(key, 0.0)
    if now - prev < throttle_seconds:
        logging.debug("API alert throttled: %s", key)
        return
    _last_api_alert_at[key] = now

    hint = _hint_for_exception(exc)
    err_line = f"{type(exc).__name__}: {exc}"
    lines = [
        f"Контекст: {context}",
        f"Имя: {name}",
        f"Панель: {api_base_url}",
        f"Ошибка: {err_line}",
        hint,
    ]
    text = _format_notification_html("Панель API: сбой проверки", lines)
    _post_html_message(text)


def _dispatch_in_background(fn) -> None:
    """Запускает синхронную функцию в executor, не блокируя event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        fn()
        return

    async def _runner():
        await loop.run_in_executor(None, fn)

    loop.create_task(_runner())


def schedule_notify_api_panel_unreachable(
    context: str,
    name: str,
    exc: BaseException,
    api_base_url: str,
) -> None:
    """Фоновое троттлированное уведомление о недоступности панели."""
    _dispatch_in_background(
        partial(
            notify_api_panel_unreachable,
            context,
            name,
            exc,
            api_base_url,
        )
    )


async def await_telegram_notification(message: str, *, title: str = "Уведомление бота") -> None:
    """Для slash-команд: дождаться отправки (в executor), не блокируя event loop синхронным requests."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        partial(send_telegram_notification, message, title=title),
    )
