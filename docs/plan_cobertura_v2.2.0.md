# Plan de cobertura funcional — Softmobile 2025 v2.2.0

Este documento consolida la cobertura vigente descrita en `README.md` y `AGENTS.md` y lista las actividades de seguimiento necesarias para preservar la versión v2.2.0 sin introducir regresiones.

## 1. Auditoría y recordatorios de seguridad

**Requisito declarado**
- El README indica que la bitácora permite exportar CSV/PDF con estado de acuse, generar recordatorios automáticos con snooze y registrar acuses manuales para alertas críticas.【F:README.md†L31-L33】

**Situación actual**
- El backend ya publica `/audit/reminders`, `/audit/acknowledgements` y `/reports/audit/pdf`, con métricas que distinguen alertas pendientes vs. atendidas y pruebas `pytest` en verde.【F:backend/app/routers/audit.py†L19-L140】【F:backend/app/routers/reports.py†L190-L248】【F:backend/tests/test_audit_logs.py†L1-L128】
- `frontend/src/api.ts` expone helpers para recordatorios, acuses y PDF con cabecera `X-Reason`, listos para reutilizarse en la UI.【F:frontend/src/api.ts†L4323-L4350】
- `frontend/src/modules/security/components/AuditLog.tsx` ya consume recordatorios, acuses y descargas con motivo corporativo, mostrando badges en vivo, snooze de 10 minutos y prompts para `X-Reason`.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L210】【F:frontend/src/modules/security/components/AuditLog.tsx†L520-L706】

**Acciones requeridas**
- **Monitoreo continuo**
  1. Validar en QA que los badges de pendientes/atendidas, el snooze y las descargas con motivo respondan correctamente tras cada despliegue de backend.
  2. Registrar en `docs/bitacora_pruebas_2025-10-14.md` los hallazgos multiusuario y auditar trimestralmente los umbrales `threshold_minutes` y `min_occurrences` para confirmar que priorizan alertas críticas.
  3. Auditar los roles con acceso a auditoría y documentar la revisión junto con los resultados de `pytest`.
- **Pruebas y calidad**
  4. ✅ `frontend/src/modules/security/components/__tests__/AuditLog.test.tsx` cubre recordatorios, descargas con `X-Reason` y acuses simulando los servicios de `api.ts` vía Vitest/RTL; mantener los escenarios de snooze y acuses agregando datos sintéticos si surgen nuevas categorías.【F:frontend/src/modules/security/components/__tests__/AuditLog.test.tsx†L1-L242】
  5. ✅ `frontend/package.json` incorpora `npm run test` y la bitácora `docs/bitacora_pruebas_2025-10-14.md` registra las ejecuciones junto a `pytest`.
- **Documentación y seguimiento**
  6. Mantener README, esta guía y `AGENTS.md` alineados con el estado real de Seguridad.
- **Observabilidad**
  7. ✅ `/monitoring/metrics` queda disponible para roles `ADMIN`, exponiendo contadores de acuses, fallos e hit/miss de cache definidos en `backend/app/telemetry.py`; consulta su salida después de cada corrida de pruebas para garantizar coherencia con los datos mostrados en Seguridad.
  8. Analizar la factibilidad de exponer métricas Prometheus dedicadas (`audit_acknowledgements_total`, `audit_reminders_pending`) aprovechando el módulo `telemetry.py`.
- **Optimización sugerida**
  9. ✅ Se añadió un cache TTL de 60 segundos para `crud.get_persistent_audit_alerts` con invalidación automática cuando se inserta un nuevo log o acuse, evitando consultas repetitivas en ráfagas intensas.

## 2. Exportación CSV con cabecera obligatoria

**Requisito declarado**
- `AGENTS.md` establece que las operaciones sensibles deben exigir cabecera `X-Reason` ≥ 5 caracteres.【F:AGENTS.md†L8-L14】

**Situación actual**
- Se confirmó que la exportación CSV sigue siendo una operación sensible: las pruebas envían `X-Reason` y la respuesta 400 quedó resuelta.【F:backend/tests/test_audit_logs.py†L27-L67】
- `AuditLog.tsx` solicita el motivo corporativo antes de exportar CSV/PDF y propaga el header a los servicios de reporte.【F:frontend/src/modules/security/components/AuditLog.tsx†L520-L706】

**Acciones requeridas**
- **Pruebas y calidad**
  1. ✅ La suite `AuditLog.test.tsx` verifica motivos menores a 5 caracteres, cabeceras `X-Reason` y toasts informativos al exportar CSV.
- **Documentación y métricas**
  2. Mantener README y la bitácora con ejemplos de motivos utilizados y resultados de exportaciones en QA.
- **Optimización sugerida**
  3. Registrar métricas de uso de exportación (contador Prometheus o log estructurado) para analizar impacto y ajustar límites `limit`/`le` si es necesario.

## 3. Consolidación y optimización del módulo de métricas

**Requisito declarado**
- El tablero global debe distinguir alertas pendientes vs. atendidas en `/reports/metrics` y reflejar acuses en `GlobalMetrics.tsx`.【F:README.md†L31-L33】

**Situación actual**
- `compute_inventory_metrics` ya devuelve `pending_count`, `acknowledged_count` y metadatos de acuse sin errores; las pruebas backend garantizan la coherencia de recordatorios y resúmenes.【F:backend/app/crud.py†L4789-L5034】【F:backend/tests/test_audit_logs.py†L55-L128】
- `GlobalMetrics.tsx` ahora muestra pendientes/atendidas, último acuse registrado y un enlace directo hacia Seguridad cuando existen alertas por atender.【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L1-L312】

**Acciones requeridas**
- **Pruebas y validación UX**
  1. ✅ `frontend/src/modules/dashboard/components/__tests__/GlobalMetrics.test.tsx` valida badges de pendientes/atendidas, último acuse y el enlace a Seguridad condicionado por `pending_count`.【F:frontend/src/modules/dashboard/components/__tests__/GlobalMetrics.test.tsx†L1-L117】
- **Documentación**
  2. Capturar evidencia visual actualizada del tablero y mantener README/bitácora alineados con la versión vigente.
- **Optimización sugerida**
  3. Evaluar un caché ligero (p.ej. `st.cache` en servicios) si `/reports/metrics` comienza a recibir más de 10 consultas por minuto.
  4. Añadir memoización ligera (React `useMemo`) en `GlobalMetrics.tsx` si se detectan cuellos de botella con datasets voluminosos.

## 4. Documentación operativa y bitácoras

**Requisito declarado**
- `docs/evaluacion_requerimientos.md` debe reflejar las brechas vigentes y guiar la iteración siguiente, mientras que la bitácora de control del README debe coincidir con el estado real del sistema.【F:AGENTS.md†L96-L106】【F:docs/evaluacion_requerimientos.md†L1-L38】

**Situación actual**
- `docs/evaluacion_requerimientos.md` y `docs/verificacion_integral_v2.2.0.md` reflejan la cobertura completa de auditoría/métricas y listan únicamente mejoras evolutivas.
- El README presenta el estado consolidado del módulo de Seguridad y enlaza a esta guía como referencia operativa.【F:README.md†L31-L70】

**Acciones requeridas**
- **Documentación inmediata**
  1. ✅ `README.md`, `AGENTS.md`, esta guía y `docs/verificacion_integral_v2.2.0.md` reflejan la cobertura completa de Seguridad y métricas con referencias a las nuevas pruebas.
  2. ✅ `docs/bitacora_pruebas_2025-10-14.md` registra `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test` con resultados recientes.
- **Seguimiento operativo**
  3. Registrar en la bitácora del README los avances de frontend (por ejemplo, "Se habilitaron recordatorios en UI" con fecha y hash) para mantener trazabilidad.
  4. Mantener visible el checklist recurrente (leer README/AGENTS, ejecutar pruebas, validar UI) en esta guía y en `docs/prompts_operativos_v2.2.0.md`.
- **Optimización sugerida**
  5. Automatizar un pre-push hook que verifique cambios en `frontend/src/modules/security/components/AuditLog.tsx` y exija actualizar esta documentación antes de permitir subir commits.
  6. Establecer recordatorios automáticos (por ejemplo, Git pre-push hook) que disparen `pytest` y validen que la documentación clave se mantenga sincronizada.

## 5. Seguimiento de pruebas y calidad

**Requisito declarado**
- `AGENTS.md` exige que `pytest` concluya en verde y que se registren las brechas detectadas tras cada ejecución.【F:AGENTS.md†L4-L11】

**Situación actual**
- `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test` se ejecutan en verde, validando recordatorios, acuses y métricas con cobertura backend/frontend documentada.【b3d853†L1-L24】【c13833†L1-L14】
- `docs/bitacora_pruebas_2025-10-14.md` registra las corridas recientes con fecha, resultado y hash de commit, alineadas al checklist corporativo.【F:docs/bitacora_pruebas_2025-10-14.md†L1-L80】

**Acciones requeridas**
- **Pruebas automatizadas**
  1. ✅ `pytest` y `npm --prefix frontend run test` quedaron integrados al flujo y documentados para auditoría continua.
  2. ✅ La bitácora incorpora la evidencia de las corridas backend/frontend con fecha, resultado y hash de commit.
- **Checklist de entrega**
  3. Conservar el checklist al final de este documento y ampliarlo cuando se agreguen nuevos módulos (p.ej. monitoreo multi-sucursal).
- **Optimización sugerida**
  4. Configurar CI para ejecutar `pytest` y `npm --prefix frontend test` en paralelo, agregando métricas de cobertura de auditoría.
  5. Integrar `pytest -k audit` en CI para acelerar validaciones y añadir cobertura mínima esperada en el reporte (≥90 % en routers de auditoría).

---

Completar los puntos anteriores asegurará que la implementación coincida con la documentación y restablecerá las pruebas fallidas en la versión v2.2.0.

## Checklist de control previo a la entrega

1. Leer nuevamente `README.md`, `AGENTS.md`, `docs/evaluacion_requerimientos.md` y este plan para confirmar que no se omitió ningún pendiente.
2. Verificar que los endpoints implementados (`/audit/reminders`, `/audit/acknowledgements`, `/reports/audit/pdf`, `/reports/metrics`) respondan correctamente mediante `pytest` y pruebas manuales con `curl` incluyendo la cabecera `X-Reason` cuando aplique.
3. Ejecutar `pytest` y documentar el resultado en `docs/bitacora_pruebas_2025-10-14.md` junto con la fecha y hash de commit.
4. Correr `npm --prefix frontend test` (o el comando equivalente documentado) validando que los componentes `AuditLog` y `GlobalMetrics` manejen pendientes/atendidas sin errores.
5. Revisar desde el frontend la sección Seguridad para confirmar que recordatorios, acuses, snooze y descargas PDF funcionen con el tema oscuro.
6. Actualizar el README con el estado real de auditoría/metricas y registrar en la bitácora operativa los ajustes realizados.
7. Confirmar que no se modificó la versión 2.2.0 en ningún archivo y que los feature flags permanecen con los valores establecidos en el mandato.
