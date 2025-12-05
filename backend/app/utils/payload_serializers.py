"""Utilidades para serialización de payloads de sincronización."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .. import models

from .decimal_helpers import to_decimal
from .analytics_helpers import user_display_name


def customer_payload(customer: any) -> dict[str, object]:
    """Serializa un cliente para sincronización."""
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


def customer_privacy_request_payload(
    request: any,
) -> dict[str, object]:
    """Serializa una solicitud de privacidad de cliente."""
    return {
        "id": request.id,
        "customer_id": request.customer_id,
        "request_type": request.request_type.value,
        "status": request.status.value,
        "reason": request.reason,
        "requested_by_id": request.requested_by_id,
        "processed_by_id": request.processed_by_id,
        "requested_at": request.requested_at.isoformat(),
        "processed_at": request.processed_at.isoformat() if request.processed_at else None,
    }


def device_sync_payload(device: any) -> dict[str, object]:
    """Construye el payload serializado de un dispositivo para sincronización."""
    commercial_state = getattr(
        device.estado_comercial, "value", device.estado_comercial)
    updated_at = getattr(device, "updated_at", None)
    store_name = device.store.name if getattr(device, "store", None) else None
    return {
        "id": device.id,
        "store_id": device.store_id,
        "store_name": store_name,
        "warehouse_id": device.warehouse_id,
        "warehouse_name": getattr(device.warehouse, "name", None),
        "sku": device.sku,
        "name": device.name,
        "quantity": device.quantity,
        "unit_price": float(to_decimal(device.unit_price)),
        "costo_unitario": float(to_decimal(device.costo_unitario)),
        "margen_porcentaje": float(to_decimal(device.margen_porcentaje)),
        "estado": device.estado,
        "estado_comercial": commercial_state,
        "minimum_stock": int(getattr(device, "minimum_stock", 0) or 0),
        "reorder_point": int(getattr(device, "reorder_point", 0) or 0),
        "imei": device.imei,
        "serial": device.serial,
        "marca": device.marca,
        "modelo": device.modelo,
        "color": device.color,
        "capacidad_gb": device.capacidad_gb,
        "garantia_meses": device.garantia_meses,
        "proveedor": device.proveedor,
        "lote": device.lote,
        "fecha_compra": device.fecha_compra.isoformat() if device.fecha_compra else None,
        "fecha_ingreso": device.fecha_ingreso.isoformat() if device.fecha_ingreso else None,
        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
    }


def inventory_movement_payload(movement: any) -> dict[str, object]:
    """Genera el payload de sincronización para un movimiento de inventario."""
    store_name = movement.store.name if movement.store else None
    source_name = movement.source_store.name if movement.source_store else None
    warehouse_name = movement.warehouse.name if movement.warehouse else None
    source_warehouse_name = (
        movement.source_warehouse.name if movement.source_warehouse else None
    )
    device = movement.device
    performed_by = user_display_name(movement.performed_by)
    created_at = movement.created_at.isoformat() if movement.created_at else None
    reference_type = getattr(movement, "reference_type", None)
    reference_id = getattr(movement, "reference_id", None)
    return {
        "id": movement.id,
        "store_id": movement.store_id,
        "store_name": store_name,
        "source_store_id": movement.source_store_id,
        "source_store_name": source_name,
        "warehouse_id": movement.warehouse_id,
        "warehouse_name": warehouse_name,
        "source_warehouse_id": movement.source_warehouse_id,
        "source_warehouse_name": source_warehouse_name,
        "device_id": movement.device_id,
        "device_sku": device.sku if device else None,
        "movement_type": movement.movement_type.value,
        "quantity": movement.quantity,
        "comment": movement.comment,
        "unit_cost": float(to_decimal(movement.unit_cost)) if movement.unit_cost is not None else None,
        "performed_by_id": movement.performed_by_id,
        "performed_by_name": performed_by,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "created_at": created_at,
    }


def purchase_order_payload(order: any) -> dict[str, object]:
    """Serializa una orden de compra para la cola de sincronización."""
    store_name = order.store.name if getattr(order, "store", None) else None
    status_value = getattr(order.status, "value", order.status)
    items_payload = [
        {
            "device_id": item.device_id,
            "quantity_ordered": item.quantity_ordered,
            "quantity_received": item.quantity_received,
            "unit_cost": float(to_decimal(item.unit_cost)),
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
                "storage_backend": document.storage_backend,
                "uploaded_at": document.uploaded_at.isoformat(),
            }
            for document in getattr(order, "documents", [])
        ],
        "status_history": [
            {
                "id": event.id,
                "status": getattr(event.status, "value", event.status),
                "note": event.note,
                "created_at": event.created_at.isoformat(),
                "created_by_id": event.created_by_id,
            }
            for event in getattr(order, "status_events", [])
        ],
    }


def transfer_order_payload(order: any) -> dict[str, object]:
    """Serializa una orden de transferencia para la cola híbrida."""
    origin_store = getattr(order, "origin_store", None)
    destination_store = getattr(order, "destination_store", None)
    requested_by = getattr(order, "requested_by", None)
    dispatched_by = getattr(order, "dispatched_by", None)
    received_by = getattr(order, "received_by", None)
    cancelled_by = getattr(order, "cancelled_by", None)
    items_payload = []
    for item in getattr(order, "items", []) or []:
        device = getattr(item, "device", None)
        items_payload.append(
            {
                "device_id": item.device_id,
                "quantity": item.quantity,
                "dispatched_quantity": item.dispatched_quantity,
                "received_quantity": item.received_quantity,
                "dispatched_unit_cost": float(item.dispatched_unit_cost)
                if item.dispatched_unit_cost is not None
                else None,
                "sku": getattr(device, "sku", None),
                "imei": getattr(device, "imei", None),
                "serial": getattr(device, "serial", None),
            }
        )
    status_value = getattr(order.status, "value", order.status)
    return {
        "id": order.id,
        "origin_store_id": order.origin_store_id,
        "origin_store_name": getattr(origin_store, "name", None),
        "destination_store_id": order.destination_store_id,
        "destination_store_name": getattr(destination_store, "name", None),
        "status": status_value,
        "reason": order.reason,
        "requested_by_id": order.requested_by_id,
        "requested_by_name": user_display_name(requested_by),
        "dispatched_by_id": order.dispatched_by_id,
        "dispatched_by_name": user_display_name(dispatched_by),
        "received_by_id": order.received_by_id,
        "received_by_name": user_display_name(received_by),
        "cancelled_by_id": order.cancelled_by_id,
        "cancelled_by_name": user_display_name(cancelled_by),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "dispatched_at": order.dispatched_at.isoformat() if order.dispatched_at else None,
        "received_at": order.received_at.isoformat() if order.received_at else None,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        "items": items_payload,
    }
