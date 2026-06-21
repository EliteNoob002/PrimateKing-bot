"""Подключение к базе данных через SQLAlchemy"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.bootstrap_settings import load_bootstrap_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    """Возвращает engine, создавая его при первом вызове"""
    global _engine
    if _engine is None:
        settings = load_bootstrap_settings()
        _engine = create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
    return _engine


def get_session_factory():
    """Возвращает фабрику сессий, создавая её при первом вызове"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


@contextmanager
def get_session():
    """Контекстный менеджер для работы с сессией БД"""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_sync():
    """Возвращает сессию для синхронной работы (устаревший метод, использовать get_session)"""
    return get_session_factory()()


def init_db():
    """Инициализирует таблицы в базе данных"""
    import models  # noqa: F401 — регистрация моделей в metadata

    Base.metadata.create_all(bind=get_engine())


def ensure_bot_schema() -> None:
    """Создаёт отсутствующие таблицы бота (безопасно при общей БД с web-панелью)."""
    init_db()
