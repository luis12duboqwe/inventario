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

## Actualización 17/10/2025 — Inventario pro y edición de dispositivos

- Hash base: `335916d` (antes de registrar costo unitario opcional y modal de edición en inventario).
- `pytest` → ✅ 37 pruebas en verde tras capturar costo unitario y validar edición pro de dispositivos.【262bbb†L1-L18】
- `npm --prefix frontend run build` → ✅ compilación lista sin errores luego del refuerzo visual del inventario.【ab41e6†L1-L12】
- `npm --prefix frontend run test` → ✅ pruebas de Vitest en verde conservando auditoría y métricas globales.【7c59fb†L1-L14】
- Observaciones: el formulario de movimientos ahora respeta el motivo mínimo y permite registrar `unit_cost` en entradas; el modal `DeviceEditDialog` exige motivo corporativo y normaliza campos sensibles del catálogo pro.

## Actualización 02/03/2025 — Paginación dinámica y ajuste directo de existencias

- Hash base: `bb855a5` (antes de habilitar la paginación configurable y el ajuste directo de stock desde la edición pro).
- `pytest` → ✅ 37 pruebas en verde tras instalar dependencias faltantes (`prometheus-client`) y validar inventario paginado.【ec2f81†L1-L15】
- `npm --prefix frontend run build` → ✅ compilación lista con advertencias de tamaño esperadas en los *chunks* analíticos.【e62bb2†L1-L12】
- `npm --prefix frontend run test` → ✅ pruebas de Vitest en verde; persisten advertencias de `act(...)` y navegación simulada propias del entorno jsdom.【0f7ebc†L1-L11】
- Observaciones: la tabla de inventario permite ajustar el tamaño de página sin perder la vista completa con carga progresiva, y el modal de edición solicita motivo corporativo antes de aplicar el nuevo total de existencias.

## Actualización 03/03/2025 — Motivo obligatorio en descargas de inventario

- Hash base: `bb855a5` (antes de exigir motivo `X-Reason` en la descarga del PDF de inventario).
- `pytest` → ✅ 37 pruebas en verde luego de instalar `prometheus-client` y validar los prompts de motivo corporativo en inventario y sincronización.【b5c05f†L1-L18】
- `npm --prefix frontend run build` → ✅ compilación exitosa con advertencia por *chunks* grandes en analítica.【722e51†L1-L11】
- `npm --prefix frontend run test` → ⚠️ no se ejecutó porque `vitest` no está instalado en el entorno de CI actual.【0dc846†L1-L6】
- Observaciones: la descarga de inventario desde Inventario y Sincronización ahora solicita motivo corporativo, propaga el header `X-Reason` y muestra toasts de confirmación o error según el resultado.

## Actualización 04/03/2025 — Motivo obligatorio en descargas analíticas

- Hash base: `b663d7d` (antes de exigir motivo `X-Reason` en los reportes analíticos CSV/PDF).
- `pytest` → ✅ 37 pruebas en verde tras instalar `prometheus-client` y validar que `/reports/analytics/pdf` y `/reports/analytics/export.csv` requieran motivo corporativo.【3251e1†L1-L20】
- `npm --prefix frontend run build` → ✅ compilación lista con las advertencias habituales de tamaño en los *chunks* de analítica.【7c9b5c†L1-L10】
- `npm --prefix frontend run test` → ⚠️ falla porque `vitest` no está disponible en el contenedor actual; se mantiene el pendiente de instalación para el entorno CI.【9978d2†L1-L6】
- Observaciones: el tablero `AnalyticsBoard.tsx` ahora solicita motivo antes de exportar y el backend valida la cabecera `X-Reason`, manteniendo trazabilidad en descargas ejecutivas.

