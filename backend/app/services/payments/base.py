from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol


class PaymentTokenizationError(RuntimeError):
    """Señala un fallo al tokenizar un instrumento de pago."""

    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = metadata or {}


class PaymentExecutionError(RuntimeError):
    """Señala un fallo al iniciar o confirmar un cargo electrónico."""

    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = metadata or {}


@dataclass(slots=True)
class PaymentToken:
    token: str
    expires_at: datetime | None = None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class PaymentInitiation:
    transaction_id: str
    status: str
    raw: dict[str, Any]


@dataclass(slots=True)
class PaymentConfirmation:
    transaction_id: str
    status: str
    approval_code: str | None = None
    reconciliation_id: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def reconciled(self) -> bool:
        normalized = (self.status or "").strip().lower()
        return normalized in {"confirmed", "settled", "reconciled"}


class HondurasBankClient(Protocol):
    """Interfaz genérica para SDKs bancarios hondureños."""

    def tokenize(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def create_payment(
        self,
        *,
        token: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def confirm_payment(
        self,
        *,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class HondurasPaymentAdapter(Protocol):
    """Adaptador para un proveedor bancario hondureño específico."""

    name: str

    def tokenize(self, payload: dict[str, Any]) -> PaymentToken:
        ...

    def initiate(
        self,
        *,
        token: PaymentToken,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentInitiation:
        ...

    def confirm(
        self,
        *,
        initiation: PaymentInitiation,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentConfirmation:
        ...


__all__ = [
    "PaymentToken",
    "PaymentInitiation",
    "PaymentConfirmation",
    "PaymentTokenizationError",
    "PaymentExecutionError",
    "HondurasBankClient",
    "HondurasPaymentAdapter",
]
