from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from .base import Base


class CorporateSearchSession(Base):
    __tablename__ = 'corporates_search_sessions'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    channel = Column(String(20), nullable=False, default='web')
    origin = Column(String(20), nullable=False, default='inventory')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship('CorporateQueryEvent', back_populates='session', cascade='all, delete-orphan')


class CorporateQueryEvent(Base):
    __tablename__ = 'corporates_query_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('corporates_search_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    term = Column(String(120), nullable=False, index=True)
    normalized_term = Column(String(120), nullable=False, index=True)
    filters = Column(Text, nullable=True)
    results_count = Column(Integer, nullable=False, default=0)
    action = Column(String(32), nullable=False, default='search')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    session = relationship('CorporateSearchSession', back_populates='events')


Index('ix_cqe_term_ts', CorporateQueryEvent.term, CorporateQueryEvent.timestamp)
