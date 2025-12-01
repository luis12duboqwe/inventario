# Integraciones externas — Softmobile 2025 v2.2.0

## 1. Inventario y catálogo
- **Importación y auditoría**: `/inventory/import/smart` admite archivos Excel/CSV con modo borrador o confirmación, controlando overrides y motivos corporativos (`X-Reason`). Ofrece historial paginado en `/inventory/import/smart/history` para rastrear corridas y advertencias.【F:backend/app/routers/inventory.py†L27-L99】【F:backend/app/routers/inventory.py†L101-L140】
- **Reservas y movimientos**: `/inventory/reservations` permite listar, crear y caducar reservas en sucursales, reutilizando validaciones de stock y encabezado `X-Reason`. Esta ruta sirve como base para integraciones de pick-up y marketplaces.【F:backend/app/routers/inventory.py†L142-L223】
- **Catálogo enriquecido**: los modelos `Device` y `DeviceIdentifier` exponen IMEI, seriales y metadatos comerciales. Se propaga por la cola híbrida para mantener consistencia con catálogos externos.【F:backend/app/models/__init__.py†L245-L360】

## 2. Movimientos comerciales y POS
- **POS corporativo**: `/pos/sale` registra ventas completas o borradores, resolviendo dispositivos por IMEI y devolviendo recibos PDF/JSON compatibles. Exige `X-Reason`, valida límite de crédito y múltiples métodos de pago.【F:backend/app/routers/pos.py†L1-L105】
- **Recibos y recuperación**: `/pos/receipt/{sale_id}` entrega el PDF corporativo, permitiendo que sistemas externos descarguen comprobantes firmados tras la venta.【F:backend/app/routers/pos.py†L107-L142】
- **Ventas, compras y transferencias**: Routers dedicados (`/sales`, `/purchases`, `/transfers`) cubren flujos completos de órdenes, recepciones parciales, descuentos y cambios de stock, compartiendo esquema de auditoría y encabezados sensibles.【F:backend/app/routers/sales.py†L1-L160】【F:backend/app/routers/purchases.py†L1-L120】【F:backend/app/routers/transfers.py†L1-L150】

## 3. Clientes, proveedores y reparaciones
- **Gestión de clientes**: `/customers` admite filtros por estado, tipo y deuda; expone endpoints de pagos, notas y resúmenes financieros para sincronizar CRMs o ERPs.【F:backend/app/routers/customers.py†L1-L180】
- **Proveedores y compras**: `/suppliers` complementa la lógica de abastecimiento con sincronización de lotes, contactos y ajustes de deuda corporativa.【F:backend/app/routers/suppliers.py†L1-L140】
- **Reparaciones**: `/repairs` controla órdenes con partes y estados, útil para talleres externos que requieren visibilidad de SLA y cotizaciones.【F:backend/app/routers/repairs.py†L1-L160】

## 4. Reportes, monitoreo y actualizaciones
- **Analítica avanzada**: `/reports/*` genera tableros globales, exportaciones PDF/Excel y reportes específicos (portafolio de clientes, métricas de inventario), sujetos a `X-Reason` y feature flag de analítica.【F:backend/app/routers/reports.py†L1-L120】【F:backend/app/routers/reports.py†L122-L183】
- **Monitoreo operativo**: `/monitoring` y `/system_logs` permiten integrar paneles externos para alertamiento y seguimiento de errores corporativos.【F:backend/app/routers/monitoring.py†L1-L120】【F:backend/app/routers/system_logs.py†L1-L140】
- **Actualizaciones**: `/updates/status` y `/updates/history` consumen el feed oficial `docs/releases.json`, facilitando integraciones con CMDB o herramientas de despliegue.【F:backend/app/routers/updates.py†L1-L28】

## 5. Sincronización híbrida y colas
- **Outbox transaccional**: `SyncOutbox` almacena cambios críticos por entidad con control de intentos, prioridad y resolución de conflictos *last-write-wins*, habilitando replicación hacia sistemas externos.【F:backend/app/models/__init__.py†L2006-L2044】
- **Cola híbrida**: `SyncQueue` y `SyncAttempt` persisten eventos listos para despachar, registrando estado, intentos y errores para observabilidad completa.【F:backend/app/models/__init__.py†L2046-L2092】
- **Servicios de despacho**: `/sync/events`, `/sync/dispatch` y `/sync/status*` permiten inyectar eventos, disparar reintentos y consultar métricas; el servicio `sync_queue.dispatch_pending_events` reintenta con *backoff* y opcionalmente publica en un webhook remoto configurable (`settings.sync_remote_url`).【F:backend/app/routers/sync.py†L47-L135】【F:backend/app/services/sync_queue.py†L1-L103】【F:backend/app/services/sync_queue.py†L105-L188】
- **Motivos obligatorios**: `require_reason` y `require_reason_optional` centralizan la validación del encabezado `X-Reason` (≥5 caracteres) para toda operación sensible, requisito clave en integraciones.【F:backend/app/routers/dependencies.py†L1-L26】

## 6. Evaluación de Webhooks vs Colas
| Caso | Estado actual | Riesgos detectados | Ajustes recomendados |
| --- | --- | --- | --- |
| Confirmaciones de venta y recibos | POS devuelve PDF/JSON bajo demanda; la cola híbrida puede emitir eventos `sales.*`. | Dependencia de sondeos para saber cuándo una venta quedó registrada. | Habilitar webhook opcional que se dispare desde `sync_queue.dispatch_pending_events` cuando `settings.sync_remote_url` esté definido, con payload resumido y reintentos controlados por la cola.【F:backend/app/services/sync_queue.py†L67-L121】 |
| Alertas de inventario crítico | Endpoints `/inventory/reservations` y reportes requieren consulta activa. | Riesgo de saturar API en integraciones con monitoreo en tiempo real. | Agregar evento `inventory.threshold_breach` en outbox/cola y webhook, aprovechando `SyncQueue` para reintentos y confirmaciones.【F:backend/app/models/__init__.py†L2006-L2092】 |
| Auditoría de seguridad | `/audit` y `/security` registran acciones pero no emiten notificaciones. | Alta latencia para SOC externos. | Reusar cola híbrida para publicar `security.audit_event` hacia SIEM vía webhook autenticado. |

**Conclusión**: Mantener la cola híbrida como origen de verdad y ofrecer webhooks opcionales (configurados por `settings.sync_remote_url`) evita duplicar lógica de reintentos, concentrando el despacho en un punto controlado.【F:backend/app/services/sync_queue.py†L105-L188】

## 7. Matriz de compatibilidad propuesta
| Integración | Autenticación | Formatos soportados | Dependencias | Observaciones |
| --- | --- | --- | --- | --- |
| OMS externo (ventas) | Token Bearer + `X-Reason` | JSON + PDF (recibo) | `/pos/sale`, `/pos/receipt/{id}` | Validar límites de crédito antes de confirmar ventas a crédito.【F:backend/app/routers/pos.py†L24-L105】 |
| ERP compras | Token Bearer + `X-Reason` | JSON | `/purchases`, `/suppliers` | Soporta recepciones parciales y ajustes de costo promedio; requiere sincronizar proveedores previo al alta.【F:backend/app/routers/purchases.py†L1-L120】【F:backend/app/routers/suppliers.py†L1-L140】 |
| Marketplace inventario | Token Bearer + `X-Reason` | JSON | `/inventory/*`, `SyncQueue` | Aprovecha catálogo con IMEI/serial; se recomienda consumir eventos `inventory.*` vía cola para evitar sobreconsulta.【F:backend/app/routers/inventory.py†L27-L223】【F:backend/app/models/__init__.py†L2006-L2092】 |
| CRM fidelización | Token Bearer + `X-Reason` | JSON, CSV/PDF (reportes) | `/customers`, `/reports/customers/*` | Permite pagos y notas; exporta portafolio para campañas.【F:backend/app/routers/customers.py†L1-L180】【F:backend/app/routers/reports.py†L1-L183】 |

## 8. Matriz de pruebas piloto
| Fase | Objetivo | Endpoints | Métricas de éxito | Consideraciones |
| --- | --- | --- | --- | --- |
| Piloto 1 — Ventas POS hacia OMS | Validar registro y confirmación de ventas con recibo. | `/pos/sale`, `/pos/receipt/{id}`, `/sync/status` | % de ventas confirmadas sin reintentos > 99 %, latencia < 5 s. | Simular ventas con descuentos y crédito para asegurar compatibilidad financiera.【F:backend/app/routers/pos.py†L24-L142】【F:backend/app/routers/sync.py†L47-L135】 |
| Piloto 2 — Inventario en marketplace | Publicar catálogo actualizado y reservas. | `/inventory/import/smart`, `/inventory/reservations`, eventos `inventory.*` | Diferencia de stock < 1 %, reservas expiradas resueltas en < 15 min. | Activar eventos en `SyncQueue` y validar reintentos con `sync_dispatch` programado.【F:backend/app/routers/inventory.py†L27-L223】【F:backend/app/services/sync_queue.py†L105-L188】 |
| Piloto 3 — Reportes financieros en CRM | Exportar métricas y portafolio de clientes. | `/reports/customers/portfolio`, `/customers/*` | Coincidencia de saldos > 99.5 %, generación de PDF < 10 s. | Confirmar cabecera `X-Reason` en exportaciones y revisar límites de paginación.【F:backend/app/routers/reports.py†L1-L183】【F:backend/app/routers/customers.py†L1-L180】 |
| Piloto 4 — Alertas de seguridad | Notificar auditorías críticas en tiempo real. | `/audit`, `/security`, eventos `security.*` vía cola | Tiempo de notificación < 60 s, cero eventos perdidos tras 3 reintentos. | Extender webhook con firma HMAC aprovechando `SyncQueue` y `sync_remote_url`.【F:backend/app/routers/audit.py†L1-L140】【F:backend/app/services/sync_queue.py†L105-L188】 |

## 9. Próximos pasos
1. Documentar payloads estándar (esquemas pydantic) por módulo para compartirlos con aliados externos.
2. Definir contrato de webhook (firma, reintentos, cabeceras) reutilizando `SyncQueue` como planificador.
3. Orquestar pruebas automáticas de integraciones clave usando `pytest` y ambientes aislados con fixtures para colas híbridas.
