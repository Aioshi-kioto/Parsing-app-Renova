"""
SQLAlchemy Database Setup — PostgreSQL Only.

Sprint 2.5: Убрали SQLite fallback. Единственная БД — PostgreSQL.
Если psycopg2 не установлен — будет явная ошибка при старте.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from backend.config import settings
except Exception:
    from config import settings

# PostgreSQL — единственный движок
SQLALCHEMY_DATABASE_URL = getattr(settings, "DATABASE_URL", "postgresql://renova:password@localhost:5432/renova")

# Нормализация URL (Heroku / Railway иногда дают postgres:// вместо postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Локальный запуск: хост "db" есть только в Docker; подменяем на localhost
if "@db:" in SQLALCHEMY_DATABASE_URL or "@db/" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("@db:", "@localhost:").replace("@db/", "@localhost/")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_sqlalchemy_database():
    """Создать все ORM-таблицы если их ещё нет."""
    try:
        from backend.db_models import Base
    except Exception:
        from db_models import Base
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency для получения сессии БД в FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
