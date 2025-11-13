import requests
import json
import yaml
import logging
import asyncio

with open("config.yaml", encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader,)

async def yandexgpt(user_input):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    data = {
                "modelUri": f"gpt://{config['folder_id']}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": config['api_tokens']  # Используем числовое значение, а не строку
                },
                "messages": [
                    {
                        "role": "system",
                        "text": "Ты дружелюбный помощник, но запрос одноразовый и тебе не смогут ответить"
                    },
                    {
                        "role": "user",
                        "text": user_input
                    }
                ]
    }

    headers = {
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {config['yandex_api_key']}",
                "x-folder-id": f"{config['folder_id']}"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            answer_nonformat = response.json()
            answer = answer_nonformat['result']['alternatives'][0]['message']['text']
            return answer
        else:
            logging.error(f"Ошибка POST запроса yandexgptapi. Код ошибки: {response.status_code}, Текст: {response.text}")
            answer = f'Ошибка запроса YandexGPTApi'
            return answer


    except Exception as e:
        logging.error("Ошибка функции yandexgpt ", e)