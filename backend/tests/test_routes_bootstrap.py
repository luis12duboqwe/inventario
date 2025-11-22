from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.routers import auth as auth_router


def _build_test_app() -> FastAPI:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_router.router)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def _bootstrap_user(client: TestClient) -> dict:
    payload = {
        "username": "estado_user",
        "email": "estado_user@example.com",
        "password": "EstadoSeguro123",
        "roles": ["ADMIN"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201
    return payload


def test_login_and_refresh_cycle() -> None:
    """Genera tokens y verifica que el refresh entregue uno nuevo."""

    app = _build_test_app()

    with TestClient(app) as client:
        user_payload = _bootstrap_user(client)

        login_response = client.post(
            "/auth/login",
            json={
                "username": user_payload["username"],
                "password": user_payload["password"],
            },
        )

        assert login_response.status_code == 200
        first_token = login_response.json()["access_token"]
        refresh_cookie = login_response.cookies.get("softmobile_refresh_token")
        assert refresh_cookie

        refresh_response = client.post(
            "/auth/refresh",
            cookies={"softmobile_refresh_token": refresh_cookie},
        )

        assert refresh_response.status_code == 200
        refreshed_token = refresh_response.json()["access_token"]
        assert refreshed_token != first_token


def test_verify_access_token_endpoint() -> None:
    """Valida que /auth/verify responda para un token válido."""

    app = _build_test_app()

    with TestClient(app) as client:
        user_payload = _bootstrap_user(client)

        token_response = client.post(
            "/auth/token",
            data={
                "username": user_payload["username"],
                "password": user_payload["password"],
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        assert token_response.status_code == 200
        access_token = token_response.json()["access_token"]

        verification = client.post(
            "/auth/verify",
            json={"token": access_token},
        )

        assert verification.status_code == 200
        verification_body = verification.json()
        assert verification_body["is_valid"] is True
        assert verification_body["user"]["username"] == user_payload["username"]
