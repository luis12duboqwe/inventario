"""Esquemas para la gestión de usuarios y autenticación."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    AliasChoices,
    computed_field,
    field_validator,
    model_validator,
)

from backend.app.models import ReturnDisposition
from .audit import AuditTrailInfo, DashboardAuditAlerts
from .stores import StoreResponse


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    # El campo principal es username; aceptamos 'correo' como alias de entrada mediante _coerce_aliases.
    username: Annotated[str, Field(..., max_length=120)]
    full_name: Annotated[str | None, Field(default=None, max_length=120)]
    telefono: str | None = Field(default=None, max_length=30)

    model_config = ConfigDict(populate_by_name=True)

    @computed_field(alias="correo")
    @property
    def correo(self) -> str:
        return self.username

    @computed_field(alias="nombre")
    @property
    def nombre(self) -> str | None:
        return self.full_name

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("El correo del usuario es obligatorio")
        return value.strip()

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover - lógica simple
        """Permite aceptar claves alternativas (correo/nombre) sin usar validation_alias.

        Evita warnings de Pydantic v2 y mantiene compatibilidad con payloads históricos.
        """
        if not isinstance(data, dict):
            return data
        # username <= correo/email
        if "username" not in data:
            if "correo" in data and data.get("correo"):
                data["username"] = data.get("correo")
            elif "email" in data and data.get("email"):
                data["username"] = data.get("email")
        # full_name <= nombre
        if "full_name" not in data and "nombre" in data:
            data["full_name"] = data.get("nombre")
        return data


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)
    store_id: Annotated[int | None, Field(default=None, ge=1)]


class UserResponse(UserBase):
    id: int
    is_active: bool
    rol: str
    estado: str
    created_at: datetime
    roles: list[RoleResponse]
    store: StoreResponse | None = Field(default=None, exclude=True)
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("roles", mode="before")
    @classmethod
    def _flatten_roles(cls, value: Any) -> list[RoleResponse]:
        if value is None:
            return []
        flattened: list[RoleResponse] = []
        for item in value:
            if isinstance(item, RoleResponse):
                flattened.append(item)
                continue
            role_obj = getattr(item, "role", item)
            flattened.append(RoleResponse.model_validate(role_obj))
        return flattened

    @computed_field
    @property
    def store_id(self) -> int | None:
        store_obj = self.store
        if store_obj is None:
            return None
        return store_obj.id

    @computed_field
    @property
    def store_name(self) -> str | None:
        store_obj = self.store
        if store_obj is None:
            return None
        return store_obj.name

    @computed_field(alias="fecha_creacion")
    @property
    def fecha_creacion(self) -> datetime:
        return self.created_at

    @computed_field(alias="sucursal_id")
    @property
    def sucursal_id(self) -> int | None:
        return self.store_id

    @computed_field(alias="rol_id")
    @property
    def primary_role_id(self) -> int | None:
        if not self.roles:
            return None
        return self.roles[0].id


class UserUpdate(BaseModel):
    full_name: Annotated[str | None, Field(default=None, max_length=120)]
    telefono: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    store_id: Annotated[int | None, Field(default=None, ge=1)]
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover - simple
        if not isinstance(data, dict):
            return data
        if "full_name" not in data and "nombre" in data:
            data["full_name"] = data.get("nombre")
        if "store_id" not in data and "sucursal_id" in data:
            data["store_id"] = data.get("sucursal_id")
        return data


class RoleModulePermission(BaseModel):
    module: str = Field(..., min_length=2, max_length=120)
    can_view: bool = Field(default=False)
    can_edit: bool = Field(default=False)
    can_delete: bool = Field(default=False)


class RolePermissionMatrix(BaseModel):
    role: str = Field(..., min_length=2, max_length=60)
    permissions: list[RoleModulePermission] = Field(default_factory=list)


class RolePermissionUpdate(BaseModel):
    permissions: list[RoleModulePermission] = Field(default_factory=list)


class UserDirectoryFilters(BaseModel):
    search: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=60)
    status: Literal["all", "active", "inactive", "locked"] = "all"
    store_id: int | None = Field(default=None, ge=1)


class UserDirectoryTotals(BaseModel):
    total: int
    active: int
    inactive: int
    locked: int


class UserDirectoryEntry(BaseModel):
    user_id: int = Field(alias="id")
    username: str
    full_name: str | None = Field(default=None)
    telefono: str | None = Field(default=None)
    rol: str
    estado: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    store_id: int | None = Field(default=None)
    store_name: str | None = Field(default=None)
    last_login_at: datetime | None = None
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(populate_by_name=True)


class UserDirectoryReport(BaseModel):
    generated_at: datetime
    filters: UserDirectoryFilters
    totals: UserDirectoryTotals
    items: list[UserDirectoryEntry]


class UserDashboardActivity(BaseModel):
    id: int
    action: str
    created_at: datetime
    severity: Literal["info", "warning", "critical"]
    performed_by_id: int | None = None
    performed_by_name: str | None = None
    target_user_id: int | None = None
    target_username: str | None = None
    details: dict[str, Any] | None = None


class UserSessionSummary(BaseModel):
    session_id: int
    user_id: int
    username: str
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    status: Literal["activa", "revocada", "expirada"]
    revoke_reason: str | None = None


class UserDashboardMetrics(BaseModel):
    generated_at: datetime
    totals: UserDirectoryTotals
    recent_activity: list[UserDashboardActivity] = Field(default_factory=list)
    active_sessions: list[UserSessionSummary] = Field(default_factory=list)
    audit_alerts: DashboardAuditAlerts


# // [PACK28-schemas]
class AuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=3, max_length=128)
    otp: str | None = Field(default=None, min_length=6, max_length=6)


# // [PACK28-schemas]
class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# // [PACK28-schemas]
class AuthProfileResponse(UserResponse):
    name: str
    email: str | None = Field(default=None)
    role: str


class TokenResponse(BaseModel):
    access_token: str
    session_id: int
    token_type: str = "bearer"


class SessionLoginResponse(BaseModel):
    session_id: int
    detail: str


class PasswordRecoveryRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=20, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    detail: str
    reset_token: str | None = Field(default=None)


class TokenPayload(BaseModel):
    # // [PACK28-schemas]
    sub: str
    name: str | None = None
    role: str | None = None
    iat: int
    exp: int
    jti: str
    sid: str | None = None
    token_type: str = Field(default="access")


class TokenVerificationRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)


class TokenVerificationResponse(BaseModel):
    is_valid: bool = Field(...,
                           description="Indica si el token sigue siendo válido.")
    detail: str = Field(...,
                        description="Mensaje descriptivo del estado del token.")
    session_id: int | None = Field(
        default=None,
        description="Identificador interno de la sesión asociada al token.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Fecha de expiración registrada para la sesión.",
    )
    user: UserResponse | None = Field(
        default=None,
        description="Información del usuario cuando el token es válido.",
    )

    model_config = ConfigDict(from_attributes=True)


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TOTPStatusResponse(BaseModel):
    is_active: bool
    activated_at: datetime | None
    last_verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TOTPActivateRequest(BaseModel):
    """Payload para activar 2FA TOTP.

    Acepta alias comunes como otp/totp/token/otp_code sin generar warnings de alias.
    """

    code: str = Field(..., min_length=6, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        if "code" not in data:
            for key in ("otp", "totp", "token", "otp_code"):
                if key in data and data[key]:
                    data["code"] = data[key]
                    break
        return data


class ActiveSessionResponse(BaseModel):
    id: int
    user_id: int
    session_token: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    revoked_by_id: int | None
    revoke_reason: str | None
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_reason_alias(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "reason" not in data:
            for alias in ("motivo", "revoke_reason"):
                if alias in data:
                    data["reason"] = data[alias]
                    break
        return data


class POSReturnItemRequest(BaseModel):
    """Item devuelto desde el POS identificable por producto, línea o IMEI."""

    sale_item_id: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            validation_alias=AliasChoices(
                "sale_item_id",
                "saleItemId",
                "item_id",
                "itemId",
            ),
        ),
    ]
    product_id: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            validation_alias=AliasChoices(
                "product_id",
                "productId",
                "device_id",
            ),
        ),
    ]
    imei: Annotated[
        str | None,
        Field(
            default=None,
            max_length=18,
            validation_alias=AliasChoices("imei", "imei_1"),
        ),
    ]
    qty: Annotated[
        int,
        Field(
            ...,
            ge=1,
            validation_alias=AliasChoices("quantity", "qty"),
        ),
    ]
    disposition: Annotated[
        ReturnDisposition,
        Field(
            default=ReturnDisposition.VENDIBLE,
            validation_alias=AliasChoices("disposition", "estado"),
        ),
    ]
    warehouse_id: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            validation_alias=AliasChoices(
                "warehouse_id", "warehouseId", "almacen_id"),
        ),
    ]

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "POSReturnItemRequest":
        if not (self.sale_item_id or self.product_id or self.imei):
            raise ValueError(
                "Debes proporcionar sale_item_id, product_id o imei para la devolución."
            )
        return self


class BootstrapStatusResponse(BaseModel):
    disponible: bool = Field(
        ...,
        description="Indica si el registro inicial de administrador está habilitado.",
    )
    usuarios_registrados: int = Field(
        ...,
        description="Cantidad de usuarios actualmente registrados en el sistema.",
    )


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class UserStatusUpdate(BaseModel):
    is_active: bool
