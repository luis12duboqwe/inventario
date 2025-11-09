"""Endpoints para ventas y devoluciones."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import audit_logger, sales_reports

router = APIRouter(prefix="/sales", tags=["ventas"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


def _prepare_sales_report(
    db: Session,
    *,
    store_id: int | None,
    customer_id: int | None,
    performed_by_id: int | None,
    product_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    query: str | None,
) -> schemas.SalesReport:
    filters = schemas.SalesReportFilters(
        store_id=store_id,
        customer_id=customer_id,
        performed_by_id=performed_by_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        query=query,
    )
    sales = crud.list_sales(
        db,
        store_id=store_id,
        limit=None,
        offset=0,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        performed_by_id=performed_by_id,
        product_id=product_id,
        query=query,
    )
    audit_trails = audit_logger.get_last_audit_trails(
        db,
        entity_type="sale",
        entity_ids=[sale.id for sale in sales if sale.id is not None],
    )
    return sales_reports.build_sales_report(
        sales,
        filters,
        audit_trails=audit_trails,
    )


@router.get(
    "/",
    response_model=list[schemas.SaleResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_sales_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    performed_by_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    search = q.strip() if q else None
    return crud.list_sales(
        db,
        store_id=store_id,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        performed_by_id=performed_by_id,
        product_id=product_id,
        query=search,
    )


@router.get(
    "/export/pdf",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def export_sales_pdf(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    performed_by_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    search = q.strip() if q else None
    report = _prepare_sales_report(
        db,
        store_id=store_id,
        customer_id=customer_id,
        performed_by_id=performed_by_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        query=search,
    )
    pdf_bytes = sales_reports.render_sales_report_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"ventas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get(
    "/export/xlsx",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def export_sales_excel(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    performed_by_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    search = q.strip() if q else None
    report = _prepare_sales_report(
        db,
        store_id=store_id,
        customer_id=customer_id,
        performed_by_id=performed_by_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        query=search,
    )
    excel_bytes = sales_reports.render_sales_report_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"ventas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.post(
    "/",
    response_model=schemas.SaleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def create_sale_endpoint(
    payload: schemas.SaleCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        with transactional_session(db):
            sale = crud.create_sale(
                db,
                payload,
                performed_by_id=current_user.id,
                reason=reason,
            )
        return sale
    except LookupError as exc:
        if str(exc) == "supplier_batch_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El lote indicado no existe o no coincide con el producto.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes agregar artículos a la venta.",
            ) from exc
        if detail == "sale_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la venta.",
            ) from exc
        if detail == "sale_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la venta.",
            ) from exc
        if detail == "sale_device_already_sold":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya fue vendido y no está disponible.",
            ) from exc
        if detail == "supplier_batch_code_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar un lote válido para cada artículo.",
            ) from exc
        if detail == "supplier_batch_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El lote seleccionado no cuenta con unidades suficientes.",
            ) from exc
        if detail == "sale_requires_single_unit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los dispositivos con IMEI o serie se venden por unidad.",
            ) from exc
        if detail == "customer_credit_limit_exceeded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente excede el límite de crédito disponible.",
            ) from exc
        raise


@router.post(
    "/returns",
    response_model=list[schemas.SaleReturnResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def register_sale_return_endpoint(
    payload: schemas.SaleReturnCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        with transactional_session(db):
            sale_returns = crud.register_sale_return(
                db,
                payload,
                processed_by_id=current_user.id,
                reason=reason,
            )
        return sale_returns
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta o artículo no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_return_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar artículos a devolver.",
            ) from exc
        if detail == "sale_return_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cantidad de devolución inválida.",
            ) from exc
        if detail == "sale_return_invalid_warehouse":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selecciona un almacén válido para la devolución.",
            ) from exc
        raise


@router.put(
    "/{sale_id}",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def update_sale_endpoint(
    payload: schemas.SaleUpdate,
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        with transactional_session(db):
            sale = crud.update_sale(
                db,
                sale_id,
                payload,
                performed_by_id=current_user.id,
                reason=reason,
            )
        return sale
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes agregar artículos a la venta.",
            ) from exc
        if detail == "sale_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la venta.",
            ) from exc
        if detail == "sale_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la venta.",
            ) from exc
        if detail == "sale_device_already_sold":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya fue vendido y no está disponible.",
            ) from exc
        if detail == "sale_requires_single_unit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los dispositivos con IMEI o serie se venden por unidad.",
            ) from exc
        if detail == "sale_has_returns":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes editar una venta con devoluciones registradas.",
            ) from exc
        if detail == "sale_already_cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La venta ya se encuentra anulada.",
            ) from exc
        if detail == "customer_credit_limit_exceeded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente excede el límite de crédito disponible.",
            ) from exc
        raise


@router.post(
    "/{sale_id}/cancel",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def cancel_sale_endpoint(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        with transactional_session(db):
            sale = crud.cancel_sale(
                db,
                sale_id,
                performed_by_id=current_user.id,
                reason=reason,
            )
        return sale
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "sale_already_cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La venta ya se encuentra anulada.",
            ) from exc
        raise
