from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from ... import models, schemas
from .. import audit_logger
from .base import PaymentExecutionError, PaymentToken, PaymentTokenizationError
from .registry import registry


class ElectronicPaymentError(RuntimeError):
    """Error controlado al procesar pagos electrónicos POS."""

    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = metadata or {}


def _currency_from_terminal(terminal_cfg: dict[str, Any]) -> str:
    currency = str(terminal_cfg.get("currency") or "HNL").strip().upper()
    return currency or "HNL"


def _metadata_payload(
    payment: schemas.POSSalePaymentInput,
    payload: schemas.POSSaleRequest,
    *,
    terminal_cfg: dict[str, Any],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "terminal_id": payment.terminal_id,
        "method": payment.method.value,
        "store_id": payload.store_id,
    }
    if payment.reference:
        metadata["reference"] = payment.reference
    if payment.metadata:
        metadata.update(payment.metadata)
    metadata["terminal_label"] = terminal_cfg.get("label")
    return metadata


def process_electronic_payments(
    db: Session,
    *,
    payments: Iterable[schemas.POSSalePaymentInput],
    payload: schemas.POSSaleRequest,
    user_id: int | None,
    terminals_config: dict[str, dict[str, Any]],
) -> list[schemas.POSElectronicPaymentResult]:
    """Tokeniza, inicia y confirma pagos electrónicos, devolviendo el resumen normalizado."""

    results: list[schemas.POSElectronicPaymentResult] = []
    for payment in payments:
        if payment.method not in {
            models.PaymentMethod.TARJETA,
            models.PaymentMethod.TRANSFERENCIA,
        }:
            continue
        terminal_id = (payment.terminal_id or "").strip()
        if not terminal_id:
            raise ElectronicPaymentError(
                "Debes seleccionar un terminal electrónico.",
                metadata={"method": payment.method.value},
            )
        terminal_cfg = terminals_config.get(terminal_id)
        if terminal_cfg is None:
            raise ElectronicPaymentError(
                "El terminal seleccionado no está configurado.",
                metadata={"terminal_id": terminal_id},
            )
        adapter_key = str(terminal_cfg.get("adapter") or "").strip().lower()
        if not adapter_key:
            raise ElectronicPaymentError(
                "El terminal no tiene adaptador asociado.",
                metadata={"terminal_id": terminal_id},
            )
        try:
            adapter = registry.get(adapter_key)
        except LookupError as exc:  # pragma: no cover - configuración inválida
            raise ElectronicPaymentError(
                "No se encontró el adaptador bancario requerido.",
                metadata={"adapter": adapter_key},
            ) from exc

        metadata_payload = _metadata_payload(payment, payload, terminal_cfg=terminal_cfg)
        token_payload = {
            "reference": payment.reference or payment.token or terminal_id,
            "cardholder": payment.metadata.get("cardholder") if payment.metadata else None,
        }
        try:
            token = (
                adapter.tokenize(token_payload)
                if not payment.token
                else PaymentToken(token=payment.token)
            )
        except PaymentTokenizationError as exc:
            audit_logger.record_audit_event(
                db,
                action="pos.payment.tokenization_failed",
                entity_type="pos_sale",
                entity_id=str(payload.store_id),
                user_id=user_id,
                metadata={"error": str(exc), "details": exc.metadata},
            )
            raise ElectronicPaymentError("Falló la tokenización del pago electrónico.") from exc

        amount = Decimal(payment.amount)
        if payment.tip_amount is not None:
            amount += Decimal(payment.tip_amount)
        currency = _currency_from_terminal(terminal_cfg)
        try:
            initiation = adapter.initiate(
                token=token if isinstance(token, schemas.POSPaymentToken) else token,
                amount=amount,
                currency=currency,
                metadata=metadata_payload,
            )
            confirmation = adapter.confirm(
                initiation=initiation,
                amount=amount,
                currency=currency,
                metadata=metadata_payload,
            )
        except PaymentExecutionError as exc:
            audit_logger.record_audit_event(
                db,
                action="pos.payment.execution_failed",
                entity_type="pos_sale",
                entity_id=str(payload.store_id),
                user_id=user_id,
                metadata={
                    "error": str(exc),
                    "details": getattr(exc, "metadata", {}),
                    "terminal": terminal_id,
                },
            )
            raise ElectronicPaymentError("El pago electrónico fue rechazado por el banco.") from exc

        result = schemas.POSElectronicPaymentResult(
            terminal_id=terminal_id,
            method=payment.method,
            transaction_id=confirmation.transaction_id,
            status=confirmation.status,
            approval_code=confirmation.approval_code,
            reconciled=confirmation.reconciled,
            tip_amount=payment.tip_amount,
        )
        results.append(result)
        audit_logger.record_audit_event(
            db,
            action="pos.payment.confirmed",
            entity_type="pos_sale",
            entity_id=str(payload.store_id),
            user_id=user_id,
            metadata={
                "terminal": terminal_id,
                "transaction_id": confirmation.transaction_id,
                "status": confirmation.status,
                "approval": confirmation.approval_code,
            },
        )
    return results


__all__ = ["process_electronic_payments", "ElectronicPaymentError"]
