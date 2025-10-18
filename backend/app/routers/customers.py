"""Router de clientes corporativos."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=list[schemas.CustomerResponse])
def list_customers_endpoint(
    q: str | None = Query(default=None, description="Término de búsqueda"),
    limit: int = Query(default=100, ge=1, le=500),
    export: str | None = Query(default=None, description="Formato de exportación"),
    status_filter: str | None = Query(default=None, description="Filtrar por estado del cliente"),
    customer_type_filter: str | None = Query(default=None, description="Filtrar por tipo de cliente"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        customers = crud.list_customers(
            db,
            query=q,
            limit=limit,
            status=status_filter,
            customer_type=customer_type_filter,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "invalid_customer_status":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estado de cliente inválido.",
            ) from exc
        if detail == "invalid_customer_type":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de cliente inválido.",
            ) from exc
        raise
    if export == "csv":
        csv_content = crud.export_customers_csv(
            db,
            query=q,
            status=status_filter,
            customer_type=customer_type_filter,
        )
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=clientes.csv"},
        )
    return customers


@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer_endpoint(
    payload: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        customer = crud.create_customer(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        if str(exc) == "customer_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente ya existe.",
            ) from exc
        if str(exc) == "invalid_customer_status":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estado de cliente inválido.",
            ) from exc
        if str(exc) == "invalid_customer_type":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de cliente inválido.",
            ) from exc
        if str(exc) == "customer_credit_limit_negative":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El límite de crédito debe ser mayor o igual a cero.",
            ) from exc
        if str(exc) == "customer_outstanding_debt_negative":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El saldo pendiente no puede ser negativo.",
            ) from exc
        if str(exc) == "customer_outstanding_exceeds_limit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El saldo pendiente no puede exceder el límite de crédito configurado.",
            ) from exc
        raise
    return customer


@router.get("/{customer_id}", response_model=schemas.CustomerResponse)
def get_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_customer(db, customer_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc


@router.put("/{customer_id}", response_model=schemas.CustomerResponse)
def update_customer_endpoint(
    customer_id: int,
    payload: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.update_customer(
            db,
            customer_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "invalid_customer_status":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estado de cliente inválido.",
            ) from exc
        if detail == "invalid_customer_type":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de cliente inválido.",
            ) from exc
        if detail == "customer_credit_limit_negative":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El límite de crédito debe ser mayor o igual a cero.",
            ) from exc
        if detail == "customer_outstanding_debt_negative":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El saldo pendiente no puede ser negativo.",
            ) from exc
        if detail == "customer_outstanding_exceeds_limit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El saldo pendiente no puede exceder el límite de crédito configurado.",
            ) from exc
        raise


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        crud.delete_customer(
            db,
            customer_id,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{customer_id}/notes", response_model=schemas.CustomerResponse)
def append_customer_note_endpoint(
    customer_id: int,
    payload: schemas.CustomerNoteCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.append_customer_note(
            db,
            customer_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc


@router.post(
    "/{customer_id}/payments",
    response_model=schemas.CustomerLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer_payment_endpoint(
    customer_id: int,
    payload: schemas.CustomerPaymentCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        ledger_entry = crud.register_customer_payment(
            db,
            customer_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
        return schemas.CustomerLedgerEntryResponse.model_validate(ledger_entry)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "customer_payment_no_debt":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente no tiene saldo pendiente por cobrar.",
            ) from exc
        if detail == "customer_payment_invalid_amount":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El monto del pago es inválido.",
            ) from exc
        if detail == "customer_payment_sale_mismatch":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La venta indicada no corresponde al cliente.",
            ) from exc
        raise


@router.get("/{customer_id}/summary", response_model=schemas.CustomerSummaryResponse)
def get_customer_summary_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_customer_summary(db, customer_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc
