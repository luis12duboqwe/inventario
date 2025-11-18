"""Servicios auxiliares para documentos de órdenes de compra."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ..config import settings
from .. import models
from . import notifications

logger = logging.getLogger(__name__)


class PurchaseDocumentStorageError(RuntimeError):
    """Se lanza cuando no es posible operar con el backend de almacenamiento."""


@dataclass(slots=True)
class StoredDocument:
    """Representa un archivo almacenado en el backend configurado."""

    backend: str
    path: str


class PurchaseDocumentStorage:
    """API mínima para guardar y recuperar archivos adjuntos."""

    backend_name: str

    def save(self, *, filename: str, content_type: str, content: bytes) -> StoredDocument:
        raise NotImplementedError

    def open(self, path: str) -> bytes:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError


class _LocalPurchaseDocumentStorage(PurchaseDocumentStorage):
    backend_name = "local"

    def __init__(self, base_directory: Path) -> None:
        self._base_directory = base_directory
        self._base_directory.mkdir(parents=True, exist_ok=True)

    def save(self, *, filename: str, content_type: str, content: bytes) -> StoredDocument:
        safe_name = _build_storage_name(filename)
        target_path = self._base_directory / safe_name
        target_path.write_bytes(content)
        return StoredDocument(self.backend_name, str(target_path))

    def open(self, path: str) -> bytes:
        file_path = Path(path)
        if not file_path.is_file():
            raise PurchaseDocumentStorageError("document_not_found")
        return file_path.read_bytes()

    def delete(self, path: str) -> None:
        file_path = Path(path)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            logger.warning("No se pudo eliminar el archivo local %s", path)


class _S3PurchaseDocumentStorage(PurchaseDocumentStorage):
    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        region: str | None,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
    ) -> None:
        kwargs: dict[str, str] = {}
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        if region:
            kwargs["region_name"] = region
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("s3", **kwargs)
        self._bucket = bucket
        self._prefix = prefix.strip("/") if prefix else "purchase_orders"

    def save(self, *, filename: str, content_type: str, content: bytes) -> StoredDocument:
        key = f"{self._prefix}/{_build_storage_name(filename)}"
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - dependencias externas
            logger.exception("Error subiendo documento a S3")
            raise PurchaseDocumentStorageError("document_upload_failed") from exc
        return StoredDocument(self.backend_name, key)

    def open(self, path: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=path)
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - dependencias externas
            logger.exception("Error descargando documento de S3")
            raise PurchaseDocumentStorageError("document_download_failed") from exc
        body = response.get("Body")
        if body is None:
            raise PurchaseDocumentStorageError("document_download_failed")
        return body.read()

    def delete(self, path: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=path)
        except (BotoCoreError, ClientError):  # pragma: no cover - mejor esfuerzo
            logger.warning("No se pudo eliminar el documento %s en S3", path)


def _build_storage_name(filename: str) -> str:
    sanitized = Path(filename or "documento.pdf").name.replace(" ", "_")
    identifier = uuid4().hex
    return f"{identifier}_{sanitized}"


@lru_cache(maxsize=1)
def get_storage() -> PurchaseDocumentStorage:
    backend = settings.purchases_documents_backend
    if backend == "s3":
        bucket = settings.purchases_documents_s3_bucket
        if not bucket:
            raise PurchaseDocumentStorageError("s3_bucket_not_configured")
        return _S3PurchaseDocumentStorage(
            bucket=bucket,
            prefix=settings.purchases_documents_s3_prefix,
            region=settings.purchases_documents_s3_region,
            endpoint_url=settings.purchases_documents_s3_endpoint,
            access_key=settings.purchases_documents_s3_access_key,
            secret_key=settings.purchases_documents_s3_secret_key,
        )
    return _LocalPurchaseDocumentStorage(settings.purchases_documents_directory)


def render_purchase_order_pdf(order: models.PurchaseOrder) -> bytes:
    """Genera el PDF oficial de una orden de compra."""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"OrdenCompra_{order.id}")

    width, height = letter
    cursor_y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, cursor_y, f"Orden de compra #{order.id:05d}")
    cursor_y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, cursor_y, f"Sucursal: {order.store_id}")
    cursor_y -= 18
    pdf.drawString(50, cursor_y, f"Proveedor: {order.supplier}")
    cursor_y -= 18
    pdf.drawString(50, cursor_y, f"Estado: {order.status.value if hasattr(order.status, 'value') else order.status}")
    cursor_y -= 18
    pdf.drawString(50, cursor_y, f"Creada: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    cursor_y -= 18
    if order.closed_at:
        pdf.drawString(50, cursor_y, f"Cerrada: {order.closed_at.strftime('%Y-%m-%d %H:%M')}")
        cursor_y -= 18
    if order.notes:
        pdf.drawString(50, cursor_y, f"Notas: {order.notes}")
        cursor_y -= 24

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, cursor_y, "Detalle de artículos")
    cursor_y -= 20

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, cursor_y, "Producto")
    pdf.drawRightString(width - 200, cursor_y, "Ordenado")
    pdf.drawRightString(width - 120, cursor_y, "Recibido")
    pdf.drawRightString(width - 40, cursor_y, "Costo")
    cursor_y -= 16

    subtotal = 0.0
    recibido = 0.0
    for item in order.items:
        pdf.drawString(50, cursor_y, f"ID {item.device_id}")
        pdf.drawRightString(width - 200, cursor_y, str(item.quantity_ordered))
        pdf.drawRightString(width - 120, cursor_y, str(item.quantity_received))
        pdf.drawRightString(width - 40, cursor_y, f"${float(item.unit_cost):.2f}")
        subtotal += item.quantity_ordered * float(item.unit_cost)
        recibido += item.quantity_received * float(item.unit_cost)
        cursor_y -= 14
        if cursor_y < 120:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            cursor_y = height - 80

    pdf.setFont("Helvetica-Bold", 12)
    if cursor_y < 140:
        pdf.showPage()
        cursor_y = height - 80
        pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, cursor_y, "Resumen")
    cursor_y -= 20
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, cursor_y, f"Subtotal: ${subtotal:.2f}")
    cursor_y -= 16
    pdf.drawString(50, cursor_y, f"Recibido: ${recibido:.2f}")
    cursor_y -= 16
    pdf.drawString(50, cursor_y, f"Saldo pendiente: ${max(subtotal - recibido, 0):.2f}")
    cursor_y -= 24

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, cursor_y, "Historial de estados")
    cursor_y -= 20
    pdf.setFont("Helvetica", 10)
    events = sorted(
        getattr(order, "status_events", []),
        key=lambda event: event.created_at,
    )
    for event in events:
        status_value = event.status.value if hasattr(event.status, "value") else str(event.status)
        timestamp = event.created_at.strftime("%Y-%m-%d %H:%M")
        author = event.created_by.full_name if getattr(event.created_by, "full_name", None) else None
        note = event.note
        line = f"{timestamp} · {status_value}"
        if author:
            line = f"{line} · {author}"
        pdf.drawString(50, cursor_y, line)
        cursor_y -= 14
        if note:
            pdf.drawString(60, cursor_y, f"Nota: {note}")
            cursor_y -= 14
        if cursor_y < 120:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            cursor_y = height - 80

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_pdf_attachment(order: models.PurchaseOrder) -> notifications.Attachment:
    pdf_bytes = render_purchase_order_pdf(order)
    filename = f"orden_compra_{order.id:05d}.pdf"
    return notifications.Attachment(
        filename=filename,
        content=pdf_bytes,
        content_type="application/pdf",
    )


def send_purchase_order_email(
    *,
    order: models.PurchaseOrder,
    recipients: Iterable[str],
    message: str | None = None,
    include_documents: bool = False,
) -> None:
    """Envía la orden de compra oficial a los destinatarios indicados."""

    attachments: list[notifications.Attachment] = [build_pdf_attachment(order)]
    if include_documents:
        storage = get_storage()
        for document in getattr(order, "documents", []):
            try:
                content = storage.open(document.object_path)
            except PurchaseDocumentStorageError:
                logger.warning(
                    "No fue posible adjuntar el documento %s de la orden %s",
                    document.id,
                    order.id,
                )
                continue
            attachments.append(
                notifications.Attachment(
                    filename=document.filename,
                    content=content,
                    content_type=document.content_type or "application/octet-stream",
                )
            )

    body = message or (
        "Adjuntamos la orden de compra oficial generada desde Softmobile."
    )
    subject = f"Orden de compra #{order.id:05d}"

    notifications.send_email_notification(
        recipients=list(recipients),
        subject=subject,
        body=body,
        attachments=attachments,
    )


__all__ = [
    "PurchaseDocumentStorageError",
    "StoredDocument",
    "get_storage",
    "render_purchase_order_pdf",
    "build_pdf_attachment",
    "send_purchase_order_email",
]
