"""Синхронизация команд с API и MySQL."""

import inspect
import logging
import re
import sys
from pathlib import Path

import discord
import requests
from discord.ext import commands
from sqlalchemy.dialects.mysql import insert as mysql_insert

from models.command_setting import CommandSetting
from models.function_setting import FunctionSetting
from utils.bootstrap_settings import load_bootstrap_settings
from utils.database import get_session

PROJECT_MODULE_PREFIXES = ["commands", "events", "services", "utils", "models", "tasks", "ui"]


def get_panel_api_url() -> str | None:
    settings = load_bootstrap_settings()
    return settings.panel_api_url


def _normalize_command_name(cmd_type: str, name: str) -> str:
    if cmd_type == "prefix":
        return name.lstrip("$")
    if cmd_type == "function":
        return name.removeprefix("func_")
    return name


def _discover_function_names_from_decorator() -> set[str]:
    function_names = set()
    project_root = Path(__file__).parent.parent
    for module_dir in PROJECT_MODULE_PREFIXES:
        dir_path = project_root / module_dir
        if not dir_path.exists():
            continue
        for file_path in dir_path.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                for line in content.split("\n"):
                    if line.strip().startswith("#"):
                        continue
                    code_part = line.split("#")[0]
                    matches = re.findall(
                        r'function_enabled_check\(["\']([^"\']+)["\']\)',
                        code_part,
                    )
                    function_names.update(matches)
            except Exception:
                continue
    return function_names


def parse_commands_and_functions(bot) -> list[dict]:
    """Собирает список slash/prefix команд и функций бота."""
    commands_list = []

    for command in bot.tree.walk_commands():
        if isinstance(command, discord.app_commands.Command):
            commands_list.append(
                {
                    "name": command.name,
                    "type": "slash",
                    "enabled": True,
                    "description": command.description or "",
                }
            )

    for command in bot.commands:
        if isinstance(command, commands.Command):
            clean_name = command.name.lstrip("$")
            commands_list.append(
                {
                    "name": f"${clean_name}",
                    "type": "prefix",
                    "enabled": True,
                    "description": command.help or "",
                }
            )

    function_names_from_decorator = _discover_function_names_from_decorator()
    seen_functions = set()

    for module_name, module in sys.modules.items():
        if module is None:
            continue
        if not any(module_name.startswith(prefix) for prefix in PROJECT_MODULE_PREFIXES) and module_name != "__main__":
            continue

        try:
            module_file = getattr(module, "__file__", None)
            project_roots = [str(Path(__file__).parent.parent), "commands", "events", "services"]
            if module_file and not any(module_file.startswith(p) for p in project_roots):
                continue

            for func_name, func in inspect.getmembers(
                module,
                predicate=lambda x: inspect.isfunction(x) or inspect.iscoroutinefunction(x),
            ):
                if func_name.startswith("_") or func_name in seen_functions:
                    continue

                try:
                    func_module = getattr(func, "__module__", None)
                    if func_module:
                        stdlib_prefixes = (
                            "sqlalchemy",
                            "discord",
                            "yaml",
                            "paramiko",
                            "aiohttp",
                            "requests",
                            "asyncio",
                            "inspect",
                            "logging",
                            "datetime",
                            "io",
                            "urllib",
                            "json",
                            "os",
                            "sys",
                            "time",
                            "uuid",
                            "re",
                            "random",
                            "typing",
                            "functools",
                            "pathlib",
                            "mysql",
                            "pymysql",
                        )
                        if func_module.startswith(stdlib_prefixes):
                            continue
                        if not any(func_module.startswith(prefix) for prefix in PROJECT_MODULE_PREFIXES) and func_module != "__main__":
                            continue
                except Exception:
                    pass

                seen_functions.add(func_name)
                clean_name = func_name.removeprefix("func_")
                description = ""
                if func.__doc__:
                    description = func.__doc__.strip()
                    if len(description) > 500:
                        description = description[:500] + "..."

                commands_list.append(
                    {
                        "name": f"func_{clean_name}",
                        "type": "function",
                        "enabled": True,
                        "description": description,
                    }
                )
        except (AttributeError, ImportError, TypeError):
            continue

    for func_name in function_names_from_decorator:
        if func_name not in seen_functions:
            commands_list.append(
                {
                    "name": f"func_{func_name}",
                    "type": "function",
                    "enabled": True,
                    "description": "",
                }
            )

    return commands_list


def upsert_settings_to_mysql(commands_list: list[dict], guild_id: int | None = None) -> None:
    """Upsert command/function settings в MySQL без перезаписи enabled=false."""
    with get_session() as session:
        for cmd in commands_list:
            cmd_type = cmd["type"]
            if cmd_type in ("slash", "prefix"):
                storage_name = _normalize_command_name(cmd_type, cmd["name"])
                existing = (
                    session.query(CommandSetting)
                    .filter_by(
                        guild_id=guild_id,
                        command_name=storage_name,
                        command_type=cmd_type,
                    )
                    .first()
                )
                if existing:
                    continue

                stmt = mysql_insert(CommandSetting).values(
                    guild_id=guild_id,
                    command_name=storage_name,
                    command_type=cmd_type,
                    enabled=cmd.get("enabled", True),
                )
                stmt = stmt.on_duplicate_key_update(
                    command_name=stmt.inserted.command_name,
                )
                session.execute(stmt)

            elif cmd_type == "function":
                storage_name = _normalize_command_name(cmd_type, cmd["name"])
                existing = session.query(FunctionSetting).filter_by(guild_id=guild_id, function_name=storage_name).first()
                if existing:
                    continue

                stmt = mysql_insert(FunctionSetting).values(
                    guild_id=guild_id,
                    function_name=storage_name,
                    enabled=cmd.get("enabled", True),
                )
                stmt = stmt.on_duplicate_key_update(
                    function_name=stmt.inserted.function_name,
                )
                session.execute(stmt)

    logging.info("MySQL: upsert %d command/function settings", len(commands_list))


def _fetch_panel_commands(api_base: str) -> list[dict]:
    """GET /commands из OpenAPI панели (пагинация)."""
    headers = {"Content-Type": "application/json"}
    items: list[dict] = []
    page = 1
    page_size = 100

    while True:
        url = f"{api_base.rstrip('/')}/commands"
        resp = requests.get(
            url,
            params={"page": page, "page_size": page_size},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("items", [])
        items.extend(batch)

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return items


def sync_descriptions_to_panel(api_base: str, commands_list: list[dict]) -> None:
    """Обновляет description в панели для существующих команд (PATCH /commands/{id})."""
    try:
        panel_items = _fetch_panel_commands(api_base)
    except Exception as e:
        logging.warning("Панель %s/commands недоступна: %s", api_base, e)
        return

    panel_by_key = {(item["type"], item["name"]): item for item in panel_items}

    for cmd in commands_list:
        key = (cmd["type"], cmd["name"])
        panel_item = panel_by_key.get(key)
        if not panel_item:
            continue

        new_desc = cmd.get("description", "")
        old_desc = panel_item.get("description") or ""
        if new_desc and new_desc != old_desc:
            cmd_id = panel_item["id"]
            try:
                resp = requests.patch(
                    f"{api_base.rstrip('/')}/commands/{cmd_id}",
                    json={"description": new_desc},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                resp.raise_for_status()
                logging.debug("Обновлено описание команды %s в панели", key)
            except Exception as e:
                logging.warning("Не удалось обновить описание %s: %s", key, e)


def send_commands_to_api(bot) -> None:
    """Синхронизирует команды: MySQL upsert + опционально панель OpenAPI."""
    try:
        commands_list = parse_commands_and_functions(bot)
    except Exception as e:
        logging.error("parse_commands_and_functions() failed: %s", e, exc_info=True)
        return

    settings = load_bootstrap_settings()
    upsert_settings_to_mysql(commands_list, guild_id=settings.primary_guild_id)

    if bot.config_cache:
        bot.config_cache.reload()

    api_base = settings.panel_api_url
    if not api_base:
        logging.info("PANEL_API_URL не задан — синхронизация с панелью пропущена.")
        return

    sync_descriptions_to_panel(api_base, commands_list)
    logging.info("Синхронизация команд завершена: %d items", len(commands_list))
