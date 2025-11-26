"""Endpoints para el centro de ayuda y modo demostración."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas.help_center import DemoPreview, HelpCenterResponse
from ..services.demo_mode import get_demo_dataset, get_help_guides, is_demo_mode_enabled

router = APIRouter(prefix="/help", tags=["help"])


@router.get("/context", response_model=HelpCenterResponse)
def get_help_context() -> HelpCenterResponse:
    """Devuelve las guías contextuales y el estado del modo demo."""

    guides = get_help_guides()
    return HelpCenterResponse(
        guides=guides,
        manuals_base_path="docs/capacitacion",
        demo_mode_enabled=is_demo_mode_enabled(),
    )


@router.get("/demo", response_model=DemoPreview)
def get_demo_preview() -> DemoPreview:
    """Informa si el modo demo está activo y entrega dataset ficticio aislado."""

    enabled = is_demo_mode_enabled()
    notice = (
        "Modo demostración habilitado: los datos listados son ficticios y no tocan la base corporativa."
        if enabled
        else "Modo demostración desactivado: activa SOFTMOBILE_DEMO_MODE=1 para exponer el dataset ficticio."
    )
    dataset = get_demo_dataset() if enabled else None
    return DemoPreview(enabled=enabled, notice=notice, dataset=dataset)
