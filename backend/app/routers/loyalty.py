"""Endpoints para gestionar cuentas de lealtad y sus movimientos."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get(
    "/accounts",
    response_model=list[schemas.LoyaltyAccountResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_loyalty_accounts_endpoint(
    is_active: bool | None = Query(default=None),
    customer_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    return crud.list_loyalty_accounts(
        db, is_active=is_active, customer_id=customer_id
    )


@router.get(
    "/accounts/{customer_id}",
    response_model=schemas.LoyaltyAccountResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_loyalty_account_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    account = crud.get_loyalty_account(
        db, customer_id, with_transactions=False
    )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta de lealtad no encontrada.",
        )
    return account


@router.put(
    "/accounts/{customer_id}",
    response_model=schemas.LoyaltyAccountResponse,
)
def update_loyalty_account_endpoint(
    customer_id: int,
    payload: schemas.LoyaltyAccountUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        account = crud.update_loyalty_account(
            db,
            customer_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except ValueError as exc:
        if str(exc) == "loyalty_redemption_rate_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La tasa de canje debe ser mayor que cero.",
            ) from exc
        raise
    return account


@router.get(
    "/transactions",
    response_model=list[schemas.LoyaltyTransactionResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_loyalty_transactions_endpoint(
    account_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    sale_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    return crud.list_loyalty_transactions(
        db,
        account_id=account_id,
        customer_id=customer_id,
        sale_id=sale_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/reports/summary",
    response_model=schemas.LoyaltyReportSummary,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_loyalty_summary_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    return crud.get_loyalty_summary(db)
