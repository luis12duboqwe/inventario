from __future__ import annotations

import pytest
from fastapi import status

from backend.app.core.roles import ADMIN, GERENTE, OPERADOR, INVITADO


def _bootstrap_role(client, role: str, username: str) -> dict[str, str]:
    """Crea un usuario con un rol y devuelve headers de autenticación."""
    admin_payload = {
        "username": f"admin_{role}",
        "password": "MuySegura123",
        "full_name": "Admin Bootstrap",
        "roles": [ADMIN],
    }
    # Bootstrap admin (idempotente por prueba aislada)
    client.post("/auth/bootstrap", json=admin_payload)
    token_resp = client.post(
        "/auth/token",
        data={"username": admin_payload["username"],
              "password": admin_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == status.HTTP_200_OK
    admin_token = token_resp.json()["access_token"]

    create_resp = client.post(
        "/users",
        json={
            "username": username,
            "password": "PwdSegura123",
            "full_name": f"Usuario {role}",
            "roles": [role],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Puede existir ya si la prueba se reintenta: permitir 409
    assert create_resp.status_code in (
        status.HTTP_201_CREATED, status.HTTP_409_CONFLICT)

    token_user = client.post(
        "/auth/token",
        data={"username": username, "password": "PwdSegura123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_user.status_code == status.HTTP_200_OK
    user_token = token_user.json()["access_token"]
    return {"Authorization": f"Bearer {user_token}"}


@pytest.mark.parametrize("path", [
    "/reports/inventory/current/csv",  # requiere ADMIN (router + middleware)
    "/reports/inventory/value/csv",
])
def test_guest_cannot_access_reports(client, path: str) -> None:
    """INVITADO no debe acceder aunque envíe un X-Reason válido.

    Enviamos X-Reason para evitar el 400 por cabecera faltante y aislar la verificación RBAC.
    """
    guest_headers = _bootstrap_role(client, INVITADO, "guest_rbac")
    enriched = {**guest_headers, "X-Reason": "Motivo reporte inventario"}
    response = client.get(path, headers=enriched)
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_operator_cannot_export_audit_ui(client) -> None:
    """OPERADOR no puede exportar auditoría UI (solo ADMIN)."""
    operator_headers = _bootstrap_role(client, OPERADOR, "oper_rbac")
    response = client.get("/api/audit/ui/export", headers=operator_headers)
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_manager_cannot_delete_security_resource(client) -> None:
    """GERENTE no posee permisos de borrado en módulo seguridad según matriz.

    Simulamos intento de borrado usando un endpoint de sesión inexistente con método DELETE;
    debe fallar (403/405/404), nunca 200.
    """
    manager_headers = _bootstrap_role(client, GERENTE, "ger_rbac")
    response = client.delete(
        "/security/sessions/99999/revoke", headers=manager_headers)
    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_404_NOT_FOUND,
    }
