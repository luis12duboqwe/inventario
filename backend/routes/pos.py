"""Router POS extendido con soporte de ventas multipago."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from backend.app.core.roles import GESTION_ROLES
from backend.app.core.transactions import flush_session, transactional_session
from backend.app.routers import pos as core_pos
from backend.app.routers.dependencies import require_reason
from backend.app.schemas import BinaryFileResponse
from backend.app.security import get_current_user, require_roles
from backend.core.logging import logger as core_logger
from backend.db import get_db, init_db
from backend.models.pos import Payment, PaymentMethod, Sale, SaleItem, SaleStatus
from backend.schemas import pos as schemas

from ._core_bridge import mount_core_router

extended_router = APIRouter(prefix="/pos", tags=["pos"])

logger = core_logger.bind(component="backend.routes.pos")


async def _initialize_pos_tables() -> None:
    """Prepara las tablas requeridas por el POS extendido en el arranque."""

    init_db()


extended_router.add_event_handler("startup", _initialize_pos_tables)


_DECIMAL_ZERO = Decimal("0")
_DECIMAL_CENT = Decimal("0.01")
_POS_ID_OFFSET = schemas.POS_SALE_OFFSET


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_DECIMAL_CENT)


def _load_sale(db: Session, sale_id: int, *, allow_internal: bool = False) -> Sale | None:
    if sale_id >= _POS_ID_OFFSET:
        internal_id = sale_id - _POS_ID_OFFSET
    elif allow_internal:
        internal_id = sale_id
    else:
        return None
    statement = (
        select(Sale)
        .where(Sale.id == internal_id)
        .options(selectinload(Sale.items), selectinload(Sale.payments))
    )
    return db.execute(statement).scalar_one_or_none()


def _ensure_sale(db: Session, sale_id: int) -> Sale:
    sale = _load_sale(db, sale_id, allow_internal=True)
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "sale_not_found", "message": "Venta no encontrada."},
        )
    return sale


def _build_item_from_payload(sale: Sale, payload: schemas.SaleItemCreate) -> SaleItem:
    unit_price = _quantize(payload.unit_price)
    line_subtotal = _quantize(unit_price * payload.quantity)
    discount = min(_quantize(payload.discount_amount), line_subtotal)
    taxable_base = line_subtotal - discount
    tax_rate = _quantize(payload.tax_rate)
    tax_amount = _quantize(taxable_base * (tax_rate / Decimal("100")))
    total = _quantize(taxable_base + tax_amount)
    return SaleItem(
        sale_id=sale.id,
        product_id=payload.product_id,
        description=payload.description,
        quantity=payload.quantity,
        unit_price=unit_price,
        discount_amount=discount,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        line_subtotal=line_subtotal,
        total_amount=total,
    )


@extended_router.post(
    "/sales",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_201_CREATED,
)
def create_sale(
    payload: schemas.SaleCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.SaleResponse:
    del reason, current_user
    with transactional_session(db):
        sale = Sale(store_id=payload.store_id, notes=payload.notes)
        db.add(sale)
        flush_session(db)
        sale_id = sale.id
    persisted = _ensure_sale(db, sale_id)
    logger.bind(module="pos", action="sale_created", sale_id=sale.id).info(
        "Se creó una venta POS en estado OPEN"
    )
    return schemas.SaleResponse.model_validate(persisted)


@extended_router.post(
    "/sales/{sale_id}/items",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_201_CREATED,
)
def add_items(
    payload: schemas.SaleItemsRequest,
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.SaleResponse:
    del reason, current_user
    with transactional_session(db):
        sale = _ensure_sale(db, sale_id)
        if sale.status not in {SaleStatus.OPEN, SaleStatus.HELD}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "sale_not_editable",
                    "message": "Solo las ventas abiertas u on hold admiten modificaciones.",
                },
            )
        sale.items.extend(
            _build_item_from_payload(sale, item_payload)
            for item_payload in payload.items
        )
        sale.recompute_totals()
        if sale.status == SaleStatus.HELD:
            sale.held_at = datetime.utcnow()
        db.add(sale)
        flush_session(db)
        db.refresh(sale)
        persisted = sale
    logger.bind(module="pos", action="items_added", sale_id=sale_id).info(
        "Se añadieron artículos a la venta"
    )
    return schemas.SaleResponse.model_validate(persisted)


@extended_router.post(
    "/sales/{sale_id}/checkout",
    response_model=schemas.CheckoutResponse,
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_200_OK,
)
def checkout_sale(
    payload: schemas.CheckoutRequest,
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.CheckoutResponse:
    del reason, current_user
    request_id = uuid4()
    with transactional_session(db):
        sale = _ensure_sale(db, sale_id)
        if not sale.items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "sale_without_items",
                    "message": "No es posible finalizar una venta sin artículos registrados.",
                },
            )
        if sale.status == SaleStatus.VOID:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "sale_voided", "message": "La venta fue anulada previamente."},
            )
        sale.recompute_totals()
        payments_total = _quantize(
            sum((_quantize(payment.amount) for payment in payload.payments), _DECIMAL_ZERO)
        )
        if payments_total != sale.total_amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "payments_do_not_match_total",
                    "message": "La suma de los pagos debe coincidir con el total de la venta.",
                },
            )
        sale.payments.clear()
        for payment_payload in payload.payments:
            sale.payments.append(
                Payment(
                    method=payment_payload.method,
                    amount=_quantize(payment_payload.amount),
                    reference=payment_payload.reference,
                )
            )
        sale.status = SaleStatus.COMPLETED
        sale.completed_at = datetime.utcnow()
        sale.voided_at = None
        sale.updated_at = datetime.utcnow()
        db.add(sale)
        flush_session(db)
        db.refresh(sale)
        persisted = sale
    logger.bind(module="pos", action="sale_completed", sale_id=sale_id).info(
        "Venta finalizada con pagos múltiples"
    )
    response = schemas.CheckoutResponse.model_validate(persisted)
    response.request_id = request_id
    return response


@extended_router.post(
    "/sales/{sale_id}/hold",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_200_OK,
)
def hold_sale(
    sale_id: int,
    payload: schemas.SaleActionRequest | None = None,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.SaleResponse:
    del reason, current_user
    with transactional_session(db):
        sale = _ensure_sale(db, sale_id)
        if sale.status != SaleStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "sale_cannot_hold",
                    "message": "Solo las ventas abiertas pueden pasar a estado hold.",
                },
            )
        sale.status = SaleStatus.HELD
        sale.held_at = datetime.utcnow()
        if payload and payload.reason:
            sale.notes = payload.reason
        sale.updated_at = datetime.utcnow()
        db.add(sale)
        flush_session(db)
        db.refresh(sale)
        persisted = sale
    logger.bind(module="pos", action="sale_held", sale_id=sale_id).info(
        "Venta movida a estado hold"
    )
    return schemas.SaleResponse.model_validate(persisted)


@extended_router.post(
    "/sales/{sale_id}/resume",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(get_current_user)],
)
def resume_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.SaleResponse:
    del reason, current_user
    with transactional_session(db):
        sale = _ensure_sale(db, sale_id)
        if sale.status != SaleStatus.HELD:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "sale_cannot_resume",
                    "message": "Solo las ventas en hold pueden reanudarse.",
                },
            )
        sale.status = SaleStatus.OPEN
        sale.held_at = None
        sale.updated_at = datetime.utcnow()
        db.add(sale)
        flush_session(db)
        db.refresh(sale)
        persisted = sale
    logger.bind(module="pos", action="sale_resumed", sale_id=sale_id).info(
        "Venta reanudada desde hold"
    )
    return schemas.SaleResponse.model_validate(persisted)


@extended_router.post(
    "/sales/{sale_id}/void",
    response_model=schemas.SaleResponse,
    dependencies=[Depends(get_current_user)],
)
def void_sale(
    sale_id: int,
    payload: schemas.SaleActionRequest | None = None,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.SaleResponse:
    del reason, current_user
    with transactional_session(db):
        sale = _ensure_sale(db, sale_id)
        if sale.status == SaleStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "sale_completed",
                    "message": "No es posible anular una venta completada desde el POS ligero.",
                },
            )
        sale.status = SaleStatus.VOID
        sale.voided_at = datetime.utcnow()
        if payload and payload.reason:
            sale.notes = payload.reason
        sale.updated_at = datetime.utcnow()
        sale.payments.clear()
        db.add(sale)
        flush_session(db)
        db.refresh(sale)
        persisted = sale
    logger.bind(module="pos", action="sale_voided", sale_id=sale_id).warning(
        "Venta anulada"
    )
    return schemas.SaleResponse.model_validate(persisted)


@extended_router.get(
    "/receipt/{sale_id}",
    response_model=schemas.ReceiptResponse | BinaryFileResponse,
    dependencies=[Depends(get_current_user)],
)
def read_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    if sale_id >= _POS_ID_OFFSET:
        sale = _load_sale(db, sale_id)
        if sale and sale.status == SaleStatus.COMPLETED:
            return schemas.ReceiptResponse.model_validate(sale)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "sale_not_found", "message": "Venta no encontrada."},
        )

    try:
        return core_pos.download_pos_receipt(
            sale_id=sale_id,
            db=db,
            reason=reason,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except OperationalError:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.setTitle(f"Recibo POS {sale_id}")
        pdf.drawString(72, 800, "Recibo POS no disponible en la base actual")
        pdf.drawString(72, 780, f"ID de venta: {sale_id}")
        pdf.drawString(72, 760, "Generado desde Softmobile 2025 v2.2.0")
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return Response(
            content=buffer.read(),
            media_type="application/pdf",
            status_code=status.HTTP_200_OK,
        )


router = APIRouter()
router.include_router(extended_router)

core_router = mount_core_router(core_pos.router)
core_router.routes[:] = [
    route
    for route in core_router.routes
    if getattr(route, "path", None) != "/pos/receipt/{sale_id}"
]
router.include_router(core_router)


__all__ = ["extended_router", "router"]
