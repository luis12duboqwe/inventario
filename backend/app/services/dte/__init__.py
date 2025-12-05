"""Servicios de generación y seguimiento de Documentos Tributarios Electrónicos."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...core.transactions import transactional_session
from .signature import build_signature


def _ensure_authorization_scope(authorization: models.DTEAuthorization, sale: models.Sale) -> None:
    if not authorization.active:
        raise ValueError("dte_authorization_inactive")
    if authorization.expiration_date < date.today():
        raise ValueError("dte_authorization_expired")
    if authorization.store_id not in (None, sale.store_id):
        raise ValueError("dte_authorization_store_mismatch")


def _format_amount(value: Decimal | float | int) -> str:
    if isinstance(value, Decimal):
        normalized = value.quantize(Decimal("0.01"))
    else:
        normalized = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{normalized:.2f}"


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.replace(tzinfo=None).isoformat() + "Z"


def _extract_customer_tax_id(sale: models.Sale) -> str | None:
    if sale.customer and sale.customer.tax_id:
        return sale.customer.tax_id
    return None


def _extract_customer_name(sale: models.Sale) -> str:
    if sale.customer and sale.customer.name:
        return sale.customer.name
    return sale.customer_name or "Consumidor Final"


def _build_line_items(items: Iterable[models.SaleItem], detail_node: Element) -> None:
    for index, item in enumerate(items, start=1):
        line = SubElement(detail_node, "Linea", numero=str(index))
        description = item.device.name if item.device else f"Artículo #{item.device_id}"
        SubElement(line, "Descripcion").text = description
        SubElement(line, "Cantidad").text = str(item.quantity)
        SubElement(line, "PrecioUnitario").text = _format_amount(item.unit_price)
        SubElement(line, "Descuento").text = _format_amount(item.discount_amount)
        SubElement(line, "Subtotal").text = _format_amount(item.total_line)


def _render_dte_xml(
    *,
    sale: models.Sale,
    authorization: models.DTEAuthorization,
    issuer: schemas.DTEIssuerInfo,
    control_number: str,
    correlative: int,
    signature_serial: str,
    signature_value: str,
) -> str:
    root = Element("DTE")
    root.set("version", "0.1")

    header = SubElement(root, "Encabezado")
    SubElement(header, "NumeroControl").text = control_number
    SubElement(header, "CAI").text = authorization.cai
    SubElement(header, "FechaEmision").text = _format_timestamp(sale.created_at)
    SubElement(header, "FechaLimiteEmision").text = authorization.expiration_date.isoformat()
    SubElement(header, "Sucursal").text = sale.store.name if sale.store else ""
    SubElement(header, "Documento").text = authorization.document_type
    SubElement(header, "Serie").text = authorization.serie
    SubElement(header, "Correlativo").text = str(correlative)

    SubElement(header, "RtnEmisor").text = issuer.rtn
    SubElement(header, "NombreEmisor").text = issuer.name
    SubElement(header, "DireccionEmisor").text = issuer.address

    customer_tax_id = _extract_customer_tax_id(sale)
    SubElement(header, "RtnReceptor").text = customer_tax_id or "0000000000000"
    SubElement(header, "NombreReceptor").text = _extract_customer_name(sale)

    SubElement(header, "Subtotal").text = _format_amount(sale.subtotal_amount)
    SubElement(header, "Impuesto").text = _format_amount(sale.tax_amount)
    SubElement(header, "Total").text = _format_amount(sale.total_amount)

    detail = SubElement(root, "Detalle")
    _build_line_items(sale.items, detail)

    totals = SubElement(root, "Totales")
    SubElement(totals, "Subtotal").text = _format_amount(sale.subtotal_amount)
    SubElement(totals, "Impuesto").text = _format_amount(sale.tax_amount)
    SubElement(totals, "Total").text = _format_amount(sale.total_amount)

    signature_node = SubElement(root, "Firma")
    SubElement(signature_node, "NumeroControl").text = control_number
    SubElement(signature_node, "SerieCertificado").text = signature_serial
    SubElement(signature_node, "Valor").text = signature_value

    return tostring(root, encoding="utf-8").decode("utf-8")


def generate_document(
    db: Session,
    payload: schemas.DTEGenerationRequest,
    *,
    performed_by_id: int | None = None,
) -> models.DTEDocument:
    """Genera y registra un DTE firmado para la venta indicada."""

    with transactional_session(db):
        sale = crud.get_sale(db, payload.sale_id)
        authorization = crud.get_dte_authorization(db, payload.authorization_id)
        _ensure_authorization_scope(authorization, sale)

        correlative = crud.reserve_dte_folio(db, authorization)
        control_number = f"{authorization.serie}-{correlative:08d}"
        signature_value = build_signature(
            control_number=control_number,
            cai=authorization.cai,
            total=sale.total_amount,
            private_key=payload.signer.private_key,
        )
        xml_content = _render_dte_xml(
            sale=sale,
            authorization=authorization,
            issuer=payload.issuer,
            control_number=control_number,
            correlative=correlative,
            signature_serial=payload.signer.certificate_serial,
            signature_value=signature_value,
        )
        reference_code = f"{authorization.cai}-{correlative:08d}"

        document = crud.register_dte_document(
            db,
            sale=sale,
            authorization=authorization,
            xml_content=xml_content,
            signature=signature_value,
            control_number=control_number,
            correlative=correlative,
            reference_code=reference_code,
        )

        crud.log_dte_event(
            db,
            document=document,
            event_type="generated",
            status=document.status,
            detail=f"Documento firmado con certificado {payload.signer.certificate_serial}",
            performed_by_id=performed_by_id,
        )

        if payload.offline:
            crud.enqueue_dte_dispatch(
                db,
                document=document,
                error_message=None,
            )
            crud.log_dte_event(
                db,
                document=document,
                event_type="queued_offline",
                status=document.status,
                detail="Documento encolado por modo offline.",
                performed_by_id=performed_by_id,
            )

        db.flush()
        db.refresh(document, attribute_names=["events", "dispatch_entries"])
        return document


def record_dispatch(
    db: Session,
    document: models.DTEDocument,
    payload: schemas.DTEDispatchRequest,
    *,
    performed_by_id: int | None = None,
) -> models.DTEDispatchQueue | None:
    """Registra la acción de envío del documento."""

    with transactional_session(db):
        if payload.mode == "OFFLINE":
            queue_entry = crud.enqueue_dte_dispatch(
                db,
                document=document,
                error_message=payload.error_message,
            )
            crud.log_dte_event(
                db,
                document=document,
                event_type="queued_offline",
                status=document.status,
                detail=payload.error_message or "Documento encolado para envío diferido.",
                performed_by_id=performed_by_id,
            )
            db.refresh(document, attribute_names=["dispatch_entries"])
            return queue_entry

        queue_entry = crud.mark_dte_dispatch_sent(
            db,
            document=document,
            error_message=payload.error_message,
        )
        crud.log_dte_event(
            db,
            document=document,
            event_type="dispatched",
            status=document.status,
            detail=payload.error_message or "Documento enviado al SAR.",
            performed_by_id=performed_by_id,
        )
        db.refresh(document, attribute_names=["dispatch_entries"])
        return queue_entry


def register_acknowledgement(
    db: Session,
    document: models.DTEDocument,
    payload: schemas.DTEAckRegistration,
    *,
    performed_by_id: int | None = None,
) -> models.DTEDocument:
    """Registra el acuse o respuesta del SAR para el documento."""

    received_at = payload.received_at or datetime.now(timezone.utc)
    with transactional_session(db):
        updated_document = crud.register_dte_ack(
            db,
            document=document,
            status=payload.status,
            code=payload.code,
            detail=payload.detail,
            received_at=received_at,
        )
        crud.log_dte_event(
            db,
            document=updated_document,
            event_type="acknowledged",
            status=payload.status,
            detail=payload.detail or "Acuse registrado manualmente.",
            performed_by_id=performed_by_id,
        )
        db.flush()
        db.refresh(updated_document, attribute_names=["events"])
        return updated_document


__all__ = [
    "generate_document",
    "record_dispatch",
    "register_acknowledgement",
]
