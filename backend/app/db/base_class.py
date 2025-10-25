"""Declarative base class for SQLAlchemy models."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class that configures naming conventions later if needed."""

    __abstract__ = True
