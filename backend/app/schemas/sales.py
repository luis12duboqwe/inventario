from __future__ import annotations
import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import (
    PaymentMethod,
    ReturnDisposition,
    ReturnReasonCategory,
    WarrantyClaimStatus,
    WarrantyClaimType,
    WarrantyStatus,
    DTEStatus,
    CashSessionStatus,
)
from .audit import AuditTrailInfo
from .customers import (
    CustomerDebtSnapshot,
    CreditScheduleEntry,
    CustomerPaymentReceiptResponse,
    LoyaltyAccountSummary,
)
from .pos import POSAppliedPromotion


class SaleItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )
    batch_code: str | None = Field(default=None, max_length=80)
    unit_price_override: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=Decimal("0"),
            validation_alias=AliasChoices("unit_price_override", "price"),
        ),
    ]  # // [PACK34-schema]
    reservation_id: int | None = Field(default=None, ge=1)

    @field_validator("discount_percent")
    @classmethod
    def _normalize_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @field_validator("batch_code")
    @classmethod
    def _normalize_sale_batch(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SaleCreate(BaseModel):
    store_id: int = Field(..., ge=1)  # // [PACK30-31-BACKEND]
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    status: str = Field(default="COMPLETADA", max_length=30)
    notes: str | None = Field(default=None, max_length=255)
    items: list[SaleItemCreate]

    @model_validator(mode="before")
    @classmethod
    def _coerce_sale_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        if "store_id" not in data:
            for k in ("branch_id",):
                if k in data:
                    data["store_id"] = data[k]
                    break
        return data

    @field_validator("customer_name")
    @classmethod
    def _normalize_customer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_sale_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "COMPLETADA"

    @field_validator("items")
    @classmethod
    def _ensure_sale_items(cls, value: list[SaleItemCreate]) -> list[SaleItemCreate]:
        if not value:
            raise ValueError("Debes agregar artículos a la venta.")
        return value


class SaleUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    status: str = Field(default="COMPLETADA", max_length=30)
    notes: str | None = Field(default=None, max_length=255)
    items: list[SaleItemCreate]

    @field_validator("customer_name")
    @classmethod
    def _normalize_update_customer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_update_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def _normalize_update_status(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "COMPLETADA"

    @field_validator("items")
    @classmethod
    def _ensure_update_items(cls, value: list[SaleItemCreate]) -> list[SaleItemCreate]:
        if not value:
            raise ValueError("Debes agregar artículos a la venta.")
        return value


class SaleStoreSummary(BaseModel):
    id: int
    name: str
    location: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleUserSummary(BaseModel):
    id: int
    username: str
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleDeviceSummary(BaseModel):
    id: int
    sku: str
    name: str
    modelo: str | None = None
    imei: str | None = None
    serial: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WarrantyDeviceSummary(BaseModel):
    id: int
    sku: str
    name: str
    imei: str | None = None
    serial: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WarrantySaleSummary(BaseModel):
    id: int
    store_id: int
    customer_id: int | None = None
    customer_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarrantyClaimCreate(BaseModel):
    claim_type: WarrantyClaimType
    notes: str | None = Field(default=None, max_length=500)
    repair_order_id: int | None = Field(default=None, ge=1)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WarrantyClaimStatusUpdate(BaseModel):
    status: WarrantyClaimStatus
    notes: str | None = Field(default=None, max_length=500)
    resolved_at: datetime | None = None

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WarrantyMetrics(BaseModel):
    active_warranties: int
    claims_open: int
    claims_resolved_30d: int
    claims_rejected_30d: int


class WarrantyClaimResponse(BaseModel):
    id: int
    claim_type: WarrantyClaimType
    status: WarrantyClaimStatus
    notes: str | None = None
    opened_at: datetime
    resolved_at: datetime | None = None
    repair_order_id: int | None = None
    performed_by_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class WarrantyAssignmentResponse(BaseModel):
    id: int
    sale_item_id: int
    device_id: int
    coverage_months: int
    activation_date: date
    expiration_date: date
    status: WarrantyStatus
    serial_number: str | None = None
    activation_channel: str | None = None
    created_at: datetime
    updated_at: datetime
    device: WarrantyDeviceSummary | None = None
    sale: WarrantySaleSummary | None = None
    claims: list[WarrantyClaimResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def remaining_days(self) -> int:
        today = date.today()
        return max((self.expiration_date - today).days, 0)

    @computed_field
    @property
    def is_expired(self) -> bool:
        return self.expiration_date < date.today()


class SaleItemResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    total_line: Decimal
    device: SaleDeviceSummary | None = None
    reservation_id: int | None = None
    warranty_status: WarrantyStatus | None = None
    warranty: WarrantyAssignmentResponse | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price", "discount_amount", "total_line")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class SaleCustomerSummary(BaseModel):
    id: int
    name: str
    outstanding_debt: Decimal
    loyalty_account: LoyaltyAccountSummary | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class CashSessionSummary(BaseModel):
    id: int
    status: CashSessionStatus
    opened_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str | None
    document_type: str | None = None
    document_number: str | None = None
    payment_method: PaymentMethod
    discount_percent: Decimal
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    loyalty_points_earned: Decimal = Field(default=Decimal("0"))
    loyalty_points_redeemed: Decimal = Field(default=Decimal("0"))
    status: str
    notes: str | None
    invoice_reported: bool = False
    invoice_reported_at: datetime | None = None
    invoice_annulled_at: datetime | None = None
    invoice_credit_note_code: str | None = None
    created_at: datetime
    performed_by_id: int | None
    cash_session_id: int | None
    customer: SaleCustomerSummary | None = None
    cash_session: CashSessionSummary | None = None
    items: list[SaleItemResponse]
    returns: list["SaleReturnResponse"] = []
    store: SaleStoreSummary | None = None
    performed_by: SaleUserSummary | None = None
    dte_status: DTEStatus | None = None
    dte_reference: str | None = None
    ultima_accion: AuditTrailInfo | None = None
    loyalty_account: LoyaltyAccountSummary | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "discount_percent",
        "subtotal_amount",
        "tax_amount",
        "total_amount",
        "loyalty_points_earned",
        "loyalty_points_redeemed",
    )
    @classmethod
    def _serialize_sale_amount(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(alias="fecha", return_type=datetime)
    def fecha_operacion(self) -> datetime:
        return self.created_at


class SaleReturnItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)
    disposition: ReturnDisposition = Field(
        default=ReturnDisposition.VENDIBLE
    )
    warehouse_id: int | None = Field(default=None, ge=1)
    category: ReturnReasonCategory = Field(
        default=ReturnReasonCategory.CLIENTE
    )

    @field_validator("reason")
    @classmethod
    def _normalize_sale_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class ReturnApprovalRequest(BaseModel):
    supervisor_username: str = Field(..., min_length=3, max_length=120)
    pin: str = Field(..., min_length=4, max_length=64)


class SaleReturnCreate(BaseModel):
    sale_id: int = Field(..., ge=1)
    items: list[SaleReturnItem]
    approval: ReturnApprovalRequest | None = None

    @field_validator("items")
    @classmethod
    def _ensure_return_items(cls, value: list[SaleReturnItem]) -> list[SaleReturnItem]:
        if not value:
            raise ValueError("Debes indicar artículos a devolver.")
        return value


class SaleReturnResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    reason: str
    reason_category: ReturnReasonCategory
    disposition: ReturnDisposition
    warehouse_id: int | None
    processed_by_id: int | None
    approved_by_id: int | None
    approved_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field(alias="fecha", return_type=datetime)
    def fecha_registro(self) -> datetime:
        return self.created_at


class SaleHistorySearchResponse(BaseModel):
    by_ticket: list[SaleResponse] = Field(default_factory=list)
    by_date: list[SaleResponse] = Field(default_factory=list)
    by_customer: list[SaleResponse] = Field(default_factory=list)
    by_qr: list[SaleResponse] = Field(default_factory=list)


class SalesReportFilters(BaseModel):
    store_id: int | None = None
    customer_id: int | None = None
    performed_by_id: int | None = None
    product_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    query: str | None = None


class SalesReportTotals(BaseModel):
    count: int
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    cost: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    daily_average: Decimal = Decimal("0")

    @field_serializer("subtotal", "tax", "total", "cost", "net_income", "daily_average")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class SalesReportItem(BaseModel):
    sale_id: int
    folio: str
    store_name: str
    customer_name: str | None
    performed_by: str | None
    payment_method: PaymentMethod
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    created_at: datetime
    items: list[SaleItemResponse]
    ultima_accion: AuditTrailInfo | None = None

    @field_serializer("subtotal", "tax", "total")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class SalesReportGroup(BaseModel):
    id: int | None
    name: str
    total: Decimal
    count: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class SalesReportProduct(BaseModel):
    product_id: int
    sku: str | None
    name: str
    units: int
    total: Decimal

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class SalesReport(BaseModel):
    generated_at: datetime
    filters: SalesReportFilters
    totals: SalesReportTotals
    # DashboardChartPoint is circular import if not careful
    daily_stats: list[Any]
    items: list[SalesReportItem]
    by_store: list[SalesReportGroup] = Field(default_factory=list)
    by_user: list[SalesReportGroup] = Field(default_factory=list)
    top_products: list[SalesReportProduct] = Field(default_factory=list)


class POSCartItem(BaseModel):
    """Elemento del carrito POS aceptando identificadores flexibles."""

    # // [PACK34-schema]
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, max_length=18)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    tax_code: str | None = Field(default=None, max_length=50)
    reservation_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("discount_percent")
    @classmethod
    def _normalize_pos_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @model_validator(mode="before")
    @classmethod
    def _coerce_cart_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        mapping = {
            "device_id": ["productId", "product_id"],
            "imei": ["imei_1", "imei1"],
            "quantity": ["qty"],
            "discount_percent": ["discount"],
            "unit_price_override": ["price"],
            "tax_code": ["taxCode"],
        }
        for target, sources in mapping.items():
            if target not in data:
                for s in sources:
                    if s in data:
                        data[target] = data[s]
                        break
        return data


class POSSalePaymentInput(BaseModel):
    """Definición de pago para registrar montos por método."""

    # // [PACK34-schema]
    method: PaymentMethod
    amount: Decimal = Field(..., ge=Decimal("0"))
    reference: str | None = Field(default=None, max_length=64)
    terminal_id: str | None = Field(
        default=None, max_length=40, alias="terminalId")
    tip_amount: Decimal | None = Field(
        default=None, ge=Decimal("0"), alias="tipAmount")
    token: str | None = Field(default=None, max_length=128)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_method_alias(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "method" not in data:
            for k in ("paymentMethod",):
                if k in data:
                    data["method"] = data[k]
                    break
        return data

    @field_validator("reference", "terminal_id", "token")
    @classmethod
    def _normalize_optional_str(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("metadata", mode="before")
    @classmethod
    def _ensure_metadata(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
        raise ValueError("metadata debe ser un diccionario de texto")


class POSSaleRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )
    notes: str | None = Field(default=None, max_length=255)
    items: list[POSCartItem]
    draft_id: int | None = Field(default=None, ge=1)
    save_as_draft: bool = Field(default=False)
    confirm: bool = Field(default=False)
    apply_taxes: bool = Field(default=True)
    coupons: list[str] = Field(default_factory=list)
    cash_session_id: int | None = Field(default=None, ge=1)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)
    payments: list[POSSalePaymentInput] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("customer_name")
    @classmethod
    def _normalize_pos_customer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_pos_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_pos_items(cls, value: list[POSCartItem]) -> list[POSCartItem]:
        if not value:
            raise ValueError("Debes agregar dispositivos al carrito.")
        return value

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
            except ValueError as exc:  # pragma: no cover - validation error path
                raise ValueError(
                    "Método de pago inválido en el desglose.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized

    @field_validator("coupons")
    @classmethod
    def _normalize_coupons(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            trimmed = (raw or "").strip()
            if len(trimmed) < 3:
                continue
            code = trimmed.upper()
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return normalized

    @model_validator(mode="before")
    @classmethod
    def _coerce_pos_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        mapping = {
            "store_id": ["branchId", "branch_id"],
            "customer_name": ["customer"],
            "payment_method": ["payment_method", "defaultPaymentMethod"],
            "notes": ["note", "notes"],
            "cash_session_id": ["sessionId"],
        }
        for target, sources in mapping.items():
            if target not in data:
                for s in sources:
                    if s in data:
                        data[target] = data[s]
                        break
        return data

    @model_validator(mode="after")
    def _sync_pos_payments(self) -> "POSSaleRequest":
        # // [PACK34-schema]
        if self.payments:
            breakdown: dict[str, Decimal] = {}
            for payment in self.payments:
                method_key = payment.method.value
                total_amount = Decimal(str(payment.amount))
                if payment.tip_amount is not None:
                    total_amount += Decimal(str(payment.tip_amount))
                breakdown[method_key] = (
                    breakdown.get(method_key, Decimal("0")) + total_amount
                )
            self.payment_breakdown = breakdown
        return self


class POSDraftResponse(BaseModel):
    id: int
    store_id: int
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class POSLoyaltySaleSummary(BaseModel):
    account_id: int
    earned_points: Decimal = Field(default=Decimal("0"))
    redeemed_points: Decimal = Field(default=Decimal("0"))
    balance_points: Decimal = Field(default=Decimal("0"))
    redemption_amount: Decimal = Field(default=Decimal("0"))
    expiration_days: int | None = None
    expires_at: datetime | None = None

    @field_serializer(
        "earned_points",
        "redeemed_points",
        "balance_points",
        "redemption_amount",
    )
    @classmethod
    def _serialize_loyalty_decimal(cls, value: Decimal) -> float:
        return float(value)


class POSReceiptDeliveryChannel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class POSElectronicPaymentResult(BaseModel):
    terminal_id: str
    method: PaymentMethod
    transaction_id: str
    status: str
    approval_code: str | None = None
    reconciled: bool = Field(default=False)
    tip_amount: Decimal | None = None

    @field_serializer("tip_amount")
    @classmethod
    def _serialize_tip(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class POSSaleResponse(BaseModel):
    status: Literal["draft", "registered"]
    sale: SaleResponse | None = None
    draft: POSDraftResponse | None = None
    receipt_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    cash_session_id: int | None = None
    payment_breakdown: dict[str, float] = Field(default_factory=dict)
    receipt_pdf_base64: str | None = Field(default=None)
    applied_promotions: list[POSAppliedPromotion] = Field(default_factory=list)
    debt_summary: CustomerDebtSnapshot | None = None
    credit_schedule: list[CreditScheduleEntry] = Field(default_factory=list)
    debt_receipt_pdf_base64: str | None = None
    payment_receipts: list[CustomerPaymentReceiptResponse] = Field(
        default_factory=list
    )
    electronic_payments: list["POSElectronicPaymentResult"] = Field(
        default_factory=list)
    loyalty_summary: POSLoyaltySaleSummary | None = None
    # Campos superiores esperados por pruebas POS
    document_type: str | None = None
    document_number: str | None = None

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @computed_field(return_type=float)  # type: ignore[misc]
    def total_caja(self) -> float:
        if self.sale is not None:
            return float(self.sale.total_amount)
        if self.payment_breakdown:
            return float(sum(self.payment_breakdown.values()))
        return 0.0


class POSReturnItemRequest(BaseModel):  # pragma: no cover
    sale_item_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, max_length=18)
    qty: int = Field(..., ge=1)
    disposition: ReturnDisposition = Field(default=ReturnDisposition.VENDIBLE)
    warehouse_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "POSReturnItemRequest":
        if not (self.sale_item_id or self.product_id or self.imei):
            raise ValueError(
                "Debes proporcionar sale_item_id, product_id o imei para la devolución.")
        return self


class POSReceiptDeliveryRequest(BaseModel):
    channel: POSReceiptDeliveryChannel
    recipient: str = Field(..., min_length=5, max_length=255)
    message: str | None = Field(default=None, max_length=500)
    subject: str | None = Field(default=None, max_length=120)

    @field_validator("recipient")
    @classmethod
    def _normalize_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("recipient_required")
        return normalized


class POSReceiptDeliveryResponse(BaseModel):
    channel: POSReceiptDeliveryChannel
    status: str


class POSReturnRequest(BaseModel):
    """Solicitud de devolución rápida en POS (alias normalizados)."""

    original_sale_id: int = Field(..., ge=1)
    items: list[POSReturnItemRequest]
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_return_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "original_sale_id" not in data:
            for k in ("originalSaleId", "sale_id"):
                if k in data:
                    data["original_sale_id"] = data[k]
                    break
        return data

    @field_validator("items")
    @classmethod
    def _ensure_return_items(cls, value: list[POSReturnItemRequest]) -> list[POSReturnItemRequest]:
        if not value:
            raise ValueError("Debes indicar artículos a devolver.")
        return value

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class POSReturnResponse(BaseModel):
    """Respuesta estandarizada tras registrar devoluciones POS."""

    # // [PACK34-schema]
    sale_id: int
    return_ids: list[int]
    notes: str | None = None
    dispositions: list[ReturnDisposition] = Field(default_factory=list)


class POSSaleDetailResponse(BaseModel):
    """Detalle completo de ventas POS con acceso a recibo."""

    # // [PACK34-schema]
    sale: SaleResponse
    receipt_url: str
    receipt_pdf_base64: str | None = None
    debt_summary: CustomerDebtSnapshot | None = None
    credit_schedule: list[CreditScheduleEntry] = Field(default_factory=list)
