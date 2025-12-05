"""Punto de entrada para la aplicación FastAPI."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud
from .config import settings
from .core.roles import DEFAULT_ROLES
from .core.transactions import transactional_session
from .database import SessionLocal, get_db, Base
from .middleware import (
    DEFAULT_EXPORT_PREFIXES,
    DEFAULT_EXPORT_TOKENS,
    DEFAULT_SENSITIVE_GET_PREFIXES,
    build_reason_header_middleware,
)
from .middleware.error_handler import capture_internal_errors
from .middleware.cors_handler import cors_preflight_handler
from .routers import (
    alerts,
    configuration,
    audit,
    audit_ui,
    auth,
    backups,
    cloud,
    customers,
    dte,
    health,
    help_center,
    discovery,
    import_validation,
    integrations,
    integration_hooks,
    inventory,
    inventory_export,
    inventory_import,
    inventory_variants,
    inventory_counts,
    loyalty,
    monitoring,
    observability_admin,
    operations,
    price_lists,
    payments,
    pos,
    support,
    rmas,
    purchases,
    repairs,
    warranties,
    reports,
    reports_sales,
    store_credits,
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

    _enforce_reason_header = build_reason_header_middleware(
        sensitive_methods=settings.sensitive_methods,
        sensitive_prefixes=tuple(settings.sensitive_prefixes),
        export_tokens=DEFAULT_EXPORT_TOKENS,
        export_prefixes=DEFAULT_EXPORT_PREFIXES,
        read_sensitive_get_prefixes=tuple(settings.read_sensitive_prefixes),
        optional_reason_prefixes=tuple(settings.optional_reason_prefixes),
        optional_reason_suffixes=tuple(settings.optional_reason_suffixes),
    )

    @app.middleware("http")
    async def enforce_reason_header(request: Request, call_next):
        return await _enforce_reason_header(request, call_next)

    app.middleware("http")(capture_internal_errors)
    app.middleware("http")(cors_preflight_handler)

    routers_to_mount: tuple[APIRouter, ...] = (
        health.router,
        help_center.router,
        support.router,
        alerts.router,
        auth.router,
        users.router,
        stores.router,
        inventory.router,
        inventory_export.router,
        inventory_import.router,
        inventory_variants.router,
        inventory_counts.router,
        import_validation.router,
        discovery.router,
        pos.router,
        purchases.router,
        price_lists.router,
        price_lists.pricing_router,
        loyalty.router,
        payments.router,
        customers.router,
        configuration.router,
        store_credits.router,
        suppliers.router,
        repairs.router,
        warranties.router,
        sales.router,
        dte.router,
        returns.router,
        rmas.router,
        operations.router,
        sync.router,
        integrations.router,
        integration_hooks.router,
        transfers.router,
        updates.router,
        backups.router,
        cloud.router,
        reports.router,
        reports_sales.router,
        security_router.router,
        system_logs.router,
        monitoring.router,
        observability_admin.router,
        audit.router,
        audit_ui.router,
        # Los handlers verifican el flag y devuelven 404 cuando está desactivado.
        wms_bins.router,
    )

    for module_router in routers_to_mount:
        app.include_router(module_router)

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
        app.include_router(versioned_router)

    _mount_versioned(settings.api_v1_prefix)

    for alias_prefix in settings.api_alias_prefixes:
        _mount_versioned(alias_prefix)

    return app


app = create_app()
