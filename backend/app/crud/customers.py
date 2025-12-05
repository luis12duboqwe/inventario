"""Operaciones CRUD para el módulo de Clientes."""
from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence, Any
from datetime import datetime

from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from .common import to_decimal as _to_decimal, log_audit_event as _log_action
from .sync import enqueue_sync_outbox


def _customer_payload(customer: models.Customer) -> dict[str, object]:
    return {
        "id": customer.id,
        "name": customer.name,
        "contact_name": customer.contact_name,
        "email": customer.email,
        "phone": customer.phone,
        "customer_type": customer.customer_type,
        "status": customer.status,
        "segment_category": customer.segment_category,
        "tags": customer.tags,
        "tax_id": customer.tax_id,
        "credit_limit": float(customer.credit_limit or Decimal("0")),
        "outstanding_debt": float(customer.outstanding_debt or Decimal("0")),
        "last_interaction_at": customer.last_interaction_at.isoformat() if customer.last_interaction_at else None,
        "privacy_consents": dict(customer.privacy_consents or {}),
        "privacy_metadata": dict(customer.privacy_metadata or {}),
        "privacy_last_request_at": customer.privacy_last_request_at.isoformat()
        if customer.privacy_last_request_at
        else None,
        "updated_at": customer.updated_at.isoformat(),
        "annual_purchase_amount": float(customer.annual_purchase_amount),
        "orders_last_year": customer.orders_last_year,
        "purchase_frequency": customer.purchase_frequency,
        "segment_labels": list(customer.segment_labels),
        "last_purchase_at": customer.last_purchase_at.isoformat()
        if customer.last_purchase_at
        else None,
    }


def _history_to_json(
    entries: list[schemas.ContactHistoryEntry] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    if not entries:
        return normalized
    for entry in entries:
        if isinstance(entry, schemas.ContactHistoryEntry):
            timestamp = entry.timestamp
            note = entry.note
        else:
            timestamp = entry.get("timestamp")  # type: ignore[assignment]
            note = entry.get("note") if isinstance(entry, dict) else None
        if isinstance(timestamp, str):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, datetime):
            parsed_timestamp = timestamp.isoformat()
        else:
            parsed_timestamp = datetime.utcnow().isoformat()
        normalized.append({"timestamp": parsed_timestamp,
                          "note": (note or "").strip()})
    return normalized


def _last_history_timestamp(history: list[dict[str, object]]) -> datetime | None:
    timestamps = []
    for entry in history:
        raw_timestamp = entry.get("timestamp")
        if isinstance(raw_timestamp, datetime):
            timestamps.append(raw_timestamp)
        elif isinstance(raw_timestamp, str):
            try:
                timestamps.append(datetime.fromisoformat(raw_timestamp))
            except ValueError:
                continue
    if not timestamps:
        return None
    return max(timestamps)


def _append_customer_history(customer: models.Customer, note: str) -> None:
    history = list(customer.history or [])
    history.append({"timestamp": datetime.utcnow().isoformat(), "note": note})
    customer.history = history
    customer.last_interaction_at = datetime.utcnow()


def _mask_email(value: str) -> str:
    email = (value or "").strip()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    local = local.strip()
    domain = domain.strip() or "anon.invalid"
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = f"{local[0]}*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


def _mask_phone(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if not digits:
        return "***"
    if len(digits) <= 4:
        visible = digits[-1:] if digits else ""
        return f"{'*' * max(0, len(digits) - 1)}{visible}"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def _mask_person_name(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    parts = text.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + "*")
        else:
            masked_parts.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked_parts)


def _mask_generic_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}***{text[-2:]}"


def _apply_customer_anonymization(
    customer: models.Customer, fields: Sequence[str]
) -> list[str]:
    normalized: list[str] = []
    for raw in fields or []:
        text = str(raw or "").strip().lower()
        if text and text not in normalized:
            normalized.append(text)

    masked: list[str] = []
    for field in normalized:
        if field == "name" and customer.name:
            customer.name = _mask_person_name(customer.name)
            masked.append("name")
        elif field == "contact_name" and customer.contact_name:
            customer.contact_name = _mask_person_name(customer.contact_name)
            masked.append("contact_name")
        elif field == "email" and customer.email:
            customer.email = _mask_email(customer.email)
            masked.append("email")
        elif field == "phone" and customer.phone:
            customer.phone = _mask_phone(customer.phone)
            masked.append("phone")
        elif field == "address" and customer.address:
            customer.address = _mask_generic_text(customer.address)
            masked.append("address")
        elif field == "notes" and customer.notes:
            customer.notes = _mask_generic_text(customer.notes)
            masked.append("notes")
        elif field == "tax_id" and customer.tax_id:
            customer.tax_id = _mask_generic_text(customer.tax_id)
            masked.append("tax_id")

    if "history" in normalized and customer.history:
        history_entries = list(customer.history or [])
        customer.history = [
            {
                "timestamp": entry.get("timestamp"),
                "note": "***",
            }
            for entry in history_entries
        ]
        masked.append("history")

    return masked


_ALLOWED_CUSTOMER_STATUSES = {
    "activo", "inactivo", "moroso", "vip", "bloqueado"}
_ALLOWED_CUSTOMER_TYPES = {"minorista", "mayorista", "corporativo"}


def _normalize_customer_status(value: str | None) -> str:
    normalized = (value or "activo").strip().lower()
    if normalized not in _ALLOWED_CUSTOMER_STATUSES:
        raise ValueError("invalid_customer_status")
    return normalized


def _normalize_customer_type(value: str | None) -> str:
    normalized = (value or "minorista").strip().lower()
    if normalized not in _ALLOWED_CUSTOMER_TYPES:
        raise ValueError("invalid_customer_type")
    return normalized


def _normalize_customer_segment_category(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_customer_tags(tags: Sequence[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


_RTN_CANONICAL_TEMPLATE = "{0}-{1}-{2}"


def _normalize_rtn(value: str | None, *, error_code: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) != 14:
        raise ValueError(error_code)
    return _RTN_CANONICAL_TEMPLATE.format(digits[:4], digits[4:8], digits[8:])


def _generate_customer_tax_id_placeholder() -> str:
    placeholder = models.generate_customer_tax_id_placeholder()
    return _normalize_rtn(placeholder, error_code="customer_tax_id_invalid")


def _normalize_customer_tax_id(
    value: str | None, *, allow_placeholder: bool = True
) -> str:
    cleaned = (value or "").strip()
    if cleaned:
        return _normalize_rtn(cleaned, error_code="customer_tax_id_invalid")
    if allow_placeholder:
        return _generate_customer_tax_id_placeholder()
    raise ValueError("customer_tax_id_invalid")


def _is_tax_id_integrity_error(error: IntegrityError) -> bool:
    message = str(getattr(error, "orig", error)).lower()
    return "rtn" in message or "tax_id" in message or "segmento_etiquetas" in message


def _ensure_non_negative_decimal(value: Decimal, error_code: str) -> Decimal:
    normalized = _to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    if normalized < Decimal("0"):
        raise ValueError(error_code)
    return normalized


def _ensure_positive_decimal(value: Decimal, error_code: str) -> Decimal:
    normalized = _to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized <= Decimal("0"):
        raise ValueError(error_code)
    return normalized


def _ensure_debt_respects_limit(credit_limit: Decimal, outstanding: Decimal) -> None:
    """Valida que el saldo pendiente no supere el límite de crédito configurado."""

    normalized_limit = _to_decimal(credit_limit).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    normalized_outstanding = _to_decimal(outstanding).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized_outstanding <= Decimal("0"):
        return
    if normalized_limit <= Decimal("0"):
        raise ValueError("customer_outstanding_exceeds_limit")
    if normalized_outstanding > normalized_limit:
        raise ValueError("customer_outstanding_exceeds_limit")


def _validate_customer_credit(customer: models.Customer, pending_charge: Decimal) -> None:
    amount = _to_decimal(pending_charge)
    if amount <= Decimal("0"):
        return
    limit = _to_decimal(customer.credit_limit)
    if limit <= Decimal("0"):
        raise ValueError("customer_credit_limit_exceeded")
    projected = (_to_decimal(customer.outstanding_debt) + amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if projected > limit:
        raise ValueError("customer_credit_limit_exceeded")


def _customer_ledger_payload(entry: models.CustomerLedgerEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "customer_id": entry.customer_id,
        "entry_type": entry.entry_type.value,
        "reference_type": entry.reference_type,
        "reference_id": entry.reference_id,
        "amount": float(entry.amount),
        "balance_after": float(entry.balance_after),
        "note": entry.note,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(),
        "created_by_id": entry.created_by_id,
    }


def _create_customer_ledger_entry(
    db: Session,
    *,
    customer: models.Customer,
    entry_type: models.CustomerLedgerEntryType,
    amount: Decimal,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    details: dict[str, object] | None = None,
    created_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    entry = models.CustomerLedgerEntry(
        customer_id=customer.id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        amount=_to_decimal(amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=_to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    flush_session(db)
    return entry


def _sync_customer_ledger_entry(db: Session, entry: models.CustomerLedgerEntry) -> None:
    with transactional_session(db):
        db.refresh(entry)
        db.refresh(entry, attribute_names=["created_by"])
        enqueue_sync_outbox(
            db,
            entity_type="customer_ledger_entry",
            entity_id=str(entry.id),
            operation="UPSERT",
            payload=_customer_ledger_payload(entry),
        )


def list_customers(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    customer_type: str | None = None,
    has_debt: bool | None = None,
    segment_category: str | None = None,
    tags: Sequence[str] | None = None,
) -> list[models.Customer]:
    statement = (
        select(models.Customer)
        .options(selectinload(models.Customer.loyalty_account))
        .options(selectinload(models.Customer.segment_snapshot))
        .where(models.Customer.is_deleted.is_(False))
        .order_by(models.Customer.name.asc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        normalized_status = _normalize_customer_status(status)
        statement = statement.where(
            models.Customer.status == normalized_status)
    if customer_type:
        normalized_type = _normalize_customer_type(customer_type)
        statement = statement.where(
            models.Customer.customer_type == normalized_type)
    if segment_category:
        normalized_category = _normalize_customer_segment_category(
            segment_category)
        if normalized_category:
            statement = statement.where(
                models.Customer.segment_category == normalized_category
            )
    normalized_tags = _normalize_customer_tags(tags)
    if normalized_tags:
        tags_column = func.lower(cast(models.Customer.tags, String))
        for tag in normalized_tags:
            statement = statement.where(tags_column.like(f'%"{tag}"%'))
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Customer.name).like(normalized),
                func.lower(models.Customer.contact_name).like(normalized),
                func.lower(models.Customer.email).like(normalized),
                func.lower(models.Customer.phone).like(normalized),
                func.lower(models.Customer.customer_type).like(normalized),
                func.lower(models.Customer.status).like(normalized),
                func.lower(func.coalesce(models.Customer.segment_category, "")).like(
                    normalized),
                func.lower(func.coalesce(models.Customer.notes, "")
                           ).like(normalized),
                func.lower(cast(models.Customer.tags, String)
                           ).like(normalized),
                func.lower(func.coalesce(models.Customer.tax_id, "")
                           ).like(normalized),
            )
        )
    if has_debt is True:
        statement = statement.where(models.Customer.outstanding_debt > 0)
    elif has_debt is False:
        statement = statement.where(models.Customer.outstanding_debt <= 0)
    return list(db.scalars(statement))


def get_customer(db: Session, customer_id: int) -> models.Customer:
    statement = (
        select(models.Customer)
        .options(selectinload(models.Customer.loyalty_account))
        .options(selectinload(models.Customer.segment_snapshot))
        .options(selectinload(models.Customer.privacy_requests))
        .where(
            models.Customer.id == customer_id,
            models.Customer.is_deleted.is_(False),
        )
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("customer_not_found") from exc


def create_customer(
    db: Session,
    payload: schemas.CustomerCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Customer:
    with transactional_session(db):
        history = _history_to_json(payload.history)
        customer_type = _normalize_customer_type(payload.customer_type)
        status = _normalize_customer_status(payload.status)
        segment_category = _normalize_customer_segment_category(
            payload.segment_category
        )
        tags = _normalize_customer_tags(payload.tags)
        tax_id = _normalize_customer_tax_id(payload.tax_id)
        credit_limit = _ensure_non_negative_decimal(
            payload.credit_limit, "customer_credit_limit_negative"
        )
        outstanding_debt = _ensure_non_negative_decimal(
            payload.outstanding_debt, "customer_outstanding_debt_negative"
        )
        _ensure_debt_respects_limit(credit_limit, outstanding_debt)
        customer = models.Customer(
            name=payload.name,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            customer_type=customer_type,
            status=status,
            segment_category=segment_category,
            tags=tags,
            tax_id=tax_id,
            credit_limit=credit_limit,
            notes=payload.notes,
            history=history,
            outstanding_debt=outstanding_debt,
            last_interaction_at=_last_history_timestamp(history),
        )
        db.add(customer)
        try:
            flush_session(db)
        except IntegrityError as exc:
            if _is_tax_id_integrity_error(exc):
                raise ValueError("customer_tax_id_duplicate") from exc
            raise ValueError("customer_already_exists") from exc
        db.refresh(customer)

        _log_action(
            db,
            action="customer_created",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps({
                "name": customer.name,
                "tax_id": customer.tax_id,
                "segment_category": customer.segment_category,
                "tags": customer.tags,
            }),
        )
        flush_session(db)
        db.refresh(customer)
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
    return customer


def update_customer(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Customer:
    customer = get_customer(db, customer_id)
    with transactional_session(db):
        previous_outstanding = _to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        updated_fields: dict[str, object] = {}
        outstanding_delta: Decimal | None = None
        ledger_entry: models.CustomerLedgerEntry | None = None
        ledger_details: dict[str, object] | None = None
        pending_history_note: str | None = None
        pending_ledger_entry_kwargs: dict[str, object] | None = None
        if payload.name is not None:
            customer.name = payload.name
            updated_fields["name"] = payload.name
        if payload.contact_name is not None:
            customer.contact_name = payload.contact_name
            updated_fields["contact_name"] = payload.contact_name
        if payload.email is not None:
            customer.email = payload.email
            updated_fields["email"] = payload.email
        if payload.phone is not None:
            customer.phone = payload.phone
            updated_fields["phone"] = payload.phone
        if payload.address is not None:
            customer.address = payload.address
            updated_fields["address"] = payload.address
        if payload.customer_type is not None:
            normalized_type = _normalize_customer_type(payload.customer_type)
            customer.customer_type = normalized_type
            updated_fields["customer_type"] = normalized_type
        if payload.status is not None:
            normalized_status = _normalize_customer_status(payload.status)
            customer.status = normalized_status
            updated_fields["status"] = normalized_status
        if payload.tax_id is not None:
            normalized_tax_id = _normalize_customer_tax_id(
                payload.tax_id, allow_placeholder=False
            )
            customer.tax_id = normalized_tax_id
            updated_fields["tax_id"] = normalized_tax_id
        if payload.segment_category is not None:
            normalized_category = _normalize_customer_segment_category(
                payload.segment_category
            )
            customer.segment_category = normalized_category
            updated_fields["segment_category"] = normalized_category
        if payload.tags is not None:
            normalized_tags = _normalize_customer_tags(payload.tags)
            customer.tags = normalized_tags
            updated_fields["tags"] = normalized_tags
        if payload.credit_limit is not None:
            customer.credit_limit = _ensure_non_negative_decimal(
                payload.credit_limit, "customer_credit_limit_negative"
            )
            updated_fields["credit_limit"] = float(customer.credit_limit)
        if payload.notes is not None:
            customer.notes = payload.notes
            updated_fields["notes"] = payload.notes
        if payload.outstanding_debt is not None:
            new_outstanding = _ensure_non_negative_decimal(
                payload.outstanding_debt, "customer_outstanding_debt_negative"
            )
            difference = (new_outstanding - previous_outstanding).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            customer.outstanding_debt = new_outstanding
            updated_fields["outstanding_debt"] = float(new_outstanding)
            if difference != Decimal("0"):
                outstanding_delta = difference
                pending_history_note = (
                    "Ajuste manual de saldo: antes $"
                    f"{float(previous_outstanding):.2f}, ahora ${float(new_outstanding):.2f}"
                )
                ledger_details = {
                    "previous_balance": float(previous_outstanding),
                    "new_balance": float(new_outstanding),
                    "difference": float(difference),
                }
                updated_fields["outstanding_debt_delta"] = float(difference)
                pending_ledger_entry_kwargs = {
                    "entry_type": models.CustomerLedgerEntryType.ADJUSTMENT,
                    "amount": outstanding_delta,
                    "note": pending_history_note,
                    "reference_type": "adjustment",
                    "reference_id": None,
                    "details": ledger_details,
                    "created_by_id": performed_by_id,
                }
            previous_outstanding = new_outstanding
        if payload.history is not None:
            history = _history_to_json(payload.history)
            customer.history = history
            customer.last_interaction_at = _last_history_timestamp(history)
            updated_fields["history"] = history
        _ensure_debt_respects_limit(
            customer.credit_limit, customer.outstanding_debt)
        if pending_history_note:
            _append_customer_history(customer, pending_history_note)
            updated_fields.setdefault("history_note", pending_history_note)
        if pending_ledger_entry_kwargs is not None:
            ledger_entry = _create_customer_ledger_entry(
                db,
                customer=customer,
                **pending_ledger_entry_kwargs,
            )
        db.add(customer)
        try:
            flush_session(db)
        except IntegrityError as exc:
            if _is_tax_id_integrity_error(exc):
                raise ValueError("customer_tax_id_duplicate") from exc
            raise
        db.refresh(customer)

        if ledger_entry is not None:
            _sync_customer_ledger_entry(db, ledger_entry)

        if updated_fields:
            _log_action(
                db,
                action="customer_updated",
                entity_type="customer",
                entity_id=str(customer.id),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )
            flush_session(db)
            db.refresh(customer)
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
    return customer


def delete_customer(
    db: Session,
    customer_id: int,
    *,
    performed_by_id: int | None = None,
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    customer = get_customer(db, customer_id)
    has_dependencies = any(
        [
            customer.sales,
            customer.repair_orders,
            customer.ledger_entries,
            customer.store_credits,
        ]
    )
    should_hard_delete = allow_hard_delete and (
        not has_dependencies or is_superadmin)
    with transactional_session(db):
        if should_hard_delete:
            db.delete(customer)
            flush_session(db)
            _log_action(
                db,
                action="customer_deleted",
                entity_type="customer",
                entity_id=str(customer_id),
                performed_by_id=performed_by_id,
            )
        else:
            customer.is_deleted = True
            db.add(customer)
            flush_session(db)
            _log_action(
                db,
                action="customer_soft_deleted",
                entity_type="customer",
                entity_id=str(customer_id),
                performed_by_id=performed_by_id,
            )
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer_id),
            operation="DELETE",
            payload={"id": customer_id},
        )
