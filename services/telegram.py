"""Уведомления в Telegram"""
import requests
import logging
from datetime import datetime
from utils.config import get_config

TG_BOT_TOKEN = get_config('tg_bot_token')
TG_CHAT_ID = get_config('tg_chat_id')

def send_telegram_notification(message):
    """Отправляет уведомление в Telegram"""
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

