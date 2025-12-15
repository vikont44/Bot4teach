import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.error import Conflict, NetworkError
from uuid import UUID
from typing import Optional

from database.db_manager import db_manager
from database.models import GradeEnum

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8486918034:AAFI7u2rLZm7eYEUhmtVOfNeKSD2lKcIQ_E"

# Состояния для ConversationHandler
(ADD_SKILL_NAME, ADD_SKILL_DESC,
 ADD_QUESTION_TEXT, ADD_QUESTION_EXAMPLE, ADD_QUESTION_PRIORITY,
 EDIT_SKILL_CHOICE, EDIT_SKILL_FIELD, EDIT_SKILL_VALUE,
 EDIT_QUESTION_CHOICE, EDIT_QUESTION_FIELD, EDIT_QUESTION_VALUE,
 LINK_SKILL_ID, LINK_QUESTION_ID,
 TEST_START, TEST_QUESTION, TEST_ANSWER) = range(16)


def get_user_tg_name(update: Update) -> str:
    """Получает имя пользователя Telegram"""
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username:
        return user.username
    return str(user.id)


def get_mentor_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру для ментора"""
    keyboard = [
        [
            KeyboardButton("📋 Компетенции"),
            KeyboardButton("❓ Вопросы")
        ],
        [
            KeyboardButton("➕ Добавить"),
            KeyboardButton("✏️ Редактировать")
        ],
        [
            KeyboardButton("🗑️ Удалить"),
            KeyboardButton("🔗 Связать")
        ],
        [
            KeyboardButton("🏠 Меню"),
            KeyboardButton("ℹ️ Помощь")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_student_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру для студента"""
    keyboard = [
        [
            KeyboardButton("🧪 Начать тест")
        ],
        [
            KeyboardButton("📊 Мои результаты")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет, есть ли пользователь в БД"""
    tg_name = get_user_tg_name(update)
    agent = await db_manager.get_agent_by_tg_name(tg_name)
    if not agent:
        if update.message:
            await update.message.reply_text(
                "❌ <b>Доступ запрещен</b>\n\n"
                "Вы не зарегистрированы в системе.\n"
                "Обратитесь к администратору для получения доступа.",
                parse_mode='HTML'
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "❌ Вы не зарегистрированы в системе",
                show_alert=True
            )
        return False
    return True


async def check_mentor_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет, является ли пользователь ментором"""
    # Сначала проверяем доступ
    if not await check_user_access(update, context):
        return False
    
    tg_name = get_user_tg_name(update)
    is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
    if not is_mentor:
        if update.message:
            await update.message.reply_text(
                "❌ У вас нет прав для выполнения этой команды. "
                "Только менторы могут управлять компетенциями и вопросами."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "❌ Только менторы могут выполнять это действие",
                show_alert=True
            )
    return is_mentor


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    tg_name = get_user_tg_name(update)
    agent = await db_manager.get_agent_by_tg_name(tg_name)
    
    role_text = "👨‍🏫 ментор" if agent.is_mentor() else "👨‍🎓 студент"
    text = f"👋 Привет! Твоя роль: {role_text}\n\n"
    
    if agent.is_mentor():
        text += "👨‍🏫 <b>Добро пожаловать в панель ментора!</b>\n\n"
        text += "Используй кнопки внизу для управления компетенциями и вопросами.\n"
        text += "Или используй команду /panel для inline-панели."
        await update.message.reply_text(
            text,
            reply_markup=get_mentor_keyboard(),
            parse_mode='HTML'
        )
    else:
        text += "👨‍🎓 <b>Добро пожаловать!</b>\n\n"
        text += "Используй кнопки внизу для навигации."
        await update.message.reply_text(
            text,
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    tg_name = get_user_tg_name(update)
    is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
    
    help_text = "📚 Доступные команды:\n\n"
    help_text += "👁️ Просмотр:\n"
    help_text += "/skills - Список всех компетенций\n"
    help_text += "/questions - Список всех вопросов\n"
    help_text += "/skill <id> - Детали компетенции\n"
    help_text += "/question <id> - Детали вопроса\n"
    
    if is_mentor:
        help_text += "\n✏️ Управление (только для менторов):\n"
        help_text += "/panel - Панель ментора с кнопками\n"
        help_text += "/add_skill - Добавить компетенцию\n"
        help_text += "/edit_skill - Редактировать компетенцию\n"
        help_text += "/delete_skill <id> - Удалить компетенцию\n"
        help_text += "/link - Связать компетенцию с вопросом\n"
        help_text += "/unlink - Удалить связь\n"
        help_text += "\n⚠️ Вопросы управляются напрямую через БД\n"
    else:
        help_text = "👨‍🎓 <b>Справка для студента</b>\n\n"
        help_text += "🧪 <b>Начать тест</b> - Начать прохождение тестирования по вопросам\n"
        help_text += "📊 <b>Мои результаты</b> - Просмотреть результаты пройденных тестов\n\n"
        help_text += "💡 <i>Используйте кнопки внизу для навигации</i>"
    
    keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
    await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode='HTML' if not is_mentor else None)


async def mentor_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает панель ментора с inline кнопками"""
    if not await check_user_access(update, context):
        return
    if not await check_mentor_permission(update, context):
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Список компетенций", callback_data="list_skills"),
            InlineKeyboardButton("❓ Список вопросов", callback_data="list_questions")
        ],
        [
            InlineKeyboardButton("➕ Добавить компетенцию", callback_data="add_skill")
        ],
        [
            InlineKeyboardButton("✏️ Редактировать компетенцию", callback_data="edit_skill")
        ],
        [
            InlineKeyboardButton("🗑️ Удалить компетенцию", callback_data="delete_skill")
        ],
        [
            InlineKeyboardButton("🔗 Связать", callback_data="link"),
            InlineKeyboardButton("🔓 Развязать", callback_data="unlink")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍🏫 <b>Панель ментора (Inline)</b>\n\n"
        "Выберите действие:\n\n"
        "ℹ️ <i>Вопросы управляются напрямую через БД</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def handle_keyboard_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщения от постоянной клавиатуры"""
    if not update.message:
        return
    
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    text = update.message.text
    tg_name = get_user_tg_name(update)
    agent = await db_manager.get_agent_by_tg_name(tg_name)
    
    if not agent:
        return
    
    is_mentor = agent.is_mentor()
    
    # Если идет тест, обрабатываем ответ
    # Проверяем это в первую очередь, до обработки других команд
    if 'test_questions' in context.user_data and 'test_current_index' in context.user_data:
        # Проверяем, что это не команда клавиатуры (которые могут отменить тест)
        keyboard_commands = ["🏠 Меню", "ℹ️ Помощь", "📋 Компетенции", "❓ Вопросы", 
                             "🧪 Начать тест", "📊 Мои результаты", "➕ Добавить", 
                             "✏️ Редактировать", "🗑️ Удалить", "🔗 Связать", "🔓 Развязать"]
        
        # Если это команда клавиатуры во время теста, игнорируем её (кроме отмены)
        if text in keyboard_commands and text != "/cancel":
            await update.message.reply_text(
                "⚠️ <b>Идет тестирование!</b>\n\n"
                "Пожалуйста, завершите тест или используйте /cancel для отмены.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        # Обрабатываем ответ на вопрос теста
        await process_test_answer(update, context)
        return
    
    # Если есть активное действие для ментора, пропускаем обработку клавиатуры
    if context.user_data.get('action') and is_mentor:
        return
    
    # Обработка команд для студентов
    if not is_mentor:
        if text == "🧪 Начать тест":
            await start_test(update, context)
            return
        
        if text == "📊 Мои результаты":
            await show_my_results(update, context)
            return
        
        # Если это не команда клавиатуры, игнорируем
        return
    
    # Обработка команд для менторов
    
    # Очищаем предыдущие действия при возврате в главное меню
    if text == "🏠 Меню":
        context.user_data.clear()
        await show_main_menu(update, context)
        return
    
    if text == "ℹ️ Помощь":
        await show_mentor_help(update, context)
        return
    
    if text == "📋 Компетенции":
        await list_skills(update, context)
        return
    
    if text == "❓ Вопросы":
        await list_questions(update, context)
        return
    
    if text == "➕ Добавить":
        context.user_data['action'] = 'add_skill'
        await update.message.reply_text(
            "➕ <b>Добавление новой компетенции</b>\n\n"
            "Введите название компетенции:\n\n"
            "💡 <i>Для отмены используйте /cancel</i>",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if text == "✏️ Редактировать":
        context.user_data['action'] = 'edit_skill'
        await update.message.reply_text(
            "✏️ <b>Редактирование компетенции</b>\n\n"
            "Введите ID компетенции для редактирования:\n\n"
            "💡 <i>Используйте кнопку '📋 Компетенции' для просмотра ID</i>",
            parse_mode='HTML'
        )
        return
    
    if text == "🗑️ Удалить":
        context.user_data['action'] = 'delete_skill'
        await update.message.reply_text(
            "🗑️ <b>Удаление компетенции</b>\n\n"
            "Введите ID компетенции для удаления:\n\n"
            "⚠️ <b>Внимание:</b> Это действие нельзя отменить!\n"
            "💡 <i>Используйте кнопку '📋 Компетенции' для просмотра ID</i>",
            parse_mode='HTML'
        )
        return
    
    if text == "🔗 Связать":
        context.user_data['action'] = 'link'
        await update.message.reply_text(
            "🔗 <b>Связывание компетенции с вопросом</b>\n\n"
            "Введите ID компетенции и ID вопроса через пробел:\n"
            "Например: <code>skill_id question_id</code>\n\n"
            "💡 <i>Используйте кнопку '📋 Компетенции' или '❓ Вопросы' для просмотра ID</i>",
            parse_mode='HTML'
        )
        return
    


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню ментора"""
    text = (
        "👨‍🏫 <b>Главное меню ментора</b>\n\n"
        "<b>Описание кнопок:</b>\n\n"
        "📋 <b>Компетенции</b> - Показать список всех компетенций с их ID\n"
        "❓ <b>Вопросы</b> - Показать список всех вопросов с их ID (только просмотр)\n\n"
        "➕ <b>Добавить</b> - Создать новую компетенцию\n"
        "✏️ <b>Редактировать</b> - Изменить название или описание компетенции\n"
        "🗑️ <b>Удалить</b> - Удалить компетенцию (необратимо!)\n"
        "🔗 <b>Связать</b> - Связать компетенцию с вопросом\n\n"
        "🏠 <b>Меню</b> - Вернуться в это меню\n"
        "ℹ️ <b>Помощь</b> - Подробная справка\n\n"
        "⚠️ <i>Вопросы управляются напрямую через БД</i>"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_mentor_keyboard(),
        parse_mode='HTML'
    )


async def show_mentor_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку для ментора"""
    text = (
        "ℹ️ <b>Подробная справка для ментора</b>\n\n"
        "<b>📋 Компетенции</b>\n"
        "Показывает список всех компетенций с их ID, названиями и описаниями.\n"
        "Используйте ID для редактирования, удаления или связывания.\n\n"
        
        "<b>❓ Вопросы</b>\n"
        "Показывает список всех вопросов с их ID и приоритетами.\n"
        "Вопросы управляются напрямую через БД (не через бота).\n\n"
        
        "<b>➕ Добавить</b>\n"
        "Создание новой компетенции:\n"
        "1. Нажмите кнопку '➕ Добавить'\n"
        "2. Введите название компетенции\n"
        "3. Введите описание (или /skip для пропуска)\n\n"
        
        "<b>✏️ Редактировать</b>\n"
        "Изменение компетенции:\n"
        "1. Нажмите кнопку '✏️ Редактировать'\n"
        "2. Введите ID компетенции (из списка '📋 Компетенции')\n"
        "3. Выберите что изменить: 1 - Название, 2 - Описание\n"
        "4. Введите новое значение\n\n"
        
        "<b>🗑️ Удалить</b>\n"
        "Удаление компетенции (необратимо!):\n"
        "1. Нажмите кнопку '🗑️ Удалить'\n"
        "2. Введите ID компетенции для удаления\n\n"
        
        "<b>🔗 Связать</b>\n"
        "Связывание компетенции с вопросом:\n"
        "1. Нажмите кнопку '🔗 Связать'\n"
        "2. Введите: <code>skill_id question_id</code> (через пробел)\n"
        "Пример: <code>123e4567-e89b-12d3-a456-426614174000 987fcdeb-51a2-43d1-b789-123456789abc</code>\n\n"
        
        "💡 <i>Для отмены любой операции используйте /cancel</i>"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_mentor_keyboard(),
        parse_mode='HTML'
    )




async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки панели ментора"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    tg_name = get_user_tg_name(update)
    if not await db_manager.is_mentor_by_tg_name(tg_name):
        await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    callback_data = query.data
    
    if callback_data == "list_skills":
        await list_skills_callback(query, context)
    elif callback_data == "list_questions":
        await list_questions_callback(query, context)
    elif callback_data == "add_skill":
        await query.edit_message_text(
            "📝 Добавление новой компетенции.\n"
            "Введите название компетенции:"
        )
        context.user_data['action'] = 'add_skill'
    elif callback_data == "edit_skill":
        await query.edit_message_text(
            "✏️ Редактирование компетенции\n\n"
            "Введите ID компетенции для редактирования:"
        )
        context.user_data['action'] = 'edit_skill'
    elif callback_data == "delete_skill":
        await query.edit_message_text(
            "🗑️ Удаление компетенции\n\n"
            "Введите ID компетенции для удаления:"
        )
        context.user_data['action'] = 'delete_skill'
    elif callback_data == "link":
        await query.edit_message_text(
            "🔗 Связывание компетенции с вопросом\n\n"
            "Введите ID компетенции и ID вопроса через пробел:\n"
            "Например: <code>skill_id question_id</code>",
            parse_mode='HTML'
        )
        context.user_data['action'] = 'link'
    elif callback_data == "unlink":
        await query.edit_message_text(
            "🔓 Развязывание компетенции и вопроса\n\n"
            "Введите ID компетенции и ID вопроса через пробел:\n"
            "Например: <code>skill_id question_id</code>",
            parse_mode='HTML'
        )
        context.user_data['action'] = 'unlink'


async def list_skills_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список компетенций через callback"""
    try:
        skills = await db_manager.get_all_skills()
        if not skills:
            await query.edit_message_text("📋 Компетенции не найдены.")
            return
        
        text = "📋 Список компетенций:\n\n"
        for i, skill in enumerate(skills, 1):
            text += f"{i}. <b>{skill.skill}</b>\n"
            text += f"   ID: <code>{str(skill.id)[:8]}</code>\n"
            if skill.description:
                text += f"   Описание: {skill.description[:50]}...\n" if len(skill.description) > 50 else f"   Описание: {skill.description}\n"
            text += "\n"
        
        await query.edit_message_text(text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка компетенций: {e}")
        await query.edit_message_text("❌ Ошибка при получении списка компетенций.")


async def list_questions_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список вопросов через callback"""
    try:
        questions = await db_manager.get_all_questions()
        if not questions:
            await query.edit_message_text("❓ Вопросы не найдены.")
            return
        
        text = "❓ Список вопросов:\n\n"
        for i, question in enumerate(questions, 1):
            text += f"{i}. {question.question[:60]}...\n" if len(question.question) > 60 else f"{i}. {question.question}\n"
            text += f"   ID: <code>{str(question.id)[:8]}</code>\n"
            text += f"   Приоритет: {question.priority}\n\n"
        
        await query.edit_message_text(text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка вопросов: {e}")
        await query.edit_message_text("❌ Ошибка при получении списка вопросов.")




# Команды для просмотра компетенций
async def list_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список всех компетенций"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    try:
        skills = await db_manager.get_all_skills()
        if not skills:
            await update.message.reply_text(
                "📋 <b>Компетенции не найдены.</b>\n\n"
                "💡 <i>Используйте кнопку '➕ Добавить компетенцию' для создания новой</i>",
                reply_markup=get_mentor_keyboard(),
                parse_mode='HTML'
            )
            return
        
        text = f"📋 <b>Список компетенций ({len(skills)}):</b>\n\n"
        for i, skill in enumerate(skills, 1):
            text += f"{i}. <b>{skill.skill}</b>\n"
            text += f"   🆔 ID: <code>{skill.id}</code>\n"
            if skill.description:
                desc = skill.description[:50] + "..." if len(skill.description) > 50 else skill.description
                text += f"   📝 Описание: {desc}\n"
            text += "\n"
        
        text += "💡 <i>Используйте ID для редактирования, удаления или связывания</i>"
        
        # Определяем клавиатуру в зависимости от роли
        tg_name = get_user_tg_name(update)
        is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка компетенций: {e}")
        tg_name = get_user_tg_name(update)
        is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        await update.message.reply_text(
            "❌ Ошибка при получении списка компетенций.",
            reply_markup=keyboard
        )


async def show_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали компетенции"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /skill <id>")
        return
    
    try:
        skill_id = UUID(context.args[0])
        skill = await db_manager.get_skill_by_id(skill_id)
        if not skill:
            await update.message.reply_text("❌ Компетенция не найдена.")
            return
        
        text = f"📖 Компетенция: <b>{skill.skill}</b>\n"
        text += f"ID: <code>{skill.id}</code>\n\n"
        if skill.description:
            text += f"Описание: {skill.description}\n\n"
        if skill.grade:
            text += f"Оценка: {skill.grade.value}\n\n"
        
        # Получаем вопросы для этой компетенции
        questions = await db_manager.get_questions_for_skill(skill.id)
        if questions:
            text += f"Вопросы ({len(questions)}):\n"
            for i, q in enumerate(questions, 1):
                text += f"{i}. {q.question[:50]}...\n" if len(q.question) > 50 else f"{i}. {q.question}\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при получении компетенции: {e}")
        await update.message.reply_text("❌ Ошибка при получении компетенции.")


# Команды для просмотра вопросов
async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список всех вопросов"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    try:
        questions = await db_manager.get_all_questions()
        if not questions:
            await update.message.reply_text(
                "❓ <b>Вопросы не найдены.</b>\n\n"
                "💡 <i>Используйте кнопку '➕ Добавить вопрос' для создания нового</i>",
                reply_markup=get_mentor_keyboard(),
                parse_mode='HTML'
            )
            return
        
        text = f"❓ <b>Список вопросов ({len(questions)}):</b>\n\n"
        for i, question in enumerate(questions, 1):
            q_text = question.question[:60] + "..." if len(question.question) > 60 else question.question
            text += f"{i}. {q_text}\n"
            text += f"   🆔 ID: <code>{question.id}</code>\n"
            text += f"   📊 Приоритет: {question.priority}\n\n"
        
        text += "💡 <i>Используйте ID для редактирования, удаления или связывания</i>"
        
        # Определяем клавиатуру в зависимости от роли
        tg_name = get_user_tg_name(update)
        is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка вопросов: {e}")
        tg_name = get_user_tg_name(update)
        is_mentor = await db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        await update.message.reply_text(
            "❌ Ошибка при получении списка вопросов.",
            reply_markup=keyboard
        )


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали вопроса"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /question <id>")
        return
    
    try:
        question_id = UUID(context.args[0])
        question = await db_manager.get_question_by_id(question_id)
        if not question:
            await update.message.reply_text("❌ Вопрос не найден.")
            return
        
        text = f"❓ Вопрос:\n{question.question}\n\n"
        text += f"ID: <code>{question.id}</code>\n"
        text += f"Приоритет: {question.priority}\n\n"
        if question.answer_example:
            text += f"Пример ответа: {question.answer_example}\n\n"
        
        # Получаем компетенции для этого вопроса
        skills = await db_manager.get_skills_for_question(question.id)
        if skills:
            text += f"Компетенции ({len(skills)}):\n"
            for i, s in enumerate(skills, 1):
                text += f"{i}. {s.skill}\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при получении вопроса: {e}")
        await update.message.reply_text("❌ Ошибка при получении вопроса.")


# Команды для добавления компетенций (только для менторов)
async def add_skill_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления компетенции"""
    if not await check_user_access(update, context):
        return ConversationHandler.END
    if not await check_mentor_permission(update, context):
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 Добавление новой компетенции.\n"
        "Введите название компетенции:"
    )
    context.user_data.pop('action', None)  # Очищаем действие, если было установлено
    return ADD_SKILL_NAME


async def add_skill_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает название компетенции"""
    context.user_data['skill_name'] = update.message.text
    await update.message.reply_text(
        "Введите описание компетенции (или /skip для пропуска):"
    )
    return ADD_SKILL_DESC


async def add_skill_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает описание компетенции"""
    if update.message.text.lower() != '/skip':
        context.user_data['skill_desc'] = update.message.text
    else:
        context.user_data['skill_desc'] = None
    
    try:
        skill = await db_manager.create_skill(
            context.user_data['skill_name'],
            context.user_data.get('skill_desc')
        )
        await update.message.reply_text(
            f"✅ Компетенция добавлена!\n"
            f"Название: {skill.skill}\n"
            f"ID: <code>{skill.id}</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении компетенции: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении компетенции.")
    
    return ConversationHandler.END


# Команды для добавления вопросов (только для менторов)
async def add_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления вопроса"""
    if not await check_mentor_permission(update, context):
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 Добавление нового вопроса.\n"
        "Введите текст вопроса:"
    )
    context.user_data.pop('action', None)  # Очищаем действие, если было установлено
    return ADD_QUESTION_TEXT


async def add_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает текст вопроса"""
    context.user_data['question_text'] = update.message.text
    await update.message.reply_text(
        "Введите пример ответа (или /skip для пропуска):"
    )
    return ADD_QUESTION_EXAMPLE


async def add_question_example(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает пример ответа"""
    if update.message.text.lower() != '/skip':
        context.user_data['question_example'] = update.message.text
    else:
        context.user_data['question_example'] = None
    
    await update.message.reply_text(
        "Введите приоритет (число, 0 - по умолчанию, или /skip):"
    )
    return ADD_QUESTION_PRIORITY


async def add_question_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает приоритет вопроса"""
    priority = 0
    if update.message.text.lower() != '/skip':
        try:
            priority = int(update.message.text)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат приоритета. Используется значение по умолчанию: 0")
    
    try:
        question = await db_manager.create_question(
            context.user_data['question_text'],
            context.user_data.get('question_example'),
            priority
        )
        await update.message.reply_text(
            f"✅ Вопрос добавлен!\n"
            f"Вопрос: {question.question}\n"
            f"ID: <code>{question.id}</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении вопроса: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении вопроса.")
    
    return ConversationHandler.END


# Команды для редактирования вопросов
async def edit_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс редактирования вопроса"""
    if not await check_mentor_permission(update, context):
        return ConversationHandler.END
    
    if not context.args:
        await update.message.reply_text("Использование: /edit_question <id>")
        return ConversationHandler.END
    
    try:
        question_id = UUID(context.args[0])
        question = await db_manager.get_question_by_id(question_id)
        if not question:
            await update.message.reply_text("❌ Вопрос не найден.")
            return ConversationHandler.END
        
        context.user_data['edit_question_id'] = question_id
        text = f"Редактирование вопроса: {question.question[:50]}...\n\n"
        text += "Что вы хотите изменить?\n"
        text += "1 - Текст вопроса\n"
        text += "2 - Пример ответа\n"
        text += "3 - Приоритет\n"
        text += "4 - Отмена"
        
        await update.message.reply_text(text)
        return EDIT_QUESTION_CHOICE
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
        return ConversationHandler.END


async def edit_question_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор поля для редактирования вопроса"""
    choice = update.message.text.strip()
    if choice == '4':
        await update.message.reply_text("❌ Редактирование отменено.")
        return ConversationHandler.END
    
    fields = {'1': 'question', '2': 'answer_example', '3': 'priority'}
    if choice not in fields:
        await update.message.reply_text("❌ Неверный выбор. Введите 1, 2, 3 или 4.")
        return EDIT_QUESTION_CHOICE
    
    context.user_data['edit_question_field'] = fields[choice]
    field_names = {
        'question': 'текст вопроса',
        'answer_example': 'пример ответа',
        'priority': 'приоритет (число)'
    }
    await update.message.reply_text(f"Введите новое значение для {field_names[fields[choice]]}:")
    return EDIT_QUESTION_VALUE


async def edit_question_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает новое значение для вопроса"""
    question_id = context.user_data['edit_question_id']
    field = context.user_data['edit_question_field']
    value = update.message.text
    
    try:
        if field == 'question':
            updated = await db_manager.update_question(question_id, question=value)
        elif field == 'answer_example':
            updated = await db_manager.update_question(question_id, answer_example=value)
        else:  # priority
            try:
                priority = int(value)
                updated = await db_manager.update_question(question_id, priority=priority)
            except ValueError:
                await update.message.reply_text("❌ Неверный формат приоритета. Введите число.")
                return EDIT_QUESTION_VALUE
        
        if updated:
            await update.message.reply_text(
                "✅ <b>Вопрос успешно обновлен!</b>",
                reply_markup=get_mentor_keyboard(),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при обновлении.",
                reply_markup=get_mentor_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при редактировании вопроса: {e}")
        await update.message.reply_text(
            "❌ Ошибка при редактировании вопроса.",
            reply_markup=get_mentor_keyboard()
        )
    
    return ConversationHandler.END


# Команды для редактирования компетенций
async def edit_skill_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс редактирования компетенции"""
    if not await check_user_access(update, context):
        return ConversationHandler.END
    if not await check_mentor_permission(update, context):
        return ConversationHandler.END
    
    if not context.args:
        await update.message.reply_text("Использование: /edit_skill <id>")
        return ConversationHandler.END
    
    try:
        skill_id = UUID(context.args[0])
        skill = await db_manager.get_skill_by_id(skill_id)
        if not skill:
            await update.message.reply_text("❌ Компетенция не найдена.")
            return ConversationHandler.END
        
        context.user_data['edit_skill_id'] = skill_id
        text = f"Редактирование компетенции: {skill.skill}\n\n"
        text += "Что вы хотите изменить?\n"
        text += "1 - Название\n"
        text += "2 - Описание\n"
        text += "3 - Отмена"
        
        await update.message.reply_text(text)
        return EDIT_SKILL_CHOICE
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
        return ConversationHandler.END


async def edit_skill_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор поля для редактирования"""
    choice = update.message.text.strip()
    if choice == '3':
        await update.message.reply_text("❌ Редактирование отменено.")
        return ConversationHandler.END
    
    fields = {'1': 'name', '2': 'description'}
    if choice not in fields:
        await update.message.reply_text("❌ Неверный выбор. Введите 1, 2 или 3.")
        return EDIT_SKILL_CHOICE
    
    context.user_data['edit_skill_field'] = fields[choice]
    field_names = {'name': 'название', 'description': 'описание'}
    await update.message.reply_text(f"Введите новое {field_names[fields[choice]]}:")
    return EDIT_SKILL_VALUE


async def edit_skill_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает новое значение"""
    skill_id = context.user_data['edit_skill_id']
    field = context.user_data['edit_skill_field']
    value = update.message.text
    
    try:
        if field == 'name':
            updated = await db_manager.update_skill(skill_id, skill=value)
        else:
            updated = await db_manager.update_skill(skill_id, description=value)
        
        if updated:
            await update.message.reply_text(
                "✅ <b>Компетенция успешно обновлена!</b>",
                reply_markup=get_mentor_keyboard(),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при обновлении.",
                reply_markup=get_mentor_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при редактировании компетенции: {e}")
        await update.message.reply_text(
            "❌ Ошибка при редактировании компетенции.",
            reply_markup=get_mentor_keyboard()
        )
    
    return ConversationHandler.END


# Команды для удаления
async def delete_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет компетенцию"""
    if not await check_user_access(update, context):
        return
    if not await check_mentor_permission(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /delete_skill <id>")
        return
    
    try:
        skill_id = UUID(context.args[0])
        success = await db_manager.delete_skill(skill_id)
        if success:
            await update.message.reply_text("✅ Компетенция удалена.")
        else:
            await update.message.reply_text("❌ Компетенция не найдена.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при удалении компетенции: {e}")
        await update.message.reply_text("❌ Ошибка при удалении компетенции.")


async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет вопрос"""
    if not await check_mentor_permission(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /delete_question <id>")
        return
    
    try:
        question_id = UUID(context.args[0])
        success = await db_manager.delete_question(question_id)
        if success:
            await update.message.reply_text("✅ Вопрос удален.")
        else:
            await update.message.reply_text("❌ Вопрос не найден.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при удалении вопроса: {e}")
        await update.message.reply_text("❌ Ошибка при удалении вопроса.")


# Команды для связывания
async def link_skill_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Связывает компетенцию с вопросом"""
    if not await check_user_access(update, context):
        return ConversationHandler.END
    if not await check_mentor_permission(update, context):
        return ConversationHandler.END
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Использование: /link <skill_id> <question_id>")
        return ConversationHandler.END
    
    try:
        skill_id = UUID(context.args[0])
        question_id = UUID(context.args[1])
        
        # Проверяем существование навыка и вопроса
        skill = await db_manager.get_skill_by_id(skill_id)
        question = await db_manager.get_question_by_id(question_id)
        
        if not skill:
            await update.message.reply_text("❌ Компетенция не найдена.")
            return
        if not question:
            await update.message.reply_text("❌ Вопрос не найден.")
            return
        
        link = await db_manager.link_skill_to_question(skill_id, question_id)
        if link:
            await update.message.reply_text(
                f"✅ Связь создана!\n"
                f"Компетенция: {skill.skill}\n"
                f"Вопрос: {question.question[:50]}..."
            )
        else:
            await update.message.reply_text("❌ Ошибка при создании связи.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при связывании: {e}")
        await update.message.reply_text("❌ Ошибка при связывании.")


async def unlink_skill_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет связь между компетенцией и вопросом"""
    if not await check_user_access(update, context):
        return
    if not await check_mentor_permission(update, context):
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Использование: /unlink <skill_id> <question_id>")
        return
    
    try:
        skill_id = UUID(context.args[0])
        question_id = UUID(context.args[1])
        
        success = await db_manager.unlink_skill_from_question(skill_id, question_id)
        if success:
            await update.message.reply_text("✅ Связь удалена.")
        else:
            await update.message.reply_text("❌ Связь не найдена.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при удалении связи: {e}")
        await update.message.reply_text("❌ Ошибка при удалении связи.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущую операцию"""
    # Очищаем данные теста, если тест был начат
    if 'test_questions' in context.user_data:
        # Отменяем тест в БД, если он был создан
        test_result_id = context.user_data.get('test_result_id')
        if test_result_id:
            try:
                async with db_manager.pool.acquire() as connection:
                    await connection.execute(
                        "UPDATE test_result SET summary = 'Тест отменен пользователем' WHERE id = $1",
                        test_result_id
                    )
            except Exception as e:
                logger.error(f"Ошибка при отмене теста в БД: {e}")
        
        context.user_data.clear()
        tg_name = get_user_tg_name(update)
        agent = await db_manager.get_agent_by_tg_name(tg_name)
        if agent and agent.is_student():
            await update.message.reply_text(
                "❌ <b>Тест отменен.</b>",
                reply_markup=get_student_keyboard(),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Операция отменена.",
                reply_markup=get_mentor_keyboard()
            )
    else:
        # Отменяем другие операции
        context.user_data.clear()
        tg_name = get_user_tg_name(update)
        agent = await db_manager.get_agent_by_tg_name(tg_name)
        if agent and agent.is_mentor():
            await update.message.reply_text(
                "❌ Операция отменена.",
                reply_markup=get_mentor_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Операция отменена.",
                reply_markup=get_student_keyboard()
            )
    return ConversationHandler.END


# Функции для тестирования
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает тестирование"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    tg_name = get_user_tg_name(update)
    agent = await db_manager.get_agent_by_tg_name(tg_name)
    
    # Получаем все вопросы
    questions = await db_manager.get_all_questions()
    
    if not questions:
        await update.message.reply_text(
            "❌ <b>Вопросы не найдены</b>\n\n"
            "В базе данных пока нет вопросов для тестирования.",
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Инициализируем тест
    import time
    context.user_data['test_start_time'] = time.time()
    context.user_data['test_questions'] = questions
    context.user_data['test_current_index'] = 0
    context.user_data['test_answers'] = []
    context.user_data['test_result_id'] = None
    
    # Создаем запись о начале теста
    test_result = await db_manager.create_test_result(
        agent.id,
        summary="Тест в процессе",
        skills_total=len(questions)
    )
    context.user_data['test_result_id'] = test_result.id
    
    # Показываем первый вопрос
    await show_next_question(update, context)


async def show_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает следующий вопрос теста"""
    questions = context.user_data.get('test_questions', [])
    current_index = context.user_data.get('test_current_index', 0)
    
    if current_index >= len(questions):
        # Тест завершен
        await finish_test(update, context)
        return
    
    question = questions[current_index]
    
    text = f"❓ <b>Вопрос {current_index + 1} из {len(questions)}</b>\n\n"
    text += f"{question.question}\n\n"
    
    if question.answer_example:
        text += f"💡 <i>Пример ответа: {question.answer_example[:100]}{'...' if len(question.answer_example) > 100 else ''}</i>\n\n"
    
    text += "Введите ваш ответ:\n"
    text += "💡 <i>Для отмены используйте /cancel</i>"
    
    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )


async def process_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответ на вопрос теста"""
    questions = context.user_data.get('test_questions', [])
    current_index = context.user_data.get('test_current_index', 0)
    test_result_id = context.user_data.get('test_result_id')
    
    if current_index >= len(questions) or not test_result_id:
        # Тест уже завершен или ошибка
        if not test_result_id:
            await update.message.reply_text(
                "❌ Ошибка: данные теста потеряны. Тест отменен.",
                reply_markup=get_student_keyboard()
            )
            context.user_data.clear()
        return
    
    question = questions[current_index]
    answer = update.message.text
    
    try:
        # Сохраняем ответ
        test_detail = await db_manager.create_test_detail(
            test_result_id,
            question.id,
            answer=answer,
            answer_analyze_result=None  # Можно добавить анализ ответа позже
        )
        
        context.user_data['test_answers'].append({
            'question_id': question.id,
            'answer': answer
        })
        
        # Переходим к следующему вопросу
        context.user_data['test_current_index'] = current_index + 1
        
        if context.user_data['test_current_index'] < len(questions):
            await show_next_question(update, context)
        else:
            await finish_test(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на тест: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении ответа. Попробуйте еще раз или используйте /cancel для отмены.",
            reply_markup=ReplyKeyboardRemove()
        )


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершает тест и показывает результаты"""
    import time
    
    test_start_time = context.user_data.get('test_start_time', time.time())
    test_timing = int(time.time() - test_start_time)
    test_result_id = context.user_data.get('test_result_id')
    questions = context.user_data.get('test_questions', [])
    
    if not test_result_id:
        await update.message.reply_text(
            "❌ Ошибка при завершении теста.",
            reply_markup=get_student_keyboard()
        )
        context.user_data.clear()
        return
    
    # Обновляем результат теста
    async with db_manager.pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE test_result 
            SET test_timing = $1, summary = $2
            WHERE id = $3
            """,
            test_timing, f"Тест завершен. Отвечено на {len(questions)} вопросов.", test_result_id
        )
    
    # Формируем сообщение о завершении
    minutes = test_timing // 60
    seconds = test_timing % 60
    
    text = (
        f"✅ <b>Тест завершен!</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"• Всего вопросов: {len(questions)}\n"
        f"• Отвечено: {len(context.user_data.get('test_answers', []))}\n"
        f"• Время прохождения: {minutes} мин {seconds} сек\n\n"
        f"💡 <i>Ваши ответы сохранены. Ментор сможет их просмотреть и оценить.</i>"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_student_keyboard(),
        parse_mode='HTML'
    )
    
    # Очищаем данные теста
    context.user_data.pop('test_questions', None)
    context.user_data.pop('test_current_index', None)
    context.user_data.pop('test_answers', None)
    context.user_data.pop('test_start_time', None)
    context.user_data.pop('test_result_id', None)


async def show_my_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает результаты тестов пользователя"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return
    
    tg_name = get_user_tg_name(update)
    agent = await db_manager.get_agent_by_tg_name(tg_name)
    
    if not agent:
        await update.message.reply_text(
            "❌ Пользователь не найден.",
            reply_markup=get_student_keyboard()
        )
        return
    
    # Получаем результаты тестов
    results = await db_manager.get_test_results_by_agent(agent.id)
    
    if not results:
        await update.message.reply_text(
            "📊 <b>Результаты тестов</b>\n\n"
            "У вас пока нет пройденных тестов.\n"
            "Используйте кнопку '🧪 Начать тест' для прохождения тестирования.",
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )
        return
    
    text = f"📊 <b>Мои результаты ({len(results)}):</b>\n\n"
    
    for i, result in enumerate(results, 1):
        created = result.created_at.strftime("%d.%m.%Y %H:%M") if result.created_at else "N/A"
        timing = result.test_timing
        if timing:
            minutes = timing // 60
            seconds = timing % 60
            time_str = f"{minutes} мин {seconds} сек"
        else:
            time_str = "N/A"
        
        text += f"{i}. <b>Тест от {created}</b>\n"
        text += f"   ⏱ Время: {time_str}\n"
        text += f"   📋 Вопросов: {result.skills_total}\n"
        if result.summary:
            text += f"   📝 {result.summary[:50]}{'...' if len(result.summary) > 50 else ''}\n"
        text += "\n"
    
    await update.message.reply_text(
        text,
        reply_markup=get_student_keyboard(),
        parse_mode='HTML'
    )


async def handle_action_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Обрабатывает сообщения для действий после нажатия кнопок"""
    # Проверяем доступ пользователя
    if not await check_user_access(update, context):
        return ConversationHandler.END
    
    # Тест обрабатывается в handle_keyboard_message, здесь не нужно
    
    action = context.user_data.get('action')
    
    # Если нет активного действия, пропускаем обработку
    # (сообщение будет обработано keyboard_handler)
    if not action:
        return None
    
    # Обработка добавления компетенции через кнопку
    if action == 'add_skill':
        # Проверяем, на каком этапе мы находимся
        if 'skill_name' not in context.user_data:
            # Это первое сообщение - название компетенции
            context.user_data['skill_name'] = update.message.text
            await update.message.reply_text(
                "Введите описание компетенции (или /skip для пропуска):"
            )
            context.user_data['action'] = 'add_skill_desc'
            return None
        elif context.user_data.get('action') == 'add_skill_desc':
            # Это второе сообщение - описание
            if update.message.text.lower() != '/skip':
                context.user_data['skill_desc'] = update.message.text
            else:
                context.user_data['skill_desc'] = None
            
            try:
                skill = await db_manager.create_skill(
                    context.user_data['skill_name'],
                    context.user_data.get('skill_desc')
                )
                await update.message.reply_text(
                    f"✅ <b>Компетенция успешно добавлена!</b>\n\n"
                    f"📋 Название: <b>{skill.skill}</b>\n"
                    f"🆔 ID: <code>{skill.id}</code>\n\n"
                    f"💡 <i>Используйте этот ID для редактирования или связывания</i>",
                    reply_markup=get_mentor_keyboard(),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка при добавлении компетенции: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при добавлении компетенции.",
                    reply_markup=get_mentor_keyboard()
                )
            
            # Очищаем данные
            context.user_data.pop('skill_name', None)
            context.user_data.pop('skill_desc', None)
            context.user_data.pop('action', None)
            return ConversationHandler.END
    
    if action == 'delete_skill':
        try:
            skill_id = UUID(update.message.text.strip())
            success = await db_manager.delete_skill(skill_id)
            if success:
                await update.message.reply_text(
                    "✅ <b>Компетенция успешно удалена!</b>",
                    reply_markup=get_mentor_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Компетенция не найдена.",
                    reply_markup=get_mentor_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Попробуйте еще раз:",
                reply_markup=get_mentor_keyboard()
            )
            return None
        except Exception as e:
            logger.error(f"Ошибка при удалении компетенции: {e}")
            await update.message.reply_text(
                "❌ Ошибка при удалении компетенции.",
                reply_markup=get_mentor_keyboard()
            )
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    elif action == 'delete_question':
        try:
            question_id = UUID(update.message.text.strip())
            success = await db_manager.delete_question(question_id)
            if success:
                await update.message.reply_text(
                    "✅ <b>Вопрос успешно удален!</b>",
                    reply_markup=get_mentor_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Вопрос не найден.",
                    reply_markup=get_mentor_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Попробуйте еще раз:",
                reply_markup=get_mentor_keyboard()
            )
            return None
        except Exception as e:
            logger.error(f"Ошибка при удалении вопроса: {e}")
            await update.message.reply_text(
                "❌ Ошибка при удалении вопроса.",
                reply_markup=get_mentor_keyboard()
            )
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    elif action == 'link':
        try:
            parts = update.message.text.strip().split()
            if len(parts) < 2:
                await update.message.reply_text("❌ Введите два ID через пробел: skill_id question_id")
                return None
            
            skill_id = UUID(parts[0])
            question_id = UUID(parts[1])
            
            skill = await db_manager.get_skill_by_id(skill_id)
            question = await db_manager.get_question_by_id(question_id)
            
            if not skill:
                await update.message.reply_text("❌ Компетенция не найдена.")
                context.user_data.pop('action', None)
                return ConversationHandler.END
            if not question:
                await update.message.reply_text("❌ Вопрос не найден.")
                context.user_data.pop('action', None)
                return ConversationHandler.END
            
            link = await db_manager.link_skill_to_question(skill_id, question_id)
            if link:
                await update.message.reply_text(
                    f"✅ <b>Связь успешно создана!</b>\n\n"
                    f"📋 Компетенция: <b>{skill.skill}</b>\n"
                    f"❓ Вопрос: {question.question[:50]}...",
                    reply_markup=get_mentor_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при создании связи.",
                    reply_markup=get_mentor_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Введите два ID через пробел:",
                reply_markup=get_mentor_keyboard()
            )
            return None
        except Exception as e:
            logger.error(f"Ошибка при связывании: {e}")
            await update.message.reply_text(
                "❌ Ошибка при связывании.",
                reply_markup=get_mentor_keyboard()
            )
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    elif action == 'unlink':
        try:
            parts = update.message.text.strip().split()
            if len(parts) < 2:
                await update.message.reply_text("❌ Введите два ID через пробел: skill_id question_id")
                return None
            
            skill_id = UUID(parts[0])
            question_id = UUID(parts[1])
            
            success = await db_manager.unlink_skill_from_question(skill_id, question_id)
            if success:
                await update.message.reply_text(
                    "✅ <b>Связь успешно удалена!</b>",
                    reply_markup=get_mentor_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Связь не найдена.",
                    reply_markup=get_mentor_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Введите два ID через пробел:",
                reply_markup=get_mentor_keyboard()
            )
            return None
        except Exception as e:
            logger.error(f"Ошибка при удалении связи: {e}")
            await update.message.reply_text(
                "❌ Ошибка при удалении связи.",
                reply_markup=get_mentor_keyboard()
            )
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    elif action == 'edit_skill':
        try:
            skill_id = UUID(update.message.text.strip())
            skill = await db_manager.get_skill_by_id(skill_id)
            if not skill:
                await update.message.reply_text("❌ Компетенция не найдена.")
                context.user_data.pop('action', None)
                return ConversationHandler.END
            
            context.user_data['edit_skill_id'] = skill_id
            text = f"Редактирование компетенции: {skill.skill}\n\n"
            text += "Что вы хотите изменить?\n"
            text += "1 - Название\n"
            text += "2 - Описание\n"
            text += "3 - Отмена"
            
            await update.message.reply_text(
                text,
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['action'] = None
            return EDIT_SKILL_CHOICE
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Попробуйте еще раз:",
                reply_markup=get_mentor_keyboard()
            )
            context.user_data.pop('action', None)
            return ConversationHandler.END
    
    elif action == 'edit_question':
        try:
            question_id = UUID(update.message.text.strip())
            question = await db_manager.get_question_by_id(question_id)
            if not question:
                await update.message.reply_text("❌ Вопрос не найден.")
                context.user_data.pop('action', None)
                return ConversationHandler.END
            
            context.user_data['edit_question_id'] = question_id
            text = f"Редактирование вопроса: {question.question[:50]}...\n\n"
            text += "Что вы хотите изменить?\n"
            text += "1 - Текст вопроса\n"
            text += "2 - Пример ответа\n"
            text += "3 - Приоритет\n"
            text += "4 - Отмена"
            
            await update.message.reply_text(
                text,
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['action'] = None
            return EDIT_QUESTION_CHOICE
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Попробуйте еще раз:",
                reply_markup=get_mentor_keyboard()
            )
            context.user_data.pop('action', None)
            return ConversationHandler.END
    
    return None


def main() -> None:
    """Основная функция для запуска бота"""
    # Инициализируем подключение к БД синхронно
    async def init_db():
        await db_manager.connect()
        logger.info("Подключение к БД установлено")
    
    # Запускаем инициализацию БД
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд для просмотра
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("panel", mentor_panel))
    application.add_handler(CommandHandler("skills", list_skills))
    application.add_handler(CommandHandler("questions", list_questions))
    application.add_handler(CommandHandler("skill", show_skill))
    application.add_handler(CommandHandler("question", show_question))
    
    # Регистрируем обработчики команд для управления (только для менторов)
    application.add_handler(CommandHandler("delete_skill", delete_skill))
    application.add_handler(CommandHandler("delete_question", delete_question))
    application.add_handler(CommandHandler("link", link_skill_question))
    application.add_handler(CommandHandler("unlink", unlink_skill_question))
    
    # Обработчик для callback_query (кнопки)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # ConversationHandler для добавления компетенции
    add_skill_handler = ConversationHandler(
        entry_points=[CommandHandler("add_skill", add_skill_start)],
        states={
            ADD_SKILL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_skill_name)],
            ADD_SKILL_DESC: [MessageHandler(filters.TEXT, add_skill_desc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(add_skill_handler)
    
    # ConversationHandler для добавления вопроса
    add_question_handler = ConversationHandler(
        entry_points=[CommandHandler("add_question", add_question_start)],
        states={
            ADD_QUESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_text)],
            ADD_QUESTION_EXAMPLE: [MessageHandler(filters.TEXT, add_question_example)],
            ADD_QUESTION_PRIORITY: [MessageHandler(filters.TEXT, add_question_priority)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(add_question_handler)
    
    # ConversationHandler для редактирования компетенции
    edit_skill_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_skill", edit_skill_start)],
        states={
            EDIT_SKILL_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_skill_choice)],
            EDIT_SKILL_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_skill_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(edit_skill_handler)
    
    # ConversationHandler для редактирования вопроса
    edit_question_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_question", edit_question_start)],
        states={
            EDIT_QUESTION_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_question_choice)],
            EDIT_QUESTION_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_question_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(edit_question_handler)
    
    # ConversationHandler для тестирования не нужен, так как тест обрабатывается через handle_action_message
    
    # Обработчик для постоянной клавиатуры ментора
    # Обрабатывает команды клавиатуры (кнопки)
    keyboard_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_keyboard_message
    )
    application.add_handler(keyboard_handler)
    
    # Обработчик для действий через сообщения (после нажатия кнопок)
    # Обрабатывает действия после установки context.user_data['action']
    # Должен быть после keyboard_handler, чтобы обрабатывать действия после команд клавиатуры
    action_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_action_message
    )
    application.add_handler(action_handler)
    
    # Обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает ошибки"""
        error = context.error
        
        if isinstance(error, Conflict):
            logger.error(
                "⚠️ Конфликт: Другой экземпляр бота уже запущен!\n"
                "Убедитесь, что запущен только один экземпляр бота."
            )
            logger.info("Остановка бота...")
            # Останавливаем бота при конфликте
            application.stop()
            return
        
        if isinstance(error, NetworkError):
            logger.warning(f"⚠️ Ошибка сети: {error}")
            return
        
        # Логируем другие ошибки
        logger.error(f"Необработанная ошибка: {error}", exc_info=error)
        
        # Если есть update, отправляем сообщение пользователю
        if update and isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Пожалуйста, попробуйте позже или используйте /start"
                )
            except Exception:
                pass
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен...")
    try:
        application.run_polling(
            drop_pending_updates=True,  # Пропускаем старые обновления при перезапуске
            allowed_updates=Update.ALL_TYPES
        )
    except KeyboardInterrupt:
        logger.info("Получено прерывание, закрываю БД...")
    except Conflict:
        logger.error(
            "❌ Конфликт: Другой экземпляр бота уже запущен!\n"
            "Пожалуйста, остановите все другие экземпляры бота перед запуском."
        )
    finally:
        # Закрываем подключение к БД
        loop.run_until_complete(db_manager.disconnect())
        loop.close()
        logger.info("Подключение к БД закрыто")


if __name__ == '__main__':
    main()
