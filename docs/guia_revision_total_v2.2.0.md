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

### Mejoras sugeridas

- Integrar reportes de cobertura en la bitácora para asegurar >90 % en routers de auditoría y métricas.
- Añadir un tablero rápido (por ejemplo, `docs/dashboard_ci.md`) con el historial de corridas para auditoría interna.

---

Sigue esta guía en paralelo al `docs/plan_cobertura_v2.2.0.md` y actualiza el estado en `docs/verificacion_integral_v2.2.0.md` tras completar cada bloque. Mantén la versión 2.2.0 intacta en todos los archivos.
