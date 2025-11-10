"""Utilidades para distribuir segmentos de clientes a campañas externas."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import httpx

from ..config import settings
from backend.core.logging import logger as core_logger

logger = core_logger.bind(component=__name__)


@dataclass(slots=True)
class SegmentCustomer:
    """Representa un cliente listo para exportación de marketing."""

    id: int
    name: str
    email: str | None
    phone: str | None
    annual_purchase_amount: float
    orders_last_year: int
    purchase_frequency: str
    segment_labels: list[str]
    last_purchase_at: str | None


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def export_segment_csv(
    segment_key: str,
    customers: Iterable[SegmentCustomer],
    *,
    generated_at: datetime,
    directory: str | None = None,
) -> Path | None:
    """Genera un archivo CSV local para el segmento proporcionado."""

    customer_list = list(customers)
    if not customer_list:
        return None

    base_dir = Path(directory or settings.customer_segments_export_directory)
    _ensure_directory(base_dir)
    timestamp = generated_at.strftime("%Y%m%d%H%M%S")
    export_path = base_dir / f"{segment_key}_{timestamp}.csv"

    with export_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "id",
                "nombre",
                "correo",
                "telefono",
                "monto_anual",
                "ordenes_anuales",
                "frecuencia",
                "etiquetas",
                "ultima_compra",
            ]
        )
        for customer in customer_list:
            writer.writerow(
                [
                    customer.id,
                    customer.name,
                    customer.email or "",
                    customer.phone or "",
                    f"{customer.annual_purchase_amount:.2f}",
                    customer.orders_last_year,
                    customer.purchase_frequency,
                    ",".join(customer.segment_labels),
                    customer.last_purchase_at or "",
                ]
            )
    logger.info(
        "Segmento exportado localmente",
        segment=segment_key,
        path=str(export_path),
        customers=len(customer_list),
    )
    return export_path


def push_to_mailchimp(
    segment_key: str,
    customers: Iterable[SegmentCustomer],
    *,
    generated_at: datetime,
    api_url: str | None = None,
    api_key: str | None = None,
    directory: str | None = None,
    export_path: Path | None = None,
) -> None:
    """Envía el segmento a Mailchimp mediante archivo local y API si está disponible."""

    customer_list = list(customers)
    if not customer_list:
        return

    file_path = export_path
    if file_path is None:
        file_path = export_segment_csv(
            segment_key,
            customer_list,
            generated_at=generated_at,
            directory=directory,
        )

    url = api_url or settings.mailchimp_api_url
    token = api_key or settings.mailchimp_api_key
    if not url or not token:
        logger.info(
            "Mailchimp no configurado; se generó archivo local",
            segment=segment_key,
            customers=len(customer_list),
            path=str(file_path) if file_path else None,
        )
        return

    payload = {
        "segment": segment_key,
        "generated_at": generated_at.isoformat(),
        "customers": [asdict(customer) for customer in customer_list],
        "export_path": str(file_path) if file_path else None,
    }

    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        logger.info(
            "Segmento enviado a Mailchimp",
            segment=segment_key,
            customers=len(customer_list),
        )
    except Exception as exc:  # pragma: no cover - ruta de fallo registrada
        logger.warning(
            "Error al enviar segmento a Mailchimp",
            segment=segment_key,
            error=str(exc),
        )


def push_to_sms_gateway(
    segment_key: str,
    customers: Iterable[SegmentCustomer],
    *,
    generated_at: datetime,
    api_url: str | None = None,
    api_token: str | None = None,
    sender: str | None = None,
    export_path: Path | None = None,
) -> None:
    """Envía el segmento a la pasarela SMS cuando existe configuración."""

    customer_list = list(customers)
    if not customer_list:
        return

    url = api_url or settings.sms_campaign_api_url
    token = api_token or settings.sms_campaign_api_token
    sender_id = sender or settings.sms_campaign_sender
    if not url or not token:
        logger.info(
            "Pasarela SMS no configurada; se omite envío",
            segment=segment_key,
            customers=len(customer_list),
            path=str(export_path) if export_path else None,
        )
        return

    payload = {
        "segment": segment_key,
        "generated_at": generated_at.isoformat(),
        "sender": sender_id,
        "recipients": [
            {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "frequency": customer.purchase_frequency,
                "labels": customer.segment_labels,
            }
            for customer in customer_list
            if customer.phone
        ],
    }

    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        logger.info(
            "Segmento enviado a pasarela SMS",
            segment=segment_key,
            customers=len(payload["recipients"]),
            path=str(export_path) if export_path else None,
        )
    except Exception as exc:  # pragma: no cover - ruta de fallo registrada
        logger.warning(
            "Error al enviar segmento a SMS",
            segment=segment_key,
            error=str(exc),
        )
