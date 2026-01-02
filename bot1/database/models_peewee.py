"""
Модели данных для базы данных с использованием Peewee ORM
"""
import peewee
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional
import os
import uuid
from datetime import datetime, timezone  # timezone нужен для UTC
from .config import db_config

# Создаем подключение к базе данных
db = peewee.PostgresqlDatabase(
    db_config.database,
    user=db_config.user,
    password=db_config.password,
    host=db_config.host,
    port=db_config.port
)

class GradeEnum(str, Enum):
    """Enum для оценки навыков"""
    NOT_PASSED = "not_passed"
    LOW = "low"
    PASSED = "passed"

class RoleEnum(str, Enum):
    """Enum для ролей пользователей"""
    STUDENT = "student"
    MENTOR = "mentor"

class UUIDField(peewee.Field):
    """Пользовательское поле для UUID"""
    field_type = 'UUID'

class BaseModel(peewee.Model):
    """Базовая модель со общим Meta"""
    class Meta:
        database = db

class Agent(BaseModel):
    """Модель агента (пользователя)"""
    id = peewee.AutoField(primary_key=True)
    tg_name = peewee.CharField(max_length=255, unique=True)
    role = peewee.CharField(max_length=20, default=RoleEnum.STUDENT.value)  # .value, потому что Peewee хранит строку
    created_at = peewee.DateTimeField(default=lambda:datetime.now(timezone.utc))

    class Meta:
        table_name = 'agents'  # Явно задаём имя таблицы

    def is_mentor(self) -> bool:
        return self.role == RoleEnum.MENTOR.value

    def is_student(self) -> bool:
        return self.role == RoleEnum.STUDENT.value

class Question(BaseModel):
    """Модель вопроса"""
    id = peewee.AutoField(primary_key=True)
    question = peewee.TextField()
    answer_example = peewee.TextField(null=True)  # Пример ответа (может показываться студентам)
    correct_answer = peewee.TextField(null=True)  # Правильный ответ (только для анализа, не показывается студентам)
    priority = peewee.IntegerField(default=0)

    class Meta:
        table_name = 'questions'

class Skill(BaseModel):
    """Модель навыка (компетенции)"""
    id = peewee.AutoField(primary_key=True)
    skill = peewee.CharField(max_length=255)
    description = peewee.TextField(null=True)
    grade = peewee.CharField(max_length=20, null=True)

    class Meta:
        table_name = 'skills'

class SkillQuestion(BaseModel):
    """Модель связи навыка и вопроса (many-to-many)"""
    id = peewee.AutoField(primary_key=True)
    skill_id = UUIDField()
    question_id = UUIDField()

    class Meta:
        table_name = 'skills_questions'
        # Если захочешь уникальность пары (рекомендую добавить индекс вручную в миграции)
        # indexes = ((('skill_id', 'question_id'), True),)

class TestResult(BaseModel):
    """Модель результата тестирования"""
    id = peewee.AutoField(primary_key=True)
    agent_id = UUIDField()
    summary = peewee.TextField(null=True)
    test_timing = peewee.IntegerField(null=True)
    skills_total = peewee.IntegerField(default=0)
    skills_not_passed = peewee.IntegerField(default=0)
    skills_low = peewee.IntegerField(default=0)
    skills_passed = peewee.IntegerField(default=0)
    created_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'test_result'

class TestDetail(BaseModel):
    """Модель детали тестирования (ответ на конкретный вопрос)"""
    id = peewee.AutoField(primary_key=True)
    test_result_id = UUIDField()
    question_id = UUIDField()
    answer = peewee.TextField(null=True)
    answer_analyze_result = peewee.CharField(max_length=50, null=True)

    class Meta:
        table_name = 'test_details'