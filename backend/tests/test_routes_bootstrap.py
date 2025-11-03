from collections.abc import Iterator
import pytest

pytest.importorskip(
    "fastapi",
    reason="Las pruebas de autenticación requieren la librería fastapi instalada.",
)
pytest.importorskip(
    "fastapi_limiter",
    reason="Las pruebas de autenticación requieren fastapi-limiter para emular el rate limiter.",
)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.models import User
from backend.routes.auth import router as auth_router, verify_email
from backend.schemas.auth import VerifyEmailRequest
from fastapi_limiter import FastAPILimiter
from backend.core.settings import settings


class _DummyLimiter:
    async def evalsha(self, *args, **kwargs) -> int:
        return 0


def _reset_database() -> None:
    """Limpia las tablas antes de ejecutar los escenarios de autenticación."""

    init_db()
    with SessionLocal() as session:
        with session.begin():
            session.query(User).delete()


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)
    return app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    _reset_database()
    FastAPILimiter.redis = _DummyLimiter()

    async def _identifier(_request):
        return "test-client"

    FastAPILimiter.identifier = _identifier
    test_app = _create_test_app()
    with TestClient(test_app) as test_client:
        if settings.BOOTSTRAP_TOKEN:
            test_client.headers.update(
                {"X-Bootstrap-Token": settings.BOOTSTRAP_TOKEN}
            )
        yield test_client
    FastAPILimiter.redis = None
    FastAPILimiter.identifier = None


def test_auth_status_route_returns_success(client: TestClient) -> None:
    """La ruta de estado de autenticación debe responder con el mensaje esperado."""

    register_payload = {
        "username": "estado_user",
        "email": "estado_user@example.com",
        "password": "estado_seguro",
    }
    register_response = client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "username": register_payload["username"],
            "password": register_payload["password"],
        },
    )
    assert login_response.status_code == 200
    token_payload = login_response.json()

    response = client.get(
        "/auth/status",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Autenticación lista y conectada a SQLite ✅"}


def test_register_login_and_verify_flow(client: TestClient) -> None:
    """Permite registrar un usuario, iniciar sesión y validar el token emitido."""

    register_payload = {
        "username": "soporte",
        "email": "soporte@example.com",
        "password": "contraseña_segura",
    }
    register_response = client.post("/auth/register", json=register_payload)

    assert register_response.status_code == 200
    registered = register_response.json()
    assert registered["username"] == register_payload["username"]
    assert registered["email"] == register_payload["email"]

    login_response = client.post(
        "/auth/login",
        json={
            "username": register_payload["username"],
            "password": register_payload["password"],
        },
    )

    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert "access_token" in token_payload

    verify_response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )

    assert verify_response.status_code == 200
    verification = verify_response.json()
    assert verification["valid"] is True
    assert verification["user"]["username"] == register_payload["username"]


def test_register_without_explicit_email_reuses_username(client: TestClient) -> None:
    """Si no se envía el correo, el nombre de usuario debe emplearse como email."""

    payload = {
        "username": "softmobile1@gmail.com",
        "password": "clave_segura",
    }
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["username"]


def test_register_repeated_user_is_rejected(client: TestClient) -> None:
    """Registrar dos veces el mismo usuario debe devolver un error 400."""

    payload = {
        "username": "soporte",
        "email": "soporte@example.com",
        "password": "contraseña_segura",
    }

    first_response = client.post("/auth/register", json=payload)
    assert first_response.status_code == 200

    conflict_response = client.post("/auth/register", json=payload)

    assert conflict_response.status_code == 400
    assert conflict_response.json()["detail"] == "El nombre de usuario o correo ya están registrados."


def test_refresh_reset_and_verify_flow(client: TestClient) -> None:
    """Cubre la renovación de tokens, restablecimiento y verificación de correo."""

    register_payload = {
        "username": "refresh_user",
        "email": "refresh_user@example.com",
        "password": "clave_inicial_segura",
    }
    register_response = client.post("/auth/register", json=register_payload)

    assert register_response.status_code == 200
    registered = register_response.json()
    assert registered["username"] == register_payload["username"]
    assert registered["is_verified"] is False
    verification_token = registered["verification_token"]

    login_response = client.post(
        "/auth/login",
        json={
            "username": register_payload["username"],
            "password": register_payload["password"],
        },
    )

    assert login_response.status_code == 200
    login_tokens = login_response.json()
    assert "access_token" in login_tokens
    assert "refresh_token" in login_tokens

    refresh_response = client.post(
        "/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]}
    )

    assert refresh_response.status_code == 200
    refreshed_tokens = refresh_response.json()
    assert refreshed_tokens["access_token"]
    assert refreshed_tokens["refresh_token"] != login_tokens["refresh_token"]

    forgot_response = client.post(
        "/auth/forgot", json={"email": register_payload["email"]}
    )

    assert forgot_response.status_code == 202
    reset_token = forgot_response.json()["reset_token"]
    assert isinstance(reset_token, str) and reset_token

    new_password = "clave_nueva_segura"
    reset_response = client.post(
        "/auth/reset",
        json={"token": reset_token, "new_password": new_password},
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Contraseña actualizada correctamente."

    relogin_response = client.post(
        "/auth/login",
        json={
            "username": register_payload["username"],
            "password": new_password,
        },
    )

    assert relogin_response.status_code == 200
    relogin_tokens = relogin_response.json()
    assert "access_token" in relogin_tokens

    verify_response = client.post(
        "/auth/verify", json={"token": verification_token}
    )

    assert verify_response.status_code == 200

    with SessionLocal() as session:
        verify_email(VerifyEmailRequest(token=verification_token), db=session)
        user = session.query(User).filter(User.email == register_payload["email"]).one()
        assert user.is_verified is True

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {relogin_tokens['access_token']}"},
    )

    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["username"] == register_payload["username"]
    assert me_payload["is_verified"] is True


def test_legacy_token_endpoint_returns_token_pair(client: TestClient) -> None:
    """El endpoint histórico debe seguir devolviendo tokens de acceso y refresco."""

    payload = {
        "username": "legacy_user",
        "email": "legacy_user@example.com",
        "password": "legacy_password",
    }
    register_response = client.post("/auth/register", json=payload)

    assert register_response.status_code == 200

    token_response = client.post(
        "/auth/token",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )

    assert token_response.status_code == 200
    token_payload = token_response.json()
    assert token_payload["token_type"] == "bearer"
    assert "access_token" in token_payload
    assert "refresh_token" in token_payload


__all__ = [
    "test_auth_status_route_returns_success",
    "test_register_login_and_verify_flow",
    "test_register_without_explicit_email_reuses_username",
    "test_register_repeated_user_is_rejected",
    "test_refresh_reset_and_verify_flow",
    "test_legacy_token_endpoint_returns_token_pair",
]
