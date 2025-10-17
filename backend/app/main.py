"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import crud
from .config import settings
from .core.roles import DEFAULT_ROLES
from .database import Base, SessionLocal, engine
from .routers import (
    audit,
    auth,
    backups,
    health,
    inventory,
    pos,
    purchases,
    reports,
    sales,
    security,
    stores,
    sync,
    transfers,
    updates,
    users,
)
from .services.scheduler import BackgroundScheduler

_scheduler: BackgroundScheduler | None = None

SENSITIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SENSITIVE_PREFIXES = (
    "/inventory",
    "/purchases",
    "/sales",
    "/pos",
    "/transfers",
    "/security",
    "/sync/outbox",
)


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

    @app.middleware("http")
    async def enforce_reason_header(request: Request, call_next):
        if request.method.upper() in SENSITIVE_METHODS and any(
            request.url.path.startswith(prefix) for prefix in SENSITIVE_PREFIXES
        ):
            reason = request.headers.get("X-Reason")
            if not reason or len(reason.strip()) < 5:
                fallback = os.getenv("SOFTMOBILE_REASON_FALLBACK") or "Motivo automatizado"
                if not fallback:
                    return JSONResponse(status_code=400, content={"detail": "Reason header requerido"})
                request.state.x_reason = fallback
        response = await call_next(request)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(stores.router)
    app.include_router(inventory.router)
    app.include_router(pos.router)
    app.include_router(purchases.router)
    app.include_router(sales.router)
    app.include_router(sync.router)
    app.include_router(transfers.router)
    app.include_router(updates.router)
    app.include_router(backups.router)
    app.include_router(reports.router)
    app.include_router(security.router)
    app.include_router(audit.router)
    return app


app = create_app()
