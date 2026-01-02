"""
Конфигурация для подключения к базе данных
"""
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class DatabaseConfig:
    """Класс для хранения конфигурации БД"""
    
    def __init__(self):
        self.host: str = os.getenv("DB_HOST", "5.129.215.27")
        self.port: int = int(os.getenv("DB_PORT", "5432"))
        self.database: str = os.getenv("DB_NAME", "telegram_bot")
        self.user: str = os.getenv("DB_USER", "postgres")
        self.password: str = os.getenv("DB_PASSWORD", "postgres")
    
    @property
    def connection_string(self) -> str:
        """Возвращает строку подключения к БД"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    # @property
    # def async_connection_string(self) -> str:
    #     """Возвращает асинхронную строку подключения к БД"""
    #     return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# Глобальный экземпляр конфигурации
db_config = DatabaseConfig()

