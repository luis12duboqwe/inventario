"""Esquemas Pydantic para validar solicitudes y respuestas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import BackupMode, MovementType, SyncMode, SyncStatus


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120, description="Nombre visible de la sucursal")
    location: Optional[str] = Field(default=None, max_length=120, description="Dirección o referencia")
    timezone: str = Field(default="UTC", max_length=50, description="Zona horaria de la sucursal")


class StoreCreate(StoreBase):
    pass


class StoreResponse(StoreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80, description="Identificador único del producto")
    name: str = Field(..., max_length=120, description="Descripción del dispositivo")
    quantity: int = Field(default=0, ge=0, description="Cantidad disponible en inventario")


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    quantity: Optional[int] = Field(default=None, ge=0)


class DeviceResponse(DeviceBase):
    id: int
    store_id: int

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str = Field(..., max_length=80)
    full_name: Optional[str] = Field(default=None, max_length=120)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    roles: list[RoleResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("roles", mode="before")
    @classmethod
    def _flatten_roles(cls, value):
        if value is None:
            return []
        flattened = []
        for item in value:
            role = getattr(item, "role", item)
            flattened.append(role)
        return flattened


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


class MovementBase(BaseModel):
    device_id: int = Field(..., ge=1)
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    reason: Optional[str] = Field(default=None, max_length=255)


class MovementCreate(MovementBase):
    pass


class MovementResponse(MovementBase):
    id: int
    store_id: int
    performed_by_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventorySummary(BaseModel):
    store_id: int
    store_name: str
    total_items: int
    devices: list[DeviceResponse]


class SyncSessionResponse(BaseModel):
    id: int
    store_id: Optional[int]
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    finished_at: Optional[datetime]
    triggered_by_id: Optional[int]
    error_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SyncRequest(BaseModel):
    store_id: Optional[int] = Field(default=None, ge=1)


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str]
    performed_by_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackupRunRequest(BaseModel):
    nota: Optional[str] = Field(default=None, max_length=255)


class BackupJobResponse(BaseModel):
    id: int
    mode: BackupMode
    executed_at: datetime
    pdf_path: str
    archive_path: str
    total_size_bytes: int
    notes: Optional[str]
    triggered_by_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)
