# Guía de revisión y acciones pendientes — Softmobile 2025 v2.2.0

Este documento consolida los hallazgos detectados al comparar el estado real del código con los requisitos descritos en el README y en el mandato operativo (`AGENTS.md`). Se enumeran los pasos concretos para implementar lo faltante, junto con ideas de optimización y pruebas recomendadas, manteniendo estrictamente la versión 2.2.0.

## 1. Auditoría corporativa y recordatorios

- **Referencia funcional**: el README anuncia exportaciones CSV/PDF con acuses, recordatorios automáticos y registro manual de notas en Seguridad.【F:README.md†L31-L33】 El mandato exige cabecera `X-Reason` en operaciones sensibles como el POS y auditoría.【F:AGENTS.md†L8-L14】
- **Estado actual**:
  - El backend ya ofrece `/audit/reminders`, `/audit/acknowledgements`, `/reports/audit/pdf` y métricas enriquecidas con estado de acuse; las pruebas `pytest` validan recordatorios, acuses y descargas exitosas.【F:backend/app/routers/audit.py†L18-L120】【F:backend/app/routers/reports.py†L25-L120】【F:backend/tests/test_audit_logs.py†L1-L120】
  - `AuditLog.tsx` importa `useRef`, pero mantiene una definición duplicada de `buildCurrentFilters`, invoca funciones inexistentes (`loadReminders`, `snoozedUntil`) y no consume los nuevos servicios de `api.ts`, por lo que la UI sigue sin mostrar recordatorios ni acuses.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】

### Pasos obligatorios

1. **Frontend**
   - Consolidar `buildCurrentFilters` en una sola definición, crear `loadReminders` y `handleAcknowledge` con `useCallback`, y consumir `getAuditReminders`/`acknowledgeAuditAlert` para poblar tablas y badges de pendiente/atendida.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】【F:frontend/src/api.ts†L1800-L1889】
   - Implementar temporizadores (`reminderIntervalRef`, `snoozeTimeoutRef`) y un control de snooze que pause recordatorios 10 min, actualizando toasts con el motivo registrado.
   - Mostrar acciones de descarga CSV/PDF solicitando el motivo corporativo (`X-Reason`) antes de invocar `exportAuditLogsCsv` o `downloadAuditPdf`.

2. **Pruebas**
   - Crear pruebas Vitest/React Testing Library que simulen cargas de recordatorios, registro de acuses (HTTP 201) y descargas con motivo inválido/valido, mockeando los servicios de `api.ts`.

3. **Documentación**
   - Actualizar README y `docs/evaluacion_requerimientos.md` cuando la UI expose recordatorios/acuses, documentando atajos, motivos sugeridos y resultados de pruebas.

### Mejoras sugeridas

- Registrar métricas Prometheus para `audit_acknowledgements` y cachear brevemente los recordatorios si el número de alertas supera 200 por minuto.
- Exponer una cola interna para reenviar recordatorios fallidos con backoff exponencial y notas en la bitácora.

## 2. Métricas ejecutivas y tablero global

- **Referencia funcional**: el README indica que `/reports/metrics` diferencia alertas pendientes vs. atendidas y que el tablero muestra destacados listos para responder.【F:README.md†L31-L39】
- **Estado actual**:
  - El backend ya entrega `pending_count`, `acknowledged_count`, metadatos de acuse y resúmenes consistentes; las pruebas de auditoría garantizan la integridad de los datos.【F:backend/app/crud.py†L1856-L1943】【F:backend/tests/test_audit_logs.py†L69-L118】
  - `GlobalMetrics.tsx` sigue mostrando únicamente el conteo de críticas/preventivas sin reflejar los nuevos campos ni accesos directos a Seguridad.【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L1-L148】

### Pasos obligatorios

1. Extender `GlobalMetrics.tsx` para renderizar `pending_count`/`acknowledged_count`, mostrar el último `acknowledged_by_name` y añadir un enlace hacia Seguridad cuando existan pendientes.【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L1-L148】【F:backend/app/crud.py†L1856-L1943】
2. Utilizar `useMemo` para derivar resúmenes y evitar renders costosos cuando sólo cambian métricas no relacionadas.
3. Documentar el nuevo comportamiento en README y capturar evidencias visuales una vez integrado.

### Mejoras sugeridas

- Agregar selectores de rango temporal en el tablero y permitir exportación directa de métricas consolidadas desde el frontend.
- Implementar almacenamiento en caché por tienda para los cálculos más pesados, invalidándolos cuando se registre un acuse.

## 3. Bitácora operativa y pruebas recurrentes

- **Referencia funcional**: el mandato requiere ejecutar `pytest`, revisar README/AGENTS en cada iteración y mantener bitácoras actualizadas.【F:AGENTS.md†L4-L11】【F:docs/evaluacion_requerimientos.md†L1-L39】
- **Estado actual**: `pytest` concluye en verde, pero aún no se registran corridas de pruebas de frontend ni existe una bitácora unificada de comandos.

### Pasos obligatorios

1. Actualizar/crear `docs/bitacora_pruebas_2025-10-14.md` anotando fecha, hash y resultado de `pytest` y `npm --prefix frontend test`.
2. Registrar en la bitácora operativa del README los avances de la UI (activación de recordatorios, badges, exportación con motivo) para mantener trazabilidad.【F:README.md†L16-L40】
3. Configurar un recordatorio interno (pre-push hook o tarea CI) que valide `pytest` y las pruebas de frontend antes de aceptar nuevos commits.

### Mejoras sugeridas

- Integrar reportes de cobertura en la bitácora para asegurar >90 % en routers de auditoría y métricas.
- Añadir un tablero rápido (por ejemplo, `docs/dashboard_ci.md`) con el historial de corridas para auditoría interna.

---

Sigue esta guía en paralelo al `docs/plan_cobertura_v2.2.0.md` y actualiza el estado en `docs/verificacion_integral_v2.2.0.md` tras completar cada bloque. Mantén la versión 2.2.0 intacta en todos los archivos.
