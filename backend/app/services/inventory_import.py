"""Herramientas de importación y exportación masiva para el catálogo de productos."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.transactions import transactional_session

from .. import crud, models, schemas

EXPORT_HEADERS = [
    "sku",
    "name",
    "marca",
    "modelo",
    "categoria",
    "condicion",
    "color",
    "capacidad",
    "capacidad_gb",
    "estado",
    "estado_comercial",
    "quantity",
    "costo_compra",
    "precio_venta",
    "proveedor",
    "ubicacion",
    "fecha_compra",
    "fecha_ingreso",
    "garantia_meses",
    "lote",
    "descripcion",
    "imagen_url",
    "imei",
    "serial",
]

REQUIRED_COLUMNS = {"sku", "name"}


def export_devices_csv(
    db: Session,
    store_id: int,
    *,
    search: str | None = None,
    estado: models.CommercialState | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
) -> str:
    """Genera un CSV con la ficha completa de los productos de la sucursal."""

    devices = crud.list_devices(
        db,
        store_id,
        search=search,
        estado=estado,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
        limit=None,
    )
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_HEADERS)
    writer.writeheader()
    for device in devices:
        writer.writerow(
            {
                "sku": device.sku,
                "name": device.name,
                "marca": device.marca or "",
                "modelo": device.modelo or "",
                "categoria": device.categoria or "",
                "condicion": device.condicion or "",
                "color": device.color or "",
                "capacidad": device.capacidad or "",
                "capacidad_gb": device.capacidad_gb or "",
                "estado": device.estado,
                "estado_comercial": device.estado_comercial.value if device.estado_comercial else "",
                "quantity": device.quantity,
                "costo_compra": _decimal_to_str(device.costo_unitario),
                "precio_venta": _decimal_to_str(device.precio_venta),
                "proveedor": device.proveedor or "",
                "ubicacion": device.ubicacion or "",
                "fecha_compra": device.fecha_compra.isoformat() if device.fecha_compra else "",
                "fecha_ingreso": device.fecha_ingreso.isoformat() if device.fecha_ingreso else "",
                "garantia_meses": device.garantia_meses,
                "lote": device.lote or "",
                "descripcion": (device.descripcion or "").replace("\n", " ").strip(),
                "imagen_url": device.imagen_url or "",
                "imei": device.imei or "",
                "serial": device.serial or "",
            }
        )
    return buffer.getvalue()


def import_devices_from_csv(
    db: Session,
    store_id: int,
    csv_bytes: bytes,
    *,
    performed_by_id: int | None = None,
) -> dict[str, Any]:
    """Importa o actualiza productos a partir de un archivo CSV."""

    try:
        decoded = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError("csv_encoding_error") from exc

    reader = csv.DictReader(StringIO(decoded))
    if reader.fieldnames is None:
        raise ValueError("csv_missing_header")
    missing = REQUIRED_COLUMNS - {header.strip().lower() for header in reader.fieldnames}
    if missing:
        raise ValueError(f"csv_missing_columns:{','.join(sorted(missing))}")

    result = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    with transactional_session(db):
        for index, raw_row in enumerate(reader, start=2):
            row = {key.lower(): value for key, value in raw_row.items()}
            sku = (row.get("sku") or "").strip()
            name = (row.get("name") or "").strip()
            if not sku or not name:
                result["skipped"] += 1
                result["errors"].append({"row": index, "message": "sku_name_required"})
                continue

            quantity = _parse_int(row.get("quantity"))
            garantia = _parse_int(row.get("garantia_meses"))
            capacidad_gb = _parse_int(row.get("capacidad_gb"))
            costo_unitario = _parse_decimal(row.get("costo_compra"))
            precio_venta = _parse_decimal(row.get("precio_venta"))
            fecha_compra = _parse_date(row.get("fecha_compra"))
            fecha_ingreso = _parse_date(row.get("fecha_ingreso"))

            payload_common: dict[str, Any] = {
                "sku": sku,
                "name": name,
                "marca": _normalize_string(row.get("marca")),
                "modelo": _normalize_string(row.get("modelo")),
                "categoria": _normalize_string(row.get("categoria")),
                "condicion": _normalize_string(row.get("condicion")),
                "color": _normalize_string(row.get("color")),
                "capacidad": _normalize_string(row.get("capacidad")),
                "capacidad_gb": capacidad_gb,
                "estado": _normalize_string(row.get("estado")) or "disponible",
                "estado_comercial": _normalize_string(row.get("estado_comercial")) or None,
                "proveedor": _normalize_string(row.get("proveedor")),
                "ubicacion": _normalize_string(row.get("ubicacion")),
                "descripcion": _normalize_string(row.get("descripcion")),
                "imagen_url": _normalize_string(row.get("imagen_url")),
                "imei": _normalize_string(row.get("imei")),
                "serial": _normalize_string(row.get("serial")),
                "lote": _normalize_string(row.get("lote")),
                "costo_unitario": costo_unitario,
                "costo_compra": costo_unitario,
                "unit_price": precio_venta,
                "precio_venta": precio_venta,
                "fecha_compra": fecha_compra,
                "fecha_ingreso": fecha_ingreso,
            }
            if garantia is not None:
                payload_common["garantia_meses"] = garantia
            if quantity is not None:
                payload_common["quantity"] = quantity

            existing_statement = select(models.Device).where(
                models.Device.store_id == store_id, func.lower(models.Device.sku) == sku.lower()
            )
            existing = db.scalars(existing_statement).first()

            try:
                if existing is None:
                    create_payload = schemas.DeviceCreate(**payload_common)
                    crud.create_device(db, store_id, create_payload, performed_by_id=performed_by_id)
                    result["created"] += 1
                else:
                    base_updates = {
                        key: value
                        for key, value in payload_common.items()
                        if key
                        not in {
                            "sku",
                            "quantity",
                            "costo_unitario",
                            "unit_price",
                            "garantia_meses",
                            "capacidad_gb",
                        }
                        and value is not None
                    }
                    # Campos numéricos que admiten actualización explícita
                    numeric_updates: dict[str, Any] = {}
                    if quantity is not None:
                        numeric_updates["quantity"] = quantity
                    if costo_unitario is not None:
                        numeric_updates["costo_unitario"] = costo_unitario
                        numeric_updates["costo_compra"] = costo_unitario
                    if precio_venta is not None:
                        numeric_updates["unit_price"] = precio_venta
                        numeric_updates["precio_venta"] = precio_venta
                    if garantia is not None:
                        numeric_updates["garantia_meses"] = garantia
                    if capacidad_gb is not None:
                        numeric_updates["capacidad_gb"] = capacidad_gb
                    combined_updates = {**base_updates, **numeric_updates}
                    if combined_updates:
                        crud.update_device(
                            db,
                            store_id,
                            existing.id,
                            schemas.DeviceUpdate(**combined_updates),
                            performed_by_id=performed_by_id,
                        )
                        result["updated"] += 1
                    else:
                        result["skipped"] += 1
            except ValueError as exc:
                result["skipped"] += 1
                result["errors"].append({"row": index, "message": str(exc)})

    return result


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (ArithmeticError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _decimal_to_str(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return f"{Decimal(str(value)):.2f}"
