"""Reportes consolidados y bitácoras."""
from __future__ import annotations

import csv
from datetime import date, datetime
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import AUDITORIA_ROLES, REPORTE_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import analytics as analytics_service
from ..services import audit as audit_service
from ..services import backups as backup_services
from ..utils import audit as audit_utils

router = APIRouter(prefix="/reports", tags=["reportes"])


def _ensure_analytics_enabled() -> None:
    if not settings.enable_analytics_adv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    return crud.list_audit_logs(
        db,
        limit=limit,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/audit/pdf")
def audit_logs_pdf(
    limit: int = Query(default=200, ge=1, le=1000),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
    _reason: str = Depends(require_reason),
):
    logs = crud.list_audit_logs(
        db,
        limit=limit,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    summary = audit_utils.summarize_alerts(logs)
    filters: dict[str, str] = {}
    if action:
        filters["Acción"] = action
    if entity_type:
        filters["Tipo de entidad"] = entity_type
    if performed_by_id is not None:
        filters["Usuario"] = str(performed_by_id)
    if date_from:
        filters["Desde"] = str(date_from)
    if date_to:
        filters["Hasta"] = str(date_to)
    pdf_bytes = audit_service.render_audit_pdf(logs, filters=filters, alerts=summary)
    buffer = BytesIO(pdf_bytes)
    headers = {"Content-Disposition": "attachment; filename=auditoria_softmobile.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@router.get("/analytics/rotation", response_model=schemas.AnalyticsRotationResponse)
def analytics_rotation(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsRotationResponse(items=[schemas.RotationMetric(**item) for item in data])


@router.get("/analytics/aging", response_model=schemas.AnalyticsAgingResponse)
def analytics_aging(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsAgingResponse(items=[schemas.AgingMetric(**item) for item in data])


@router.get("/analytics/stockout_forecast", response_model=schemas.AnalyticsForecastResponse)
def analytics_forecast(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsForecastResponse(items=[schemas.StockoutForecastMetric(**item) for item in data])


@router.get("/analytics/comparative", response_model=schemas.AnalyticsComparativeResponse)
def analytics_comparative(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsComparativeResponse(
        items=[schemas.StoreComparativeMetric(**item) for item in data]
    )


@router.get("/analytics/profit_margin", response_model=schemas.AnalyticsProfitMarginResponse)
def analytics_profit_margin(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsProfitMarginResponse(
        items=[schemas.ProfitMarginMetric(**item) for item in data]
    )


@router.get("/analytics/sales_forecast", response_model=schemas.AnalyticsSalesProjectionResponse)
def analytics_sales_projection(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsSalesProjectionResponse(
        items=[schemas.SalesProjectionMetric(**item) for item in data]
    )


@router.get("/analytics/categories", response_model=schemas.AnalyticsCategoriesResponse)
def analytics_categories(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    categories = crud.list_analytics_categories(db)
    return schemas.AnalyticsCategoriesResponse(categories=categories)


@router.get("/analytics/alerts", response_model=schemas.AnalyticsAlertsResponse)
def analytics_alerts(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.generate_analytics_alerts(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsAlertsResponse(
        items=[schemas.AnalyticsAlert(**item) for item in data]
    )


@router.get("/analytics/realtime", response_model=schemas.AnalyticsRealtimeResponse)
def analytics_realtime(
    store_ids: list[int] | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_realtime_store_widget(
        db,
        store_ids=store_ids,
        category=category,
    )
    return schemas.AnalyticsRealtimeResponse(
        items=[schemas.StoreRealtimeWidget(**item) for item in data]
    )


@router.get("/analytics/pdf")
def analytics_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    _ensure_analytics_enabled()
    rotation = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    aging = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    forecast = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    comparatives = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    profit = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    projection = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    pdf_bytes = analytics_service.render_analytics_pdf(
        rotation=rotation,
        aging=aging,
        forecast=forecast,
        comparatives=comparatives,
        profit=profit,
        projection=projection,
    )
    buffer = BytesIO(pdf_bytes)
    headers = {"Content-Disposition": "attachment; filename=softmobile_analytics.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@router.get("/analytics/export.csv")
def analytics_export_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    _ensure_analytics_enabled()
    comparatives = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    profit = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    projection = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Comparativo sucursales"])
    writer.writerow([
        "Sucursal",
        "Dispositivos",
        "Unidades",
        "Valor inventario",
        "Rotación promedio",
        "Envejecimiento promedio",
        "Ventas 30d",
        "Órdenes 30d",
    ])
    for item in comparatives:
        writer.writerow(
            [
                item["store_name"],
                item["device_count"],
                item["total_units"],
                f"{item['inventory_value']:.2f}",
                f"{item['average_rotation']:.2f}",
                f"{item['average_aging_days']:.2f}",
                f"{item['sales_last_30_days']:.2f}",
                item["sales_count_last_30_days"],
            ]
        )

    writer.writerow([])
    writer.writerow(["Margen por sucursal"])
    writer.writerow(["Sucursal", "Ingresos", "Costo", "Utilidad", "% Margen"])
    for item in profit:
        writer.writerow(
            [
                item["store_name"],
                f"{item['revenue']:.2f}",
                f"{item['cost']:.2f}",
                f"{item['profit']:.2f}",
                f"{item['margin_percent']:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Proyección ventas 30 días"])
    writer.writerow([
        "Sucursal",
        "Unidades diarias",
        "Ticket promedio",
        "Unidades proyectadas",
        "Ingresos proyectados",
        "Confianza",
    ])
    for item in projection:
        writer.writerow(
            [
                item["store_name"],
                f"{item['average_daily_units']:.2f}",
                f"{item['average_ticket']:.2f}",
                f"{item['projected_units']:.2f}",
                f"{item['projected_revenue']:.2f}",
                f"{item['confidence']:.2f}",
            ]
        )

    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=softmobile_analytics.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/inventory/current", response_model=schemas.InventoryCurrentReport)
def inventory_current(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.get_inventory_current_report(db, store_ids=store_ids)


@router.get("/inventory/value", response_model=schemas.InventoryValueReport)
def inventory_value(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    normalized_categories = [category for category in categories or [] if category]
    return crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )


@router.get(
    "/inventory/movements",
    response_model=schemas.InventoryMovementsReport,
)
def inventory_movements(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc
    return crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )


@router.get(
    "/inventory/top-products",
    response_model=schemas.TopProductsReport,
)
def inventory_top_products(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/inventory/pdf")
def inventory_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    pdf_bytes = backup_services.render_snapshot_pdf(snapshot)
    buffer = BytesIO(pdf_bytes)
    headers = {
        "Content-Disposition": "attachment; filename=softmobile_inventario.pdf",
    }
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@router.get("/inventory/csv")
def inventory_csv(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
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
        writer.writerow([f"Sucursal: {store['name']}", store.get("location", "-"), store.get("timezone", "UTC")])
        writer.writerow(
            [
                "SKU",
                "Nombre",
                "Cantidad",
                "Precio unitario",
                "Valor total",
                "IMEI",
                "Serie",
                "Marca",
                "Modelo",
                "Proveedor",
                "Color",
                "Capacidad (GB)",
                "Estado",
                "Lote",
                "Fecha compra",
                "Garantía (meses)",
                "Costo unitario",
                "Margen (%)",
            ]
        )
        store_total = 0.0
        for device in store.get("devices", []):
            inventory_value_raw = device.get("inventory_value", 0)
            unit_price_raw = device.get("unit_price", 0)
            costo_unitario_raw = device.get("costo_unitario", 0.0)
            margen_raw = device.get("margen_porcentaje", 0.0)

            try:
                inventory_value_float = float(inventory_value_raw)
            except (TypeError, ValueError):
                inventory_value_float = 0.0

            try:
                unit_price_float = float(unit_price_raw)
            except (TypeError, ValueError):
                unit_price_float = 0.0

            try:
                costo_unitario = float(costo_unitario_raw)
            except (TypeError, ValueError):
                costo_unitario = 0.0

            try:
                margen_porcentaje = float(margen_raw)
            except (TypeError, ValueError):
                margen_porcentaje = 0.0

            store_total += inventory_value_float
            garantia = device.get("garantia_meses")
            writer.writerow(
                [
                    device.get("sku"),
                    device.get("name"),
                    device.get("quantity"),
                    f"{unit_price_float:.2f}",
                    f"{inventory_value_float:.2f}",
                    device.get("imei") or "-",
                    device.get("serial") or "-",
                    device.get("marca") or "-",
                    device.get("modelo") or "-",
                    device.get("proveedor") or "-",
                    device.get("color") or "-",
                    device.get("capacidad_gb") if device.get("capacidad_gb") is not None else "-",
                    device.get("estado_comercial", "-"),
                    device.get("lote") or "-",
                    device.get("fecha_compra") or "-",
                    garantia if garantia is not None else "-",
                    f"{costo_unitario:.2f}",
                    f"{margen_porcentaje:.2f}",
                ]
            )

        registered_value_raw = store.get("inventory_value")
        try:
            registered_value = float(registered_value_raw) if registered_value_raw is not None else store_total
        except (TypeError, ValueError):
            registered_value = store_total

        totals_padding = [""] * 13
        writer.writerow(["TOTAL SUCURSAL", "", "", "", f"{store_total:.2f}", *totals_padding])
        writer.writerow(["VALOR CONTABLE", "", "", "", f"{registered_value:.2f}", *totals_padding])

        consolidated_total += store_total

    summary = snapshot.get("summary") or {}
    if summary:
        writer.writerow([])
        writer.writerow(["Resumen corporativo"])
        writer.writerow(["Sucursales auditadas", summary.get("store_count", 0)])
        writer.writerow(["Dispositivos catalogados", summary.get("device_records", 0)])
        writer.writerow(["Unidades totales", summary.get("total_units", 0)])
        summary_value_raw = summary.get("inventory_value")
        try:
            summary_value = float(summary_value_raw) if summary_value_raw is not None else 0.0
        except (TypeError, ValueError):
            summary_value = 0.0
        writer.writerow(["Inventario consolidado registrado (MXN)", f"{summary_value:.2f}"])
        writer.writerow(["Inventario consolidado calculado (MXN)", f"{consolidated_total:.2f}"])

    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=softmobile_inventario.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/inventory/value/csv")
def inventory_value_csv(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    normalized_categories = [category for category in categories or [] if category]
    report = crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Valoración de inventario"])
    writer.writerow(["Sucursales consideradas", len(report.stores)])
    writer.writerow([])
    writer.writerow(["Sucursal", "Valor total (MXN)", "Valor costo (MXN)", "Margen estimado (MXN)"])
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
    writer.writerow([
        "Totales corporativos",
        f"{report.totals.valor_total:.2f}",
        f"{report.totals.valor_costo:.2f}",
        f"{report.totals.margen_total:.2f}",
    ])

    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=softmobile_valor_inventario.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/inventory/movements/csv")
def inventory_movements_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc

    report = crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Movimientos de inventario"])
    writer.writerow(["Total registros", report.resumen.total_movimientos])
    writer.writerow(["Total unidades", report.resumen.total_unidades])
    writer.writerow(["Valor total (MXN)", f"{report.resumen.total_valor:.2f}"])
    writer.writerow([])
    writer.writerow(["Resumen por tipo"])
    writer.writerow(["Tipo", "Cantidad", "Valor (MXN)"])
    for entry in report.resumen.por_tipo:
        writer.writerow(
            [
                entry.tipo_movimiento.value,
                entry.total_cantidad,
                f"{entry.total_valor:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Acumulado por periodo"])
    writer.writerow(["Fecha", "Tipo", "Cantidad", "Valor (MXN)"])
    for period_entry in report.periodos:
        writer.writerow(
            [
                period_entry.periodo.isoformat(),
                period_entry.tipo_movimiento.value,
                period_entry.total_cantidad,
                f"{period_entry.total_valor:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Detalle de movimientos"])
    writer.writerow(
        [
            "ID",
            "Fecha",
            "Tipo",
            "Cantidad",
            "Valor (MXN)",
            "Sucursal destino",
            "Sucursal origen",
            "Usuario",
            "Comentario",
        ]
    )
    for movement in report.movimientos:
        writer.writerow(
            [
                movement.id,
                movement.fecha.isoformat(),
                movement.tipo_movimiento.value,
                movement.cantidad,
                f"{movement.valor_total:.2f}",
                movement.tienda_destino or "-",
                movement.tienda_origen or "-",
                movement.usuario or "-",
                movement.comentario or "-",
            ]
        )

    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=softmobile_movimientos.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/inventory/top-products/csv")
def inventory_top_products_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Productos más vendidos"])
    writer.writerow(["Total unidades", report.total_unidades])
    writer.writerow(["Ingresos totales (MXN)", f"{report.total_ingresos:.2f}"])
    writer.writerow([])
    writer.writerow(
        [
            "SKU",
            "Producto",
            "Sucursal",
            "Unidades vendidas",
            "Ingresos (MXN)",
            "Margen estimado (MXN)",
        ]
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
    headers = {"Content-Disposition": "attachment; filename=softmobile_top_productos.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get(
    "/inventory/supplier-batches",
    response_model=list[schemas.SupplierBatchOverviewItem],
)
def inventory_supplier_batches(
    store_id: int = Query(..., ge=1),
    limit: int = Query(default=5, ge=1, le=25),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.get_supplier_batch_overview(db, store_id=store_id, limit=limit)


@router.get("/metrics", response_model=schemas.InventoryMetricsResponse)
def inventory_metrics(
    low_stock_threshold: int = Query(default=5, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.compute_inventory_metrics(db, low_stock_threshold=low_stock_threshold)
