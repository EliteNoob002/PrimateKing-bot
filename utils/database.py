"""Подключение к базе данных через SQLAlchemy"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from urllib.parse import quote_plus
from utils.config import get_config

# Базовый класс для моделей
Base = declarative_base()

# Создание engine
def create_database_engine():
    """Создаёт engine для подключения к базе данных"""
    host = get_config('host_db')
    database = get_config('database')
    user = get_config('user_db')
    password = get_config('password_db')
    
    # Экранируем специальные символы в пароле и других параметрах для URL
    user_escaped = quote_plus(str(user))
    password_escaped = quote_plus(str(password))
    host_escaped = quote_plus(str(host))
    database_escaped = quote_plus(str(database))
    
    connection_string = f"mysql+pymysql://{user_escaped}:{password_escaped}@{host_escaped}/{database_escaped}?charset=utf8mb4"
    
    engine = create_engine(
        connection_string,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Проверка соединений перед использованием
        pool_recycle=3600,   # Переподключение через час
        echo=False
    )
    
    return engine

# Глобальный engine
_engine = None

def get_engine():
    """Возвращает engine, создавая его при первом вызове"""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine

# Фабрика сессий (будет создана при первом использовании)
_SessionLocal = None

def get_session_factory():
    """Возвращает фабрику сессий, создавая её при первом вызове"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

@contextmanager
def get_session():
    """Контекстный менеджер для работы с сессией БД"""
    SessionLocal = get_session_factory()
    session = SessionLocal()
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
    SessionLocal = get_session_factory()
    return SessionLocal()

# Инициализация моделей
def init_db():
    """Инициализирует таблицы в базе данных"""
    from models.user import User  # Импортируем модели
    Base.metadata.create_all(bind=get_engine())
