# Instrucciones para agentes

1. **Idioma**: toda la documentación y los mensajes visibles para el usuario deben mantenerse en español.
2. **Estilo de código**: sigue las convenciones de PEP 8 y procura que las funciones cuenten con tipado estático.
3. **Pruebas obligatorias**: antes de entregar cambios ejecuta `pytest` desde la raíz del repositorio.
4. **Dependencias**: agrega nuevas librerías a `requirements.txt` y documenta su uso en el `README.md` cuando sean necesarias.
5. **Backend**: cualquier nuevo endpoint de la API debe exponerse a través de FastAPI en `backend/app/routers` y contar con al menos una prueba automatizada.
6. **Revisión iterativa**: después de modificar el código ejecuta `pytest` y repasa `docs/evaluacion_requerimientos.md`; si encuentras brechas con el plan Softmobile 2025 v2.2 corrige y repite el proceso hasta cumplirlo por completo.
7. **Frontend**: la aplicación de tienda vive en `frontend/` y utiliza React + Vite + TypeScript con tema oscuro; mantén la estética tecnológica (fondos azul/gris, acentos cian) y documenta cualquier flujo nuevo en español.
8. **Finalización completa**: cada vez que leas este archivo o el `README.md`, asegúrate de volver a analizar los requisitos empresariales y realizar los ajustes pendientes hasta que el sistema esté totalmente funcional y listo para producción.
9. **Actualizaciones**: mantén el feed `docs/releases.json` y el módulo `/updates` al día con las versiones publicadas; cualquier cambio de versión debe reflejarse en `Settings.version`, documentación y pruebas.
10. **Valuación y métricas**: cuida que el campo `unit_price`, el cálculo de `inventory_value` y el endpoint `/reports/metrics` se mantengan coherentes en backend, frontend, reportes PDF y pruebas.

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
- ⏳ **Lote D — Analítica avanzada**: pendientes endpoints `/reports/analytics/*` y generación de PDF oscuro.
- ⏳ **Lote E — Seguridad y auditoría fina**: pendiente middleware `X-Reason`, 2FA TOTP, auditoría de sesiones y motivo obligatorio en ajustes.
- ⏳ **Lote F — Modo híbrido**: pendiente cola `sync_outbox` con reintentos y resolución *last-write-wins*.

**Próximos pasos**

1. Activar los controles de seguridad del **Lote E**: middleware global `X-Reason`, rutas 2FA TOTP, auditoría/revocación de sesiones y componentes `TwoFactorSetup.tsx`/`AuditLog.tsx` con pruebas.
2. Desarrollar el **Lote D** con endpoints `/reports/analytics/*`, cálculos avanzados y generación de PDF oscuro, incluyendo cobertura de pruebas.
3. Completar el **Lote F** implementando la cola `sync_outbox`, manejo de reintentos y estrategia *last-write-wins* con validaciones automatizadas.
