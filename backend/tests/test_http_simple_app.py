"""Pruebas unitarias para el microframework HTTP simplificado."""

from __future__ import annotations

from http import HTTPStatus

import pytest

from backend.app.http import Request, Response, Router, SimpleApp
from backend.schemas.audit import AuditStatusResponse


@pytest.fixture()
def simple_app() -> SimpleApp:
    """Crea una instancia fresca de ``SimpleApp`` para cada prueba."""
    return SimpleApp()


def test_simple_app_responde_a_peticion_get(simple_app: SimpleApp) -> None:
    """Verifica que una ruta registrada procese solicitudes GET exitosamente."""

    @simple_app.get("/estado")
    def estado(_: Request) -> dict[str, str]:
        return {"estado": "operativo"}

    respuesta = simple_app.handle_request("GET", "/estado")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"estado": "operativo"}


def test_simple_app_interpola_parametros_de_ruta(simple_app: SimpleApp) -> None:
    """Confirma que los parámetros en la URL se entregan al manejador."""

    @simple_app.get("/dispositivos/{imei}")
    def obtener_dispositivo(_: Request, imei: str) -> dict[str, str]:
        return {"imei": imei}

    respuesta = simple_app.handle_request("GET", "/dispositivos/123456789012345")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"imei": "123456789012345"}


def test_simple_app_devuelve_405_y_cabecera_allow(simple_app: SimpleApp) -> None:
    """Garantiza que se devuelva 405 y la cabecera Allow cuando el método no coincide."""

    @simple_app.post("/sincronizaciones")
    def crear_sincronizacion(_: Request) -> dict[str, str]:
        return {"resultado": "creada"}

    respuesta = simple_app.handle_request("GET", "/sincronizaciones")

    assert respuesta.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert respuesta.headers == {"Allow": "POST"}
    assert respuesta.json()["error"]["code"] == "method_not_allowed"


def test_simple_app_devuelve_404_para_rutas_desconocidas(simple_app: SimpleApp) -> None:
    """Confirma que las rutas inexistentes respondan con 404 estándar."""

    respuesta = simple_app.handle_request("GET", "/no-existe")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json() == {
        "error": {"code": "not_found", "message": "Endpoint not found"},
    }


def test_simple_app_aplica_manejadores_de_excepcion(simple_app: SimpleApp) -> None:
    """Verifica que los manejadores de excepción registrados transformen la respuesta."""

    @simple_app.get("/reportes")
    def listar_reportes(_: Request) -> None:
        raise ValueError("error controlado")

    @simple_app.exception_handler(ValueError)
    def manejar_value_error(_: Request, exc: ValueError) -> Response:
        return Response(
            status_code=int(HTTPStatus.BAD_REQUEST),
            content={"detalle": str(exc)},
            headers={"X-Handled": "true"},
        )

    respuesta = simple_app.handle_request("GET", "/reportes")

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.headers["X-Handled"] == "true"
    assert respuesta.json() == {"detalle": "error controlado"}


def test_simple_app_admite_routers_con_prefijo(simple_app: SimpleApp) -> None:
    """Valida que los routers incluidos respeten el prefijo configurado."""

    router = Router(prefix="/v1")

    @router.get("/auditoria", response_model=AuditStatusResponse)
    def obtener_auditoria(_: Request) -> dict[str, str]:
        return {"estatus": "registrada"}

    simple_app.include_router(router)

    respuesta = simple_app.handle_request("GET", "/v1/auditoria")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"estatus": "registrada"}
