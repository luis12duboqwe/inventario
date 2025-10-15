# Plan de cobertura funcional — Softmobile 2025 v2.2.0

Este documento resume las brechas detectadas entre lo descrito en `README.md` y `AGENTS.md` y la implementación actual. Sirve como guía explícita para completar los faltantes sin modificar la versión v2.2.0.

## 1. Auditoría y recordatorios de seguridad

**Requisito declarado**
- El README indica que la bitácora permite exportar CSV/PDF con estado de acuse, generar recordatorios automáticos con snooze y registrar acuses manuales para alertas críticas.【F:README.md†L31-L33】

**Situación actual**
- El backend ya publica `/audit/reminders`, `/audit/acknowledgements` y `/reports/audit/pdf`, con métricas que distinguen alertas pendientes vs. atendidas y pruebas `pytest` en verde.【F:backend/app/routers/audit.py†L18-L120】【F:backend/app/routers/reports.py†L25-L120】【F:backend/tests/test_audit_logs.py†L1-L120】
- `frontend/src/api.ts` expone helpers para recordatorios, acuses y PDF con cabecera `X-Reason`, listos para reutilizarse en la UI.【F:frontend/src/api.ts†L1820-L1889】
- `frontend/src/modules/security/components/AuditLog.tsx` sigue duplicando `buildCurrentFilters`, invoca `loadReminders`/`snoozedUntil` sin definirlos y no consume los nuevos servicios, por lo que la funcionalidad permanece oculta en la interfaz.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】

**Acciones requeridas**
- **Frontend**
  1. Refactorizar `AuditLog.tsx` para consolidar `buildCurrentFilters`, crear `loadReminders`/`handleAcknowledge` con `useCallback`, y aprovechar los helpers `getAuditReminders`, `acknowledgeAuditAlert` y `downloadAuditPdf`.
  2. Implementar temporizadores con `useRef` (`reminderIntervalRef`, `snoozeTimeoutRef`) que administren intervalos de 60 s para recordatorios y snooze de 10 min, actualizando badges de pendiente/atendida.
  3. Renderizar tarjetas/resúmenes que muestren `pending_count`, `acknowledged_count`, últimos motivos y un CTA para abrir Seguridad cuando haya alertas críticas.
- **Pruebas y calidad**
  4. Añadir pruebas Vitest/React Testing Library que simulen la carga de recordatorios, la ejecución de `acknowledge` (HTTP 201) y el flujo de descarga CSV/PDF, mockeando los servicios de `api.ts`.
  5. Documentar en `package.json` el comando de pruebas de UI y registrarlo junto con `pytest` en la bitácora `docs/bitacora_pruebas_2025-10-14.md`.
- **Documentación y seguimiento**
  6. Actualizar README y esta guía cuando el frontend exponga recordatorios/acuses, detallando los atajos de teclado y la política de motivos en descargas.
- **Optimización sugerida**
  7. Evaluar un cache TTL corto (ej. `functools.lru_cache`) para `crud.get_persistent_audit_alerts` si la frecuencia de consulta supera 5 por minuto, invalidándolo cuando se registre un acuse nuevo.

## 2. Exportación CSV con cabecera obligatoria

**Requisito declarado**
- `AGENTS.md` establece que las operaciones sensibles deben exigir cabecera `X-Reason` ≥ 5 caracteres.【F:AGENTS.md†L8-L14】

**Situación actual**
- Se confirmó que la exportación CSV sigue siendo una operación sensible: las pruebas envían `X-Reason` y la respuesta 400 quedó resuelta.【F:backend/tests/test_audit_logs.py†L27-L67】
- El frontend aún no envía motivos personalizados al descargar CSV/PDF desde `AuditLog.tsx`, por lo que la interacción depende de valores por defecto del helper `exportAuditLogsCsv`.

**Acciones requeridas**
- **Política y UX**
  1. Mostrar un modal o prompt en `AuditLog.tsx` para capturar el motivo corporativo antes de exportar, reutilizando el texto por defecto cuando el usuario no edite el campo.
- **Implementación técnica**
  2. Garantizar que las descargas desde la UI propaguen el motivo ingresado (`X-Reason`) tanto en CSV como en PDF y manejen errores 400/409 con toasts descriptivos.
  3. Validar en Vitest que el componente envía el header correcto y reintenta en caso de motivos menores a 5 caracteres.
- **Documentación y métricas**
  4. Actualizar README con un ejemplo `curl` que incluya la cabecera y documentar en esta guía la plantilla sugerida para motivos (p.ej. `Revision auditoria {fecha}`).
  5. Registrar en la bitácora cualquier ajuste de límites `limit`/`le` y monitorear con logs estructurados el uso de exportaciones.

## 3. Consolidación y optimización del módulo de métricas

**Requisito declarado**
- El tablero global debe distinguir alertas pendientes vs. atendidas en `/reports/metrics` y reflejar acuses en `GlobalMetrics.tsx`.【F:README.md†L31-L33】

**Situación actual**
- `crud.get_dashboard_metrics` ya devuelve `pending_count`, `acknowledged_count` y metadatos de acuse sin errores; las pruebas backend garantizan la coherencia de recordatorios y resúmenes.【F:backend/app/crud.py†L1856-L1943】【F:backend/tests/test_audit_logs.py†L69-L118】
- `GlobalMetrics.tsx` continúa mostrando sólo el conteo de críticas/preventivas y no aprovecha la información de acuses para badges y llamadas a la acción.

**Acciones requeridas**
- **Frontend**
  1. Extender el estado `auditAlerts` para renderizar totales pendientes/atendidas, mostrar el último `acknowledged_by_name` y proveer un acceso directo a Seguridad.
  2. Utilizar `useMemo` para derivar resúmenes y evitar renders costosos cuando únicamente cambian métricas ajenas a auditoría.
- **Documentación y pruebas**
  3. Incorporar pruebas Vitest que validen el renderizado condicional de badges y los enlaces cuando haya pendientes.
  4. Actualizar README y esta guía con capturas/indicaciones del nuevo tablero una vez desplegado.
- **Optimización sugerida**
  5. Evaluar un caché ligero (p.ej. `st.cache` en servicios) si `/reports/metrics` comienza a recibir más de 10 consultas por minuto.

## 4. Documentación operativa y bitácoras

**Requisito declarado**
- `docs/evaluacion_requerimientos.md` debe reflejar las brechas vigentes y guiar la iteración siguiente, mientras que la bitácora de control del README debe coincidir con el estado real del sistema.【F:AGENTS.md†L96-L106】【F:docs/evaluacion_requerimientos.md†L1-L38】

**Situación actual**
- `docs/evaluacion_requerimientos.md` y `docs/verificacion_integral_v2.2.0.md` ya reflejan que el backend está completo y que la deuda se concentra en el frontend de Seguridad.【F:docs/evaluacion_requerimientos.md†L1-L54】【F:docs/verificacion_integral_v2.2.0.md†L1-L210】
- El README señala explícitamente que la UI de auditoría sigue pendiente, orientando a los desarrolladores hacia esta guía.【F:README.md†L24-L40】

**Acciones requeridas**
- **Documentación inmediata**
  1. Actualizar estos archivos en cuanto `AuditLog.tsx` y `GlobalMetrics.tsx` incorporen recordatorios/acuse, cambiando los estados de ⚠️/⚠️ a ✅ y documentando las pruebas ejecutadas.
  2. Crear/actualizar `docs/bitacora_pruebas_2025-10-14.md` registrando comandos (`pytest`, `npm --prefix frontend test`) y resultados cada vez que se valide Seguridad.
- **Seguimiento operativo**
  3. Registrar en la bitácora del README los avances de frontend (por ejemplo, "Se habilitaron recordatorios en UI" con fecha y hash) para mantener trazabilidad.
  4. Mantener visible el checklist recurrente (leer README/AGENTS, ejecutar pruebas, validar UI) en esta guía y en `docs/prompts_operativos_v2.2.0.md`.
- **Optimización sugerida**
  5. Automatizar un pre-push hook que verifique cambios en `frontend/src/modules/security/components/AuditLog.tsx` y exija actualizar esta documentación antes de permitir subir commits.

## 5. Seguimiento de pruebas y calidad

**Requisito declarado**
- `AGENTS.md` exige que `pytest` concluya en verde y que se registren las brechas detectadas tras cada ejecución.【F:AGENTS.md†L4-L11】

**Situación actual**
- `pytest` ya se ejecuta en verde tras la incorporación de recordatorios y métricas; falta añadir pruebas de frontend que garanticen la integración completa.【9071c6†L1-L25】
- Aún no se documentan corridas de `npm --prefix frontend test` ni existe cobertura automatizada para la bitácora.

**Acciones requeridas**
- **Pruebas automatizadas**
  1. Mantener `pytest` en cada iteración y añadir pruebas Vitest/React Testing Library que cubran exportación, recordatorios y acuses en la UI.
  2. Registrar en `docs/bitacora_pruebas_2025-10-14.md` cada ejecución de pruebas backend/frontend con fecha y resultado.
- **Checklist de entrega**
  3. Conservar el checklist al final de este documento y ampliarlo cuando se agreguen nuevos módulos (p.ej. monitoreo multi-sucursal).
- **Optimización sugerida**
  4. Configurar CI para ejecutar `pytest` y `npm --prefix frontend test` en paralelo, agregando métricas de cobertura de auditoría.

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
