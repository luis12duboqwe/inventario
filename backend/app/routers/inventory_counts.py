"""Endpoints de recepciones y conteos cíclicos de inventario."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN, MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import inventory_reports, audit as audit_service
from ..utils import audit as audit_utils

router = APIRouter(prefix="/inventory/counts", tags=["inventario"])


def _resolve_identifier(line: schemas.InventoryReceivingLine | schemas.InventoryCountLine) -> str:
    if getattr(line, "imei", None):
        return str(line.imei)
    if getattr(line, "serial", None):
        return str(line.serial)
    if getattr(line, "device_id", None):
        return str(line.device_id)
    return "desconocido"


def _decorate_comment(base: str, responsible: str | None, suffix: str | None = None) -> str:
    segments = [base.strip()]
    if responsible:
        segments.append(f"Resp: {responsible.strip()}")
    if suffix:
        segments.append(suffix.strip())
    comment = " · ".join(segment for segment in segments if segment)
    return comment[:255]


@router.post(
    "/receipts",
    response_model=schemas.InventoryReceivingResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def register_inventory_receiving(
    payload: schemas.InventoryReceivingRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.InventoryReceivingResult:
    """Registra recepciones masivas, creando movimientos de entrada."""

    processed: list[schemas.InventoryReceivingProcessed] = []
    total_quantity = 0
    performer_id = getattr(current_user, "id", None)
    auto_transfers: list[schemas.TransferOrderResponse] = []
    distribution_plan: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    if any(line.distributions for line in payload.lines) and not settings.enable_transfers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Las transferencias automáticas están deshabilitadas.",
        )

    for line in payload.lines:
        try:
            device = crud.resolve_device_for_inventory(
                db,
                store_id=payload.store_id,
                device_id=line.device_id,
                imei=line.imei,
                serial=line.serial,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="device_not_found",
            ) from exc

        comment_base = line.comment or payload.note
        comment = _decorate_comment(comment_base, payload.responsible)
        movement_payload = schemas.MovementCreate(
            producto_id=device.id,
            tipo_movimiento=models.MovementType.IN,
            cantidad=line.quantity,
            comentario=comment,
            unit_cost=line.unit_cost,
        )

        try:
            movement = crud.create_inventory_movement(
                db,
                payload.store_id,
                movement_payload,
                performed_by_id=performer_id,
                reference_type="inventory_receiving",
                reference_id=payload.reference or _resolve_identifier(line),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        processed.append(
            schemas.InventoryReceivingProcessed(
                identifier=_resolve_identifier(line),
                device_id=device.id,
                quantity=line.quantity,
                movement=schemas.MovementResponse.model_validate(movement),
            )
        )
        total_quantity += line.quantity

        if line.distributions:
            for allocation in line.distributions:
                if allocation.store_id == payload.store_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="La distribución automática no puede usar la misma sucursal de origen.",
                    )
                distribution_plan[allocation.store_id][device.id] += allocation.quantity

    totals = schemas.InventoryReceivingSummary(lines=len(processed), total_quantity=total_quantity)
    if distribution_plan:
        transfer_reason_base = payload.note.strip()
        transfer_reason = f"{transfer_reason_base} · distribución automática"[:255]
        for destination_store_id, device_map in distribution_plan.items():
            items = [
                schemas.TransferOrderItemCreate(device_id=device_id, quantity=quantity)
                for device_id, quantity in device_map.items()
                if quantity > 0
            ]
            if not items:
                continue
            transfer_payload = schemas.TransferOrderCreate(
                origin_store_id=payload.store_id,
                destination_store_id=destination_store_id,
                reason=transfer_reason,
                items=items,
            )
            try:
                order = crud.create_transfer_order(
                    db,
                    transfer_payload,
                    requested_by_id=performer_id,
                )
            except PermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para transferir desde la sucursal seleccionada.",
                ) from exc
            except LookupError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La distribución apunta a una sucursal inexistente.",
                ) from exc
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc

            try:
                order = crud.dispatch_transfer_order(
                    db,
                    order.id,
                    performed_by_id=performer_id,
                    reason=transfer_reason,
                )
            except (PermissionError, ValueError):
                order = crud.get_transfer_order(db, order.id)

            auto_transfers.append(
                schemas.TransferOrderResponse.model_validate(
                    order,
                    from_attributes=True,
                )
            )

    return schemas.InventoryReceivingResult(
        store_id=payload.store_id,
        processed=processed,
        totals=totals,
        auto_transfers=auto_transfers or None,
    )


@router.post(
    "/cycle",
    response_model=schemas.InventoryCycleCountResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def register_cycle_count(
    payload: schemas.InventoryCycleCountRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.InventoryCycleCountResult:
    """Conciliación de conteos cíclicos; crea ajustes cuando hay diferencias."""

    adjustments: list[schemas.InventoryCountDiscrepancy] = []
    performer_id = getattr(current_user, "id", None)
    total_variance = 0
    matched = 0

    for line in payload.lines:
        try:
            device = crud.resolve_device_for_inventory(
                db,
                store_id=payload.store_id,
                device_id=line.device_id,
                imei=line.imei,
                serial=line.serial,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="device_not_found",
            ) from exc

        expected = int(device.quantity)
        counted = int(line.counted)
        identifier = _resolve_identifier(line)

        if counted == expected:
            matched += 1
            continue

        comment_base = line.comment or payload.note
        comment_suffix = f"Conteo={counted}" if counted >= 0 else None
        comment = _decorate_comment(comment_base, payload.responsible, comment_suffix)

        movement_payload = schemas.MovementCreate(
            producto_id=device.id,
            tipo_movimiento=models.MovementType.ADJUST,
            cantidad=counted,
            comentario=comment,
        )

        try:
            movement = crud.create_inventory_movement(
                db,
                payload.store_id,
                movement_payload,
                performed_by_id=performer_id,
                reference_type="inventory_cycle_count",
                reference_id=payload.reference or identifier,
            )
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        delta = counted - expected
        total_variance += abs(delta)
        adjustments.append(
            schemas.InventoryCountDiscrepancy(
                device_id=device.id,
                sku=getattr(device, "sku", None),
                expected=expected,
                counted=counted,
                delta=delta,
                movement=schemas.MovementResponse.model_validate(movement),
                identifier=identifier,
            )
        )

    totals = schemas.InventoryCycleCountSummary(
        lines=len(payload.lines),
        adjusted=len(adjustments),
        matched=matched,
        total_variance=total_variance,
    )
    return schemas.InventoryCycleCountResult(
        store_id=payload.store_id,
        adjustments=adjustments,
        totals=totals,
    )


@router.get(
    "/adjustments/report",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def inventory_adjustments_report(
    format: Literal["pdf", "csv"] = Query(default="pdf"),
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=models.MovementType.ADJUST,
    )
    if format == "pdf":
        pdf_bytes = inventory_reports.render_inventory_adjustments_pdf(report)
        buffer = BytesIO(pdf_bytes)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_ajustes.pdf",
            media_type="application/pdf",
        )
        return StreamingResponse(
            buffer,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )

    csv_data = inventory_reports.serialize_inventory_adjustments_csv(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_ajustes.csv",
        media_type="text/csv; charset=utf-8",
    )
    return PlainTextResponse(
        csv_data,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get(
    "/audit/report",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def inventory_audit_report(
    format: Literal["pdf", "csv"] = Query(default="pdf"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    logs = crud.list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        action="inventory_movement",
        entity_type="inventory_movement",
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    filters: dict[str, str] = {"Acción": "inventory_movement"}
    if performed_by_id is not None:
        filters["Usuario"] = str(performed_by_id)
    if date_from:
        filters["Desde"] = str(date_from)
    if date_to:
        filters["Hasta"] = str(date_to)

    if format == "pdf":
        summary = audit_utils.summarize_alerts(logs)
        pdf_bytes = audit_service.render_audit_pdf(logs, filters=filters, alerts=summary)
        buffer = BytesIO(pdf_bytes)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_auditoria_inventario.pdf",
            media_type="application/pdf",
        )
        return StreamingResponse(
            buffer,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )

    csv_data = crud.export_audit_logs_csv(
        db,
        limit=limit,
        offset=offset,
        action="inventory_movement",
        entity_type="inventory_movement",
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_auditoria_inventario.csv",
        media_type="text/csv; charset=utf-8",
    )
    return PlainTextResponse(
        csv_data,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


__all__ = ["router"]
