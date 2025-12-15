# Telegram Bot

Telegram бот с интеграцией базы данных PostgreSQL для управления агентами, вопросами, навыками и результатами тестирования.

## Быстрый старт

**Подробное руководство по установке смотрите в [SETUP_GUIDE.md](SETUP_GUIDE.md)**

**📖 Полное руководство пользователя: [USER_GUIDE.md](USER_GUIDE.md)**

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Установите PostgreSQL (если еще не установлен):
   - Скачайте с официального сайта: https://www.postgresql.org/download/windows/
   - Или используйте установщик: https://www.postgresql.org/download/

3. Настройте переменные окружения:
   
   **Windows:**
   ```powershell
   copy env.example .env
   ```
   
   **Linux/Mac:**
   ```bash
   cp env.example .env
   ```
   
   Откройте файл `.env` и укажите свои параметры подключения к БД и токен бота.

4. Создайте базу данных:
   
   **Перед созданием БД рекомендуется проверить подключение:**
   ```bash
   python check_postgresql.py
   ```
   
   **Создание базы данных:**
   ```bash
   python create_database.py
   ```
   
   **Альтернативные способы (если первый не работает):**
   - Linux/Mac (если PostgreSQL утилиты в PATH):
     ```bash
     createdb telegram_bot
     ```
   - Windows (через psql):
     ```powershell
     psql -U postgres -c "CREATE DATABASE telegram_bot;"
     ```

5. Инициализируйте схему базы данных:
```bash
python init_database.py
```

## Запуск

Запустите бота командой:
```bash
python bot.py
```

## Структура базы данных

### Таблицы:

- **agents** - Агенты (пользователи бота)
  - `id` (uuid) - Уникальный идентификатор
  - `tg_name` (varchar) - Имя в Telegram (уникальное)
  - `role` (enum) - Роль: `student` (студент) или `mentor` (ментор/админ)
  - `created_at` (timestamp) - Дата создания
  
  **Роли:**
  - `student` - Студент (роль по умолчанию)
  - `mentor` - Ментор/Администратор (может управлять системой)

- **questions** - Вопросы для тестирования
  - `id` (uuid) - Уникальный идентификатор
  - `question` (varchar) - Текст вопроса
  - `answer_example` (varchar) - Пример ответа
  - `priority` (integer) - Приоритет вопроса

- **skills** - Навыки
  - `id` (uuid) - Уникальный идентификатор
  - `skill` (varchar) - Название навыка
  - `description` (varchar) - Описание
  - `grade` (enum) - Оценка: not_passed, low, passed

- **skills_questions** - Связь навыков и вопросов
  - `id` (uuid) - Уникальный идентификатор
  - `skill_id` (uuid) - ID навыка
  - `question_id` (uuid) - ID вопроса

- **test_result** - Результаты тестирования
  - `id` (uuid) - Уникальный идентификатор
  - `summary` (varchar) - Краткое резюме
  - `test_timing` (int) - Время прохождения теста
  - `skills_total` (int) - Всего навыков
  - `skills_not_passed` (int) - Не пройдено
  - `skills_low` (int) - Низкий уровень
  - `skills_passed` (int) - Пройдено
  - `agent_id` (uuid) - ID агента
  - `created_at` (timestamp) - Дата создания

- **test_details** - Детали тестирования
  - `id` (uuid) - Уникальный идентификатор
  - `test_result_id` (uuid) - ID результата теста
  - `question_id` (uuid) - ID вопроса
  - `answer` (varchar) - Ответ
  - `answer_analyze_result` (varchar) - Результат анализа ответа

## Структура проекта

- `bot.py` - Основной файл бота
- `check_postgresql.py` - Скрипт диагностики подключения к PostgreSQL
- `create_database.py` - Скрипт создания БД (работает на всех ОС)
- `init_database.py` - Скрипт инициализации схемы БД
- `migrate_add_roles.py` - Скрипт миграции для добавления ролей
- `add_mentor.py` - Скрипт для добавления менторов
- `database/` - Пакет для работы с БД
  - `schema.sql` - SQL схема базы данных
  - `models.py` - Модели данных
  - `db_manager.py` - Менеджер для работы с БД
  - `config.py` - Конфигурация подключения
  - `example_usage.py` - Примеры использования БД
- `requirements.txt` - Зависимости проекта
- `env.example` - Пример конфигурации (.env файл)
- `README.md` - Документация
- `SETUP_GUIDE.md` - Подробное руководство по установке

## Функциональность

### Команды для всех пользователей:
- `/start` - Запустить бота (автоматическая регистрация)
- `/help` - Показать справку
- `/skills` - Список всех компетенций
- `/questions` - Список всех вопросов
- `/skill <id>` - Детали компетенции
- `/question <id>` - Детали вопроса

### Команды для менторов (администраторов):
- `/add_skill` - Добавить новую компетенцию
- `/add_question` - Добавить новый вопрос
- `/edit_skill <id>` - Редактировать компетенцию
- `/edit_question <id>` - Редактировать вопрос
- `/delete_skill <id>` - Удалить компетенцию
- `/delete_question <id>` - Удалить вопрос
- `/link <skill_id> <question_id>` - Связать компетенцию с вопросом
- `/unlink <skill_id> <question_id>` - Удалить связь между компетенцией и вопросом

**Важно:** Только пользователи с ролью "ментор" могут добавлять, редактировать и удалять компетенции и вопросы.

## Использование базы данных

Пример использования в коде бота:

```python
from database.db_manager import db_manager

# При запуске бота
await db_manager.connect()

# Создание агента
agent = await db_manager.create_agent("username")

# Создание вопроса
question = await db_manager.create_question(
    "Что такое Python?",
    answer_example="Python - это язык программирования",
    priority=1
)

# При остановке бота
await db_manager.disconnect()
```
