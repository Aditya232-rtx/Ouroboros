"""
Ouroboros AI - Database Session Management
SQLAlchemy connection and session handling
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from config.settings import settings
from src.database.models import Base

logger = logging.getLogger(__name__)


# Create database engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=False  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_db():
    """Drop all database tables (DANGEROUS - use only in development)"""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with get_db() as db:
            scan = db.query(Scan).filter_by(scan_id="SCAN-123").first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session (for dependency injection in FastAPI).
    
    Usage:
        @app.get("/scans/{scan_id}")
        def get_scan(scan_id: str, db: Session = Depends(get_db_session)):
            return db.query(Scan).filter_by(scan_id=scan_id).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
