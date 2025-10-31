"""Herramientas para transformar registros de auditoría a representaciones públicas."""
from __future__ import annotations

import json
from typing import Any, Iterable

from .. import models, schemas


def _merge_metadata(
    base: dict[str, Any] | None,
    extra: Iterable[tuple[str, Any]],
) -> dict[str, Any] | None:
    metadata: dict[str, Any] | None = None
    if base is not None:
        metadata = dict(base)
    for key, value in extra:
        if value is None:
            continue
        if metadata is None:
            metadata = {}
        metadata[key] = value
    return metadata


def parse_audit_details(details: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """Obtiene una descripción y metadatos serializables a partir del campo ``details``."""

    if not details:
        return None, None

    try:
        data = json.loads(details)
    except json.JSONDecodeError:
        return details, None

    if isinstance(data, str):
        return data or None, None

    if isinstance(data, dict):
        description = data.get("description")
        metadata_field = data.get("metadata")

        normalized_description = description if isinstance(description, str) else None

        normalized_metadata: dict[str, Any] | None = None
        if isinstance(metadata_field, dict):
            normalized_metadata = metadata_field
        elif metadata_field is not None:
            normalized_metadata = {"value": metadata_field}

        extra_pairs = [
            (key, value)
            for key, value in data.items()
            if key not in {"description", "metadata"}
        ]
        normalized_metadata = _merge_metadata(normalized_metadata, extra_pairs)

        if normalized_description is None and normalized_metadata:
            normalized_description = ", ".join(
                f"{key}: {value}" for key, value in normalized_metadata.items()
            )

        return normalized_description, normalized_metadata

    if isinstance(data, list):
        return ", ".join(map(str, data)) or None, None

    return str(data), None


def to_audit_trail(log: models.AuditLog) -> schemas.AuditTrailInfo:
    """Convierte un modelo ``AuditLog`` en una estructura lista para respuesta API."""

    description, metadata = parse_audit_details(log.details)
    if description is None:
        description = f"{log.action} · {log.entity_type} #{log.entity_id}".strip()
    performed_by = log.performed_by
    performed_by_name: str | None = None
    if performed_by is not None:
        performed_by_name = performed_by.full_name or performed_by.username

    return schemas.AuditTrailInfo(
        accion=log.action,
        descripcion=description,
        entidad=log.entity_type,
        registro_id=log.entity_id,
        usuario_id=log.performed_by_id,
        usuario=performed_by_name,
        timestamp=log.created_at,
        metadata=metadata,
    )


__all__ = ["parse_audit_details", "to_audit_trail"]
