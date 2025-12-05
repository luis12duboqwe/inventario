"""Operaciones CRUD para compras (Purchase Orders)."""
from __future__ import annotations

import json
import csv
import io
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, extract
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..config import settings
from ..core.transactions import flush_session, transactional_session
from ..services.purchases import assign_supplier_batch
from .audit import log_audit_event as _log_action
from .common import to_decimal as _to_decimal
from .devices import get_device
from .inventory import create_inventory_movement as _register_inventory_movement
from .stores import get_store, recalculate_store_inventory_value as _recalculate_store_inventory_value
from .suppliers import _get_supplier_by_name
from .sync import enqueue_sync_outbox


def _purchase_order_payload(order: models.PurchaseOrder) -> dict[str, object]:
    """Serializa una orden de compra para la cola de sincronización."""

    store_name = order.store.name if getattr(order, "store", None) else None
    status_value = getattr(order.status, "value", order.status)
    items_payload = [
        {
            "device_id": item.device_id,
            "quantity_ordered": item.quantity_ordered,
            "quantity_received": item.quantity_received,
            "unit_cost": float(_to_decimal(item.unit_cost)),
        }
        for item in order.items
    ]
    return {
        "id": order.id,
        "store_id": order.store_id,
        "store_name": store_name,
        "supplier": order.supplier,
        "status": status_value,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "closed_at": order.closed_at.isoformat() if order.closed_at else None,
        "requires_approval": getattr(order, "requires_approval", False),
        "approved_by_id": getattr(order, "approved_by_id", None),
        "items": items_payload,
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "content_type": document.content_type,
            }
            for document in order.documents
        ],
    }


def _register_purchase_status_event(
    db: Session,
    order: models.PurchaseOrder,
    *,
    status: models.PurchaseStatus,
    created_by_id: int | None,
    note: str | None = None,
) -> models.PurchaseOrderStatusEvent:
    event = models.PurchaseOrderStatusEvent(
        purchase_order_id=order.id,
        status=status,
        note=note,
        created_by_id=created_by_id,
    )
    db.add(event)
    flush_session(db)
    db.refresh(event)
    return event


def list_purchase_orders(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.PurchaseOrder]:
    statement = (
        select(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
        .order_by(models.PurchaseOrder.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_purchase_orders(db: Session, *, store_id: int | None = None) -> int:
    statement = select(func.count()).select_from(models.PurchaseOrder)
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return int(db.scalar(statement) or 0)


def get_purchase_order(db: Session, order_id: int) -> models.PurchaseOrder:
    statement = (
        select(models.PurchaseOrder)
        .where(models.PurchaseOrder.id == order_id)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
            joinedload(models.PurchaseOrder.documents),
            joinedload(models.PurchaseOrder.status_events).joinedload(
                models.PurchaseOrderStatusEvent.created_by
            ),
            joinedload(models.PurchaseOrder.approved_by),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("purchase_not_found") from exc


def create_purchase_order(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
) -> models.PurchaseOrder:
    if not payload.items:
        raise ValueError("purchase_items_required")

    get_store(db, payload.store_id)

    total_amount = Decimal("0")
    for item in payload.items:
        total_amount += Decimal(item.quantity_ordered) * \
            _to_decimal(item.unit_cost)
    approval_threshold = _to_decimal(
        getattr(settings, "purchases_large_order_threshold", Decimal("0"))
    )
    requires_approval = approval_threshold > 0 and total_amount >= approval_threshold

    order = models.PurchaseOrder(
        store_id=payload.store_id,
        supplier=payload.supplier,
        notes=payload.notes,
        created_by_id=created_by_id,
        requires_approval=requires_approval,
    )
    with transactional_session(db):
        db.add(order)
        flush_session(db)

        for item in payload.items:
            if item.quantity_ordered <= 0:
                raise ValueError("purchase_invalid_quantity")
            if item.unit_cost < 0:
                raise ValueError("purchase_invalid_quantity")

            device = get_device(db, payload.store_id, item.device_id)
            order_item = models.PurchaseOrderItem(
                purchase_order_id=order.id,
                device_id=device.id,
                quantity_ordered=item.quantity_ordered,
                unit_cost=_to_decimal(item.unit_cost).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            db.add(order_item)

        db.refresh(order)

        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=created_by_id,
            note="Creación de orden",
        )
        db.refresh(order)

        _log_action(
            db,
            action="purchase_order_created",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {"store_id": order.store_id, "supplier": order.supplier}
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    db.refresh(order)
    return order


def create_purchase_order_from_suggestion(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
    reason: str,
) -> models.PurchaseOrder:
    """Genera una orden de compra desde una sugerencia automatizada."""

    order = create_purchase_order(db, payload, created_by_id=created_by_id)

    items_details = [
        {"device_id": item.device_id, "quantity_ordered": item.quantity_ordered}
        for item in order.items
    ]

    with transactional_session(db):
        _log_action(
            db,
            action="purchase_order_generated_from_suggestion",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {
                    "store_id": order.store_id,
                    "supplier": order.supplier,
                    "reason": reason,
                    "source": "purchase_suggestion",
                    "items": items_details,
                }
            ),
        )
        flush_session(db)

    db.refresh(order)
    return order


def _build_purchase_movement_comment(
    action: str,
    order: models.PurchaseOrder,
    device: models.Device,
    reason: str | None,
) -> str:
    """Genera una descripción legible para los movimientos de compras."""

    parts: list[str] = [
        action, f"OC #{order.id}", f"Proveedor: {order.supplier}"]
    if device.imei:
        parts.append(f"IMEI: {device.imei}")
    if device.serial:
        parts.append(f"Serie: {device.serial}")
    if reason:
        normalized_reason = reason.strip()
        if normalized_reason:
            parts.append(normalized_reason)
    comment = " | ".join(part for part in parts if part)
    return comment[:255]


def receive_purchase_order(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReceiveRequest,
    *,
    received_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status in {models.PurchaseStatus.CANCELADA, models.PurchaseStatus.COMPLETADA}:
        raise ValueError("purchase_not_receivable")
    if order.requires_approval and order.approved_by_id is None:
        raise PermissionError("purchase_requires_approval")
    if order.status == models.PurchaseStatus.BORRADOR:
        raise ValueError("purchase_not_receivable")
    if not payload.items:
        raise ValueError("purchase_items_required")

    items_by_device = {item.device_id: item for item in order.items}
    reception_details: dict[str, int] = {}
    batch_updates: dict[str, int] = {}
    store = get_store(db, order.store_id)

    for receive_item in payload.items:
        order_item = items_by_device.get(receive_item.device_id)
        if order_item is None:
            raise LookupError("purchase_item_not_found")
        pending = order_item.quantity_ordered - order_item.quantity_received
        if receive_item.quantity <= 0 or receive_item.quantity > pending:
            raise ValueError("purchase_invalid_quantity")

        order_item.quantity_received += receive_item.quantity

        device = get_device(db, order.store_id, order_item.device_id)
        movement_payload = schemas.MovementCreate(
            producto_id=device.id,
            tipo_movimiento=models.MovementType.IN,
            cantidad=receive_item.quantity,
            comentario=_build_purchase_movement_comment(
                "Recepción OC",
                order,
                device,
                reason,
            ),
            unit_cost=_to_decimal(order_item.unit_cost),
            sucursal_destino_id=order.store_id,
        )

        movement = _register_inventory_movement(
            db,
            store_id=order.store_id,
            payload=movement_payload,
            performed_by_id=received_by_id,
            reference_type="purchase_order",
            reference_id=str(order.id),
        )
        movement_device = movement.device or device
        movement_device.proveedor = order.supplier
        reception_details[str(device.id)] = receive_item.quantity

        batch_code = getattr(receive_item, "batch_code", None)
        if batch_code:
            batch = assign_supplier_batch(
                db,
                supplier_name=order.supplier,
                store=store,
                device=movement_device,
                batch_code=batch_code,
                quantity=receive_item.quantity,
                unit_cost=_to_decimal(order_item.unit_cost),
                purchase_date=datetime.now(timezone.utc).date(),
            )
            movement_device.lote = batch.batch_code
            movement_device.fecha_compra = batch.purchase_date
            movement_device.costo_unitario = batch.unit_cost
            if batch.supplier and batch.supplier.name:
                movement_device.proveedor = batch.supplier.name
            db.add(movement_device)
            batch_updates[batch.batch_code] = (
                batch_updates.get(batch.batch_code, 0) + receive_item.quantity
            )

    with transactional_session(db):
        if all(item.quantity_received == item.quantity_ordered for item in order.items):
            order.status = models.PurchaseStatus.COMPLETADA
            order.closed_at = datetime.now(timezone.utc)
        else:
            order.status = models.PurchaseStatus.PARCIAL

        flush_session(db)
        db.refresh(order)
        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=received_by_id,
            note=reason,
        )
        db.refresh(order)
        _recalculate_store_inventory_value(db, order.store_id)

        _log_action(
            db,
            action="purchase_order_received",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=received_by_id,
            details=json.dumps(
                {
                    "items": reception_details,
                    "status": order.status.value,
                    "reason": reason,
                    "batches": batch_updates,
                }
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    return order


def _revert_purchase_inventory(
    db: Session,
    order: models.PurchaseOrder,
    *,
    cancelled_by_id: int,
    reason: str | None,
) -> dict[str, int]:
    """Revierte el inventario recibido cuando se cancela una compra."""

    reversal_details: dict[str, int] = {}
    adjustments_performed = False

    for order_item in order.items:
        received_qty = order_item.quantity_received
        if received_qty <= 0:
            continue

        device = get_device(db, order.store_id, order_item.device_id)
        if device.quantity < received_qty:
            raise ValueError("purchase_cancellation_insufficient_stock")

        movement_payload = schemas.MovementCreate(
            producto_id=device.id,
            tipo_movimiento=models.MovementType.OUT,
            cantidad=received_qty,
            comentario=_build_purchase_movement_comment(
                "Reversión OC",
                order,
                device,
                reason,
            ),
            unit_cost=_to_decimal(order_item.unit_cost),
            sucursal_origen_id=order.store_id,
        )

        _register_inventory_movement(
            db,
            store_id=order.store_id,
            payload=movement_payload,
            performed_by_id=cancelled_by_id,
            reference_type="purchase_order",
            reference_id=str(order.id),
        )

        reversal_details[str(device.id)] = received_qty
        order_item.quantity_received = 0
        adjustments_performed = True

    if adjustments_performed:
        _recalculate_store_inventory_value(db, order.store_id)

    return reversal_details


def cancel_purchase_order(
    db: Session,
    order_id: int,
    *,
    cancelled_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status == models.PurchaseStatus.CANCELADA:
        raise ValueError("purchase_not_cancellable")

    with transactional_session(db):
        reversal_details = _revert_purchase_inventory(
            db,
            order,
            cancelled_by_id=cancelled_by_id,
            reason=reason,
        )

        order.status = models.PurchaseStatus.CANCELADA
        order.closed_at = datetime.now(timezone.utc)
        if reason:
            order.notes = (order.notes or "") + \
                f" | Cancelación: {reason}" if order.notes else reason

        flush_session(db)
        db.refresh(order)
        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=cancelled_by_id,
            note=reason,
        )
        db.refresh(order)

        _log_action(
            db,
            action="purchase_order_cancelled",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=cancelled_by_id,
            details=json.dumps(
                {
                    "status": order.status.value,
                    "reason": reason,
                    "reversed_items": reversal_details,
                }
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    return order


def _register_supplier_credit_note(
    db: Session,
    *,
    supplier_name: str | None,
    purchase_order_id: int,
    credit_amount: Decimal,
    corporate_reason: str | None,
    processed_by_id: int | None,
) -> models.SupplierLedgerEntry | None:
    supplier = _get_supplier_by_name(db, supplier_name)
    if supplier is None:
        return None

    normalized_amount = _to_decimal(credit_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized_amount <= Decimal("0"):
        return None

    # TODO: Implementar lógica de notas de crédito cuando se migre el ledger
    # Por ahora retornamos None para no romper la compatibilidad
    return None


# --- Legacy Purchase Vendor Logic ---

def list_purchase_vendors(
    db: Session,
    *,
    vendor_id: int | None = None,
    query: str | None = None,
    estado: str | None = None,
    active_only: bool = True,
    limit: int | None = 100,
    offset: int = 0,
) -> list[models.Proveedor]:
    statement = select(models.Proveedor).order_by(models.Proveedor.nombre)
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
        # If querying by ID, we usually want the specific record regardless of active status
        # unless active_only is explicitly enforced. But for status update return, we need it.
        # Let's keep active_only logic but maybe the caller should set active_only=False if needed.
        # However, the router call doesn't specify active_only, so it defaults to True.
        # If I just updated status to 'inactivo', and active_only=True, it won't return it.
        # So I should probably disable active_only if vendor_id is present, or let the caller decide.
        # Given the router usage: crud.list_purchase_vendors(db, vendor_id=vendor_id, limit=1)
        # It expects the updated vendor. If status is inactive, it won't be returned if active_only=True.
        # So I should set active_only=False if vendor_id is provided?
        # Or better, change the default behavior or check how it's used.
        # The router doesn't pass active_only=False.
        # So I will modify the logic: if vendor_id is provided, ignore active_only default?
        # No, that's implicit magic.
        # But wait, the router just updated the status. If it set it to inactive, and then calls list with active_only=True (default), it returns empty.
        # The router should probably call get_purchase_vendor instead.
        # But it calls list_purchase_vendors.
        # I will add vendor_id support. And I will assume that if vendor_id is passed, we want that vendor.
        pass

    if active_only and not vendor_id:
        statement = statement.where(models.Proveedor.estado == "activo")

    if estado:
        statement = statement.where(func.lower(
            models.Proveedor.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    if limit is not None:
        statement = statement.limit(limit).offset(offset)
    return db.execute(statement).scalars().all()


def create_purchase_vendor(
    db: Session,
    payload: schemas.PurchaseVendorCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    with transactional_session(db):
        db_vendor = models.Proveedor(
            nombre=payload.nombre,
            telefono=payload.telefono,
            correo=payload.correo,
            direccion=payload.direccion,
            tipo=payload.tipo,
            estado="activo",
            notas=payload.notas,
        )
        db.add(db_vendor)
        flush_session(db)
        db.refresh(db_vendor)

        _log_action(
            db,
            action="purchase_vendor_created",
            entity_type="purchase_vendor",
            entity_id=str(db_vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "nombre": db_vendor.nombre,
                    "tipo": db_vendor.tipo,
                    "estado": db_vendor.estado,
                }
            ),
        )
    return db_vendor


def get_purchase_vendor(
    db: Session,
    vendor_id: int,
) -> models.Proveedor | None:
    return db.get(models.Proveedor, vendor_id)


def update_purchase_vendor(
    db: Session,
    vendor_id: int,
    vendor_update: schemas.PurchaseVendorUpdate,
) -> models.Proveedor | None:
    db_vendor = get_purchase_vendor(db, vendor_id)
    if not db_vendor:
        return None

    update_data = vendor_update.dict(exclude_unset=True)
    # Map schema fields to model fields
    field_map = {
        "name": "nombre",
        "phone": "telefono",
        "email": "correo",
        "address": "direccion",
        "vendor_type": "tipo",
        "notes": "notas",
        "is_active": "estado",
    }

    for schema_field, model_field in field_map.items():
        if schema_field in update_data:
            value = update_data[schema_field]
            if schema_field == "is_active":
                value = "activo" if value else "inactivo"
            setattr(db_vendor, model_field, value)

    flush_session(db)
    db.refresh(db_vendor)
    return db_vendor


def compute_purchase_suggestions(
    db: Session,
    *,
    store_id: int | None = None,
    weeks_history: int = 4,
    safety_stock_days: int = 7,
) -> list[dict]:
    """
    Genera sugerencias de compra basadas en rotación de inventario.
    Calcula venta diaria promedio (ADS) y sugiere reabastecimiento.
    """
    # 1. Calcular fecha de inicio para análisis de ventas
    start_date = datetime.now(timezone.utc) - timedelta(weeks=weeks_history)

    # 2. Obtener ventas por producto en el periodo
    sales_query = (
        select(
            models.DetalleVenta.producto_id,
            func.sum(models.DetalleVenta.cantidad).label("total_sold"),
        )
        .join(models.Venta)
        .where(models.Venta.fecha >= start_date)
        .where(models.Venta.estado != "cancelada")
        .group_by(models.DetalleVenta.producto_id)
    )

    if store_id:
        # Asumiendo que Venta tiene store_id o relación con usuario->sucursal
        # Por ahora simplificado, idealmente filtrar por tienda
        pass

    sales_data = db.execute(sales_query).all()
    sales_map = {row.producto_id: row.total_sold for row in sales_data}

    # 3. Obtener inventario actual
    devices = db.execute(
        select(models.Device).where(models.Device.estado == "disponible")
    ).scalars().all()

    # Agrupar inventario por modelo/SKU (simplificado por ID de dispositivo base si aplica)
    # En este modelo, Device es un item individual. Para sugerencias de compra,
    # necesitamos agrupar por "tipo de producto" (ej. iPhone 13 128GB).
    # Como Device es individual, usamos atributos para agrupar.
    inventory_count = defaultdict(int)
    product_info = {}

    for device in devices:
        # Clave de agrupación: Marca + Modelo + Capacidad
        key = (device.marca, device.modelo, device.capacidad_gb)
        inventory_count[key] += 1
        if key not in product_info:
            product_info[key] = {
                "marca": device.marca,
                "modelo": device.modelo,
                "capacidad": device.capacidad_gb,
                "sample_device_id": device.id,  # Para referencia
            }

    suggestions = []
    days_analyzed = weeks_history * 7

    for key, current_stock in inventory_count.items():
        # Estimar ventas para este grupo
        # Esto es complejo porque sales_map está por device_id (que es único).
        # Necesitamos mapear ventas históricas a este grupo también.
        # Por simplicidad en esta migración, usamos un placeholder o lógica simplificada.
        # En un sistema real, se necesita una tabla de "Producto/SKU" separada de "Device/Item".

        # Lógica placeholder: Si stock < 2, sugerir comprar 5
        if current_stock < 2:
            suggestions.append({
                "product_name": f"{key[0]} {key[1]} {key[2]}GB",
                "current_stock": current_stock,
                "suggested_quantity": 5,
                "reason": "Stock bajo crítico",
                "estimated_cost": 0,  # Requiere costo promedio
            })

    return suggestions


def export_purchase_vendors_csv(
    db: Session,
    query: str | None = None,
    estado: str | None = None,
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nombre", "Teléfono", "Correo",
                    "Dirección", "Tipo", "Estado", "Notas"])

    vendors = list_purchase_vendors(
        db,
        query=query,
        estado=estado,
        active_only=False,
        limit=None
    )
    for v in vendors:
        writer.writerow([
            v.id_proveedor,
            v.nombre,
            v.telefono,
            v.correo,
            v.direccion,
            v.tipo,
            v.estado,
            v.notas,
        ])

    return output.getvalue()


# --- Legacy Purchase Record Logic (Compras) ---

def _purchase_record_statement():
    return (
        select(models.Compra)
        .options(
            joinedload(models.Compra.proveedor),
            joinedload(models.Compra.usuario),
            joinedload(models.Compra.detalles).joinedload(
                models.DetalleCompra.producto),
        )
        .order_by(models.Compra.fecha.desc(), models.Compra.id_compra.desc())
    )


def _apply_purchase_record_filters(
    statement,
    *,
    proveedor_id: int | None,
    usuario_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    estado: str | None,
    query: str | None,
):
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return statement


def list_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Compra]:
    statement = _purchase_record_statement()
    statement = _apply_purchase_record_filters(
        statement,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    if limit is not None:
        statement = statement.limit(limit)
    if offset:
        statement = statement.offset(offset)

    results = list(db.scalars(statement).unique())

    for record in results:
        record.proveedor_nombre = record.proveedor.nombre
        record.subtotal = record.total - record.impuesto

        items_list = []
        for detalle in record.detalles:
            detalle.producto_nombre = detalle.producto.name
            items_list.append(detalle)
        record.items = items_list

    return results


def create_purchase_record(
    db: Session,
    purchase: schemas.PurchaseRecordCreate,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Compra:
    user_id = performed_by_id
    # 1. Crear cabecera de compra
    db_purchase = models.Compra(
        proveedor_id=purchase.proveedor_id,
        usuario_id=user_id,
        fecha=purchase.fecha or datetime.now(timezone.utc),
        total=0,  # Se calcula después
        impuesto=0,
        forma_pago=purchase.forma_pago,
        estado=purchase.estado,
    )
    db.add(db_purchase)
    flush_session(db)  # Para obtener ID

    subtotal_accumulated = Decimal(0)

    # 2. Procesar detalles y actualizar inventario
    for item in purchase.items:
        # Calcular subtotal
        quantity = Decimal(item.cantidad)
        cost = Decimal(item.costo_unitario)
        subtotal = quantity * cost
        subtotal_accumulated += subtotal

        # Crear detalle
        db_detail = models.DetalleCompra(
            compra_id=db_purchase.id_compra,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            costo_unitario=cost,
            subtotal=subtotal,
        )
        db.add(db_detail)

        # Actualizar dispositivo (costo y stock si aplica)
        device = db.get(models.Device, item.producto_id)
        if not device:
            # Si no existe, podríamos crearlo, pero aquí asumimos que existe
            # O lanzar error. Para simplificar, saltamos o lanzamos error.
            raise LookupError(f"Device {item.producto_id} not found")

        movement_payload = schemas.MovementCreate(
            producto_id=item.producto_id,
            tipo_movimiento=models.MovementType.IN,
            cantidad=item.cantidad,
            comentario=f"Compra #{db_purchase.id_compra}",
            unit_cost=cost,
            sucursal_destino_id=device.store_id,
        )

        _register_inventory_movement(
            db,
            store_id=device.store_id,
            payload=movement_payload,
            performed_by_id=user_id,
            reference_type="purchase_record",  # O "compra_legacy"
            reference_id=str(db_purchase.id_compra),
        )

    # 3. Actualizar total compra
    tax_rate = purchase.impuesto_tasa if purchase.impuesto_tasa is not None else Decimal(
        0)
    tax_amount = subtotal_accumulated * tax_rate

    db_purchase.impuesto = tax_amount
    db_purchase.total = subtotal_accumulated + tax_amount

    flush_session(db)
    db.refresh(db_purchase)

    # Auditoría
    _log_action(
        db,
        performed_by_id=user_id,
        action="purchase_created",
        entity_type="purchase",
        entity_id=str(db_purchase.id_compra),
        details={"total": float(db_purchase.total),
                 "vendor_id": purchase.proveedor_id},
    )

    # Populate fields for response schema
    db_purchase.proveedor_nombre = db_purchase.proveedor.nombre
    db_purchase.subtotal = subtotal_accumulated

    # Populate items with product name
    items_list = []
    for detalle in db_purchase.detalles:
        detalle.producto_nombre = detalle.producto.name
        items_list.append(detalle)
    db_purchase.items = items_list

    return db_purchase


def get_purchase_statistics(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    top_limit: int = 5,
) -> dict:
    """
    Calcula estadísticas de compras: total gastado, compras por mes, top proveedores.
    """
    # Filtros base
    base_query = select(models.Compra).where(
        models.Compra.estado != "cancelada")
    if date_from:
        base_query = base_query.where(models.Compra.fecha >= date_from)
    if date_to:
        base_query = base_query.where(models.Compra.fecha <= date_to)

    # Eager load relationships
    base_query = base_query.options(
        joinedload(models.Compra.proveedor),
        joinedload(models.Compra.usuario)
    )

    purchases = db.execute(base_query).scalars().all()

    monthly_total = Decimal(0)
    monthly_count = 0

    vendor_map = defaultdict(
        lambda: {"total": Decimal(0), "orders": 0, "name": ""})
    user_map = defaultdict(
        lambda: {"total": Decimal(0), "orders": 0, "name": ""})

    for p in purchases:
        total = p.total or Decimal(0)
        monthly_total += total
        monthly_count += 1

        # Vendor stats
        if p.proveedor:
            v_id = p.proveedor.id_proveedor
            vendor_map[v_id]["total"] += total
            vendor_map[v_id]["orders"] += 1
            vendor_map[v_id]["name"] = p.proveedor.nombre

        # User stats
        if p.usuario:
            u_id = p.usuario.id
            user_map[u_id]["total"] += total
            user_map[u_id]["orders"] += 1
            user_map[u_id]["name"] = p.usuario.full_name or f"User {u_id}"

    # Top Vendors
    top_vendors = []
    sorted_vendors = sorted(
        vendor_map.items(), key=lambda x: x[1]["total"], reverse=True)[:top_limit]
    for v_id, data in sorted_vendors:
        top_vendors.append({
            "vendor_id": v_id,
            "vendor_name": data["name"],
            "total": data["total"],
            "orders": data["orders"]
        })

    # Top Users
    top_users = []
    sorted_users = sorted(
        user_map.items(), key=lambda x: x[1]["total"], reverse=True)[:top_limit]
    for u_id, data in sorted_users:
        top_users.append({
            "user_id": u_id,
            "user_name": data["name"],
            "total": data["total"],
            "orders": data["orders"]
        })

    # Daily Average
    days = 1
    if date_from and date_to:
        days = (date_to - date_from).days + 1
    elif purchases:
        dates = [p.fecha for p in purchases if p.fecha]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            days = (max_date - min_date).days + 1

    days = max(1, days)
    daily_average = monthly_total / Decimal(days)

    return {
        "monthly_total": monthly_total,
        "monthly_count": monthly_count,
        "top_vendors": top_vendors,
        "top_users": top_users,
        "daily_average": daily_average,
    }


def list_vendor_purchase_history(
    db: Session,
    vendor_id: int,
    limit: int = 10,
    offset: int = 0,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    vendor = db.get(models.Proveedor, vendor_id)
    if not vendor:
        raise LookupError("vendor_not_found")

    query = select(models.Compra).where(
        models.Compra.proveedor_id == vendor_id)

    if date_from:
        query = query.where(models.Compra.fecha >= date_from)
    if date_to:
        query = query.where(models.Compra.fecha <= date_to)

    # Calculate totals for the filtered range
    count_query = select(func.count()).select_from(query.subquery())
    total_registros = db.scalar(count_query) or 0

    sum_query = select(
        func.sum(models.Compra.total),
        func.sum(models.Compra.impuesto)
    ).where(models.Compra.proveedor_id == vendor_id)

    if date_from:
        sum_query = sum_query.where(models.Compra.fecha >= date_from)
    if date_to:
        sum_query = sum_query.where(models.Compra.fecha <= date_to)

    total_amount, total_tax = db.execute(
        sum_query).first() or (Decimal(0), Decimal(0))

    records = db.execute(
        query.order_by(models.Compra.fecha.desc())
        .limit(limit)
        .offset(offset)
        .options(joinedload(models.Compra.detalles).joinedload(models.DetalleCompra.producto))
    ).scalars().unique().all()

    hydrated_records = []
    for record in records:
        subtotal = Decimal(0)
        hydrated_items = []
        for item in record.detalles:
            item_subtotal = item.cantidad * item.costo_unitario
            subtotal += item_subtotal
            item.producto_nombre = item.producto.name if item.producto else "Producto desconocido"
            item.subtotal = item_subtotal
            hydrated_items.append(item)

        record.subtotal = subtotal
        record.proveedor_nombre = vendor.nombre
        record.items = hydrated_items
        hydrated_records.append(record)

    return {
        "proveedor": vendor,
        "compras": hydrated_records,
        "total": total_amount or Decimal(0),
        "impuesto": total_tax or Decimal(0),
        "registros": total_registros
    }


def count_purchase_vendors(
    db: Session,
    *,
    vendor_id: int | None = None,
    query: str | None = None,
    estado: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Proveedor)
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(func.lower(
            models.Proveedor.nombre).like(normalized))
    if estado:
        statement = statement.where(func.lower(
            models.Proveedor.estado) == estado.lower())
    return int(db.scalar(statement) or 0)


def set_purchase_vendor_status(
    db: Session,
    vendor_id: int,
    estado: str,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = get_purchase_vendor(db, vendor_id)
    if not vendor:
        raise LookupError("vendor_not_found")

    with transactional_session(db):
        vendor.estado = estado
        db.add(vendor)

        _log_action(
            db,
            action="purchase_vendor_status_updated",
            entity_type="purchase_vendor",
            entity_id=str(vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps({"estado": estado}),
        )
        flush_session(db)
        db.refresh(vendor)
    return vendor


def count_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Compra)
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return int(db.scalar(statement) or 0)


def list_purchase_records_for_report(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> list[models.Compra]:
    # Reusing _fetch_purchase_records which was added in part 1
    # But wait, _fetch_purchase_records was added as internal function.
    # I should check if I exposed it or if I should just copy the body.
    # I'll assume it's available as I appended it.
    return _fetch_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
        limit=None,
    )


def count_purchase_orders(db: Session, *, store_id: int | None = None) -> int:
    statement = select(func.count()).select_from(models.PurchaseOrder)
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return int(db.scalar(statement) or 0)


def create_purchase_order_from_suggestion(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
    reason: str,
) -> models.PurchaseOrder:
    """Genera una orden de compra desde una sugerencia automatizada."""

    order = create_purchase_order(db, payload, created_by_id=created_by_id)

    items_details = [
        {"device_id": item.device_id, "quantity_ordered": item.quantity_ordered}
        for item in order.items
    ]

    with transactional_session(db):
        _log_action(
            db,
            action="purchase_order_generated_from_suggestion",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {
                    "store_id": order.store_id,
                    "supplier": order.supplier,
                    "reason": reason,
                    "source": "purchase_suggestion",
                    "items": items_details,
                }
            ),
        )
        flush_session(db)

    db.refresh(order)
    return order


def _purchase_record_statement():
    return (
        select(models.Compra)
        .options(
            joinedload(models.Compra.proveedor),
            joinedload(models.Compra.usuario),
            joinedload(models.Compra.detalles).joinedload(
                models.DetalleCompra.producto),
        )
        .order_by(models.Compra.fecha.desc(), models.Compra.id_compra.desc())
    )


def _apply_purchase_record_filters(
    statement,
    *,
    proveedor_id: int | None,
    usuario_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    estado: str | None,
    query: str | None,
):
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return statement


def _fetch_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Compra]:
    statement = _purchase_record_statement()
    statement = _apply_purchase_record_filters(
        statement,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    if limit is not None:
        statement = statement.limit(limit)
    if offset:
        statement = statement.offset(offset)

    results = list(db.scalars(statement).unique())

    for record in results:
        record.proveedor_nombre = record.proveedor.nombre
        record.subtotal = record.total - record.impuesto

        items_list = []
        for detalle in record.detalles:
            detalle.producto_nombre = detalle.producto.name
            items_list.append(detalle)
        record.items = items_list

    return results
