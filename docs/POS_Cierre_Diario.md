# POS – Cierre de caja diario (v2.2.0)

Este documento define el **alcance funcional y técnico** del cierre de caja diario para Softmobile 2025 v2.2.0.

## Objetivos
- Resumen por día y sucursal: ventas brutas/netas, margen, tickets, devoluciones, medios de pago.
- Operación segura con **roles** (OPERADOR/GERENTE/ADMIN) + **X-Reason**.
- Exportables: JSON y CSV (y PDF si se requiere).

## Endpoints propuestos
> Se publicarán bajo el prefijo `/reports` para mantener coherencia con módulo de reportes.

1. `GET /reports/sales/daily`  
   **Query**: `date=YYYY-MM-DD` (default: hoy), `store_id` (opcional), `payment_method` (opcional).  
   **Roles**: OPERADOR+ (si `store_id` es propio), GERENTE, ADMIN.  
   **Respuesta**:
   ```json
   {
     "date": "2025-10-31",
     "store": {"id": 1, "name": "Centro"},
     "totals": {
       "gross": 12345.67,
       "discounts": 120.00,
       "net": 12225.67,
       "cost": 9800.00,
       "margin": 2425.67,
       "margin_pct": 19.84
     },
     "tickets": {
       "count": 37,
       "avg_ticket": 330.16
     },
     "payments": [
       {"method": "cash", "amount": 6000.00, "count": 18},
       {"method": "card", "amount": 5000.00, "count": 15},
       {"method": "transfer", "amount": 1225.67, "count": 4}
     ],
     "returns": {
       "count": 2,
       "amount": 450.00
     }
   }
   ```

2. `GET /reports/sales/daily/export.csv`  
   **Mismos filtros** que el anterior. Devuelve CSV con agregados por método de pago y líneas por ticket.

3. `POST /reports/sales/close`  
   **Body**: `{date, store_id, notes}`  \u2192 Genera un "cierre virtual" (persistencia opcional) incluyendo un hash de control para detectar alteraciones posteriores.

> Primera entrega: `GET /reports/sales/daily` + `export.csv` (sin persistencia).

## Reglas y seguridad
- **Auth obligatorio** + header `X-Reason`.
- **ACL**: `require_roles('OPERADOR','GERENTE','ADMIN')` con validación de sucursal cuando el rol sea OPERADOR.

## Implementación técnica
- Se reutilizará `crud.list_sales` y `crud.list_sale_items` para obtener datos; cuando no esté disponible, se aplicarán sumatorias directas por SQLAlchemy.
- Export CSV con `StreamingResponse`.
- Auditoría: `audit_event(user_id,'view','reports.sales.daily',reason,{...})` y `...csv`.

## Tareas (PR 1)
- [ ] Endpoint `GET /reports/sales/daily`.
- [ ] Endpoint `GET /reports/sales/daily/export.csv`.
- [ ] Tests unitarios básicos sobre agregación.
- [ ] Documentación de uso.

## Tareas (PR 2)
- [ ] Cierre virtual `POST /reports/sales/close`.
- [ ] PDF resumen.
- [ ] Validaciones por rol de sucursal (OPERADOR).
