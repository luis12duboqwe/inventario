from __future__ import annotations

import csv
from datetime import date, datetime
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, models, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import backups as backup_services
from backend.app.services import inventory_reports
from backend.app.services import sync_conflict_reports
from backend.schemas.common import Page, PageParams

router = APIRouter(prefix="/inventory", tags=["reportes", "inventario"])


def _movement_type(value: str | None) -> models.MovementType | None:
    if not value:
        return None
    try:
        return models.MovementType(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tipo de movimiento inválido",
        ) from exc


def _categories(values: list[str] | None) -> list[str] | None:
    normalized = [value for value in values or [] if value]
    return normalized or None


@router.get("/current", response_model=schemas.InventoryCurrentReport)
def inventory_current(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_inventory_current_report(db, store_ids=store_ids)


@router.get("/current/csv", response_model=schemas.BinaryFileResponse)
def inventory_current_csv(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Existencias actuales"])
    writer.writerow(["Sucursales consideradas", report.totals.stores])
    writer.writerow(["Dispositivos catalogados", report.totals.devices])
    writer.writerow(["Unidades totales", report.totals.total_units])
    writer.writerow(["Valor consolidado (MXN)", f"{report.totals.total_value:.2f}"])
    writer.writerow([])
    writer.writerow(["Sucursal", "Dispositivos", "Unidades", "Valor total (MXN)"])
    for store in report.stores:
        writer.writerow(
            [store.store_name, store.device_count, store.total_units, f"{store.total_value:.2f}"]
        )
    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/current/pdf", response_model=schemas.BinaryFileResponse)
def inventory_current_pdf(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)
    pdf_bytes = inventory_reports.render_inventory_current_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.pdf", media_type="application/pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/current/xlsx", response_model=schemas.BinaryFileResponse)
def inventory_current_excel(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)
    workbook = inventory_reports.build_inventory_current_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/value", response_model=schemas.InventoryValueReport)
def inventory_value(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_inventory_value_report(
        db, store_ids=store_ids, categories=_categories(categories)
    )


@router.get("/value/csv", response_model=schemas.BinaryFileResponse)
def inventory_value_csv(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_value_report(
        db, store_ids=store_ids, categories=_categories(categories)
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Valoración de inventario"])
    writer.writerow(["Sucursales consideradas", len(report.stores)])
    writer.writerow([])
    writer.writerow(
        ["Sucursal", "Valor total (MXN)", "Valor costo (MXN)", "Margen estimado (MXN)"]
    )
    for store in report.stores:
        writer.writerow(
            [
                store.store_name,
                f"{store.valor_total:.2f}",
                f"{store.valor_costo:.2f}",
                f"{store.margen_total:.2f}",
            ]
        )
    writer.writerow([])
    writer.writerow(
        [
            "Totales corporativos",
            f"{report.totals.valor_total:.2f}",
            f"{report.totals.valor_costo:.2f}",
            f"{report.totals.margen_total:.2f}",
        ]
    )
    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/value/pdf", response_model=schemas.BinaryFileResponse)
def inventory_value_pdf(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_value_report(
        db, store_ids=store_ids, categories=_categories(categories)
    )
    pdf_bytes = inventory_reports.render_inventory_value_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.pdf", media_type="application/pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/value/xlsx", response_model=schemas.BinaryFileResponse)
def inventory_value_excel(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_value_report(
        db, store_ids=store_ids, categories=_categories(categories)
    )
    workbook = inventory_reports.build_inventory_value_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inactive-products", response_model=schemas.InactiveProductReport)
def inventory_inactive_products(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    min_days_without_movement: int = Query(default=30, ge=0, le=365),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_inactive_products_report(
        db,
        store_ids=store_ids,
        categories=_categories(categories),
        min_days_without_movement=min_days_without_movement,
        limit=limit,
        offset=offset,
    )


@router.get("/movements", response_model=schemas.InventoryMovementsReport)
def inventory_movements(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=_movement_type(movement_type),
        limit=limit,
        offset=offset,
    )


def _movement_report(
    db: Session,
    store_ids: list[int] | None,
    date_from: datetime | date | None,
    date_to: datetime | date | None,
    movement_type: str | None,
    limit: int | None,
    offset: int,
):
    return crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=_movement_type(movement_type),
        limit=limit,
        offset=offset,
    )


@router.get("/movements/csv", response_model=schemas.BinaryFileResponse)
def inventory_movements_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _movement_report(
        db, store_ids, date_from, date_to, movement_type, limit, offset
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Movimientos de inventario"])
    writer.writerow(["Total registros", report.resumen.total_movimientos])
    writer.writerow(["Total unidades", report.resumen.total_unidades])
    writer.writerow(["Valor total (MXN)", f"{report.resumen.total_valor:.2f}"])
    writer.writerow([])
    writer.writerow(["Detalle de movimientos"])
    writer.writerow(
        [
            "ID", "Fecha", "Tipo", "Cantidad", "Valor (MXN)", "Sucursal destino",
            "Sucursal origen", "Usuario", "Referencia", "Comentario", "Última acción",
        ]
    )
    for movement in report.movimientos:
        reference = "-"
        if movement.referencia_tipo and movement.referencia_id:
            reference = f"{movement.referencia_tipo}:{movement.referencia_id}"
        elif movement.referencia_id:
            reference = movement.referencia_id
        elif movement.referencia_tipo:
            reference = movement.referencia_tipo
        last_action = "-"
        if movement.ultima_accion:
            actor = movement.ultima_accion.usuario or "-"
            stamp = movement.ultima_accion.timestamp.strftime("%d/%m/%Y %H:%M")
            last_action = f"{movement.ultima_accion.accion} · {actor} · {stamp}"
        writer.writerow(
            [
                movement.id,
                movement.fecha.isoformat(),
                movement.tipo_movimiento.value,
                movement.cantidad,
                f"{movement.valor_total:.2f}",
                movement.sucursal_destino or "-",
                movement.sucursal_origen or "-",
                movement.usuario or "-",
                reference,
                movement.comentario or "-",
                last_action,
            ]
        )
    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/movements/pdf", response_model=schemas.BinaryFileResponse)
def inventory_movements_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _movement_report(
        db, store_ids, date_from, date_to, movement_type, limit, offset
    )
    pdf_bytes = inventory_reports.render_inventory_movements_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.pdf", media_type="application/pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/movements/xlsx", response_model=schemas.BinaryFileResponse)
def inventory_movements_excel(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _movement_report(
        db, store_ids, date_from, date_to, movement_type, limit, offset
    )
    workbook = inventory_reports.build_inventory_movements_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/sync-discrepancies", response_model=schemas.SyncDiscrepancyReport)
def inventory_sync_discrepancies(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    min_difference: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_sync_discrepancies_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        min_difference=min_difference,
        limit=limit,
        offset=offset,
    )


@router.get("/sync-discrepancies/xlsx", response_model=schemas.BinaryFileResponse)
def inventory_sync_discrepancies_excel(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    min_difference: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_sync_discrepancies_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        min_difference=min_difference,
        limit=limit,
        offset=offset,
    )
    workbook_bytes = sync_conflict_reports.render_conflict_report_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_discrepancias_sync.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/top-products", response_model=schemas.TopProductsReport)
def inventory_top_products(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


def _top_products_report(
    db: Session,
    store_ids: list[int] | None,
    date_from: datetime | date | None,
    date_to: datetime | date | None,
    limit: int,
    offset: int,
):
    return crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/top-products/csv", response_model=schemas.BinaryFileResponse)
def inventory_top_products_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _top_products_report(db, store_ids, date_from, date_to, limit, offset)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Productos más vendidos"])
    writer.writerow(["Total unidades", report.total_unidades])
    writer.writerow(["Ingresos totales (MXN)", f"{report.total_ingresos:.2f}"])
    writer.writerow([])
    writer.writerow(
        ["SKU", "Producto", "Sucursal", "Unidades vendidas", "Ingresos (MXN)", "Margen estimado (MXN)"]
    )
    for item in report.items:
        writer.writerow(
            [
                item.sku,
                item.nombre,
                item.store_name,
                item.unidades_vendidas,
                f"{item.ingresos_totales:.2f}",
                f"{item.margen_estimado:.2f}",
            ]
        )
    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/top-products/pdf", response_model=schemas.BinaryFileResponse)
def inventory_top_products_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _top_products_report(db, store_ids, date_from, date_to, limit, offset)
    pdf_bytes = inventory_reports.render_top_products_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.pdf", media_type="application/pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/top-products/xlsx", response_model=schemas.BinaryFileResponse)
def inventory_top_products_excel(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = _top_products_report(db, store_ids, date_from, date_to, limit, offset)
    workbook = inventory_reports.build_top_products_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/pdf", response_model=schemas.BinaryFileResponse)
def inventory_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    pdf_bytes = backup_services.render_snapshot_pdf(snapshot)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_inventario.pdf", media_type="application/pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/csv", response_model=schemas.BinaryFileResponse)
def inventory_csv(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Inventario corporativo"])
    writer.writerow(["Generado", datetime.utcnow().isoformat()])
    consolidated_total = 0.0

    for store in snapshot.get("stores", []):
        writer.writerow([])
        writer.writerow(
            [f"Sucursal: {store['name']}", store.get("location", "-"), store.get("timezone", "UTC")]
        )
        writer.writerow(
            [
                "SKU", "Nombre", "Cantidad", "Precio unitario", "Valor total", "IMEI", "Serie",
                "Marca", "Modelo", "Proveedor", "Color", "Capacidad (GB)", "Estado", "Lote",
                "Fecha compra", "Garantía (meses)", "Costo unitario", "Margen (%)",
            ]
        )
        store_total = 0.0
        for device in store.get("devices", []):
            try:
                inventory_value = float(device.get("inventory_value", 0) or 0)
            except (TypeError, ValueError):
                inventory_value = 0.0
            try:
                unit_price = float(device.get("unit_price", 0) or 0)
            except (TypeError, ValueError):
                unit_price = 0.0
            try:
                unit_cost = float(device.get("costo_unitario", 0) or 0)
            except (TypeError, ValueError):
                unit_cost = 0.0
            try:
                margin = float(device.get("margen_porcentaje", 0) or 0)
            except (TypeError, ValueError):
                margin = 0.0
            store_total += inventory_value
            writer.writerow(
                [
                    device.get("sku"), device.get("name"), device.get("quantity"), f"{unit_price:.2f}",
                    f"{inventory_value:.2f}", device.get("imei") or "-", device.get("serial") or "-",
                    device.get("marca") or "-", device.get("modelo") or "-", device.get("proveedor") or "-",
                    device.get("color") or "-",
                    device.get("capacidad_gb") if device.get("capacidad_gb") is not None else "-",
                    device.get("estado_comercial", "-"), device.get("lote") or "-",
                    device.get("fecha_compra") or "-",
                    device.get("garantia_meses") if device.get("garantia_meses") is not None else "-",
                    f"{unit_cost:.2f}", f"{margin:.2f}",
                ]
            )
        try:
            registered_value = float(store.get("inventory_value", store_total) or 0)
        except (TypeError, ValueError):
            registered_value = store_total
        padding = [""] * 13
        writer.writerow(["TOTAL SUCURSAL", "", "", "", f"{store_total:.2f}", *padding])
        writer.writerow(["VALOR CONTABLE", "", "", "", f"{registered_value:.2f}", *padding])
        consolidated_total += store_total

    summary = snapshot.get("summary") or {}
    if summary:
        writer.writerow([])
        writer.writerow(["Resumen corporativo"])
        writer.writerow(["Sucursales auditadas", summary.get("store_count", 0)])
        writer.writerow(["Dispositivos catalogados", summary.get("device_records", 0)])
        writer.writerow(["Unidades totales", summary.get("total_units", 0)])
        try:
            summary_value = float(summary.get("inventory_value", 0) or 0)
        except (TypeError, ValueError):
            summary_value = 0.0
        writer.writerow(["Inventario consolidado registrado (MXN)", f"{summary_value:.2f}"])
        writer.writerow(["Inventario consolidado calculado (MXN)", f"{consolidated_total:.2f}"])

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_inventario.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/supplier-batches", response_model=Page[schemas.SupplierBatchOverviewItem])
def inventory_supplier_batches(
    store_id: int = Query(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.SupplierBatchOverviewItem]:
    page_offset = pagination.offset if pagination.page > 1 and offset == 0 else offset
    page_size = min(pagination.size, limit)
    total = crud.count_supplier_batch_overview(db, store_id=store_id)
    items = crud.get_supplier_batch_overview(
        db, store_id=store_id, limit=page_size, offset=page_offset
    )
    return Page.from_items(
        items, page=pagination.page, size=page_size, total=total
    )
