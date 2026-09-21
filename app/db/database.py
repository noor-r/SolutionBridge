"""Database connectivity and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()

# Configure engine based explicitly on DATABASE_URL
engine_kwargs = {"echo": False}

if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # MySQL 8 pool settings
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
    )

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_db_connection() -> bool:
    """Test connection to the database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False


def init_db() -> None:
    """Create all tables in the database."""
    import app.db.models  # Ensure models are imported for metadata registration
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")
