"""Endpoints para la gestión de órdenes de compra."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import purchase_reports
from backend.schemas.common import Page, PageParams

router = APIRouter(prefix="/purchases", tags=["compras"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


def _prepare_purchase_report(
    db: Session,
    *,
    proveedor_id: int | None,
    usuario_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    estado: str | None,
    query: str | None,
) -> schemas.PurchaseReport:
    filters = schemas.PurchaseReportFilters(
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    purchases = crud.list_purchase_records_for_report(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    return purchase_reports.build_purchase_report(purchases, filters)


@router.get(
    "/suggestions",
    response_model=schemas.PurchaseSuggestionsResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_purchase_suggestions_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    lookback_days: int = Query(default=30, ge=7, le=90),
    planning_horizon_days: int = Query(default=14, ge=7, le=60),
    minimum_stock: int | None = Query(default=None, ge=0, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PurchaseSuggestionsResponse:
    _ensure_feature_enabled()
    store_ids = [store_id] if store_id else None
    return crud.compute_purchase_suggestions(
        db,
        store_ids=store_ids,
        lookback_days=lookback_days,
        minimum_stock=minimum_stock,
        planning_horizon_days=planning_horizon_days,
    )


@router.get("/vendors", response_model=Page[schemas.PurchaseVendorResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_purchase_vendors_endpoint(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    estado: str | None = Query(default=None, min_length=3, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.PurchaseVendorResponse]:
    _ensure_feature_enabled()
    query = q.strip() if q else None
    estado_value = estado.strip() if estado else None
    page_offset = pagination.offset if (pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_purchase_vendors(
        db,
        query=query,
        estado=estado_value,
    )
    vendors = crud.list_purchase_vendors(
        db,
        vendor_id=None,
        query=query,
        estado=estado_value,
        limit=page_size,
        offset=page_offset,
    )
    return Page.from_items(vendors, page=pagination.page, size=page_size, total=total)


@router.post(
    "/suggestions/orders",
    response_model=schemas.PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_order_from_suggestion_endpoint(
    payload: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_purchase_order_from_suggestion(
            db,
            payload,
            created_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes incluir artículos en la orden.",
            ) from exc
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la orden.",
            ) from exc
        raise


@router.post("/vendors", response_model=schemas.PurchaseVendorResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def create_purchase_vendor_endpoint(
    payload: schemas.PurchaseVendorCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        vendor = crud.create_purchase_vendor(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        if str(exc) == "purchase_vendor_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El proveedor ya existe.",
            ) from exc
        raise

    summary = crud.list_purchase_vendors(db, vendor_id=vendor.id_proveedor, limit=1)
    if summary:
        return summary[0]
    return schemas.PurchaseVendorResponse(
        id_proveedor=vendor.id_proveedor,
        nombre=vendor.nombre,
        telefono=vendor.telefono,
        correo=vendor.correo,
        direccion=vendor.direccion,
        tipo=vendor.tipo,
        notas=vendor.notas,
        estado=vendor.estado,
        total_compras=Decimal("0"),
        total_impuesto=Decimal("0"),
        compras_registradas=0,
        ultima_compra=None,
    )


@router.put("/vendors/{vendor_id}", response_model=schemas.PurchaseVendorResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def update_purchase_vendor_endpoint(
    vendor_id: int,
    payload: schemas.PurchaseVendorUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        crud.update_purchase_vendor(
            db,
            vendor_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc

    summary = crud.list_purchase_vendors(db, vendor_id=vendor_id, limit=1)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return summary[0]


@router.post("/vendors/{vendor_id}/status", response_model=schemas.PurchaseVendorResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def update_purchase_vendor_status_endpoint(
    vendor_id: int,
    payload: schemas.PurchaseVendorStatusUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        crud.set_purchase_vendor_status(
            db,
            vendor_id,
            payload.estado,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc

    summary = crud.list_purchase_vendors(db, vendor_id=vendor_id, limit=1)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return summary[0]


@router.get("/vendors/export/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def export_purchase_vendors_csv_endpoint(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    estado: str | None = Query(default=None, min_length=3, max_length=40),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    query = q.strip() if q else None
    estado_value = estado.strip() if estado else None
    csv_content = crud.export_purchase_vendors_csv(
        db,
        query=query,
        estado=estado_value,
    )
    metadata = schemas.BinaryFileResponse(
        filename=f"proveedores_compras_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
        media_type="text/csv",
    )
    response = Response(
        content=csv_content.encode("utf-8"),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )
    response.headers["Content-Type"] = metadata.media_type
    return response


@router.get("/vendors/{vendor_id}/history", response_model=schemas.PurchaseVendorHistory, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def purchase_vendor_history_endpoint(
    vendor_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.list_vendor_purchase_history(
            db,
            vendor_id,
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc


@router.get("/records", response_model=Page[schemas.PurchaseRecordResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_purchase_records_endpoint(
    proveedor_id: int | None = Query(default=None, ge=1),
    usuario_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    estado: str | None = Query(default=None, min_length=3, max_length=40),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.PurchaseRecordResponse]:
    _ensure_feature_enabled()
    query = q.strip() if q else None
    estado_value = estado.strip() if estado else None
    page_offset = pagination.offset if (pagination.page > 1 and offset == 0) else offset
    page_limit = min(pagination.size, limit)
    total = crud.count_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado_value,
        query=query,
    )
    records = crud.list_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado_value,
        query=query,
        limit=page_limit,
        offset=page_offset,
    )
    return Page.from_items(records, page=pagination.page, size=page_limit, total=total)


@router.post("/records", response_model=schemas.PurchaseRecordResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def create_purchase_record_endpoint(
    payload: schemas.PurchaseRecordCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_purchase_record(
            db,
            payload,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        detail = str(exc)
        if detail == "purchase_vendor_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado") from exc
        if detail == "device_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado") from exc
        raise
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_record_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes agregar productos a la compra.",
            ) from exc
        if detail == "purchase_record_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la compra.",
            ) from exc
        if detail == "purchase_record_invalid_cost":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Costo unitario inválido.",
            ) from exc
        raise


@router.get("/records/export/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def export_purchase_records_pdf_endpoint(
    proveedor_id: int | None = Query(default=None, ge=1),
    usuario_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    estado: str | None = Query(default=None, min_length=3, max_length=40),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    query = q.strip() if q else None
    estado_value = estado.strip() if estado else None
    report = _prepare_purchase_report(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado_value,
        query=query,
    )
    pdf_bytes = purchase_reports.render_purchase_report_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"compras_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/records/export/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def export_purchase_records_excel_endpoint(
    proveedor_id: int | None = Query(default=None, ge=1),
    usuario_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    estado: str | None = Query(default=None, min_length=3, max_length=40),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    query = q.strip() if q else None
    estado_value = estado.strip() if estado else None
    report = _prepare_purchase_report(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado_value,
        query=query,
    )
    excel_bytes = purchase_reports.render_purchase_report_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"compras_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/statistics", response_model=schemas.PurchaseStatistics, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_purchase_statistics_endpoint(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    top_limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    return crud.get_purchase_statistics(
        db,
        date_from=date_from,
        date_to=date_to,
        top_limit=top_limit,
    )


@router.get("/", response_model=Page[schemas.PurchaseOrderResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_purchase_orders_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store_id: int | None = Query(default=None, ge=1),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.PurchaseOrderResponse]:
    _ensure_feature_enabled()
    page_offset = pagination.offset if (pagination.page > 1 and offset == 0) else offset
    page_limit = min(pagination.size, limit)
    total = crud.count_purchase_orders(db, store_id=store_id)
    orders = crud.list_purchase_orders(
        db,
        store_id=store_id,
        limit=page_limit,
        offset=page_offset,
    )
    return Page.from_items(orders, page=pagination.page, size=page_limit, total=total)


@router.get(
    "/{order_id}",
    response_model=schemas.PurchaseOrderResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_purchase_order_endpoint(
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.get_purchase_order(db, order_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        ) from exc


@router.post("/", response_model=schemas.PurchaseOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def create_purchase_order_endpoint(
    payload: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_purchase_order(db, payload, created_by_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes incluir artículos en la orden.",
            ) from exc
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la orden.",
            ) from exc
        raise


@router.post(
    "/import",
    response_model=schemas.PurchaseImportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
async def import_purchase_orders_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        raw_content = await file.read()
        csv_content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible interpretar el archivo CSV proporcionado.",
        ) from exc

    try:
        orders, errors = crud.import_purchase_orders_from_csv(
            db,
            csv_content,
            created_by_id=current_user.id,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    response_orders = [
        schemas.PurchaseOrderResponse.model_validate(order, from_attributes=True)
        for order in orders
    ]
    return schemas.PurchaseImportResponse(
        imported=len(response_orders),
        orders=response_orders,
        errors=errors,
    )


@router.post("/{order_id}/receive", response_model=schemas.PurchaseOrderResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def receive_purchase_order_endpoint(
    payload: schemas.PurchaseReceiveRequest,
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.receive_purchase_order(
            db,
            order_id,
            payload,
            received_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_not_receivable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no puede recibir más artículos.",
            ) from exc
        if detail == "purchase_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar artículos a recibir.",
            ) from exc
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cantidad a recibir inválida.",
            ) from exc
        if detail == "supplier_batch_code_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Indica un código de lote válido para la recepción.",
            ) from exc
        raise


@router.post("/{order_id}/cancel", response_model=schemas.PurchaseOrderResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def cancel_purchase_order_endpoint(
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.cancel_purchase_order(
            db,
            order_id,
            cancelled_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "purchase_not_cancellable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya fue cerrada.",
            ) from exc
        raise


@router.post("/{order_id}/returns", response_model=schemas.PurchaseReturnResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def register_purchase_return_endpoint(
    payload: schemas.PurchaseReturnCreate,
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.register_purchase_return(
            db,
            order_id,
            payload,
            processed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden o artículo no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida.",
            ) from exc
        if detail == "purchase_return_exceeds_received":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes devolver más de lo recibido.",
            ) from exc
        if detail == "purchase_return_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para devolver.",
            ) from exc
        raise
