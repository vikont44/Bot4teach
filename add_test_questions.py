#!/usr/bin/env python3
"""
Скрипт для добавления простых тестовых вопросов
"""

import asyncio
import sys
from database.db_manager import db_manager

# Простые вопросы для тестирования функционала "Мои результаты"
TEST_QUESTIONS = [
    "Как называется язык программирования Python?",
    "Что такое переменная?",
    "Что такое функция?",
    "Что такое база данных?",
    "Что такое API?"
]

async def add_questions():
    """Добавляет вопросы в БД"""
    try:
        # Подключение
        print("Подключение к БД...", file=sys.stderr)
        await db_manager.connect()
        print("Подключено!", file=sys.stderr)
        
        added = 0
        skipped = 0
        
        # Получаем все существующие вопросы
        existing_questions = await db_manager.get_all_questions()
        existing_texts = {q.question.lower().strip() for q in existing_questions}
        
        # Добавляем новые вопросы
        for q_text in TEST_QUESTIONS:
            if q_text.lower().strip() in existing_texts:
                print(f"Пропущен (уже есть): {q_text}", file=sys.stderr)
                skipped += 1
                continue
            
            try:
                question = await db_manager.create_question(
                    question=q_text,
                    answer_example=f"Пример ответа на: {q_text}",
                    priority=1
                )
                print(f"Добавлен: {question.question} (ID: {question.id})", file=sys.stderr)
                added += 1
            except Exception as e:
                print(f"Ошибка при добавлении '{q_text}': {e}", file=sys.stderr)
        
        # Показываем итоги
        all_questions = await db_manager.get_all_questions()
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Итого:", file=sys.stderr)
        print(f"  Добавлено: {added}", file=sys.stderr)
        print(f"  Пропущено: {skipped}", file=sys.stderr)
        print(f"  Всего в БД: {len(all_questions)}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        
        # Выводим список всех вопросов
        if all_questions:
            print("Список всех вопросов в БД:", file=sys.stderr)
            for i, q in enumerate(all_questions, 1):
                print(f"  {i}. {q.question}", file=sys.stderr)
        
        print("\n✅ Вопросы успешно добавлены в БД!", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    finally:
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(add_questions())
