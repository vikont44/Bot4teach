#!/usr/bin/env python3
"""
Скрипт для управления пользователями в базе данных
Позволяет добавлять, удалять, просматривать и изменять роли пользователей
"""

import asyncio
import sys
from uuid import UUID
from database.db_manager import db_manager
from database.models import RoleEnum


async def list_users():
    """Показывает список всех пользователей"""
    try:
        # Получаем всех пользователей напрямую из БД
        async with db_manager.pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT id, tg_name, role, created_at FROM agents ORDER BY created_at DESC"
            )
            
            if not rows:
                print("📋 Пользователи не найдены.")
                return
            
            print(f"\n📋 Список пользователей ({len(rows)}):\n")
            print("-" * 80)
            print(f"{'ID':<38} {'Telegram':<25} {'Роль':<10} {'Дата создания'}")
            print("-" * 80)
            
            for row in rows:
                role_emoji = "👨‍🏫" if row['role'] == 'mentor' else "👨‍🎓"
                role_text = "Ментор" if row['role'] == 'mentor' else "Студент"
                created = row['created_at'].strftime("%Y-%m-%d %H:%M") if row['created_at'] else "N/A"
                print(f"{str(row['id']):<38} {row['tg_name']:<25} {role_emoji} {role_text:<6} {created}")
            
            print("-" * 80)
    except Exception as e:
        print(f"❌ Ошибка при получении списка пользователей: {e}")


async def add_user(tg_name: str, role: str = "student"):
    """Добавляет нового пользователя"""
    try:
        # Проверяем роль
        if role.lower() not in ['student', 'mentor', 'студент', 'ментор']:
            print("❌ Неверная роль. Используйте: student, mentor, студент или ментор")
            return
        
        # Преобразуем роль
        if role.lower() in ['mentor', 'ментор']:
            role_enum = RoleEnum.MENTOR
            role_text = "ментор"
        else:
            role_enum = RoleEnum.STUDENT
            role_text = "студент"
        
        # Проверяем, существует ли пользователь
        existing = await db_manager.get_agent_by_tg_name(tg_name)
        if existing:
            existing_role_emoji = "👨‍🏫" if existing.role == RoleEnum.MENTOR else "👨‍🎓"
            print(f"⚠️ Пользователь {tg_name} уже существует!")
            print(f"   ID: {existing.id}")
            print(f"   Роль: {existing_role_emoji} {existing.role.value}")
            return
        
        # Создаем пользователя
        agent = await db_manager.create_agent(tg_name, role_enum)
        role_emoji = "👨‍🏫" if role_enum == RoleEnum.MENTOR else "👨‍🎓"
        
        print(f"✅ Пользователь успешно добавлен!")
        print(f"   Telegram: {agent.tg_name}")
        print(f"   Роль: {role_emoji} {role_text}")
        print(f"   ID: {agent.id}")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")


async def delete_user(tg_name: str):
    """Удаляет пользователя"""
    try:
        # Проверяем существование пользователя
        agent = await db_manager.get_agent_by_tg_name(tg_name)
        if not agent:
            print(f"❌ Пользователь {tg_name} не найден.")
            return
        
        # Подтверждение
        print(f"\n⚠️ ВНИМАНИЕ: Вы собираетесь удалить пользователя:")
        print(f"   Telegram: {agent.tg_name}")
        print(f"   Роль: {agent.role.value}")
        print(f"   ID: {agent.id}")
        
        confirm = input("\nВы уверены? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена.")
            return
        
        # Удаляем пользователя
        async with db_manager.pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM agents WHERE tg_name = $1",
                tg_name
            )
        
        print(f"✅ Пользователь {tg_name} успешно удален.")
        
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")


async def change_role(tg_name: str, new_role: str):
    """Изменяет роль пользователя"""
    try:
        # Проверяем существование пользователя
        agent = await db_manager.get_agent_by_tg_name(tg_name)
        if not agent:
            print(f"❌ Пользователь {tg_name} не найден.")
            return
        
        # Проверяем роль
        if new_role.lower() not in ['student', 'mentor', 'студент', 'ментор']:
            print("❌ Неверная роль. Используйте: student, mentor, студент или ментор")
            return
        
        # Преобразуем роль
        if new_role.lower() in ['mentor', 'ментор']:
            role_enum = RoleEnum.MENTOR
            role_text = "ментор"
        else:
            role_enum = RoleEnum.STUDENT
            role_text = "студент"
        
        # Проверяем, не та же ли роль
        if agent.role == role_enum:
            print(f"⚠️ Пользователь {tg_name} уже имеет роль {role_text}.")
            return
        
        # Изменяем роль
        async with db_manager.pool.acquire() as connection:
            await connection.execute(
                "UPDATE agents SET role = $1 WHERE tg_name = $2",
                role_enum.value, tg_name
            )
        
        old_role_emoji = "👨‍🏫" if agent.role == RoleEnum.MENTOR else "👨‍🎓"
        new_role_emoji = "👨‍🏫" if role_enum == RoleEnum.MENTOR else "👨‍🎓"
        
        print(f"✅ Роль пользователя изменена!")
        print(f"   Telegram: {agent.tg_name}")
        print(f"   Старая роль: {old_role_emoji} {agent.role.value}")
        print(f"   Новая роль: {new_role_emoji} {role_text}")
        
    except Exception as e:
        print(f"❌ Ошибка при изменении роли: {e}")


async def show_user(tg_name: str):
    """Показывает информацию о пользователе"""
    try:
        agent = await db_manager.get_agent_by_tg_name(tg_name)
        if not agent:
            print(f"❌ Пользователь {tg_name} не найден.")
            return
        
        role_emoji = "👨‍🏫" if agent.is_mentor() else "👨‍🎓"
        role_text = "Ментор" if agent.is_mentor() else "Студент"
        created = agent.created_at.strftime("%Y-%m-%d %H:%M:%S") if agent.created_at else "N/A"
        
        print(f"\n👤 Информация о пользователе:")
        print("-" * 50)
        print(f"Telegram: {agent.tg_name}")
        print(f"Роль: {role_emoji} {role_text}")
        print(f"ID: {agent.id}")
        print(f"Дата создания: {created}")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Ошибка при получении информации о пользователе: {e}")


def print_help():
    """Показывает справку по использованию"""
    print("""
📚 Управление пользователями в базе данных

Использование:
  python manage_users.py <команда> [аргументы]

Команды:
  list                    - Показать список всех пользователей
  add <tg_name> [role]   - Добавить пользователя (role: student/mentor, по умолчанию student)
  delete <tg_name>       - Удалить пользователя
  role <tg_name> <role>  - Изменить роль пользователя (role: student/mentor)
  show <tg_name>         - Показать информацию о пользователе
  help                   - Показать эту справку

Примеры:
  python manage_users.py list
  python manage_users.py add @username mentor
  python manage_users.py add username123 student
  python manage_users.py role @username mentor
  python manage_users.py delete @username
  python manage_users.py show @username
""")


async def main():
    """Главная функция"""
    # Инициализируем подключение к БД
    await db_manager.connect()
    
    try:
        if len(sys.argv) < 2:
            print_help()
            return
        
        command = sys.argv[1].lower()
        
        if command == "list":
            await list_users()
        
        elif command == "add":
            if len(sys.argv) < 3:
                print("❌ Укажите Telegram имя пользователя")
                print("Использование: python manage_users.py add <tg_name> [role]")
                return
            tg_name = sys.argv[2]
            role = sys.argv[3] if len(sys.argv) > 3 else "student"
            await add_user(tg_name, role)
        
        elif command == "delete":
            if len(sys.argv) < 3:
                print("❌ Укажите Telegram имя пользователя")
                print("Использование: python manage_users.py delete <tg_name>")
                return
            tg_name = sys.argv[2]
            await delete_user(tg_name)
        
        elif command == "role":
            if len(sys.argv) < 4:
                print("❌ Укажите Telegram имя пользователя и новую роль")
                print("Использование: python manage_users.py role <tg_name> <role>")
                return
            tg_name = sys.argv[2]
            new_role = sys.argv[3]
            await change_role(tg_name, new_role)
        
        elif command == "show":
            if len(sys.argv) < 3:
                print("❌ Укажите Telegram имя пользователя")
                print("Использование: python manage_users.py show <tg_name>")
                return
            tg_name = sys.argv[2]
            await show_user(tg_name)
        
        elif command == "help":
            print_help()
        
        else:
            print(f"❌ Неизвестная команда: {command}")
            print_help()
    
    finally:
        # Закрываем подключение к БД
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
