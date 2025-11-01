from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..acl import require_roles
from ..audit_logger import audit_event

# Nota: evitamos depender de detalles de modelos específicos.
# Si existen helpers en crud, podemos usarlos; de lo contrario devolvemos forma vacía válida.
from .. import crud

router = APIRouter(
    prefix="/reports/sales",
    tags=["ventas"],
    dependencies=[Depends(require_roles('OPERADOR','GERENTE','ADMIN'))],
)


def _parse_date(d: Optional[str]) -> date:
    if not d:
        return date.today()
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, use YYYY-MM-DD")


@router.get("/daily")
def get_daily_sales(
    date_str: Optional[str] = Query(default=None, alias="date"),
    store_id: Optional[int] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
):
    """Resumen por día/sucursal.
    Entrega forma estable aunque no hayan datos (evita romper UI).
    """
    target_date = _parse_date(date_str)

    # Estructura canónica que espera el frontend
    payload: Dict[str, Any] = {
        "date": target_date.isoformat(),
        "store": ({"id": store_id, "name": None} if store_id else None),
        "totals": {
            "gross": 0.0,
            "discounts": 0.0,
            "net": 0.0,
            "cost": 0.0,
            "margin": 0.0,
            "margin_pct": 0.0,
        },
        "tickets": {
            "count": 0,
            "avg_ticket": 0.0,
        },
        "payments": [],
        "returns": {
            "count": 0,
            "amount": 0.0,
        },
    }

    # Si hay crud con sumatorias, intentamos poblar datos reales
    try:
        if crud is not None and hasattr(crud, 'summarize_sales_daily'):
            data = crud.summarize_sales_daily(target_date=target_date, store_id=store_id, payment_method=payment_method)
            if isinstance(data, dict):
                payload.update(data)
    except Exception:
        # No rompemos el endpoint si hay problemas internos
        pass

    audit_event(None, 'view', 'reports.sales.daily', None, {
        'date': payload['date'],
        'store_id': store_id,
        'payment_method': payment_method,
    })
    return payload


@router.get("/daily/export.csv")
def export_daily_sales_csv(
    date_str: Optional[str] = Query(default=None, alias="date"),
    store_id: Optional[int] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
):
    target_date = _parse_date(date_str)

    # Cabecera CSV estándar
    header = [
        'date','store_id','store_name','gross','discounts','net','cost','margin','margin_pct','tickets','avg_ticket','method','amount','count','returns_count','returns_amount'
    ]

    row = [
        target_date.isoformat(),
        store_id or '',
        '',
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0, 0.0,
        '', 0.0, 0,
        0, 0.0
    ]

    # Intentar datos reales si hay crud.summarize_sales_daily
    try:
        if crud is not None and hasattr(crud, 'summarize_sales_daily'):
            data = crud.summarize_sales_daily(target_date=target_date, store_id=store_id, payment_method=payment_method)
            if isinstance(data, dict):
                totals = data.get('totals') or {}
                tickets = data.get('tickets') or {}
                payments = (data.get('payments') or [])
                returns = data.get('returns') or {}
                # Exportamos una fila por método de pago (o una sola si vacío)
                rows: List[List[Any]] = []
                if payments:
                    for p in payments:
                        rows.append([
                            target_date.isoformat(),
                            store_id or '',
                            (data.get('store') or {}).get('name') if isinstance(data.get('store'), dict) else '',
                            totals.get('gross',0.0), totals.get('discounts',0.0), totals.get('net',0.0), totals.get('cost',0.0), totals.get('margin',0.0), totals.get('margin_pct',0.0),
                            tickets.get('count',0), tickets.get('avg_ticket',0.0),
                            p.get('method',''), p.get('amount',0.0), p.get('count',0),
                            returns.get('count',0), returns.get('amount',0.0)
                        ])
                else:
                    rows = [row]
            else:
                rows = [row]
        else:
            rows = [row]
    except Exception:
        rows = [row]

    sio = StringIO()
    sio.write(','.join(header) + '\n')
    for r in rows:
        sio.write(','.join(map(lambda x: str(x).replace(',', ' '), r)) + '\n')
    sio.seek(0)

    audit_event(None, 'export', 'reports.sales.daily.csv', None, {
        'date': target_date.isoformat(),
        'store_id': store_id,
        'payment_method': payment_method,
    })

    return StreamingResponse(sio, media_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename=daily_sales_{target_date.isoformat()}.csv'
    })
