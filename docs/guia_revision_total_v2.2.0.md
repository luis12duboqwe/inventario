# Guía de revisión y acciones pendientes — Softmobile 2025 v2.2.0

Este documento consolida los hallazgos detectados al comparar el estado real del código con los requisitos descritos en el README y en el mandato operativo (`AGENTS.md`). Se enumeran los pasos concretos para implementar lo faltante, junto con ideas de optimización y pruebas recomendadas, manteniendo estrictamente la versión 2.2.0.

## 1. Auditoría corporativa y recordatorios

- **Referencia funcional**: el README anuncia exportaciones CSV/PDF con acuses, recordatorios automáticos y registro manual de notas en Seguridad.【F:README.md†L31-L33】 El mandato exige cabecera `X-Reason` en operaciones sensibles como el POS y auditoría.【F:AGENTS.md†L8-L14】
- **Estado actual**:
  - El backend ofrece `/audit/reminders`, `/audit/acknowledgements`, `/reports/audit/pdf` y métricas enriquecidas con estado de acuse; `pytest` valida recordatorios, acuses y descargas exitosas.【F:backend/app/routers/audit.py†L18-L120】【F:backend/app/routers/reports.py†L25-L120】【F:backend/tests/test_audit_logs.py†L1-L120】
  - `AuditLog.tsx` consume los servicios, muestra badges en vivo, snooze corporativo y descargas con motivo obligatorio; `frontend/src/modules/security/components/__tests__/AuditLog.test.tsx` cubre recordatorios, exportaciones y acuses con validaciones de `X-Reason`.

### Pasos de validación continua

1. Ejecutar `npm --prefix frontend run test` tras cada cambio relacionado con Seguridad para asegurar que los flujos de recordatorios, descargas y acuses permanecen estables.
2. Revisar manualmente el módulo de Seguridad en ambientes multiusuario verificando badges, snooze y toasts en vivo; documentar hallazgos en la bitácora corporativa.
3. Mantener README, `AGENTS.md` y esta guía alineados con los motivos corporativos y escenarios representativos detectados en QA.
4. Consultar `/monitoring/metrics` con credenciales ADMIN tras cada iteración para validar que los contadores de acuses, fallos e hit/miss del cache coinciden con los eventos registrados en Seguridad.
  - El router `audit.py` sólo publica `/audit/logs` y `/audit/logs/export.csv`; faltan rutas para recordatorios y acuses, y la exportación CSV exige `X-Reason`, provocando un 400 en las pruebas corporativas.【F:backend/app/routers/audit.py†L20-L68】【F:backend/tests/test_audit_logs.py†L33-L70】
  - Las utilidades de auditoría no incluyen `entity_id` en los destacados, lo que impide vincular acuses y rompe las métricas globales.【F:backend/app/utils/audit.py†L54-L105】【F:backend/app/crud.py†L1858-L1935】
  - El componente `AuditLog.tsx` duplica `buildCurrentFilters`, usa `useRef` sin importarlo e invoca `loadReminders`/`snoozedUntil` sin definirlos, dejando incompleto el UI prometido.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】

### Pasos obligatorios

1. **Backend**
   - Añadir en `backend/app/routers/audit.py` los endpoints `GET /audit/reminders` y `POST /audit/acknowledgements`, delegando en `crud.get_pending_audit_alerts`/`crud.acknowledge_audit_alert` y aplicando `require_reason` sólo en mutaciones.【F:backend/app/routers/audit.py†L20-L68】
   - Exponer `GET /reports/audit/pdf` en `backend/app/routers/reports.py`, reutilizando `services.audit.render_audit_pdf` para alinear la exportación con el README.【F:backend/app/services/audit.py†L1-L100】
   - Extender `backend/app/utils/audit.py.HighlightEntry` con `entity_id`, `acknowledged_at`, `acknowledged_by` y ajustar los consumidores en `crud` para devolver resúmenes consistentes.【F:backend/app/utils/audit.py†L54-L105】【F:backend/app/crud.py†L1858-L1935】
   - Decidir la política del header `X-Reason` para `/audit/logs/export.csv` y reflejarla en las pruebas: si se mantiene obligatorio, actualizar los tests y fixtures; si se elimina, retirar la dependencia en el router y documentarlo.【F:backend/app/routers/audit.py†L42-L68】【F:backend/tests/test_audit_logs.py†L33-L70】

2. **Frontend**
   - Completar `AuditLog.tsx`: importar `useRef`, consolidar la función `buildCurrentFilters` en una sola definición, implementar `loadReminders`, estados de snooze y acciones de acuse apuntando a las nuevas rutas, y mostrar badges de pendiente/atendida con botones de descarga CSV/PDF.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】
   - Incorporar en `frontend/src/api.ts` funciones para `fetchAuditReminders`, `acknowledgeAuditAlert` y `downloadAuditPdf`, propagando `X-Reason` cuando corresponda.【F:frontend/src/api.ts†L941-L1468】

3. **Pruebas**
   - Actualizar `backend/tests/test_audit_logs.py` para cubrir recordatorios y acuses tras definir la política de `X-Reason`, garantizando que `/reports/audit` y `/reports/audit/pdf` respondan en verde.【F:backend/tests/test_audit_logs.py†L33-L82】
   - Añadir pruebas de interfaz (Vitest) que confirmen la aparición de botones de acuse/snooze y la descarga de PDF/CSV.

4. **Documentación**
   - Sincronizar README y `docs/evaluacion_requerimientos.md` tan pronto como los endpoints se publiquen, retirando las advertencias de esta guía.

### Mejoras sugeridas

- Registrar métricas Prometheus para `audit_acknowledgements` y cachear brevemente los recordatorios si el número de alertas supera 200 por minuto.
- Exponer una cola interna para reenviar recordatorios fallidos con backoff exponencial y notas en la bitácora.

## 2. Métricas ejecutivas y tablero global

- **Referencia funcional**: el README indica que `/reports/metrics` diferencia alertas pendientes vs. atendidas y que el tablero muestra destacados listos para responder.【F:README.md†L31-L39】
- **Estado actual**:
  - El backend entrega `pending_count`, `acknowledged_count`, metadatos de acuse y resúmenes consistentes; las pruebas de auditoría garantizan la integridad de los datos.【F:backend/app/crud.py†L1856-L1943】【F:backend/tests/test_audit_logs.py†L69-L118】
  - `GlobalMetrics.tsx` refleja pendientes/atendidas, último acuse y acceso directo a Seguridad cuando existen pendientes; `frontend/src/modules/dashboard/components/__tests__/GlobalMetrics.test.tsx` asegura el comportamiento.

### Pasos de validación continua

1. Ejecutar `npm --prefix frontend run test` y revisar el tablero con datos de ejemplo para confirmar que badges, resumen de acuses y enlace a Seguridad responden correctamente.
2. Monitorear el desempeño de gráficos y, si la carga supera los 2 MB, evaluar caches o segmentación de datos.
3. Documentar cualquier ajuste visual en README y capturar evidencia cuando se actualicen estilos o datasets.
  - `compute_inventory_metrics` intenta combinar acuses, pero falla por la ausencia de `entity_id` en los destacados y por no incluir datos de reconocimiento en la respuesta, generando un `KeyError` en las pruebas de inventario.【F:backend/app/crud.py†L1858-L1935】
  - `GlobalMetrics.tsx` asume que `audit_alerts.highlights` contiene metadatos para mostrar la severidad y fecha, pero no puede diferenciar pendientes/atendidas ni mostrar quién realizó el acuse.【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L34-L148】

### Pasos obligatorios

1. Ajustar `audit_utils.HighlightEntry` y la estructura retornada por `compute_inventory_metrics` para añadir campos `entity_id`, `acknowledged_at`, `acknowledged_by_name`, `pending_count` y `acknowledged_count`.【F:backend/app/utils/audit.py†L54-L105】【F:backend/app/crud.py†L1858-L1935】
2. Crear o actualizar pruebas (`backend/tests/test_inventory_flow.py` o nuevas) que validen el conteo diferenciado de alertas pendientes/atendidas al consumir `/reports/metrics`.
3. Modificar `GlobalMetrics.tsx` para mostrar badges de estado, totales de pendientes vs. atendidas y enlaces rápidos a Seguridad, aprovechando `useMemo` para evitar renders costosos.【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L34-L148】
4. Documentar el contrato actualizado en README y en esta guía, registrando la corrida de `pytest` que confirma la corrección.

### Mejoras sugeridas

- Agregar selectores de rango temporal en el tablero y permitir exportación directa de métricas consolidadas desde el frontend.
- Implementar almacenamiento en caché por tienda para los cálculos más pesados, invalidándolos cuando se registre un acuse.

## 3. Bitácora operativa y pruebas recurrentes

- **Referencia funcional**: el mandato requiere ejecutar `pytest`, revisar README/AGENTS en cada iteración y mantener bitácoras actualizadas.【F:AGENTS.md†L4-L11】【F:docs/evaluacion_requerimientos.md†L1-L39】
- **Estado actual**: `docs/bitacora_pruebas_2025-10-14.md` registra las corridas de `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test`, incluyendo resultados y hash corporativo.

### Pasos de validación continua

1. Actualizar la bitácora tras cada ejecución relevante, indicando fecha, responsable y estado de las pruebas backend/frontend.
2. Mantener en README el resumen operativo de las últimas corridas y hallazgos multiusuario.
3. Automatizar (pre-push/CI) la ejecución de `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test` para evitar regresiones.
- **Estado actual**: la suite falla en auditoría y métricas, y no existe un registro de corridas reciente que documente los intentos en rojo.

### Pasos obligatorios

1. Crear `docs/bitacora_pruebas_2025-10-14.md` (o actualizarlo si ya existe) con fecha, hash de commit, comando ejecutado y resultado de `pytest`/`npm test`.
2. Registrar en la bitácora operativa del README los errores detectados (`test_audit_filters_and_csv_export`, `test_inventory_flow`) y añadir una nota cuando queden resueltos.【F:README.md†L20-L43】
3. Automatizar un recordatorio (pre-push hook o tarea CI) que verifique este archivo y ejecute `pytest -k audit` antes de permitir un push a la rama principal.

### Mejoras sugeridas

- Integrar reportes de cobertura en la bitácora para asegurar >90 % en routers de auditoría y métricas.
- Añadir un tablero rápido (por ejemplo, `docs/dashboard_ci.md`) con el historial de corridas para auditoría interna.

---

Sigue esta guía en paralelo al `docs/plan_cobertura_v2.2.0.md` y actualiza el estado en `docs/verificacion_integral_v2.2.0.md` tras completar cada bloque. Mantén la versión 2.2.0 intacta en todos los archivos.
