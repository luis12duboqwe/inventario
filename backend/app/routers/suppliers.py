"""Router de proveedores estratégicos."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("/", response_model=list[schemas.SupplierResponse])
def list_suppliers_endpoint(
    q: str | None = Query(default=None, description="Término de búsqueda"),
    limit: int = Query(default=100, ge=1, le=500),
    export: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    suppliers = crud.list_suppliers(db, query=q, limit=limit)
    if export == "csv":
        csv_content = crud.export_suppliers_csv(db, query=q)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=proveedores.csv"},
        )
    return suppliers


@router.post("/", response_model=schemas.SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_endpoint(
    payload: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        supplier = crud.create_supplier(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        if str(exc) == "supplier_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El proveedor ya existe.",
            ) from exc
        raise
    return supplier


@router.get("/{supplier_id}", response_model=schemas.SupplierResponse)
def get_supplier_endpoint(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_supplier(db, supplier_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc


@router.put("/{supplier_id}", response_model=schemas.SupplierResponse)
def update_supplier_endpoint(
    supplier_id: int,
    payload: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.update_supplier(
            db,
            supplier_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_endpoint(
    supplier_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        crud.delete_supplier(
            db,
            supplier_id,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
