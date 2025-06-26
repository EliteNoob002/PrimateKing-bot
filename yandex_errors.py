# yandex_errors.py

YANDEX_ERROR_TRANSLATIONS = {
    "it is not possible to generate an image from this request because it may violate the terms of use":
        "Промт не прошёл модерацию. Попробуйте переформулировать его, избегая неприемлемых или чувствительных тем.",

    "internal error":
        "Произошла внутренняя ошибка на стороне сервиса. Попробуйте позже.",

    "bad request":
        "Некорректный запрос. Убедитесь, что вы ввели понятный и завершённый текст.",

    "unauthorized":
        "Проблема с авторизацией API. Обратитесь к администратору бота.",

    "rate limit exceeded":
        "Превышен лимит запросов к API. Подождите немного и попробуйте снова.",

    "prompt positive size exceeds limit":
        "Промт слишком длинный. Сократите описание до 500 символов или менее.",
}

def translate_yandex_error(error_msg: str) -> str:
    msg_lower = error_msg.lower()
    for key, translation in YANDEX_ERROR_TRANSLATIONS.items():
        if key in msg_lower:
            return translation
    return f"Неизвестная ошибка: {error_msg}"
