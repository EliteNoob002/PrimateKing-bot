"""Интеграция с Yandex GPT API"""

import json
import logging

import requests

from services.config_cache import get_global_config_cache
from utils.bootstrap_settings import load_bootstrap_settings


async def yandexgpt(user_input):
    """Отправляет запрос к Yandex GPT API"""
    settings = load_bootstrap_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        logging.error("Yandex GPT не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID")
        return "Yandex GPT не настроен"

    cache = get_global_config_cache()
    max_tokens = cache.get_bot_setting("api_tokens", 500) if cache else 500

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    data = {
        "modelUri": f"gpt://{settings.yandex_folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": max_tokens,
        },
        "messages": [
            {"role": "system", "text": "Ты дружелюбный помощник, но запрос одноразовый и тебе не смогут ответить"},
            {"role": "user", "text": user_input},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            answer_nonformat = response.json()
            answer = answer_nonformat["result"]["alternatives"][0]["message"]["text"]
            return answer
        else:
            logging.error(
                "Ошибка POST запроса yandexgptapi. Код ошибки: %s, Текст: %s",
                response.status_code,
                response.text,
            )
            return "Ошибка запроса YandexGPTApi"

    except Exception as e:
        logging.error("Ошибка функции yandexgpt %s", e)
        return "Ошибка запроса YandexGPTApi"
