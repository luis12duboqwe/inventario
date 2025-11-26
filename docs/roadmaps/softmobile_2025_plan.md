# Softmobile 2025 v2.2.0 — Plan maestro y módulos impactados

Este mapa relaciona los requisitos del plan maestro vigente con los módulos de backend y frontend que los implementan, además de resaltar las migraciones y *feature flags* que controlan cada capacidad.【F:README.md†L931-L971】

## Requisito: Catálogo pro de dispositivos
- **Backend**
  - `backend/app/routers/inventory.py` gestiona altas, reservas y reportes del catálogo extendido con validación de motivos y paginación unificada.【F:backend/app/routers/inventory.py†L1-L156】
  - El modelo `Device` incorpora los campos avanzados (IMEI, serie, proveedor, garantía, etc.) que exige el plan maestro.【F:backend/app/models/__init__.py†L248-L326】
- **Frontend**
  - `frontend/src/modules/inventory/components/AdvancedSearch.tsx` ofrece filtros completos por IMEI/serie, proveedor, estado comercial y fechas, alineado con el catálogo pro.【F:frontend/src/modules/inventory/components/AdvancedSearch.tsx†L1-L160】
- **Migraciones asociadas**
  - `202502150003_catalog_pro_fields.py` crea los nuevos campos e índices de unicidad para dispositivos.【F:backend/alembic/versions/202502150003_catalog_pro_fields.py†L1-L86】
- **Flags relevantes**
  - El comportamiento depende de `Settings.enable_catalog_pro`, activado por `SOFTMOBILE_ENABLE_CATALOG_PRO` en la configuración corporativa.【F:backend/app/config.py†L224-L239】【F:.env.example†L10-L19】

## Requisito: Transferencias entre tiendas
- **Backend**
  - `backend/app/routers/transfers.py` controla el flujo SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA con reportes PDF y cabecera `X-Reason` obligatoria.【F:backend/app/routers/transfers.py†L1-L200】
- **Frontend**
  - `frontend/src/modules/operations/components/TransferOrders.tsx` permite crear, despachar, recibir y cancelar transferencias aplicando validaciones de motivo corporativo.【F:frontend/src/modules/operations/components/TransferOrders.tsx†L1-L160】
- **Migraciones asociadas**
  - `202502150004_transfer_orders.py` añade tablas `transfer_orders`, `transfer_order_items` y `store_memberships` con el catálogo de estados corporativos.【F:backend/alembic/versions/202502150004_transfer_orders.py†L1-L144】
- **Flags relevantes**
  - El router verifica `Settings.enable_transfers`, controlado por `SOFTMOBILE_ENABLE_TRANSFERS`.【F:backend/app/routers/transfers.py†L23-L25】【F:backend/app/config.py†L239-L249】【F:.env.example†L12-L18】

## Requisito: Compras y ventas con devoluciones
- **Backend**
  - `backend/app/routers/purchases.py` expone el flujo completo de órdenes de compra, recepciones parciales, devoluciones y exportaciones.【F:backend/app/routers/purchases.py†L1-L140】
  - `backend/app/routers/sales.py` cubre ventas, devoluciones y reportes PDF/Excel reutilizando el encabezado `X-Reason`.【F:backend/app/routers/sales.py†L1-L140】
- **Frontend**
  - `frontend/src/modules/operations/components/Purchases.tsx` consolida formularios, listados y exportaciones de compras con filtros avanzados.【F:frontend/src/modules/operations/components/Purchases.tsx†L1-L140】
  - `frontend/src/modules/operations/components/Sales.tsx` administra ventas, descuentos, métodos de pago y exportaciones desde la UI corporativa.【F:frontend/src/modules/operations/components/Sales.tsx†L1-L120】
- **Migraciones asociadas**
  - `202502150005_purchases_sales.py` crea las tablas de compras, devoluciones y ventas con catálogos de estatus y métodos de pago.【F:backend/alembic/versions/202502150005_purchases_sales.py†L1-L200】
- **Flags relevantes**
  - Ambos routers dependen de `Settings.enable_purchases_sales`, configurado mediante `SOFTMOBILE_ENABLE_PURCHASES_SALES`.【F:backend/app/routers/purchases.py†L24-L31】【F:backend/app/routers/sales.py†L23-L26】【F:backend/app/config.py†L249-L259】【F:.env.example†L13-L18】

## Requisito: Analítica avanzada y reportes oscuros
- **Backend**
  - `backend/app/routers/reports.py` centraliza los endpoints `/reports/analytics/*`, exportaciones PDF/CSV y controles de habilitación por *flag*.【F:backend/app/routers/reports.py†L442-L836】
- **Frontend**
  - `frontend/src/modules/analytics/components/AnalyticsBoard.tsx` consume las métricas de rotación, aging, comparativos, forecast y margen con descargas protegidas por motivo corporativo.【F:frontend/src/modules/analytics/components/AnalyticsBoard.tsx†L1-L158】
- **Migraciones asociadas**
  - `202502150006_security_analytics_sync.py` incorpora tablas de 2FA, sesiones activas y `sync_outbox`, soporte estructural requerido por la analítica avanzada y la auditoría fina.【F:backend/alembic/versions/202502150006_security_analytics_sync.py†L1-L84】
- **Flags relevantes**
  - El backend exige `Settings.enable_analytics_adv` y `Settings.enable_purchases_sales` antes de exponer los endpoints.【F:backend/app/routers/reports.py†L31-L33】【F:backend/app/config.py†L259-L269】

## Requisito: Seguridad y auditoría fina (2FA, sesiones, motivos)
- **Backend**
  - `backend/app/routers/security.py` gestiona provisión/activación de TOTP, revocación de sesiones y validación de motivos corporativos.【F:backend/app/routers/security.py†L1-L128】
- **Frontend**
  - `frontend/src/modules/security/components/TwoFactorSetup.tsx` habilita el flujo completo de 2FA, revocación de sesiones y validación de motivos ≥5 caracteres.【F:frontend/src/modules/security/components/TwoFactorSetup.tsx†L1-L160】
- **Migraciones asociadas**
  - `202502150006_security_analytics_sync.py` crea `user_totp_secrets` y `active_sessions`, imprescindibles para 2FA y auditoría de sesiones.【F:backend/alembic/versions/202502150006_security_analytics_sync.py†L16-L49】
  - `202503010013_audit_ui_table.py` y `202503010012_system_logs_tables.py` refuerzan la trazabilidad de auditoría corporativa.【F:backend/alembic/versions/202503010012_system_logs_tables.py†L1-L70】【F:backend/alembic/versions/202503010013_audit_ui_table.py†L1-L80】
- **Flags relevantes**
  - La disponibilidad de 2FA depende de `Settings.enable_2fa`, controlado por `SOFTMOBILE_ENABLE_2FA` (actualmente desactivado por defecto).【F:backend/app/routers/security.py†L18-L25】【F:backend/app/config.py†L268-L277】【F:.env.example†L14-L19】

## Requisito: Modo híbrido con cola `sync_outbox`
- **Backend**
  - `backend/app/services/sync.py` reintenta eventos, detecta discrepancias y registra sesiones de sincronización siguiendo la estrategia *last-write-wins*.【F:backend/app/services/sync.py†L1-L180】
- **Frontend**
  - `frontend/src/modules/sync/pages/SyncPage.tsx` expone controles de sincronización manual, panel de outbox y monitoreo de reintentos en tiempo real.【F:frontend/src/modules/sync/pages/SyncPage.tsx†L180-L301】
- **Migraciones asociadas**
  - `202502150006_security_analytics_sync.py` introduce `sync_outbox` y estado `PENDING/SENT/FAILED` usado por el servicio híbrido.【F:backend/alembic/versions/202502150006_security_analytics_sync.py†L51-L69】
  - `202503010015_sync_queue_tables.py` añade `sync_queue` y `sync_attempts` para la cola local avanzada.【F:backend/alembic/versions/202503010015_sync_queue_tables.py†L1-L71】
- **Flags relevantes**
  - El modo híbrido se gobierna con `Settings.enable_hybrid_prep`, ligado a `SOFTMOBILE_ENABLE_HYBRID_PREP`.【F:backend/app/services/sync.py†L24-L30】【F:backend/app/config.py†L277-L287】【F:.env.example†L15-L19】

## Dependencias de datos adicionales
- Las migraciones `202503010005_clientes_estructura_relaciones.py` y `202503010008_usuarios_estructura_roles.py` mantienen consistentes los módulos de clientes y usuarios que interactúan con compras/ventas y auditoría.【F:backend/alembic/versions/202503010005_clientes_estructura_relaciones.py†L1-L80】【F:backend/alembic/versions/202503010008_usuarios_estructura_roles.py†L1-L90】
- `202503010012_system_logs_tables.py` y `202503010014_cost_ledger.py` sostienen la trazabilidad corporativa necesaria para el monitoreo y la valuación de inventario en reportes ejecutivos.【F:backend/alembic/versions/202503010012_system_logs_tables.py†L1-L70】【F:backend/alembic/versions/202503010014_cost_ledger.py†L1-L80】

## Feature flags actuales y nuevas banderas sugeridas
- **Banderas vigentes**
  - El README resume los valores operativos de `SOFTMOBILE_ENABLE_*`, consistentes con la definición de `Settings` y el ejemplo de `.env` corporativo.【F:README.md†L931-L939】【F:backend/app/config.py†L224-L304】【F:.env.example†L10-L19】
- **Banderas adicionales sugeridas**
  - `SOFTMOBILE_ENABLE_OBSERVABILITY_STACK`: permitiría activar gradualmente integraciones de monitoreo centralizado y tableros externos sin afectar instalaciones actuales, alineado con la prioridad de observabilidad para despliegues en nube.【F:docs/evaluacion_requerimientos.md†L23-L24】【F:docs/evaluacion_requerimientos.md†L71-L72】
  - `SOFTMOBILE_ENABLE_ANALYTICS_COMPARATIVE_EXPORTS`: aislaría la futura ampliación de analítica comparativa y nuevos formatos de exportación planificados para la versión 2.3.【F:docs/evaluacion_requerimientos.md†L74-L75】【F:README.md†L970-L970】
  - `SOFTMOBILE_ENABLE_REMOTE_SUPPORT`: facilitaría documentar y desplegar gradualmente los protocolos de soporte remoto para 2FA y sincronización, permitiendo activarlos por cliente mientras se completan las guías corporativas.【F:docs/evaluacion_requerimientos.md†L73-L74】【F:docs/evaluacion_requerimientos.md†L86-L87】【F:README.md†L971-L971】

## Próximos pasos coordinados
1. Definir responsables y alcance técnico de la capa de observabilidad antes de habilitar el *flag* propuesto de monitoreo en entornos piloto.【F:docs/evaluacion_requerimientos.md†L89-L90】
2. Diseñar la ampliación de analítica comparativa (nuevos exports y métricas inter-sucursal) bajo un *feature flag* específico, reutilizando los routers y componentes listados anteriormente.【F:README.md†L970-L971】【F:backend/app/routers/reports.py†L442-L836】
3. Elaborar y publicar los manuales de soporte remoto (2FA + sincronización) vinculados al nuevo *flag* para garantizar adopción controlada en franquicias y socios estratégicos.【F:docs/evaluacion_requerimientos.md†L73-L74】【F:docs/evaluacion_requerimientos.md†L86-L87】
