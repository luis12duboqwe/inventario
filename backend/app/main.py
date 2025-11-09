"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from collections.abc import Callable, Generator, Mapping

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from . import crud, security as security_core
from .config import settings
from .core.roles import DEFAULT_ROLES
from .core.transactions import transactional_session
from .database import SessionLocal, get_db, Base, engine
from .middleware import (
    DEFAULT_EXPORT_PREFIXES,
    DEFAULT_EXPORT_TOKENS,
    DEFAULT_SENSITIVE_GET_PREFIXES,
    build_reason_header_middleware,
)
from .routers import (
    alerts,
    audit,
    audit_ui,
    auth,
    backups,
    customers,
    health,
    import_validation,
    integrations,
    inventory,
    inventory_export,
    inventory_import,
    monitoring,
    operations,
    price_lists,
    payments,
    pos,
    purchases,
    price_lists,
    repairs,
    reports,
    reports_sales,
    returns,
    sales,
    security as security_router,
    system_logs,
    stores,
    suppliers,
    sync,
    transfers,
    updates,
    users,
    wms_bins,
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
    "/returns",
    "/transfers",
    "/security",
    "/sync/outbox",
    "/operations",
    "/pricing",
    "/integrations",
    "/price-lists",
)
READ_SENSITIVE_PREFIXES = ("/pos", "/reports", "/customers")


def _resolve_additional_cors_origins() -> set[str]:
    """Genera orígenes adicionales para entornos de desarrollo (Codespaces, localhost)."""

    extra_origins: set[str] = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }

    dev_host = os.getenv("VITE_DEV_HOST", "").strip()
    if dev_host and dev_host not in {"localhost", "127.0.0.1"}:
        extra_origins.add(f"http://{dev_host}:5173")
        extra_origins.add(f"https://{dev_host}:5173")

    codespace_name = os.getenv("CODESPACE_NAME", "").strip()
    if codespace_name:
        forwarding_domain = os.getenv(
            "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN",
            "app.github.dev",
        ).strip()
        if forwarding_domain:
            extra_origins.add(
                f"https://{codespace_name}-5173.{forwarding_domain}")
            extra_origins.add(
                f"https://{codespace_name}-4173.{forwarding_domain}")

    env_extra = os.getenv("SOFTMOBILE_EXTRA_ORIGINS", "").strip()
    if env_extra:
        for origin in env_extra.split(","):
            cleaned = origin.strip()
            if cleaned:
                extra_origins.add(cleaned)

    return {origin for origin in extra_origins if origin}


def _resolve_router(target_app: FastAPI | APIRouter) -> APIRouter:
    """Devuelve el enrutador interno independientemente del tipo recibido."""

    if isinstance(target_app, FastAPI):
        return target_app.router
    return target_app


def _remove_route(target_app: FastAPI | APIRouter, path: str, method: str) -> None:
    """Elimina del contenedor de rutas la coincidencia especificada."""

    method_upper = method.upper()
    router = _resolve_router(target_app)
    routes = router.routes
    router.routes[:] = [
        route
        for route in routes
        if not (
            isinstance(route, APIRoute)
            and route.path == path
            and method_upper in (route.methods or {"GET"})
        )
    ]


def _mount_pos_extensions(target_app: FastAPI | APIRouter) -> None:
    """Registra los endpoints POS extendidos sobre la app o router recibido."""

    from backend.routes.pos import extended_router

    _remove_route(target_app, "/pos/receipt/{sale_id}", "GET")
    target_app.include_router(extended_router)


ROLE_PROTECTED_PREFIXES: dict[str, set[str]] = {
    "/users": {"ADMIN"},
    "/sync": {"ADMIN", "GERENTE"},
    "/integrations": {"ADMIN"},
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
    ("/returns", "operaciones"),
    ("/transfers", "transferencias"),
    ("/operations", "operaciones"),
    ("/pricing", "precios"),
    ("/reports", "reportes"),
    ("/audit", "auditoria"),
    ("/sync", "sincronizacion"),
    ("/backups", "respaldos"),
    ("/updates", "actualizaciones"),
    ("/integrations", "integraciones"),
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


def _bootstrap_defaults(session: Session = None) -> None:
    """Crea datos base requeridos (roles, etc.) usando la sesión provista.

    En pruebas, esta sesión debe provenir del motor de pruebas para evitar
    desincronizaciones entre motores en memoria.
    """
    created_local_session = False
    if session is None:
        session = SessionLocal()
        created_local_session = True
    try:
        with transactional_session(session):
            for role in DEFAULT_ROLES:
                crud.ensure_role(session, role)
    finally:
        if created_local_session:
            session.close()


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
                content={
                    "detail": "No fue posible obtener la sesión de base de datos."},
            )

        auth_header = headers.get(
            "Authorization") or headers.get("authorization")
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
            active_session = crud.get_active_session_by_token(
                db, session_token)
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
            active_session = crud.get_active_session_by_token(
                db, session_token)
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
            # Reglas de GET: solo exigir en exportaciones (csv/pdf/xlsx/export) y lecturas POS sensibles
            def _requires_reason_get(p: str) -> bool:
                if any(token in p for token in ("/csv", "/pdf", "/xlsx", "/export/")) and (
                    p.startswith("/reports")
                    or p.startswith("/purchases")
                    or p.startswith("/sales")
                    or p.startswith("/backups")
                    or p.startswith("/users")
                ):
                    return True
                if p.startswith("/pos/receipt") or p.startswith("/pos/config"):
                    return True
                return False

            requires_reason = (
                method_upper in SENSITIVE_METHODS
                and any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES)
            ) or (method_upper == "GET" and _requires_reason_get(path))
            if requires_reason:
                reason = headers.get("X-Reason") or headers.get("x-reason")
                if not reason or len(reason.strip()) < 5:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": "X-Reason header required with at least 5 characters.",
                        },
                    )
            else:
                # Si el cliente envía X-Reason pero es inválido, rechazar igualmente
                reason_hdr = headers.get("X-Reason") or headers.get("x-reason")
                if reason_hdr is not None and len(reason_hdr.strip()) < 5:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": "X-Reason header required with at least 5 characters."},
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
async def lifespan(app: FastAPI):
    # Obtiene la sesión a utilizar para bootstrap. En pruebas, usa el override
    # de get_db para compartir el mismo motor que las fixtures.
    override_dep = app.dependency_overrides.get(get_db)
    created_local_session = False
    session: Session | None = None
    try:
        if override_dep is not None:
            # override_dep es un generador fastapi-style
            gen = override_dep()
            try:
                session = next(gen)
            except StopIteration:  # pragma: no cover - defensivo
                session = None
        if session is None:
            session = SessionLocal()
            created_local_session = True

        # En modo pruebas, crea el esquema en el motor asociado a la sesión usada
        # para que las consultas de bootstrap no fallen por tablas inexistentes.
        if settings.testing_mode:
            try:
                bind = session.get_bind()
                Base.metadata.create_all(bind=bind)
            except Exception:  # pragma: no cover - defensivo en pruebas
                logger.exception(
                    "No se pudo crear el esquema en modo de pruebas")

        _bootstrap_defaults(session)
    finally:
        if created_local_session and session is not None:
            session.close()
    global _scheduler
    if settings.enable_background_scheduler:
        _scheduler = BackgroundScheduler(session_provider=SessionLocal)
        await _scheduler.start()
    try:
        yield
    finally:
        if _scheduler is not None:
            await _scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.title,
                  version=settings.version, lifespan=lifespan)
    if settings.allowed_origins:
        resolved_origins = sorted(
            {origin.strip()
             for origin in settings.allowed_origins if origin.strip()}
            | _resolve_additional_cors_origins()
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _persist_system_error(request: Request, exc: Exception, *, status_code: int | None = None) -> None:
        if status_code is not None and status_code < 500:
            return
        module = _resolve_module(request.url.path) or "general"
        message = getattr(exc, "detail", str(exc))
        if not isinstance(message, str):
            try:
                message = json.dumps(message, ensure_ascii=False)
            except Exception:  # pragma: no cover - degradado seguro
                message = str(message)
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
                            user = crud.get_user_by_username(
                                session, payload.sub)
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

    _enforce_reason_header = build_reason_header_middleware(
        sensitive_methods=SENSITIVE_METHODS,
        sensitive_prefixes=SENSITIVE_PREFIXES,
        export_tokens=DEFAULT_EXPORT_TOKENS,
        export_prefixes=DEFAULT_EXPORT_PREFIXES,
        read_sensitive_get_prefixes=DEFAULT_SENSITIVE_GET_PREFIXES,
    )

    @app.middleware("http")
    async def enforce_reason_header(request: Request, call_next):
        return await _enforce_reason_header(request, call_next)

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
            allow_headers = request.headers.get(
                "access-control-request-headers")
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

    routers_to_mount: tuple[APIRouter, ...] = (
        health.router,
        alerts.router,
        auth.router,
        users.router,
        stores.router,
        inventory.router,
        inventory_export.router,
        inventory_import.router,
        import_validation.router,
        pos.router,
        purchases.router,
        price_lists.router,
        payments.router,
        customers.router,
        suppliers.router,
        repairs.router,
        sales.router,
        returns.router,
        operations.router,
        price_lists.router,
        sync.router,
        integrations.router,
        transfers.router,
        updates.router,
        backups.router,
        reports.router,
        reports_sales.router,
        security_router.router,
        system_logs.router,
        monitoring.router,
        audit.router,
        audit_ui.router,
        wms_bins.router,  # Los handlers verifican el flag y devuelven 404 cuando está desactivado.
    )

    for module_router in routers_to_mount:
        app.include_router(module_router)

    _mount_pos_extensions(app)

    mounted_prefixes: set[str] = set()

    def _mount_versioned(prefix: str) -> None:
        normalized_prefix = prefix.strip()
        if not normalized_prefix or normalized_prefix == "/":
            return
        if not normalized_prefix.startswith("/"):
            normalized_prefix = f"/{normalized_prefix}"
        if normalized_prefix in mounted_prefixes:
            return

        mounted_prefixes.add(normalized_prefix)
        versioned_router = APIRouter(prefix=normalized_prefix)
        for module_router in routers_to_mount:
            versioned_router.include_router(module_router)

        _mount_pos_extensions(versioned_router)
        app.include_router(versioned_router)

    _mount_versioned(settings.api_v1_prefix)

    for alias_prefix in settings.api_alias_prefixes:
        _mount_versioned(alias_prefix)

    return app


app = create_app()
