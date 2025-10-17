"""Genera un escenario de rendimiento para Softmobile 2025 v2.2.0.

Este script utiliza la propia API FastAPI para poblar una base de datos
nueva con al menos 500 dispositivos y 1000 movimientos de inventario,
además de transacciones clave que alimentan los módulos de dashboard.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable, TypeVar, cast

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "softmobile_performance.db"

os.environ.setdefault("SOFTMOBILE_DATABASE_URL", f"sqlite:///{DB_PATH}")
os.environ.setdefault("SOFTMOBILE_ENABLE_CATALOG_PRO", "1")
os.environ.setdefault("SOFTMOBILE_ENABLE_TRANSFERS", "1")
os.environ.setdefault("SOFTMOBILE_ENABLE_PURCHASES_SALES", "1")
os.environ.setdefault("SOFTMOBILE_ENABLE_ANALYTICS_ADV", "1")
os.environ.setdefault("SOFTMOBILE_ENABLE_HYBRID_PREP", "1")
os.environ.setdefault("SOFTMOBILE_ENABLE_2FA", "0")
os.environ.setdefault("SOFTMOBILE_ENABLE_SCHEDULER", "0")
os.environ.setdefault("SOFTMOBILE_ENABLE_BACKUP_SCHEDULER", "0")
os.environ.setdefault(
    "SOFTMOBILE_ALLOWED_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173,http://0.0.0.0:5173",
)

from backend.app.main import app  # noqa: E402  # import after configurar entorno


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123!"
REASON_HEADER = {"X-Reason": "Carga masiva corporativa"}

TOTAL_DEVICES = 500
MOVEMENTS_PER_DEVICE = 2  # entrada + salida para cada dispositivo


@dataclass
class StageResult:
    """Representa el resultado cronometrado de una etapa del escenario."""

    name: str
    duration_seconds: float
    details: dict[str, Any]


class ScenarioError(RuntimeError):
    """Error genérico del escenario de rendimiento."""


T = TypeVar("T")


def _reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _ensure_ok(response, *, context: str) -> dict[str, Any]:
    if response.status_code >= 400:
        raise ScenarioError(
            f"{context} falló con {response.status_code}: {response.text}"
        )
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return {}


def _bootstrap_admin(client: TestClient) -> dict[str, Any]:
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "full_name": "Admin Performance",
        "roles": ["ADMIN", "GERENTE"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    return _ensure_ok(response, context="Bootstrap de administrador")


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/auth/token",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    data = _ensure_ok(response, context="Inicio de sesión")
    token = data.get("access_token")
    if not token:
        raise ScenarioError("La respuesta de autenticación no contiene token")
    return token


def _create_stores(client: TestClient, headers: dict[str, str]) -> list[int]:
    store_specs = [
        {"name": "Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        {"name": "Norte", "location": "Monterrey", "timezone": "America/Monterrey"},
        {"name": "Sur", "location": "Mérida", "timezone": "America/Merida"},
    ]
    store_ids: list[int] = []
    for spec in store_specs:
        response = client.post("/stores", json=spec, headers=headers)
        data = _ensure_ok(response, context=f"Creación de sucursal {spec['name']}")
        store_ids.append(int(data["id"]))
    return store_ids


def _create_users(client: TestClient, headers: dict[str, str]) -> list[int]:
    usernames = [
        ("operaciones", "Operaciones Central", ["GERENTE"]),
        ("analista", "Analista Corporativo", ["GERENTE"]),
        ("soporte", "Soporte Híbrido", ["OPERADOR"]),
    ]
    user_ids: list[int] = []
    for username, full_name, roles in usernames:
        payload = {
            "username": username,
            "password": f"{username.capitalize()}123!",
            "full_name": full_name,
            "roles": roles,
        }
        response = client.post("/users", json=payload, headers=headers)
        data = _ensure_ok(response, context=f"Alta de usuario {username}")
        user_ids.append(int(data["id"]))
    return user_ids


def _create_customers(client: TestClient, headers: dict[str, str]) -> list[int]:
    customers = []
    for index in range(1, 16):
        payload = {
            "name": f"Cliente {index:02d}",
            "contact_name": f"Contacto {index:02d}",
            "email": f"cliente{index:02d}@softmobile.mx",
            "phone": f"555-010-{index:04d}",
            "address": f"Sucursal {index:02d} CDMX",
            "customer_type": "corporativo" if index % 3 == 0 else "minorista",
            "status": "activo",
            "credit_limit": float(index * 1000.0),
            "notes": "Cliente recurrente del escenario de rendimiento.",
            "outstanding_debt": float(index * 150.0),
            "history": [
                {"note": "Registro automático", "timestamp": "2025-02-01T10:00:00"}
            ],
        }
        response = client.post(
            "/customers/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context=f"Alta de cliente {index}")
        customers.append(int(data["id"]))
    return customers


def _create_suppliers(client: TestClient, headers: dict[str, str]) -> list[int]:
    suppliers: list[int] = []
    for index in range(1, 11):
        payload = {
            "name": f"Proveedor {index:02d}",
            "contact_name": f"Proveedor Contacto {index:02d}",
            "email": f"proveedor{index:02d}@softmobile.mx",
            "phone": f"558-020-{index:04d}",
            "address": f"Parque Industrial {index:02d}",
            "notes": "Proveedor con acuerdos marco.",
            "history": [
                {"note": "Negociación anual", "timestamp": "2025-02-02T11:00:00"}
            ],
        }
        response = client.post(
            "/suppliers/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context=f"Alta de proveedor {index}")
        suppliers.append(int(data["id"]))
    return suppliers


def _assign_store_memberships(
    client: TestClient,
    headers: dict[str, str],
    store_ids: Iterable[int],
    user_id: int,
) -> dict[str, Any]:
    assigned: list[int] = []
    for store_id in store_ids:
        payload = {
            "store_id": store_id,
            "user_id": user_id,
            "can_create_transfer": True,
            "can_receive_transfer": True,
        }
        response = client.put(
            f"/stores/{store_id}/memberships/{user_id}",
            json=payload,
            headers=headers,
        )
        _ensure_ok(response, context="Asignación de membresía")
        assigned.append(store_id)
    return {"assigned_store_ids": assigned, "user_id": user_id}


def _create_devices(
    client: TestClient,
    headers: dict[str, str],
    store_ids: Iterable[int],
) -> dict[str, Any]:
    store_cycle = list(store_ids)
    device_ids: dict[int, list[int]] = {store_id: [] for store_id in store_cycle}
    partial_candidates: dict[int, list[int]] = {store_id: [] for store_id in store_cycle}
    for index in range(TOTAL_DEVICES):
        store_id = store_cycle[index % len(store_cycle)]
        imei_value = f"86{index:013d}" if index % 4 == 0 else None
        serial_value = f"SN-{index:06d}" if index % 3 == 0 else None
        payload = {
            "sku": f"SKU-{index:04d}",
            "name": f"Smartphone Serie {index:04d}",
            "quantity": 20,
            "unit_price": float(4500 + (index % 25) * 250),
            "imei": imei_value,
            "serial": serial_value,
            "marca": f"Marca {index % 10}",
            "modelo": f"Modelo {index % 15}",
            "color": ["Negro", "Plata", "Azul", "Rojo"][index % 4],
            "capacidad_gb": 64 + (index % 4) * 64,
            "estado_comercial": "nuevo" if index % 3 == 0 else "A",
            "proveedor": "Proveedor corporativo",
            "costo_unitario": float(3800 + (index % 25) * 180),
            "margen_porcentaje": float(15 + (index % 10)),
            "garantia_meses": 12,
            "lote": f"Lote-{index // 50 + 1:03d}",
            "fecha_compra": "2025-01-15",
        }
        response = client.post(
            f"/stores/{store_id}/devices",
            json=payload,
            headers=headers,
        )
        data = _ensure_ok(
            response,
            context=f"Alta de dispositivo {payload['sku']} en sucursal {store_id}",
        )
        device_id = int(data["id"])
        device_ids[store_id].append(device_id)
        if imei_value is None and serial_value is None:
            partial_candidates[store_id].append(device_id)
    stats = {
        "stores": {store_id: len(ids) for store_id, ids in device_ids.items()},
        "total_devices": sum(len(ids) for ids in device_ids.values()),
        "partial_ready": {
            store_id: len(ids) for store_id, ids in partial_candidates.items()
        },
    }
    return {
        "map": device_ids,
        "partial_candidates": partial_candidates,
        "stats": stats,
    }


def _register_movements(
    client: TestClient,
    headers: dict[str, str],
    device_map: dict[int, list[int]],
) -> int:
    total_movements = 0
    for store_id, devices in device_map.items():
        for device_id in devices:
            entry_payload = {
                "device_id": device_id,
                "movement_type": "entrada",
                "quantity": 3,
                "reason": "Ingreso masivo de stock",
            }
            response = client.post(
                f"/inventory/stores/{store_id}/movements",
                json=entry_payload,
                headers=headers | REASON_HEADER,
            )
            _ensure_ok(response, context="Movimiento de entrada")
            exit_payload = {
                "device_id": device_id,
                "movement_type": "salida",
                "quantity": 1,
                "reason": "Salida controlada",
            }
            response = client.post(
                f"/inventory/stores/{store_id}/movements",
                json=exit_payload,
                headers=headers | REASON_HEADER,
            )
            _ensure_ok(response, context="Movimiento de salida")
            total_movements += MOVEMENTS_PER_DEVICE
    return total_movements


def _create_purchase_orders(
    client: TestClient,
    headers: dict[str, str],
    device_map: dict[int, list[int]],
    suppliers: list[int],
) -> list[int]:
    order_ids: list[int] = []
    for store_id, device_ids in device_map.items():
        chunk = device_ids[:10]
        if not chunk:
            continue
        items = [
            {
                "device_id": device_id,
                "quantity_ordered": 5 + (idx % 3),
                "unit_cost": float(4200 + idx * 50),
            }
            for idx, device_id in enumerate(chunk)
        ]
        payload = {
            "store_id": store_id,
            "supplier": f"Proveedor {suppliers[store_id % len(suppliers)]}",
            "notes": "Orden automatizada del escenario",
            "items": items,
        }
        response = client.post(
            "/purchases/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context="Creación de orden de compra")
        order_id = int(data["id"])
        order_ids.append(order_id)
        receive_payload = {
            "items": [
                {"device_id": item["device_id"], "quantity": item["quantity_ordered"]}
                for item in items
            ]
        }
        response = client.post(
            f"/purchases/{order_id}/receive",
            json=receive_payload,
            headers=headers | REASON_HEADER,
        )
        _ensure_ok(response, context="Recepción de orden de compra")
    return order_ids


def _create_sales(
    client: TestClient,
    headers: dict[str, str],
    device_map: dict[int, list[int]],
    customers: list[int],
) -> list[int]:
    sale_ids: list[int] = []
    customer_cycle = customers or [None]
    for store_id, device_ids in device_map.items():
        sample_devices = device_ids[:5]
        if not sample_devices:
            continue
        payload = {
            "store_id": store_id,
            "customer_id": customer_cycle[store_id % len(customer_cycle)],
            "payment_method": "EFECTIVO",
            "discount_percent": 5,
            "notes": "Venta demostrativa",
            "items": [
                {"device_id": device_id, "quantity": 1 + (idx % 2)}
                for idx, device_id in enumerate(sample_devices)
            ],
        }
        response = client.post(
            "/sales/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context="Registro de venta")
        sale_ids.append(int(data["id"]))
    return sale_ids


def _register_sale_returns(
    client: TestClient,
    headers: dict[str, str],
    sale_ids: list[int],
    device_map: dict[int, list[int]],
) -> int:
    if not sale_ids:
        return 0
    processed = 0
    for sale_id, (store_id, devices) in zip(sale_ids, device_map.items()):
        if not devices:
            continue
        payload = {
            "sale_id": sale_id,
            "items": [
                {"device_id": devices[0], "quantity": 1, "reason": "Ajuste de escenario"}
            ],
        }
        response = client.post(
            "/sales/returns",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        _ensure_ok(response, context="Registro de devolución")
        processed += 1
    return processed


def _create_transfer_orders(
    client: TestClient,
    headers: dict[str, str],
    device_map: dict[int, list[int]],
    partial_candidates: dict[int, list[int]],
) -> list[int]:
    store_ids = list(device_map.keys())
    transfer_ids: list[int] = []
    if len(store_ids) < 2:
        return transfer_ids
    for index in range(len(store_ids)):
        origin = store_ids[index]
        destination = store_ids[(index + 1) % len(store_ids)]
        candidates = partial_candidates.get(origin, [])
        devices = candidates[:3]
        if not devices:
            continue
        payload = {
            "origin_store_id": origin,
            "destination_store_id": destination,
            "reason": "Balanceo de stock",
            "items": [
                {"device_id": device_id, "quantity": 2}
                for device_id in devices
            ],
        }
        response = client.post(
            "/transfers/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context="Creación de transferencia")
        transfer_id = int(data["id"])
        transfer_ids.append(transfer_id)
        dispatch_payload = {"reason": "Salida a ruta"}
        response = client.post(
            f"/transfers/{transfer_id}/dispatch",
            json=dispatch_payload,
            headers=headers | REASON_HEADER,
        )
        _ensure_ok(response, context="Despacho de transferencia")
        receive_payload = {"reason": "Recepción en destino"}
        response = client.post(
            f"/transfers/{transfer_id}/receive",
            json=receive_payload,
            headers=headers | REASON_HEADER,
        )
        _ensure_ok(response, context="Recepción de transferencia")
    return transfer_ids


def _create_repairs(
    client: TestClient,
    headers: dict[str, str],
    device_map: dict[int, list[int]],
    customers: list[int],
) -> list[int]:
    repair_ids: list[int] = []
    for store_id, devices in device_map.items():
        if not devices:
            continue
        payload = {
            "store_id": store_id,
            "customer_id": customers[store_id % len(customers)] if customers else None,
            "customer_name": "Cliente reparación",
            "technician_name": "Técnico certificado",
            "damage_type": "Pantalla rota",
            "device_description": "Smartphone en escenario de carga",
            "notes": "Orden creada por el script de rendimiento",
            "labor_cost": 950.0,
            "parts": [
                {"device_id": devices[0], "quantity": 1, "unit_cost": 500.0}
            ],
        }
        response = client.post(
            "/repairs/",
            json=payload,
            headers=headers | REASON_HEADER,
        )
        data = _ensure_ok(response, context="Creación de reparación")
        repair_ids.append(int(data["id"]))
    return repair_ids


def _trigger_sync_sessions(
    client: TestClient,
    headers: dict[str, str],
    store_ids: Iterable[int],
) -> list[int]:
    session_ids: list[int] = []
    for store_id in store_ids:
        payload = {"store_id": store_id}
        response = client.post("/sync/run", json=payload, headers=headers)
        data = _ensure_ok(response, context="Sesión de sincronización")
        session_ids.append(int(data["id"]))
    global_session = client.post("/sync/run", json={"store_id": None}, headers=headers)
    data = _ensure_ok(global_session, context="Sesión global")
    session_ids.append(int(data["id"]))
    return session_ids


def _generate_backup(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    payload = {"nota": "Respaldo del escenario de rendimiento"}
    response = client.post(
        "/backups/run",
        json=payload,
        headers=headers,
    )
    return _ensure_ok(response, context="Generación de respaldo")


def run_scenario() -> list[StageResult]:
    _reset_database()
    results: list[StageResult] = []
    with TestClient(app) as client:
        start = perf_counter()
        admin = _bootstrap_admin(client)
        admin_stage = StageResult(
            name="bootstrap_admin",
            duration_seconds=perf_counter() - start,
            details={"admin_id": admin["id"]},
        )
        admin_id = int(admin["id"])
        results.append(admin_stage)

        start = perf_counter()
        token = _login_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        results.append(
            StageResult(
                name="login_admin",
                duration_seconds=perf_counter() - start,
                details={"token_prefix": token[:12]},
            )
        )

        def timed_stage(
            name: str,
            func: Callable[..., T],
            *args: Any,
            **kwargs: Any,
        ) -> tuple[StageResult, T]:
            stage_start = perf_counter()
            payload = func(*args, **kwargs)
            if isinstance(payload, dict):
                details = cast(dict[str, Any], payload)
            else:
                details = {"result": payload}
            stage = StageResult(
                name=name,
                duration_seconds=perf_counter() - stage_start,
                details=details,
            )
            return stage, payload

        store_stage, store_payload = timed_stage(
            "create_stores", _create_stores, client, auth_headers
        )
        store_ids = [int(store_id) for store_id in cast(Iterable[int], store_payload)]
        results.append(store_stage)

        membership_stage, _ = timed_stage(
            "assign_memberships",
            _assign_store_memberships,
            client,
            auth_headers,
            store_ids,
            admin_id,
        )
        results.append(membership_stage)

        user_stage, _ = timed_stage("create_users", _create_users, client, auth_headers)
        results.append(user_stage)

        customer_stage, customer_payload = timed_stage(
            "create_customers", _create_customers, client, auth_headers
        )
        customer_ids = cast(list[int], customer_payload)
        results.append(customer_stage)

        supplier_stage, supplier_payload = timed_stage(
            "create_suppliers", _create_suppliers, client, auth_headers
        )
        supplier_ids = cast(list[int], supplier_payload)
        results.append(supplier_stage)

        device_stage, device_payload = timed_stage(
            "create_devices", _create_devices, client, auth_headers, store_ids
        )
        device_data = cast(dict[str, Any], device_payload)
        device_map = cast(dict[int, list[int]], device_data["map"])
        partial_candidates = cast(
            dict[int, list[int]], device_data["partial_candidates"]
        )
        device_stage.details = cast(dict[str, Any], device_data["stats"])
        results.append(device_stage)

        movement_stage_start = perf_counter()
        total_movements = _register_movements(client, auth_headers, device_map)
        results.append(
            StageResult(
                name="register_movements",
                duration_seconds=perf_counter() - movement_stage_start,
                details={"total_movements": total_movements},
            )
        )

        purchase_stage, _ = timed_stage(
            "create_purchases",
            _create_purchase_orders,
            client,
            auth_headers,
            device_map,
            supplier_ids,
        )
        results.append(purchase_stage)

        sale_stage, sale_ids = timed_stage(
            "create_sales",
            _create_sales,
            client,
            auth_headers,
            device_map,
            customer_ids,
        )
        results.append(sale_stage)

        sale_return_stage, processed_returns = timed_stage(
            "register_sale_returns",
            _register_sale_returns,
            client,
            auth_headers,
            cast(list[int], sale_ids),
            device_map,
        )
        sale_return_stage.details = {"processed_returns": processed_returns}
        results.append(sale_return_stage)

        transfer_stage, _ = timed_stage(
            "create_transfers",
            _create_transfer_orders,
            client,
            auth_headers,
            device_map,
            partial_candidates,
        )
        results.append(transfer_stage)

        repair_stage, _ = timed_stage(
            "create_repairs",
            _create_repairs,
            client,
            auth_headers,
            device_map,
            customer_ids,
        )
        results.append(repair_stage)

        sync_stage, _ = timed_stage(
            "trigger_sync_sessions",
            _trigger_sync_sessions,
            client,
            auth_headers,
            store_ids,
        )
        results.append(sync_stage)

        backup_stage, backup_payload = timed_stage(
            "generate_backup", _generate_backup, client, auth_headers
        )
        backup_stage.details = backup_payload
        results.append(backup_stage)
    return results


def main() -> None:
    results = run_scenario()
    print("ESCENARIO DE RENDIMIENTO — Softmobile 2025 v2.2.0")
    print(f"Base de datos: {DB_PATH}")
    print("Etapas ejecutadas:")
    for stage in results:
        print(
            f" - {stage.name}: {stage.duration_seconds:.2f}s | detalles: {stage.details}"
        )
    total_devices_created = next(
        (
            stage.details.get("total_devices")
            for stage in results
            if stage.name == "create_devices"
        ),
        None,
    )
    total_movements = next(
        (
            stage.details.get("total_movements")
            for stage in results
            if stage.name == "register_movements"
        ),
        None,
    )
    print(
        f"Resumen: dispositivos={total_devices_created}, movimientos={total_movements}"
    )


if __name__ == "__main__":
    main()
