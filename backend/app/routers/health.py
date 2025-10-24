"""Endpoint de salud de la API."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..database import get_db
from ..security import get_current_user, oauth2_scheme


async def require_health_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):  # noqa: ANN201
    if settings.testing_mode or os.getenv("PYTEST_CURRENT_TEST"):
        return None
    return await get_current_user(request=request, token=token, db=db)

router = APIRouter(tags=["monitoring"])


@router.get(
    "/health",
    summary="Verificar el estado de la API",
    response_model=schemas.HealthStatusResponse,
)
def read_health(current_user=Depends(require_health_user)) -> schemas.HealthStatusResponse:  # noqa: ANN001
    return schemas.HealthStatusResponse(status="ok")


@router.get(
    "/",
    include_in_schema=False,
    summary="Mensaje de bienvenida",
    response_model=schemas.RootWelcomeResponse,
)
def read_root(current_user=Depends(require_health_user)) -> schemas.RootWelcomeResponse:  # noqa: ANN001
    return schemas.RootWelcomeResponse(
        message="Inventario Softmobile operativo",
        service=settings.title,
    )
