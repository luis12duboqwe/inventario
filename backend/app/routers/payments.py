from datetime import datetime

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import credit, pos_receipts

_ERROR_MESSAGES = {
    "customer_payment_no_debt": (
        status.HTTP_409_CONFLICT,
        "El cliente no tiene deuda pendiente.",
    ),
    "customer_payment_invalid_amount": (
        status.HTTP_400_BAD_REQUEST,
        "El monto del pago es inválido.",
    ),
    "customer_payment_sale_mismatch": (
        status.HTTP_400_BAD_REQUEST,
        "La venta seleccionada no pertenece al cliente.",
    ),
    "payment_center_refund_invalid_amount": (
        status.HTTP_400_BAD_REQUEST,
        "El monto del reembolso es inválido.",
    ),
    "payment_center_credit_note_invalid_amount": (
        status.HTTP_400_BAD_REQUEST,
        "El monto de la nota de crédito es inválido.",
    ),
}


def _map_value_error(error: ValueError, default_message: str) -> HTTPException:
    error_key = str(error)
    status_code, detail = _ERROR_MESSAGES.get(
        error_key, (status.HTTP_400_BAD_REQUEST, default_message)
    )
    return HTTPException(status_code=status_code, detail=detail)

router = APIRouter(prefix="/payments", tags=["pagos"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


@router.get("/center", response_model=schemas.PaymentCenterResponse)
def get_payment_center(
    limit: int = Query(default=50, ge=1, le=200),
    query: str | None = Query(default=None, min_length=1, max_length=120),
    method: str | None = Query(default=None, min_length=2, max_length=40),
    type_filter: str | None = Query(default=None, alias="type"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.PaymentCenterResponse:
    _ensure_feature_enabled()
    normalized_type: str | None = None
    if type_filter:
        candidate = type_filter.strip().upper()
        if candidate in {"PAYMENT", "REFUND", "CREDIT_NOTE"}:
            normalized_type = candidate
    transactions = crud.list_payment_center_transactions(
        db,
        limit=limit,
        query=query.strip() if isinstance(query, str) and query.strip() else None,
        method=method.strip().upper() if isinstance(method, str) and method.strip() else None,
        type_filter=normalized_type,  # type: ignore[arg-type]
        date_from=date_from,
        date_to=date_to,
    )
    summary = crud.get_payment_center_summary(db)
    return schemas.PaymentCenterResponse(summary=summary, transactions=transactions)


@router.post(
    "/center/payment",
    response_model=schemas.CustomerPaymentReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_payment_center_payment(
    payload: schemas.PaymentCenterPaymentCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.CustomerPaymentReceiptResponse:
    _ensure_feature_enabled()
    _ = reason
    try:
        outcome = crud.register_customer_payment(
            db,
            payload.customer_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        raise _map_value_error(exc, "No fue posible registrar el pago.") from exc
    snapshot = credit.build_debt_snapshot(
        previous_balance=outcome.previous_debt,
        new_charges=Decimal("0"),
        payments_applied=outcome.applied_amount,
    )
    schedule = credit.build_credit_schedule(
        base_date=outcome.ledger_entry.created_at,
        remaining_balance=snapshot.remaining_balance,
    )
    debt_summary = schemas.CustomerDebtSnapshot(
        previous_balance=snapshot.previous_balance,
        new_charges=snapshot.new_charges,
        payments_applied=snapshot.payments_applied,
        remaining_balance=snapshot.remaining_balance,
    )
    schedule_payload = [
        schemas.CreditScheduleEntry.model_validate(entry)
        for entry in schedule
    ]
    receipt_pdf = pos_receipts.render_debt_receipt_base64(
        outcome.customer,
        outcome.ledger_entry,
        snapshot,
        schedule,
    )
    return schemas.CustomerPaymentReceiptResponse(
        ledger_entry=schemas.CustomerLedgerEntryResponse.model_validate(
            outcome.ledger_entry
        ),
        debt_summary=debt_summary,
        credit_schedule=schedule_payload,
        receipt_pdf_base64=receipt_pdf,
    )


@router.post(
    "/center/refund",
    response_model=schemas.CustomerLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_payment_center_refund(
    payload: schemas.PaymentCenterRefundCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.CustomerLedgerEntryResponse:
    _ensure_feature_enabled()
    _ = reason
    try:
        ledger_entry = crud.register_payment_center_refund(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        raise _map_value_error(exc, "No fue posible registrar el reembolso.") from exc
    return schemas.CustomerLedgerEntryResponse.model_validate(ledger_entry)


@router.post(
    "/center/credit-note",
    response_model=schemas.CustomerLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_payment_center_credit_note(
    payload: schemas.PaymentCenterCreditNoteCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.CustomerLedgerEntryResponse:
    _ensure_feature_enabled()
    _ = reason
    try:
        ledger_entry = crud.register_payment_center_credit_note(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        raise _map_value_error(
            exc, "No fue posible registrar la nota de crédito."
        ) from exc
    return schemas.CustomerLedgerEntryResponse.model_validate(ledger_entry)

