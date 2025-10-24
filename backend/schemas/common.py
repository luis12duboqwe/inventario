"""Esquemas compartidos para respuestas y paginación del backend ligero."""
from __future__ import annotations

from math import ceil
from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.generics import GenericModel

T = TypeVar("T")


class PageParams(BaseModel):
    """Parámetros estándar de paginación."""

    page: int = Field(default=1, ge=1, description="Número de página solicitada")
    size: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Cantidad de registros por página",
    )

    model_config = ConfigDict(extra="forbid")

    @computed_field
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(GenericModel, Generic[T]):
    """Respuesta paginada genérica."""

    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)

    model_config = ConfigDict(extra="forbid")

    @computed_field
    @property
    def pages(self) -> int:
        return ceil(self.total / self.size)

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @classmethod
    def from_items(
        cls,
        items: Sequence[T],
        *,
        page: int,
        size: int,
        total: int | None = None,
    ) -> "Page[T]":
        effective_total = total if total is not None else len(items)
        return cls(items=list(items), total=effective_total, page=page, size=size)


class ErrorResponse(BaseModel):
    """Formato unificado para respuestas de error."""

    code: str = Field(..., min_length=3, max_length=80)
    message: str = Field(..., min_length=3, max_length=1024)

    model_config = ConfigDict(extra="forbid")


class APIStatusResponse(BaseModel):
    """Respuesta resumida para el estado general de la API."""

    message: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Mensaje corporativo que confirma la disponibilidad del servicio.",
    )

    model_config = ConfigDict(extra="forbid")
