"""Monitoreo de riesgo operacional sobre ventas."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from . import notifications

logger = logging.getLogger(__name__)


def _default_range(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    end = date_to or now
    start = date_from or now - timedelta(days=30)
    return start, end


def _gather_discount_metrics(db: Session, date_from: datetime, date_to: datetime) -> schemas.RiskMetric:
    base = (
        select(
            func.count(models.Sale.id),
            func.avg(models.Sale.discount_percent),
            func.max(models.Sale.discount_percent),
        )
        .where(models.Sale.created_at >= date_from)
        .where(models.Sale.created_at <= date_to)
        .where(func.upper(models.Sale.status) != "CANCELADA")
    )
    count, avg_discount, max_discount = db.execute(base).one()
    return schemas.RiskMetric(
        total=count or 0,
        average=float(avg_discount or 0),
        maximum=float(max_discount or 0),
    )


def _gather_cancellation_metrics(db: Session, date_from: datetime, date_to: datetime) -> schemas.RiskMetric:
    base = (
        select(func.count(models.Sale.id), func.max(models.Sale.updated_at))
        .where(func.upper(models.Sale.status) == "CANCELADA")
        .where(models.Sale.created_at >= date_from)
        .where(models.Sale.created_at <= date_to)
    )
    total, last_seen = db.execute(base).one()
    return schemas.RiskMetric(
        total=total or 0,
        average=0,
        maximum=0,
        last_seen=last_seen,
    )


def _build_discount_alert(metric: schemas.RiskMetric, threshold: float) -> schemas.RiskAlert | None:
    if metric.maximum < threshold:
        return None
    severity = "media" if metric.maximum < (threshold + 10) else "alta"
    if metric.maximum >= threshold + 20:
        severity = "critica"
    return schemas.RiskAlert(
        code="discount_spikes",
        title="Descuentos inusuales detectados",
        description=(
            "Se registraron ventas con descuentos superiores al umbral permitido."
            " Revisa aprobaciones y justificaciones de los supervisores."
        ),
        severity=severity,
        occurrences=metric.total,
        detail={
            "promedio": metric.average,
            "maximo": metric.maximum,
            "umbral": threshold,
        },
    )


def _build_cancellation_alert(metric: schemas.RiskMetric, threshold: int) -> schemas.RiskAlert | None:
    if metric.total < threshold:
        return None
    severity = "media" if metric.total == threshold else "alta"
    if metric.total >= threshold * 2:
        severity = "critica"
    return schemas.RiskAlert(
        code="cancellations_peak",
        title="Aumento de anulaciones",
        description=(
            "Las anulaciones recientes superan el rango esperado."
            " Verifica motivos corporativos y reversiones de inventario."
        ),
        severity=severity,
        occurrences=metric.total,
        detail={"ultima_anulacion": metric.last_seen.isoformat() if metric.last_seen else None},
    )


def compute_risk_alerts(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    discount_threshold: float = 25.0,
    cancellation_threshold: int = 3,
) -> schemas.RiskAlertsResponse:
    start, end = _default_range(date_from, date_to)
    discount_metric = _gather_discount_metrics(db, start, end)
    cancellation_metric = _gather_cancellation_metrics(db, start, end)

    alerts: list[schemas.RiskAlert] = []
    for builder in (
        lambda: _build_discount_alert(discount_metric, discount_threshold),
        lambda: _build_cancellation_alert(cancellation_metric, cancellation_threshold),
    ):
        alert = builder()
        if alert:
            alerts.append(alert)

    return schemas.RiskAlertsResponse(
        generated_at=datetime.utcnow(),
        alerts=alerts,
        metrics={
            "discounts": discount_metric,
            "cancellations": cancellation_metric,
        },
    )


def _notify_by_email(alerts: Iterable[schemas.RiskAlert]) -> bool:
    recipients = [email for email in settings.risk_alert_email_recipients if email]
    if not recipients:
        return False
    critical = [alert for alert in alerts if alert.severity in {"alta", "critica"}]
    if not critical:
        return False
    body_lines = [
        "Alertas críticas detectadas en Softmobile:",
        "",
    ]
    for alert in critical:
        body_lines.append(f"- {alert.title}: {alert.description} (ocurrencias: {alert.occurrences})")
    try:
        notifications.send_email_notification(
            recipients=recipients,
            subject="Alertas críticas de riesgo operativo",
            body="\n".join(body_lines),
        )
        return True
    except notifications.NotificationError:
        logger.exception("No se pudo enviar la alerta crítica por correo")
        return False


def _notify_by_webhook(alerts: Iterable[schemas.RiskAlert]) -> bool:
    webhook = settings.risk_alert_webhook_url
    if not webhook:
        return False
    payload = {
        "source": "softmobile-risk-monitor",
        "alerts": [alert.model_dump() for alert in alerts],
    }
    try:
        response = httpx.post(webhook, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception:  # pragma: no cover - integración externa
        logger.exception("No se pudo enviar la alerta crítica por webhook")
        return False


def dispatch_risk_notifications(alerts: Iterable[schemas.RiskAlert]) -> set[str]:
    delivered: set[str] = set()
    critical = [alert for alert in alerts if alert.severity in {"alta", "critica"}]
    if not critical:
        return delivered

    if _notify_by_email(critical):
        delivered.add("email")
    if _notify_by_webhook(critical):
        delivered.add("push")
    return delivered


__all__ = [
    "compute_risk_alerts",
    "dispatch_risk_notifications",
]
