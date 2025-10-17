"""Endpoints dedicados al punto de venta con control de stock y recibos."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Response, status
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/pos", tags=["pos"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


@router.post("/sale", response_model=schemas.POSSaleResponse, status_code=status.HTTP_201_CREATED)
def register_pos_sale_endpoint(
    payload: schemas.POSSaleRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        if payload.save_as_draft:
            draft = crud.save_pos_draft(
                db,
                payload,
                saved_by_id=current_user.id if current_user else None,
                reason=reason,
            )
            return schemas.POSSaleResponse(status="draft", draft=draft, warnings=[])

        sale, warnings = crud.register_pos_sale(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
        return schemas.POSSaleResponse(
            status="registered",
            sale=sale,
            warnings=warnings,
            receipt_url=f"/pos/receipt/{sale.id}",
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "pos_confirmation_required":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Confirma visualmente el total antes de registrar la venta.",
            ) from exc
        if detail == "sale_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la venta.",
            ) from exc
        if detail == "sale_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para completar la venta.",
            ) from exc
        raise


@router.get("/receipt/{sale_id}")
def download_pos_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    x_reason: str | None = Header(default=None, alias="X-Reason"),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    if x_reason is not None and len(x_reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason header inválido",
        )
    try:
        sale = crud.get_sale(db, sale_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada") from exc

    config = crud.get_pos_config(db, sale.store_id)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    store_name = sale.store.name if sale.store else "Sucursal"
    pdf.setTitle(f"Recibo_{config.invoice_prefix}_{sale.id}")
    y_position = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y_position, store_name)
    y_position -= 18
    pdf.setFont("Helvetica", 10)
    if sale.store and sale.store.location:
        pdf.drawString(40, y_position, sale.store.location)
        y_position -= 14

    pdf.drawString(40, y_position, f"Factura: {config.invoice_prefix}-{sale.id:06d}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Fecha: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    y_position -= 14
    if sale.customer_name:
        pdf.drawString(40, y_position, f"Cliente: {sale.customer_name}")
        y_position -= 14
    pdf.drawString(40, y_position, f"Método: {sale.payment_method.value}")
    y_position -= 20

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Detalle")
    y_position -= 16
    pdf.setFont("Helvetica", 10)

    def _ensure_space(current: float, lines: int = 1) -> float:
        required = 12 * lines
        if current - required < 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            return height - 40
        return current

    for item in sale.items:
        y_position = _ensure_space(y_position, 2)
        device_label = item.device.name if item.device else f"ID {item.device_id}"
        pdf.drawString(40, y_position, f"{device_label} · Cant: {item.quantity}")
        pdf.drawRightString(
            width - 40,
            y_position,
            f"${item.total_line:.2f}",
        )
        y_position -= 14
        pdf.drawString(
            60,
            y_position,
            f"Precio: ${item.unit_price:.2f}  Descuento: ${item.discount_amount:.2f}",
        )
        y_position -= 14

    y_position = _ensure_space(y_position, 4)
    pdf.line(40, y_position, width - 40, y_position)
    y_position -= 14
    pdf.drawRightString(width - 40, y_position, f"Subtotal: ${sale.subtotal_amount:.2f}")
    y_position -= 14
    pdf.drawRightString(width - 40, y_position, f"Impuestos ({float(config.tax_rate):.2f}%): ${sale.tax_amount:.2f}")
    y_position -= 14
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 40, y_position, f"Total: ${sale.total_amount:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    filename = f"recibo_{config.invoice_prefix}_{sale.id}.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


@router.get("/config", response_model=schemas.POSConfigResponse)
def read_pos_config(
    store_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        config = crud.get_pos_config(db, store_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada") from exc
    return config


@router.put("/config", response_model=schemas.POSConfigResponse)
def update_pos_config_endpoint(
    payload: schemas.POSConfigUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        config = crud.update_pos_config(
            db,
            payload,
            updated_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada") from exc
    return config
