"""SQLAlchemy database engine and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.core.logging import logger

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
except Exception as exc:
    logger.warning(
        f"Failed to connect to primary DATABASE_URL '{settings.DATABASE_URL}'. Falling back to local SQLite: {exc}"
    )
    engine = create_engine(
        "sqlite:///./ip_sakti.db",
        echo=settings.DB_ECHO,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates all database tables based on registered models."""
    logger.info("Synchronizing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema synchronized successfully.")
