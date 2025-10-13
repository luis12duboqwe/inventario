"""Database session and engine configuration."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings

engine = create_engine(
    settings.sqlalchemy_database_uri,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Yield a database session for request scope."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
