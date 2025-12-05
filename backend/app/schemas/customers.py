"""Esquemas para la gestión de clientes y fidelización."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, cast, Iterable, List, Dict

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import (
    CustomerLedgerEntryType,
    LoyaltyTransactionType,
    PaymentMethod,
    PrivacyRequestStatus,
    PrivacyRequestType,
    StoreCreditStatus,
)
from .common import (
    ContactHistoryEntry,
    DashboardChartPoint,
    normalize_optional_rtn_value,
)


class CustomerBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str = Field(..., min_length=5, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    customer_type: str = Field(
        default="minorista", min_length=3, max_length=30)
    status: str = Field(default="activo", min_length=3, max_length=20)
    tax_id: str | None = Field(default=None, min_length=5, max_length=30)
    segment_category: str | None = Field(default=None, max_length=60)
    tags: list[str] = Field(default_factory=list)
    credit_limit: Decimal = Field(default=Decimal("0"))
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: List[ContactHistoryEntry] = Field(
        default_factory=list)

    @field_validator(
        "contact_name",
        "email",
        "phone",
        "address",
        "customer_type",
        "status",
        "notes",
        "segment_category",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tax_id", mode="before")
    @classmethod
    def _normalize_tax_id(cls, value: str | None) -> str | None:
        return normalize_optional_rtn_value(value)

    @field_validator("segment_category", mode="before")
    @classmethod
    def _normalize_segment_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(
        cls, value: list[str] | str | None
    ) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        else:
            raw_items = value
        normalized: list[str] = []
        for item in raw_items:
            if not isinstance(item, str):  # type: ignore
                continue
            cleaned = item.strip().lower()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("credit_limit")
    @classmethod
    def _serialize_credit_limit(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("phone", mode="after")
    @classmethod
    def _ensure_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El teléfono del cliente es obligatorio.")
        return normalized


class CustomerCreate(CustomerBase):
    name: str = Field(..., max_length=120)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    customer_type: str | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, max_length=20)
    tax_id: str | None = Field(default=None, min_length=5, max_length=30)
    segment_category: str | None = Field(default=None, max_length=60)
    tags: list[str] | None = Field(default=None)
    credit_limit: Decimal | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: List[ContactHistoryEntry] | None = Field(
        default=None)

    @field_validator(
        "name",
        "contact_name",
        "email",
        "phone",
        "address",
        "customer_type",
        "status",
        "notes",
        "segment_category",
        mode="before",
    )
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tax_id", mode="before")
    @classmethod
    def _normalize_update_tax_id(cls, value: str | None) -> str | None:
        return normalize_optional_rtn_value(value)

    @field_validator("segment_category", mode="before")
    @classmethod
    def _normalize_update_segment_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_update_tags(
        cls, value: list[str] | str | None
    ) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            raw_items = value.split(",")
        else:
            raw_items = value
        normalized: list[str] = []
        for item in raw_items:
            if not isinstance(item, str):  # type: ignore
                continue
            cleaned = item.strip().lower()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized


class LoyaltyAccountBase(BaseModel):
    accrual_rate: Decimal = Field(default=Decimal("1"), ge=Decimal("0"))
    redemption_rate: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    expiration_days: int = Field(default=365, ge=0)
    is_active: bool = Field(default=True)
    rule_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rule_config", mode="before")
    @classmethod
    def _ensure_rule_config(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}  # type: ignore
        raise ValueError("rule_config debe ser un objeto JSON válido")


class LoyaltyAccountCreate(LoyaltyAccountBase):
    customer_id: int = Field(..., ge=1)


class LoyaltyAccountUpdate(BaseModel):
    accrual_rate: Decimal | None = Field(default=None, ge=Decimal("0"))
    redemption_rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    expiration_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    rule_config: dict[str, Any] | None = None

    @field_validator("rule_config", mode="before")
    @classmethod
    def _normalize_rule_config(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}  # type: ignore
        raise ValueError("rule_config debe ser un objeto JSON válido")


class LoyaltyAccountSummary(BaseModel):
    id: int
    balance_points: Decimal = Field(default=Decimal("0"))
    lifetime_points_earned: Decimal = Field(default=Decimal("0"))
    lifetime_points_redeemed: Decimal = Field(default=Decimal("0"))
    expired_points_total: Decimal = Field(default=Decimal("0"))
    accrual_rate: Decimal = Field(default=Decimal("0"))
    redemption_rate: Decimal = Field(default=Decimal("0"))
    expiration_days: int = Field(default=0)
    is_active: bool = Field(default=True)
    last_accrual_at: datetime | None = None
    last_redemption_at: datetime | None = None
    last_expiration_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "balance_points",
        "lifetime_points_earned",
        "lifetime_points_redeemed",
        "expired_points_total",
        "accrual_rate",
        "redemption_rate",
    )
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class LoyaltyAccountResponse(LoyaltyAccountSummary):
    customer_id: int
    rule_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LoyaltyTransactionResponse(BaseModel):
    id: int
    account_id: int
    sale_id: int | None = None
    transaction_type: LoyaltyTransactionType
    points: Decimal
    balance_after: Decimal
    currency_amount: Decimal
    description: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime
    expires_at: datetime | None = None
    registered_by_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("points", "balance_after", "currency_amount")
    @classmethod
    def _serialize_transaction_decimal(cls, value: Decimal) -> float:
        return float(value)


class LoyaltyReportSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    total_balance: Decimal = Field(default=Decimal("0"))
    total_earned: Decimal = Field(default=Decimal("0"))
    total_redeemed: Decimal = Field(default=Decimal("0"))
    total_expired: Decimal = Field(default=Decimal("0"))
    last_activity: datetime | None = None

    @field_serializer(
        "total_balance",
        "total_earned",
        "total_redeemed",
        "total_expired",
    )
    @classmethod
    def _serialize_summary_decimal(cls, value: Decimal) -> float:
        return float(value)


class CustomerResponse(CustomerBase):
    id: int
    name: str
    last_interaction_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = None
    privacy_consents: dict[str, bool] = Field(default_factory=dict)
    privacy_metadata: dict[str, Any] = Field(default_factory=dict)
    privacy_last_request_at: datetime | None = None
    loyalty_account: LoyaltyAccountResponse | None = None
    annual_purchase_amount: float = Field(default=0.0)
    orders_last_year: int = Field(default=0)
    purchase_frequency: str = Field(default="sin_datos")
    segment_labels: list[str] = Field(default_factory=list)
    last_purchase_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerNoteCreate(BaseModel):
    note: str = Field(..., min_length=3, max_length=255)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La nota del cliente es obligatoria.")
        return normalized


class CustomerPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))
    method: str = Field(default="manual", min_length=3, max_length=40)
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: str | None) -> str:
        if value is None:
            return "manual"
        normalized = value.strip()
        if not normalized:
            raise ValueError("Indica un método de pago válido.")
        return normalized

    @field_validator("reference", "note", mode="before")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerLedgerEntryResponse(BaseModel):
    id: int
    entry_type: CustomerLedgerEntryType
    reference_type: str | None
    reference_id: str | None
    amount: float
    balance_after: float
    note: str | None
    details: dict[str, Any]
    created_at: datetime
    created_by: str | None

    @staticmethod
    def _extract_author(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        name_attrs = ("full_name", "nombre", "name")
        for attr in name_attrs:
            candidate = getattr(value, attr, None)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        username_attrs = ("username", "correo", "email")
        for attr in username_attrs:
            candidate = getattr(value, attr, None)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        identifier = getattr(value, "id_usuario",
                             None) or getattr(value, "id", None)
        if identifier is not None:
            return str(identifier)
        return str(value)

    @field_validator("created_by", mode="before")
    @classmethod
    def _normalize_created_by(cls, value: Any) -> str | None:
        return cls._extract_author(value)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("created_by")
    @classmethod
    def _serialize_created_by(cls, value: Any) -> str | None:
        return cls._extract_author(value)


class StoreCreditRedemptionResponse(BaseModel):
    id: int
    store_credit_id: int
    sale_id: int | None
    amount: float
    notes: str | None
    created_at: datetime
    created_by: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _coerce_author(cls, data: Any) -> Any:
        try:
            from .. import models  # type: ignore
        except ImportError:  # pragma: no cover - fallback en tiempo de import
            models = None  # type: ignore
        if models is not None and isinstance(data, models.StoreCreditRedemption):
            author = getattr(data, "created_by", None)
            return {
                "id": data.id,
                "store_credit_id": data.store_credit_id,
                "sale_id": data.sale_id,
                "amount": data.amount,
                "notes": data.notes,
                "created_at": data.created_at,
                "created_by": getattr(author, "full_name", None)
                or getattr(author, "username", None),
            }
        if isinstance(data, dict) and "created_by" in data:
            author_obj = cast(object, data["created_by"])
            if hasattr(author_obj, "full_name") or hasattr(author_obj, "username"):
                data_dict = dict(cast(Dict[str, Any], data))
                data_dict["created_by"] = getattr(author_obj, "full_name", None) or getattr(
                    author_obj, "username", None
                )
                return data_dict
        return data

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, value: datetime) -> str:
        return value.isoformat()


class StoreCreditResponse(BaseModel):
    id: int
    code: str
    customer_id: int
    issued_amount: float
    balance_amount: float
    status: StoreCreditStatus
    notes: str | None
    context: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("context", "metadata"),
        serialization_alias="context",
    )
    issued_at: datetime
    redeemed_at: datetime | None
    expires_at: datetime | None
    redemptions: List[StoreCreditRedemptionResponse]

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, data: Any) -> Any:
        try:
            from .. import models  # type: ignore
        except ImportError:  # pragma: no cover
            models = None  # type: ignore
        if models is not None and isinstance(data, models.StoreCredit):
            return {
                "id": data.id,
                "code": data.code,
                "customer_id": data.customer_id,
                "issued_amount": data.issued_amount,
                "balance_amount": data.balance_amount,
                "status": data.status,
                "notes": data.notes,
                "context": getattr(data, "context", {}) or {},
                "issued_at": data.issued_at,
                "redeemed_at": data.redeemed_at,
                "expires_at": data.expires_at,
                "redemptions": list(getattr(data, "redemptions", []) or []),
            }
        if isinstance(data, dict):
            payload: dict[str, Any] = dict(data)  # type: ignore
            context_payload = payload.get("context")
            metadata_payload = payload.get("metadata")
            if context_payload is None and metadata_payload is not None:
                payload["context"] = metadata_payload
            payload.setdefault("context", {})
            return payload
        return data

    @field_serializer("issued_amount", "balance_amount")
    @classmethod
    def _serialize_credit_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("issued_at", when_used="json")
    @classmethod
    def _serialize_issued_at(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("redeemed_at", "expires_at", when_used="json")
    @classmethod
    def _serialize_optional_datetime(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class StoreCreditIssueRequest(BaseModel):
    customer_id: int = Field(..., ge=1)
    amount: Decimal = Field(..., gt=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None
    code: str | None = Field(default=None, max_length=32)
    context: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("context", "metadata"),
        serialization_alias="context",
    )

    @field_validator("context", mode="before")
    @classmethod
    def _ensure_context(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)  # type: ignore
        raise ValueError("context debe ser un diccionario")


class StoreCreditRedeemRequest(BaseModel):
    store_credit_id: int | None = Field(default=None, ge=1)
    code: str | None = Field(default=None, max_length=32)
    amount: Decimal = Field(..., gt=Decimal("0"))
    sale_id: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _ensure_reference(self) -> "StoreCreditRedeemRequest":
        if self.store_credit_id is None and not (self.code and self.code.strip()):
            raise ValueError(
                "Debes indicar el identificador o el código de la nota de crédito."
            )
        return self


class CustomerDebtSnapshot(BaseModel):
    previous_balance: Decimal
    new_charges: Decimal
    payments_applied: Decimal
    remaining_balance: Decimal

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("previous_balance", "new_charges", "payments_applied", "remaining_balance")
    @classmethod
    def _serialize_snapshot_decimal(cls, value: Decimal) -> float:
        return float(value)


class CreditScheduleEntry(BaseModel):
    sequence: int
    due_date: datetime
    amount: Decimal
    status: Literal["pending", "due_soon", "overdue"]
    reminder: str | None = None

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("due_date")
    @classmethod
    def _serialize_due_date(cls, value: datetime) -> str:
        return value.isoformat()


class AccountsReceivableEntry(BaseModel):
    ledger_entry_id: int
    reference_type: str | None = None
    reference_id: str | None = None
    reference: str | None = None
    issued_at: datetime
    original_amount: float
    balance_due: float
    days_outstanding: int
    status: Literal["current", "overdue"]
    note: str | None = None
    details: dict[str, Any] | None = None

    @field_serializer("issued_at")
    @classmethod
    def _serialize_issued_at(cls, value: datetime) -> str:
        return value.isoformat()


class AccountsReceivableBucket(BaseModel):
    label: str
    days_from: int
    days_to: int | None = None
    amount: float
    percentage: float
    count: int


class AccountsReceivableSummary(BaseModel):
    total_outstanding: float
    available_credit: float
    credit_limit: float
    last_payment_at: datetime | None = None
    next_due_date: datetime | None = None
    average_days_outstanding: float
    contact_email: str | None = None
    contact_phone: str | None = None

    @field_serializer("last_payment_at", "next_due_date")
    @classmethod
    def _serialize_optional_datetime(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class CustomerAccountsReceivableResponse(BaseModel):
    customer: CustomerResponse
    summary: AccountsReceivableSummary
    aging: List[AccountsReceivableBucket] = Field(
        default_factory=list)
    open_entries: List[AccountsReceivableEntry] = Field(
        default_factory=list)
    credit_schedule: List[CreditScheduleEntry] = Field(
        default_factory=list)
    recent_activity: List[CustomerLedgerEntryResponse] = Field(
        default_factory=list)
    generated_at: datetime

    @field_serializer("generated_at")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


class CustomerStatementLine(BaseModel):
    created_at: datetime
    description: str
    reference: str | None = None
    entry_type: CustomerLedgerEntryType
    amount: float
    balance_after: float

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, value: datetime) -> str:
        return value.isoformat()


class CustomerStatementReport(BaseModel):
    customer: CustomerResponse
    summary: AccountsReceivableSummary
    lines: List[CustomerStatementLine] = Field(
        default_factory=list)
    generated_at: datetime

    @field_serializer("generated_at")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


class CustomerPaymentReceiptResponse(BaseModel):
    ledger_entry: CustomerLedgerEntryResponse
    debt_summary: CustomerDebtSnapshot
    credit_schedule: List[CreditScheduleEntry] = Field(
        default_factory=list)
    receipt_pdf_base64: str


class CustomerSaleSummary(BaseModel):
    sale_id: int
    store_id: int
    store_name: str | None
    payment_method: PaymentMethod
    status: str
    subtotal_amount: float
    tax_amount: float
    total_amount: float
    created_at: datetime


class CustomerInvoiceSummary(BaseModel):
    sale_id: int
    invoice_number: str
    total_amount: float
    status: str
    created_at: datetime
    store_id: int


class CustomerFinancialSnapshot(BaseModel):
    credit_limit: float
    outstanding_debt: float
    available_credit: float
    total_sales_credit: float
    total_payments: float
    store_credit_issued: float
    store_credit_available: float
    store_credit_redeemed: float


class CustomerPrivacyRequestResponse(BaseModel):
    id: int
    customer_id: int
    request_type: PrivacyRequestType
    status: PrivacyRequestStatus
    details: str | None = None
    consent_snapshot: dict[str, bool] = Field(default_factory=dict)
    masked_fields: list[str] = Field(default_factory=list)
    created_at: datetime
    processed_at: datetime | None = None
    processed_by_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerPrivacyRequestCreate(BaseModel):
    request_type: PrivacyRequestType
    details: str | None = Field(default=None, max_length=255)
    consent: dict[str, bool] | None = None
    mask_fields: list[str] = Field(default_factory=list)

    @field_validator("consent", mode="before")
    @classmethod
    def _normalize_consent(
        cls, value: dict[str, object] | None
    ) -> dict[str, bool] | None:
        if value is None:
            return None
        normalized: dict[str, bool] = {}
        for key, raw in value.items():
            name = str(key).strip().lower()
            if not name:
                continue
            normalized[name] = bool(raw)
        return normalized

    @field_validator("mask_fields", mode="before")
    @classmethod
    def _normalize_mask_fields(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            items = list(cast(Iterable[Any], value))
        else:
            items = str(value).split(",")
        normalized: list[str] = []
        for item in items:
            text = str(item).strip().lower()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @model_validator(mode="after")
    def _validate_payload(self) -> "CustomerPrivacyRequestCreate":
        if self.request_type == PrivacyRequestType.CONSENT:
            if not self.consent:
                raise ValueError(
                    "Debes proporcionar al menos un consentimiento a actualizar."
                )
        elif not self.mask_fields:
            self.mask_fields = ["email", "phone", "address"]
        return self


class CustomerSummaryResponse(BaseModel):
    customer: CustomerResponse
    totals: CustomerFinancialSnapshot
    sales: List[CustomerSaleSummary]
    invoices: List[CustomerInvoiceSummary]
    payments: List[CustomerLedgerEntryResponse]
    ledger: List[CustomerLedgerEntryResponse]
    store_credits: List[StoreCreditResponse]
    privacy_requests: List[CustomerPrivacyRequestResponse] = Field(
        default_factory=list)


class CustomerPrivacyActionResponse(BaseModel):
    customer: CustomerResponse
    request: CustomerPrivacyRequestResponse


class PaymentCenterSummary(BaseModel):
    collections_today: float = 0.0
    collections_month: float = 0.0
    pending_balance: float = 0.0
    refunds_month: float = 0.0


class PaymentCenterTransaction(BaseModel):
    id: int
    type: Literal["PAYMENT", "REFUND", "CREDIT_NOTE"]
    amount: float
    created_at: datetime
    order_id: int | None = None
    order_number: str | None = None
    customer_id: int
    customer_name: str
    method: str | None = None
    note: str | None = None
    status: Literal["POSTED", "VOID"] = "POSTED"


class PaymentCenterResponse(BaseModel):
    summary: PaymentCenterSummary
    transactions: List[PaymentCenterTransaction]


class PaymentCenterPaymentCreate(CustomerPaymentCreate):
    customer_id: int = Field(gt=0)


class PaymentCenterRefundCreate(BaseModel):
    customer_id: int = Field(gt=0)
    amount: Decimal = Field(..., gt=Decimal("0"))
    method: str = Field(min_length=3, max_length=40)
    reason: str = Field(min_length=3, max_length=120)
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("method", "reason", mode="before")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo es obligatorio")
        return normalized

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PaymentCenterCreditNoteLine(BaseModel):
    description: str = Field(min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=0)
    amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripción es obligatoria")
        return normalized


class PaymentCenterCreditNoteCreate(BaseModel):
    customer_id: int = Field(gt=0)
    lines: List[PaymentCenterCreditNoteLine]
    total: Decimal = Field(..., gt=Decimal("0"))
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("lines")
    @classmethod
    def _ensure_lines(cls, value: List[PaymentCenterCreditNoteLine]) -> List[PaymentCenterCreditNoteLine]:
        if not value:
            raise ValueError(
                "La nota de crédito requiere al menos un concepto")
        return value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerPortfolioFilters(BaseModel):
    category: Literal["delinquent", "frequent"]
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=50, ge=1, le=500)


class CustomerPortfolioTotals(BaseModel):
    customers: int
    moroso_flagged: int
    outstanding_debt: float
    sales_total: float


class CustomerPortfolioItem(BaseModel):
    customer_id: int
    name: str
    status: str
    customer_type: str
    credit_limit: float
    outstanding_debt: float
    available_credit: float
    sales_total: float
    sales_count: int
    last_sale_at: datetime | None
    last_interaction_at: datetime | None


class CustomerPortfolioReport(BaseModel):
    generated_at: datetime
    category: Literal["delinquent", "frequent"]
    filters: CustomerPortfolioFilters
    items: List[CustomerPortfolioItem]
    totals: CustomerPortfolioTotals


class CustomerLeaderboardEntry(BaseModel):
    customer_id: int
    name: str
    status: str
    customer_type: str
    sales_total: float
    sales_count: int
    last_sale_at: datetime | None
    outstanding_debt: float


class CustomerDelinquentSummary(BaseModel):
    customers_with_debt: int
    moroso_flagged: int
    total_outstanding_debt: float


class CustomerDashboardMetrics(BaseModel):
    generated_at: datetime
    months: int
    new_customers_per_month: List[DashboardChartPoint]
    top_customers: List[CustomerLeaderboardEntry]
    delinquent_summary: CustomerDelinquentSummary
