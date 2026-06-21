"""Настройки Discord-сервера (guild)."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, func

from utils.database import Base


class GuildSetting(Base):
    __tablename__ = "bot_guild_settings"

    guild_id = Column(BigInteger, primary_key=True)
    guild_name = Column(String(255), nullable=True, comment="Название Discord-сервера")
    prefix = Column(String(10), nullable=False, default="$")
    language = Column(String(16), nullable=False, default="ru")
    status_rotation_enabled = Column(Boolean, nullable=False, default=True)
    status_rotation_interval = Column(Integer, nullable=False, default=60)
    log_channel_id = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(128), nullable=True)
