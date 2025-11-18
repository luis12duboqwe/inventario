from fastapi import status


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin-export",
        "password": "ClaveSegura789",
        "full_name": "Admin Export",
        "roles": ["ADMIN"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_devices_export_pdf_and_excel(client) -> None:
    headers = _auth_headers(client)
    # Crear sucursal
    store_payload = {"name": "Sucursal Export",
                     "location": "CDMX", "timezone": "America/Mexico_City"}
    store_resp = client.post("/stores", json=store_payload,
                             headers={**headers, "X-Reason": "Crear sucursal para export"})
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    # Crear dispositivos mínimos
    for idx in range(1, 3):
        device_payload = {
            "sku": f"EXP-SKU-{idx:03d}",
            "name": f"Dispositivo Export {idx}",
            "quantity": idx,
            "unit_price": 1000 + idx * 10,
        }
        r = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers={**headers, "X-Reason": "Alta dispositivo export"},
        )
        assert r.status_code == status.HTTP_201_CREATED

    # Export PDF
    pdf_resp = client.get(
        f"/inventory/stores/{store_id}/devices/export/pdf",
        headers={**headers, "X-Reason": "Exportar catalogo PDF"},
    )
    assert pdf_resp.status_code == status.HTTP_200_OK
    assert pdf_resp.headers["content-type"].startswith("application/pdf")
    pdf_bytes = pdf_resp.content
    assert pdf_bytes[:4] == b"%PDF"
    # Verificar tamaño mínimo indicativo de contenido (encabezados + filas)
    assert len(pdf_bytes) > 800

    # Export Excel
    xlsx_resp = client.get(
        f"/inventory/stores/{store_id}/devices/export/xlsx",
        headers={**headers, "X-Reason": "Exportar catalogo XLSX"},
    )
    assert xlsx_resp.status_code == status.HTTP_200_OK
    assert xlsx_resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    xlsx_bytes = xlsx_resp.content
    # XLSX empaquetado por openxml inicia normalmente con bytes PK (zip)
    assert xlsx_bytes[:2] == b"PK"
