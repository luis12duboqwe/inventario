#!/usr/bin/env python3
"""
Verificación de integridad de stock: compara el snapshot de inventario con
resúmenes por sucursal y lista discrepancias.

Uso:
  PYTHONPATH=/workspaces/inventario /workspaces/inventario/.venv/bin/python backend/scripts/verify_stock_integrity.py

Variables mínimas de entorno necesarias (se proveen defaults seguros si faltan):
  - DATABASE_URL (sqlite:///./integrity.db)
  - JWT_SECRET_KEY (dummy)
  - ACCESS_TOKEN_EXPIRE_MINUTES (5)
  - REFRESH_TOKEN_EXPIRE_DAYS (1)
  - CORS_ORIGINS (["http://localhost"])
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Asegurar que el paquete 'backend' sea importable incluso cuando PYTHONPATH no se propaga correctamente
# (escenario observado en pruebas subprocess donde ModuleNotFoundError ocurría).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings  # type: ignore  # noqa: E402
from backend.app.database import SessionLocal, Base, engine  # type: ignore  # noqa: E402
from backend.app.services.backups import build_inventory_snapshot  # type: ignore  # noqa: E402

# Defaults seguros para entorno CLI independiente
os.environ.setdefault("DATABASE_URL", "sqlite:///./integrity.db")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_integrity_secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "1")
os.environ.setdefault("CORS_ORIGINS", "[\"http://localhost\"]")
os.environ.setdefault("ENABLE_BACKGROUND_SCHEDULER", "0")
os.environ.setdefault("TESTING_MODE", "1")


def main() -> None:
    # En modo pruebas, aseguramos que el esquema exista para evitar errores en SQLite vacía
    try:
        if settings.testing_mode:
            Base.metadata.create_all(bind=engine)
    except Exception:
        # No interrumpir la ejecución por errores no críticos de creación
        pass
    with SessionLocal() as session:
        snapshot: dict[str, Any] = build_inventory_snapshot(session)
    stores = snapshot.get("stores", [])
    summary = snapshot.get("summary", {})
    integrity = snapshot.get("integrity_report", {})

    print("Resumen corporativo:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    print("\nSucursales:")
    for store in stores:
        name = store.get("name")
        device_count = store.get("device_count")
        total_units = store.get("total_units")
        inventory_value = store.get("inventory_value")
        print(
            f"- {name}: dispositivos={device_count} unidades={total_units} valor={inventory_value}")

    if integrity:
        print("\nReporte de integridad:")
        print(json.dumps(integrity, ensure_ascii=False, indent=2))
    else:
        print("\nNo se encontraron datos de integridad en el snapshot.")


if __name__ == "__main__":
    main()
