"""Настройки включения/выключения функций."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, UniqueConstraint, func

from utils.database import Base


class FunctionSetting(Base):
    __tablename__ = "bot_function_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=True)
    function_name = Column(String(128), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "function_name",
            name="uq_bot_function_settings",
        ),
    )
