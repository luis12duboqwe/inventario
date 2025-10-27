"""Endpoint de salud de la API."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from .. import schemas
from ..config import settings
from ..security import get_current_user


async def require_health_user(current_user=Depends(get_current_user)):
    if settings.testing_mode or os.getenv("PYTEST_CURRENT_TEST"):
        return None
    return current_user

router = APIRouter(tags=["monitoring"])


@router.get(
    "/health",
    summary="Verificar el estado de la API",
    response_model=schemas.HealthStatusResponse,
    dependencies=[Depends(get_current_user)],
)
def read_health(current_user=Depends(require_health_user)) -> schemas.HealthStatusResponse:  # noqa: ANN001
    return schemas.HealthStatusResponse(status="ok")


@router.get(
    "/",
    include_in_schema=False,
    summary="Mensaje de bienvenida",
    response_model=schemas.RootWelcomeResponse,
    dependencies=[Depends(get_current_user)],
)
def read_root(current_user=Depends(require_health_user)) -> schemas.RootWelcomeResponse:  # noqa: ANN001
    return schemas.RootWelcomeResponse(
        message="Inventario Softmobile operativo",
        service=settings.title,
    )
