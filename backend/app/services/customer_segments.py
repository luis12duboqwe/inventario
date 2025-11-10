"""Cálculo y exportación de segmentos de clientes."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..config import settings
from backend.core.logging import logger as core_logger
from ..core.transactions import transactional_session
from . import customer_marketing

logger = core_logger.bind(component=__name__)


@dataclass(slots=True)
class SegmentComputationResult:
    """Resumen de la ejecución del cálculo de segmentos."""

    updated_customers: int
    segments: dict[str, list[customer_marketing.SegmentCustomer]]


_EXPORTABLE_SEGMENTS: dict[str, str] = {
    "alto_valor": "Clientes con compras anuales superiores al umbral alto.",
    "valor_medio": "Compras anuales en el rango medio configurado.",
    "valor_bajo": "Clientes con baja facturación anual.",
    "frecuente": "Clientes con órdenes recurrentes durante el último año.",
    "recurrente": "Clientes con actividad constante durante el último año.",
    "ocasional": "Clientes con pocas compras en el año.",
    "sin_compras": "Clientes sin compras registradas en los últimos meses.",
    "recuperacion": "Clientes inactivos según la ventana de recuperación.",
    "nuevo": "Clientes con ventas recientes dentro del periodo inicial.",
    "vip": "Clientes marcados como VIP o corporativos.",
    "moroso": "Clientes con saldo moroso activo.",
}


def compute_customer_segments(
    db: Session,
    *,
    now: datetime | None = None,
) -> SegmentComputationResult:
    """Actualiza los snapshots de segmentos y retorna los grupos calculados."""

    current_time = now or datetime.now(timezone.utc)
    window_start = current_time - timedelta(days=settings.customer_segment_window_days)

    statement = (
        select(
            models.Customer,
            func.coalesce(func.sum(models.Sale.total_amount), Decimal("0")).label("annual_amount"),
            func.coalesce(func.count(models.Sale.id), 0).label("orders_last_year"),
            func.max(models.Sale.created_at).label("last_sale_at"),
        )
        .outerjoin(
            models.Sale,
            and_(
                models.Sale.customer_id == models.Customer.id,
                models.Sale.status == "COMPLETADA",
                models.Sale.created_at >= window_start,
            ),
        )
        .group_by(models.Customer.id)
    )

    results = db.execute(statement).all()
    segments: dict[str, list[customer_marketing.SegmentCustomer]] = defaultdict(list)
    updated = 0

    for customer, annual_amount, orders_last_year, last_sale_at in results:
        updated += 1
        amount_decimal = Decimal(annual_amount or Decimal("0"))
        orders = int(orders_last_year or 0)
        average_ticket = (
            (amount_decimal / orders).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if orders
            else Decimal("0")
        )
        frequency_label = _resolve_frequency_label(orders)
        segment_labels = _resolve_segment_labels(
            customer,
            amount_decimal,
            orders,
            last_sale_at,
            current_time,
        )

        snapshot = customer.segment_snapshot
        if snapshot is None:
            snapshot = models.CustomerSegmentSnapshot(customer=customer)
            db.add(snapshot)

        snapshot.annual_amount = amount_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        snapshot.orders_last_year = orders
        snapshot.average_ticket = average_ticket
        snapshot.frequency_label = frequency_label
        snapshot.segment_labels = segment_labels
        snapshot.last_sale_at = last_sale_at
        snapshot.computed_at = current_time

        segments_payload = customer_marketing.SegmentCustomer(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            annual_purchase_amount=float(snapshot.annual_amount),
            orders_last_year=orders,
            purchase_frequency=frequency_label,
            segment_labels=list(segment_labels),
            last_purchase_at=last_sale_at.isoformat() if last_sale_at else None,
        )
        for label in segment_labels:
            segments[label].append(segments_payload)

    return SegmentComputationResult(
        updated_customers=updated,
        segments={key: list(value) for key, value in segments.items()},
    )


def refresh_customer_segments(
    db: Session,
    *,
    now: datetime | None = None,
    trigger_marketing: bool = True,
    export_directory: str | None = None,
) -> SegmentComputationResult:
    """Recalcula los segmentos y ejecuta hooks externos cuando corresponde."""

    current_time = now or datetime.now(timezone.utc)
    with transactional_session(db):
        result = compute_customer_segments(db, now=current_time)

    if trigger_marketing:
        _dispatch_marketing_hooks(
            result.segments,
            generated_at=current_time,
            export_directory=export_directory,
        )
    return result


def ensure_segments_are_fresh(db: Session, *, now: datetime | None = None) -> None:
    """Lanza un recálculo cuando la data supera el TTL configurado."""

    current_time = now or datetime.now(timezone.utc)
    last_computed = db.scalar(
        select(func.max(models.CustomerSegmentSnapshot.computed_at))
    )
    if (
        last_computed is None
        or (current_time - last_computed).total_seconds()
        >= settings.customer_segment_ttl_seconds
    ):
        logger.info(
            "Regenerando segmentos por TTL vencido",
            last_computed=last_computed.isoformat() if last_computed else None,
        )
        refresh_customer_segments(
            db,
            now=current_time,
            trigger_marketing=False,
        )


def export_segment(
    db: Session,
    *,
    segment_key: str,
    export_format: str = "csv",
    now: datetime | None = None,
) -> tuple[str, str, str]:
    """Prepara el contenido exportable del segmento solicitado."""

    normalized_key = segment_key.strip().lower()
    if normalized_key not in _EXPORTABLE_SEGMENTS:
        raise ValueError("unknown_segment")
    if export_format != "csv":
        raise ValueError("unsupported_format")

    ensure_segments_are_fresh(db, now=now)

    customers_query = (
        select(models.Customer)
        .options(selectinload(models.Customer.segment_snapshot))
        .order_by(models.Customer.name.asc())
    )

    customers = db.scalars(customers_query).all()
    rows: list[customer_marketing.SegmentCustomer] = []
    for customer in customers:
        snapshot = customer.segment_snapshot
        if not snapshot:
            continue
        if normalized_key not in snapshot.segment_labels:
            continue
        rows.append(
            customer_marketing.SegmentCustomer(
                id=customer.id,
                name=customer.name,
                email=customer.email,
                phone=customer.phone,
                annual_purchase_amount=float(snapshot.annual_amount),
                orders_last_year=int(snapshot.orders_last_year),
                purchase_frequency=snapshot.frequency_label,
                segment_labels=list(snapshot.segment_labels),
                last_purchase_at=snapshot.last_sale_at.isoformat()
                if snapshot.last_sale_at
                else None,
            )
        )

    output_lines = [
        "id,nombre,correo,telefono,monto_anual,ordenes_anuales,frecuencia,etiquetas,ultima_compra"
    ]
    for customer in rows:
        output_lines.append(
            ",".join(
                [
                    str(customer.id),
                    _escape_csv(customer.name),
                    _escape_csv(customer.email or ""),
                    _escape_csv(customer.phone or ""),
                    f"{customer.annual_purchase_amount:.2f}",
                    str(customer.orders_last_year),
                    customer.purchase_frequency,
                    "|".join(customer.segment_labels),
                    customer.last_purchase_at or "",
                ]
            )
        )

    export_time = now or datetime.now(timezone.utc)
    filename = f"segmento_{normalized_key}_{export_time.strftime('%Y%m%d%H%M%S')}.csv"
    content = "\n".join(output_lines)
    media_type = "text/csv"
    return filename, content, media_type


def _dispatch_marketing_hooks(
    segments: dict[str, list[customer_marketing.SegmentCustomer]],
    *,
    generated_at: datetime,
    export_directory: str | None,
) -> None:
    targeted_segments = (
        set(settings.customer_segments_mailchimp_labels)
        | set(settings.customer_segments_sms_labels)
    )
    for segment_key in targeted_segments:
        customers = segments.get(segment_key, [])
        if not customers:
            continue
        export_path = customer_marketing.export_segment_csv(
            segment_key,
            customers,
            generated_at=generated_at,
            directory=export_directory,
        )
        logger.info(
            "Disparando hooks de marketing",
            segment=segment_key,
            customers=len(customers),
        )
        if segment_key in settings.customer_segments_mailchimp_labels:
            customer_marketing.push_to_mailchimp(
                segment_key,
                customers,
                generated_at=generated_at,
                directory=export_directory,
                export_path=export_path,
            )
        if segment_key in settings.customer_segments_sms_labels:
            customer_marketing.push_to_sms_gateway(
                segment_key,
                customers,
                generated_at=generated_at,
                export_path=export_path,
            )


def _resolve_frequency_label(orders: int) -> str:
    if orders >= settings.customer_segment_frequent_orders_threshold:
        return "frecuente"
    if orders >= settings.customer_segment_regular_orders_threshold:
        return "recurrente"
    if orders == 0:
        return "sin_compras"
    return "ocasional"


def _resolve_segment_labels(
    customer: models.Customer,
    annual_amount: Decimal,
    orders: int,
    last_sale_at: datetime | None,
    current_time: datetime,
) -> list[str]:
    labels: set[str] = set()

    if annual_amount >= settings.customer_segment_high_value_threshold:
        labels.add("alto_valor")
    elif annual_amount >= settings.customer_segment_medium_value_threshold:
        labels.add("valor_medio")
    else:
        labels.add("valor_bajo")

    frequency_label = _resolve_frequency_label(orders)
    labels.add(frequency_label)

    if last_sale_at is None:
        labels.add("recuperacion")
    else:
        if (current_time - last_sale_at).days >= settings.customer_segment_recovery_days:
            labels.add("recuperacion")
        if (current_time - last_sale_at).days <= settings.customer_segment_new_customer_days:
            labels.add("nuevo")

    if customer.customer_type.lower() in {"vip", "corporativo"}:
        labels.add("vip")

    if customer.status.lower() == "moroso":
        labels.add("moroso")

    return sorted(labels)


def _escape_csv(value: str) -> str:
    if "," in value or "\"" in value:
        sanitized = value.replace("\"", "\"\"")
        return f'"{sanitized}"'
    return value
