"""Pydantic schemas for Device entities."""
from pydantic import BaseModel, ConfigDict, Field


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80)
    name: str = Field(..., max_length=150)
    quantity: int = Field(default=0, ge=0)


class DeviceCreate(DeviceBase):
    pass


class Device(DeviceBase):
    id: int
    store_id: int

    model_config = ConfigDict(from_attributes=True)
