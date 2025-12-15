-- SQL скрипт для добавления простых тестовых вопросов
-- Запустите этот скрипт в вашей PostgreSQL БД

-- Простые вопросы для тестирования функционала "Мои результаты"
INSERT INTO questions (id, question, answer_example, priority)
VALUES 
    (uuid_generate_v4(), 'Как называется язык программирования Python?', 'Python - это язык программирования', 1),
    (uuid_generate_v4(), 'Что такое переменная?', 'Переменная хранит данные', 1),
    (uuid_generate_v4(), 'Что такое функция?', 'Функция - это блок кода', 1),
    (uuid_generate_v4(), 'Что такое база данных?', 'База данных хранит информацию', 1),
    (uuid_generate_v4(), 'Что такое API?', 'API - это интерфейс для взаимодействия', 1)
ON CONFLICT DO NOTHING;

-- Проверка добавленных вопросов
SELECT id, question, priority FROM questions ORDER BY priority, question;
