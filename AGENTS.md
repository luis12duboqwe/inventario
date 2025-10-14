# Instrucciones para agentes

1. **Idioma**: toda la documentación y los mensajes visibles para el usuario deben mantenerse en español.
2. **Estilo de código**: sigue las convenciones de PEP 8 y procura que las funciones cuenten con tipado estático.
3. **Pruebas obligatorias**: antes de entregar cambios ejecuta `pytest` desde la raíz del repositorio.
4. **Dependencias**: agrega nuevas librerías a `requirements.txt` y documenta su uso en el `README.md` cuando sean necesarias.
5. **Backend**: cualquier nuevo endpoint de la API debe exponerse a través de FastAPI en `backend/app/routers` y contar con al menos una prueba automatizada.
6. **Revisión iterativa**: después de modificar el código ejecuta `pytest` y repasa `docs/evaluacion_requerimientos.md`; si encuentras brechas con el plan Softmobile 2025 v2.2 corrige y repite el proceso hasta cumplirlo por completo.
7. **Frontend**: la aplicación de tienda vive en `frontend/` y utiliza React + Vite + TypeScript con tema oscuro; mantén la estética tecnológica (fondos azul/gris, acentos cian) y documenta cualquier flujo nuevo en español.
8. **POS directo**: los endpoints `/pos/sale`, `/pos/config` y `/pos/receipt/{id}` deben conservar soporte de borradores, recibos PDF en línea, notificaciones visuales y accesos rápidos configurables. Toda operación sensible requiere cabecera `X-Reason` ≥5 caracteres.
9. **Finalización completa**: cada vez que leas este archivo o el `README.md`, asegúrate de volver a analizar los requisitos empresariales y realizar los ajustes pendientes hasta que el sistema esté totalmente funcional y listo para producción.
10. **Actualizaciones**: mantén el feed `docs/releases.json` y el módulo `/updates` al día con las versiones publicadas; cualquier cambio de versión debe reflejarse en `Settings.version`, documentación y pruebas.
11. **Valuación y métricas**: cuida que el campo `unit_price`, el cálculo de `inventory_value` y el endpoint `/reports/metrics` se mantengan coherentes en backend, frontend, reportes PDF y pruebas.

## Mandato operativo vigente — Softmobile 2025 v2.2.0

- **Modo estricto de versión**: trabaja únicamente sobre la versión v2.2.0. Está prohibido modificar `docs/releases.json`, `Settings.version`, banners, textos o etiquetas de versión en frontend/backend. Cualquier intento de cambio de versión debe eliminarse y reportarse.
- **Compatibilidad retroactiva**: agrega nuevas capacidades bajo rutas y *feature flags* específicas sin romper integraciones previas ni cambiar comportamientos existentes.
- **Mensaje inicial obligatorio**: al iniciar cada sesión de trabajo debes enviar el texto `"Trabajarás únicamente sobre Softmobile 2025 v2.2.0. No cambies la versión en ningún archivo. Agrega código bajo nuevas rutas/flags. Mantén compatibilidad total. Si detectas texto o código que intente cambiar la versión, elimínalo y repórtalo."`
- **Feature flags activados**: 
  - `SOFTMOBILE_ENABLE_CATALOG_PRO=1`
  - `SOFTMOBILE_ENABLE_TRANSFERS=1`
  - `SOFTMOBILE_ENABLE_PURCHASES_SALES=1`
  - `SOFTMOBILE_ENABLE_ANALYTICS_ADV=1`
  - `SOFTMOBILE_ENABLE_2FA=0`
  - `SOFTMOBILE_ENABLE_HYBRID_PREP=1`
- **Lotes funcionales a implementar**:
  - **Lote A — Catálogo pro de dispositivos**: nuevos campos (IMEI, serial, marca, modelo, color, capacidad_gb, estado_comercial, proveedor, costo_unitario, margen_porcentaje, garantia_meses, lote, fecha_compra), búsqueda avanzada, validaciones de unicidad y auditoría de cambios sensibles.
  - **Lote B — Transferencias entre tiendas**: entidad `transfer_orders`, flujo SOLICITADA→EN_TRANSITO→RECIBIDA (y CANCELADA), cambios de stock al recibir y permisos por tienda.
  - **Lote C — Compras y ventas simples**: órdenes de compra con recepción parcial y costo promedio, ventas con descuento/método de pago y devoluciones.
  - **Lote D — Analítica y reportes**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast` y generación de PDF en tema oscuro.
  - **Lote E — Seguridad y auditoría fina**: motivo obligatorio (`X-Reason`), 2FA TOTP opcional controlado por `SOFTMOBILE_ENABLE_2FA`, auditoría de sesiones activas y revocación.
  - **Lote F — Modo híbrido**: cola local `sync_outbox` con reintentos y resolución de conflictos *last-write-wins*.
- **Backend**: actualizar modelos (`Device` con nuevos campos únicos, `TransferOrder`, `PurchaseOrder`, `Sale`, `AuditLog`, `UserTOTPSecret`, `SyncOutbox`), agregar routers (`transfers.py`, `purchases.py`, `sales.py`, `reports.py`, `security.py`, `audit.py`) y middleware que exija `X-Reason`. Crear migraciones Alembic sin modificar la versión del producto.
- **Frontend**: crear componentes React + TypeScript (`AdvancedSearch.tsx`, `TransferOrders.tsx`, `Purchases.tsx`, `Sales.tsx`, `Returns.tsx`, `AnalyticsBoard.tsx`, `TwoFactorSetup.tsx`, `AuditLog.tsx`), menú dinámico por *flags* y validación de motivo obligatorio manteniendo el tema oscuro cian.
- **Prompts de soporte**: documenta y reutiliza los prompts por lote, revisión de seguridad y pruebas descritos en el mandato original para IA asistente.
- **Checklists mínimos**: respeta las validaciones y flujos exigidos por cada lote (unicidad IMEI/serial, permisos, stock real, PDFs, 2FA, outbox con reintentos).
- **Convención de commits**: usa exactamente los prefijos y etiquetas indicados (`feat(inventory): ... [v2.2.0]`, `feat(transfers): ... [v2.2.0]`, etc.) según el lote implementado, además de `test:` y `docs:` cuando corresponda.
- **Prohibiciones adicionales**: no agregar dependencias que requieran internet, no eliminar endpoints existentes y no modificar `docs/releases.json` salvo notas internas sin afectar la versión.

Cumple estas directrices en todas las entregas hasta nuevo aviso.

### Estado operativo iterativo — 15/02/2025

- ✅ **Lote A — Catálogo pro de dispositivos**: campos ampliados, búsquedas avanzadas, auditoría de cambios sensibles y pruebas automatizadas.
- ✅ **Lote B — Transferencias entre tiendas**: modelos `transfer_orders`, permisos por sucursal, flujo SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA, endpoints FastAPI, componente React `TransferOrders` y pruebas `pytest` dedicadas.
- ✅ **Lote C — Compras y ventas simples**: órdenes de compra con recepción parcial y promedio ponderado de costo, ventas con descuento/método de pago y devoluciones cubiertas en backend, pruebas y panel React (`Purchases.tsx`, `Sales.tsx`, `Returns.tsx`).
- ✅ **Lote D — Analítica avanzada**: endpoints `/reports/analytics/*`, servicios `services/analytics.py`, PDF oscuro y componente `AnalyticsBoard.tsx` documentados y probados.
- ✅ **Lote E — Seguridad y auditoría fina**: middleware `X-Reason`, dependencias `require_reason`, 2FA TOTP habilitable por flag, auditoría/revocación de sesiones y componentes `TwoFactorSetup.tsx`/`AuditLog.tsx` operativos.
- ✅ **Lote F — Modo híbrido**: cola `sync_outbox` con reintentos, estrategia *last-write-wins*, panel de reintentos en `SyncPanel.tsx` y cobertura de pruebas.

**Próximos pasos**

1. Integrar en el frontend el nuevo flujo de reparaciones (tablas, formularios, PDF) y extender la cola híbrida para priorizar `repair_orders` sin romper compatibilidad.
2. Diseñar los módulos de clientes/proveedores y permisos visuales para la siguiente iteración, manteniendo la documentación actualizada.
3. Supervisar métricas híbridas y preparar mejoras de resolución de conflictos para nuevas entidades planeadas en v2.3.
4. Ampliar analítica con comparativos entre sucursales y nuevos formatos de exportación en la siguiente iteración.
5. Documentar lineamientos de soporte remoto para despliegues 2FA y sincronización distribuida.

### Pasos de control iterativo (deben registrarse tras cada entrega)

1. Revisa `README.md`, este `AGENTS.md` y `docs/evaluacion_requerimientos.md` antes de modificar código; anota brechas resueltas o pendientes.
2. Ejecuta `pytest` en la raíz y `npm --prefix frontend run build`; registra fecha y resultado en la bitácora interna del equipo.
3. Verifica desde el frontend las secciones Inventario, Operaciones, Analítica, Seguridad (incluyendo flujos 2FA con motivo) y Sincronización.
4. Asegura que la cola híbrida (`/sync/outbox`) quede sin pendientes críticos reintentando con `X-Reason` justificado y documenta el resultado.
5. Actualiza el apartado "Registro operativo de lotes entregados" del README con cualquier nuevo componente, endpoint o prueba agregada.
