# Bitácora de pruebas operativas — 14/10/2025

> Trabajaste sobre **Softmobile 2025 v2.2.0** en modo estricto de versión. No se realizaron cambios de versión ni de banderas corporativas.

## Preparación del entorno

1. Se creó un entorno virtual con `python -m venv .venv` y se instalaron dependencias desde `requirements.txt`.
2. Se levantó el backend FastAPI mediante `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` habilitando los *feature flags* requeridos (`SOFTMOBILE_ENABLE_CATALOG_PRO`, `SOFTMOBILE_ENABLE_TRANSFERS`, `SOFTMOBILE_ENABLE_PURCHASES_SALES`, `SOFTMOBILE_ENABLE_ANALYTICS_ADV`, `SOFTMOBILE_ENABLE_HYBRID_PREP`).
3. Se instaló el frontend (`npm install`) y se ejecutó `npm run dev -- --host 0.0.0.0 --port 5173` para validar la interfaz.

## Datos creados para la prueba integral

| Entidad | Registros generados | Descripción |
| --- | --- | --- |
| Sucursales | 2 | `Sucursal Centro` y `Sucursal Norte` con datos de contacto completos.【F:docs/bitacora_pruebas_2025-10-14.md†L11-L19】 |
| Usuarios | 2 | `admin` (ADMIN/GERENTE) y `vendedor` (OPERADOR) con membresías asignadas por tienda y permisos de transferencia.【F:docs/bitacora_pruebas_2025-10-14.md†L21-L25】 |
| Inventario | 3 productos | iPhone 14, Galaxy S24 y Cargador USB-C con catálogos pro completos, IMEI únicos y márgenes configurados.【F:docs/bitacora_pruebas_2025-10-14.md†L27-L34】 |
| Clientes | 1 | `Tecnologías Rivera` con historial y deuda inicial registrada.【F:docs/bitacora_pruebas_2025-10-14.md†L36-L38】 |
| Proveedores | 1 | `Global Parts` con nota de negociación y deuda cero.【F:docs/bitacora_pruebas_2025-10-14.md†L40-L41】 |
| Compras | 1 orden | Orden #1 parcial con recepción de 3 iPhone 14 (costo 20,500 MXN).【F:docs/bitacora_pruebas_2025-10-14.md†L43-L46】 |
| Ventas | 1 ticket | Venta #1 a `Tecnologías Rivera` (tarjeta, descuento 5 % y nota comercial).【F:docs/bitacora_pruebas_2025-10-14.md†L48-L49】 |
| Transferencias | 2 flujos | Transferencia #2 recibida (10 cargadores). Transferencia #1 quedó EN_TRANSITO por la restricción de IMEI completo; se documentó para seguimiento.【F:docs/bitacora_pruebas_2025-10-14.md†L51-L54】 |

## Evidencia relevante

- Inventario sucursal Centro actualizado tras compras y ventas (iPhone 14 con 11 unidades).【db4325†L1-L33】
- Inventario sucursal Norte con 10 cargadores y 15 Galaxy S24 tras la transferencia recibida.【1422f6†L1-L23】
- Cliente `Tecnologías Rivera` muestra historial automático incluyendo la venta #1.【ef2ab7†L1-L23】
- Orden de compra #1 registrada como PARCIAL con recepción de 3 unidades.【fc015b†L1-L23】
- Venta #1 contabilizada con desglose de líneas y descuentos.【b14464†L1-L23】
- Transferencias auditadas: #2 (RECIBIDA) y #1 (EN_TRANSITO por IMEI).【e5f5ff†L1-L29】

## Incidencias detectadas

- **Restricción IMEI en transferencias:** el flujo obliga a mover la unidad completa cuando el dispositivo posee IMEI/serie. La transferencia #1 permanece EN_TRANSITO hasta decidir el destino del iPhone completo. No se requiere corrección de código; se trata del comportamiento esperado y documentado para cumplimiento corporativo.

## Próximos pasos sugeridos

1. Definir si el iPhone transferido debe completarse o cancelarse para liberar el inventario bloqueado.
2. Ejecutar `pytest` y `npm --prefix frontend run build` en la siguiente iteración de mantenimiento para actualizar la bitácora operativa.
3. Cerrar la transferencia pendiente o generar un recibo POS que consuma la unidad según la política de IMEI.

## Actualización 14/10/2025 — Regresión auditoría/métricas

- Hash base: `335916d` (antes de integrar ajustes de UI de Seguridad).
- `pytest` → ✅ 37 pruebas en verde (37 passed, 2 warnings) validando recordatorios, métricas y flujos POS.【a8dcda†L1-L20】
- `npm --prefix frontend run build` → ✅ compilación exitosa sin errores (avisos de chunk esperados).【1889c4†L1-L12】
- Observaciones: `AuditLog.tsx` muestra recordatorios activos con snooze y motivo corporativo obligatorio; `GlobalMetrics.tsx` refleja pendientes/atendidas y enlaza a Seguridad para atender acuses.

## Actualización 15/02/2025 — Cobertura completa de Seguridad

- Hash base: `worktree` (pendiente de registrar el hash definitivo al fusionar este commit).
- `pytest` → ✅ 37 pruebas en verde (37 passed, 2 warnings) tras integrar los mocks de contexto de Dashboard en Vitest.【b3d853†L1-L24】
- `npm --prefix frontend run build` → ✅ compilación finalizada sin errores (únicamente advertencias de chunk esperadas).【dbe5a6†L1-L12】
- `npm --prefix frontend run test` → ✅ Vitest ejecuta `AuditLog.test.tsx` y `GlobalMetrics.test.tsx`, validando recordatorios, motivos corporativos, descargas y enlaces rápidos.【c13833†L1-L14】
- Observaciones: la suite de Seguridad utiliza `vi.hoisted` para simular `useDashboard`, evitando depender de `DashboardProvider` y permitiendo aislar toasts/métricas en pruebas.

