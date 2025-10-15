# Plan de cobertura funcional — Softmobile 2025 v2.2.0

Este documento resume las brechas detectadas entre lo descrito en `README.md` y `AGENTS.md` y la implementación actual. Sirve como guía explícita para completar los faltantes sin modificar la versión v2.2.0.

## 1. Auditoría y recordatorios de seguridad

**Requisito declarado**
- El README indica que la bitácora permite exportar CSV/PDF con estado de acuse, generar recordatorios automáticos con snooze y registrar acuses manuales para alertas críticas.【F:README.md†L31-L33】

**Situación actual**
- El router `backend/app/routers/audit.py` sólo expone `/audit/logs` y `/audit/logs/export.csv`; no existen los endpoints para acuses ni recordatorios prometidos.【F:backend/app/routers/audit.py†L20-L71】
- El servicio para renderizar PDF (`render_audit_pdf`) ya existe, pero no está conectado a ninguna ruta pública, por lo que el enlace `/reports/audit/pdf` falla en el frontend.【F:backend/app/services/audit.py†L1-L103】
- `frontend/src/modules/security/components/AuditLog.tsx` referencia recordatorios y snooze, pero carece de importaciones (`useRef`) y de funciones/estados (`loadReminders`, `snoozedUntil`, acciones de acuse), quedando incompleto y duplicando lógica de filtros.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L193】
- Las entradas destacadas de auditoría no incluyen `entity_id`, lo que provoca errores al vincular acuses en métricas y rompe pruebas (`KeyError: 'entity_id'`).【F:backend/app/utils/audit.py†L37-L78】【7f4f71†L75-L132】

**Acciones requeridas**
- **Backend**
  1. Crear en `backend/app/routers/audit.py` los endpoints pendientes:
     - `GET /audit/reminders` consumiendo `crud.get_persistent_audit_alerts` y aplicando `require_reason` únicamente cuando la alerta vaya a modificarse.
     - `POST /audit/acknowledgements` que invoque `crud.acknowledge_audit_alert`, valide `X-Reason` ≥ 5 caracteres y registre usuario, nota y sello de tiempo.
  2. Exponer en `backend/app/routers/reports.py` la ruta `GET /reports/audit/pdf` reutilizando `services.audit.render_audit_pdf`, con validación de roles (`AUDITORIA_ROLES`) y parámetros de filtro reutilizables con `/audit/logs`.
  3. Extender `backend/app/utils/audit.py.HighlightEntry` para incluir `entity_id`, `acknowledged_at` y `acknowledged_by`, ajustar `summarize_alerts` y consumidores (`crud.get_dashboard_metrics`, `services.audit`) y añadir `selectinload` para usuarios asociados.
- **Frontend**
  4. Completar `frontend/src/modules/security/components/AuditLog.tsx`:
     - Importar `useRef`, consolidar `buildCurrentFilters` y centralizar el estado de paginación.
     - Implementar hooks para cargar recordatorios (`/audit/reminders`), ejecutar snooze de 10 minutos y registrar acuses (`/audit/acknowledgements`).
     - Mostrar badges de estado (pendiente/atendida), botón de descarga PDF y toasts contextualizados con el motivo capturado.
  5. Agregar en `frontend/src/api.ts` las funciones `fetchAuditReminders`, `acknowledgeAuditAlert` y `downloadAuditPdf`, propagando `X-Reason` en mutaciones y controlando errores 404 temporales mientras se publica el endpoint.
- **Pruebas y calidad**
  6. Ampliar `backend/tests/test_audit_logs.py` para validar recordatorios, acuses y la descarga de PDF; actualizar `test_stores.py` o crear `test_dashboard_metrics.py` para cubrir la agregación de acuses en métricas.
  7. Crear pruebas de interfaz (React Testing Library o Vitest) para los botones de acuse/snooze y documentar los comandos en `package.json`.
- **Documentación y seguimiento**
  8. Registrar en `docs/bitacora_pruebas_2025-10-14.md` las corridas de `pytest`/`npm test` que validen estos cambios y actualizar README para indicar que la funcionalidad quedó activa.
- **Optimización sugerida**
  9. Añadir caché en memoria (TTL corto) a `crud.get_persistent_audit_alerts` si el número de alertas supera 200 registros y documentar los parámetros de invalidez.

## 2. Exportación CSV con cabecera obligatoria

**Requisito declarado**
- `AGENTS.md` establece que las operaciones sensibles deben exigir cabecera `X-Reason` ≥ 5 caracteres.【F:AGENTS.md†L8-L14】

**Situación actual**
- La exportación `/audit/logs/export.csv` exige `X-Reason`, pero las pruebas oficiales (`test_audit_filters_and_csv_export`) la consumen sin el encabezado, provocando respuestas 400.【F:backend/app/routers/audit.py†L42-L68】【7f4f71†L1-L74】

**Acciones requeridas**
- **Decisión de política**
  1. Definir, junto con Seguridad, si las exportaciones CSV deben exigir motivo corporativo. Documentar la decisión en `docs/bitacora_pruebas_2025-10-14.md` y en README.
     - Si se confirma como operación sensible, mantener `require_reason`, actualizar fixtures (`backend/tests/conftest.py`) y ajustar `test_audit_filters_and_csv_export` para enviar `X-Reason` ≥ 5 caracteres.
     - Si se descarta como sensible, remover `require_reason` de `/audit/logs/export.csv`, trasladar la verificación a mutaciones (`POST /audit/acknowledgements`) y actualizar la política en middleware/documentación.
- **Implementación técnica**
  2. Crear helpers reutilizables en `backend/app/routers/dependencies.py` para validar motivos sólo en mutaciones de auditoría.
  3. Añadir pruebas de regresión que cubran ambos escenarios (con y sin cabecera) según la política adoptada.
- **Documentación**
  4. Refrescar el README con ejemplos explícitos de llamada (curl) incluyendo la cabecera según corresponda y añadir un snippet en `frontend/src/modules/security/components/AuditLog.tsx` para prevenir regresiones.
- **Optimización sugerida**
  5. Registrar métricas de uso de exportación (contador Prometheus o log estructurado) para analizar impacto y ajustar límites `limit`/`le` si es necesario.

## 3. Consolidación y optimización del módulo de métricas

**Requisito declarado**
- El tablero global debe distinguir alertas pendientes vs. atendidas en `/reports/metrics` y reflejar acuses en `GlobalMetrics.tsx`.【F:README.md†L31-L33】

**Situación actual**
- `crud.get_dashboard_metrics` intenta combinar acuses con resúmenes, pero falla porque los `HighlightEntry` carecen de `entity_id`; además no hay caché ni normalización del tamaño de respuesta.【F:backend/app/crud.py†L1860-L1936】【F:backend/app/utils/audit.py†L37-L78】

**Acciones requeridas**
- **Backend**
  1. Incorporar `entity_id` en `HighlightEntry` y rehidratar los resúmenes en `crud.get_dashboard_metrics`, agregando campos `pending_count`, `acknowledged_count`, `last_acknowledged_by` y `last_acknowledged_at`.
  2. Optimizar la consulta usando `selectinload`/`joinedload` sólo para usuarios necesarios y limitar columnas (`load_only`) en modelos pesados.
  3. Incluir pruebas unitarias en `backend/tests/test_dashboard_metrics.py` que verifiquen el conteo diferenciado de pendientes vs. atendidas.
- **Frontend**
  4. Actualizar `frontend/src/modules/dashboard/components/GlobalMetrics.tsx` para consumir los nuevos campos, mostrando badges de estado, totales por tipo de alerta y accesos directos a Seguridad.
  5. Ajustar `frontend/src/api.ts` para mapear correctamente la estructura extendida y reutilizarla en notificaciones globales.
- **Optimización sugerida**
  6. Añadir memoización ligera (React `useMemo`) en `GlobalMetrics.tsx` para evitar renders costosos cuando sólo cambian métricas no relacionadas.
- **Documentación y pruebas**
  7. Documentar el nuevo contrato en README y actualizar la bitácora de pruebas con la suite de regresión ejecutada.

## 4. Documentación operativa y bitácoras

**Requisito declarado**
- `docs/evaluacion_requerimientos.md` debe reflejar las brechas vigentes y guiar la iteración siguiente, mientras que la bitácora de control del README debe coincidir con el estado real del sistema.【F:AGENTS.md†L96-L106】【F:docs/evaluacion_requerimientos.md†L1-L38】

**Situación actual**
- El documento de evaluación reporta “✅” en seguridad/auditoría a pesar de que faltan recordatorios, acuses y PDF, lo que genera un falso positivo durante la revisión.【F:docs/evaluacion_requerimientos.md†L12-L39】【F:backend/app/routers/audit.py†L20-L71】
- El README da por implementados los recordatorios y los acuses cuando todavía no existen rutas públicas ni componentes completos, por lo que la guía operativa no coincide con el código.【F:README.md†L31-L39】【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L212】

**Acciones requeridas**
- **Documentación inmediata**
  1. Mantener `docs/evaluacion_requerimientos.md` sincronizado con el estado real (marcando Seguridad/Auditoría como ⚠️ o ❌ según corresponda) y enlazar este plan en cada revisión.
  2. Añadir en README una nota visible de "Funcionalidad en implementación" para recordatorios y acuses mientras los endpoints estén ausentes; retirar la nota cuando finalice el desarrollo.
  3. Crear `docs/bitacora_pruebas_2025-10-14.md` (si no existe) registrando fecha, comando ejecutado y resultado de `pytest`/`npm test` para cada corrección.
- **Seguimiento operativo**
  4. Actualizar la bitácora operativa del README con los fallos detectados (`test_audit_filters_and_csv_export`, `test_inventory_flow`) y referenciar el commit que los corrige.
  5. Incorporar checklist de revisión en la bitácora (leer README/AGENTS, ejecutar pruebas, validar UI Seguridad y métricas) para que próximas iteraciones sigan el mismo flujo.
- **Optimización sugerida**
  6. Establecer recordatorios automáticos (por ejemplo, Git pre-push hook) que disparen `pytest` y validen que `docs/evaluacion_requerimientos.md` está actualizado antes de subir cambios.

## 5. Seguimiento de pruebas y calidad

**Requisito declarado**
- `AGENTS.md` exige que `pytest` concluya en verde y que se registren las brechas detectadas tras cada ejecución.【F:AGENTS.md†L4-L11】

**Situación actual**
- La suite actual presenta dos fallos directamente relacionados con las brechas de auditoría (cabecera `X-Reason` y resúmenes sin `entity_id`).【17888e†L1-L132】
- No existe un documento que detalle el estado de las pruebas recientes ni un checklist para validar que los nuevos endpoints queden cubiertos.

**Acciones requeridas**
- **Pruebas automatizadas**
  1. Reparar los endpoints y componentes descritos en los puntos anteriores y ejecutar `pytest` hasta obtener verde; registrar cada corrida (comando, hora, resultado) en la bitácora.
  2. Añadir casos nuevos en `backend/tests/test_audit_logs.py` y crear `backend/tests/test_dashboard_metrics.py` para cubrir métricas pendientes vs. atendidas.
  3. Preparar pruebas de contrato para `frontend/src/api.ts` (Vitest) asegurando que los servicios de auditoría manejan estados intermedios.
- **Checklist de entrega**
  4. Incluir un checklist reusable al final de este documento con pasos a seguir antes de cerrar la iteración (revisión de docs, ejecución de pruebas, validación de UI, verificación de logs).
- **Optimización sugerida**
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
