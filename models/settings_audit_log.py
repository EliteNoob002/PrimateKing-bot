"""Журнал изменений настроек (запись — зона ответственности web-панели)."""

from sqlalchemy import JSON, BigInteger, Column, DateTime, String, func

from utils.database import Base


class SettingsAuditLog(Base):
    __tablename__ = "bot_settings_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor = Column(String(128), nullable=True)
    scope = Column(String(64), nullable=False)
    scope_id = Column(String(128), nullable=True)
    setting_key = Column(String(128), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
