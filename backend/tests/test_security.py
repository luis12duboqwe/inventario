from fastapi import status
import pyotp

from backend.app.config import settings
from backend.app.core.roles import ADMIN


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


def test_totp_flow_and_session_revocation(client):
    settings.enable_2fa = True
    payload = _bootstrap_admin(client)

    login_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token_data = login_response.json()
    access_token = token_data["access_token"]

    security_headers = {"Authorization": f"Bearer {access_token}", "X-Reason": "Configurar 2FA"}

    setup_response = client.post("/security/2fa/setup", headers=security_headers)
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
        data={"username": payload["username"], "password": payload["password"]},
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
    auth_headers = {"Authorization": f"Bearer {good_data['access_token']}", "X-Reason": "Revocacion"}

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

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {good_data['access_token']}"})
    assert me_response.status_code == status.HTTP_401_UNAUTHORIZED

    settings.enable_2fa = False
