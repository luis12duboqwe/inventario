"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import crud, security as security_core
from .config import settings
from .core.roles import DEFAULT_ROLES
from .database import Base, SessionLocal, engine, get_db
from .routers import (
    audit,
    auth,
    backups,
    customers,
    health,
    inventory,
    operations,
    pos,
    purchases,
    repairs,
    reports,
    sales,
    security as security_router,
    stores,
    suppliers,
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
    "/customers",
    "/suppliers",
    "/repairs",
    "/transfers",
    "/security",
    "/sync/outbox",
    "/operations",
)

ROLE_PROTECTED_PREFIXES: dict[str, set[str]] = {
    "/users": {"ADMIN"},
    "/sync": {"ADMIN", "GERENTE"},
}


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
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Proporciona el encabezado X-Reason con al menos 5 caracteres.",
                    },
                )
            request.state.x_reason = reason.strip()
        response = await call_next(request)
        return response

    @app.middleware("http")
    async def enforce_route_permissions(request: Request, call_next):
        for prefix, required_roles in ROLE_PROTECTED_PREFIXES.items():
            if request.url.path.startswith(prefix):
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Autenticación requerida."},
                    )
                parts = auth_header.split(" ", 1)
                if len(parts) != 2 or parts[0].lower() != "bearer":
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Esquema de autenticación inválido."},
                    )
                token = parts[1].strip()
                try:
                    payload = security_core.decode_token(token)
                except HTTPException as exc:  # pragma: no cover - error propagado
                    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

                dependency = request.app.dependency_overrides.get(get_db, get_db)
                db_generator = dependency()
                try:
                    db = next(db_generator)
                except StopIteration:  # pragma: no cover - defensive
                    db = None
                try:
                    if db is None:
                        return JSONResponse(
                            status_code=500,
                            content={"detail": "No fue posible obtener la sesión de base de datos."},
                        )
                    active_session = crud.get_active_session_by_token(db, payload.jti)
                    if active_session is None or active_session.revoked_at is not None:
                        return JSONResponse(
                            status_code=401,
                            content={"detail": "Sesión inválida o revocada."},
                        )
                    user = crud.get_user_by_username(db, payload.sub)
                    if user is None or not user.is_active:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Usuario inactivo o inexistente."},
                        )
                    user_roles = {assignment.role.name for assignment in user.roles}
                    if required_roles and user_roles.isdisjoint(required_roles):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "No cuentas con permisos suficientes."},
                        )
                    crud.mark_session_used(db, payload.jti)
                finally:
                    close_gen = getattr(db_generator, "close", None)
                    if callable(close_gen):
                        close_gen()
                break

        response = await call_next(request)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(stores.router)
    app.include_router(inventory.router)
    app.include_router(pos.router)
    app.include_router(purchases.router)
    app.include_router(customers.router)
    app.include_router(suppliers.router)
    app.include_router(repairs.router)
    app.include_router(sales.router)
    app.include_router(operations.router)
    app.include_router(sync.router)
    app.include_router(transfers.router)
    app.include_router(updates.router)
    app.include_router(backups.router)
    app.include_router(reports.router)
    app.include_router(security_router.router)
    app.include_router(audit.router)
    return app


app = create_app()
