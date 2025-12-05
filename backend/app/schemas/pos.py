from __future__ import annotations
import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import (
    CashSessionStatus,
    PaymentMethod,
    CashEntryType,
)
from .pos_hardware import POSHardwareSettings, POSPrinterSettings, POSCashDrawerSettings, POSCustomerDisplaySettings

# Re-export POSAppliedPromotion if needed, or define it here if it belongs here.
# The user context showed POSAppliedPromotion in __init__.py, so I should define it here.
# But wait, sales.py imports it from .pos_hardware.
# If I define it here, I should update sales.py.


class CashDenominationInput(BaseModel):
    value: Decimal = Field(..., gt=Decimal("0"))
    quantity: int = Field(default=0, ge=0)

    @field_serializer("value")
    @classmethod
    def _serialize_value(cls, value: Decimal) -> float:
        return float(value)


class CashRegisterEntryBase(BaseModel):
    session_id: int = Field(..., ge=1)
    entry_type: CashEntryType
    amount: Decimal = Field(..., gt=Decimal("0"))
    reason: str = Field(..., min_length=5, max_length=255)
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashRegisterEntryCreate(CashRegisterEntryBase):
    pass


class CashRegisterEntryResponse(CashRegisterEntryBase):
    id: int
    created_by_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class CashSessionOpenRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    opening_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashSessionCloseRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    closing_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)
    denominations: list["CashDenominationInput"] = Field(default_factory=list)
    reconciliation_notes: str | None = Field(default=None, max_length=255)
    difference_reason: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("payment_breakdown", mode="before")
    @classmethod
    def _normalize_breakdown(cls, value: dict[str, Decimal] | None) -> dict[str, Decimal]:
        if value is None:
            return {}
        normalized: dict[str, Decimal] = {}
        for method_key, amount in value.items():
            method = method_key.strip().upper()
            try:
                PaymentMethod(method)
            except ValueError as exc:
                raise ValueError("Método de pago inválido.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized

    @field_validator("reconciliation_notes", "difference_reason")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashSessionResponse(BaseModel):
    id: int
    store_id: int
    status: CashSessionStatus
    opening_amount: Decimal
    closing_amount: Decimal
    expected_amount: Decimal
    difference_amount: Decimal
    payment_breakdown: dict[str, float]
    denomination_breakdown: dict[str, int]
    reconciliation_notes: str | None
    difference_reason: str | None
    notes: str | None
    opened_by_id: int | None
    closed_by_id: int | None
    opened_at: datetime
    closed_at: datetime | None
    entries: list["CashRegisterEntryResponse"] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "opening_amount",
        "closing_amount",
        "expected_amount",
        "difference_amount",
    )
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @field_serializer("denomination_breakdown")
    @classmethod
    def _serialize_denominations(cls, value: dict[str, int]) -> dict[str, int]:
        return {str(denomination): int(count) for denomination, count in value.items()}


class POSSessionOpenPayload(BaseModel):
    """Carga útil para aperturas de caja rápidas desde POS (branch/store alias)."""

    branch_id: int = Field(..., ge=1)
    opening_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_open_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "branch_id" not in data:
            for k in ("branchId", "store_id"):
                if k in data:
                    data["branch_id"] = data[k]
                    break
        return data

    @field_validator("notes")
    @classmethod
    def _normalize_pos_session_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class POSSessionClosePayload(BaseModel):
    """Datos requeridos para cerrar sesiones POS."""

    # // [PACK34-schema]
    session_id: int = Field(..., ge=1)
    closing_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    payments: dict[str, Decimal] = Field(default_factory=dict)
    difference_reason: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_close_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("payments", mode="before")
    @classmethod
    def _normalize_payments(
        cls, value: dict[str, Decimal] | list[dict[str, Decimal | str]] | None
    ) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        if value is None:
            return normalized
        if isinstance(value, dict):
            source = value.items()
        else:
            source = []
            for entry in value:
                method = str(entry.get("method") or entry.get(
                    "paymentMethod") or "").strip()
                amount = entry.get("amount") or entry.get("value")
                if not method:
                    continue
                source.append((method, amount))
        for raw_method, raw_amount in source:
            method_key = str(raw_method).strip().upper()
            try:
                PaymentMethod(method_key)
            except ValueError as exc:
                raise ValueError("Método de pago inválido.") from exc
            normalized[method_key] = Decimal(str(raw_amount))
        return normalized


class POSSessionSummary(BaseModel):
    """Resumen compacto de sesiones POS para la UI."""

    # // [PACK34-schema]
    session_id: int
    branch_id: int
    status: CashSessionStatus
    opened_at: datetime
    closing_at: datetime | None = None
    opening_amount: Decimal | None = None
    closing_amount: Decimal | None = None
    expected_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    payment_breakdown: dict[str, float] = Field(default_factory=dict)
    denomination_breakdown: dict[str, int] = Field(default_factory=dict)
    reconciliation_notes: str | None = None
    difference_reason: str | None = None

    @classmethod
    def from_model(cls, session: Any) -> "POSSessionSummary":
        # // [PACK34-schema]
        return cls(
            session_id=session.id,
            branch_id=session.store_id,
            status=session.status,
            opened_at=session.opened_at,
            closing_at=session.closed_at,
            opening_amount=getattr(session, "opening_amount", None),
            closing_amount=getattr(session, "closing_amount", None),
            expected_amount=getattr(session, "expected_amount", None),
            difference_amount=getattr(session, "difference_amount", None),
            payment_breakdown={
                key: float(value) for key, value in (session.payment_breakdown or {}).items()
            },
            denomination_breakdown={
                str(key): int(count)
                for key, count in (session.denomination_breakdown or {}).items()
            },
            reconciliation_notes=getattr(
                session, "reconciliation_notes", None),
            difference_reason=getattr(session, "difference_reason", None),
        )

    @field_serializer(
        "opening_amount",
        "closing_amount",
        "expected_amount",
        "difference_amount",
    )
    @classmethod
    def _serialize_optional_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("denomination_breakdown")
    @classmethod
    def _serialize_optional_denominations(cls, value: dict[str, int]) -> dict[str, int]:
        return {str(denomination): int(count) for denomination, count in value.items()}


class POSSessionPageResponse(BaseModel):
    """Respuesta paginada para historiales de sesiones POS."""

    items: list[POSSessionSummary] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)


class AsyncJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncJobResponse(BaseModel):
    id: str
    session_id: int
    job_type: str
    status: AsyncJobStatus
    output_path: str | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class POSTaxInfo(BaseModel):
    """Catálogo simple de impuestos POS."""

    # // [PACK34-schema]
    code: str
    name: str
    rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))

    @field_serializer("rate")
    @classmethod
    def _serialize_tax_rate(cls, value: Decimal) -> float:
        return float(value)


class POSPaymentToken(BaseModel):
    """Token de pago electrónico (bancario) para POS."""

    token: str = Field(..., min_length=1, max_length=128)


class POSTerminalConfig(BaseModel):
    id: str
    label: str
    adapter: str
    currency: str

    @field_validator("id", "label", "adapter", "currency")
    @classmethod
    def _normalize_terminal_str(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Los campos de terminal no pueden estar vacíos")
        return normalized


class POSConfigResponse(BaseModel):
    store_id: int
    tax_rate: Decimal
    invoice_prefix: str
    printer_name: str | None
    printer_profile: str | None
    quick_product_ids: list[int]
    hardware_settings: POSHardwareSettings = Field(
        default_factory=POSHardwareSettings
    )
    updated_at: datetime
    terminals: list[POSTerminalConfig] = Field(default_factory=list)
    tip_suggestions: list[float] = Field(default_factory=list)
    default_document_type: str = Field(default="TICKET")
    document_catalog: list[dict[str, str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("tax_rate")
    @classmethod
    def _serialize_tax(cls, value: Decimal) -> float:
        return float(value)

    @classmethod
    def from_model(
        cls,
        config: Any,
        *,
        terminals: dict[str, dict[str, Any]],
        tip_suggestions: list[Decimal],
    ) -> "POSConfigResponse":

        terminals_payload = [
            POSTerminalConfig(
                id=terminal_id,
                label=str(data.get("label") or terminal_id),
                adapter=str(data.get("adapter")
                            or "").strip() or "banco_atlantida",
                currency=str(data.get("currency") or "HNL"),
            )
            for terminal_id, data in terminals.items()
        ]
        hw = config.hardware_settings if isinstance(
            config.hardware_settings, dict) else {}
        default_doc = str(hw.get("default_document_type")
                          or "TICKET").strip().upper() or "TICKET"
        catalog = [
            {"type": "TICKET", "name": "Ticket POS",
                "description": "Documento no fiscal"},
            {"type": "FACTURA", "name": "Factura",
                "description": "Documento fiscal"},
            {"type": "NOTA_CREDITO", "name": "Nota de crédito",
                "description": "Documento fiscal"},
            {"type": "NOTA_DEBITO", "name": "Nota de débito",
                "description": "Documento fiscal"},
        ]
        # Normaliza hardware_settings al esquema público
        try:
            normalized_hw = POSHardwareSettings(
                printers=[POSPrinterSettings(**p)
                          for p in (hw.get("printers") or [])],
                cash_drawer=POSCashDrawerSettings(
                    **(hw.get("cash_drawer") or {})),
                customer_display=POSCustomerDisplaySettings(
                    **(hw.get("customer_display") or {})),
            )
        except Exception:
            # Si el JSON almacenado no coincide exactamente, cae a defaults seguros
            normalized_hw = POSHardwareSettings()
        return cls(
            store_id=config.store_id,
            tax_rate=config.tax_rate,
            invoice_prefix=config.invoice_prefix,
            printer_name=config.printer_name,
            printer_profile=config.printer_profile,
            quick_product_ids=list(config.quick_product_ids or []),
            hardware_settings=normalized_hw,
            updated_at=config.updated_at,
            terminals=terminals_payload,
            tip_suggestions=[float(Decimal(str(value)))
                             for value in tip_suggestions],
            default_document_type=default_doc,
            document_catalog=catalog,
        )


class POSPromotionFeatureFlags(BaseModel):
    volume: bool = False
    combos: bool = False
    coupons: bool = False


class POSVolumePromotion(BaseModel):
    id: str = Field(..., min_length=1, max_length=60)
    device_id: int = Field(..., ge=1)
    min_quantity: int = Field(..., ge=1)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)


class POSComboPromotionItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class POSComboPromotion(BaseModel):
    id: str = Field(..., min_length=1, max_length=60)
    items: list[POSComboPromotionItem] = Field(default_factory=list)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[POSComboPromotionItem]) -> list[POSComboPromotionItem]:
        if not value:
            raise ValueError("Los combos deben incluir al menos un artículo.")
        return value


class POSCouponPromotion(BaseModel):
    code: str = Field(..., min_length=3, max_length=40)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))
    description: str | None = Field(default=None, max_length=120)

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)


class POSPromotionsConfig(BaseModel):
    feature_flags: POSPromotionFeatureFlags = Field(
        default_factory=POSPromotionFeatureFlags)
    volume_promotions: list[POSVolumePromotion] = Field(default_factory=list)
    combo_promotions: list[POSComboPromotion] = Field(default_factory=list)
    coupons: list[POSCouponPromotion] = Field(default_factory=list)


class POSPromotionsUpdate(POSPromotionsConfig):
    store_id: int = Field(..., ge=1)


class POSPromotionsResponse(POSPromotionsConfig):
    store_id: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class POSAppliedPromotion(BaseModel):
    id: str
    promotion_type: Literal["volume", "combo", "coupon"]
    description: str
    discount_percent: Decimal = Field(default=Decimal(
        "0"), ge=Decimal("0"), le=Decimal("100"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    affected_items: list[int] = Field(default_factory=list)
    coupon_code: str | None = Field(default=None, max_length=60)

    @field_serializer("discount_percent", "discount_amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class POSConfigUpdate(BaseModel):
    store_id: int = Field(..., ge=1)
    tax_rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    invoice_prefix: str = Field(..., min_length=1, max_length=12)
    printer_name: str | None = Field(default=None, max_length=120)
    printer_profile: str | None = Field(default=None, max_length=255)
    quick_product_ids: list[int] = Field(default_factory=list)
    hardware_settings: POSHardwareSettings | None = Field(default=None)
    default_document_type: str | None = Field(default=None)

    @field_validator("quick_product_ids")
    @classmethod
    def _validate_quick_products(cls, value: list[int]) -> list[int]:
        normalized = []
        for item in value:
            if int(item) < 1:
                raise ValueError(
                    "Los identificadores rápidos deben ser positivos.")
            normalized.append(int(item))
        return normalized

    @field_validator("default_document_type")
    @classmethod
    def _normalize_default_doc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        allowed = {"FACTURA", "TICKET", "NOTA_CREDITO", "NOTA_DEBITO"}
        if normalized and normalized not in allowed:
            raise ValueError("Tipo de documento por defecto inválido")
        return normalized or None
