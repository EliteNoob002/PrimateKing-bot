"""Конфигурация бота"""
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_config_cache = None

def load_config():
    """Загружает конфигурацию из config.yaml"""
    global _config_cache
    if _config_cache is None:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            _config_cache = yaml.load(f, Loader=yaml.FullLoader)
    return _config_cache

def get_config(key: str, default=None):
    """Получает значение из конфигурации"""
    config = load_config()
    return config.get(key, default)

