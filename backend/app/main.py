"""Entry point for the Softmobile inventory API."""
from fastapi import FastAPI

from .api.v1.api import api_router
from .db.base_class import Base
from .db.session import engine
from . import models  # noqa: F401  # ensure models are imported for metadata creation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Softmobile Inventory API",
    version="0.1.0",
    description=(
        "API inicial para el sistema Softmobile 2025 v2.2. "
        "Incluye endpoints mínimos para gestionar tiendas y dispositivos."
    ),
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Pequeña ruta raíz para confirmar que la aplicación está disponible."""

    return {"message": "Softmobile API operational"}
