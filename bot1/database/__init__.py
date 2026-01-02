"""
Пакет для работы с базой данных
"""
from .models_peewee import (
    Agent,
    Question,
    Skill,
    SkillQuestion,
    TestResult,
    TestDetail,
    GradeEnum,
    RoleEnum
)
from .db_manager_peewee import db_manager
from .config import db_config

__all__ = [
    "Agent",
    "Question",
    "Skill",
    "SkillQuestion",
    "TestResult",
    "TestDetail",
    "GradeEnum",
    "RoleEnum",
    "db_manager",
    "db_config"
]

