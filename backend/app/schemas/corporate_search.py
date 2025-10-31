from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CorporateSearchSessionCreate(BaseModel):
    user_id: str = Field(..., max_length=64)
    channel: str = Field('web', max_length=20)
    origin: str = Field('inventory', max_length=20)


class CorporateSearchSessionRead(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    channel: str
    origin: str

    class Config:
        from_attributes = True


class CorporateQueryEventCreate(BaseModel):
    term: str = Field(..., max_length=120)
    normalized_term: Optional[str] = None
    filters: Optional[str] = None
    results_count: int = 0
    action: str = 'search'


class CorporateQueryEventRead(BaseModel):
    id: int
    session_id: str
    timestamp: datetime
    term: str
    normalized_term: str
    filters: Optional[str]
    results_count: int
    action: str

    class Config:
        from_attributes = True


class TopTerm(BaseModel):
    term: str
    hits: int


class DailyMetric(BaseModel):
    date: str
    queries: int
    unique_terms: int
