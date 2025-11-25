"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

try:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
    
    # Проверка подключения
    engine.connect()
    logger.info("Database connection successful")
except OperationalError as e:
    logger.warning(f"Database connection failed: {e}")
    logger.warning("Backend will start but database operations will fail")
    # Создаем engine даже если БД недоступна, чтобы приложение могло запуститься
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_pre_ping=False,  # Отключаем проверку если БД недоступна
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Please ensure PostgreSQL is running."
        )
    finally:
        db.close()
