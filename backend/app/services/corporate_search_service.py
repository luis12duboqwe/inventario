from uuid import uuid4
from ..repositories.corporate_search_repository import CorporateSearchRepository


class CorporateSearchService:
    def __init__(self, repo: CorporateSearchRepository):
        self.repo = repo

    def start_session(self, user_id: str, channel: str, origin: str):
        session_id = str(uuid4())
        return self.repo.create_session(session_id, user_id, channel, origin)

    def end_session(self, session_id: str):
        return self.repo.end_session(session_id)

    def track_event(self, session_id: str, term: str, normalized_term: str | None, filters: str | None, results_count: int, action: str):
        norm = (normalized_term or term).strip().lower()
        return self.repo.add_event(session_id, term.strip(), norm, filters, results_count, action)

    def list_sessions(self, user_id: str | None, limit: int, offset: int):
        return self.repo.list_sessions(user_id, limit, offset)

    def list_events(self, session_id: str, limit: int, offset: int):
        return self.repo.list_events(session_id, limit, offset)

    def top_terms(self, days: int, limit: int):
        return self.repo.top_terms(days, limit)

    def daily_metrics(self, days: int):
        return self.repo.daily_metrics(days)
