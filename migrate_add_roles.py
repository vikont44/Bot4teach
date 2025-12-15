"""
Скрипт миграции для добавления ролевой модели в существующую базу данных
"""
import asyncio
import sys
from database.db_manager import db_manager


async def migrate():
    """Применяет миграцию для добавления ролей"""
    try:
        print("=" * 60)
        print("Миграция: Добавление ролевой модели")
        print("=" * 60)
        print()
        
        print("Подключение к базе данных...")
        await db_manager.connect()
        
        print("Применение миграции...")
        
        # Выполняем миграцию напрямую через SQL команды
        async with db_manager.pool.acquire() as connection:
            # Создание типа enum для ролей (если не существует)
            await connection.execute("""
                DO $$ BEGIN
                    CREATE TYPE role_enum AS ENUM ('student', 'mentor');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            print("✓ Тип role_enum проверен/создан")
            
            # Добавление поля role в таблицу agents (если не существует)
            await connection.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'agents' AND column_name = 'role'
                    ) THEN
                        ALTER TABLE agents ADD COLUMN role role_enum DEFAULT 'student' NOT NULL;
                    END IF;
                END $$;
            """)
            print("✓ Поле role добавлено в таблицу agents")
            
            # Добавление поля created_at (если не существует)
            await connection.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'agents' AND column_name = 'created_at'
                    ) THEN
                        ALTER TABLE agents ADD COLUMN created_at timestamp DEFAULT CURRENT_TIMESTAMP;
                    END IF;
                END $$;
            """)
            print("✓ Поле created_at добавлено в таблицу agents")
            
            # Добавление уникального ограничения на tg_name (если не существует)
            await connection.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'agents_tg_name_key'
                    ) THEN
                        ALTER TABLE agents ADD CONSTRAINT agents_tg_name_key UNIQUE (tg_name);
                    END IF;
                END $$;
            """)
            print("✓ Уникальное ограничение на tg_name добавлено")
            
            # Создание индексов
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_agents_role ON agents (role);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_agents_tg_name ON agents (tg_name);")
            print("✓ Индексы созданы")
            
            # Обновление существующих записей
            await connection.execute("UPDATE agents SET role = 'student' WHERE role IS NULL;")
            print("✓ Существующие записи обновлены")
        
        print()
        print("=" * 60)
        print("✓ Миграция успешно применена!")
        print("=" * 60)
        print()
        print("Теперь в базе данных доступны роли:")
        print("  - student (студент) - роль по умолчанию")
        print("  - mentor (ментор/админ) - для управления")
        print()
        print("Для добавления ментора используйте:")
        print("  python add_mentor.py <telegram_username>")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Ошибка при применении миграции: {e}")
        print("=" * 60)
        sys.exit(1)
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate())

