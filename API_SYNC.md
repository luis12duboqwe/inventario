# Referencia de sincronización — Softmobile 2025 v2.2.0

Esta guía describe los endpoints de sincronización híbrida disponibles en el backend FastAPI. Todos los ejemplos asumen autenticación Bearer y el uso del encabezado `X-Reason` (mínimo 5 caracteres) para operaciones sensibles.

## Convenciones generales

- Base path: `/api/v1/sync`
- Autenticación: JWT Bearer. Los roles `admin`, `manager` o `sync_operator` pueden invocar los métodos.
- Encabezados relevantes:
  - `Authorization: Bearer <token>`
  - `X-Reason: <motivo corporativo>`
  - `X-Idempotency-Key` (opcional) para asegurar operaciones idempotentes.

## Endpoints principales

### Ejecutar sincronización inmediata

`POST /run`

Inicia un ciclo de sincronización contra la central híbrida.

```http
POST /api/v1/sync/run HTTP/1.1
Authorization: Bearer <token>
X-Reason: Sincronización manual inventario
Content-Type: application/json

{}
```

**Respuesta**

```json
{
  "id": 814,
  "mode": "hybrid",
  "status": "completed",
  "started_at": "2025-02-15T10:22:41.871Z",
  "finished_at": "2025-02-15T10:23:18.102Z"
}
```

### Registrar eventos en la cola local

`POST /queue/events`

Permite agregar eventos a la cola híbrida. Usa `X-Idempotency-Key` para evitar duplicados.

```http
POST /api/v1/sync/queue/events HTTP/1.1
Authorization: Bearer <token>
X-Reason: Ajuste inventario remoto
X-Idempotency-Key: queue-inventory-1
Content-Type: application/json

{
  "events": [
    {
      "event_type": "inventory.adjustment",
      "payload": {
        "store_id": 3,
        "device_id": 120,
        "delta": -1,
        "comment": "Ajuste manual"
      }
    }
  ]
}
```

**Respuesta**

```json
{
  "queued": [
    {
      "id": 95,
      "event_type": "inventory.adjustment",
      "status": "PENDING",
      "idempotency_key": "queue-inventory-1",
      "created_at": "2025-02-15T10:24:02.482Z"
    }
  ],
  "reused": []
}
```

### Resumen de cola local

`GET /status/summary`

Devuelve métricas generales de la cola híbrida.

```json
{
  "percent": 96.4,
  "total": 1420,
  "processed": 1368,
  "pending": 42,
  "failed": 10,
  "last_updated": "2025-02-15T10:21:55.001Z",
  "oldest_pending": "2025-02-14T23:01:12.000Z"
}
```

### Panorama híbrido consolidado

`GET /overview`

Integra progreso, estimaciones y desglose por módulo.

```json
{
  "generated_at": "2025-02-15T10:20:11.001Z",
  "percent": 97.8,
  "total": 1890,
  "processed": 1848,
  "pending": 34,
  "failed": 8,
  "remaining": {
    "total": 42,
    "pending": 34,
    "failed": 8,
    "remote_pending": 21,
    "remote_failed": 6,
    "outbox_pending": 13,
    "outbox_failed": 2,
    "estimated_minutes_remaining": 18,
    "estimated_completion": "2025-02-15T10:38:00Z"
  },
  "queue_summary": { "percent": 97.1, "total": 640, "processed": 622, "pending": 12, "failed": 6 },
  "progress": {
    "percent": 97.8,
    "total": 1890,
    "processed": 1848,
    "pending": 34,
    "failed": 8,
    "components": {
      "queue": { "total": 640, "processed": 622, "pending": 12, "failed": 6 },
      "outbox": { "total": 1250, "processed": 1226, "pending": 22, "failed": 2 }
    }
  },
  "forecast": {
    "lookback_minutes": 30,
    "processed_recent": 240,
    "processed_queue": 140,
    "processed_outbox": 100,
    "attempts_total": 260,
    "attempts_successful": 252,
    "success_rate": 96.9,
    "events_per_minute": 7.8,
    "backlog_pending": 34,
    "backlog_failed": 8,
    "backlog_total": 42,
    "estimated_minutes_remaining": 18,
    "estimated_completion": "2025-02-15T10:38:00Z"
  },
  "breakdown": [
    {
      "module": "inventory",
      "label": "Inventario",
      "total": 820,
      "processed": 804,
      "pending": 10,
      "failed": 6,
      "percent": 98.1,
      "queue": { "total": 320, "processed": 314, "pending": 4, "failed": 2 },
      "outbox": { "total": 500, "processed": 490, "pending": 6, "failed": 4 }
    }
  ]
}
```

### Outbox corporativa

`GET /outbox`

Lista eventos pendientes en la outbox central (servidor). Puedes filtrar por `status` (`PENDING`, `FAILED`).

`POST /outbox/retry`

Reagenda eventos fallidos. Requiere `X-Reason` y recomienda utilizar `X-Idempotency-Key`.

### Webhooks públicos para contabilidad y e-commerce

`GET /integrations/hooks/{slug}/events`

Entrega eventos de ventas y transferencias listos para despachar a conectores contables o de e-commerce usando el token API del conector (`X-Integration-Token`). Los eventos provienen de la outbox híbrida (`sale`, `transfer_order`, `inventory`) y respetan el motivo corporativo (`X-Reason`).

`POST /integrations/hooks/{slug}/events/{id}/ack`

Permite confirmar (`sent`) o reportar fallo (`failed`) en la entrega del evento. Al confirmar se marca la entrada como `SENT`; al reportar error se conserva el detalle y el estatus `FAILED` en la outbox.

### Historial por tienda

`GET /history`

Devuelve sesiones agrupadas por sucursal con estados `completed`, `running` o `failed`. Utiliza el panel para identificar tiendas con retrasos recurrentes.

## Cabeceras y utilidades

- Usa `backend/app/api/deps_enterprise.py` para validar motivos (`require_reason`) y claves idempotentes (`require_idempotency_key`).
- Genera claves determinísticas con `backend/app/utils/idempotency.py` (`generate_from_parts`, `combine_keys`).
- Todas las exportaciones (`/reports/*`) requieren `X-Reason` y respetan los flags `SOFTMOBILE_ENABLE_*`.

## Buenas prácticas

1. Registra siempre el motivo corporativo en auditoría (`audit_log`).
2. Evita limpiar la outbox manualmente; utiliza los endpoints de retry.
3. No desactives `SOFTMOBILE_ENABLE_HYBRID_PREP` salvo en ambientes controlados.
4. Verifica métricas tras cada despliegue con `/overview` y `/outbox/stats`.

Esta referencia debe mantenerse sincronizada con los cambios documentados en `README.md` y `CHANGELOG.md`.
