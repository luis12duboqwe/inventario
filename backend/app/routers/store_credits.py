"""Endpoints para emisión y redención de notas de crédito."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/store-credits", tags=["store_credits"])


@router.get(
    "/by-customer/{customer_id}",
    response_model=list[schemas.StoreCreditResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_store_credits_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
):
    del reason
    try:
        crud.get_customer(db, customer_id)
        credits = crud.list_store_credits(db, customer_id=customer_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        ) from exc
    return [schemas.StoreCreditResponse.model_validate(credit) for credit in credits]


@router.post(
    "/",
    response_model=schemas.StoreCreditResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def issue_store_credit_endpoint(
    payload: schemas.StoreCreditIssueRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    performed_by = current_user.id if current_user else None
    try:
        credit = crud.issue_store_credit(
            db,
            payload,
            performed_by_id=performed_by,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "store_credit_code_in_use":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El código de nota de crédito ya existe.",
            ) from exc
        if detail == "store_credit_invalid_amount":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El monto debe ser mayor a cero.",
            ) from exc
        raise
    return schemas.StoreCreditResponse.model_validate(credit)


@router.post(
    "/redeem",
    response_model=schemas.StoreCreditResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def redeem_store_credit_endpoint(
    payload: schemas.StoreCreditRedeemRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    performed_by = current_user.id if current_user else None
    try:
        credit, _ = crud.redeem_store_credit(
            db,
            payload,
            performed_by_id=performed_by,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota de crédito no encontrada.",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "store_credit_invalid_amount":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El monto debe ser mayor a cero.",
            ) from exc
        if detail == "store_credit_insufficient_balance":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Saldo insuficiente en la nota de crédito.",
            ) from exc
        if detail == "store_credit_cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La nota de crédito fue cancelada.",
            ) from exc
        if detail == "store_credit_expired":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La nota de crédito expiró.",
            ) from exc
        raise
    return schemas.StoreCreditResponse.model_validate(credit)


__all__ = ["router"]
