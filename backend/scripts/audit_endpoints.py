#!/usr/bin/env python3
"""
Auditoría de endpoints: lista rutas, clasifica si requieren X-Reason (según reglas
centrales), determina módulo y roles requeridos, y genera un resumen JSON + tabla.

Uso:
  /workspaces/inventario/.venv/bin/python backend/scripts/audit_endpoints.py [--json out.json]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from fastapi.routing import APIRoute
import os

# Variables mínimas para inicializar la app sin requerir entorno completo.
os.environ.setdefault("DATABASE_URL", "sqlite:///./audit_dummy.db")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_audit_secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "1")
os.environ.setdefault("CORS_ORIGINS", "[\"http://localhost\"]")
os.environ.setdefault("ENABLE_BACKGROUND_SCHEDULER", "0")
os.environ.setdefault("TESTING_MODE", "1")

from backend.app.main import (  # noqa: E402
    READ_SENSITIVE_PREFIXES,
    ROLE_PROTECTED_PREFIXES,
    SENSITIVE_METHODS,
    SENSITIVE_PREFIXES,
    _resolve_module,
    create_app,
)


@dataclass
class RouteAudit:
    path: str
    methods: list[str]
    module: str | None
    requires_reason: bool
    required_roles: list[str]


def _requires_reason_get(path: str) -> bool:
    if any(token in path for token in ("/csv", "/pdf", "/xlsx", "/export/")) and (
        path.startswith("/reports")
        or path.startswith("/purchases")
        or path.startswith("/sales")
        or path.startswith("/backups")
        or path.startswith("/users")
    ):
        return True
    if path.startswith("/pos/receipt") or path.startswith("/pos/config"):
        return True
    return False


def _compute_requires_reason(path: str, method: str) -> bool:
    m = method.upper()
    if m in SENSITIVE_METHODS and any(path.startswith(p) for p in SENSITIVE_PREFIXES):
        return True
    if m == "GET" and _requires_reason_get(path):
        return True
    return False


def _resolve_required_roles(path: str) -> list[str]:
    for prefix, roles in ROLE_PROTECTED_PREFIXES.items():
        if path.startswith(prefix):
            return sorted(roles)
    # Si no hay prefijo protegido, algunos GET de POS/REPORTES siguen siendo sensibles
    if any(path.startswith(p) for p in READ_SENSITIVE_PREFIXES):
        return []
    return []


def collect_audit(app) -> list[RouteAudit]:
    audits: list[RouteAudit] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods: Iterable[str] = route.methods or {"GET"}
        for method in sorted(methods):
            if method == "HEAD":
                continue
            module = _resolve_module(route.path)
            audits.append(
                RouteAudit(
                    path=route.path,
                    methods=[method],
                    module=module,
                    requires_reason=_compute_requires_reason(
                        route.path, method),
                    required_roles=_resolve_required_roles(route.path),
                )
            )
    # Consolidar por path acumulando métodos
    by_path: dict[str, RouteAudit] = {}
    for item in audits:
        existing = by_path.get(item.path)
        if existing is None:
            by_path[item.path] = item
        else:
            for m in item.methods:
                if m not in existing.methods:
                    existing.methods.append(m)
            existing.methods.sort()
            existing.requires_reason = existing.requires_reason or item.requires_reason
    return sorted(by_path.values(), key=lambda r: r.path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args()

    app = create_app()
    audits = collect_audit(app)

    # Tabla simple
    print(f"{'PATH':60}  {'METHODS':20}  {'MODULE':15}  {'REQ_REASON':10}  {'ROLES'}")
    for a in audits:
        print(
            f"{a.path:60}  {','.join(a.methods):20}  {str(a.module or '-')[:15]:15}  {str(a.requires_reason):10}  {','.join(a.required_roles) or '-'}"
        )

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in audits], f,
                      ensure_ascii=False, indent=2)
        print(f"\nReporte JSON escrito en: {args.json_path}")


if __name__ == "__main__":
    main()
