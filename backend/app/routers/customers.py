"""Router de clientes corporativos."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import credit, customer_segments, pos_receipts
from ..services import credit, customer_reports, pos_receipts

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=list[schemas.CustomerResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_customers_endpoint(
    q: str | None = Query(default=None, description="Término de búsqueda"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_alias: str | None = Query(default=None, alias="status", description="Estado corporativo"),
    customer_type_alias: str | None = Query(default=None, alias="customer_type", description="Tipo de cliente"),
    has_debt: bool | None = Query(
        default=None, description="Filtra clientes con (true) o sin (false) saldo"
    ),
    export: str | None = Query(default=None, description="Formato de exportación"),
    status_filter: str | None = Query(
        default=None, alias="status_filter", description="Filtrar por estado del cliente"
    ),
    customer_type_filter: str | None = Query(
        default=None, alias="customer_type_filter", description="Filtrar por tipo de cliente"
    ),
    segment_category: str | None = Query(
        default=None,
        alias="segment_category",
        description="Filtrar por categoría de segmentación",
    ),
    tags: list[str] | None = Query(
        default=None,
        description="Filtra clientes que contengan todas las etiquetas indicadas",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    status_value = status_filter or status_alias
    customer_type_value = customer_type_filter or customer_type_alias
    try:
        customers = crud.list_customers(
            db,
            query=q,
            limit=limit,
            offset=offset,
            status=status_value,
            customer_type=customer_type_value,
            has_debt=has_debt,
            segment_category=segment_category,
            tags=tags,
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
        if detail == "customer_tax_id_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El RTN del cliente es inválido o demasiado corto.",
            ) from exc
        raise
    if export == "csv":
        csv_content = crud.export_customers_csv(
            db,
            query=q,
            status=status_value,
            customer_type=customer_type_value,
            segment_category=segment_category,
            tags=tags,
        )
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=clientes.csv"},
        )
    return customers


@router.get("/dashboard", response_model=schemas.CustomerDashboardMetrics, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_customer_dashboard_metrics_endpoint(
    months: int = Query(default=6, ge=1, le=24),
    top_limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    return crud.get_customer_dashboard_metrics(db, months=months, top_limit=top_limit)


@router.get(
    "/segments/export",
    dependencies=[Depends(require_roles(*GESTION_ROLES)), Depends(require_reason)],
)
def export_customer_segment_endpoint(
    segment: str = Query(
        ..., min_length=3, description="Clave del segmento a exportar"
    ),
    export_format: str = Query(
        default="csv", description="Formato de exportación (actualmente CSV)"
    ),
    db: Session = Depends(get_db),
):
    try:
        filename, content, media_type = customer_segments.export_segment(
            db,
            segment_key=segment,
            export_format=export_format,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "unknown_segment":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Segmento desconocido.",
            ) from exc
        if detail == "unsupported_format":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Formato de exportación no soportado.",
            ) from exc
        raise
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*GESTION_ROLES))])
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
        if str(exc) == "customer_tax_id_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El RTN del cliente es inválido o demasiado corto.",
            ) from exc
        if str(exc) == "customer_tax_id_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El RTN del cliente ya está registrado.",
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


@router.get("/{customer_id}", response_model=schemas.CustomerResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_customer(db, customer_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc


@router.put("/{customer_id}", response_model=schemas.CustomerResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
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
        if detail == "customer_tax_id_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El RTN del cliente es inválido o demasiado corto.",
            ) from exc
        if detail == "customer_tax_id_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El RTN del cliente ya está registrado.",
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


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
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


@router.post("/{customer_id}/notes", response_model=schemas.CustomerResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
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
    response_model=schemas.CustomerPaymentReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def register_customer_payment_endpoint(
    customer_id: int,
    payload: schemas.CustomerPaymentCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        outcome = crud.register_customer_payment(
            db,
            customer_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
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


@router.get("/{customer_id}/summary", response_model=schemas.CustomerSummaryResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def get_customer_summary_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_customer_summary(db, customer_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado") from exc


@router.get(
    "/{customer_id}/accounts-receivable",
    response_model=schemas.CustomerAccountsReceivableResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_customer_accounts_receivable_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_customer_accounts_receivable(db, customer_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        ) from exc


@router.get(
    "/{customer_id}/accounts-receivable/statement.pdf",
    response_model=None,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def download_customer_statement_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    del reason  # motivo registrado a nivel middleware/auditoría
    try:
        report = crud.build_customer_statement_report(db, customer_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        ) from exc
    pdf_bytes = customer_reports.render_customer_statement_pdf(report)
    filename = f"estado_cuenta_cliente_{customer_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
