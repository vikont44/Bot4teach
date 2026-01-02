import logging
import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from uuid import UUID
from typing import Optional, List
from openai import OpenAI
import sys
import time
import random

from database import db_manager
from database.models_peewee import GradeEnum, RoleEnum, TestResult, TestDetail, Question
from database.config import db_config
from ai_prompts import STUDENT_ANSWER_ANALYSIS_PROMPT, STUDENT_FEEDBACK_PROMPT

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8546564697:AAG-29UDY9HPNnvYBus5SUJMRgzXTN2n7Ks"

# DeepSeek API клиент
DEEPSEEK_CLIENT = OpenAI(
    api_key="sk-09a0a31fd11c4c5bab8b6db2e1ad932b",
    base_url="https://api.deepseek.com"
)

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения состояния пользователей
user_states = {}

def get_user_tg_name(message) -> str:
    """Получает имя пользователя Telegram"""
    user = message.from_user
    if user.username:
        return user.username
    return str(user.id)

def get_mentor_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру для ментора"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📋 Компетенции", "❓ Вопросы")
    keyboard.row("📊 Результаты студентов", "🏠 Меню")
    keyboard.row("ℹ️ Помощь")
    return keyboard

def get_student_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру для студента"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🧪 Начать тест")
    keyboard.row("📊 Мои результаты")
    return keyboard

def check_user_access(message) -> bool:
    """Проверяет, есть ли пользователь в БД"""
    tg_name = get_user_tg_name(message)
    agent = db_manager.get_agent_by_tg_name(tg_name)
    if not agent:
        bot.reply_to(message, 
            "❌ <b>Доступ запрещен</b>\n\n"
            "Вы не зарегистрированы в системе.\n"
            "Обратитесь к администратору для получения доступа.",
            parse_mode='HTML'
        )
        return False
    return True

def check_mentor_permission(message) -> bool:
    """Проверяет, является ли пользователь ментором"""
    if not check_user_access(message):
        return False
    
    tg_name = get_user_tg_name(message)
    is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
    if not is_mentor:
        bot.reply_to(message, 
            "❌ У вас нет прав для выполнения этой команды. "
            "Только менторы могут управлять компетенциями и вопросами."
        )
    return is_mentor

@bot.message_handler(commands=['start'])
def start(message):
    if not check_user_access(message):
        return
    
    tg_name = get_user_tg_name(message)
    agent = db_manager.get_agent_by_tg_name(tg_name)
    
    role_text = "👨‍🏫 ментор" if agent.is_mentor() else "👨‍🎓 студент"
    text = f"👋 Привет! Твоя роль: {role_text}\n\n"
    
    if agent.is_mentor():
        text += "👨‍🏫 <b>Добро пожаловать в панель ментора!</b>\n\n"
        text += "Используй кнопки внизу для управления компетенциями и вопросами.\n"
        text += "Или используй команду /panel для inline-панели."
        bot.reply_to(message, text, reply_markup=get_mentor_keyboard(), parse_mode='HTML')
    else:
        text += "👨‍🎓 <b>Добро пожаловать!</b>\n\n"
        text += "Используй кнопки внизу для навигации."
        bot.reply_to(message, text, reply_markup=get_student_keyboard(), parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    if not check_user_access(message):
        return
    
    tg_name = get_user_tg_name(message)
    is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
    
    help_text = "📚 Доступные команды:\n\n"
    help_text += "👁️ Просмотр:\n"
    help_text += "/skills - Список всех компетенций\n"
    help_text += "/questions - Список всех вопросов\n"
    help_text += "/skill <id> - Детали компетенции\n"
    help_text += "/question <id> - Детали вопроса\n"
    
    if is_mentor:
        help_text += "\n✏️ Управление (только для менторов):\n"
        help_text += "/panel - Панель ментора с кнопками\n"
        help_text += "\n⚠️ Вопросы управляются напрямую через БД\n"
    else:
        help_text = "👨‍🎓 <b>Справка для студента</b>\n\n"
        help_text += "🧪 <b>Начать тест</b> - Начать прохождение тестирования по вопросам\n"
        help_text += "📊 <b>Мои результаты</b> - Просмотреть результаты пройденных тестов\n\n"
        help_text += "💡 <i>Используйте кнопки внизу для навигации</i>"
    
    keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
    bot.reply_to(message, help_text, reply_markup=keyboard, parse_mode='HTML' if not is_mentor else None)

@bot.message_handler(commands=['panel'])
def mentor_panel(message):
    if not check_user_access(message):
        return
    if not check_mentor_permission(message):
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Список компетенций", callback_data="list_skills"),
            InlineKeyboardButton("❓ Список вопросов", callback_data="list_questions")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot.reply_to(message, 
        "👨‍🏫 <b>Панель ментора (Inline)</b>\n\n"
        "Выберите действие:\n\n"
        "ℹ️ <i>Все изменения происходят напрямую через БД</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

@bot.message_handler(commands=['skills'])
def list_skills(message):
    if not check_user_access(message):
        return
    
    try:
        skills = db_manager.get_all_skills()
        if not skills:
            bot.reply_to(message,
                "📋 <b>Компетенции не найдены.</b>\n\n"
                "💡 <i>Компетенции добавляются напрямую в БД</i>",
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
        
        tg_name = get_user_tg_name(message)
        is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        
        bot.reply_to(message, text, reply_markup=keyboard, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка компетенций: {e}")
        tg_name = get_user_tg_name(message)
        is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        bot.reply_to(message, "❌ Ошибка при получении списка компетенций.", reply_markup=keyboard)

@bot.message_handler(commands=['skill'])
def show_skill(message):
    if not check_user_access(message):
        return
    
    try:
        skill_id = UUID(message.text.split()[1])
        skill = db_manager.get_skill_by_id(skill_id)
        if not skill:
            bot.reply_to(message, "❌ Компетенция не найдена.")
            return
        
        text = f"📖 Компетенция: <b>{skill.skill}</b>\n"
        text += f"ID: <code>{skill.id}</code>\n\n"
        if skill.description:
            text += f"Описание: {skill.description}\n\n"
        if skill.grade:
            text += f"Оценка: {skill.grade.value}\n\n"
        
        questions = db_manager.get_questions_for_skill(skill.id)
        if questions:
            text += f"Вопросы ({len(questions)}):\n"
            for i, q in enumerate(questions, 1):
                text += f"{i}. {q.question[:50]}...\n" if len(q.question) > 50 else f"{i}. {q.question}\n"
        
        bot.reply_to(message, text, parse_mode='HTML')
    except IndexError:
        bot.reply_to(message, "Использование: /skill <id>")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при получении компетенции: {e}")
        bot.reply_to(message, "❌ Ошибка при получении компетенции.")

@bot.message_handler(commands=['questions'])
def list_questions(message):
    if not check_user_access(message):
        return
    
    try:
        questions = db_manager.get_all_questions()
        if not questions:
            bot.reply_to(message,
                "❓ <b>Вопросы не найдены.</b>\n\n"
                "💡 <i>Вопросы добавляются напрямую в БД</i>",
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
        
        tg_name = get_user_tg_name(message)
        is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        
        bot.reply_to(message, text, reply_markup=keyboard, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка вопросов: {e}")
        tg_name = get_user_tg_name(message)
        is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
        keyboard = get_mentor_keyboard() if is_mentor else get_student_keyboard()
        bot.reply_to(message, "❌ Ошибка при получении списка вопросов.", reply_markup=keyboard)

@bot.message_handler(commands=['question'])
def show_question(message):
    if not check_user_access(message):
        return
    
    try:
        question_id = UUID(message.text.split()[1])
        question = db_manager.get_question_by_id(question_id)
        if not question:
            bot.reply_to(message, "❌ Вопрос не найден.")
            return
        
        text = f"❓ Вопрос:\n{question.question}\n\n"
        text += f"ID: <code>{question.id}</code>\n"
        text += f"Приоритет: {question.priority}\n\n"
        if question.answer_example:
            text += f"Пример ответа: {question.answer_example}\n\n"
        
        skills = db_manager.get_skills_for_question(question.id)
        if skills:
            text += f"Компетенции ({len(skills)}):\n"
            for i, s in enumerate(skills, 1):
                text += f"{i}. {s.skill}\n"
        
        bot.reply_to(message, text, parse_mode='HTML')
    except IndexError:
        bot.reply_to(message, "Использование: /question <id>")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID.")
    except Exception as e:
        logger.error(f"Ошибка при получении вопроса: {e}")
        bot.reply_to(message, "❌ Ошибка при получении вопроса.")

@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.from_user.id
    if user_id in user_states and 'test_questions' in user_states[user_id]:
        test_result_id = user_states[user_id].get('test_result_id')
        if test_result_id:
            try:
                test_result = TestResult.get(TestResult.id == test_result_id)
                test_result.summary = 'Тест отменен пользователем'
                test_result.save()
            except Exception as e:
                logger.error(f"Ошибка при отмене теста в БД: {e}")
        
        del user_states[user_id]
        
        tg_name = get_user_tg_name(message)
        agent = db_manager.get_agent_by_tg_name(tg_name)
        if agent and agent.is_student():
            bot.reply_to(message, "❌ <b>Тест отменен.</b>", reply_markup=get_student_keyboard(), parse_mode='HTML')
        else:
            bot.reply_to(message, "❌ Операция отменена.", reply_markup=get_mentor_keyboard())
    else:
        if user_id in user_states:
            del user_states[user_id]
        tg_name = get_user_tg_name(message)
        agent = db_manager.get_agent_by_tg_name(tg_name)
        if agent and agent.is_mentor():
            bot.reply_to(message, "❌ Операция отменена.", reply_markup=get_mentor_keyboard())
        else:
            bot.reply_to(message, "❌ Операция отменена.", reply_markup=get_student_keyboard())

def select_test_questions() -> List:
    """
    Выбирает вопросы для тестирования согласно требованиям:
    - Минимум 2 вопроса на каждую компетенцию
    - Всего 15 вопросов
    - Вопросы выбираются случайным образом
    """
    selected_questions = []
    selected_question_ids = set()
    
    # Получаем все компетенции
    skills = db_manager.get_all_skills()
    
    if not skills:
        # Если нет компетенций, возвращаем все вопросы (до 15 штук)
        all_questions = db_manager.get_all_questions()
        if all_questions:
            random.shuffle(all_questions)
            return all_questions[:15]
        return []
    
    # Шаг 1: Для каждой компетенции выбираем минимум 2 вопроса
    for skill in skills:
        skill_questions = db_manager.get_questions_for_skill(skill.id)
        
        if len(skill_questions) >= 2:
            # Выбираем 2 случайных вопроса из доступных
            random.shuffle(skill_questions)
            for q in skill_questions[:2]:
                if q.id not in selected_question_ids:
                    selected_questions.append(q)
                    selected_question_ids.add(q.id)
        elif len(skill_questions) == 1:
            # Если только 1 вопрос, берем его
            if skill_questions[0].id not in selected_question_ids:
                selected_questions.append(skill_questions[0])
                selected_question_ids.add(skill_questions[0].id)
    
    # Шаг 2: Если вопросов меньше 15, дополняем случайными вопросами
    if len(selected_questions) < 15:
        all_questions = db_manager.get_all_questions()
        remaining_questions = [q for q in all_questions if q.id not in selected_question_ids]
        
        # Перемешиваем оставшиеся вопросы
        random.shuffle(remaining_questions)
        
        # Добавляем столько, сколько нужно до 15
        needed = 15 - len(selected_questions)
        selected_questions.extend(remaining_questions[:needed])
    
    # Шаг 3: Ограничиваем до 15 вопросов и перемешиваем весь список
    if len(selected_questions) > 15:
        random.shuffle(selected_questions)
        selected_questions = selected_questions[:15]
    else:
        random.shuffle(selected_questions)
    
    return selected_questions

def start_test(message):
    if not check_user_access(message):
        return
    
    tg_name = get_user_tg_name(message)
    agent = db_manager.get_agent_by_tg_name(tg_name)
    
    # Выбираем вопросы согласно новой логике
    questions = select_test_questions()
    
    if not questions:
        bot.reply_to(message,
            "❌ <b>Вопросы не найдены</b>\n\n"
            "В базе данных пока нет вопросов для тестирования или нет компетенций с вопросами.",
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )
        return
    
    user_id = message.from_user.id
    user_states[user_id] = {
        'test_start_time': time.time(),
        'test_questions': questions,
        'test_current_index': 0,
        'test_answers': [],
        'test_result_id': None
    }
    
    test_result = db_manager.create_test_result(
        agent.id,
        summary="Тест в процессе",
        skills_total=len(questions)
    )
    user_states[user_id]['test_result_id'] = test_result.id
    
    show_next_question(message)

def show_next_question(message):
    user_id = message.from_user.id
    questions = user_states[user_id].get('test_questions', [])
    current_index = user_states[user_id].get('test_current_index', 0)
    
    if current_index >= len(questions):
        finish_test(message)
        return
    
    question = questions[current_index]
    
    text = f"❓ <b>Вопрос {current_index + 1} из {len(questions)}</b>\n\n"
    text += f"{question.question}\n\n"
    
    if question.answer_example:
        text += f"💡 <i>Пример ответа: {question.answer_example[:100]}{'...' if len(question.answer_example) > 100 else ''}</i>\n\n"
    
    text += "Введите ваш ответ:\n"
    text += "💡 <i>Для отмены используйте /cancel</i>"
    
    bot.reply_to(message, text, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())

def analyze_student_answer(question: str, student_answer: str, example_answer: Optional[str] = None) -> str:
    try:
        prompt = STUDENT_ANSWER_ANALYSIS_PROMPT.format(
            question=question,
            example_answer=example_answer or "Не предоставлен",
            student_answer=student_answer
        )
        
        response = DEEPSEEK_CLIENT.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[{"role": "user", "content": prompt}],
            extra_body={"reasoning": {"enabled": True}}
        )
        
        assistant_message = response.choices[0].message.content
        
        response2 = DEEPSEEK_CLIENT.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_message},
                {"role": "user", "content": "Убедись, что твой ответ содержит только одно из трех слов: 'не владеет', 'частично владеет' или 'владеет'. Никаких дополнительных слов."}
            ],
            extra_body={"reasoning": {"enabled": True}}
        )
        
        final_answer = response2.choices[0].message.content.strip().lower()
        
        if "не владеет" in final_answer:
            return "не владеет"
        elif "частично владеет" in final_answer or "частично" in final_answer:
            return "частично владеет"
        elif "владеет" in final_answer:
            return "владеет"
        else:
            logger.warning(f"Не удалось распознать ответ DeepSeek: {final_answer}")
            return "частично владеет"
            
    except Exception as e:
        logger.error(f"Ошибка при анализе ответа через DeepSeek: {e}")
        return "частично владеет"

def process_test_answer(message):
    user_id = message.from_user.id
    questions = user_states[user_id].get('test_questions', [])
    current_index = user_states[user_id].get('test_current_index', 0)
    test_result_id = user_states[user_id].get('test_result_id')
    
    if current_index >= len(questions) or not test_result_id:
        if not test_result_id:
            bot.reply_to(message, "❌ Ошибка: данные теста потеряны. Тест отменен.", reply_markup=get_student_keyboard())
            del user_states[user_id]
        return
    
    question = questions[current_index]
    answer = message.text
    
    try:
        bot.reply_to(message, "🤖 Анализирую ваш ответ...", reply_markup=ReplyKeyboardRemove())
        
        analysis_result = analyze_student_answer(
            question=question.question,
            student_answer=answer,
            example_answer=question.answer_example
        )
        
        db_manager.create_test_detail(
            test_result_id,
            question.id,
            answer=answer,
            answer_analyze_result=analysis_result
        )
        
        user_states[user_id]['test_answers'].append({
            'question_id': question.id,
            'answer': answer,
            'analysis': analysis_result
        })
        
        analysis_emoji = {
            "не владеет": "❌",
            "частично владеет": "⚠️",
            "владеет": "✅"
        }
        emoji = analysis_emoji.get(analysis_result, "⚠️")
        bot.reply_to(message, f"{emoji} <b>Результат анализа:</b> {analysis_result}", parse_mode='HTML')
        
        user_states[user_id]['test_current_index'] = current_index + 1
        
        if user_states[user_id]['test_current_index'] < len(questions):
            show_next_question(message)
        else:
            finish_test(message)
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на тест: {e}")
        bot.reply_to(message,
            "❌ Произошла ошибка при сохранении ответа. Попробуйте еще раз или используйте /cancel для отмены.",
            reply_markup=ReplyKeyboardRemove()
        )

def generate_feedback_for_question(question: Question, student_answer: str, analysis_result: str, example_answer: Optional[str] = None) -> str:
    """Генерирует обратную связь для вопроса через DeepSeek"""
    try:
        # Используем correct_answer из БД, если он есть, иначе example_answer
        correct_answer = question.correct_answer or example_answer or "Не предоставлен"
        
        prompt = STUDENT_FEEDBACK_PROMPT.format(
            question=question.question,
            correct_answer=correct_answer,
            student_answer=student_answer,
            analysis_result=analysis_result
        )
        
        response = DEEPSEEK_CLIENT.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[{"role": "user", "content": prompt}],
            extra_body={"reasoning": {"enabled": True}}
        )
        
        feedback = response.choices[0].message.content.strip()
        return feedback
    except Exception as e:
        logger.error(f"Ошибка при генерации обратной связи через DeepSeek: {e}")
        return "Не удалось сгенерировать обратную связь. Обратитесь к ментору."

def generate_final_feedback(test_result_id: UUID) -> str:
    """Генерирует финальную обратную связь для всех вопросов, на которые студент ответил неправильно"""
    try:
        test_details = db_manager.get_test_details_by_result_id(test_result_id)
        
        if not test_details:
            return ""
        
        feedback_items = []
        
        for detail in test_details:
            analysis_result = detail.answer_analyze_result
            if not analysis_result or analysis_result == "владеет":
                continue
            
            # Генерируем обратную связь для вопросов с "не владеет" или "частично владеет"
            try:
                question = db_manager.get_question_by_id(detail.question_id)
                if not question:
                    continue
                
                feedback_text = generate_feedback_for_question(
                    question=question,
                    student_answer=detail.answer or "",
                    analysis_result=analysis_result,
                    example_answer=question.answer_example
                )
                
                feedback_items.append({
                    'question': question.question,
                    'feedback': feedback_text,
                    'status': analysis_result
                })
            except Exception as e:
                logger.error(f"Ошибка при генерации обратной связи для вопроса {detail.question_id}: {e}")
                continue
        
        if not feedback_items:
            return ""
        
        # Формируем итоговый текст обратной связи
        feedback_text = "📝 <b>Рекомендации по улучшению:</b>\n\n"
        
        for i, item in enumerate(feedback_items, 1):
            status_emoji = {
                "не владеет": "❌",
                "частично владеет": "⚠️",
                "владеет": "✅"
            }
            emoji = status_emoji.get(item['status'], "⚠️")
            
            feedback_text += f"{i}. {emoji} <b>Вопрос:</b> {item['question'][:100]}{'...' if len(item['question']) > 100 else ''}\n"
            feedback_text += f"<i>{item['feedback']}</i>\n\n"
        
        return feedback_text
    except Exception as e:
        logger.error(f"Ошибка при генерации финальной обратной связи: {e}")
        return ""

def finish_test(message):
    user_id = message.from_user.id
    
    test_start_time = user_states[user_id].get('test_start_time', time.time())
    test_timing = int(time.time() - test_start_time)
    test_result_id = user_states[user_id].get('test_result_id')
    questions = user_states[user_id].get('test_questions', [])
    
    if not test_result_id:
        bot.reply_to(message, "❌ Ошибка при завершении теста.", reply_markup=get_student_keyboard())
        if user_id in user_states:
            del user_states[user_id]
        return
    
    try:
        test_result = TestResult.get(TestResult.id == test_result_id)
        test_result.test_timing = test_timing
        test_result.summary = f"Тест завершен. Отвечено на {len(questions)} вопросов."
        test_result.save()
    except Exception as e:
        logger.error(f"Ошибка при обновлении результата теста: {e}")
    
    minutes = test_timing // 60
    seconds = test_timing % 60
    
    text = (
        f"✅ <b>Тест завершен!</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"• Всего вопросов: {len(questions)}\n"
        f"• Отвечено: {len(user_states[user_id].get('test_answers', []))}\n"
        f"• Время прохождения: {minutes} мин {seconds} сек\n\n"
    )
    
    bot.reply_to(message, text, reply_markup=get_student_keyboard(), parse_mode='HTML')
    
    # Генерируем обратную связь для вопросов, на которые студент ответил неправильно
    try:
        bot.reply_to(message, "🤖 Генерирую рекомендации по улучшению...", reply_markup=get_student_keyboard())
        feedback = generate_final_feedback(test_result_id)
        
        if feedback:
            bot.reply_to(message, feedback, reply_markup=get_student_keyboard(), parse_mode='HTML')
        else:
            bot.reply_to(message, 
                "✅ <b>Отлично!</b> По вашим ответам не требуется дополнительных рекомендаций.",
                reply_markup=get_student_keyboard(),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Ошибка при генерации обратной связи: {e}")
        bot.reply_to(message,
            "💡 <i>Ваши ответы сохранены. Ментор сможет их просмотреть и оценить.</i>",
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )
    
    if user_id in user_states:
        del user_states[user_id]

@bot.message_handler(commands=['results'])
def show_all_results(message):
    if not check_user_access(message):
        return
    if not check_mentor_permission(message):
        return
    
    try:
        students = db_manager.get_all_students()
        if not students:
            bot.reply_to(message, "❌ <b>Студенты не найдены.</b>", parse_mode='HTML', reply_markup=get_mentor_keyboard())
            return
        
        text = "📊 <b>Результаты всех студентов:</b>\n\n"
        
        for student in students:
            results = db_manager.get_test_results_by_agent(student.id)
            
            text += f"👨‍🎓 <b>{student.tg_name}</b>\n"
            text += f"   ID: <code>{student.id}</code>\n"
            text += f"   Всего тестов: {len(results)}\n"
            
            if results:
                latest_result = results[0]
                created = latest_result.created_at.strftime("%d.%m.%Y %H:%M") if latest_result.created_at else "N/A"
                text += f"   Последний тест: {created}\n"
                text += f"   Вопросов: {latest_result.skills_total}\n"
                text += f"   Не сдано: {latest_result.skills_not_passed}, Низкий: {latest_result.skills_low}, Сдано: {latest_result.skills_passed}\n"
            
            text += "\n"
        
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_mentor_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении результатов студентов: {e}")
        bot.reply_to(message, "❌ Ошибка при получении результатов студентов.", reply_markup=get_mentor_keyboard())

@bot.message_handler(commands=['student_results'])
def show_student_results(message):
    if not check_user_access(message):
        return
    if not check_mentor_permission(message):
        return
    
    try:
        student_id = UUID(message.text.split()[1])
        student = db_manager.get_agent_by_id(student_id)
        
        if not student or student.role != RoleEnum.STUDENT.value:
            bot.reply_to(message, "❌ Студент не найден.", reply_markup=get_mentor_keyboard())
            return
        
        results = db_manager.get_test_results_by_agent(student.id)
        
        if not results:
            bot.reply_to(message,
                f"📊 <b>Результаты студента {student.tg_name}:</b>\n\n"
                "У этого студента пока нет пройденных тестов.",
                parse_mode='HTML',
                reply_markup=get_mentor_keyboard()
            )
            return
        
        text = f"📊 <b>Результаты студента {student.tg_name}:</b>\n\n"
        
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
            text += f"   ❌ Не сдано: {result.skills_not_passed}\n"
            text += f"   ⚠️ Низкий: {result.skills_low}\n"
            text += f"   ✅ Сдано: {result.skills_passed}\n"
            if result.summary:
                text += f"   📝 {result.summary[:100]}{'...' if len(result.summary) > 100 else ''}\n"
            text += "\n"
        
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_mentor_keyboard())
    except IndexError:
        bot.reply_to(message,
            "Использование: /student_results <student_id>\n\n"
            "Для получения ID студента используйте /results",
            reply_markup=get_mentor_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID студента.", reply_markup=get_mentor_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении результатов студента: {e}")
        bot.reply_to(message, "❌ Ошибка при получении результатов студента.", reply_markup=get_mentor_keyboard())

@bot.message_handler(commands=['my_results'])
def show_my_results(message):
    if not check_user_access(message):
        return
    
    tg_name = get_user_tg_name(message)
    agent = db_manager.get_agent_by_tg_name(tg_name)
    
    if not agent:
        bot.reply_to(message, "❌ Пользователь не найден.", reply_markup=get_student_keyboard())
        return
    
    results = db_manager.get_test_results_by_agent(agent.id)
    
    if not results:
        bot.reply_to(message,
            "📊 <b>Результаты тестов</b>\n\n"
            "У вас пока нет пройденных тестов.\n"
            "Используйте кнопку '🧪 Начать тест' для прохождения тестирования.",
            reply_markup=get_student_keyboard(),
            parse_mode='HTML'
        )
        return
    
    text = f"📊 <b>Мои результаты ({len(results)}):</b>\n\n"
    text += "Выберите тест, чтобы посмотреть детали и рекомендации:\n\n"
    
    # Создаем inline-кнопки для каждого теста
    keyboard = []
    
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
        
        # Добавляем кнопку для просмотра деталей теста
        keyboard.append([InlineKeyboardButton(
            f"📄 Тест от {created}",
            callback_data=f"view_test_{result.id}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot.reply_to(message, text, reply_markup=reply_markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    bot.answer_callback_query(call.id)
    
    if not check_user_access(call.message):
        return
    
    tg_name = get_user_tg_name(call.message)
    is_mentor = db_manager.is_mentor_by_tg_name(tg_name)
    
    # Обработка callback для студентов (просмотр теста и возврат к списку)
    if call.data.startswith("view_test_"):
        test_result_id_str = call.data.replace("view_test_", "")
        try:
            test_result_id = UUID(test_result_id_str)
            # Проверяем, что тест принадлежит этому студенту
            agent = db_manager.get_agent_by_tg_name(tg_name)
            if agent:
                results = db_manager.get_test_results_by_agent(agent.id)
                if any(r.id == test_result_id for r in results):
                    show_test_details(call, test_result_id)
                else:
                    bot.answer_callback_query(call.id, "❌ Тест не найден", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ Пользователь не найден", show_alert=True)
        except ValueError:
            bot.answer_callback_query(call.id, "❌ Неверный формат ID теста", show_alert=True)
        return
    
    if call.data == "back_to_results":
        # Возвращаемся к списку результатов
        agent = db_manager.get_agent_by_tg_name(tg_name)
        if agent:
            results = db_manager.get_test_results_by_agent(agent.id)
            if results:
                text = f"📊 <b>Мои результаты ({len(results)}):</b>\n\n"
                text += "Выберите тест, чтобы посмотреть детали и рекомендации:\n\n"
                
                keyboard = []
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
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📄 Тест от {created}",
                        callback_data=f"view_test_{result.id}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # Обработка callback только для менторов
    if not is_mentor:
        bot.answer_callback_query(call.id, "❌ У вас нет прав для выполнения этой команды", show_alert=True)
        return
    
    if call.data == "list_skills":
        list_skills_callback(call)
    elif call.data == "list_questions":
        list_questions_callback(call)

def list_skills_callback(call):
    try:
        skills = db_manager.get_all_skills()
        if not skills:
            bot.edit_message_text("📋 Компетенции не найдены.", 
                                 chat_id=call.message.chat.id, 
                                 message_id=call.message.message_id)
            return
        
        text = "📋 Список компетенций:\n\n"
        for i, skill in enumerate(skills, 1):
            text += f"{i}. <b>{skill.skill}</b>\n"
            text += f"   ID: <code>{str(skill.id)[:8]}</code>\n"
            if skill.description:
                desc = skill.description[:50] + "..." if len(skill.description) > 50 else skill.description
                text += f"   Описание: {desc}\n"
            text += "\n"
        
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка компетенций: {e}")
        bot.edit_message_text("❌ Ошибка при получении списка компетенций.", 
                             chat_id=call.message.chat.id, 
                             message_id=call.message.message_id)

def list_questions_callback(call):
    try:
        questions = db_manager.get_all_questions()
        if not questions:
            bot.edit_message_text("❓ Вопросы не найдены.", 
                                 chat_id=call.message.chat.id, 
                                 message_id=call.message.message_id)
            return
        
        text = "❓ Список вопросов:\n\n"
        for i, question in enumerate(questions, 1):
            q_text = question.question[:60] + "..." if len(question.question) > 60 else question.question
            text += f"{i}. {q_text}\n"
            text += f"   ID: <code>{str(question.id)[:8]}</code>\n"
            text += f"   Приоритет: {question.priority}\n\n"
        
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка при получении списка вопросов: {e}")
        bot.edit_message_text("❌ Ошибка при получении списка вопросов.", 
                             chat_id=call.message.chat.id, 
                             message_id=call.message.message_id)

def show_test_details(call, test_result_id: UUID):
    """Показывает детали теста с рекомендациями"""
    try:
        test_result = TestResult.get(TestResult.id == test_result_id)
        
        # Формируем основную информацию о тесте
        created = test_result.created_at.strftime("%d.%m.%Y %H:%M") if test_result.created_at else "N/A"
        timing = test_result.test_timing
        if timing:
            minutes = timing // 60
            seconds = timing % 60
            time_str = f"{minutes} мин {seconds} сек"
        else:
            time_str = "N/A"
        
        text = (
            f"📊 <b>Детали теста</b>\n\n"
            f"📅 Дата: {created}\n"
            f"⏱ Время прохождения: {time_str}\n"
            f"📋 Всего вопросов: {test_result.skills_total}\n\n"
        )
        
        # Получаем все детали теста
        test_details = db_manager.get_test_details_by_result_id(test_result_id)
        
        if test_details:
            # Подсчитываем статистику
            not_passed = sum(1 for d in test_details if d.answer_analyze_result == "не владеет")
            partially = sum(1 for d in test_details if d.answer_analyze_result == "частично владеет")
            passed = sum(1 for d in test_details if d.answer_analyze_result == "владеет")
            
            text += (
                f"📈 <b>Статистика:</b>\n"
                f"❌ Не владеет: {not_passed}\n"
                f"⚠️ Частично владеет: {partially}\n"
                f"✅ Владеет: {passed}\n\n"
            )
        
        # Генерируем рекомендации (уже был answer_callback_query в button_callback, но здесь показываем процесс)
        feedback = generate_final_feedback(test_result_id)
        
        if feedback:
            text += feedback
        else:
            text += "✅ <b>Отлично!</b> По вашим ответам не требуется дополнительных рекомендаций.\n"
            text += "Все ответы оценены положительно."
        
        # Добавляем кнопку "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_results")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except TestResult.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Тест не найден", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при получении деталей теста: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при загрузке деталей теста", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user_access(message):
        return
    
    text = message.text
    tg_name = get_user_tg_name(message)
    agent = db_manager.get_agent_by_tg_name(tg_name)
    
    if not agent:
        return
    
    is_mentor = agent.is_mentor()
    
    user_id = message.from_user.id
    if user_id in user_states and 'test_questions' in user_states[user_id]:
        keyboard_commands = ["🏠 Меню", "ℹ️ Помощь", "📋 Компетенции", "❓ Вопросы",
                             "🧪 Начать тест", "📊 Мои результаты", "📊 Результаты студентов"]
        
        if text in keyboard_commands and text != "/cancel":
            bot.reply_to(message,
                "⚠️ <b>Идет тестирование!</b>\n\n"
                "Пожалуйста, завершите тест или используйте /cancel для отмены.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        process_test_answer(message)
        return
    
    if not is_mentor:
        if text == "🧪 Начать тест":
            start_test(message)
            return
        
        if text == "📊 Мои результаты":
            show_my_results(message)
            return
        
        return
    
    if text == "🏠 Меню":
        if user_id in user_states:
            del user_states[user_id]
        show_main_menu(message)
        return
    
    if text == "ℹ️ Помощь":
        if user_id in user_states:
            user_states[user_id].pop('action', None)
        show_mentor_help(message)
        return
    
    if text == "📋 Компетенции":
        if user_id in user_states:
            user_states[user_id].pop('action', None)
        list_skills(message)
        return
    
    if text == "❓ Вопросы":
        if user_id in user_states:
            user_states[user_id].pop('action', None)
        list_questions(message)
        return
    
    if text == "📊 Результаты студентов":
        if user_id in user_states:
            user_states[user_id].pop('action', None)
        show_all_results(message)
        return

def show_main_menu(message):
    text = (
        "👨‍🏫 <b>Главное меню ментора</b>\n\n"
        "<b>Описание кнопок:</b>\n\n"
        "📋 <b>Компетенции</b> - Показать список всех компетенций с их ID\n"
        "❓ <b>Вопросы</b> - Показать список всех вопросов с их ID (только просмотр)\n\n"
        "📊 <b>Результаты студентов</b> - Просмотреть результаты тестов студентов\n\n"
        "🏠 <b>Меню</b> - Вернуться в это меню\n"
        "ℹ️ <b>Помощь</b> - Подробная справка\n\n"
        "⚠️ <i>Все изменения (добавление, редактирование, удаление, связывание) происходят напрямую через БД</i>"
    )
    bot.reply_to(message, text, reply_markup=get_mentor_keyboard(), parse_mode='HTML')

def show_mentor_help(message):
    text = (
        "ℹ️ <b>Подробная справка для ментора</b>\n\n"
        "<b>📋 Компетенции</b>\n"
        "Показывает список всех компетенций с их ID, названиями и описаниями.\n\n"
        
        "<b>❓ Вопросы</b>\n"
        "Показывает список всех вопросов с их ID и приоритетами.\n\n"
        
        "<b>📊 Результаты студентов</b>\n"
        "Показывает результаты тестов всех студентов.\n\n"
        
        "<b>🏠 Меню</b>\n"
        "Возвращает в главное меню.\n\n"
        
        "<b>ℹ️ Помощь</b>\n"
        "Показывает это сообщение справки.\n\n"
        
        "⚠️ <i>Все изменения (добавление, редактирование, удаление, связывание) происходят напрямую через БД</i>"
    )
    bot.reply_to(message, text, reply_markup=get_mentor_keyboard(), parse_mode='HTML')

def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.critical("❌ BOT_TOKEN не установлен")
        sys.exit(1)

    logger.info("🚀 Запуск бота...")
    
    # Инициализация подключения к базе данных
    try:
        logger.info("Подключение к базе данных...")
        db_manager.connect()
        logger.info("Инициализация таблиц базы данных...")
        db_manager.create_tables()
        logger.info("✅ База данных готова к работе")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации базы данных: {e}")
        sys.exit(1)
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Закрываем подключение к БД при завершении
        try:
            db_manager.disconnect()
        except:
            pass

if __name__ == '__main__':
    main()


'0======3    (. )Y( .)'