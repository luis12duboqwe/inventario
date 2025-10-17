"""Endpoints for store management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .... import schemas
from ....models import Store as StoreModel
from ....services.inventory import create_store, list_stores
from ...deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Store], summary="Listar sucursales")
def get_stores(db: Session = Depends(get_db)) -> list[schemas.Store]:
    """Return every registered store."""

    return list_stores(db)


@router.post(
    "/",
    response_model=schemas.Store,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sucursal",
)
def add_store(store_in: schemas.StoreCreate, db: Session = Depends(get_db)) -> schemas.Store:
    """Create a new store ensuring uniqueness by name."""

    existing = db.query(StoreModel).filter(StoreModel.name == store_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una sucursal con ese nombre.",
        )
    return create_store(db, store_in)
