"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute

from . import crud, security as security_core
from .config import settings
from .core.roles import DEFAULT_ROLES
from .core.transactions import transactional_session
from .database import Base, SessionLocal, engine, get_db
from .routers import (
    audit,
    auth,
    backups,
    customers,
    health,
    import_validation,
    inventory,
    monitoring,
    operations,
    pos,
    purchases,
    repairs,
    reports,
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

from backend.core.logging import logger as core_logger, setup_logging

setup_logging()
logger = core_logger.bind(component="backend.app.main")

_scheduler: BackgroundScheduler | None = None

SENSITIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SENSITIVE_PREFIXES = (
    "/inventory",
    "/purchases",
    "/sales",
    "/pos",
    "/backups",
    "/customers",
    "/suppliers",
    "/repairs",
    "/transfers",
    "/security",
    "/sync/outbox",
    "/operations",
)




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
        if request.method.upper() == "OPTIONS":
            response = Response(status_code=200)
            origin = request.headers.get("origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
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
            auth_header = request.headers.get("Authorization")
            session_cookie = request.cookies.get(settings.session_cookie_name)
            token_payload = None
            session_token: str | None = None

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
                    except HTTPException as exc:  # pragma: no cover - error propagado
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
                    if request.method.upper() in SENSITIVE_METHODS and any(
                        request.url.path.startswith(prefix)
                        for prefix in SENSITIVE_PREFIXES
                    ):
                        reason = request.headers.get("X-Reason")
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
                if module:
                    action = _resolve_action(request.method)
                    if not crud.user_has_module_permission(db, user, module, action):
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
    app.include_router(system_logs.router)
    app.include_router(monitoring.router)
    app.include_router(audit.router)
    return app


app = create_app()
