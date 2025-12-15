"""Синхронизация команд с API"""
import requests
import logging
import inspect
import discord
from discord.ext import commands
from utils.config import get_config

API_URL = get_config('my_api_url')

def get_commands_from_api():
    """Получает команды из API"""
    try:
        url = f"{API_URL}/bot/items"
        response = requests.get(url)
        response.raise_for_status()
        
        commands_dict = {}
        for item in response.json():
            clean_name = item['name']
            if item['type'] == 'prefix':
                clean_name = clean_name.lstrip('$')
            elif item['type'] == 'function':
                clean_name = clean_name.removeprefix('func_')
            
            commands_dict[(item['type'], clean_name)] = {
                'status': item.get('enabled', False),
                'description': item.get('description', '')
            }
        return commands_dict
    except Exception as e:
        logging.error(f"API Error: {str(e)}")
        return {}


def parse_commands_and_functions(bot):
    """Парсит команды и функции бота"""
    try:
        response = requests.get(f"{API_URL}/bot/commands")
        api_data = response.json()
        api_commands = {
            (item['type'], item['name']): item 
            for item in api_data
        }
    except Exception as e:
        logging.error(f"API error: {e}")
        api_commands = {}

    commands_list = []

    # Обработка слэш-команд
    for command in bot.tree.walk_commands():
        if isinstance(command, discord.app_commands.Command):
            key = ('slash', command.name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': command.name,
                'type': 'slash',
                'enabled': api_entry.get('enabled', True),
                'description': command.description or ''
            })

    # Обработка префиксных команд
    for command in bot.commands:
        if isinstance(command, commands.Command):
            clean_name = command.name.lstrip('$')
            key = ('prefix', clean_name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': f'${clean_name}',
                'type': 'prefix',
                'enabled': api_entry.get('enabled', True),
                'description': command.help or ''
            })

    # Обработка функций (если есть)
    # Ищем ВСЕ функции во всех модулях проекта, аналогично globals() в оригинале
    # В API они регистрируются с префиксом func_
    import sys
    from pathlib import Path
    import re
    
    project_modules_prefixes = ['commands', 'events', 'services', 'utils', 'models', 'tasks', 'ui']
    
    # Сначала находим функции, которые используются с function_enabled_check в исходном коде
    # Это позволяет найти функции, определенные внутри других функций
    function_names_from_decorator = set()
    project_root = Path(__file__).parent.parent
    for module_dir in project_modules_prefixes:
        dir_path = project_root / module_dir
        if not dir_path.exists():
            continue
        for file_path in dir_path.glob('*.py'):
            if file_path.name == '__init__.py':
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Ищем вызовы function_enabled_check("название_функции")
                    # Исключаем комментарии - ищем только в строках кода
                    lines = content.split('\n')
                    for line in lines:
                        # Пропускаем комментарии
                        if line.strip().startswith('#'):
                            continue
                        # Убираем комментарии из конца строки
                        code_part = line.split('#')[0]
                        pattern = r'function_enabled_check\(["\']([^"\']+)["\']\)'
                        matches = re.findall(pattern, code_part)
                        function_names_from_decorator.update(matches)
            except Exception:
                continue
    
    # Теперь находим все функции на уровне модулей
    seen_functions = set()
    
    for module_name, module in sys.modules.items():
        if module is None:
            continue
        
        # Пропускаем системные модули и модули не из нашего проекта
        if not any(module_name.startswith(prefix) for prefix in project_modules_prefixes):
            if module_name != '__main__':
                continue
        
        try:
            # Получаем имя модуля для проверки, что функция определена в этом модуле
            module_file = getattr(module, '__file__', None)
            if module_file and not any(module_file.startswith(p) for p in [str(Path(__file__).parent.parent), 'commands', 'events', 'services']):
                # Пропускаем модули, которые не из нашего проекта
                continue
                
            for func_name, func in inspect.getmembers(module, predicate=lambda x: inspect.isfunction(x) or inspect.iscoroutinefunction(x)):
                # Пропускаем приватные функции (начинающиеся с _)
                if func_name.startswith('_'):
                    continue
                
                # Пропускаем уже обработанные функции
                if func_name in seen_functions:
                    continue
                
                # Проверяем, что функция определена в модуле проекта, а не импортирована
                try:
                    func_module = getattr(func, '__module__', None)
                    if func_module:
                        # Пропускаем функции из стандартных библиотек и внешних пакетов
                        if func_module.startswith(('sqlalchemy', 'discord', 'yaml', 'paramiko', 'aiohttp', 'requests', 'asyncio', 'inspect', 'logging', 'datetime', 'io', 'urllib', 'json', 'os', 'sys', 'time', 'uuid', 're', 'random', 'typing', 'functools', 'pathlib', 'mysql', 'pymysql')):
                            continue
                        # Проверяем, что функция определена в модуле проекта
                        if not any(func_module.startswith(prefix) for prefix in project_modules_prefixes):
                            if func_module != '__main__':
                                continue
                except Exception:
                    pass
                    
                seen_functions.add(func_name)
                
                # Убираем префикс 'func_' если он есть в имени функции
                clean_name = func_name.removeprefix('func_')
                key = ('function', clean_name)
                api_entry = api_commands.get(key, {})
                
                # Получаем описание, ограничиваем длину
                description = ''
                if func.__doc__:
                    description = func.__doc__.strip()
                    # Ограничиваем длину описания до 500 символов
                    if len(description) > 500:
                        description = description[:500] + '...'
                
                commands_list.append({
                    'name': f'func_{clean_name}',
                    'type': 'function',
                    'enabled': api_entry.get('enabled', True),
                    'description': description
                })
        except (AttributeError, ImportError, TypeError):
            # Игнорируем модули, которые не могут быть проверены
            continue
    
    # Добавляем функции, найденные через function_enabled_check, если их ещё нет
    for func_name in function_names_from_decorator:
        if func_name not in seen_functions:
            key = ('function', func_name)
            api_entry = api_commands.get(key, {})
            commands_list.append({
                'name': f'func_{func_name}',
                'type': 'function',
                'enabled': api_entry.get('enabled', True),
                'description': api_entry.get('description', '')
            })

    return commands_list


def send_commands_to_api(bot):
    """Отправляет команды в API для синхронизации"""
    api_base = API_URL.rstrip("/")
    url_get_commands = f"{api_base}/bot/commands"
    url_post_items = f"{api_base}/bot/items"
    headers = {"Content-Type": "application/json"}

    try:
        commands_list = parse_commands_and_functions(bot)
    except Exception as e:
        logging.error("parse_commands_and_functions() failed: %s", e, exc_info=True)
        return

    current_keys = {(cmd["type"], cmd["name"]) for cmd in commands_list}

    try:
        resp = requests.get(url_get_commands, headers=headers, timeout=5)
        resp.raise_for_status()
        api_items = resp.json()
        existing_keys = {(item["type"], item["name"]) for item in api_items}
    except Exception as e:
        logging.warning(
            "API %s недоступен или вернул ошибку: %s — пропускаю синхронизацию.",
            url_get_commands,
            e,
        )
        return

    new_items = [
        {
            "type": cmd["type"],
            "name": cmd["name"],
            "enabled": cmd.get("enabled", True),
            "description": cmd.get("description", ""),
        }
        for cmd in commands_list
        if (cmd["type"], cmd["name"]) not in existing_keys
    ]

    obsolete_keys = existing_keys - current_keys

    if not new_items and not obsolete_keys:
        logging.info("Синхронизация команд: изменений нет.")
        return

    if new_items:
        try:
            resp = requests.post(
                url_post_items,
                json=new_items,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            logging.info(
                "Отправлено в API новых/обновлённых команд: %d шт.",
                len(new_items),
            )
        except Exception as e:
            logging.error("Не удалось отправить команды в API: %s", e)
            logging.debug("Payload отправки: %s", new_items)

    for cmd_type, name in obsolete_keys:
        try:
            del_url = f"{api_base}/bot/items/{cmd_type}/{name}"
            resp = requests.delete(del_url, headers=headers, timeout=5)

            if resp.status_code == 200:
                logging.info("Удалена команда/функция из панели: type=%s, name=%s", cmd_type, name)
            elif resp.status_code == 404:
                logging.info(
                    "Команда/функция уже отсутствует в панели: type=%s, name=%s",
                    cmd_type,
                    name,
                )
            else:
                logging.warning(
                    "Не удалось удалить %s/%s: HTTP %s %s",
                    cmd_type,
                    name,
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as e:
            logging.error(
                "Ошибка при удалении команды/функции %s/%s из панели: %s",
                cmd_type,
                name,
                e,
            )

