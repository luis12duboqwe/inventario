"""Pruebas para los logs y errores del sistema."""
from datetime import datetime, timedelta

from fastapi import status

from backend.app.core.roles import ADMIN, OPERADOR
from backend.app import crud, schemas, security


def _bootstrap_admin(client):
    payload = {
        "username": "log_admin",
        "password": "Logs123*",
        "full_name": "Supervisora de Logs",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), payload


def _login(client, username: str, password: str):
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


def test_system_logs_filters_and_levels(client, db_session):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    crud._log_action(
        db_session,
        action="sale_created",
        entity_type="sale",
        entity_id="venta-1",
        performed_by_id=admin["id"],
        details="Venta completada sin incidentes",
    )
    crud._log_action(
        db_session,
        action="purchase_order_created",
        entity_type="purchase_order",
        entity_id="compra-1",
        performed_by_id=admin["id"],
        details="Orden de compra generada para proveedor",
    )
    crud._log_action(
        db_session,
        action="inventory_adjustment_performed",
        entity_type="inventory_adjustment",
        entity_id="inv-ajuste-1",
        performed_by_id=admin["id"],
        details="Ajuste manual de inventario por reconteo",
    )
    crud._log_action(
        db_session,
        action="inventory_warning",
        entity_type="inventory",
        entity_id="inv-alerta-1",
        performed_by_id=admin["id"],
        details="Ajuste manual por conteo preventivo",
    )
    crud._log_action(
        db_session,
        action="low_stock_alert",
        entity_type="inventory",
        entity_id="inv-critico-1",
        performed_by_id=admin["id"],
        details="Stock bajo detectado en sucursal",
    )
    crud._log_action(
        db_session,
        action="user_password_reset",
        entity_type="user",
        entity_id=str(admin["id"]),
        performed_by_id=admin["id"],
        details="Actualización de credenciales por política corporativa",
    )
    crud.register_system_error(
        db_session,
        mensaje="Fallo al generar factura",
        stack_trace="Traceback: error al renderizar PDF",
        modulo="ventas",
        usuario=admin["username"],
        ip_origen="127.0.0.1",
    )
    db_session.commit()

    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    info_logs = client.get("/logs/sistema", params={"nivel": "info"}, headers=auth_headers)
    assert info_logs.status_code == status.HTTP_200_OK
    info_payload = info_logs.json()
    assert any(entry["accion"] == "sale_created" for entry in info_payload)

    compras_logs = client.get(
        "/logs/sistema",
        params={"modulo": "compras"},
        headers=auth_headers,
    )
    assert compras_logs.status_code == status.HTTP_200_OK
    assert any(entry["accion"] == "purchase_order_created" for entry in compras_logs.json())

    warning_logs = client.get(
        "/logs/sistema",
        params={"nivel": "warning", "modulo": "inventario"},
        headers=auth_headers,
    )
    assert warning_logs.status_code == status.HTTP_200_OK
    warning_payload = warning_logs.json()
    assert all(entry["nivel"] == "warning" for entry in warning_payload)

    ajustes_logs = client.get(
        "/logs/sistema",
        params={"modulo": "ajustes", "nivel": "warning"},
        headers=auth_headers,
    )
    assert ajustes_logs.status_code == status.HTTP_200_OK
    ajustes_payload = ajustes_logs.json()
    assert any(entry["accion"] == "inventory_adjustment_performed" for entry in ajustes_payload)

    critical_logs = client.get(
        "/logs/sistema",
        params={"nivel": "critical"},
        headers=auth_headers,
    )
    assert critical_logs.status_code == status.HTTP_200_OK
    critical_payload = critical_logs.json()
    assert any(entry["nivel"] == "critical" for entry in critical_payload)

    usuarios_logs = client.get(
        "/logs/sistema",
        params={"modulo": "usuarios"},
        headers=auth_headers,
    )
    assert usuarios_logs.status_code == status.HTTP_200_OK
    assert any(entry["accion"] == "user_password_reset" for entry in usuarios_logs.json())

    user_logs = client.get(
        "/logs/sistema",
        params={"usuario": admin["username"], "modulo": "ventas"},
        headers=auth_headers,
    )
    assert user_logs.status_code == status.HTTP_200_OK
    assert user_logs.json()
    assert all(entry["usuario"] == admin["username"] for entry in user_logs.json())

    future_from = (datetime.utcnow() + timedelta(days=1)).isoformat()
    empty_logs = client.get(
        "/logs/sistema",
        params={"fecha_desde": future_from},
        headers=auth_headers,
    )
    assert empty_logs.status_code == status.HTTP_200_OK
    assert empty_logs.json() == []

    error_level_logs = client.get(
        "/logs/sistema",
        params={"nivel": "error"},
        headers=auth_headers,
    )
    assert error_level_logs.status_code == status.HTTP_200_OK
    assert any(
        entry["accion"] == "system_error" and entry["ip_origen"] == "127.0.0.1"
        for entry in error_level_logs.json()
    )

    error_logs = client.get(
        "/logs/errores",
        params={"modulo": "ventas"},
        headers=auth_headers,
    )
    assert error_logs.status_code == status.HTTP_200_OK
    error_payload = error_logs.json()
    assert any(entry["mensaje"] == "Fallo al generar factura" for entry in error_payload)
    assert all(entry["modulo"] == "ventas" for entry in error_payload)


def test_system_logs_rejects_non_admin_access(client, db_session):
    _admin, credentials = _bootstrap_admin(client)
    _login(client, credentials["username"], credentials["password"])

    operator_payload = schemas.UserCreate(
        username="operadora.logs@example.com",
        password="Operadora123*",
        full_name="Operadora Logs",
        roles=[OPERADOR],
    )
    crud.create_user(
        db_session,
        operator_payload,
        password_hash=security.hash_password(operator_payload.password),
        role_names=operator_payload.roles,
    )

    unauthenticated = client.get("/logs/sistema")
    assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED

    operator_tokens = _login(
        client,
        operator_payload.username,
        operator_payload.password,
    )
    forbidden_response = client.get(
        "/logs/sistema",
        headers={"Authorization": f"Bearer {operator_tokens['access_token']}"},
    )
    assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN
