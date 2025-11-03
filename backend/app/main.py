"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import traceback

import asyncio
from collections.abc import Callable, Generator, Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from . import crud, security as security_core
from .config import settings
from .core.roles import DEFAULT_ROLES
from .core.transactions import transactional_session
from .database import SessionLocal, get_db
from .routers import (
    audit,
    audit_ui,
    auth,
    backups,
    customers,
    health,
    import_validation,
    inventory,
    monitoring,
    operations,
    payments,
    pos,
    purchases,
    repairs,
    reports,
    reports_sales,
    sales,
    security as security_router,
    system_logs,
    stores,
    suppliers,
    sync,
    transfers,
    updates,
    users,
)
from .services.scheduler import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

SENSITIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SENSITIVE_PREFIXES = (
    "/inventory",
    "/purchases",
    "/sales",
    "/pos",
    "/backups",
    "/customers",
    "/reports",
    "/payments",
    "/suppliers",
    "/repairs",
    "/transfers",
    "/security",
    "/sync/outbox",
    "/operations",
)
READ_SENSITIVE_PREFIXES = ("/pos", "/reports", "/customers")




def _remove_route(target_app: FastAPI, path: str, method: str) -> None:
    """Elimina de la aplicación la ruta que coincida con el path y método."""

    method_upper = method.upper()
    routes = target_app.router.routes
    target_app.router.routes[:] = [
        route
        for route in routes
        if not (
            isinstance(route, APIRoute)
            and route.path == path
            and method_upper in (route.methods or {"GET"})
        )
    ]


def _mount_pos_extensions(target_app: FastAPI) -> None:
    """Registra los endpoints POS extendidos sobre la app principal."""

    from backend.routes.pos import extended_router

    _remove_route(target_app, "/pos/receipt/{sale_id}", "GET")
    target_app.include_router(extended_router)

ROLE_PROTECTED_PREFIXES: dict[str, set[str]] = {
    "/users": {"ADMIN"},
    "/sync": {"ADMIN", "GERENTE"},
}

MODULE_PERMISSION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("/users", "usuarios"),
    ("/security", "seguridad"),
    ("/inventory", "inventario"),
    ("/stores", "tiendas"),
    ("/purchases", "compras"),
    ("/sales", "ventas"),
    ("/pos", "pos"),
    ("/customers", "clientes"),
    ("/payments", "ventas"),
    ("/suppliers", "proveedores"),
    ("/repairs", "reparaciones"),
    ("/transfers", "transferencias"),
    ("/operations", "operaciones"),
    ("/reports", "reportes"),
    ("/audit", "auditoria"),
    ("/sync", "sincronizacion"),
    ("/backups", "respaldos"),
    ("/updates", "actualizaciones"),
)


def _resolve_module(path: str) -> str | None:
    for prefix, module in MODULE_PERMISSION_PREFIXES:
        if path.startswith(prefix):
            return module
    return None


def _resolve_action(method: str) -> str:
    normalized = method.upper()
    if normalized == "DELETE":
        return "delete"
    if normalized in {"POST", "PUT", "PATCH"}:
        return "edit"
    return "view"


def _bootstrap_defaults() -> None:
    with SessionLocal() as session:
        with transactional_session(session):
            for role in DEFAULT_ROLES:
                crud.ensure_role(session, role)


def _authorize_request_sync(
    dependency: Callable[[], Generator[Session, None, None]],
    headers: Mapping[str, str],
    cookies: Mapping[str, str],
    method_upper: str,
    path: str,
    module: str | None,
    required_roles: set[str],
) -> Response | None:
    db_generator = dependency()
    try:
        try:
            db: Session = next(db_generator)
        except StopIteration:  # pragma: no cover - defensive
            return JSONResponse(
                status_code=500,
                content={"detail": "No fue posible obtener la sesión de base de datos."},
            )

        auth_header = headers.get("Authorization") or headers.get("authorization")
        session_cookie = cookies.get(settings.session_cookie_name)
        session_token: str | None = None
        user = None

        if auth_header:
            parts = auth_header.split(" ", 1)
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Esquema de autenticación inválido."},
                )
            token = parts[1].strip()
            try:
                token_payload = security_core.decode_token(token)
            except HTTPException as exc:  # pragma: no cover - propagado
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                )
            session_token = token_payload.jti
            active_session = crud.get_active_session_by_token(db, session_token)
            if active_session is None or active_session.revoked_at is not None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sesión inválida o revocada."},
                )
            if crud.is_session_expired(active_session.expires_at):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sesión expirada."},
                )
            user = crud.get_user_by_username(db, token_payload.sub)
        elif session_cookie:
            session_token = session_cookie
            active_session = crud.get_active_session_by_token(db, session_token)
            if active_session is None or active_session.revoked_at is not None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sesión inválida o revocada."},
                )
            if crud.is_session_expired(active_session.expires_at):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sesión expirada."},
                )
            user = active_session.user
        else:
            requires_reason = (
                method_upper in SENSITIVE_METHODS
                and any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES)
            ) or (
                method_upper == "GET"
                and any(path.startswith(prefix) for prefix in READ_SENSITIVE_PREFIXES)
            )
            if requires_reason:
                reason = headers.get("X-Reason") or headers.get("x-reason")
                if not reason or len(reason.strip()) < 5:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": "Proporciona el encabezado X-Reason con al menos 5 caracteres.",
                        },
                    )
            return JSONResponse(
                status_code=401,
                content={"detail": "Autenticación requerida."},
            )

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

        if module and not crud.user_has_module_permission(db, user, module, _resolve_action(method_upper)):
            return JSONResponse(
                status_code=403,
                content={"detail": "No cuentas con permisos para este módulo."},
            )

        if session_token:
            crud.mark_session_used(db, session_token)
    finally:
        close_gen = getattr(db_generator, "close", None)
        if callable(close_gen):
            close_gen()

    return None


@asynccontextmanager
async def lifespan(_: FastAPI):
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

    def _persist_system_error(request: Request, exc: Exception, *, status_code: int | None = None) -> None:
        if status_code is not None and status_code < 500:
            return
        module = _resolve_module(request.url.path) or "general"
        message = getattr(exc, "detail", str(exc))
        stack_trace = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        client_host = request.client.host if request.client else None
        try:
            with SessionLocal() as session:
                with transactional_session(session):
                    username: str | None = None
                    auth_header = request.headers.get("Authorization") or ""
                    token_parts = auth_header.split(" ", 1)
                    if len(token_parts) == 2 and token_parts[0].lower() == "bearer":
                        token = token_parts[1].strip()
                        try:
                            payload = security_core.decode_token(token)
                            user = crud.get_user_by_username(session, payload.sub)
                            if user is not None:
                                username = user.username
                        except HTTPException:
                            username = None
                    crud.register_system_error(
                        session,
                        mensaje=message,
                        stack_trace=stack_trace,
                        modulo=module,
                        usuario=username,
                        ip_origen=client_host,
                    )
        except Exception:  # pragma: no cover - evitamos fallos en el logger
            logger.exception(
                "No se pudo registrar el error del sistema en la bitácora."
            )

    @app.middleware("http")
    async def enforce_reason_header(request: Request, call_next):
        method_upper = request.method.upper()
        requires_reason = (
            method_upper in SENSITIVE_METHODS
            and any(request.url.path.startswith(prefix) for prefix in SENSITIVE_PREFIXES)
        ) or (
            method_upper == "GET"
            and any(
                request.url.path.startswith(prefix) for prefix in READ_SENSITIVE_PREFIXES
            )
        )
        if requires_reason:
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
    async def capture_internal_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException as exc:
            _persist_system_error(request, exc, status_code=exc.status_code)
            raise
        except Exception as exc:  # pragma: no cover - errores inesperados
            _persist_system_error(request, exc)
            raise

    @app.middleware("http")
    async def enforce_route_permissions(request: Request, call_next):
        method_upper = request.method.upper()
        if method_upper == "OPTIONS":
            response = Response(status_code=200)
            origin = request.headers.get("origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            allow_headers = request.headers.get("access-control-request-headers")
            if allow_headers:
                response.headers["Access-Control-Allow-Headers"] = allow_headers
            allow_method = request.headers.get("access-control-request-method")
            if allow_method:
                response.headers["Access-Control-Allow-Methods"] = allow_method
            return response
        module = _resolve_module(request.url.path)
        required_roles: set[str] = set()
        for prefix, roles in ROLE_PROTECTED_PREFIXES.items():
            if request.url.path.startswith(prefix):
                required_roles = roles
                break

        if module or required_roles:
            dependency = request.app.dependency_overrides.get(get_db, get_db)
            auth_response = await asyncio.to_thread(
                _authorize_request_sync,
                dependency,
                request.headers,
                request.cookies,
                method_upper,
                request.url.path,
                module,
                set(required_roles),
            )
            if auth_response is not None:
                return auth_response

        response = await call_next(request)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(stores.router)
    app.include_router(inventory.router)
    app.include_router(import_validation.router)
    app.include_router(pos.router)
    _mount_pos_extensions(app)
    app.include_router(purchases.router)
    app.include_router(payments.router)
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
    app.include_router(reports_sales.router)
    app.include_router(security_router.router)
    app.include_router(system_logs.router)
    app.include_router(monitoring.router)
    app.include_router(audit.router)
    app.include_router(audit_ui.router)
    return app


app = create_app()
