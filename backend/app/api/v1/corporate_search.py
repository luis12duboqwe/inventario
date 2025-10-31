from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from ..deps import get_db
from ...repositories.corporate_search_repository import CorporateSearchRepository
from ...services.corporate_search_service import CorporateSearchService
from ...schemas.corporate_search import (CorporateSearchSessionCreate, CorporateSearchSessionRead, CorporateQueryEventCreate, CorporateQueryEventRead)

router = APIRouter(prefix='/corporate/search', tags=['corporate_search'])


# Basic header guard (X-Reason is mandatory)
async def guard_x_reason(x_reason: str | None = Header(default=None)):
    if not x_reason:
        raise HTTPException(status_code=400, detail='Missing X-Reason header')


@router.post('/sessions', response_model=CorporateSearchSessionRead, dependencies=[Depends(guard_x_reason)])
async def start_session(payload: CorporateSearchSessionCreate, db: Session = Depends(get_db)):
    service = CorporateSearchService(CorporateSearchRepository(db))
    return service.start_session(payload.user_id, payload.channel, payload.origin)


@router.post('/sessions/{session_id}/end', response_model=CorporateSearchSessionRead, dependencies=[Depends(guard_x_reason)])
async def end_session(session_id: str, db: Session = Depends(get_db)):
    service = CorporateSearchService(CorporateSearchRepository(db))
    return service.end_session(session_id)


@router.post('/sessions/{session_id}/events', response_model=CorporateQueryEventRead, dependencies=[Depends(guard_x_reason)])
async def add_event(session_id: str, payload: CorporateQueryEventCreate, db: Session = Depends(get_db)):
    service = CorporateSearchService(CorporateSearchRepository(db))
    return service.track_event(session_id, payload.term, payload.normalized_term, payload.filters, payload.results_count, payload.action)


@router.get('/sessions', response_model=list[CorporateSearchSessionRead], dependencies=[Depends(guard_x_reason)])
async def list_sessions(user_id: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    service = CorporateSearchService(CorporateSearchRepository(db))
    return service.list_sessions(user_id, limit, offset)


@router.get('/sessions/{session_id}/events', response_model=list[CorporateQueryEventRead], dependencies=[Depends(guard_x_reason)])
async def list_events(session_id: str, limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    service = CorporateSearchService(CorporateSearchRepository(db))
    return service.list_events(session_id, limit, offset)
