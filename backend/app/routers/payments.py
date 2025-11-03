from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

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
    response_model=schemas.CustomerLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_payment_center_payment(
    payload: schemas.PaymentCenterPaymentCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.CustomerLedgerEntryResponse:
    _ensure_feature_enabled()
    ledger_entry = crud.register_customer_payment(
        db,
        payload.customer_id,
        payload,
        performed_by_id=getattr(current_user, "id", None),
    )
    return schemas.CustomerLedgerEntryResponse.model_validate(ledger_entry)


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
    ledger_entry = crud.register_payment_center_refund(
        db,
        payload,
        performed_by_id=getattr(current_user, "id", None),
    )
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
    ledger_entry = crud.register_payment_center_credit_note(
        db,
        payload,
        performed_by_id=getattr(current_user, "id", None),
    )
    return schemas.CustomerLedgerEntryResponse.model_validate(ledger_entry)

