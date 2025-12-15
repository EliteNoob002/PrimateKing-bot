"""Модель пользователя"""
from sqlalchemy import Column, BigInteger, String, Integer
from utils.database import Base

class User(Base):
    """Модель пользователя для хранения статистики"""
    __tablename__ = 'user'
    
    id = Column(BigInteger, primary_key=True, comment='Discord ID пользователя')
    name = Column(String(255), nullable=False, comment='Имя пользователя')
    count = Column(Integer, default=0, nullable=False, comment='Счётчик')
    admin = Column(String(10), default="0", nullable=False, comment='Флаг администратора')
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', count={self.count})>"

