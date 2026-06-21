"""Генерация изображений через Yandex GPT Art"""

import asyncio
import base64
import logging
import os
import random
from datetime import datetime

import aiohttp

from services.telegram import schedule_notify_api_panel_unreachable
from utils.bootstrap_settings import load_bootstrap_settings

url_generate = "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync"


def _auth_headers():
    settings = load_bootstrap_settings()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {settings.yandex_api_key}",
    }


async def post_image_generation(session, user_input):
    """Отправляет запрос на генерацию изображения"""
    settings = load_bootstrap_settings()
    data = {
        "modelUri": f"art://{settings.yandex_folder_id}/yandex-art/latest",
        "generationOptions": {"seed": str(random.randint(0, 2**63 - 1)), "aspectRatio": {"widthRatio": "1", "heightRatio": "1"}},
        "messages": [{"weight": "1", "text": user_input}],
    }

    async with session.post(url_generate, headers=_auth_headers(), json=data) as response:
        response_json = await response.json()

        if response.status == 200:
            answer_id = response_json["id"]
            logging.info("id запроса для генерации картинки получен")
            return answer_id
        elif "error" in response_json:
            error_text = response_json["error"]
            logging.warning("Ошибка генерации изображения: %s", error_text)
            raise ValueError(str(error_text))
        else:
            logging.error(f"Неизвестная ошибка: {response.status}, Тело: {await response.text()}")
            raise Exception("Неизвестная ошибка при генерации изображения")


async def fetch_operation_status(session, operation_id):
    """Проверяет статус операции генерации"""
    url_get = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
    async with session.get(url_get, headers=_auth_headers()) as response:
        if response.status == 200:
            try:
                data = await response.json()
                if "response" in data and "image" in data["response"]:
                    logging.info("Данные по сгенерированной картинке получены")
                    return data["response"]["image"]
                else:
                    return None
            except ValueError:
                logging.error("Ответ не является допустимым JSON.")
                return None
        else:
            logging.error(f"Ошибка при выполнении запроса: {response.status}", await response.text())
            return None


async def save_image(image_base64, user):
    """Сохраняет изображение во временную папку"""
    image_data = base64.b64decode(image_base64)
    date = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f"gpt_img_temp/{user}_{date}.jpeg"
    os.makedirs("gpt_img_temp", exist_ok=True)
    with open(image_path, "wb") as file:
        file.write(image_data)
    logging.info("Сгенерированная картинка успешно сохранена")
    return image_path


async def _handle_upload_error(status: int, error_body: dict) -> None:
    """Разбирает envelope ошибки WaifuFiles API и бросает подходящее исключение."""
    settings = load_bootstrap_settings()
    code = error_body.get("code", "")
    message = error_body.get("message", f"HTTP {status}")
    request_id = error_body.get("request_id", "unknown")
    logging.error(
        "Ошибка загрузки файла: HTTP %s, code=%s, message=%s, request_id=%s",
        status,
        code,
        message,
        request_id,
    )

    if status == 410 and code == "endpoint_removed":
        logging.error(
            "Конфигурационная ошибка: бот вызывает удалённый POST /upload (request_id=%s)",
            request_id,
        )
        raise RuntimeError("Конфигурационная ошибка: устаревший URL загрузки файлов.")

    if status in (401, 403):
        exc = RuntimeError(f"{code}: {message} (request_id={request_id})")
        schedule_notify_api_panel_unreachable(
            "WaifuFiles upload",
            "upload_to_server",
            exc,
            settings.webupload_base or "",
        )
        raise RuntimeError("Ошибка авторизации загрузки. Обратитесь к администратору.")

    if status == 400:
        raise ValueError(message)

    raise RuntimeError(f"{code}: {message} (request_id={request_id})")


async def upload_to_server(file_path, user):
    """Загружает изображение на сервер через WaifuFiles API v1"""
    settings = load_bootstrap_settings()
    if not settings.webupload_base or not settings.webupload_api_key:
        raise RuntimeError("Webupload не настроен: задайте WEBUPLOAD_BASE и WEBUPLOAD_API_KEY")

    base = settings.webupload_base.rstrip("/")
    url = f"{base}/api/v1/files/upload"
    upload_headers = {"X-API-Key": settings.webupload_api_key}
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as file:
            original_filename = os.path.basename(file_path)
            data = aiohttp.FormData()
            data.add_field(
                "files",
                file,
                filename=original_filename,
                content_type="image/jpeg",
            )
            data.add_field("source", "discord")
            data.add_field("uploaded_by", user)
            data.add_field("manual_check", "false")

            async with session.post(
                url,
                data=data,
                headers=upload_headers,
                timeout=timeout,
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    file_url = response_data["files"][0]["url"]
                    logging.info("Файл %s сохранен на сервере", file_url)
                    return file_url

                try:
                    error_body = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    error_body = {}
                await _handle_upload_error(response.status, error_body)


async def generate_and_save_image(user_input, user):
    """Генерирует изображение и сохраняет его на сервере"""
    async with aiohttp.ClientSession() as session:
        operation_id = await post_image_generation(session, user_input)

        while True:
            image_base64 = await fetch_operation_status(session, operation_id)
            if image_base64:
                image_path = await save_image(image_base64, user)
                image_url = await upload_to_server(image_path, user)
                os.remove(image_path)
                return image_url
            else:
                await asyncio.sleep(10)
