"""Router para órdenes de reparación técnica."""
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..models import RepairStatus
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/repairs", tags=["repairs"])


@router.get("/", response_model=list[schemas.RepairOrderResponse])
def list_repairs_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    status_enum: RepairStatus | None = None
    if status_filter:
        try:
            status_enum = RepairStatus(status_filter.upper())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Estado inválido") from exc
    return crud.list_repair_orders(
        db,
        store_id=store_id,
        status=status_enum,
        query=q,
        limit=limit,
    )


@router.post("/", response_model=schemas.RepairOrderResponse, status_code=status.HTTP_201_CREATED)
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida de piezas.",
            ) from exc
        raise


@router.get("/{order_id}", response_model=schemas.RepairOrderResponse)
def get_repair_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_repair_order(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc


@router.put("/{order_id}", response_model=schemas.RepairOrderResponse)
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida de piezas.",
            ) from exc
        raise


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
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


@router.get("/{order_id}/pdf", response_model=schemas.BinaryFileResponse)
def download_repair_order_pdf(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        order = crud.get_repair_order(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada") from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setTitle(f"Orden_Reparacion_{order.id}")
    y_position = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y_position, f"Orden de reparación #{order.id}")
    y_position -= 20

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y_position, f"Sucursal: {order.store_id}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Estado: {order.status.value}")
    y_position -= 14
    if order.customer_name:
        pdf.drawString(40, y_position, f"Cliente: {order.customer_name}")
        y_position -= 14
    pdf.drawString(40, y_position, f"Técnico: {order.technician_name}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Daño reportado: {order.damage_type}")
    y_position -= 14
    if order.device_description:
        pdf.drawString(40, y_position, f"Equipo: {order.device_description}")
        y_position -= 14
    if order.notes:
        pdf.drawString(40, y_position, "Notas:")
        y_position -= 12
        pdf.setFont("Helvetica", 10)
        for line in order.notes.splitlines():
            pdf.drawString(60, y_position, line)
            y_position -= 12
        pdf.setFont("Helvetica", 11)

    y_position -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Piezas utilizadas")
    y_position -= 16
    pdf.setFont("Helvetica", 10)
    if not order.parts:
        pdf.drawString(40, y_position, "Sin registros de piezas.")
        y_position -= 14
    else:
        for part in order.parts:
            pdf.drawString(40, y_position, f"ID pieza: {part.device_id}")
            pdf.drawRightString(
                width - 40,
                y_position,
                f"Cantidad: {part.quantity}",
            )
            y_position -= 12
            pdf.drawString(
                60,
                y_position,
                f"Costo unitario: ${float(part.unit_cost):.2f}",
            )
            y_position -= 16
            if y_position < 80:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y_position = height - 60

    if y_position < 120:
        pdf.showPage()
        y_position = height - 60
        pdf.setFont("Helvetica", 11)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Resumen de costos")
    y_position -= 16
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y_position, f"Mano de obra: ${float(order.labor_cost):.2f}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Piezas: ${float(order.parts_cost):.2f}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Total: ${float(order.total_cost):.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename=f"orden_reparacion_{order.id}.pdf",
        media_type="application/pdf",
    )
    return Response(
        content=buffer.getvalue(),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(disposition="inline"),
    )
