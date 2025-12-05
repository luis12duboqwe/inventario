from typing import Any, ClassVar, Literal
import enum
from pydantic import BaseModel, Field, model_validator, field_validator


class POSConnectorType(str, enum.Enum):
    """Tipos de conectores de hardware permitidos."""

    USB = "usb"
    NETWORK = "network"


class POSPrinterMode(str, enum.Enum):
    """Tipos de impresoras POS disponibles."""

    THERMAL = "thermal"
    FISCAL = "fiscal"


class POSFiscalPrinterProfile(BaseModel):
    """Perfil técnico necesario para operar una impresora fiscal."""

    adapter: Literal["hasar", "epson", "bematech", "simulated"] = Field(
        default="simulated"
    )
    sdk_module: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=80)
    serial_number: str | None = Field(default=None, max_length=80)
    taxpayer_id: str | None = Field(default=None, max_length=32)
    document_type: Literal["ticket", "invoice", "credit_note"] = Field(
        default="ticket"
    )
    timeout_s: float = Field(default=6.0, ge=0.5, le=30.0)
    simulate_only: bool = Field(default=False)
    extra_settings: dict[str, Any] = Field(default_factory=dict)

    _DEFAULT_SDK_MODULES: ClassVar[dict[str, str | None]] = {
        "hasar": "pyhasar",
        "epson": "pyfiscalprinter",
        "bematech": "bemafiscal",
        "simulated": None,
    }

    @field_validator("sdk_module", "model", "serial_number", mode="before")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = str(value).strip()
        return trimmed or None

    @field_validator("taxpayer_id", mode="before")
    @classmethod
    def _normalize_taxpayer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().upper()
        return normalized or None

    @field_validator("extra_settings")
    @classmethod
    def _normalize_extra_settings(
        cls, value: dict[str, Any]
    ) -> dict[str, Any]:
        return {str(key): item for key, item in (value or {}).items()}

    def resolved_sdk_module(self) -> str | None:
        """Devuelve el módulo SDK preferido según el adaptador configurado."""

        return self.sdk_module or self._DEFAULT_SDK_MODULES.get(self.adapter)


class POSConnectorSettings(BaseModel):
    """Configura el punto de conexión del dispositivo POS."""

    type: POSConnectorType = Field(default=POSConnectorType.USB)
    identifier: str = Field(default="predeterminado", max_length=120)
    path: str | None = Field(default=None, max_length=255)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)

    @model_validator(mode="after")
    def _validate_target(self) -> "POSConnectorSettings":
        if self.type is POSConnectorType.NETWORK:
            if not self.host:
                raise ValueError(
                    "Los conectores de red requieren host configurado.")
        return self


class POSPrinterSettings(BaseModel):
    """Describe impresoras térmicas o fiscales."""

    name: str = Field(..., max_length=120)
    mode: POSPrinterMode = Field(default=POSPrinterMode.THERMAL)
    connector: POSConnectorSettings = Field(
        default_factory=POSConnectorSettings)
    paper_width_mm: int | None = Field(default=None, ge=40, le=120)
    is_default: bool = Field(default=False)
    vendor: str | None = Field(default=None, max_length=80)
    supports_qr: bool = Field(default=False)
    fiscal_profile: POSFiscalPrinterProfile | None = Field(default=None)

    @model_validator(mode="after")
    def _ensure_fiscal_profile(self) -> "POSPrinterSettings":
        if self.mode is POSPrinterMode.FISCAL:
            if self.fiscal_profile is None:
                self.fiscal_profile = POSFiscalPrinterProfile()
        else:
            self.fiscal_profile = None
        return self


class POSCashDrawerSettings(BaseModel):
    """Define la gaveta de efectivo conectada al POS."""

    enabled: bool = Field(default=False)
    connector: POSConnectorSettings | None = Field(default=None)
    auto_open_on_cash_sale: bool = Field(default=True)
    pulse_duration_ms: int = Field(default=150, ge=50, le=500)


class POSCustomerDisplaySettings(BaseModel):
    """Configura la pantalla de cliente enlazada al POS."""

    enabled: bool = Field(default=False)
    channel: Literal["websocket", "local"] = Field(default="websocket")
    brightness: int = Field(default=100, ge=10, le=100)
    theme: Literal["dark", "light"] = Field(default="dark")
    message_template: str | None = Field(default=None, max_length=160)


class POSHardwareSettings(BaseModel):
    """Agrupa la configuración de hardware POS por sucursal."""

    printers: list[POSPrinterSettings] = Field(default_factory=list)
    cash_drawer: POSCashDrawerSettings = Field(
        default_factory=POSCashDrawerSettings)
    customer_display: POSCustomerDisplaySettings = Field(
        default_factory=POSCustomerDisplaySettings
    )


class POSHardwarePrintTestRequest(BaseModel):
    """Solicitud de impresión de prueba."""

    store_id: int = Field(..., ge=1)
    printer_name: str | None = Field(default=None, max_length=120)
    mode: POSPrinterMode = Field(default=POSPrinterMode.THERMAL)
    sample: str = Field(
        default="*** PRUEBA DE IMPRESIÓN POS ***", max_length=512)


class LabelFormat(str, enum.Enum):
    """Formatos permitidos para etiquetas físicas."""

    PDF = "pdf"
    ZPL = "zpl"
    ESCPOS = "escpos"


class LabelTemplateKey(str, enum.Enum):
    """Plantillas disponibles según tamaño de etiqueta."""

    SIZE_38X25 = "38x25"
    SIZE_50X30 = "50x30"
    SIZE_80X50 = "80x50"
    A7 = "a7"


class LabelCommandsResponse(BaseModel):
    """Respuesta para etiquetas en formatos directos (ZPL/ESC/POS)."""

    format: LabelFormat = Field(default=LabelFormat.ZPL)
    template: LabelTemplateKey = Field(default=LabelTemplateKey.SIZE_38X25)
    commands: str = Field(..., max_length=8000)
    filename: str = Field(..., max_length=255)
    content_type: str = Field(default="text/plain")
    connector: POSConnectorSettings | None = Field(default=None)
    message: str = Field(default="Etiqueta generada para impresión directa.")


class InventoryLabelPrintRequest(BaseModel):
    """Solicitud para enviar una etiqueta a impresión directa."""

    format: LabelFormat = Field(default=LabelFormat.ZPL)
    template: LabelTemplateKey = Field(default=LabelTemplateKey.SIZE_38X25)
    connector: POSConnectorSettings | None = Field(default=None)


class POSHardwareDrawerOpenRequest(BaseModel):
    """Solicitud para apertura de gaveta."""

    store_id: int = Field(..., ge=1)
    connector_identifier: str | None = Field(default=None, max_length=120)
    pulse_duration_ms: int | None = Field(default=None, ge=50, le=500)


class POSHardwareDisplayPushRequest(BaseModel):
    """Eventos a mostrar en la pantalla de cliente."""

    store_id: int = Field(..., ge=1)
    headline: str = Field(..., max_length=80)
    message: str | None = Field(default=None, max_length=240)
    total_amount: float | None = Field(default=None, ge=0)


class POSHardwareActionResponse(BaseModel):
    """Respuesta estandarizada para acciones de hardware."""

    status: Literal["queued", "ok", "error"] = Field(default="queued")
    message: str = Field(default="")
    details: dict[str, Any] | None = Field(default=None)
