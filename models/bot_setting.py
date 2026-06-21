"""Глобальные настройки бота (JSON key-value)."""

from sqlalchemy import JSON, Column, DateTime, String, func

from utils.database import Base


class BotSetting(Base):
    __tablename__ = "bot_settings"

    setting_key = Column(String(128), primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(128), nullable=True)
