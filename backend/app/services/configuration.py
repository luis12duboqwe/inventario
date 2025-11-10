"""Servicios para gestionar la configuración centralizada del sistema."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.transactions import transactional_session


def _normalize_slug(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "-")
    return normalized


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _quantize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sanitize_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize_metadata_value(val) for key, val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_metadata_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {
        str(key): _sanitize_metadata_value(value)
        for key, value in metadata.items()
    }


def _rate_to_schema(rate: models.ConfigRate) -> schemas.ConfigurationRateResponse:
    return schemas.ConfigurationRateResponse(
        id=rate.id,
        slug=rate.slug,
        name=rate.name,
        description=rate.description,
        value=_quantize_decimal(Decimal(str(rate.value))),
        unit=rate.unit,
        currency=rate.currency,
        effective_from=rate.effective_from,
        effective_to=rate.effective_to,
        metadata=rate.metadata_json or {},
        is_active=rate.is_active,
        created_at=rate.created_at,
        updated_at=rate.updated_at,
    )


def _template_to_schema(template: models.ConfigXmlTemplate) -> schemas.ConfigurationXmlTemplateResponse:
    return schemas.ConfigurationXmlTemplateResponse(
        id=template.id,
        code=template.code,
        version=template.version,
        description=template.description,
        namespace=template.namespace,
        schema_location=template.schema_location,
        content=template.content,
        metadata=template.metadata_json or {},
        checksum=template.checksum,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _serialize_parameter_value(
    value_type: schemas.ConfigurationParameterType,
    value: Any,
) -> tuple[str | None, Any | None]:
    if value_type is schemas.ConfigurationParameterType.JSON:
        return None, value
    if value_type is schemas.ConfigurationParameterType.DECIMAL:
        return str(Decimal(str(value))), None
    if value_type is schemas.ConfigurationParameterType.INTEGER:
        return str(int(value)), None
    if value_type is schemas.ConfigurationParameterType.BOOLEAN:
        return ("true" if bool(value) else "false"), None
    return str(value), None


def _deserialize_parameter_value(parameter: models.ConfigParameter) -> Any:
    raw_type = parameter.value_type or schemas.ConfigurationParameterType.STRING.value
    param_type = schemas.ConfigurationParameterType(raw_type)
    if param_type is schemas.ConfigurationParameterType.JSON:
        return parameter.value_json or {}
    text = parameter.value_text or ""
    if param_type is schemas.ConfigurationParameterType.BOOLEAN:
        normalized = text.strip().lower()
        return normalized in {"1", "true", "yes", "si", "sí"}
    if param_type is schemas.ConfigurationParameterType.INTEGER:
        return int(text or 0)
    if param_type is schemas.ConfigurationParameterType.DECIMAL:
        return Decimal(text or "0")
    return text


def _parameter_to_schema(parameter: models.ConfigParameter) -> schemas.ConfigurationParameterResponse:
    return schemas.ConfigurationParameterResponse(
        id=parameter.id,
        key=parameter.key,
        name=parameter.name,
        category=parameter.category,
        description=parameter.description,
        value_type=schemas.ConfigurationParameterType(parameter.value_type),
        value=_deserialize_parameter_value(parameter),
        is_sensitive=parameter.is_sensitive,
        metadata=parameter.metadata_json or {},
        is_active=parameter.is_active,
        created_at=parameter.created_at,
        updated_at=parameter.updated_at,
    )


def list_config_rates(db: Session, *, include_inactive: bool = False) -> list[schemas.ConfigurationRateResponse]:
    statement = select(models.ConfigRate).order_by(models.ConfigRate.name.asc())
    if not include_inactive:
        statement = statement.where(models.ConfigRate.is_active.is_(True))
    rates = db.scalars(statement).all()
    return [_rate_to_schema(rate) for rate in rates]


def list_config_xml_templates(
    db: Session, *, include_inactive: bool = False
) -> list[schemas.ConfigurationXmlTemplateResponse]:
    statement = select(models.ConfigXmlTemplate).order_by(models.ConfigXmlTemplate.code.asc())
    if not include_inactive:
        statement = statement.where(models.ConfigXmlTemplate.is_active.is_(True))
    templates = db.scalars(statement).all()
    return [_template_to_schema(template) for template in templates]


def list_config_parameters(
    db: Session, *, include_inactive: bool = False
) -> list[schemas.ConfigurationParameterResponse]:
    statement = select(models.ConfigParameter).order_by(models.ConfigParameter.key.asc())
    if not include_inactive:
        statement = statement.where(models.ConfigParameter.is_active.is_(True))
    parameters = db.scalars(statement).all()
    return [_parameter_to_schema(parameter) for parameter in parameters]


def create_config_rate(
    db: Session, payload: schemas.ConfigurationRateCreate
) -> schemas.ConfigurationRateResponse:
    slug = _normalize_slug(payload.slug)
    with transactional_session(db):
        existing = db.scalars(
            select(models.ConfigRate).where(func.lower(models.ConfigRate.slug) == slug)
        ).first()
        if existing:
            raise ValueError("config_rate_conflict")
        rate = models.ConfigRate(
            slug=slug,
            name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        value=_quantize_decimal(payload.value),
        unit=payload.unit.strip(),
        currency=payload.currency.strip() if payload.currency else None,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        metadata_json=_sanitize_metadata(payload.metadata),
        is_active=True,
    )
    db.add(rate)
    db.flush()
    db.refresh(rate)
    return _rate_to_schema(rate)


def update_config_rate(
    db: Session, rate_id: int, payload: schemas.ConfigurationRateUpdate
) -> schemas.ConfigurationRateResponse:
    with transactional_session(db):
        rate = db.get(models.ConfigRate, rate_id)
        if rate is None:
            raise LookupError("config_rate_not_found")
        if payload.name is not None:
            rate.name = payload.name.strip()
        if payload.description is not None:
            rate.description = payload.description.strip() or None
        if payload.value is not None:
            rate.value = _quantize_decimal(payload.value)
        if payload.unit is not None:
            rate.unit = payload.unit.strip()
        if payload.currency is not None:
            rate.currency = payload.currency.strip() or None
        if payload.effective_from is not None:
            rate.effective_from = payload.effective_from
        if payload.effective_to is not None:
            rate.effective_to = payload.effective_to
        if payload.metadata is not None:
            rate.metadata_json = _sanitize_metadata(payload.metadata)
        if payload.is_active is not None:
            rate.is_active = payload.is_active
        rate.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(rate)
    return _rate_to_schema(rate)


def create_config_xml_template(
    db: Session, payload: schemas.ConfigurationXmlTemplateCreate
) -> schemas.ConfigurationXmlTemplateResponse:
    code = payload.code.strip().lower()
    with transactional_session(db):
        existing = db.scalars(
            select(models.ConfigXmlTemplate).where(func.lower(models.ConfigXmlTemplate.code) == code)
        ).first()
        if existing:
            raise ValueError("config_xml_conflict")
        checksum = _checksum(payload.content)
        template = models.ConfigXmlTemplate(
            code=code,
            version=payload.version.strip(),
            description=payload.description.strip() if payload.description else None,
            namespace=payload.namespace.strip() if payload.namespace else None,
            schema_location=payload.schema_location.strip() if payload.schema_location else None,
            content=payload.content,
            checksum=checksum,
            metadata_json=_sanitize_metadata(payload.metadata),
            is_active=True,
        )
        db.add(template)
        db.flush()
        db.refresh(template)
    return _template_to_schema(template)


def update_config_xml_template(
    db: Session, template_id: int, payload: schemas.ConfigurationXmlTemplateUpdate
) -> schemas.ConfigurationXmlTemplateResponse:
    with transactional_session(db):
        template = db.get(models.ConfigXmlTemplate, template_id)
        if template is None:
            raise LookupError("config_xml_not_found")
        if payload.version is not None:
            template.version = payload.version.strip()
        if payload.description is not None:
            template.description = payload.description.strip() or None
        if payload.namespace is not None:
            template.namespace = payload.namespace.strip() or None
        if payload.schema_location is not None:
            template.schema_location = payload.schema_location.strip() or None
        if payload.content is not None:
            template.content = payload.content
            template.checksum = _checksum(payload.content)
        if payload.metadata is not None:
            template.metadata_json = _sanitize_metadata(payload.metadata)
        if payload.is_active is not None:
            template.is_active = payload.is_active
        template.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(template)
    return _template_to_schema(template)


def create_config_parameter(
    db: Session, payload: schemas.ConfigurationParameterCreate
) -> schemas.ConfigurationParameterResponse:
    key = _normalize_key(payload.key)
    with transactional_session(db):
        existing = db.scalars(
            select(models.ConfigParameter).where(func.lower(models.ConfigParameter.key) == key)
        ).first()
        if existing:
            raise ValueError("config_parameter_conflict")
        value_text, value_json = _serialize_parameter_value(payload.value_type, payload.value)
        parameter = models.ConfigParameter(
            key=key,
            name=payload.name.strip(),
            category=payload.category.strip() if payload.category else None,
            description=payload.description.strip() if payload.description else None,
            value_type=payload.value_type.value,
            value_text=value_text,
            value_json=value_json,
            is_sensitive=payload.is_sensitive,
            metadata_json=_sanitize_metadata(payload.metadata),
            is_active=True,
        )
        db.add(parameter)
        db.flush()
        db.refresh(parameter)
    return _parameter_to_schema(parameter)


def update_config_parameter(
    db: Session, parameter_id: int, payload: schemas.ConfigurationParameterUpdate
) -> schemas.ConfigurationParameterResponse:
    with transactional_session(db):
        parameter = db.get(models.ConfigParameter, parameter_id)
        if parameter is None:
            raise LookupError("config_parameter_not_found")
        if payload.name is not None:
            parameter.name = payload.name.strip()
        if payload.category is not None:
            parameter.category = payload.category.strip() or None
        if payload.description is not None:
            parameter.description = payload.description.strip() or None
        target_type = (
            payload.value_type
            if payload.value_type is not None
            else schemas.ConfigurationParameterType(parameter.value_type)
        )
        if payload.value is not None:
            value_text, value_json = _serialize_parameter_value(target_type, payload.value)
            parameter.value_type = target_type.value
            parameter.value_text = value_text
            parameter.value_json = value_json
        elif payload.value_type is not None and payload.value is None:
            current_value = _deserialize_parameter_value(parameter)
            value_text, value_json = _serialize_parameter_value(
                target_type, current_value
            )
            parameter.value_type = target_type.value
            parameter.value_text = value_text
            parameter.value_json = value_json
        if payload.is_sensitive is not None:
            parameter.is_sensitive = payload.is_sensitive
        if payload.metadata is not None:
            parameter.metadata_json = _sanitize_metadata(payload.metadata)
        if payload.is_active is not None:
            parameter.is_active = payload.is_active
        parameter.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(parameter)
    return _parameter_to_schema(parameter)


def get_overview(db: Session, *, include_inactive: bool = True) -> schemas.ConfigurationOverview:
    return schemas.ConfigurationOverview(
        rates=list_config_rates(db, include_inactive=include_inactive),
        xml_templates=list_config_xml_templates(db, include_inactive=include_inactive),
        parameters=list_config_parameters(db, include_inactive=include_inactive),
    )


def _load_yaml_payloads(base_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    aggregated: dict[str, list[dict[str, Any]]] = {
        "rates": [],
        "xml_templates": [],
        "parameters": [],
    }
    processed: list[str] = []
    for file_path in sorted(base_dir.glob("*.y*ml")):
        with file_path.open("r", encoding="utf-8") as handler:
            try:
                data = yaml.safe_load(handler) or {}
            except yaml.YAMLError as exc:
                raise ValueError(
                    f"config_sync_yaml_invalid::{file_path.name}"
                ) from exc
        if not isinstance(data, dict):
            continue
        recognized = False
        for key in ("rates", "xml_templates", "parameters"):
            items = data.get(key)
            if isinstance(items, list) and items:
                aggregated[key].extend(items)
                recognized = True
        if recognized:
            processed.append(file_path.name)
    return aggregated, processed


def synchronize_from_yaml(db: Session, base_dir: Path) -> schemas.ConfigurationSyncResult:
    directory = Path(base_dir)
    if not directory.exists():
        raise FileNotFoundError("config_sync_directory_not_found")

    aggregated, processed_files = _load_yaml_payloads(directory)

    rates_payloads = [
        schemas.ConfigurationRateCreate.model_validate(item)
        for item in aggregated["rates"]
    ]
    template_payloads = [
        schemas.ConfigurationXmlTemplateCreate.model_validate(item)
        for item in aggregated["xml_templates"]
    ]
    parameter_payloads = [
        schemas.ConfigurationParameterCreate.model_validate(item)
        for item in aggregated["parameters"]
    ]

    rates_activated = rates_deactivated = 0
    templates_activated = templates_deactivated = 0
    parameters_activated = parameters_deactivated = 0

    with transactional_session(db):
        existing_rates = {
            rate.slug: rate for rate in db.scalars(select(models.ConfigRate)).all()
        }
        processed_rate_slugs: set[str] = set()
        for payload in rates_payloads:
            slug = _normalize_slug(payload.slug)
            processed_rate_slugs.add(slug)
            current = existing_rates.get(slug)
            if current:
                previous_active = current.is_active
                current.name = payload.name.strip()
                current.description = payload.description.strip() if payload.description else None
                current.value = _quantize_decimal(payload.value)
                current.unit = payload.unit.strip()
                current.currency = payload.currency.strip() if payload.currency else None
                current.effective_from = payload.effective_from
                current.effective_to = payload.effective_to
                current.metadata_json = _sanitize_metadata(payload.metadata)
                current.is_active = True
                current.updated_at = datetime.utcnow()
                if not previous_active:
                    rates_activated += 1
            else:
                rate = models.ConfigRate(
                    slug=slug,
                    name=payload.name.strip(),
                    description=payload.description.strip() if payload.description else None,
                    value=_quantize_decimal(payload.value),
                    unit=payload.unit.strip(),
                    currency=payload.currency.strip() if payload.currency else None,
                    effective_from=payload.effective_from,
                    effective_to=payload.effective_to,
                    metadata_json=_sanitize_metadata(payload.metadata),
                    is_active=True,
                )
                db.add(rate)
                existing_rates[slug] = rate
                rates_activated += 1
        for slug, rate in existing_rates.items():
            if slug not in processed_rate_slugs and rate.is_active:
                rate.is_active = False
                rate.updated_at = datetime.utcnow()
                rates_deactivated += 1

        existing_templates = {
            template.code: template
            for template in db.scalars(select(models.ConfigXmlTemplate)).all()
        }
        processed_template_codes: set[str] = set()
        for payload in template_payloads:
            code = payload.code.strip().lower()
            processed_template_codes.add(code)
            checksum = _checksum(payload.content)
            current = existing_templates.get(code)
            if current:
                previous_active = current.is_active
                current.version = payload.version.strip()
                current.description = payload.description.strip() if payload.description else None
                current.namespace = payload.namespace.strip() if payload.namespace else None
                current.schema_location = payload.schema_location.strip() if payload.schema_location else None
                current.content = payload.content
                current.checksum = checksum
                current.metadata_json = _sanitize_metadata(payload.metadata)
                current.is_active = True
                current.updated_at = datetime.utcnow()
                if not previous_active:
                    templates_activated += 1
            else:
                template = models.ConfigXmlTemplate(
                    code=code,
                    version=payload.version.strip(),
                    description=payload.description.strip() if payload.description else None,
                    namespace=payload.namespace.strip() if payload.namespace else None,
                    schema_location=payload.schema_location.strip() if payload.schema_location else None,
                    content=payload.content,
                    checksum=checksum,
                    metadata_json=_sanitize_metadata(payload.metadata),
                    is_active=True,
                )
                db.add(template)
                existing_templates[code] = template
                templates_activated += 1
        for code, template in existing_templates.items():
            if code not in processed_template_codes and template.is_active:
                template.is_active = False
                template.updated_at = datetime.utcnow()
                templates_deactivated += 1

        existing_parameters = {
            parameter.key: parameter
            for parameter in db.scalars(select(models.ConfigParameter)).all()
        }
        processed_parameter_keys: set[str] = set()
        for payload in parameter_payloads:
            key = _normalize_key(payload.key)
            processed_parameter_keys.add(key)
            current = existing_parameters.get(key)
            value_text, value_json = _serialize_parameter_value(
                payload.value_type, payload.value
            )
            if current:
                previous_active = current.is_active
                current.name = payload.name.strip()
                current.category = payload.category.strip() if payload.category else None
                current.description = payload.description.strip() if payload.description else None
                current.value_type = payload.value_type.value
                current.value_text = value_text
                current.value_json = value_json
                current.is_sensitive = payload.is_sensitive
                current.metadata_json = _sanitize_metadata(payload.metadata)
                current.is_active = True
                current.updated_at = datetime.utcnow()
                if not previous_active:
                    parameters_activated += 1
            else:
                parameter = models.ConfigParameter(
                    key=key,
                    name=payload.name.strip(),
                    category=payload.category.strip() if payload.category else None,
                    description=payload.description.strip() if payload.description else None,
                    value_type=payload.value_type.value,
                    value_text=value_text,
                    value_json=value_json,
                    is_sensitive=payload.is_sensitive,
                    metadata_json=_sanitize_metadata(payload.metadata),
                    is_active=True,
                )
                db.add(parameter)
                existing_parameters[key] = parameter
                parameters_activated += 1
        for key, parameter in existing_parameters.items():
            if key not in processed_parameter_keys and parameter.is_active:
                parameter.is_active = False
                parameter.updated_at = datetime.utcnow()
                parameters_deactivated += 1

    return schemas.ConfigurationSyncResult(
        rates_activated=rates_activated,
        rates_deactivated=rates_deactivated,
        templates_activated=templates_activated,
        templates_deactivated=templates_deactivated,
        parameters_activated=parameters_activated,
        parameters_deactivated=parameters_deactivated,
        processed_files=processed_files,
    )
