"""
Скрипт для инициализации базы данных
"""
import asyncio
import sys
from database.db_manager import db_manager


async def main():
    """Основная функция для инициализации БД"""
    try:
        print("Подключение к базе данных...")
        await db_manager.connect()
        
        print("Инициализация схемы базы данных...")
        await db_manager.init_database()
        
        print("База данных успешно инициализирована!")
        
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
        sys.exit(1)
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

