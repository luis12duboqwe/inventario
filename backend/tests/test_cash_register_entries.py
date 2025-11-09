from datetime import datetime

from backend.app.config import settings
from backend.tests.test_pos import _bootstrap_admin


def test_cash_register_entries_flow(client, db_session):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Operación de caja automatizada"}

        store_response = client.post(
            "/stores",
            json={"name": "Caja Norte", "location": "MTY", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == 201
        store_id = store_response.json()["id"]

        open_response = client.post(
            "/pos/cash/open",
            json={"store_id": store_id, "opening_amount": 100.0, "notes": "Inicio turno"},
            headers=reason_headers,
        )
        assert open_response.status_code == 201
        session_id = open_response.json()["id"]

        income_payload = {
            "session_id": session_id,
            "entry_type": "INGRESO",
            "amount": 50.0,
            "reason": "Reposición ventas en efectivo",
        }
        income_response = client.post(
            "/pos/cash/register/entries",
            json=income_payload,
            headers=reason_headers,
        )
        assert income_response.status_code == 201
        assert income_response.json()["entry_type"] == "INGRESO"

        expense_payload = {
            "session_id": session_id,
            "entry_type": "EGRESO",
            "amount": 20.0,
            "reason": "Pago servicio de mensajería",
            "notes": "Autorizado por supervisor",
        }
        expense_response = client.post(
            "/pos/cash/register/entries",
            json=expense_payload,
            headers=reason_headers,
        )
        assert expense_response.status_code == 201
        assert expense_response.json()["notes"] == "Autorizado por supervisor"

        entries_response = client.get(
            f"/pos/cash/register/entries?session_id={session_id}",
            headers=reason_headers,
        )
        assert entries_response.status_code == 200
        entries_payload = entries_response.json()
        assert len(entries_payload) == 2

        close_without_reason = client.post(
            "/pos/cash/close",
            json={
                "session_id": session_id,
                "closing_amount": 128.0,
                "payment_breakdown": {"EFECTIVO": 0.0},
                "denominations": [{"value": 20.0, "quantity": 3}],
            },
            headers=reason_headers,
        )
        assert close_without_reason.status_code == 422

        close_response = client.post(
            "/pos/cash/close",
            json={
                "session_id": session_id,
                "closing_amount": 128.0,
                "payment_breakdown": {"EFECTIVO": 0.0},
                "denominations": [
                    {"value": 50.0, "quantity": 1},
                    {"value": 20.0, "quantity": 2},
                    {"value": 10.0, "quantity": 1},
                ],
                "reconciliation_notes": "Conteo con supervisor",
                "difference_reason": "Faltan monedas por recolección",
            },
            headers=reason_headers,
        )
        assert close_response.status_code == 200
        closed_session = close_response.json()
        assert closed_session["status"] == "CERRADO"
        assert closed_session["difference_reason"] == "Faltan monedas por recolección"
        assert closed_session["denomination_breakdown"]["50.00"] == 1
        assert closed_session["reconciliation_notes"] == "Conteo con supervisor"

        report_json = client.get(
            f"/pos/cash/register/{session_id}/report?export=json",
            headers=reason_headers,
        )
        assert report_json.status_code == 200
        report_payload = report_json.json()
        assert report_payload["entries"] and len(report_payload["entries"]) == 2

        report_pdf = client.get(
            f"/pos/cash/register/{session_id}/report?export=pdf",
            headers=reason_headers,
        )
        assert report_pdf.status_code == 200
        assert report_pdf.headers["content-type"].startswith("application/pdf")
        assert len(report_pdf.content) > 100

        today = datetime.utcnow().date()
        cash_close = client.get(
            f"/reports/cash-close?date={today.isoformat()}&branchId={store_id}",
            headers=reason_headers,
        )
        assert cash_close.status_code == 200
        cash_close_payload = cash_close.json()
        assert cash_close_payload["incomes"] >= 50.0
        assert cash_close_payload["expenses"] >= 20.0
    finally:
        settings.enable_purchases_sales = original_flag
