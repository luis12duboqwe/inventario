from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from ..models.corporate_search import CorporateSearchSession, CorporateQueryEvent


class CorporateSearchRepository:
    def __init__(self, db: Session):
        self.db = db

    # Sessions
    def create_session(self, session_id: str, user_id: str, channel: str, origin: str) -> CorporateSearchSession:
        s = CorporateSearchSession(id=session_id, user_id=user_id, channel=channel, origin=origin)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def end_session(self, session_id: str) -> CorporateSearchSession:
        s = self.db.get(CorporateSearchSession, session_id)
        if not s:
            raise ValueError('Session not found')
        s.ended_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(s)
        return s

    def get_session(self, session_id: str) -> CorporateSearchSession:
        return self.db.get(CorporateSearchSession, session_id)

    def list_sessions(self, user_id: str = None, limit: int = 50, offset: int = 0) -> List[CorporateSearchSession]:
        q = self.db.query(CorporateSearchSession).order_by(CorporateSearchSession.started_at.desc())
        if user_id:
            q = q.filter(CorporateSearchSession.user_id == user_id)
        return q.offset(offset).limit(limit).all()

    # Events
    def add_event(self, session_id: str, term: str, normalized_term: str, filters: str, results_count: int, action: str) -> CorporateQueryEvent:
        e = CorporateQueryEvent(session_id=session_id, term=term, normalized_term=normalized_term, filters=filters, results_count=results_count, action=action)
        self.db.add(e)
        self.db.commit()
        self.db.refresh(e)
        return e

    def list_events(self, session_id: str, limit: int = 200, offset: int = 0) -> List[CorporateQueryEvent]:
        return (self.db.query(CorporateQueryEvent)
                .filter(CorporateQueryEvent.session_id == session_id)
                .order_by(CorporateQueryEvent.timestamp.asc())
                .offset(offset).limit(limit).all())

    # Stats
    def top_terms(self, days: int = 7, limit: int = 20) -> List[Tuple[str, int]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (self.db.query(CorporateQueryEvent.term, func.count(1).label('hits'))
                .filter(CorporateQueryEvent.timestamp >= cutoff)
                .group_by(CorporateQueryEvent.term)
                .order_by(func.count(1).desc())
                .limit(limit).all())

    def daily_metrics(self, days: int = 30) -> List[Tuple[str, int, int]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        date_expr = func.strftime('%Y-%m-%d', CorporateQueryEvent.timestamp)
        return (self.db.query(date_expr.label('d'), func.count(1), func.count(distinct(CorporateQueryEvent.term)))
                .filter(CorporateQueryEvent.timestamp >= cutoff)
                .group_by('d')
                .order_by('d').all())
