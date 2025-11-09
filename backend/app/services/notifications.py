"""Servicios de mensajería para correo electrónico y WhatsApp."""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable, Sequence, Tuple

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class NotificationError(RuntimeError):
    """Error base para problemas al enviar notificaciones."""


class EmailNotConfiguredError(NotificationError):
    """Se lanza cuando faltan credenciales o parámetros de correo."""


class WhatsAppNotConfiguredError(NotificationError):
    """Se lanza cuando faltan credenciales para la API de WhatsApp."""


class NotificationDeliveryError(NotificationError):
    """Falla genérica al intentar entregar una notificación."""


@dataclass(slots=True)
class Attachment:
    """Representa un archivo adjunto para los correos electrónicos."""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


def _build_email_message(
    *,
    subject: str,
    sender: str,
    recipients: Sequence[str],
    body: str,
    html_body: str | None = None,
    attachments: Iterable[Attachment] | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    for attachment in attachments or []:
        maintype, subtype = _split_content_type(attachment.content_type)
        message.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )
    return message


def _split_content_type(content_type: str) -> Tuple[str, str]:
    if "/" in content_type:
        maintype, subtype = content_type.split("/", 1)
        return maintype or "application", subtype or "octet-stream"
    return "application", content_type or "octet-stream"


def send_email_notification(
    *,
    recipients: Sequence[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: Iterable[Attachment] | None = None,
) -> None:
    """Envía un correo electrónico usando la configuración definida."""

    host = settings.notifications_email_host
    sender = settings.notifications_email_from
    if not host or not sender:
        raise EmailNotConfiguredError("email_not_configured")

    message = _build_email_message(
        subject=subject,
        sender=sender,
        recipients=recipients,
        body=body,
        html_body=html_body,
        attachments=attachments,
    )

    try:
        smtp = smtplib.SMTP(host, settings.notifications_email_port, timeout=15)
        try:
            if settings.notifications_email_use_tls:
                smtp.starttls()
            username = settings.notifications_email_username
            password = settings.notifications_email_password
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        finally:
            smtp.quit()
    except Exception as exc:  # pragma: no cover - dependencias externas
        logger.exception("Error enviando correo electrónico")
        raise NotificationDeliveryError("email_send_failed") from exc


async def send_whatsapp_message(
    *,
    to_number: str,
    message: str,
    media_url: str | None = None,
    reference: str | None = None,
) -> dict[str, object]:
    """Envía un mensaje mediante la API HTTP de WhatsApp configurada."""

    api_url = settings.notifications_whatsapp_api_url
    token = settings.notifications_whatsapp_token
    sender = settings.notifications_whatsapp_sender
    if not api_url or not token or not sender:
        raise WhatsAppNotConfiguredError("whatsapp_not_configured")

    payload: dict[str, object] = {
        "from": sender,
        "to": to_number,
        "message": message,
    }
    if media_url:
        payload["media_url"] = media_url
    if reference:
        payload["reference"] = reference

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    timeout = httpx.Timeout(settings.notifications_whatsapp_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, json=payload, headers=headers)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.exception("Error enviando mensaje de WhatsApp: %s", exc.response.text)
        raise NotificationDeliveryError("whatsapp_send_failed") from exc

    try:
        return response.json()
    except ValueError:  # pragma: no cover - respuesta sin JSON
        return {"status": "sent"}


__all__ = [
    "Attachment",
    "NotificationError",
    "EmailNotConfiguredError",
    "WhatsAppNotConfiguredError",
    "NotificationDeliveryError",
    "send_email_notification",
    "send_whatsapp_message",
]
