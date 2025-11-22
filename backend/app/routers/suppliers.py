"""Router de proveedores estratégicos."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _is_superadmin(user: Any, confirmation: bool) -> bool:
    return confirmation and str(getattr(user, "rol", "")).upper() == ADMIN


@router.get("/", response_model=list[schemas.SupplierResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_suppliers_endpoint(
    q: str | None = Query(default=None, description="Término de búsqueda"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    export: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    suppliers = crud.list_suppliers(db, query=q, limit=limit, offset=offset)
    if export == "csv":
        csv_content = crud.export_suppliers_csv(db, query=q)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=proveedores.csv"},
        )
    return suppliers


@router.get(
    "/accounts-payable",
    response_model=schemas.SupplierAccountsPayableResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_suppliers_accounts_payable_endpoint(
    db: Session = Depends(get_db),
):
    return crud.get_suppliers_accounts_payable(db)


@router.post("/", response_model=schemas.SupplierResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
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
        if str(exc) == "supplier_rtn_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El RTN del proveedor debe contener 14 dígitos (formato ####-####-######).",
            ) from exc
        if str(exc) == "supplier_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El proveedor ya existe.",
            ) from exc
        raise
    return supplier


@router.get("/{supplier_id}", response_model=schemas.SupplierResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_supplier_endpoint(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_supplier(db, supplier_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc
    except ValueError as exc:
        if str(exc) == "supplier_rtn_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El RTN del proveedor debe contener 14 dígitos (formato ####-####-######).",
            ) from exc
        raise


@router.put("/{supplier_id}", response_model=schemas.SupplierResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
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


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_supplier_endpoint(
    supplier_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    hard_delete: bool = Query(
        default=False,
        description="Eliminación definitiva solo para superadministradores",
    ),
    superadmin_confirmed: bool = Query(
        default=False,
        description="Confirma que un superadministrador autorizó la eliminación",
    ),
):
    try:
        crud.delete_supplier(
            db,
            supplier_id,
            performed_by_id=current_user.id if current_user else None,
            allow_hard_delete=hard_delete,
            is_superadmin=_is_superadmin(current_user, superadmin_confirmed),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{supplier_id}/batches",
    response_model=list[schemas.SupplierBatchResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_supplier_batches_endpoint(
    supplier_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.list_supplier_batches(
            db, supplier_id, limit=limit, offset=offset
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc


@router.post(
    "/{supplier_id}/batches",
    response_model=schemas.SupplierBatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_supplier_batch_endpoint(
    supplier_id: int,
    payload: schemas.SupplierBatchCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.create_supplier_batch(
            db,
            supplier_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        detail = str(exc)
        if detail == "device_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado") from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc
    except ValueError as exc:
        if str(exc) == "supplier_batch_store_mismatch":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El dispositivo no pertenece a la sucursal indicada.",
            ) from exc
        raise


@router.put(
    "/batches/{batch_id}",
    response_model=schemas.SupplierBatchResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_supplier_batch_endpoint(
    batch_id: int,
    payload: schemas.SupplierBatchUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.update_supplier_batch(
            db,
            batch_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado") from exc


@router.delete(
    "/batches/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_supplier_batch_endpoint(
    batch_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        crud.delete_supplier_batch(
            db,
            batch_id,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
