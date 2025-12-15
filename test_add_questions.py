import asyncio
from database.db_manager import db_manager

async def main():
    print("Starting...")
    await db_manager.connect()
    print("Connected!")
    
    # Добавляем простые вопросы
    questions = [
        "Как называется язык программирования Python?",
        "Что такое переменная?",
        "Что такое функция?"
    ]
    
    for q_text in questions:
        try:
            # Проверяем, есть ли уже такой вопрос
            all_q = await db_manager.get_all_questions()
            if any(q.question == q_text for q in all_q):
                print(f"Skip: {q_text}")
                continue
            
            q = await db_manager.create_question(question=q_text, priority=1)
            print(f"Added: {q.question} (ID: {q.id})")
        except Exception as e:
            print(f"Error: {e}")
    
    # Показываем все вопросы
    all_q = await db_manager.get_all_questions()
    print(f"\nTotal questions: {len(all_q)}")
    for q in all_q:
        print(f"  - {q.question}")
    
    await db_manager.disconnect()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
