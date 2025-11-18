# Integraciones externas — Panel corporativo v2.2.0

Este módulo documenta las integraciones verificadas en Softmobile 2025 v2.2.0.
Su objetivo es centralizar cómo se conectan los servicios externos, qué
credenciales utilizan y cuáles son los endpoints expuestos por el backend para
monitorearlos.

## Conectores homologados

| Clave | Nombre | Rol operativo | Eventos soportados | Estado |
|-------|--------|---------------|--------------------|--------|
| `zapier` | Zapier Inventory Bridge | Automatización de flujos con Zapier | `inventory.device.updated`, `sales.order.completed`, `customers.balance.changed` | Activo |
| `power_bi` | Power BI Streaming | Actualización de dashboards financieros y de inventario | `inventory.snapshot.generated`, `sales.daily_summary` | Activo |
| `erp_sync` | ERP Sync Gateway | Sincronización bidireccional con ERP contable (stock, órdenes de compra/venta) | `inventory.transfer.completed`, `purchases.order.received`, `sales.invoice.issued` | En pruebas |

Cada conector mantiene los siguientes metadatos operativos:

- **Autenticación** (`auth_type`): actualmente se soportan tokens API tipo
  "Bearer" emitidos desde este módulo.
- **Empujes** (`supports_push`): indica si la integración puede recibir eventos
  vía webhooks corporativos.
- **Extracciones** (`supports_pull`): indica si la integración consulta datos a
  través de la API pública.
- **Credenciales vigentes** (`credential.token_hint`): últimos cuatro caracteres
  del token activo para validar coincidencias sin revelar el secreto.
- **Salud** (`health.status`): resultado del último monitoreo; valores posibles:
  `operational`, `degraded`, `offline`.

## Endpoints del backend

Los endpoints viven bajo `/integrations` y requieren autenticación con rol
`ADMIN`. Las operaciones que modifican credenciales o estado deben incluir la
cabecera `X-Reason` (≥5 caracteres) tal como exige el mandato de seguridad.

### `GET /integrations`

Devuelve la lista consolidada de conectores con su estado actual y el resumen de
credenciales.

### `GET /integrations/{slug}`

Ofrece detalles completos del conector seleccionado, incluyendo instrucciones
de despliegue, documentación oficial y capacidades habilitadas.

### `POST /integrations/{slug}/rotate`

Genera un nuevo token API válido por 90 días. El secreto recién emitido se
entrega una sola vez en la respuesta (`token`). Almacena internamente el hash
SHA-256 y expone `token_hint` para auditoría.

### `POST /integrations/{slug}/health`

Permite que los monitores corporativos reporten el estado de la integración.
Actualiza `health.status`, `health.message` y la marca temporal `checked_at`.

## Flujo típico de rotación de tokens

1. Autenticarse como usuario `ADMIN` y solicitar la rotación:

   ```http
   POST /integrations/zapier/rotate
   Authorization: Bearer <token_admin>
   X-Reason: Rotacion automatizada Zapier
   Content-Length: 0
   ```

2. Guardar el token devuelto (`token`) en el gestor seguro de credenciales.
3. Compartir únicamente los últimos cuatro caracteres (`token_hint`) al equipo
   de auditoría para confirmar que la integración fue actualizada.
4. Registrar el motivo de rotación en la bitácora correspondiente.

## Health checks automatizados

Para mantener la visibilidad de los conectores híbridos:

1. El monitor externo valida la conectividad con el servicio tercero.
2. En caso de éxito, envía:

   ```http
   POST /integrations/erp_sync/health
   Authorization: Bearer <token_admin>
   X-Reason: Sondeo ERP nocturno
   Content-Type: application/json

   {
     "status": "operational",
     "message": "Webhook de recepción confirma respuesta 200 ms"
   }
   ```

3. Ante fallos recurrentes, el monitor establece `status = "degraded"` o
   `status = "offline"` con un mensaje diagnóstico.

## Consideraciones de seguridad

- Todos los tokens nuevos se generan con 48 caracteres URL-safe y expiran en 90
  días. El backend almacena únicamente su hash SHA-256.
- Ningún endpoint expone el secreto actual; sólo se divulga al momento de la
  rotación.
- Las respuestas incluyen `expires_at` y `rotated_at` para facilitar auditorías
  cronológicas.
- Las integraciones que operan en modo híbrido deben conservar `X-Reason`
  incluso en consultas GET sensibles (`/reports`, `/customers`).

Mantener actualizada esta documentación permite validar rápidamente qué
servicios externos están autorizados y qué pasos seguir ante incidencias.
