"""Генерация изображений через Yandex GPT Art"""
import aiohttp
import base64
import asyncio
import logging
import random
from datetime import datetime
import os
from utils.config import load_config
from utils.errors import translate_yandex_error

config = load_config()

url_generate = "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {config['yandex_api_key']}"
}

async def post_image_generation(session, user_input):
    """Отправляет запрос на генерацию изображения"""
    data = {
        "modelUri": f"art://{config['folder_id']}/yandex-art/latest",
        "generationOptions": {
            "seed": str(random.randint(0, 2**63 - 1)),
            "aspectRatio": {
                "widthRatio": "1",
                "heightRatio": "1"
            }
        },
        "messages": [
            {
                "weight": "1",
                "text": user_input
            }
        ]
    }

    async with session.post(url_generate, headers=headers, json=data) as response:
        response_json = await response.json()

        if response.status == 200:
            answer_id = response_json["id"]
            logging.info(f'id запроса для генерации картинки получен')
            return answer_id
        elif 'error' in response_json:
            error_text = response_json['error']
            logging.warning(f'Ошибка генерации изображения: {error_text}')
            raise Exception(error_text)
        else:
            logging.error(f"Неизвестная ошибка: {response.status}, Тело: {await response.text()}")
            raise Exception("Неизвестная ошибка при генерации изображения")

async def fetch_operation_status(session, operation_id):
    """Проверяет статус операции генерации"""
    url_get = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
    async with session.get(url_get, headers=headers) as response:
        if response.status == 200:
            try:
                data = await response.json()
                if 'response' in data and 'image' in data['response']:
                    logging.info(f'Данные по сгенерированной картинке получены')
                    return data['response']['image']
                else:
                    return None
            except ValueError:
                logging.error("Ответ не является допустимым JSON.")
                return None
        else:
            logging.error(f'Ошибка при выполнении запроса: {response.status}', await response.text())
            return None

async def save_image(image_base64, user):
    """Сохраняет изображение во временную папку"""
    image_data = base64.b64decode(image_base64)
    date = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f'gpt_img_temp/{user}_{date}.jpeg'
    os.makedirs('gpt_img_temp', exist_ok=True)
    with open(image_path, 'wb') as file:
        file.write(image_data)
    logging.info(f'Сгенерированная картинка успешно сохранена')
    return image_path

async def upload_to_server(file_path, user):
    """Загружает изображение на сервер"""
    url = f"{config['upload_url']}"
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as file:
            original_filename = os.path.basename(file_path)
            data = aiohttp.FormData()
            data.add_field('files', file, filename=original_filename)
            data.add_field('UploadBy', user)
            data.add_field('BotUpload', 'true')
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    file_url = response_data.get('file_url')
                    logging.info(f'Файл {file_url} сохранен на сервере')
                    return file_url
                else:
                    logging.error(f'Ошибка при загрузке файла на сервер. Код ошибки: {response.status}')
                    return False

async def generate_and_save_image(user_input, user):
    """Генерирует изображение и сохраняет его на сервере"""
    async with aiohttp.ClientSession() as session:
        operation_id = await post_image_generation(session, user_input)
        
        while True:
            image_base64 = await fetch_operation_status(session, operation_id)
            if image_base64:
                image_path = await save_image(image_base64, user)
                image_url = await upload_to_server(image_path, user)

                if not image_url:
                    raise ValueError("Возникла ошибка при получении URL изображения")

                os.remove(image_path)
                return image_url
            else:
                await asyncio.sleep(10)

