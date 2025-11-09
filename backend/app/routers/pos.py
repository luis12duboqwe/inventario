"""Endpoints dedicados al punto de venta con control de stock y recibos."""
from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import cash_register, payments, pos_receipts

router = APIRouter(prefix="/pos", tags=["pos"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


class _SaleValidationRollback(RuntimeError):
    """Permite abortar la transacción de validación sin efectos colaterales."""


@router.post(
    "/sale",
    response_model=schemas.POSSaleResponse,
    status_code=status.HTTP_201_CREATED
)
def register_pos_sale_endpoint(
    payload: schemas.POSSaleRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        crud.get_store(db, payload.store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sucursal no encontrada.",
        ) from exc
    try:
        if payload.save_as_draft:
            draft = crud.save_pos_draft(
                db,
                payload,
                saved_by_id=current_user.id if current_user else None,
                reason=reason,
            )
            return schemas.POSSaleResponse(status="draft", draft=draft, warnings=[])

        # // [PACK34-endpoints]
        normalized_items: list[schemas.POSCartItem] = []
        for item in payload.items:
            try:
                resolved_device = crud.resolve_device_for_pos(
                    db,
                    store_id=payload.store_id,
                    device_id=item.device_id,
                    imei=item.imei,
                )
            except LookupError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dispositivo no encontrado para la venta.",
                ) from exc
            normalized_items.append(
                item.model_copy(
                    update={
                        "device_id": resolved_device.id,
                        "imei": resolved_device.imei or item.imei,
                    }
                )
            )
        normalized_payload = payload.model_copy(update={"items": normalized_items})

        payments_payload = list(normalized_payload.payments or [])
        electronic_results: list[schemas.POSElectronicPaymentResult] = []
        has_electronic_payments = any(
            payment.method
            in {models.PaymentMethod.TARJETA, models.PaymentMethod.TRANSFERENCIA}
            for payment in payments_payload
        )

        if has_electronic_payments:
            try:
                with transactional_session(db):
                    crud.register_pos_sale(
                        db,
                        normalized_payload,
                        performed_by_id=current_user.id if current_user else None,
                        reason=reason,
                    )
                    raise _SaleValidationRollback()
            except _SaleValidationRollback:
                db.rollback()
                db.expire_all()

        if payments_payload:
            terminals_config = {
                key: dict(value)
                for key, value in settings.pos_payment_terminals.items()
            }
            try:
                electronic_results = payments.process_electronic_payments(
                    db,
                    payments=payments_payload,
                    payload=normalized_payload,
                    user_id=current_user.id if current_user else None,
                    terminals_config=terminals_config,
                )
            except payments.ElectronicPaymentError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(exc),
                ) from exc

        sale, warnings = crud.register_pos_sale(
            db,
            normalized_payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
        sale_detail = crud.get_sale(db, sale.id)
        config = crud.get_pos_config(db, sale_detail.store_id)
        receipt_pdf = pos_receipts.render_receipt_base64(sale_detail, config)
        return schemas.POSSaleResponse(
            status="registered",
            sale=sale_detail,
            warnings=warnings,
            receipt_url=f"/pos/receipt/{sale.id}",
            cash_session_id=sale.cash_session_id,
            payment_breakdown=
            {
                key: float(Decimal(str(value)))
                for key, value in payload.payment_breakdown.items()
            }
            if payload.payment_breakdown
            else {},
            receipt_pdf_base64=receipt_pdf,
            electronic_payments=electronic_results,
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
        if detail == "cash_session_not_open":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La caja indicada no está abierta.",
            ) from exc
        if detail == "customer_credit_limit_exceeded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente excede el límite de crédito disponible.",
            ) from exc
        raise


@router.get(
    "/receipt/{sale_id}",
    response_model=schemas.BinaryFileResponse
)
def download_pos_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        sale = crud.get_sale(db, sale_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada") from exc

    config = crud.get_pos_config(db, sale.store_id)
    pdf_bytes = pos_receipts.render_receipt_pdf(sale, config)  # // [PACK34-receipt]
    filename = f"recibo_{config.invoice_prefix}_{sale.id}.pdf"

    with transactional_session(db):
        crud.register_pos_receipt_download(
            db,
            sale_id=sale.id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )

    metadata = schemas.BinaryFileResponse(
        filename=filename,
        media_type="application/pdf",
    )
    return Response(
        content=pdf_bytes,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(disposition="inline"),
    )


# // [PACK34-endpoints]
@router.post(
    "/sessions/open",
    response_model=schemas.POSSessionSummary,
    status_code=status.HTTP_201_CREATED
)
def open_pos_session_endpoint(
    payload: schemas.POSSessionOpenPayload,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    open_payload = schemas.CashSessionOpenRequest(
        store_id=payload.branch_id,
        opening_amount=payload.opening_amount,
        notes=payload.notes,
    )
    session = cash_register.open_session(
        db,
        open_payload,
        opened_by_id=current_user.id if current_user else None,
        reason=reason,
    )
    return cash_register.to_summary(session)


# // [PACK34-endpoints]
@router.post(
    "/sessions/close",
    response_model=schemas.POSSessionSummary
)
def close_pos_session_endpoint(
    payload: schemas.POSSessionClosePayload,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    close_payload = schemas.CashSessionCloseRequest(
        session_id=payload.session_id,
        closing_amount=payload.closing_amount,
        notes=payload.notes,
        payment_breakdown=payload.payments,
    )
    session = cash_register.close_session(
        db,
        close_payload,
        closed_by_id=current_user.id if current_user else None,
        reason=reason,
    )
    return cash_register.to_summary(session)


# // [PACK34-endpoints]
@router.get(
    "/sessions/last",
    response_model=schemas.POSSessionSummary
)
def read_last_pos_session_endpoint(
    branch_id: int = Query(..., alias="branchId", ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        session = cash_register.last_session_for_store(db, store_id=branch_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión previa en la sucursal.",
        ) from exc
    return cash_register.to_summary(session)


# // [PACK34-endpoints]
@router.get(
    "/taxes",
    response_model=list[schemas.POSTaxInfo]
)
def list_pos_taxes_endpoint(
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    return crud.list_pos_taxes(db)


# // [PACK34-endpoints]
@router.post(
    "/return",
    response_model=schemas.POSReturnResponse,
    status_code=status.HTTP_201_CREATED
)
def register_pos_return_endpoint(
    payload: schemas.POSReturnRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        sale = crud.get_sale(db, payload.original_sale_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta original no encontrada.",
        ) from exc

    normalized_reason = payload.reason or "Devolución POS"
    normalized_items: list[schemas.SaleReturnItem] = []
    for item in payload.items:
        try:
            device = crud.resolve_device_for_pos(
                db,
                store_id=sale.store_id,
                device_id=item.product_id,
                imei=item.imei,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no localizado en la venta.",
            ) from exc
        normalized_items.append(
            schemas.SaleReturnItem(
                device_id=device.id,
                quantity=item.qty,
                reason=normalized_reason,
            )
        )

    request_payload = schemas.SaleReturnCreate(
        sale_id=sale.id,
        items=normalized_items,
    )
    try:
        returns = crud.register_sale_return(
            db,
            request_payload,
            processed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artículo de venta no encontrado para devolución.",
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
        raise

    return schemas.POSReturnResponse(
        sale_id=sale.id,
        return_ids=[sale_return.id for sale_return in returns],
        notes=payload.reason,
    )


# // [PACK34-endpoints]
@router.get(
    "/sale/{sale_id}",
    response_model=schemas.POSSaleDetailResponse
)
def read_pos_sale_detail_endpoint(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        sale = crud.get_sale(db, sale_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada.",
        ) from exc
    config = crud.get_pos_config(db, sale.store_id)
    receipt_pdf = pos_receipts.render_receipt_base64(sale, config)
    return schemas.POSSaleDetailResponse(
        sale=sale,
        receipt_url=f"/pos/receipt/{sale.id}",
        receipt_pdf_base64=receipt_pdf,
    )


@router.get(
    "/config",
    response_model=schemas.POSConfigResponse
)
def read_pos_config(
    store_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        config = crud.get_pos_config(db, store_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada") from exc
    with transactional_session(db):
        crud.register_pos_config_access(
            db,
            store_id=store_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    return schemas.POSConfigResponse.from_model(
        config,
        terminals=settings.pos_payment_terminals,
        tip_suggestions=settings.pos_tip_suggestions,
    )


@router.put(
    "/config",
    response_model=schemas.POSConfigResponse
)
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
    return schemas.POSConfigResponse.from_model(
        config,
        terminals=settings.pos_payment_terminals,
        tip_suggestions=settings.pos_tip_suggestions,
    )


@router.post(
    "/cash/open",
    response_model=schemas.CashSessionResponse,
    status_code=status.HTTP_201_CREATED
)
def open_cash_session_endpoint(
    payload: schemas.CashSessionOpenRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.open_cash_session(
            db,
            payload,
            opened_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except ValueError as exc:
        if str(exc) == "cash_session_already_open":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una caja abierta en la sucursal.",
            ) from exc
        raise


@router.post(
    "/cash/close",
    response_model=schemas.CashSessionResponse
)
def close_cash_session_endpoint(
    payload: schemas.CashSessionCloseRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.close_cash_session(
            db,
            payload,
            closed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada") from exc
    except ValueError as exc:
        if str(exc) == "cash_session_not_open":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La caja ya fue cerrada.",
            ) from exc
        raise


@router.get(
    "/cash/history",
    response_model=list[schemas.CashSessionResponse]
)
def list_cash_sessions_endpoint(
    store_id: int = Query(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    sessions = cash_register.list_sessions(
        db,
        store_id=store_id,
        limit=limit,
        offset=offset,
    )
    return sessions
