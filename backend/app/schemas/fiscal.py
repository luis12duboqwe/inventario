from __future__ import annotations
import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import DTEStatus, DTEDispatchStatus


class FiscalBookType(str, enum.Enum):
    SALES = "sales"
    PURCHASES = "purchases"


class FiscalBookFilters(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    book_type: FiscalBookType


class FiscalBookTotals(BaseModel):
    registros: int
    base_15: Decimal = Field(default=Decimal("0"))
    impuesto_15: Decimal = Field(default=Decimal("0"))
    total_15: Decimal = Field(default=Decimal("0"))
    base_18: Decimal = Field(default=Decimal("0"))
    impuesto_18: Decimal = Field(default=Decimal("0"))
    total_18: Decimal = Field(default=Decimal("0"))
    base_exenta: Decimal = Field(default=Decimal("0"))
    total_exento: Decimal = Field(default=Decimal("0"))
    total_general: Decimal = Field(default=Decimal("0"))

    @field_serializer(
        "base_15",
        "impuesto_15",
        "total_15",
        "base_18",
        "impuesto_18",
        "total_18",
        "base_exenta",
        "total_exento",
        "total_general",
    )
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class FiscalBookEntry(BaseModel):
    correlativo: int
    fecha: datetime
    documento: str
    contraparte: str | None = None
    detalle: str | None = None
    base_15: Decimal = Field(default=Decimal("0"))
    impuesto_15: Decimal = Field(default=Decimal("0"))
    base_18: Decimal = Field(default=Decimal("0"))
    impuesto_18: Decimal = Field(default=Decimal("0"))
    base_exenta: Decimal = Field(default=Decimal("0"))
    total: Decimal = Field(default=Decimal("0"))

    @field_serializer(
        "base_15",
        "impuesto_15",
        "base_18",
        "impuesto_18",
        "base_exenta",
        "total",
    )
    @classmethod
    def _serialize_entry_decimal(cls, value: Decimal) -> float:
        return float(value)


class FiscalBookReport(BaseModel):
    generated_at: datetime
    filters: FiscalBookFilters
    totals: FiscalBookTotals
    entries: list[FiscalBookEntry]


class DTEIssuerInfo(BaseModel):
    rtn: str = Field(..., min_length=5, max_length=40)
    name: str = Field(..., min_length=3, max_length=120)
    address: str = Field(..., min_length=3, max_length=255)

    @field_validator("rtn", "name", "address")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo es obligatorio.")
        return normalized


class DTESignerCredentials(BaseModel):
    certificate_serial: str = Field(..., min_length=3, max_length=120)
    private_key: str = Field(..., min_length=8, max_length=255)

    @field_validator("certificate_serial")
    @classmethod
    def _normalize_certificate(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Debes indicar el número de certificado.")
        return normalized

    @field_validator("private_key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError(
                "La llave privada debe tener al menos 8 caracteres.")
        return normalized


class DTEAuthorizationBase(BaseModel):
    document_type: str = Field(..., min_length=2, max_length=30)
    serie: str = Field(..., min_length=1, max_length=12)
    range_start: int = Field(..., ge=1, le=99999999)
    range_end: int = Field(..., ge=1, le=99999999)
    expiration_date: date
    cai: str = Field(..., min_length=8, max_length=40)
    store_id: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=255)
    active: bool = Field(default=True)

    @field_validator("document_type")
    @classmethod
    def _normalize_document_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Debes especificar el tipo de documento.")
        return normalized.upper()

    @field_validator("serie")
    @classmethod
    def _normalize_serie(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Debes indicar la serie autorizada.")
        return normalized.upper()

    @field_validator("cai")
    @classmethod
    def _normalize_cai(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError("El CAI debe contener al menos 8 caracteres.")
        return normalized.upper()

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_range(self) -> "DTEAuthorizationBase":
        if self.range_end < self.range_start:
            raise ValueError("El rango autorizado es inválido.")
        return self


class DTEAuthorizationCreate(DTEAuthorizationBase):
    pass


class DTEAuthorizationUpdate(BaseModel):
    expiration_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    active: bool | None = None

    @field_validator("notes")
    @classmethod
    def _normalize_update_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DTEAuthorizationResponse(DTEAuthorizationBase):
    id: int
    current_number: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=int)
    def remaining(self) -> int:
        next_number = max(self.current_number, self.range_start)
        if next_number > self.range_end:
            return 0
        return self.range_end - next_number + 1


class DTEGenerationRequest(BaseModel):
    sale_id: int = Field(..., ge=1)
    authorization_id: int = Field(..., ge=1)
    issuer: DTEIssuerInfo
    signer: DTESignerCredentials
    offline: bool = Field(default=False)


class DTEEventResponse(BaseModel):
    id: int
    document_id: int
    event_type: str
    status: DTEStatus
    detail: str | None
    created_at: datetime
    performed_by_id: int | None

    model_config = ConfigDict(from_attributes=True)


class DTEDispatchQueueEntryResponse(BaseModel):
    id: int
    document_id: int
    status: DTEDispatchStatus
    attempts: int
    last_error: str | None
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DTEDocumentResponse(BaseModel):
    id: int
    sale_id: int
    authorization_id: int | None
    document_type: str
    serie: str
    correlative: int
    control_number: str
    cai: str
    status: DTEStatus
    reference_code: str | None
    ack_code: str | None
    ack_message: str | None
    sent_at: datetime | None
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime
    xml_content: str
    signature: str
    events: list[DTEEventResponse] = Field(default_factory=list)
    queue: list[DTEDispatchQueueEntryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @computed_field(alias="numero_documento", return_type=str)
    def document_number(self) -> str:
        return f"{self.serie}-{self.correlative:08d}"


class DTEDispatchRequest(BaseModel):
    mode: Literal["ONLINE", "OFFLINE"] = Field(default="ONLINE")
    error_message: str | None = Field(default=None, max_length=255)

    @field_validator("mode")
    @classmethod
    def _normalize_mode(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"ONLINE", "OFFLINE"}:
            raise ValueError("Modo de envío inválido.")
        return normalized

    @field_validator("error_message")
    @classmethod
    def _normalize_error(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DTEAckRegistration(BaseModel):
    status: DTEStatus = Field(default=DTEStatus.EMITIDO)
    code: str | None = Field(default=None, max_length=80)
    detail: str | None = Field(default=None, max_length=255)
    received_at: datetime | None = None

    @field_validator("code", "detail")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
