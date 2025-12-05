from fastapi import status
import pyotp
from fastapi_limiter import FastAPILimiter

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN, OPERADOR
from backend.app.models import Store, Device


def _bootstrap_admin(client):
    payload = {
        "username": "seguridad_admin",
        "password": "Seguridad123*",
        "full_name": "Seguridad Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return payload


def test_bootstrap_status_reports_availability(client):
    initial_status = client.get("/auth/bootstrap/status")
    assert initial_status.status_code == status.HTTP_200_OK
    initial_payload = initial_status.json()
    assert initial_payload["disponible"] is True
    assert initial_payload["usuarios_registrados"] == 0

    creation_payload = {
        "username": "inicial@example.com",
        "password": "Inicial123$",
        "full_name": "Cuenta Inicial",
        "roles": [],
    }
    created = client.post("/auth/bootstrap", json=creation_payload)
    assert created.status_code == status.HTTP_201_CREATED

    final_status = client.get("/auth/bootstrap/status")
    assert final_status.status_code == status.HTTP_200_OK
    final_payload = final_status.json()
    assert final_payload["disponible"] is False
    assert final_payload["usuarios_registrados"] == 1


def test_totp_flow_and_session_revocation(client):
    settings.enable_2fa = True
    payload = _bootstrap_admin(client)

    login_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token_data = login_response.json()
    access_token = token_data["access_token"]

    security_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Reason": "Configurar 2FA",
        "X-Reauth-Password": payload["password"],
    }

    setup_response = client.post(
        "/security/2fa/setup", headers=security_headers)
    assert setup_response.status_code == status.HTTP_201_CREATED
    secret = setup_response.json()["secret"]
    totp = pyotp.TOTP(secret)

    activate_response = client.post(
        "/security/2fa/activate",
        json={"code": totp.now()},
        headers=security_headers,
    )
    assert activate_response.status_code == status.HTTP_200_OK
    assert activate_response.json()["is_active"] is True

    bad_login = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert bad_login.status_code == status.HTTP_401_UNAUTHORIZED

    otp_code = totp.now()
    good_login = client.post(
        "/auth/token",
        data={
            "username": payload["username"],
            "password": payload["password"],
            "otp": otp_code,
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert good_login.status_code == status.HTTP_200_OK
    good_data = good_login.json()
    assert "session_id" in good_data
    session_id = good_data["session_id"]
    auth_headers = {
        "Authorization": f"Bearer {good_data['access_token']}",
        "X-Reason": "Revocacion",
        "X-Reauth-Password": payload["password"],
        "X-Reauth-OTP": otp_code,
    }

    sessions_list = client.get("/security/sessions", headers=auth_headers)
    assert sessions_list.status_code == status.HTTP_200_OK
    assert any(session["id"] == session_id for session in sessions_list.json())

    revoke_response = client.post(
        f"/security/sessions/{session_id}/revoke",
        json={"reason": "Cierre manual"},
        headers=auth_headers,
    )
    assert revoke_response.status_code == status.HTTP_200_OK
    assert revoke_response.json()["revoked_at"] is not None

    me_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {good_data['access_token']}"})
    assert me_response.status_code == status.HTTP_401_UNAUTHORIZED

    settings.enable_2fa = False


def test_login_lockout_and_password_reset_flow(client):
    original_max = settings.max_failed_login_attempts
    original_lock = settings.account_lock_minutes
    original_testing = settings.testing_mode
    try:
        settings.max_failed_login_attempts = 3
        settings.account_lock_minutes = 30
        settings.testing_mode = True
        payload = _bootstrap_admin(client)

        for _ in range(settings.max_failed_login_attempts):
            response = client.post(
                "/auth/token",
                data={"username": payload["username"], "password": "Falla123"},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        locked_response = client.post(
            "/auth/token",
            data={"username": payload["username"],
                  "password": payload["password"]},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert locked_response.status_code == status.HTTP_403_FORBIDDEN

        reset_request = client.post(
            "/auth/password/request",
            json={"username": payload["username"]},
        )
        assert reset_request.status_code == status.HTTP_202_ACCEPTED
        reset_token = reset_request.json().get("reset_token")
        assert reset_token

        new_password = "ReinicioSeguro123$"
        reset_response = client.post(
            "/auth/password/reset",
            json={"token": reset_token, "new_password": new_password},
        )
        assert reset_response.status_code == status.HTTP_200_OK

        success_login = client.post(
            "/auth/token",
            data={"username": payload["username"], "password": new_password},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert success_login.status_code == status.HTTP_200_OK
        # Opcionalmente verificamos que se pueda acceder al perfil,
        # lo que implica que el usuario ya no está bloqueado ni con intentos activos
        me = client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {success_login.json()['access_token']}"},
        )
        assert me.status_code == status.HTTP_200_OK
    finally:
        settings.max_failed_login_attempts = original_max
        settings.account_lock_minutes = original_lock
        settings.testing_mode = original_testing


def test_session_cookie_login_allows_me_endpoint(client):
    payload = _bootstrap_admin(client)

    session_login = client.post(
        "/auth/session",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert session_login.status_code == status.HTTP_200_OK
    cookie_name = settings.session_cookie_name
    assert cookie_name in session_login.cookies
    session_cookie = session_login.cookies.get(cookie_name)
    assert session_cookie

    me_response = client.get("/auth/me")
    assert me_response.status_code == status.HTTP_200_OK
    assert me_response.json()["username"] == payload["username"]


def test_token_verification_endpoint_reports_status_changes(client):
    payload = {
        "username": "verificador@example.com",
        "password": "Verifica123$",
        "full_name": "Admin Verificador",
        "roles": [ADMIN],
    }
    created = client.post("/auth/bootstrap", json=payload)
    assert created.status_code == status.HTTP_201_CREATED

    login_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token_data = login_response.json()
    access_token = token_data["access_token"]
    session_id = token_data["session_id"]

    verification = client.post("/auth/verify", json={"token": access_token})
    assert verification.status_code == status.HTTP_200_OK
    verification_payload = verification.json()
    assert verification_payload["is_valid"] is True
    assert verification_payload["session_id"] == session_id
    assert verification_payload["user"]["username"] == payload["username"]

    revoke_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Reason": "Cerrar sesion activa",
    }
    revoke_response = client.post(
        f"/security/sessions/{session_id}/revoke",
        json={"reason": "Revocacion solicitada"},
        headers=revoke_headers,
    )
    assert revoke_response.status_code == status.HTTP_200_OK

    revoked_verification = client.post(
        "/auth/verify", json={"token": access_token})
    assert revoked_verification.status_code == status.HTTP_200_OK
    revoked_payload = revoked_verification.json()
    assert revoked_payload["is_valid"] is False

    tampered_token = access_token + "invalido"
    invalid_verification = client.post(
        "/auth/verify", json={"token": tampered_token})
    assert invalid_verification.status_code == status.HTTP_200_OK
    assert invalid_verification.json()["is_valid"] is False


def test_module_permissions_block_operator_edit_without_permission(client, db_session):
    admin_payload = _bootstrap_admin(client)
    login_response = client.post(
        "/auth/token",
        data={"username": admin_payload["username"],
              "password": admin_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    admin_token = login_response.json()["access_token"]

    # Create store and device
    store = Store(name="Test Store Security", code="SEC-001", status="activa")
    db_session.add(store)
    db_session.flush()
    store_id = store.id

    device = Device(
        store_id=store_id,
        sku="SEC-DEV-001",
        name="Security Device",
        quantity=10,
        unit_price=100.0,
        costo_unitario=50.0,
        estado="disponible"
    )
    db_session.add(device)
    db_session.flush()
    device_id = device.id
    db_session.commit()

    operator_payload = {
        "username": "operador@example.com",
        "password": "Operador123$",
        "full_name": "Usuario Operador",
        "roles": [OPERADOR],
    }
    create_response = client.post(
        "/users",
        json=operator_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    permission = (
        db_session.query(models.Permission)
        .filter(
            models.Permission.role_name == OPERADOR,
            models.Permission.module == "inventario",
        )
        .one()
    )
    permission.can_edit = False
    permission.can_delete = False
    db_session.commit()
    db_session.refresh(permission)
    assert permission.can_edit is False

    operator_login = client.post(
        "/auth/token",
        data={"username": operator_payload["username"],
              "password": operator_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert operator_login.status_code == status.HTTP_200_OK
    operator_token = operator_login.json()["access_token"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 1,
        "comentario": "Ajuste inventario",
        "sucursal_origen_id": None,
    }
    denied_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers={
            "Authorization": f"Bearer {operator_token}",
            "X-Reason": "Ajuste inventario",
        },
    )
    assert denied_response.status_code == status.HTTP_403_FORBIDDEN


def test_rate_limiter_initializes_within_app(client):
    assert FastAPILimiter.redis is not None
    assert FastAPILimiter.identifier is not None
