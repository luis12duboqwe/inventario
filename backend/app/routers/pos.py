"""Endpoints dedicados al punto de venta con control de stock y recibos."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Literal, Mapping

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import (
    async_jobs,
    cash_register,
    cash_reports,
    credit,
    notifications,
    payments,
    pos_receipts,
    promotions,
)
from ..services.hardware import hardware_channels, receipt_printer_service

router = APIRouter(prefix="/pos", tags=["pos"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


def _sale_display_payload(sale: object) -> dict[str, object]:
    items_payload: list[dict[str, object]] = []
    for item in getattr(sale, "items", []) or []:
        name = getattr(getattr(item, "device", None), "name", None) or getattr(
            item, "description", None
        )
        items_payload.append(
            {
                "device_id": getattr(item, "device_id", None),
                "name": name or f"Producto #{getattr(item, 'device_id', 'N/D')}",
                "quantity": getattr(item, "quantity", 0),
                "unit_price": float(getattr(item, "unit_price", 0)),
                "total": float(getattr(item, "total_line", 0)),
            }
        )
    total_amount = getattr(sale, "total_amount", None)
    created_at = getattr(sale, "created_at", None)
    created_at_iso = None
    if isinstance(created_at, datetime):
        created_at_iso = created_at.astimezone(timezone.utc).isoformat()
    return {
        "id": getattr(sale, "id", None),
        "items": items_payload,
        "total": float(total_amount) if total_amount is not None else None,
        "created_at": created_at_iso,
    }


def _queue_hardware_events(
    background_tasks: BackgroundTasks,
    sale: object,
    payment_method: object,
    hardware_config: schemas.POSHardwareSettings,
    *,
    payment_breakdown: Mapping[str, float] | None = None,
    escpos_ticket: str | None = None,
    receipt_pdf_base64: str | None = None,
) -> None:
    normalized_method = (
        payment_method.value
        if isinstance(payment_method, schemas.PaymentMethod)
        else str(payment_method)
    ).upper()
    store_id = getattr(sale, "store_id", None)
    should_open_drawer = (
        hardware_config.cash_drawer.enabled
        and hardware_config.cash_drawer.auto_open_on_cash_sale
    )
    if payment_breakdown:
        cash_amount = payment_breakdown.get(schemas.PaymentMethod.EFECTIVO.value)
        should_open_drawer = should_open_drawer and cash_amount is not None and cash_amount > 0
    if store_id is not None and should_open_drawer:
        if normalized_method == schemas.PaymentMethod.EFECTIVO.value or payment_breakdown:
            drawer_event: dict[str, object] = {
                "event": "cash_drawer.open",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "pulse_duration_ms": hardware_config.cash_drawer.pulse_duration_ms,
            }
            if hardware_config.cash_drawer.connector:
                drawer_event["connector"] = hardware_config.cash_drawer.connector.model_dump()
            hardware_channels.schedule_broadcast(background_tasks, store_id, drawer_event)

    if store_id is not None and hardware_config.customer_display.enabled:
        sale_payload = _sale_display_payload(sale)
        display_event: dict[str, object] = {
            "event": "customer_display.sale",
            "headline": f"Ticket #{sale_payload['id']}",
            "sale": sale_payload,
            "total": sale_payload["total"],
        }
        hardware_channels.schedule_broadcast(background_tasks, store_id, display_event)

    if store_id is not None and hardware_config.printers:
        printer = next((p for p in hardware_config.printers if p.is_default), None)
        if printer is None:
            printer = hardware_config.printers[0]
        receipt_event: dict[str, object] = {
            "event": "receipt.print",
            "sale_id": getattr(sale, "id", None),
            "store_id": store_id,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "printer": printer.model_dump(),
            "formats": {},
        }
        if receipt_pdf_base64:
            receipt_event["formats"]["pdf_base64"] = receipt_pdf_base64
        if escpos_ticket:
            receipt_event["formats"]["escpos_commands"] = escpos_ticket
        if receipt_event["formats"]:
            hardware_channels.schedule_broadcast(background_tasks, store_id, receipt_event)


@router.post(
    "/sale",
    response_model=schemas.POSSaleResponse,
    status_code=status.HTTP_201_CREATED
)
def register_pos_sale_endpoint(
    payload: schemas.POSSaleRequest,
    background_tasks: BackgroundTasks,
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
        config = crud.get_pos_config(db, normalized_payload.store_id)
        promotions_config = promotions.load_config(config.promotions_config)
        global_enabled = settings.enable_pos_promotions
        switches = promotions.resolve_feature_switches(
            global_volume=global_enabled and settings.enable_pos_promotions_volume,
            global_combo=global_enabled and settings.enable_pos_promotions_combo,
            global_coupon=global_enabled and settings.enable_pos_promotions_coupons,
            config_flags=promotions_config.feature_flags,
        )
        promo_result = promotions.apply_promotions(
            normalized_payload,
            config=promotions_config,
            switches=switches,
        )
        adjusted_payload = promo_result.sale_request

        electronic_results: list[schemas.POSElectronicPaymentResult] = []
        if normalized_payload.payments:
            terminals_config = {
                key: dict(value)
                for key, value in settings.pos_payment_terminals.items()
            }
            try:
                electronic_results = payments.process_electronic_payments(
                    db,
                    payments=normalized_payload.payments,
                    payload=normalized_payload,
                    user_id=current_user.id if current_user else None,
                    terminals_config=terminals_config,
                )
            except payments.ElectronicPaymentError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(exc),
                ) from exc

        sale, warnings, debt_context, loyalty_summary = crud.register_pos_sale(
            db,
            adjusted_payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
        sale_detail = crud.get_sale(db, sale.id)
        sale_schema = schemas.SaleResponse.model_validate(sale_detail)
        applied_promotions = promotions.summarize_applications(
            sale_schema,
            promo_result.applications,
        )
        config = crud.get_pos_config(db, sale_detail.store_id)
        snapshot = None
        schedule_data: list[dict[str, object]] = []
        debt_summary: schemas.CustomerDebtSnapshot | None = None
        credit_schedule: list[schemas.CreditScheduleEntry] = []
        debt_receipt_pdf_base64: str | None = None
        payment_receipts: list[schemas.CustomerPaymentReceiptResponse] = []

        if debt_context:
            snapshot = debt_context.get("snapshot")
            schedule_data = list(debt_context.get("schedule") or [])
            if snapshot is not None:
                debt_summary = schemas.CustomerDebtSnapshot(
                    previous_balance=snapshot.previous_balance,
                    new_charges=snapshot.new_charges,
                    payments_applied=snapshot.payments_applied,
                    remaining_balance=snapshot.remaining_balance,
                )
            credit_schedule = [
                schemas.CreditScheduleEntry.model_validate(entry)
                for entry in schedule_data
            ]
            payment_outcomes = debt_context.get("payments") or []
            for outcome in payment_outcomes:
                payment_snapshot = credit.build_debt_snapshot(
                    previous_balance=outcome.previous_debt,
                    new_charges=Decimal("0"),
                    payments_applied=outcome.applied_amount,
                )
                payment_schedule = credit.build_credit_schedule(
                    base_date=outcome.ledger_entry.created_at,
                    remaining_balance=payment_snapshot.remaining_balance,
                )
                payment_receipts.append(
                    schemas.CustomerPaymentReceiptResponse(
                        ledger_entry=schemas.CustomerLedgerEntryResponse.model_validate(
                            outcome.ledger_entry
                        ),
                        debt_summary=schemas.CustomerDebtSnapshot(
                            previous_balance=payment_snapshot.previous_balance,
                            new_charges=payment_snapshot.new_charges,
                            payments_applied=payment_snapshot.payments_applied,
                            remaining_balance=payment_snapshot.remaining_balance,
                        ),
                        credit_schedule=[
                            schemas.CreditScheduleEntry.model_validate(entry)
                            for entry in payment_schedule
                        ],
                        receipt_pdf_base64=pos_receipts.render_debt_receipt_base64(
                            outcome.customer,
                            outcome.ledger_entry,
                            payment_snapshot,
                            payment_schedule,
                        ),
                    )
                )

        receipt_pdf = pos_receipts.render_receipt_base64(
            sale_detail,
            config,
            debt_snapshot=snapshot,
            schedule=schedule_data,
        )
        escpos_ticket = pos_receipts.render_receipt_escpos(
            sale_detail,
            config,
            debt_snapshot=snapshot,
            schedule=schedule_data,
        )
        if snapshot is not None:
            debt_receipt_pdf_base64 = receipt_pdf
        hardware_config = schemas.POSHardwareSettings.model_validate(
            config.hardware_settings
        )
        _queue_hardware_events(
            background_tasks,
            sale_detail,
            normalized_payload.payment_method,
            hardware_config,
            payment_breakdown={
                key.upper(): float(value)
                for key, value in (adjusted_payload.payment_breakdown or {}).items()
            }
            if adjusted_payload.payment_breakdown
            else None,
            escpos_ticket=escpos_ticket,
            receipt_pdf_base64=receipt_pdf,
        )
        return schemas.POSSaleResponse(
            status="registered",
            sale=sale_detail,
            warnings=warnings,
            receipt_url=f"/pos/receipt/{sale.id}",
            cash_session_id=sale.cash_session_id,
            payment_breakdown=
            {
                key: float(Decimal(str(value)))
                for key, value in adjusted_payload.payment_breakdown.items()
            }
            if adjusted_payload.payment_breakdown
            else {},
            receipt_pdf_base64=receipt_pdf,
            applied_promotions=applied_promotions,
            debt_summary=debt_summary,
            credit_schedule=credit_schedule,
            debt_receipt_pdf_base64=debt_receipt_pdf_base64,
            payment_receipts=payment_receipts,
            electronic_payments=electronic_results,
            loyalty_summary=loyalty_summary,
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
        if detail == "loyalty_requires_customer":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para canjear puntos debes asignar un cliente.",
            ) from exc
        if detail == "loyalty_insufficient_points":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El cliente no tiene puntos suficientes para el canje solicitado.",
            ) from exc
        if detail == "loyalty_redemption_disabled":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El canje de puntos está deshabilitado para esta cuenta.",
            ) from exc
        if detail == "loyalty_invalid_redeem_amount":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El monto en puntos a canjear es inválido.",
            ) from exc
        if detail == "loyalty_redemption_rate_invalid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La tasa de canje configurada no es válida.",
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
        if detail == "store_credit_requires_customer":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asocia un cliente para aplicar notas de crédito.",
            ) from exc
        if detail == "store_credit_insufficient_balance":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La suma de notas de crédito supera el saldo disponible.",
            ) from exc
        if detail == "store_credit_invalid_amount":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El monto de la nota de crédito debe ser mayor a cero.",
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
    snapshot = None
    schedule_data: list[dict[str, object]] = []
    if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO:
        remaining = Decimal(sale.customer.outstanding_debt or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        new_charge = Decimal(sale.total_amount or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        previous_balance = (remaining - new_charge).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if previous_balance < Decimal("0"):
            previous_balance = Decimal("0.00")
        snapshot = credit.build_debt_snapshot(
            previous_balance=previous_balance,
            new_charges=new_charge,
            payments_applied=Decimal("0"),
        )
        schedule_data = credit.build_credit_schedule(
            base_date=sale.created_at,
            remaining_balance=snapshot.remaining_balance,
        )
    pdf_bytes = pos_receipts.render_receipt_pdf(
        sale,
        config,
        debt_snapshot=snapshot,
        schedule=schedule_data,
    )  # // [PACK34-receipt]
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


@router.post(
    "/receipt/{sale_id}/send",
    response_model=schemas.POSReceiptDeliveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_pos_receipt(
    sale_id: int,
    payload: schemas.POSReceiptDeliveryRequest,
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
            detail="Venta no encontrada",
        ) from exc

    config = crud.get_pos_config(db, sale.store_id)
    pdf_bytes = pos_receipts.render_receipt_pdf(sale, config)
    document_number = f"{config.invoice_prefix}-{sale.id:06d}"
    receipt_filename = f"recibo_{document_number}.pdf"
    receipt_path = f"/pos/receipt/{sale.id}"

    try:
        if payload.channel is schemas.POSReceiptDeliveryChannel.EMAIL:
            subject = payload.subject or f"Recibo {document_number}"
            body = payload.message or (
                "Hola, adjuntamos tu comprobante de compra "
                f"{document_number}."
            )
            attachment = notifications.Attachment(
                filename=receipt_filename,
                content=pdf_bytes,
                content_type="application/pdf",
            )
            notifications.send_email_notification(
                recipients=[payload.recipient],
                subject=subject,
                body=body,
                attachments=[attachment],
            )
        else:
            message = payload.message or (
                "Gracias por tu compra. Recibo "
                f"{document_number}: {receipt_path}"
            )
            await notifications.send_whatsapp_message(
                to_number=payload.recipient,
                message=message,
                media_url=None,
                reference=document_number,
            )
    except notifications.EmailNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío por correo no está configurado.",
        ) from exc
    except notifications.WhatsAppNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío por WhatsApp no está configurado.",
        ) from exc
    except notifications.NotificationDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible entregar la notificación.",
        ) from exc

    crud.register_pos_receipt_delivery(
        db,
        sale_id=sale.id,
        performed_by_id=current_user.id if current_user else None,
        reason=reason,
        channel=payload.channel.value,
        recipient=payload.recipient,
    )

    return schemas.POSReceiptDeliveryResponse(
        channel=payload.channel,
        status="sent",
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
                disposition=item.disposition,
                warehouse_id=item.warehouse_id,
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
        if detail == "sale_return_invalid_warehouse":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selecciona un almacén válido para la devolución.",
            ) from exc
        raise

    return schemas.POSReturnResponse(
        sale_id=sale.id,
        return_ids=[sale_return.id for sale_return in returns],
        notes=payload.reason,
        dispositions=[sale_return.disposition for sale_return in returns],
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
    snapshot = None
    schedule_data: list[dict[str, object]] = []
    debt_summary = None
    if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO:
        remaining = Decimal(sale.customer.outstanding_debt or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        new_charge = Decimal(sale.total_amount or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        previous_balance = (remaining - new_charge).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if previous_balance < Decimal("0"):
            previous_balance = Decimal("0.00")
        snapshot = credit.build_debt_snapshot(
            previous_balance=previous_balance,
            new_charges=new_charge,
            payments_applied=Decimal("0"),
        )
        schedule_data = credit.build_credit_schedule(
            base_date=sale.created_at,
            remaining_balance=snapshot.remaining_balance,
        )
        debt_summary = schemas.CustomerDebtSnapshot(
            previous_balance=snapshot.previous_balance,
            new_charges=snapshot.new_charges,
            payments_applied=snapshot.payments_applied,
            remaining_balance=snapshot.remaining_balance,
        )
    receipt_pdf = pos_receipts.render_receipt_base64(
        sale,
        config,
        debt_snapshot=snapshot,
        schedule=schedule_data,
    )
    credit_schedule = [
        schemas.CreditScheduleEntry.model_validate(entry)
        for entry in schedule_data
    ]
    return schemas.POSSaleDetailResponse(
        sale=sale,
        receipt_url=f"/pos/receipt/{sale.id}",
        receipt_pdf_base64=receipt_pdf,
        debt_summary=debt_summary,
        credit_schedule=credit_schedule,
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


@router.post(
    "/hardware/print-test",
    response_model=schemas.POSHardwareActionResponse,
)
async def trigger_pos_print_test(
    payload: schemas.POSHardwarePrintTestRequest,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    config = crud.get_pos_config(db, payload.store_id)
    hardware_config = schemas.POSHardwareSettings.model_validate(
        config.hardware_settings
    )
    if not hardware_config.printers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay impresoras registradas en la sucursal.",
        )
    printer = None
    if payload.printer_name:
        printer = next(
            (
                item
                for item in hardware_config.printers
                if item.name.lower() == payload.printer_name.lower()
            ),
            None,
        )
    if printer is None:
        printer = next((item for item in hardware_config.printers if item.is_default), None)
    if printer is None:
        printer = hardware_config.printers[0]
    result = await receipt_printer_service.print_sample(
        printer.model_dump(),
        sample=payload.sample,
        metadata={
            "mode": payload.mode.value,
            "requested_by": current_user.id if current_user else None,
            "reason": reason,
        },
    )
    crud.log_audit_event(
        db,
        action="pos_fiscal_print" if payload.mode is schemas.POSPrinterMode.FISCAL else "pos_print_test",
        entity_type="pos_fiscal_print",
        entity_id=printer.name,
        performed_by_id=current_user.id if current_user else None,
        details={
            "sucursal_id": payload.store_id,
            "modo": payload.mode.value,
            "resultado": result.success,
            "mensaje": result.message,
        },
    )
    status_value = "ok" if result.success else "error"
    return schemas.POSHardwareActionResponse(
        status=status_value,
        message=result.message,
        details=result.payload,
    )


@router.post(
    "/hardware/drawer/open",
    response_model=schemas.POSHardwareActionResponse,
)
def trigger_cash_drawer_open(
    payload: schemas.POSHardwareDrawerOpenRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    config = crud.get_pos_config(db, payload.store_id)
    hardware_config = schemas.POSHardwareSettings.model_validate(
        config.hardware_settings
    )
    if not hardware_config.cash_drawer.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La gaveta de efectivo no está habilitada en la sucursal.",
        )
    drawer_event: dict[str, object] = {
        "event": "cash_drawer.open",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "pulse_duration_ms": payload.pulse_duration_ms
        or hardware_config.cash_drawer.pulse_duration_ms,
        "triggered_by": current_user.id if current_user else None,
        "reason": reason,
    }
    connector = hardware_config.cash_drawer.connector
    if payload.connector_identifier:
        drawer_event["connector"] = {
            "identifier": payload.connector_identifier,
        }
    elif connector:
        drawer_event["connector"] = connector.model_dump()
    hardware_channels.schedule_broadcast(background_tasks, payload.store_id, drawer_event)
    return schemas.POSHardwareActionResponse(
        status="queued",
        message="Apertura de gaveta encolada.",
        details=drawer_event,
    )


@router.post(
    "/hardware/display/push",
    response_model=schemas.POSHardwareActionResponse,
)
def push_customer_display_event(
    payload: schemas.POSHardwareDisplayPushRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    config = crud.get_pos_config(db, payload.store_id)
    hardware_config = schemas.POSHardwareSettings.model_validate(
        config.hardware_settings
    )
    if not hardware_config.customer_display.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La pantalla de cliente no está habilitada en la sucursal.",
        )
    event_payload: dict[str, object] = {
        "event": "customer_display.message",
        "headline": payload.headline,
        "message": payload.message,
        "total": payload.total_amount,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "triggered_by": current_user.id if current_user else None,
        "reason": reason,
    }
    hardware_channels.schedule_broadcast(background_tasks, payload.store_id, event_payload)
    return schemas.POSHardwareActionResponse(
        status="queued",
        message="Mensaje enviado a pantallas de cliente.",
        details=event_payload,
    )


@router.websocket("/hardware/ws")
async def hardware_events_websocket(
    websocket: WebSocket,
    store_id: int = Query(..., alias="storeId", ge=1),
):
    await hardware_channels.connect(store_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                await hardware_channels.handle_incoming(store_id, websocket, message)
    except WebSocketDisconnect:
        await hardware_channels.disconnect(store_id, websocket)


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


@router.get(
    "/promotions",
    response_model=schemas.POSPromotionsResponse
)
def read_pos_promotions(
    store_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        response = crud.get_pos_promotions(db, store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sucursal no encontrada",
        ) from exc
    _ = reason  # motivo registrado en middleware y auditoría
    return response


@router.put(
    "/promotions",
    response_model=schemas.POSPromotionsResponse
)
def update_pos_promotions_endpoint(
    payload: schemas.POSPromotionsUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        response = crud.update_pos_promotions(
            db,
            payload,
            updated_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sucursal no encontrada",
        ) from exc
    return response


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
        if str(exc) == "difference_reason_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Indica un motivo para la diferencia registrada.",
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


@router.get(
    "/cash/history/paginated",
    response_model=schemas.POSSessionPageResponse,
)
def list_cash_sessions_paginated(
    store_id: int = Query(..., ge=1),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    total, sessions = crud.paginate_cash_sessions(
        db,
        store_id=store_id,
        page=page,
        size=size,
    )
    _ = reason
    summaries = [cash_register.to_summary(session) for session in sessions]
    return schemas.POSSessionPageResponse(
        items=summaries,
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/cash/recover",
    response_model=schemas.POSSessionSummary,
)
def recover_cash_session_endpoint(
    store_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        summary = cash_register.recover_open_session(db, store_id=store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay sesiones abiertas para recuperar en la sucursal.",
        ) from exc
    _ = reason
    return summary


@router.post(
    "/cash/register/entries",
    response_model=schemas.CashRegisterEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_register_entry(
    payload: schemas.CashRegisterEntryCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        entry = cash_register.record_entry(
            db,
            payload,
            created_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "cash_session_not_open":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La caja indicada no está abierta.",
            ) from exc
        raise
    return entry


@router.get(
    "/cash/register/entries",
    response_model=list[schemas.CashRegisterEntryResponse],
)
def list_cash_register_entries(
    session_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        crud.get_cash_session(db, session_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        ) from exc
    return cash_register.list_entries(db, session_id=session_id)


@router.get(
    "/cash/register/{session_id}/report",
    response_model=schemas.CashSessionResponse,
)
def get_cash_register_report(
    session_id: int,
    export: Literal["json", "pdf"] = Query(default="json"),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        session = crud.get_cash_session(db, session_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        ) from exc
    entries = cash_register.list_entries(db, session_id=session.id)
    if export == "pdf":
        pdf_bytes = cash_reports.render_cash_close_pdf(session, entries)
        buffer = BytesIO(pdf_bytes)
        filename = f"cierre_caja_{session_id}.pdf"
        headers = {"Content-Disposition": f"attachment; filename={filename}"}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
    session_payload = schemas.CashSessionResponse.model_validate(
        session,
        from_attributes=True,
    )
    serialized_entries = [
        schemas.CashRegisterEntryResponse.model_validate(
            entry,
            from_attributes=True,
        )
        for entry in entries
    ]
    return session_payload.model_copy(update={"entries": serialized_entries})


@router.post(
    "/cash/register/{session_id}/report/async",
    response_model=schemas.AsyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_cash_register_report(
    session_id: int,
    run_inline: bool = Query(default=False),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        crud.get_cash_session(db, session_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        ) from exc
    job = async_jobs.enqueue_cash_report(session_id)
    if run_inline:
        job = async_jobs.run_cash_report_job(job.id)
    elif background_tasks is not None:
        background_tasks.add_task(async_jobs.run_cash_report_job, job.id)
    _ = reason
    return schemas.AsyncJobResponse.model_validate(async_jobs.job_to_payload(job))


@router.get(
    "/cash/report/jobs/{job_id}",
    response_model=schemas.AsyncJobResponse,
)
def get_cash_report_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        job = async_jobs.get_job(job_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        ) from exc
    _ = db, reason, current_user  # mantener auditoría y compatibilidad
    return schemas.AsyncJobResponse.model_validate(async_jobs.job_to_payload(job))
