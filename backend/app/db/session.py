"""Database session and engine configuration."""
from ..database import SessionLocal, engine, get_db


def get_db_session():
    """Yield a database session for request scope."""

    yield from get_db()
