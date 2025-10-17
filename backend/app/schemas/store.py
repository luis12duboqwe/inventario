"""Pydantic schemas for Store entities."""
from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120, description="Nombre de la sucursal")
    location: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default="UTC", max_length=50)


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=50)


class Store(StoreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
