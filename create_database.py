"""
Скрипт для создания базы данных PostgreSQL (для Windows)
"""
import asyncio
import asyncpg
from database.config import db_config


async def create_database():
    """Создает базу данных если она не существует"""
    try:
        # Подключаемся к системной БД postgres для создания новой БД
        print(f"Подключение к серверу PostgreSQL...")
        conn = await asyncpg.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.user,
            password=db_config.password,
            database='postgres'  # Подключаемся к системной БД
        )
        
        # Проверяем, существует ли база данных
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_config.database
        )
        
        if db_exists:
            print(f"База данных '{db_config.database}' уже существует.")
        else:
            print(f"Создание базы данных '{db_config.database}'...")
            await conn.execute(f'CREATE DATABASE "{db_config.database}"')
            print(f"База данных '{db_config.database}' успешно создана!")
        
        await conn.close()
        return True
        
    except asyncpg.InvalidPasswordError:
        print("Ошибка: Неверный пароль для подключения к PostgreSQL")
        print(f"Проверьте настройки в файле .env или переменные окружения:")
        print(f"  DB_USER={db_config.user}")
        print(f"  DB_PASSWORD=***")
        return False
    except asyncpg.InvalidCatalogNameError:
        print("Ошибка: Не удалось подключиться к системной БД 'postgres'")
        print("Убедитесь, что PostgreSQL установлен и запущен.")
        return False
    except asyncpg.PostgresConnectionError as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        print(f"\nПроверьте настройки подключения:")
        print(f"  DB_HOST={db_config.host}")
        print(f"  DB_PORT={db_config.port}")
        print(f"  DB_USER={db_config.user}")
        print("\nУбедитесь, что:")
        print("  1. PostgreSQL установлен и запущен")
        print("  2. Настройки подключения корректны")
        print("  3. Файл .env настроен правильно")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False


async def main():
    """Основная функция"""
    print("=" * 50)
    print("Создание базы данных для Telegram бота")
    print("=" * 50)
    print()
    
    success = await create_database()
    
    if success:
        print()
        print("=" * 50)
        print("Следующий шаг: запустите 'python init_database.py'")
        print("для инициализации схемы базы данных")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("Не удалось создать базу данных.")
        print("Проверьте настройки и попробуйте снова.")
        print("=" * 50)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

