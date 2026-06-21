"""Настройки включения/выключения команд."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, UniqueConstraint, func

from utils.database import Base


class CommandSetting(Base):
    __tablename__ = "bot_command_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=True)
    command_name = Column(String(128), nullable=False)
    command_type = Column(String(32), nullable=False, default="slash")
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "command_name",
            "command_type",
            name="uq_bot_command_settings",
        ),
    )
