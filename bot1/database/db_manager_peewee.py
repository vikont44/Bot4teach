"""
Менеджер для работы с базой данных с использованием Peewee ORM
"""




import peewee
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .models_peewee import db, Agent, Question, Skill, SkillQuestion, TestResult, TestDetail, GradeEnum, RoleEnum
from .config import db_config

class DatabaseManager:
    """Класс для управления подключением и операциями с БД"""
    
    def __init__(self):
        self.db = db
    
    def _create_database_if_not_exists(self):
        """Создает базу данных, если она не существует"""
        try:
            # Используем psycopg2 напрямую для проверки и создания базы данных
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                user=db_config.user,
                password=db_config.password,
                database='postgres'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Проверяем, существует ли база данных
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_config.database,)
            )
            
            if not cursor.fetchone():
                # База данных не существует, создаем её
                print(f"База данных '{db_config.database}' не найдена. Создание...")
                cursor.execute(f'CREATE DATABASE "{db_config.database}"')
                print(f"База данных '{db_config.database}' успешно создана!")
            else:
                print(f"База данных '{db_config.database}' уже существует")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Предупреждение: Не удалось автоматически создать базу данных: {e}")
            print("Убедитесь, что база данных существует или создайте её вручную:")
            print(f"  CREATE DATABASE {db_config.database};")
            raise
    
    def connect(self):
        """Создает подключение к БД"""
        try:
            self.db.connect()
            print(f"Подключение к БД {db_config.database} установлено")
        except peewee.OperationalError as e:
            error_str = str(e).lower()
            
            # Проверяем тип ошибки и даем соответствующие инструкции
            if "connection refused" in error_str or "could not connect" in error_str:
                error_msg = (
                    f"❌ Не удалось подключиться к серверу PostgreSQL!\n\n"
                    f"🔍 Детали подключения:\n"
                    f"  Host: {db_config.host}\n"
                    f"  Port: {db_config.port}\n"
                    f"  Database: {db_config.database}\n"
                    f"  User: {db_config.user}\n\n"
                    f"⚠️  Возможные причины:\n"
                    f"  1. Сервер PostgreSQL не запущен\n"
                    f"  2. Неправильный адрес или порт\n"
                    f"  3. Файрвол блокирует соединение\n"
                    f"  4. Сервер не принимает удаленные подключения\n\n"
                    f"💡 Решения:\n"
                    f"  • Проверьте, запущен ли PostgreSQL на сервере {db_config.host}\n"
                    f"  • Убедитесь, что порт {db_config.port} открыт и доступен\n"
                    f"  • Проверьте файл .env и настройки подключения\n"
                    f"  • Если используете локальный PostgreSQL, установите DB_HOST=localhost\n\n"
                    f"📝 Для локального PostgreSQL создайте файл .env:\n"
                    f"  DB_HOST=localhost\n"
                    f"  DB_PORT=5432\n"
                    f"  DB_NAME=telegram_bot\n"
                    f"  DB_USER=postgres\n"
                    f"  DB_PASSWORD=your_password\n\n"
                    f"Оригинальная ошибка: {e}"
                )
                print(error_msg)
                raise ConnectionError(error_msg) from e
            elif "does not exist" in error_str or "не существует" in error_str:
                try:
                    print(f"База данных '{db_config.database}' не существует. Попытка создать...")
                    self._create_database_if_not_exists()
                    # Повторно пытаемся подключиться
                    self.db.connect()
                    print(f"Подключение к БД {db_config.database} установлено")
                except Exception as create_error:
                    error_msg = (
                        f"❌ Не удалось создать базу данных '{db_config.database}'!\n"
                        f"Ошибка: {create_error}\n\n"
                        f"Создайте базу данных вручную, выполнив:\n"
                        f"  CREATE DATABASE {db_config.database};\n\n"
                        f"Или проверьте права пользователя {db_config.user}"
                    )
                    print(error_msg)
                    raise ConnectionError(error_msg) from create_error
            else:
                error_msg = (
                    f"❌ Ошибка подключения к PostgreSQL!\n\n"
                    f"🔍 Настройки подключения:\n"
                    f"  DB_HOST={db_config.host}\n"
                    f"  DB_PORT={db_config.port}\n"
                    f"  DB_NAME={db_config.database}\n"
                    f"  DB_USER={db_config.user}\n\n"
                    f"Убедитесь, что:\n"
                    f"  1. PostgreSQL установлен и запущен\n"
                    f"  2. Настройки подключения корректны\n"
                    f"  3. Файл .env настроен правильно\n"
                    f"  4. Пользователь {db_config.user} имеет права доступа\n\n"
                    f"Ошибка: {e}"
                )
                print(error_msg)
                raise ConnectionError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"❌ Неожиданная ошибка при подключении к БД: {e}\n"
                f"Проверьте настройки подключения в файле .env"
            )
            print(error_msg)
            raise ConnectionError(error_msg) from e
    
    def disconnect(self):
        """Закрывает подключение к БД"""
        if not self.db.is_closed():
            self.db.close()
            print("Подключение к БД закрыто")
    
    def create_tables(self):
        """Создает таблицы в БД"""
        self.db.create_tables([
            Agent, Question, Skill, SkillQuestion, TestResult, TestDetail
        ], safe=True)
        print("Таблицы созданы успешно")
    
    def execute_sql_file(self, file_path: str):
        """Выполняет SQL скрипт из файла"""
        # Эта функция не нужна при использовании Peewee, т.к. мы используем модели
        # Для совместимости с оригинальным кодом
        pass
    
    def init_database(self):
        """Инициализирует базу данных, создавая все таблицы"""
        self.create_tables()
    
    # Методы для работы с агентами
    def create_agent(self, tg_name: str, role: RoleEnum = RoleEnum.STUDENT) -> Agent:
        """Создает нового агента в БД"""
        agent = Agent.create(
            id=uuid4(),
            tg_name=tg_name,
            role=role.value
        )
        return agent
    
    def get_agent_by_tg_name(self, tg_name: str) -> Optional[Agent]:
        """Получает агента по Telegram имени"""
        try:
            return Agent.get(Agent.tg_name == tg_name)
        except Agent.DoesNotExist:
            return None
    
    def get_agent_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Получает агента по ID"""
        try:
            return Agent.get(Agent.id == agent_id)
        except Agent.DoesNotExist:
            return None
    
    def update_agent_role(self, agent_id: UUID, new_role: RoleEnum) -> bool:
        """Обновляет роль агента"""
        try:
            agent = Agent.get(Agent.id == agent_id)
            agent.role = new_role.value
            agent.save()
            return True
        except Agent.DoesNotExist:
            return False
    
    def set_mentor_role(self, agent_id: UUID) -> bool:
        """Устанавливает роль ментора для агента"""
        return self.update_agent_role(agent_id, RoleEnum.MENTOR)
    
    def set_student_role(self, agent_id: UUID) -> bool:
        """Устанавливает роль студента для агента"""
        return self.update_agent_role(agent_id, RoleEnum.STUDENT)
    
    def is_mentor(self, agent_id: UUID) -> bool:
        """Проверяет, является ли агент ментором"""
        agent = self.get_agent_by_id(agent_id)
        return agent is not None and agent.is_mentor()
    
    def is_mentor_by_tg_name(self, tg_name: str) -> bool:
        """Проверяет, является ли агент ментором по Telegram имени"""
        agent = self.get_agent_by_tg_name(tg_name)
        return agent is not None and agent.is_mentor()
    
    def add_mentor(self, tg_name: str) -> Agent:
        """Добавляет нового ментора (админа)"""
        # Сначала получаем или создаем агента
        agent = self.get_agent_by_tg_name(tg_name)
        if agent:
            # Если агент существует, обновляем роль
            self.set_mentor_role(agent.id)
            return self.get_agent_by_id(agent.id)
        else:
            # Создаем нового агента с ролью ментора
            return self.create_agent(tg_name, RoleEnum.MENTOR)
    
    def get_all_mentors(self) -> List[Agent]:
        """Получает список всех менторов"""
        return list(Agent.select().where(Agent.role == RoleEnum.MENTOR.value))
    
    def get_all_students(self) -> List[Agent]:
        """Получает список всех студентов"""
        return list(Agent.select().where(Agent.role == RoleEnum.STUDENT.value))
    
    # Методы для работы с вопросами
    def create_question(self, question: str, answer_example: Optional[str] = None, correct_answer: Optional[str] = None, priority: int = 0) -> Question:
        """Создает новый вопрос в БД"""
        question_obj = Question.create(
            id=uuid4(),
            question=question,
            answer_example=answer_example,
            correct_answer=correct_answer,
            priority=priority
        )
        return question_obj
    
    def get_question_by_id(self, question_id: UUID) -> Optional[Question]:
        """Получает вопрос по ID"""
        try:
            return Question.get(Question.id == question_id)
        except Question.DoesNotExist:
            return None
    
    def get_all_questions(self) -> List[Question]:
        """Получает все вопросы"""
        return list(Question.select().order_by(Question.priority.desc()))
    
    # Методы для работы с навыками
    def create_skill(self, skill: str, description: Optional[str] = None, grade: Optional[GradeEnum] = None) -> Skill:
        """Создает новый навык в БД"""
        skill_obj = Skill.create(
            id=uuid4(),
            skill=skill,
            description=description,
            grade=grade.value if grade else None
        )
        return skill_obj
    
    def get_skill_by_id(self, skill_id: UUID) -> Optional[Skill]:
        """Получает навык по ID"""
        try:
            return Skill.get(Skill.id == skill_id)
        except Skill.DoesNotExist:
            return None
    
    def get_all_skills(self) -> List[Skill]:
        """Получает все навыки"""
        return list(Skill.select().order_by(Skill.skill))
    
    def update_skill(
        self,
        skill_id: UUID,
        skill: Optional[str] = None,
        description: Optional[str] = None,
        grade: Optional[GradeEnum] = None
    ) -> Optional[Skill]:
        """Обновляет навык"""
        try:
            skill_obj = Skill.get(Skill.id == skill_id)
            if skill is not None:
                skill_obj.skill = skill
            if description is not None:
                skill_obj.description = description
            if grade is not None:
                skill_obj.grade = grade.value
            skill_obj.save()
            return skill_obj
        except Skill.DoesNotExist:
            return None
    
    def update_question(
        self,
        question_id: UUID,
        question: Optional[str] = None,
        answer_example: Optional[str] = None,
        correct_answer: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Optional[Question]:
        """Обновляет вопрос"""
        try:
            question_obj = Question.get(Question.id == question_id)
            if question is not None:
                question_obj.question = question
            if answer_example is not None:
                question_obj.answer_example = answer_example
            if correct_answer is not None:
                question_obj.correct_answer = correct_answer
            if priority is not None:
                question_obj.priority = priority
            question_obj.save()
            return question_obj
        except Question.DoesNotExist:
            return None
    
    def delete_skill(self, skill_id: UUID) -> bool:
        """Удаляет навык"""
        try:
            skill_obj = Skill.get(Skill.id == skill_id)
            skill_obj.delete_instance()
            return True
        except Skill.DoesNotExist:
            return False
    
    def delete_question(self, question_id: UUID) -> bool:
        """Удаляет вопрос"""
        try:
            question_obj = Question.get(Question.id == question_id)
            question_obj.delete_instance()
            return True
        except Question.DoesNotExist:
            return False
    
    # Методы для работы со связями навыков и вопросов
    def link_skill_to_question(self, skill_id: UUID, question_id: UUID) -> SkillQuestion:
        """Связывает навык с вопросом"""
        # Проверяем, существует ли уже связь
        try:
            existing_link = SkillQuestion.get(
                (SkillQuestion.skill_id == skill_id) & 
                (SkillQuestion.question_id == question_id)
            )
            return existing_link
        except SkillQuestion.DoesNotExist:
            # Создаем новую связь
            link = SkillQuestion.create(
                id=uuid4(),
                skill_id=skill_id,
                question_id=question_id
            )
            return link
    
    def unlink_skill_from_question(self, skill_id: UUID, question_id: UUID) -> bool:
        """Удаляет связь между навыком и вопросом"""
        try:
            link = SkillQuestion.get(
                (SkillQuestion.skill_id == skill_id) & 
                (SkillQuestion.question_id == question_id)
            )
            link.delete_instance()
            return True
        except SkillQuestion.DoesNotExist:
            return False
    
    def get_questions_for_skill(self, skill_id: UUID) -> List[Question]:
        """Получает все вопросы для навыка"""
        question_ids = (
            SkillQuestion
            .select(SkillQuestion.question_id)
            .where(SkillQuestion.skill_id == skill_id)
        )
        question_ids_list = [link.question_id for link in question_ids]
        
        if not question_ids_list:
            return []
        
        return list(Question.select().where(Question.id.in_(question_ids_list)).order_by(Question.priority.desc()))
    
    def get_skills_for_question(self, question_id: UUID) -> List[Skill]:
        """Получает все навыки для вопроса"""
        skill_ids = (
            SkillQuestion
            .select(SkillQuestion.skill_id)
            .where(SkillQuestion.question_id == question_id)
        )
        skill_ids_list = [link.skill_id for link in skill_ids]
        
        if not skill_ids_list:
            return []
        
        return list(Skill.select().where(Skill.id.in_(skill_ids_list)).order_by(Skill.skill))
    
    # Методы для работы с результатами тестов
    def create_test_result(
        self,
        agent_id: UUID,
        summary: Optional[str] = None,
        test_timing: Optional[int] = None,
        skills_total: int = 0,
        skills_not_passed: int = 0,
        skills_low: int = 0,
        skills_passed: int = 0
    ) -> TestResult:
        """Создает новый результат тестирования"""
        test_result = TestResult.create(
            id=uuid4(),
            agent_id=agent_id,
            summary=summary,
            test_timing=test_timing,
            skills_total=skills_total,
            skills_not_passed=skills_not_passed,
            skills_low=skills_low,
            skills_passed=skills_passed
        )
        return test_result
    
    def create_test_detail(
        self,
        test_result_id: UUID,
        question_id: UUID,
        answer: Optional[str] = None,
        answer_analyze_result: Optional[str] = None
    ) -> TestDetail:
        """Создает новую деталь тестирования"""
        test_detail = TestDetail.create(
            id=uuid4(),
            test_result_id=test_result_id,
            question_id=question_id,
            answer=answer,
            answer_analyze_result=answer_analyze_result
        )
        return test_detail
    
    def get_test_results_by_agent(self, agent_id: UUID) -> List[TestResult]:
        """Получает все результаты тестов агента"""
        return list(TestResult.select().where(TestResult.agent_id == agent_id).order_by(TestResult.created_at.desc()))
    
    def get_test_details_by_result_id(self, test_result_id: UUID) -> List[TestDetail]:
        """Получает все детали теста по ID результата"""
        return list(TestDetail.select().where(TestDetail.test_result_id == test_result_id))

# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()