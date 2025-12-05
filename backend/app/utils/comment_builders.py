"""Utilidades para formateo de comentarios y descripciones de movimientos."""
from __future__ import annotations

from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .. import models, schemas


def build_transfer_movement_comment(
    order: any,  # models.TransferOrder
    device: any,  # models.Device
    direction: Literal["OUT", "IN"],
    reason: str | None,
) -> str:
    """Genera comentario para movimiento de transferencia.
    
    Args:
        order: Orden de transferencia
        device: Dispositivo transferido
        direction: Dirección ("OUT" salida, "IN" entrada)
        reason: Motivo adicional
        
    Returns:
        Comentario formateado (máx 255 caracteres)
    """
    segments = [f"Transferencia #{order.id}"]
    if direction == "OUT":
        segments.append("Salida")
        target = order.destination_store.name if order.destination_store else None
        if target:
            segments.append(f"Destino: {target}")
    else:
        segments.append("Entrada")
        origin = order.origin_store.name if order.origin_store else None
        if origin:
            segments.append(f"Origen: {origin}")
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    return " — ".join(segments)[:255]


def build_purchase_movement_comment(
    action: str,
    order: any,  # models.PurchaseOrder
    device: any,  # models.Device
    reason: str | None,
) -> str:
    """Genera comentario para movimiento de compra.
    
    Args:
        action: Acción realizada
        order: Orden de compra
        device: Dispositivo comprado
        reason: Motivo adicional
        
    Returns:
        Comentario formateado (máx 255 caracteres)
    """
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


def build_sale_movement_comment(
    sale: any,  # models.Sale
    device: any,  # models.Device
    reason: str | None
) -> str:
    """Genera comentario para movimiento de venta.
    
    Args:
        sale: Venta
        device: Dispositivo vendido
        reason: Motivo adicional
        
    Returns:
        Comentario formateado (máx 255 caracteres)
    """
    segments = [f"Venta #{sale.id}"]
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    return " — ".join(segments)[:255]


def build_sale_return_comment(
    sale: any,  # models.Sale
    device: any,  # models.Device
    reason: str | None,
    *,
    disposition: any = None,  # schemas.ReturnDisposition | None
    warehouse_name: str | None = None,
) -> str:
    """Genera comentario para devolución de venta.
    
    Args:
        sale: Venta original
        device: Dispositivo devuelto
        reason: Motivo de devolución
        disposition: Disposición del artículo devuelto
        warehouse_name: Nombre del almacén destino
        
    Returns:
        Comentario formateado (máx 255 caracteres)
    """
    segments = [f"Devolución venta #{sale.id}"]
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    if disposition is not None:
        segments.append(f"estado={disposition.value}")
    if warehouse_name:
        segments.append(f"almacen={warehouse_name}")
    return " — ".join(segments)[:255]
