"""Endpoints para la gestión de órdenes de reparación."""
from __future__ import annotations

from io import BytesIO
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES, REPORTE_ROLES
from ..database import get_db
from ..models import RepairStatus
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/repairs", tags=["reparaciones"])


def _build_pdf(order: schemas.RepairOrderResponse) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"orden-reparacion-{order.id}")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Informe de reparación", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Folio: <b>{order.id}</b>", styles["Heading3"]),
        Paragraph(f"Cliente: {order.cliente}", styles["BodyText"]),
        Paragraph(f"Dispositivo: {order.dispositivo}", styles["BodyText"]),
        Paragraph(f"Técnico asignado: {order.tecnico}", styles["BodyText"]),
        Spacer(1, 12),
    ]

    details = [
        ["Estado", order.estado.value],
        ["Costo", f"${order.costo:0.2f}"],
        ["Fecha de inicio", order.fecha_inicio.isoformat()],
        ["Fecha de entrega", order.fecha_entrega.isoformat() if order.fecha_entrega else "Pendiente"],
        ["Notas", order.notas or "Sin observaciones"],
    ]

    table = Table(details, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1f2937")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#22d3ee")),
            ]
        )
    )
    story.append(table)

    if order.piezas_usadas:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Piezas sustituidas", styles["Heading3"]))
        parts = "<br/>".join(f"• {item}" for item in order.piezas_usadas)
        story.append(Paragraph(parts, styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.get("", response_model=list[schemas.RepairOrderResponse])
def list_repair_orders(
    store_id: int | None = Query(default=None, ge=1),
    status_filter: RepairStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    store_ids: Iterable[int] | None = [store_id] if store_id else None
    orders = crud.list_repair_orders(db, store_ids=store_ids, status=status_filter)
    return orders


@router.post("", response_model=schemas.RepairOrderResponse, status_code=status.HTTP_201_CREATED)
def create_repair(
    payload: schemas.RepairOrderCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ = reason
    try:
        order = crud.create_repair_order(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada") from exc
    return order


@router.get("/{repair_id}", response_model=schemas.RepairOrderResponse)
def get_repair(
    repair_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    try:
        return crud.get_repair_order(db, repair_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc


@router.patch("/{repair_id}", response_model=schemas.RepairOrderResponse)
def update_repair(
    payload: schemas.RepairOrderUpdate,
    repair_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ = reason
    try:
        return crud.update_repair_order(
            db,
            repair_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc


@router.delete("/{repair_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repair(
    repair_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ = reason
    try:
        crud.delete_repair_order(
            db,
            repair_id,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{repair_id}/pdf", response_class=Response)
def download_repair_pdf(
    repair_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    try:
        order = crud.get_repair_order(db, repair_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc

    serialized = schemas.RepairOrderResponse.model_validate(order)
    pdf_bytes = _build_pdf(serialized)
    headers = {
        "Content-Disposition": f"inline; filename=orden-reparacion-{order.id}.pdf",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
