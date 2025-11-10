from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.app.config import settings


def _bootstrap_admin(client) -> dict[str, str]:
    payload = {
        "email": "admin@example.com",
        "password": "VerySecure123",
        "full_name": "Administrador",
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201
    token_response = client.post(
        "/auth/token",
        data={"username": payload["email"], "password": payload["password"]},
    )
    token_response.raise_for_status()
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _authorized_reason_headers(headers: dict[str, str]) -> dict[str, str]:
    merged = dict(headers)
    merged["X-Reason"] = "Actualización configuración"
    return merged


def _write_yaml(path: Path, name: str, content: str) -> None:
    target = path / name
    target.write_text(content.strip() + "\n", encoding="utf-8")


def test_configuration_rate_and_parameter_crud(client) -> None:
    headers = _bootstrap_admin(client)
    reason_headers = _authorized_reason_headers(headers)

    rate_payload: dict[str, Any] = {
        "slug": "iva_general",
        "name": "IVA general",
        "description": "Impuesto al valor agregado estándar.",
        "value": "0.1600",
        "unit": "porcentaje",
        "currency": "MXN",
        "metadata": {"autoridad": "SAT"},
    }

    create_rate = client.post(
        "/configuration/rates",
        json=rate_payload,
        headers=reason_headers,
    )
    assert create_rate.status_code == 201
    rate_id = create_rate.json()["id"]

    update_rate = client.put(
        f"/configuration/rates/{rate_id}",
        json={"value": "0.1700"},
        headers=reason_headers,
    )
    assert update_rate.status_code == 200
    assert Decimal(str(update_rate.json()["value"])) == Decimal("0.1700")

    param_payload: dict[str, Any] = {
        "key": "sar_habilitado",
        "name": "SAR habilitado",
        "value_type": "boolean",
        "value": True,
        "metadata": {"contexto": "sar"},
    }

    create_param = client.post(
        "/configuration/parameters",
        json=param_payload,
        headers=reason_headers,
    )
    assert create_param.status_code == 201
    parameter_id = create_param.json()["id"]

    update_param = client.put(
        f"/configuration/parameters/{parameter_id}",
        json={"value_type": "integer"},
        headers=reason_headers,
    )
    assert update_param.status_code == 200
    assert update_param.json()["value_type"] == "integer"
    assert update_param.json()["value"] == 1

    overview = client.get("/configuration/overview", headers=headers)
    assert overview.status_code == 200
    data = overview.json()
    assert any(rate["slug"] == "iva_general" for rate in data["rates"])
    assert any(param["key"] == "sar_habilitado" for param in data["parameters"])


def test_configuration_sync_from_yaml(client, tmp_path) -> None:
    headers = _bootstrap_admin(client)
    reason_headers = _authorized_reason_headers(headers)

    original_dir = settings.config_sync_directory
    try:
        settings.config_sync_directory = str(tmp_path)
        _write_yaml(
            tmp_path,
            "rates.yaml",
            """
            rates:
              - slug: tasa_corporativa
                name: Tasa corporativa
                value: 0.1500
                unit: porcentaje
                currency: MXN
                metadata:
                  autoridad: SAT
            """,
        )
        _write_yaml(
            tmp_path,
            "xml_templates.yml",
            """
            xml_templates:
              - code: sar_linea_base
                version: v1
                description: Plantilla SAR base
                namespace: https://softmobile.mx/sar
                schema_location: https://softmobile.mx/sar/schema.xsd
                content: |
                  <sar version=\"1.0\"><detalle>Base</detalle></sar>
            """,
        )
        _write_yaml(
            tmp_path,
            "parameters.yaml",
            """
            parameters:
              - key: sar_endpoint
                name: Endpoint SAR
                value_type: string
                value: https://sar.softmobile.mx/api
                metadata:
                  entorno: produccion
            """,
        )

        sync_response = client.post(
            "/configuration/sync",
            headers=reason_headers,
        )
        assert sync_response.status_code == 200
        sync_data = sync_response.json()
        assert sync_data["rates_activated"] >= 1
        assert "rates.yaml" in sync_data["processed_files"]

        overview = client.get("/configuration/overview", headers=headers)
        overview.raise_for_status()
        payload = overview.json()
        assert any(rate["slug"] == "tasa_corporativa" for rate in payload["rates"])
        assert any(
            template["code"] == "sar_linea_base"
            for template in payload["xml_templates"]
        )
        assert any(
            parameter["key"] == "sar_endpoint"
            for parameter in payload["parameters"]
        )
    finally:
        settings.config_sync_directory = original_dir


def test_configuration_rate_duplicate_slug_returns_conflict(client) -> None:
    headers = _bootstrap_admin(client)
    reason_headers = _authorized_reason_headers(headers)

    payload: dict[str, Any] = {
        "slug": "sar_conflicto",
        "name": "SAR Conflicto",
        "value": "0.1000",
        "unit": "porcentaje",
    }

    first_response = client.post(
        "/configuration/rates",
        json=payload,
        headers=reason_headers,
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/configuration/rates",
        json=payload,
        headers=reason_headers,
    )
    assert duplicate_response.status_code == 409
    assert "Ya existe" in duplicate_response.json()["detail"]


def test_configuration_sync_invalid_yaml_returns_unprocessable_entity(client, tmp_path) -> None:
    headers = _bootstrap_admin(client)
    reason_headers = _authorized_reason_headers(headers)

    original_dir = settings.config_sync_directory
    try:
        settings.config_sync_directory = str(tmp_path)
        _write_yaml(
            tmp_path,
            "invalid.yaml",
            """
            rates:
              - slug: tasa_invalida
                name: Tasa inválida
                value: 0.1500
                unit: porcentaje
                metadata: {
            """,
        )

        response = client.post(
            "/configuration/sync",
            headers=reason_headers,
        )
        assert response.status_code == 422
        assert "YAML" in response.json()["detail"]
    finally:
        settings.config_sync_directory = original_dir
