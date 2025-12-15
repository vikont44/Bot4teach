# Исправление проблемы с Python 3.14

## Проблема

Ошибка при запуске бота:
```
AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb' 
and no __dict__ for setting new attributes
```

## Причина

Версия `python-telegram-bot==20.7` несовместима с Python 3.14 из-за изменений в обработке приватных атрибутов классов.

## Решение

Обновите библиотеку до версии 21.0 или выше:

```bash
pip install --upgrade python-telegram-bot>=21.0
```

Или переустановите все зависимости:

```bash
pip install -r requirements.txt --upgrade
```

## Проверка версии

После обновления проверьте версию:

```bash
pip show python-telegram-bot
```

Должна быть версия 21.0 или выше.

## Если проблема осталась

1. Полностью переустановите библиотеку:
```bash
pip uninstall python-telegram-bot
pip install python-telegram-bot>=21.0
```

2. Проверьте версию Python:
```bash
python --version
```

3. Если используете Python 3.14, рекомендуется использовать версию библиотеки 21.0+

## Альтернативное решение

Если по какой-то причине нужна версия 20.7, используйте Python 3.11 или 3.12 вместо 3.14.

