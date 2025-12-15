#!/usr/bin/env python3
"""
Скрипт для добавления вопросов в базу данных
Позволяет быстро добавить вопросы для тестирования
"""

import asyncio
from database.db_manager import db_manager


# Примеры вопросов для добавления в БД
SAMPLE_QUESTIONS = [
    {
        "question": "Что такое Python?",
        "answer_example": "Python - это высокоуровневый язык программирования общего назначения с динамической типизацией.",
        "priority": 1
    },
    {
        "question": "Что такое переменная в программировании?",
        "answer_example": "Переменная - это именованная область памяти, которая хранит значение и может изменяться в процессе выполнения программы.",
        "priority": 1
    },
    {
        "question": "Объясните разницу между списком (list) и кортежем (tuple) в Python.",
        "answer_example": "Список - это изменяемая (mutable) структура данных, а кортеж - неизменяемая (immutable). Списки создаются с квадратными скобками [], кортежи - с круглыми ().",
        "priority": 2
    },
    {
        "question": "Что такое функция в программировании?",
        "answer_example": "Функция - это блок кода, который выполняет определенную задачу и может быть вызван из других частей программы. Функции помогают избежать дублирования кода.",
        "priority": 1
    },
    {
        "question": "Объясните концепцию ООП (объектно-ориентированное программирование).",
        "answer_example": "ООП - это парадигма программирования, основанная на концепции объектов, которые содержат данные (атрибуты) и методы (функции). Основные принципы: инкапсуляция, наследование, полиморфизм.",
        "priority": 3
    },
    {
        "question": "Что такое база данных?",
        "answer_example": "База данных - это организованная коллекция данных, хранящаяся и доступная электронным способом. Позволяет эффективно хранить, извлекать и управлять информацией.",
        "priority": 1
    },
    {
        "question": "Объясните разницу между SQL и NoSQL базами данных.",
        "answer_example": "SQL базы данных - реляционные, используют таблицы и структурированные схемы. NoSQL - нереляционные, более гибкие, подходят для больших объемов неструктурированных данных.",
        "priority": 2
    },
    {
        "question": "Что такое API?",
        "answer_example": "API (Application Programming Interface) - это набор правил и протоколов, который позволяет различным программным приложениям взаимодействовать друг с другом.",
        "priority": 1
    },
    {
        "question": "Объясните концепцию REST API.",
        "answer_example": "REST (Representational State Transfer) - архитектурный стиль для создания веб-сервисов. Использует HTTP методы (GET, POST, PUT, DELETE) и работает с ресурсами через URL.",
        "priority": 2
    },
    {
        "question": "Что такое Git и для чего он используется?",
        "answer_example": "Git - это распределенная система контроля версий, которая позволяет отслеживать изменения в коде, создавать ветки, объединять изменения и работать в команде над одним проектом.",
        "priority": 1
    }
]


async def add_questions():
    """Добавляет примеры вопросов в БД"""
    try:
        print("📝 Добавление вопросов в базу данных...\n")
        
        added_count = 0
        skipped_count = 0
        
        for i, q_data in enumerate(SAMPLE_QUESTIONS, 1):
            try:
                # Проверяем, существует ли уже такой вопрос
                all_questions = await db_manager.get_all_questions()
                question_exists = any(
                    q.question.lower().strip() == q_data["question"].lower().strip() 
                    for q in all_questions
                )
                
                if question_exists:
                    print(f"⏭️  {i}. Пропущен (уже существует): {q_data['question'][:50]}...")
                    skipped_count += 1
                    continue
                
                # Создаем вопрос
                question = await db_manager.create_question(
                    question=q_data["question"],
                    answer_example=q_data.get("answer_example"),
                    priority=q_data.get("priority", 0)
                )
                
                print(f"✅ {i}. Добавлен: {question.question[:60]}...")
                print(f"   ID: {question.id}")
                print(f"   Приоритет: {question.priority}\n")
                added_count += 1
                
            except Exception as e:
                print(f"❌ {i}. Ошибка при добавлении вопроса: {e}\n")
                import traceback
                traceback.print_exc()
        
        all_questions = await db_manager.get_all_questions()
        print("-" * 60)
        print(f"📊 Итого:")
        print(f"   ✅ Добавлено: {added_count}")
        print(f"   ⏭️  Пропущено: {skipped_count}")
        print(f"   📋 Всего в БД: {len(all_questions)}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении вопросов: {e}")
        import traceback
        traceback.print_exc()


async def list_questions():
    """Показывает список всех вопросов в БД"""
    try:
        questions = await db_manager.get_all_questions()
        
        if not questions:
            print("📋 Вопросы не найдены в БД.")
            return
        
        print(f"\n📋 Список вопросов в БД ({len(questions)}):\n")
        print("-" * 80)
        
        for i, question in enumerate(questions, 1):
            print(f"{i}. {question.question[:70]}{'...' if len(question.question) > 70 else ''}")
            print(f"   ID: {question.id}")
            print(f"   Приоритет: {question.priority}")
            if question.answer_example:
                print(f"   Пример ответа: {question.answer_example[:50]}...")
            print()
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка вопросов: {e}")


async def add_custom_question(question_text: str, answer_example: str = None, priority: int = 0):
    """Добавляет один вопрос в БД"""
    try:
        question = await db_manager.create_question(
            question=question_text,
            answer_example=answer_example,
            priority=priority
        )
        
        print(f"✅ Вопрос успешно добавлен!")
        print(f"   Вопрос: {question.question}")
        print(f"   ID: {question.id}")
        print(f"   Приоритет: {question.priority}")
        if question.answer_example:
            print(f"   Пример ответа: {question.answer_example[:50]}...")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении вопроса: {e}")


async def main():
    """Главная функция"""
    import sys
    
    # Инициализируем подключение к БД
    try:
        await db_manager.connect()
        print("✅ Подключение к БД установлено\n")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "list":
                await list_questions()
            
            elif command == "add":
                if len(sys.argv) < 3:
                    print("❌ Укажите текст вопроса")
                    print("Использование: python add_questions.py add \"Текст вопроса\" [пример_ответа] [приоритет]")
                    return
                
                question_text = sys.argv[2]
                answer_example = sys.argv[3] if len(sys.argv) > 3 else None
                priority = int(sys.argv[4]) if len(sys.argv) > 4 else 0
                
                await add_custom_question(question_text, answer_example, priority)
            
            else:
                print(f"❌ Неизвестная команда: {command}")
                print("Использование: python add_questions.py [list|add]")
        else:
            # По умолчанию добавляем примеры вопросов
            await add_questions()
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закрываем подключение к БД
        await db_manager.disconnect()
        print("\n✅ Подключение к БД закрыто")


if __name__ == "__main__":
    asyncio.run(main())
