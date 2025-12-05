"""Operaciones CRUD para proveedores (Suppliers)."""
from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from .audit import log_audit_event as _log_action
from .devices import _recalculate_sale_price
from .stores import get_store, recalculate_store_inventory_value as _recalculate_store_inventory_value


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


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
            parsed_timestamp = datetime.now(timezone.utc).isoformat()
        normalized.append({"timestamp": parsed_timestamp,
                          "note": (note or "").strip()})
    return normalized


def _contacts_to_json(
    contacts: list[schemas.SupplierContact] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    if not contacts:
        return normalized
    for contact in contacts:
        if isinstance(contact, schemas.SupplierContact):
            payload = contact.model_dump(exclude_none=True)
        elif isinstance(contact, Mapping):
            payload = {
                key: value
                for key, value in contact.items()
                if isinstance(key, str)
            }
        else:
            continue
        record: dict[str, object] = {}
        for key in ("name", "position", "email", "phone", "notes"):
            value = payload.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value:
                record[key] = value
        if record:
            normalized.append(record)
    return normalized


def _products_to_json(products: Sequence[str] | None) -> list[str]:
    if not products:
        return []
    normalized: list[str] = []
    for product in products:
        text = (product or "").strip()
        if not text:
            continue
        if text not in normalized:
            normalized.append(text)
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


_RTN_CANONICAL_TEMPLATE = "{0}-{1}-{2}"


def _normalize_rtn(value: str | None, *, error_code: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) != 14:
        raise ValueError(error_code)
    return _RTN_CANONICAL_TEMPLATE.format(digits[:4], digits[4:8], digits[8:])


def _get_supplier_by_name(
    db: Session, supplier_name: str | None
) -> models.Supplier | None:
    if not supplier_name:
        return None
    normalized = supplier_name.strip().lower()
    if not normalized:
        return None
    statement = (
        select(models.Supplier)
        .where(func.lower(models.Supplier.name) == normalized)
    )
    return db.scalars(statement).first()


def list_suppliers(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Supplier]:
    statement = (
        select(models.Supplier)
        .where(models.Supplier.is_deleted.is_(False))
        .order_by(models.Supplier.name.asc())
        .offset(offset)
        .limit(limit)
    )
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Supplier.name).like(normalized),
                func.lower(models.Supplier.contact_name).like(normalized),
                func.lower(models.Supplier.email).like(normalized),
                func.lower(models.Supplier.phone).like(normalized),
                func.lower(models.Supplier.rtn).like(normalized),
                func.lower(models.Supplier.payment_terms).like(normalized),
                func.lower(models.Supplier.notes).like(normalized),
            )
        )
    return list(db.scalars(statement))


def get_supplier(db: Session, supplier_id: int) -> models.Supplier:
    statement = select(models.Supplier).where(
        models.Supplier.id == supplier_id,
        models.Supplier.is_deleted.is_(False),
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("supplier_not_found") from exc


def create_supplier(
    db: Session,
    payload: schemas.SupplierCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Supplier:
    history = _history_to_json(payload.history)
    normalized_rtn = None
    if payload.rtn:
        normalized_rtn = _normalize_rtn(
            payload.rtn, error_code="supplier_rtn_invalid")
    supplier = models.Supplier(
        name=payload.name,
        rtn=normalized_rtn,
        payment_terms=payload.payment_terms,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        contact_info=_contacts_to_json(payload.contact_info),
        address=payload.address,
        notes=payload.notes,
        history=history,
        outstanding_debt=_to_decimal(payload.outstanding_debt),
        products_supplied=_products_to_json(payload.products_supplied),
    )
    try:
        with transactional_session(db):
            db.add(supplier)
            flush_session(db)

            _log_action(
                db,
                action="supplier_created",
                entity_type="supplier",
                entity_id=str(supplier.id),
                performed_by_id=performed_by_id,
                details=json.dumps({"name": supplier.name}),
            )

            db.refresh(supplier)
    except IntegrityError as exc:
        raise ValueError("supplier_already_exists") from exc
    return supplier


def update_supplier(
    db: Session,
    supplier_id: int,
    payload: schemas.SupplierUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Supplier:
    supplier = get_supplier(db, supplier_id)
    updated_fields: dict[str, object] = {}
    if payload.name is not None:
        supplier.name = payload.name
        updated_fields["name"] = payload.name
    if payload.rtn is not None:
        supplier.rtn = (
            _normalize_rtn(payload.rtn, error_code="supplier_rtn_invalid")
            if payload.rtn
            else None
        )
        updated_fields["rtn"] = supplier.rtn
    if payload.payment_terms is not None:
        supplier.payment_terms = payload.payment_terms
        updated_fields["payment_terms"] = payload.payment_terms
    if payload.contact_name is not None:
        supplier.contact_name = payload.contact_name
        updated_fields["contact_name"] = payload.contact_name
    if payload.email is not None:
        supplier.email = payload.email
        updated_fields["email"] = payload.email
    if payload.phone is not None:
        supplier.phone = payload.phone
        updated_fields["phone"] = payload.phone
    if payload.address is not None:
        supplier.address = payload.address
        updated_fields["address"] = payload.address
    if payload.notes is not None:
        supplier.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.outstanding_debt is not None:
        supplier.outstanding_debt = _to_decimal(payload.outstanding_debt)
        updated_fields["outstanding_debt"] = float(supplier.outstanding_debt)
    if payload.history is not None:
        history = _history_to_json(payload.history)
        supplier.history = history
        updated_fields["history"] = history
    if payload.contact_info is not None:
        contacts = _contacts_to_json(payload.contact_info)
        supplier.contact_info = contacts
        updated_fields["contact_info"] = contacts
    if payload.products_supplied is not None:
        products = _products_to_json(payload.products_supplied)
        supplier.products_supplied = products
        updated_fields["products_supplied"] = products
    with transactional_session(db):
        db.add(supplier)
        flush_session(db)

        if updated_fields:
            _log_action(
                db,
                action="supplier_updated",
                entity_type="supplier",
                entity_id=str(supplier.id),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )

        db.refresh(supplier)
    return supplier


def delete_supplier(
    db: Session,
    supplier_id: int,
    *,
    performed_by_id: int | None = None,
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    supplier = get_supplier(db, supplier_id)
    has_dependencies = bool(supplier.batches or supplier.ledger_entries)
    should_hard_delete = allow_hard_delete and (
        not has_dependencies or is_superadmin)
    with transactional_session(db):
        if should_hard_delete:
            db.delete(supplier)

            _log_action(
                db,
                action="supplier_deleted",
                entity_type="supplier",
                entity_id=str(supplier_id),
                performed_by_id=performed_by_id,
            )
            return

        supplier.is_deleted = True
        supplier.deleted_at = datetime.now(timezone.utc)
        _log_action(
            db,
            action="supplier_archived",
            entity_type="supplier",
            entity_id=str(supplier_id),
            performed_by_id=performed_by_id,
        )


def get_suppliers_accounts_payable(
    db: Session,
) -> schemas.SupplierAccountsPayableResponse:
    suppliers = list(
        db.scalars(select(models.Supplier).order_by(
            models.Supplier.name.asc()))
    )

    bucket_defs: list[tuple[str, int, int | None]] = [
        ("0-30 días", 0, 30),
        ("31-60 días", 31, 60),
        ("61-90 días", 61, 90),
        ("90+ días", 91, None),
    ]
    bucket_totals: list[dict[str, object]] = [
        {"label": label, "from": start, "to": end,
            "amount": Decimal("0.00"), "count": 0}
        for label, start, end in bucket_defs
    ]

    total_balance = Decimal("0.00")
    total_overdue = Decimal("0.00")
    items: list[schemas.SupplierAccountsPayableSupplier] = []
    today = datetime.now(timezone.utc).date()

    for supplier in suppliers:
        balance = _to_decimal(supplier.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        history = (
            supplier.history
            if isinstance(supplier.history, list)
            else []
        )
        last_history = _last_history_timestamp(history)
        last_activity = last_history or supplier.updated_at or supplier.created_at

        days_outstanding = 0
        if last_activity is not None:
            days_outstanding = max(
                (today - last_activity.date()).days,
                0,
            )

        bucket_index = 0
        for idx, (_, start, end) in enumerate(bucket_defs):
            if end is None or days_outstanding <= end:
                if end is None or days_outstanding >= start:
                    bucket_index = idx
                    break

        bucket = bucket_totals[bucket_index]
        bucket["amount"] = _to_decimal(
            bucket["amount"]) + balance  # type: ignore[index]
        if balance > Decimal("0"):
            bucket["count"] = int(bucket["count"]) + 1  # type: ignore[index]

        total_balance += balance
        if days_outstanding > 30:
            total_overdue += balance

        contact_name = supplier.contact_name
        contact_email = supplier.email
        contact_phone = supplier.phone
        if not contact_name and supplier.contact_info:
            # Intentar obtener el primer contacto
            contacts = supplier.contact_info
            if isinstance(contacts, list) and contacts:
                first = contacts[0]
                if isinstance(first, dict):
                    contact_name = str(first.get("name") or "")
                    contact_email = str(first.get("email") or "")
                    contact_phone = str(first.get("phone") or "")

        items.append(
            schemas.SupplierAccountsPayableSupplier(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                rtn=supplier.rtn,
                payment_terms=supplier.payment_terms,
                outstanding_debt=float(balance),
                bucket_label=str(bucket["label"]),
                bucket_from=int(bucket["from"]),  # type: ignore
                # type: ignore
                bucket_to=int(
                    bucket["to"]) if bucket["to"] is not None else None,
                days_outstanding=days_outstanding,
                last_activity=last_activity,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                products_supplied=supplier.products_supplied or [],
                contact_info=[schemas.SupplierContact(
                    **c) for c in (supplier.contact_info or [])] if isinstance(supplier.contact_info, list) else [],
            )
        )

    # Construct buckets objects
    summary_buckets = []
    total_amount_buckets = sum(float(b["amount"])
                               for b in bucket_totals)  # type: ignore

    for b in bucket_totals:
        amount = float(b["amount"])  # type: ignore
        percentage = (amount / total_amount_buckets *
                      100) if total_amount_buckets > 0 else 0.0
        summary_buckets.append(
            schemas.SupplierAccountsPayableBucket(
                label=str(b["label"]),
                days_from=int(b["from"]),  # type: ignore
                # type: ignore
                days_to=int(b["to"]) if b["to"] is not None else None,
                amount=amount,
                percentage=percentage,
                count=int(b["count"])  # type: ignore
            )
        )

    summary = schemas.SupplierAccountsPayableSummary(
        total_balance=float(total_balance),
        total_overdue=float(total_overdue),
        supplier_count=len(items),
        generated_at=datetime.now(timezone.utc),
        buckets=summary_buckets
    )

    return schemas.SupplierAccountsPayableResponse(
        summary=summary,
        suppliers=items,
    )


def export_suppliers_csv(db: Session, *, query: str | None = None) -> str:
    suppliers = list_suppliers(db, query=query, limit=10000)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "RTN",
            "Contacto",
            "Email",
            "Teléfono",
            "Dirección",
            "Deuda Pendiente",
            "Productos Suministrados",
        ]
    )
    for supplier in suppliers:
        writer.writerow(
            [
                supplier.id,
                supplier.name,
                supplier.rtn or "",
                supplier.contact_name or "",
                supplier.email or "",
                supplier.phone or "",
                supplier.address or "",
                f"{_to_decimal(supplier.outstanding_debt):.2f}",
                ", ".join(_products_to_json(supplier.products_supplied)),
            ]
        )
    return buffer.getvalue()


def list_supplier_batches(
    db: Session, supplier_id: int, *, limit: int = 50, offset: int = 0
) -> list[models.SupplierBatch]:
    supplier = get_supplier(db, supplier_id)
    statement = (
        select(models.SupplierBatch)
        .where(models.SupplierBatch.supplier_id == supplier.id)
        .order_by(models.SupplierBatch.purchase_date.desc(), models.SupplierBatch.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def get_supplier_batch_overview(
    db: Session,
    *,
    store_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    batch_filter = or_(
        models.SupplierBatch.store_id == store_id,
        models.SupplierBatch.store_id.is_(None),
    )

    latest_rank = func.row_number().over(
        partition_by=models.SupplierBatch.supplier_id,
        order_by=(
            models.SupplierBatch.purchase_date.desc(),
            models.SupplierBatch.created_at.desc(),
        ),
    )

    ranked_batches = (
        select(
            models.SupplierBatch.supplier_id.label("supplier_id"),
            models.SupplierBatch.batch_code.label("latest_batch_code"),
            models.SupplierBatch.unit_cost.label("latest_unit_cost"),
            latest_rank.label("batch_rank"),
        )
        .where(batch_filter)
    ).subquery()

    latest_batches = (
        select(
            ranked_batches.c.supplier_id,
            ranked_batches.c.latest_batch_code,
            ranked_batches.c.latest_unit_cost,
        )
        .where(ranked_batches.c.batch_rank == 1)
    ).subquery()

    aggregated = (
        select(
            models.SupplierBatch.supplier_id.label("supplier_id"),
            models.Supplier.name.label("supplier_name"),
            func.count().label("batch_count"),
            func.sum(models.SupplierBatch.quantity).label("total_quantity"),
            func.sum(
                models.SupplierBatch.quantity * models.SupplierBatch.unit_cost
            ).label("total_value"),
            func.max(models.SupplierBatch.purchase_date).label(
                "latest_purchase_date"
            ),
        )
        .join(models.Supplier, models.Supplier.id == models.SupplierBatch.supplier_id)
        .where(batch_filter)
        .group_by(models.SupplierBatch.supplier_id, models.Supplier.name)
    ).subquery()

    statement = (
        select(
            aggregated.c.supplier_id,
            aggregated.c.supplier_name,
            aggregated.c.batch_count,
            aggregated.c.total_quantity,
            aggregated.c.total_value,
            aggregated.c.latest_purchase_date,
            latest_batches.c.latest_batch_code,
            latest_batches.c.latest_unit_cost,
        )
        .join(
            latest_batches,
            latest_batches.c.supplier_id == aggregated.c.supplier_id,
            isouter=True,
        )
        .order_by(
            aggregated.c.latest_purchase_date.desc(),
            aggregated.c.total_value.desc(),
        )
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

    rows = db.execute(statement).all()

    result: list[dict[str, object]] = []
    for row in rows:
        total_value = Decimal(row.total_value or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        latest_unit_cost = row.latest_unit_cost
        result.append(
            {
                "supplier_id": row.supplier_id,
                "supplier_name": row.supplier_name,
                "batch_count": int(row.batch_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": float(total_value),
                "latest_purchase_date": row.latest_purchase_date,
                "latest_batch_code": row.latest_batch_code,
                "latest_unit_cost": float(latest_unit_cost)
                if latest_unit_cost is not None
                else None,
            }
        )

    return result


def count_supplier_batch_overview(db: Session, *, store_id: int) -> int:
    statement = (
        select(func.count(func.distinct(models.SupplierBatch.supplier_id)))
        .where(
            or_(
                models.SupplierBatch.store_id == store_id,
                models.SupplierBatch.store_id.is_(None),
            )
        )
    )
    total = db.scalar(statement)
    return int(total or 0)


def create_supplier_batch(
    db: Session,
    supplier_id: int,
    payload: schemas.SupplierBatchCreate,
    *,
    performed_by_id: int | None = None,
) -> models.SupplierBatch:
    supplier = get_supplier(db, supplier_id)
    store = get_store(db, payload.store_id) if payload.store_id else None
    device: models.Device | None = None
    if payload.device_id:
        device = db.get(models.Device, payload.device_id)
        if device is None:
            raise LookupError("device_not_found")
        if store is not None and device.store_id != store.id:
            raise ValueError("supplier_batch_store_mismatch")
        if store is None:
            store = device.store

    with transactional_session(db):
        batch = models.SupplierBatch(
            supplier_id=supplier.id,
            store_id=store.id if store else None,
            device_id=device.id if device else None,
            model_name=payload.model_name or (device.name if device else ""),
            batch_code=payload.batch_code,
            unit_cost=_to_decimal(payload.unit_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP),
            quantity=payload.quantity,
            purchase_date=payload.purchase_date,
            notes=payload.notes,
        )
        now = datetime.now(timezone.utc)
        batch.created_at = now
        batch.updated_at = now
        db.add(batch)

        if device is not None:
            device.proveedor = supplier.name
            device.lote = payload.batch_code or device.lote
            device.fecha_compra = payload.purchase_date
            device.costo_unitario = batch.unit_cost
            _recalculate_sale_price(device)
            db.add(device)

        flush_session(db)
        db.refresh(batch)

        if device is not None:
            _recalculate_store_inventory_value(db, device.store_id)

        _log_action(
            db,
            action="supplier_batch_created",
            entity_type="supplier_batch",
            entity_id=str(batch.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"supplier_id": supplier.id,
                               "batch_code": batch.batch_code}),
        )
        flush_session(db)
        db.refresh(batch)
    return batch


def update_supplier_batch(
    db: Session,
    batch_id: int,
    payload: schemas.SupplierBatchUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.SupplierBatch:
    statement = select(models.SupplierBatch).where(
        models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")

    updated_fields: dict[str, object] = {}

    with transactional_session(db):
        if payload.model_name is not None:
            batch.model_name = payload.model_name
            updated_fields["model_name"] = payload.model_name
        if payload.batch_code is not None:
            batch.batch_code = payload.batch_code
            updated_fields["batch_code"] = payload.batch_code
        if payload.unit_cost is not None:
            batch.unit_cost = _to_decimal(payload.unit_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
            updated_fields["unit_cost"] = float(batch.unit_cost)
        if payload.quantity is not None:
            batch.quantity = payload.quantity
            updated_fields["quantity"] = payload.quantity
        if payload.purchase_date is not None:
            batch.purchase_date = payload.purchase_date
            updated_fields["purchase_date"] = batch.purchase_date.isoformat()
        if payload.notes is not None:
            batch.notes = payload.notes
            updated_fields["notes"] = payload.notes
        if payload.store_id is not None:
            store = get_store(db, payload.store_id)
            batch.store_id = store.id
            updated_fields["store_id"] = store.id
        if payload.device_id is not None:
            if payload.device_id:
                device = db.get(models.Device, payload.device_id)
                if device is None:
                    raise LookupError("device_not_found")
                batch.device_id = device.id
                updated_fields["device_id"] = device.id
            else:
                batch.device_id = None
                updated_fields["device_id"] = None

        batch.updated_at = datetime.now(timezone.utc)

        db.add(batch)
        flush_session(db)
        db.refresh(batch)

        if updated_fields:
            _log_action(
                db,
                action="supplier_batch_updated",
                entity_type="supplier_batch",
                entity_id=str(batch.id),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )
            flush_session(db)
            db.refresh(batch)
    return batch


def delete_supplier_batch(
    db: Session,
    batch_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    statement = select(models.SupplierBatch).where(
        models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")
    store_id = batch.store_id
    with transactional_session(db):
        db.delete(batch)
        flush_session(db)
        if store_id:
            _recalculate_store_inventory_value(db, store_id)
        _log_action(
            db,
            action="supplier_batch_deleted",
            entity_type="supplier_batch",
            entity_id=str(batch_id),
            performed_by_id=performed_by_id,
        )
        flush_session(db)
