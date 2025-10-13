"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import crud
from .config import settings
from .core.roles import DEFAULT_ROLES
from .database import Base, SessionLocal, engine
from .routers import auth, backups, health, inventory, reports, stores, sync, updates, users
from .services.scheduler import BackgroundScheduler

_scheduler: BackgroundScheduler | None = None


def _bootstrap_defaults() -> None:
    with SessionLocal() as session:
        for role in DEFAULT_ROLES:
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
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(stores.router)
    app.include_router(inventory.router)
    app.include_router(sync.router)
    app.include_router(updates.router)
    app.include_router(backups.router)
    app.include_router(reports.router)
    return app


app = create_app()
