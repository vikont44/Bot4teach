"""
Скрипт для добавления нового ментора (админа)
Использование: python add_mentor.py <telegram_username>
"""
import asyncio
import sys
from database.db_manager import db_manager


async def add_mentor(tg_name: str):
    """Добавляет нового ментора"""
    try:
        print("=" * 60)
        print("Добавление нового ментора")
        print("=" * 60)
        print()
        
        await db_manager.connect()
        
        # Проверяем, является ли тот, кто добавляет, ментором
        # (в реальном приложении здесь должна быть проверка прав)
        
        print(f"Добавление ментора: {tg_name}...")
        mentor = await db_manager.add_mentor(tg_name)
        
        print()
        print("=" * 60)
        print("✓ Ментор успешно добавлен!")
        print("=" * 60)
        print(f"ID: {mentor.id}")
        print(f"Telegram имя: {mentor.tg_name}")
        print(f"Роль: {mentor.role.value}")
        print(f"Создан: {mentor.created_at}")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Ошибка при добавлении ментора: {e}")
        print("=" * 60)
        sys.exit(1)
    finally:
        await db_manager.disconnect()


async def list_mentors():
    """Показывает список всех менторов"""
    try:
        await db_manager.connect()
        
        mentors = await db_manager.get_all_mentors()
        
        print("=" * 60)
        print(f"Список менторов (всего: {len(mentors)})")
        print("=" * 60)
        print()
        
        if not mentors:
            print("Менторы не найдены")
        else:
            for i, mentor in enumerate(mentors, 1):
                print(f"{i}. {mentor.tg_name} (ID: {mentor.id})")
                print(f"   Создан: {mentor.created_at}")
                print()
        
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)
    finally:
        await db_manager.disconnect()


async def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python add_mentor.py <telegram_username>  - добавить ментора")
        print("  python add_mentor.py --list               - показать список менторов")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        await list_mentors()
    else:
        tg_name = sys.argv[1]
        await add_mentor(tg_name)


if __name__ == "__main__":
    asyncio.run(main())

