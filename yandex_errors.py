import logging

def translate_yandex_error(error_msg: str) -> str:
    msg_lower = error_msg.lower()

    TRANSLATION_KEYS = {
        ("prompt", "positive", "size", "exceeds", "limit"): 
            "Промт слишком длинный. Сократите описание до 500 символов или менее.",

        ("it", "is", "not", "possible", "to", "generate", "an", "image", "because", "violate"): 
            "Промт не прошёл модерацию. Попробуйте переформулировать его.",

        ("internal", "error"): 
            "Произошла внутренняя ошибка на стороне сервиса. Попробуйте позже.",

        ("bad", "request"): 
            "Некорректный запрос. Убедитесь, что вы ввели понятный и завершённый текст.",

        ("unauthorized",): 
            "Проблема с авторизацией API. Обратитесь к администратору бота.",

        ("rate", "limit", "exceeded"): 
            "Превышен лимит запросов к API. Подождите немного и попробуйте снова.",
    }

    for keys, translation in TRANSLATION_KEYS.items():
        if all(key in msg_lower for key in keys):
            logging.info(f"Переведена ошибка API: '{error_msg}' -> '{translation}'")
            return translation

    # Логируем оригинальный непереведённый текст ошибки для анализа
    logging.warning(f"Неизвестная ошибка API: '{error_msg}'")
    return f"Неизвестная ошибка: {error_msg}"
