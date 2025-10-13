"""FastAPI dependencies for Softmobile."""
from collections.abc import Generator

from sqlalchemy.orm import Session

from ..db.session import get_db_session


def get_db() -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session per request."""

    yield from get_db_session()
