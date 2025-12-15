#!/usr/bin/env python3
"""
Простой скрипт для добавления тестовых вопросов в БД
"""

import asyncio
import sys
from database.db_manager import db_manager

# Простые вопросы для тестирования
SIMPLE_QUESTIONS = [
    {
        "question": "Как называется язык программирования Python?",
        "answer_example": "Python - это язык программирования",
        "priority": 1
    },
    {
        "question": "Что такое переменная?",
        "answer_example": "Переменная хранит данные",
        "priority": 1
    },
    {
        "question": "Что такое функция?",
        "answer_example": "Функция - это блок кода",
        "priority": 1
    }
]


async def main():
    """Добавляет простые вопросы в БД"""
    import sys
    sys.stdout.flush()
    print("🔌 Подключение к БД...", flush=True)
    try:
        await db_manager.connect()
        print("✅ Подключено!\n", flush=True)
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return
    
    try:
        print("📝 Добавление вопросов...\n", flush=True)
        added = 0
        skipped = 0
        
        for i, q in enumerate(SIMPLE_QUESTIONS, 1):
            try:
                # Проверяем существование
                all_q = await db_manager.get_all_questions()
                exists = any(q_obj.question.lower().strip() == q["question"].lower().strip() for q_obj in all_q)
                
                if exists:
                    print(f"⏭️  {i}. Пропущен: {q['question'][:50]}...", flush=True)
                    skipped += 1
                    continue
                
                # Добавляем
                question = await db_manager.create_question(
                    question=q["question"],
                    answer_example=q.get("answer_example"),
                    priority=q.get("priority", 0)
                )
                
                print(f"✅ {i}. Добавлен: {question.question}", flush=True)
                print(f"   ID: {question.id}\n", flush=True)
                added += 1
                
            except Exception as e:
                print(f"❌ {i}. Ошибка: {e}\n", flush=True)
                import traceback
                traceback.print_exc()
        
        # Показываем итоги
        all_questions = await db_manager.get_all_questions()
        print("-" * 60, flush=True)
        print(f"📊 Итого:", flush=True)
        print(f"   ✅ Добавлено: {added}", flush=True)
        print(f"   ⏭️  Пропущено: {skipped}", flush=True)
        print(f"   📋 Всего в БД: {len(all_questions)}", flush=True)
        print("-" * 60, flush=True)
        
        if len(all_questions) > 0:
            print("\n📋 Список всех вопросов в БД:", flush=True)
            for i, q in enumerate(all_questions, 1):
                print(f"   {i}. {q.question[:60]}...", flush=True)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.disconnect()
        print("\n✅ Готово!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
