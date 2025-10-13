"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .database import Base, engine
from .routers import health, stores


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.title, version=settings.version, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(stores.router)
    return app


app = create_app()
