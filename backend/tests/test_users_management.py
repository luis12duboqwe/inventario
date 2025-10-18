from fastapi import status


def _bootstrap_admin(client):
    payload = {
        "username": "admin_usuarios",
        "password": "AdminUsuarios123*",
        "full_name": "Admin Usuarios",
        "roles": ["ADMIN"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return payload, token_response.json()["access_token"]


def test_user_filters_dashboard_and_export(client):
    admin_payload, admin_token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    create_payload = {
        "username": "operador_demo@softmobile.test",
        "password": "OperadorSeguro123*",
        "full_name": "Operador Demo",
        "roles": ["OPERADOR"],
    }
    create_response = client.post("/users", json=create_payload, headers=auth_headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["id"]

    # Desactivar temporalmente al usuario
    deactivate_headers = {**auth_headers, "X-Reason": "Suspension temporal"}
    deactivate_response = client.patch(
        f"/users/{user_id}",
        json={"is_active": False},
        headers=deactivate_headers,
    )
    assert deactivate_response.status_code == status.HTTP_200_OK
    assert deactivate_response.json()["is_active"] is False

    # Listar filtrando por estado inactivo
    list_response = client.get(
        "/users",
        headers=auth_headers,
        params={"status": "inactive"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    users = list_response.json()
    assert any(item["id"] == user_id for item in users)

    # Actualizar datos del usuario, incluyendo contraseña
    update_headers = {**auth_headers, "X-Reason": "Actualizacion de perfil"}
    update_payload = {
        "full_name": "Operador Actualizado",
        "telefono": "+52 55 1234 5678",
        "password": "ClaveNuevaSegura456*",
        "store_id": None,
    }
    update_response = client.put(
        f"/users/{user_id}",
        json=update_payload,
        headers=update_headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_user = update_response.json()
    assert updated_user["full_name"] == "Operador Actualizado"
    assert updated_user.get("telefono") == "+52 55 1234 5678"

    # Verificar que la nueva contraseña permita el inicio de sesión
    token_response = client.post(
        "/auth/token",
        data={"username": create_payload["username"], "password": update_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK

    # Consultar el dashboard de usuarios
    dashboard_response = client.get("/users/dashboard", headers=auth_headers)
    assert dashboard_response.status_code == status.HTTP_200_OK
    dashboard = dashboard_response.json()
    assert "totals" in dashboard
    assert "recent_activity" in dashboard
    assert "active_sessions" in dashboard
    assert "audit_alerts" in dashboard

    # Exportar a PDF
    pdf_response = client.get(
        "/users/export",
        headers={**auth_headers, "X-Reason": "Auditoria usuarios"},
        params={"format": "pdf"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    # Exportar a Excel
    xlsx_response = client.get(
        "/users/export",
        headers={**auth_headers, "X-Reason": "Auditoria usuarios"},
        params={"format": "xlsx"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in xlsx_response.headers["content-type"]


def test_role_permissions_update(client):
    _, admin_token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # Crear un usuario operador para garantizar la existencia del rol y sus permisos base
    operator_payload = {
        "username": "perm_operator@softmobile.test",
        "password": "PermisoSeguro123*",
        "full_name": "Operador Permisos",
        "roles": ["OPERADOR"],
    }
    create_operator = client.post("/users", json=operator_payload, headers=auth_headers)
    assert create_operator.status_code == status.HTTP_201_CREATED

    permissions_response = client.get("/users/permissions", headers=auth_headers)
    assert permissions_response.status_code == status.HTTP_200_OK
    permissions_data = permissions_response.json()
    assert any(item["role"] == "OPERADOR" for item in permissions_data)

    update_headers = {**auth_headers, "X-Reason": "Revision de permisos"}
    update_payload = {
        "permissions": [
            {
                "module": "inventario",
                "can_view": True,
                "can_edit": False,
                "can_delete": False,
            }
        ]
    }
    update_response = client.put(
        "/users/roles/OPERADOR/permissions",
        json=update_payload,
        headers=update_headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_matrix = update_response.json()
    assert updated_matrix["role"] == "OPERADOR"
    inventario_permission = next(
        perm for perm in updated_matrix["permissions"] if perm["module"] == "inventario"
    )
    assert inventario_permission == {
        "module": "inventario",
        "can_view": True,
        "can_edit": False,
        "can_delete": False,
    }

    # Confirmar que la actualización persiste
    confirm_response = client.get(
        "/users/permissions",
        headers=auth_headers,
        params={"role": "OPERADOR"},
    )
    assert confirm_response.status_code == status.HTTP_200_OK
    confirm_matrix = confirm_response.json()[0]
    confirm_permission = next(
        perm for perm in confirm_matrix["permissions"] if perm["module"] == "inventario"
    )
    assert confirm_permission == inventario_permission


def test_update_user_roles_requires_reason(client):
    _, admin_token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    create_payload = {
        "username": "cambios_roles@softmobile.test",
        "password": "CambioRoles123*",
        "full_name": "Cambios Roles",
        "roles": ["OPERADOR"],
    }
    create_response = client.post("/users", json=create_payload, headers=auth_headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["id"]

    missing_reason = client.put(
        f"/users/{user_id}/roles",
        json={"roles": ["GERENTE"]},
        headers=auth_headers,
    )
    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST

    update_headers = {**auth_headers, "X-Reason": "Reasignacion de rol"}
    update_response = client.put(
        f"/users/{user_id}/roles",
        json={"roles": ["GERENTE"]},
        headers=update_headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_user = update_response.json()
    assert updated_user["rol"] == "GERENTE"
    assert sorted(role["name"] for role in updated_user["roles"]) == ["GERENTE"]
