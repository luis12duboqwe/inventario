"""Router para órdenes de reparación técnica."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..models import RepairStatus
from ..routers.dependencies import require_reason
from ..services.repair_documents import render_repair_pdf  # // [PACK37-backend]
from ..security import require_roles

router = APIRouter(prefix="/repairs", tags=["repairs"])


@router.get("/", response_model=list[schemas.RepairOrderResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_repairs_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    branch_id: int | None = Query(default=None, ge=1, alias="branchId"),  # // [PACK37-backend]
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    from_date: datetime | date | None = Query(default=None, alias="from"),  # // [PACK37-backend]
    to_date: datetime | date | None = Query(default=None, alias="to"),  # // [PACK37-backend]
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    status_enum: RepairStatus | None = None
    if status_filter:
        try:
            status_enum = RepairStatus(status_filter.upper())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Estado inválido") from exc
    effective_store_id = store_id or branch_id
    if store_id and branch_id and store_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Los parámetros store_id y branchId deben coincidir.",
        )
    return crud.list_repair_orders(
        db,
        store_id=effective_store_id,
        status=status_enum,
        query=q,
        date_from=from_date,
        date_to=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=schemas.RepairOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def create_repair_order_endpoint(
    payload: schemas.RepairOrderCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.create_repair_order(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "repair_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la reparación.",
            ) from exc
        if detail == "repair_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cantidad inválida de piezas.",
            ) from exc
        if detail == "repair_part_device_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Selecciona un dispositivo válido para las piezas de inventario.",
            ) from exc
        if detail == "repair_part_name_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Describe el repuesto externo antes de registrarlo.",
            ) from exc
        raise


@router.get("/{order_id}", response_model=schemas.RepairOrderResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_repair_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_repair_order(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc


@router.put("/{order_id}", response_model=schemas.RepairOrderResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def update_repair_order_endpoint(
    order_id: int,
    payload: schemas.RepairOrderUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.update_repair_order(
            db,
            order_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "repair_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la reparación.",
            ) from exc
        if detail == "repair_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cantidad inválida de piezas.",
            ) from exc
        if detail == "repair_part_device_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Selecciona un dispositivo válido para las piezas de inventario.",
            ) from exc
        if detail == "repair_part_name_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Describe el repuesto externo antes de registrarlo.",
            ) from exc
        raise


@router.post(  # // [PACK37-backend]
    "/{order_id}/parts",
    response_model=schemas.RepairOrderResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def append_repair_parts_endpoint(
    order_id: int,
    payload: schemas.RepairOrderPartsRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.append_repair_parts(
            db,
            order_id,
            payload.parts,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "repair_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la reparación.",
            ) from exc
        if detail == "repair_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cantidad inválida de piezas.",
            ) from exc
        if detail == "repair_part_device_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Selecciona un dispositivo válido para las piezas de inventario.",
            ) from exc
        if detail == "repair_part_name_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Describe el repuesto externo antes de registrarlo.",
            ) from exc
        raise


@router.delete(  # // [PACK37-backend]
    "/{order_id}/parts/{part_id}",
    response_model=schemas.RepairOrderResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def remove_repair_part_endpoint(
    order_id: int,
    part_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.remove_repair_part(
            db,
            order_id,
            part_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pieza no encontrada") from exc


@router.post(  # // [PACK37-backend]
    "/{order_id}/close",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def close_repair_order_endpoint(
    order_id: int,
    payload: schemas.RepairOrderCloseRequest | None = None,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        order = crud.close_repair_order(
            db,
            order_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "repair_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la reparación.",
            ) from exc
        if detail == "repair_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cantidad inválida de piezas.",
            ) from exc
        if detail == "repair_part_device_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Selecciona un dispositivo válido para las piezas de inventario.",
            ) from exc
        if detail == "repair_part_name_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Describe el repuesto externo antes de registrarlo.",
            ) from exc
        raise

    pdf_bytes = render_repair_pdf(order)
    metadata = schemas.BinaryFileResponse(
        filename=f"orden_reparacion_{order.id}.pdf",
        media_type="application/pdf",
    )
    return Response(
        content=pdf_bytes,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(disposition="inline"),
    )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_repair_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        crud.delete_repair_order(
            db,
            order_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{order_id}/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def download_repair_order_pdf(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        order = crud.get_repair_order(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc

    pdf_bytes = render_repair_pdf(order)  # // [PACK37-backend]
    metadata = schemas.BinaryFileResponse(
        filename=f"orden_reparacion_{order.id}.pdf",
        media_type="application/pdf",
    )
    return Response(
        content=pdf_bytes,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(disposition="inline"),
    )
