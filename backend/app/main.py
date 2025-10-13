"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import crud
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, backups, health, inventory, reports, stores, sync, users
from .services.scheduler import BackgroundScheduler

_scheduler: BackgroundScheduler | None = None


def _bootstrap_defaults() -> None:
    with SessionLocal() as session:
        for role in ("admin", "manager", "auditor"):
            crud.ensure_role(session, role)
        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _bootstrap_defaults()
    global _scheduler
    if settings.enable_background_scheduler:
        _scheduler = BackgroundScheduler()
        await _scheduler.start()
    try:
        yield
    finally:
        if _scheduler is not None:
            await _scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.title, version=settings.version, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(stores.router)
    app.include_router(inventory.router)
    app.include_router(sync.router)
    app.include_router(backups.router)
    app.include_router(reports.router)
    return app


app = create_app()
