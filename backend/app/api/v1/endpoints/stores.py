"""Endpoints for store management."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .... import schemas
from ....core.roles import GESTION_ROLES
from ....models.store import Store as StoreModel
from ....security import require_roles
from ....services.inventory import create_store, list_stores
from ...deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Store], summary="Listar sucursales")
def get_stores(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.Store]:
    """Return every registered store."""

    return list_stores(db, limit=limit, offset=offset)


@router.post(
    "/",
    response_model=schemas.Store,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sucursal",
)
def add_store(
    store_in: schemas.StoreCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.Store:
    """Create a new store ensuring uniqueness by name."""

    existing = db.query(StoreModel).filter(StoreModel.name == store_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una sucursal con ese nombre.",
        )
    return create_store(db, store_in)
