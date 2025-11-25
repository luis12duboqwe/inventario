# PWA híbrida para conteos y ventas offline (Softmobile 2025 v2.2.0)

## Objetivos
- Capturar conteos de inventario y ventas en modo offline manteniendo la experiencia POS con soporte de borradores y recibos.
- Garantizar confidencialidad mediante cifrado local y control de acceso basado en sesión corporativa.
- Sincronizar automáticamente con el backend al recuperar conectividad, resolviendo identificadores temporales y reconciliando diferencias sin romper compatibilidad.

## Arquitectura general
- **App Shell + Service Worker**: caché de recursos críticos (HTML, JS, estilos, fuentes) y estrategias `stale-while-revalidate` para cargar rápido en campo. Colas dedicadas en el SW para telemetría mínima y reintentos.
- **Almacenamiento local cifrado**: IndexedDB con envoltorio en WebCrypto (AES-GCM 256). Clave derivada de secreto efímero de sesión (`session_key`) y salt por dispositivo; se almacena sólo el material envuelto con `CryptoKey` no exportable.
- **Repositorio offline**: tablas `inventory_counts`, `draft_sales`, `sync_outbox`, `sync_inbox`, `attachments` con marcas `store_id`, `user_id`, `device_id`, `created_at`, `updated_at`, `x_reason` y `last_hash` para auditoría.
- **Feature flags y compatibilidad**: se expone bajo flag `SOFTMOBILE_ENABLE_HYBRID_PREP` sin modificar rutas actuales; los endpoints existentes permanecen intactos y reciben la data reconciliada cuando vuelva la red.

### Estructura y cifrado de datos locales
- **Tablas clave**: `inventory_counts` (detalle de conteos y ajustes), `draft_sales` (ventas y pagos), `attachments` (firmas/fotos), `sync_outbox`/`sync_inbox` (eventos pendientes/recibidos) y `id_map` (mapeo `tmp_id`⇔`server_id`).
- **Cifrado en repositorio**: cada registro persiste `{cipher_iv, cipher_tag, payload_encrypted}`; el `payload_encrypted` contiene el JSON serializado del objeto incluyendo hashes de integridad (`sha256`), totales y desglose de impuestos.
- **Gestión de claves**: la `session_key` se deriva con `PBKDF2` (>=100k iteraciones) y salt por dispositivo; se guarda únicamente la clave envuelta con `CryptoKey` no exportable. Se rota al cerrar sesión, al detectar 24 h de antigüedad o al recibir error criptográfico.
- **Validación previa a escritura**: todo payload cifrado incluye `x_reason` (mínimo 5 caracteres), `store_id`, `user_id` y `device_id`; el wrapper rechaza escrituras incompletas para evitar registros huérfanos.

## Identificadores temporales
- **Numeración local**: prefijo `TMP-{store_id}-{device_id}-{epoch_ms}-{seq}` para ventas y conteos; se usa como `external_id` hasta recibir folio corporativo.
- **Mapa de reconciliación**: tabla `id_map` mantiene pares `{tmp_id -> server_id, version, status}`. Al confirmar en backend se actualiza y se propagan los cambios al UI y a la cola `sync_outbox`.
- **Compatibilidad POS**: `/pos/sale` y `/pos/sales/*` siguen generando recibos PDF; los temporales usan borradores y recibos locales en base64 hasta que el backend devuelva el PDF oficial.

## Flujo offline de conteos
1. **Inicio de sesión**: al autenticarse se genera `session_key` y se precargan catálogos mínimos (productos, sucursales, impuestos) en caché cifrada.
2. **Captura**: cada conteo almacena items con `quantity`, `unit_price`, `inventory_value` calculado localmente y hash incremental para validación de integridad.
3. **Auditoría**: se guarda `x_reason` (≥5 caracteres), geolocalización opcional y firma de usuario; las ediciones incrementan `version` y recalculan `last_hash`.
4. **Cola de sincronización**: se agrega evento `count.created|updated|deleted` en `sync_outbox` con snapshot cifrado y checksum; el SW controla reintentos exponenciales y backoff por error 409/429.

## Flujo offline de ventas
1. **Borrador**: venta inicia como `draft_sales` con métodos de pago múltiples y balanceo de inventario reservado localmente.
2. **Pagos y descuentos**: se registran pagos parciales, descuentos y devoluciones asociadas al `tmp_id`; se valida límite de crédito usando datos cacheados y se bloquea si no hay respaldo local.
3. **Impuestos y totales**: cálculo de `unit_price` y `inventory_value` sigue las reglas vigentes; se guarda desglose para evitar divergencias al sincronizar.
4. **Completado local**: al cerrar se genera recibo HTML/PDF local para el cliente y se emite evento `sale.completed` en `sync_outbox` con trace de reservas de inventario.

### Secuencias de sincronización
1. **Desencadenante**: el SW recibe `online` o `sync:force` desde la UI. El planificador prioriza `sync_outbox` por `created_at` y categoría (ventas antes que conteos cuando ambos están pendientes).
2. **Envío cifrado**: cada evento se desencripta en memoria, se valida hash y se envía vía `/sync/outbox` con `tmp_id`, `last_hash`, `x_reason` y versión local. Los adjuntos viajan como `multipart/form-data` en la misma sesión.
3. **Respuesta del backend**: el servidor confirma con `server_id`, `folio`, `pdf_url|pdf_base64`, `inventory_delta` y `conflict` opcional. Si `conflict=true`, se coloca en `sync_inbox` con snapshot de servidor y local para reconciliación guiada.
4. **Actualización local**: se actualiza `id_map`, se reemplaza el recibo local y se marca el evento como `ack` en `sync_outbox`. Para conteos, se registra ajuste compensatorio con referencia al folio corporativo.
5. **Confirmación visual**: la UI muestra progreso, número de operaciones sincronizadas y errores pendientes. Los elementos reconciliados desaparecen del contador de pendientes en tabs/accordions.

## Sincronización y reconciliación
- **Desencadenante**: el SW detecta conectividad o el usuario fuerza sincronización. Primero se envían pendientes de `sync_outbox` en orden FIFO por `created_at`.
- **Resolución de conflictos**: estrategia *last-write-wins* por `updated_at` + `version`, con validación de hashes. Si el backend reporta diferencia en stock, se genera ajuste compensatorio en `sync_inbox` para revisión manual.
- **Asignación de folios**: al confirmar venta/conteo, el backend devuelve `server_id`, folio y PDF; se actualiza `id_map`, se sustituye el recibo local y se cierra el temporal.
- **Reintentos**: códigos 5xx/timeout reprograman envío con jitter; 401/403 limpian claves y fuerzan reautenticación; 409 dispara merge guiado mostrando diferencias al usuario.
- **Telemetría**: métricas anónimas (sin datos sensibles) sobre número de reintentos, tiempo de sincronización y tasa de conflictos, enviadas sólo cuando hay red.

### Manejo de errores y reconciliación guiada
- **409 con diferencia de stock**: se presenta tabla comparativa `local vs servidor` para cantidades y `inventory_value`; la selección del usuario genera un nuevo evento `count.merge` en `sync_outbox` con la versión elegida.
- **Errores criptográficos**: cualquier fallo de derivación o desencriptado detiene sincronización, borra claves envueltas y exige reautenticación antes de continuar.
- **Tiempo excedido**: si un envío supera 15 s, se reencola con `retry_at` + `jitter`; tras 5 intentos se muestra alerta persistente en la UI y se sugiere conexión estable.
- **Adjuntos fallidos**: cuando una foto o firma no sube, se conserva en `attachments` con contador de reintentos independiente y se reenvía ligado al `tmp_id` original.

## Observabilidad y pruebas
- **Métricas**: contador de operaciones pendientes, tiempo promedio de sincronización, ratio de conflictos y fallos de cifrado; se publican cuando hay red y sin incluir datos sensibles.
- **Trazas**: cada evento guarda `trace_id` compartido entre `sync_outbox` y logs de backend para cruzar reintentos y folios asignados.
- **Pruebas recomendadas**:
  - Mock de conectividad (`online/offline`) y expiración de `session_key` para validar rotación de claves.
  - Simulación de 409 entre conteo local y servidor, confirmando la creación de `count.merge` con el hash adecuado.
  - Validar que devoluciones y pagos parciales preserven `inventory_value` y se reconcilien al recibir el folio corporativo.
  - Prueba de adjuntos: subir foto en offline, forzar 2 fallos y confirmar reintento exitoso con el `tmp_id` mapeado.

## Seguridad y privacidad
- Clave local rotada al cerrar sesión o tras 24 horas; se invalida el repositorio si falla la derivación de clave.
- Adjuntos (fotos, firmas) se cifran como blobs en `attachments` y se eliminan tras confirmación del backend o al expirar TTL configurable.
- Se evita almacenar credenciales; sólo tokens efímeros en memoria y metadatos mínimos cifrados en repositorio.

## Interfaz y UX
- Indicadores visibles en tabs/accordions existentes: estado de conexión, conteos/ventas pendientes, últimos conflictos y botón «Forzar sincronización».
- Modal de reconciliación muestra diferencias campo a campo y permite elegir versión local o servidor antes de reenviar.
- Alertas accesibles (tema oscuro cian) para fallos de cifrado, clave expirada o falta de motivo `X-Reason`.

## Consideraciones de implementación
- Reutilizar `sync_outbox` del modo híbrido para registrar operaciones locales; extender esquemas con `tmp_id`, `cipher_iv`, `hash` y `x_reason`.
- Service Worker debe exponer canal `postMessage` para que la app informe nuevas operaciones y reciba estado de sincronización.
- Pruebas: simulaciones con `msw`/`pytest` para validar reconexión, mapeo de folios, cálculo de inventario y preservación de `inventory_value`.
- Documentar flags, rutas y limitaciones en README/bitácoras sin modificar la versión declarada (v2.2.0).

## Checklist de validaciones offline
- **Integridad de datos**: todo registro cifrado debe incluir `sha256(payload)` y `last_hash` encadenado; si la verificación falla al desencriptar, se descarta el evento y se marca como `corrupt` en `sync_outbox`.
- **Motivo corporativo**: ninguna operación se acepta sin `x_reason` (≥5 caracteres). El validador bloquea ventas, conteos y adjuntos antes de persistir localmente.
- **Consistencia de inventario**: los conteos y ventas locales recalculan `inventory_value` usando la misma fórmula del backend para evitar ajustes posteriores; se registran `previous_quantity` y `delta`.
- **Sesión**: al expirar `session_key` el repositorio se cierra en modo de sólo lectura hasta que el usuario vuelva a autenticarse y rederive la clave.
- **Adjuntos**: cada blob almacena `mime_type`, `size`, `checksum` y `retry_count`; si supera tres reintentos fallidos se mueve a una bandeja de revisión manual.

## Estrategia de reconciliación avanzada
- **Merge guiado**: cuando el backend devuelve `conflict=true`, se presenta un diff detallado (cantidades, impuestos, descuentos, pagos y adjuntos). El usuario selecciona versión y se genera `count.merge` o `sale.merge` en `sync_outbox` con el snapshot elegido.
- **Prevención de duplicados**: el mapeo `id_map` marca `status=pending_merge` mientras exista un conflicto; se evita crear nuevas operaciones sobre el mismo `tmp_id` hasta que se resuelva.
- **Reversión segura**: si el usuario descarta la versión local, se genera una anotación `discarded_local` en `sync_outbox` que elimina borradores y libera reservas de inventario.
- **Auditoría cruzada**: toda reconciliación graba `x_reason`, `user_id`, `device_id`, `store_id` y `trace_id` para correlacionar con logs de backend. Los eventos aceptados permanecen consultables en la bitácora local durante 30 días.
- **Adjuntos sincronizados**: los archivos ligados a un `tmp_id` en conflicto se vuelven a subir sólo si cambió el `checksum`; de lo contrario se reutiliza el adjunto ya aceptado por el servidor para ahorrar ancho de banda.

## Telemetría y monitoreo
- **Dashboards**: la UI expone contadores de `sync_outbox` (pendientes, en progreso, corruptos) y de `sync_inbox` (conflictos abiertos, resueltos), junto con tiempo promedio de sincronización.
- **Alertas**: se muestran banners persistentes cuando hay claves expiradas, más de tres reintentos fallidos o cuando `inventory_value` local diverge del servidor; incluyen acción rápida «Reintentar» o «Forzar reautenticación».
- **Logs estructurados**: el SW registra eventos `sync_event_sent`, `sync_event_ack`, `sync_event_failed` y `crypto_error` con metadatos mínimos (sin payloads) y los envía en lote cuando vuelve la red.

## Pruebas adicionales sugeridas
- **Flujos POS**: simular venta a crédito en offline que exceda límite local, verificar bloqueo y que el backend rechace con `409` al sincronizar, manteniendo el inventario intacto.
- **Rotación de claves**: forzar expiración de `session_key`, intentar escribir y confirmar que el repositorio entra en modo lectura; tras reautenticarse, validar que los datos antiguos se desencriptan con la nueva clave envuelta.
- **Adjuntos grandes**: probar subida de imágenes de 5 MB en offline, provocar dos fallas y validar reintento exitoso con mantenimiento del `checksum`.
- **Corruptelas de disco**: alterar manualmente un registro en IndexedDB y asegurar que el sistema lo marca `corrupt`, pide recolección de datos y continúa con el resto de la cola.
