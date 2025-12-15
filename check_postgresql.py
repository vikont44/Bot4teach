"""
Скрипт для проверки подключения к PostgreSQL
Помогает диагностировать проблемы с подключением
"""
import asyncio
import sys
import socket
from database.config import db_config


async def check_postgresql_connection():
    """Проверяет возможность подключения к PostgreSQL"""
    print("=" * 60)
    print("Диагностика подключения к PostgreSQL")
    print("=" * 60)
    print()
    
    # Проверка 1: Проверка доступности хоста и порта
    print("1. Проверка доступности сервера PostgreSQL...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((db_config.host, db_config.port))
        sock.close()
        
        if result == 0:
            print(f"   ✓ Сервер доступен на {db_config.host}:{db_config.port}")
        else:
            print(f"   ✗ Не удается подключиться к {db_config.host}:{db_config.port}")
            print(f"     Возможные причины:")
            print(f"     - PostgreSQL не запущен")
            print(f"     - Неправильный порт (текущий: {db_config.port})")
            print(f"     - Брандмауэр блокирует подключение")
            return False
    except Exception as e:
        print(f"   ✗ Ошибка при проверке: {e}")
        return False
    
    print()
    
    # Проверка 2: Проверка настроек подключения
    print("2. Проверка настроек подключения...")
    print(f"   Host: {db_config.host}")
    print(f"   Port: {db_config.port}")
    print(f"   Database: {db_config.database}")
    print(f"   User: {db_config.user}")
    print(f"   Password: {'*' * len(db_config.password) if db_config.password else 'НЕ ЗАДАН'}")
    
    if not db_config.password or db_config.password == "postgres":
        print()
        print("   ⚠ Внимание: Используется пароль по умолчанию или пароль не задан")
        print("      Убедитесь, что вы указали правильный пароль в файле .env")
    
    print()
    
    # Проверка 3: Попытка подключения к PostgreSQL
    print("3. Попытка подключения к PostgreSQL...")
    try:
        import asyncpg
        
        try:
            # Пытаемся подключиться к системной БД
            conn = await asyncpg.connect(
                host=db_config.host,
                port=db_config.port,
                user=db_config.user,
                password=db_config.password,
                database='postgres',
                timeout=10
            )
            print("   ✓ Подключение к PostgreSQL успешно!")
            
            # Проверяем версию PostgreSQL
            version = await conn.fetchval("SELECT version()")
            print(f"   Версия PostgreSQL: {version.split(',')[0]}")
            
            await conn.close()
            return True
            
        except asyncpg.InvalidPasswordError:
            print("   ✗ Ошибка: Неверный пароль")
            print()
            print("   Решение:")
            print("   1. Проверьте пароль в файле .env")
            print("   2. Убедитесь, что пароль совпадает с паролем, указанным при установке PostgreSQL")
            print("   3. Если забыли пароль, см. инструкции по сбросу пароля PostgreSQL")
            return False
            
        except asyncpg.InvalidCatalogNameError:
            print("   ✗ Ошибка: База данных 'postgres' не найдена")
            print()
            print("   Решение:")
            print("   Это критическая ошибка. PostgreSQL установлен неправильно.")
            print("   Попробуйте переустановить PostgreSQL.")
            return False
            
        except asyncpg.PostgresConnectionError as e:
            print(f"   ✗ Ошибка подключения: {e}")
            print()
            print("   Возможные причины:")
            print("   1. PostgreSQL не запущен")
            print("   2. Неправильный хост или порт")
            print("   3. Проблемы с сетью или брандмауэром")
            print()
            print("   Решение для Windows:")
            print("   1. Откройте 'Службы' (Services): Win+R -> services.msc")
            print("   2. Найдите 'postgresql-x64-XX' (где XX - версия)")
            print("   3. Убедитесь, что служба запущена")
            print("   4. Если не запущена, нажмите 'Запустить'")
            return False
            
        except Exception as e:
            print(f"   ✗ Неожиданная ошибка: {e}")
            print(f"   Тип ошибки: {type(e).__name__}")
            return False
            
    except ImportError:
        print("   ✗ Библиотека asyncpg не установлена")
        print()
        print("   Решение:")
        print("   Установите зависимости: pip install -r requirements.txt")
        return False


def check_windows_services():
    """Проверяет, запущена ли служба PostgreSQL в Windows"""
    print()
    print("4. Информация для Windows:")
    print("   Чтобы проверить, запущена ли служба PostgreSQL:")
    print()
    print("   Способ 1 (через PowerShell):")
    print("   Get-Service -Name postgresql*")
    print()
    print("   Способ 2 (через командную строку):")
    print("   sc query postgresql*")
    print()
    print("   Способ 3 (через интерфейс):")
    print("   1. Нажмите Win+R")
    print("   2. Введите: services.msc")
    print("   3. Найдите службу PostgreSQL и проверьте её статус")


async def main():
    """Основная функция"""
    success = await check_postgresql_connection()
    
    check_windows_services()
    
    print()
    print("=" * 60)
    
    if success:
        print("✓ Все проверки пройдены успешно!")
        print("  Теперь можно запускать: python create_database.py")
    else:
        print("✗ Обнаружены проблемы с подключением")
        print()
        print("Рекомендации:")
        print("1. Убедитесь, что PostgreSQL установлен и запущен")
        print("2. Проверьте настройки в файле .env")
        print("3. Проверьте, не блокирует ли брандмауэр подключение")
        print("4. Попробуйте перезапустить службу PostgreSQL")
        
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nОперация прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)

