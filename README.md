# Softmobile 2025 v2.2.0

Plataforma empresarial para la gestión centralizada de inventarios, sincronización entre sucursales y control operativo integral de cadenas de tiendas con una experiencia visual moderna en tema oscuro.

## Arquitectura general

Softmobile 2025 se compone de dos módulos cooperantes:

1. **Softmobile Inventario (frontend)**: cliente React + Vite pensado para ejecutarse en cada tienda. Permite registrar movimientos, disparar sincronizaciones, generar respaldos manuales y descargar reportes PDF con un diseño oscuro y acentos cian.
2. **Softmobile Central (backend)**: API FastAPI que consolida catálogos, controla la seguridad, genera reportes, coordina sincronizaciones automáticas/manuales y ejecuta respaldos programados.

La versión v2.2.0 trabaja en modo local (sin nube) pero está preparada para empaquetarse en instaladores Windows y evolucionar a despliegues híbridos.

## Verificación Global - Módulo de Inventario Softmobile 2025 v2.2.0

- **Fecha y hora**: 17/10/2025 05:41 UTC.
- **Resumen**: se ejecutó una validación integral que cubre catálogo de productos, existencias, identificadores IMEI/serie, valoración financiera, ajustes y auditoría, reportes avanzados, permisos RBAC e interfaz visual. No se detectaron defectos funcionales ni inconsistencias de datos.
- **Pruebas ejecutadas**: `pytest`, `npm --prefix frontend run build`, `npm --prefix frontend run test`.

| Área evaluada | Estado | Evidencia clave |
| --- | --- | --- |
| Catálogo de productos | Completo | Alta, búsqueda avanzada y auditoría de cambios validados en `backend/tests/test_catalog_pro.py`. |
| Existencias y movimientos | Completo | Ajustes, alertas y respuestas enriquecidas verificados en `backend/tests/test_stores.py`. |
| Gestión de IMEI y series | Completo | Endpoints de identificadores y bloqueos de duplicados cubiertos por `backend/tests/test_device_identifiers.py`. |
| Valoraciones y costos | Completo | Cálculos ponderados ejercitados en `backend/tests/test_inventory_valuation.py`. |
| Ajustes, auditorías y alertas | Completo | Alertas críticas/preventivas registradas en `backend/tests/test_stores.py`. |
| Reportes y estadísticas | Completo | Exportaciones CSV/PDF/Excel y agregadores probados en `backend/tests/test_reports_inventory.py`. |
| Roles y permisos | Completo | Restricciones por rol y utilidades RBAC validadas en `backend/tests/test_stores.py` y `backend/tests/test_roles.py`. |
| Interfaz visual del inventario | Completo | Composición de pestañas, tablas, reportes y analítica confirmada en `frontend/src/modules/inventory/pages/InventoryPage.tsx` y pruebas Vitest asociadas. |

- **Correcciones aplicadas**: no se requirió modificar código; se aseguraron dependencias de pruebas instaladas (por ejemplo, `openpyxl`) antes de la ejecución de la suite.
- **Recomendaciones**: mantener la ejecución periódica de las suites de backend y frontend, y monitorear advertencias de React/Vitest para futuros refinamientos de pruebas.

## Capacidades implementadas

- **API empresarial FastAPI** con modelos SQLAlchemy para tiendas, dispositivos, movimientos, usuarios, roles, sesiones de sincronización, bitácoras y respaldos.
- **Seguridad por roles** con autenticación JWT, alta inicial segura (`/auth/bootstrap`), administración de usuarios y auditoría completa. Los roles corporativos vigentes son `ADMIN`, `GERENTE` y `OPERADOR`.
- **Gestión de inventario** con movimientos de entrada/salida/ajuste, actualización de dispositivos, reportes consolidados por tienda e impresión de etiquetas individuales con QR (generadas en frontend mediante la librería `qrcode`) para cada dispositivo.
- **Ajustes manuales auditables** con motivo obligatorio, captura del usuario responsable y alertas automáticas de stock bajo o inconsistencias registradas en la bitácora corporativa.
- **Valuación y métricas financieras** con precios unitarios, ranking de sucursales y alertas de stock bajo expuestos vía `/reports/metrics` y el panel React.
- **Sincronización programada y bajo demanda** mediante un orquestador asincrónico que ejecuta tareas periódicas configurables.
- **Respaldos empresariales** con generación automática/manual de PDF y archivos comprimidos JSON usando ReportLab; historial consultable vía API.
- **Módulo de actualizaciones** que consulta el feed corporativo (`/updates/*`) para verificar versiones publicadas y descargar instaladores.
- **Frontend oscuro moderno** para el módulo de tienda, construido con React + TypeScript, compatible con escritorio y tablet.
- **Instaladores corporativos**: plantilla PyInstaller para el backend y script Inno Setup que empaqueta ambos módulos y crea accesos directos.
- **Pruebas automatizadas** (`pytest`) que validan flujo completo de autenticación, inventario, sincronización y respaldos.
- **Transferencias entre tiendas** protegidas por permisos por sucursal y feature flag, con flujo SOLICITADA → EN_TRANSITO → RECIBIDA/CANCELADA, auditoría en cada transición y componente React dedicado.
- **Compras y ventas operativas** con órdenes de compra parcialmente recibidas, cálculo de costo promedio, ventas con descuento/método de pago y devoluciones auditadas desde la UI (`Purchases.tsx`, `Sales.tsx`, `Returns.tsx`).
- **Operaciones automatizadas** con importación masiva desde CSV, plantillas recurrentes reutilizables y panel histórico filtrable por técnico, sucursal y rango de fechas (`/operations/history`).
- **Punto de venta directo (POS)** con carrito multiartículo, control automático de stock, borradores corporativos, recibos PDF en línea y configuración de impuestos/impresora.
- **Gestión de clientes y proveedores corporativos** con historial de contacto, exportación CSV, saldos pendientes y notas auditables desde la UI.
- ⚠️ **Bitácora de auditoría filtrable**: actualmente sólo están disponibles `/audit/logs` y la exportación CSV con motivo obligatorio; falta publicar `/audit/reminders`, `/audit/acknowledgements` y `/reports/audit/pdf` para reflejar acuses y notas tal como indica el plan.【F:backend/app/routers/audit.py†L20-L68】【F:docs/guia_revision_total_v2.2.0.md†L1-L87】
- ⚠️ **Recordatorios automáticos de seguridad**: la UI referencia recordatorios y snooze, pero el componente `AuditLog.tsx` carece de lógica efectiva y endpoints públicos; se debe completar siguiendo la guía de acciones pendientes.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L220】【F:docs/guia_revision_total_v2.2.0.md†L1-L107】
- ⚠️ **Acuses manuales de resolución**: existen modelos y funciones en `crud.py`, pero aún no hay rutas ni métricas que distingan pendientes vs. atendidas; consulta la guía para habilitarlos sin cambiar la versión.【F:backend/app/crud.py†L1858-L1935】【F:docs/guia_revision_total_v2.2.0.md†L88-L140】
- **Órdenes de reparación sincronizadas** con piezas descontadas automáticamente del inventario, estados corporativos (🟡/🟠/🟢/⚪) y descarga de orden en PDF.
- **POS avanzado con arqueos y ventas a crédito** incluyendo sesiones de caja, desglose por método de pago, recibos PDF y devoluciones controladas desde el último ticket.
- **Analítica comparativa multi-sucursal** con endpoints `/reports/analytics/comparative`, `/reports/analytics/profit_margin` y `/reports/analytics/sales_forecast`, exportación CSV consolidada y tablero React con filtros por sucursal.
- **Analítica predictiva en tiempo real** con regresión lineal para agotamiento/ventas, alertas automáticas (`/reports/analytics/alerts`), categorías dinámicas y widget en vivo por sucursal (`/reports/analytics/realtime`) integrado en `AnalyticsBoard.tsx`.
- **Sincronización híbrida priorizada** mediante `sync_outbox` con niveles HIGH/NORMAL/LOW, estadísticas por entidad y reintentos auditados desde el panel.
- **Métricas ejecutivas en vivo** con tablero global que consolida ventas, ganancias, inventario y reparaciones, acompañado de mini-gráficos (línea, barras y pastel) generados con Recharts.
- **Gestión visual de usuarios corporativos** con checkboxes para roles `ADMIN`/`GERENTE`/`OPERADOR`, control de activación y validación de motivos antes de persistir cambios.
- **Historial híbrido por tienda** con cola de reintentos automáticos (`/sync/history`) y middleware de acceso que bloquea rutas sensibles a usuarios sin privilegios.
- **Experiencia UI responsiva** con toasts contextuales, animaciones suaves y selector de tema claro/oscuro que mantiene el modo oscuro como predeterminado.
- **Interfaz animada Softmobile** con pantalla de bienvenida en movimiento, iconografía por módulo, toasts de sincronización modernizados y modo táctil optimizado para el POS, impulsados por `framer-motion`.

### Plan activo de finalización v2.2.0

| Paso | Estado | Directrices |
| --- | --- | --- |
| Conectar recordatorios, snooze y acuses en Seguridad (`AuditLog.tsx`) | ✅ Listo | La UI consume los servicios corporativos con motivo obligatorio, badges en vivo y registro de notas. |
| Actualizar el tablero global con métricas de pendientes/atendidas | ✅ Listo | `GlobalMetrics.tsx` muestra conteos, último acuse y acceso directo a Seguridad desde el dashboard. |
| Automatizar pruebas de frontend (Vitest/RTL) para recordatorios, acuses y descargas | 🔄 En progreso | Configurar `npm run test` con mocks de `api.ts`, validar snooze, motivos y descargas con `Blob`. |
| Registrar bitácora operativa de corridas (`pytest`, `npm --prefix frontend run build`) y validaciones multiusuario | 🔄 En progreso | Documentar cada corrida en `docs/bitacora_pruebas_*.md` y verificar escenarios simultáneos en Seguridad. |

**Directrices rápidas:**

- Captura siempre un motivo corporativo (`X-Reason` ≥ 5 caracteres) al descargar CSV/PDF o registrar un acuse.
- Repite `pytest` y `npm --prefix frontend run build` antes de fusionar cambios y anota el resultado en la bitácora.
- Mantén sincronizados README, `AGENTS.md` y `docs/evaluacion_requerimientos.md` tras completar cada paso del plan activo.

## Actualización Compras - Parte 1 (Estructura y Relaciones)

- **Estructura base garantizada**: se añadieron los modelos ORM `Proveedor`, `Compra` y `DetalleCompra` (`backend/app/models/__init__.py`) alineados con las tablas `proveedores`, `compras` y `detalle_compras`. Cada entidad expone relaciones bidireccionales para navegar proveedores, usuarios y dispositivos sin romper compatibilidad con flujos existentes.
- **Migración idempotente**: la migración `202502150011_compras_estructura_relaciones.py` crea las tablas cuando no existen y agrega columnas/fks/índices faltantes en instalaciones previas, asegurando claves primarias, tipos numéricos y vínculos con `users` y `devices`.
- **Verificación automatizada**: la prueba `backend/tests/test_compras_schema.py` inspecciona columnas, tipos, índices y claves foráneas para confirmar que el esquema cumpla con `proveedores → compras → detalle_compras` y la referencia hacia el catálogo de productos.
- **Documentación corporativa**: este README, el `CHANGELOG.md` y `AGENTS.md` registran la actualización bajo el apartado «Actualización Compras - Parte 1 (Estructura y Relaciones)» para mantener trazabilidad empresarial.
- **17/10/2025 10:45 UTC — Revalidación estructural**: se volvió a inspeccionar el esquema con SQLAlchemy `inspect`, confirmando tipos `Integer`/`Numeric`/`DateTime`, claves foráneas (`compras.proveedor_id`, `compras.usuario_id`, `detalle_compras.compra_id`, `detalle_compras.producto_id`) y la presencia de índices `ix_*` exigidos por el mandato.

## Actualización Compras - Parte 2 (Lógica e Integración con Inventario)

- **Recepciones trazables**: cada recepción de una orden crea movimientos de tipo **entrada** en `inventory_movements` con comentarios normalizados que incluyen proveedor, motivo corporativo e identificadores IMEI/serie, manteniendo al usuario responsable en `performed_by_id`.
- **Reversión segura de cancelaciones**: al anular una orden se revierten todas las unidades recibidas mediante movimientos **salida**, se recalcula el costo promedio ponderado y se deja rastro del proveedor y los artículos revertidos en la bitácora.
- **Devoluciones con costo promedio actualizado**: las devoluciones al proveedor descuentan stock, ajustan el costo ponderado y registran la operación en inventario reutilizando el formato corporativo de comentarios.
- **Cobertura de pruebas**: `backend/tests/test_purchases.py` incorpora validaciones de recepción, devolución y cancelación para garantizar el cálculo de stock/costo y la generación de movimientos conforme a la política corporativa.
- **Compatibilidad heredada con reportes**: se publica la vista SQL `movimientos_inventario` como alias directo de `inventory_movements`, permitiendo que integraciones históricas consulten los movimientos de entradas/salidas sin modificar sus consultas.

## Actualización Sucursales - Parte 1 (Estructura y Relaciones)

- La migración `202503010007_sucursales_estructura_relaciones.py` renombra `stores` a `sucursales` y homologa los campos obligatorios (`id_sucursal`, `nombre`, `direccion`, `telefono`, `responsable`, `estado`, `codigo`, `fecha_creacion`), manteniendo `timezone` e `inventory_value` para conservar compatibilidad histórica.
- Se reconstruyen índices únicos `ix_sucursales_nombre` e `ix_sucursales_codigo`, además del filtro operacional `ix_sucursales_estado`, poblando valores por omisión (`estado="activa"`, `codigo="SUC-###"`) para registros legados.
- Se actualizan las relaciones de integridad: el catálogo de productos (`devices`, alias corporativo de `productos`) y `users` referencian `sucursales.id_sucursal` mediante `sucursal_id`, mientras que `inventory_movements` enlaza `sucursal_destino_id` y `sucursal_origen_id` con reglas `CASCADE`/`SET NULL` según corresponda.
- La prueba `backend/tests/test_sucursales_schema.py` inspecciona columnas, tipos, índices y claves foráneas para evitar regresiones del módulo de sucursales.

## Actualización Compras - Parte 3 (Interfaz y Reportes)

- **Formulario de registro directo**: el módulo de Operaciones incorpora un formulario dedicado para capturar compras inmediatas seleccionando proveedor, productos y tasa de impuesto; calcula subtotal/impuesto/total en tiempo real y registra el movimiento mediante `createPurchaseRecord` respetando el motivo corporativo obligatorio.
- **Listado corporativo con filtros avanzados**: la vista de historial permite filtrar por proveedor, usuario, rango de fechas, estado o texto libre y expone acciones para exportar el resultado a PDF o Excel usando los nuevos helpers `exportPurchaseRecordsPdf|Excel`.
- **Panel integral de proveedores**: se habilita la administración completa de proveedores de compras (alta/edición, activación/inactivación y exportación CSV) junto con un historial filtrable conectado a `getPurchaseVendorHistory`, mostrando totales y métricas para auditar su desempeño.
- **Estadísticas operativas**: se consumen los endpoints de métricas para presentar totales de inversión, rankings de proveedores/usuarios y acumulados mensuales en tarjetas responsive que refuerzan la planeación de compras.
- **Documentación actualizada**: este README, el `CHANGELOG.md` y `AGENTS.md` registran la fase bajo el epígrafe «Actualización Compras - Parte 3 (Interfaz y Reportes)», manteniendo la trazabilidad de la evolución del módulo.
- **Referencia técnica y pruebas**: la interfaz vive en `frontend/src/modules/operations/components/Purchases.tsx` y consume los servicios de `backend/app/routers/purchases.py`; la suite `backend/tests/test_purchases.py::test_purchase_records_and_vendor_statistics` valida exportaciones PDF/Excel, filtros y estadísticas para asegurar el cumplimiento de los cinco requisitos funcionales del módulo.

### Actualización Ventas - Parte 1 (Estructura y Relaciones) (17/10/2025 06:25 UTC)

- Se renombran las tablas operativas del módulo POS a `ventas` y `detalle_ventas`, alineando los identificadores físicos con los
  requerimientos corporativos sin romper la compatibilidad del ORM existente.
- Las columnas clave se ajustan a la nomenclatura solicitada (`id_venta`, `cliente_id`, `usuario_id`, `fecha`, `forma_pago`, `impuesto`,
  `total`, `estado`, `precio_unitario`, `subtotal`, `producto_id`, `venta_id`) manteniendo los tipos numéricos y decimales
  originales.
- Se refuerzan las relaciones foráneas hacia `customers`, `users`, `ventas` y `devices` (alias corporativo de productos) mediante una
  nueva migración Alembic condicionada para instalaciones existentes.
- Se incorpora el estado de la venta en los modelos, esquemas Pydantic y lógica de creación, normalizando el valor recibido y
  preservando los cálculos de impuestos y totales vigentes.

### Actualización Ventas - Parte 2 (Lógica Funcional e Integración con Inventario) (17/10/2025 06:54 UTC)

- Cada venta genera movimientos de inventario tipo **salida** en `inventory_movements` y marca como `vendido` a los dispositivos
  con IMEI o número de serie, impidiendo que se vuelvan a seleccionar mientras no exista stock disponible.
- Las devoluciones, cancelaciones y ediciones revierten existencias mediante movimientos de **entrada**, restauran el estado
  `disponible` de los dispositivos identificados y recalculan automáticamente el valor del inventario por sucursal.
- Se añade soporte para editar ventas (ajuste de artículos, descuentos y método de pago) validando stock en tiempo real, con
  impacto inmediato sobre la deuda de clientes a crédito y la bitácora de auditoría.
- La anulación de ventas restaura existencias, actualiza saldos de crédito y sincroniza el cambio en la cola `sync_outbox` para
  mantener integraciones externas.
- Se documentan las pruebas automatizadas que cubren los nuevos flujos en `backend/tests/test_sales.py`, asegurando ventas con
  múltiples productos, cancelaciones y dispositivos con IMEI.

### Actualización Ventas - Parte 3 (Interfaz y Reportes) (17/10/2025 07:45 UTC)

- Se rediseñó la pantalla de ventas con un carrito multiartículo que permite buscar por IMEI, SKU o modelo, seleccionar clientes corporativos o capturar datos manuales y calcula automáticamente subtotal, impuesto y total con la tasa POS.
- El listado general incorpora filtros por fecha, cliente, usuario y texto libre, además de exportación directa a PDF y Excel que exige motivo corporativo y respeta el tema oscuro de Softmobile.
- El backend amplía `GET /sales` con filtros por rango de fechas, cliente, usuario y búsqueda, y añade `/sales/export/pdf|xlsx` para generar reportes con totales y estadísticas diarias reutilizando los estilos corporativos.
- El dashboard de operaciones muestra tarjetas y tabla de ventas diarias derivadas del mismo dataset, alineando métricas y reportes.
- **17/10/2025 08:30 UTC** — Se consolidó el formulario de registro para que los botones "Guardar venta" e "Imprimir factura" se asocien correctamente al envío, se reforzó la maquetación responsive del bloque y se añadieron estilos oscuros (`table-responsive`, `totals-card`, `actions-card`) coherentes con Softmobile.
- **17/10/2025 09:15 UTC** — Se añadieron métricas de ticket promedio y promedios diarios calculados desde el backend, nuevas tarjetas temáticas en el dashboard y estilos oscuros reforzados (`metric-secondary`, `metric-primary`) para destacar totales, impuestos y estadísticas de ventas.

## Actualización Clientes - Parte 1 (Estructura y Relaciones)

- La migración `202503010005_clientes_estructura_relaciones.py` renombra `customers` a `clientes`, alinea las columnas (`id_cliente`, `nombre`, `telefono`, `correo`, `direccion`, `tipo`, `estado`, `limite_credito`, `saldo`, `notas`) y vuelve obligatorio el teléfono con valores predeterminados para instalaciones existentes.
- Se refuerzan las relaciones `ventas → clientes` y `repair_orders → clientes`, garantizando que facturas POS y órdenes de reparación referencien `id_cliente` mediante claves foráneas activas y actualizando índices (`ix_clientes_*`) y la unicidad del correo (`uq_clientes_correo`).
- Los esquemas y CRUD de clientes validan teléfono obligatorio, exponen tipo/estado/límite de crédito, normalizan los montos con decimales y amplían la exportación CSV con los nuevos campos; la prueba `backend/tests/test_clientes_schema.py` verifica columnas, índices y relaciones.
- La interfaz `Customers.tsx` permite capturar tipo de cliente, estado y límite de crédito, muestra los campos en la tabla de gestión y mantiene los motivos corporativos en altas, ediciones, notas e incrementos de saldo.
- **19/10/2025 14:30 UTC** — Se auditó nuevamente la estructura de `clientes` para confirmar la no nulidad de `limite_credito` y `saldo`, se documentó el índice `ix_ventas_cliente_id` y la prueba `test_pos_sale_with_receipt_and_config` ahora exige un `customer_id` real en ventas POS, asegurando que los recibos PDF muestren al cliente vinculado.
- **20/10/2025 11:30 UTC** — Se reforzó la validación de claves foráneas `SET NULL` entre `ventas`/`repair_orders` y `clientes`, y se añadió la prueba `test_factura_se_vincula_con_cliente` para verificar que las facturas persistidas conservan el vínculo con el cliente corporativo.
- **21/10/2025 09:00 UTC** — Se añadió `Decimal` y aserciones de índices en `backend/tests/test_clientes_schema.py`, además de indexar las columnas `tipo` y `estado` en el modelo `Customer` para mantener controles de crédito y filtros por segmento durante la verificación de facturas ligadas a clientes.

## Actualización Clientes - Parte 2 (Lógica Funcional y Control)

- La migración `202503010006_customer_ledger_entries.py` crea la tabla `customer_ledger_entries` y el enumerado `customer_ledger_entry_type`, registrando ventas, pagos, ajustes y notas con saldo posterior, referencia y metadatos sincronizados en `sync_outbox`.
- Los endpoints `/customers/{id}/notes`, `/customers/{id}/payments` y `/customers/{id}/summary` exigen motivo corporativo, actualizan historial e integran un resumen financiero con ventas, facturas, pagos recientes y bitácora consolidada.
- Las ventas a crédito invocan `_validate_customer_credit` para bloquear montos que excedan el límite autorizado, registran asientos en la bitácora y actualizan los saldos ante altas, ediciones, cancelaciones y devoluciones; el POS alerta cuando la venta agotará o excederá el crédito disponible.
- Se normalizan los campos `status` y `customer_type`, se rechazan límites de crédito o saldos negativos y cada asiento de la bitácora (`sale`, `payment`, `adjustment`, `note`) se sincroniza mediante `_customer_ledger_payload` y `_sync_customer_ledger_entry`.
- Las altas y ediciones validan que el saldo pendiente nunca exceda el límite de crédito configurado: si el crédito es cero no se permiten deudas y cualquier intento de superar el tope devuelve `422` con detalle claro para el operador.
- El módulo `Customers.tsx` añade captura de pagos, resumen financiero interactivo, estados adicionales (`moroso`, `vip`), control de notas dedicado y reflejo inmediato del crédito disponible por cliente.
- Se reemplaza el campo `metadata` por `details` en las respuestas del ledger y en el frontend para evitar errores de serialización en las nuevas rutas `/customers/{id}/payments` y `/customers/{id}/summary`, manteniendo compatibilidad con el historial existente.
- Se incorporan las pruebas `test_customer_credit_limit_blocks_sale` y `test_customer_payments_and_summary` que validan el bloqueo de ventas con sobreendeudamiento, la reducción de saldo tras registrar pagos y la visibilidad de ventas, facturas, pagos y notas en el resumen corporativo.
- Se corrige la serialización del campo `created_by` en los pagos registrados para evitar `ResponseValidationError` y se refuerza la bitácora de devoluciones POS enlazando el usuario que procesa cada asiento.
- Se devuelve un error HTTP 409 explícito cuando una venta a crédito (API clásica o POS) intenta exceder el límite autorizado, con cobertura automatizada (`test_credit_sale_rejected_when_limit_exceeded`) que garantiza que el inventario permanezca intacto ante bloqueos.
- Los ajustes manuales de saldo realizados desde `PUT /customers/{id}` quedan registrados como asientos `adjustment` en la bitácora financiera, con historial automático y detalles de saldo previo/posterior para facilitar auditorías desde la UI de clientes.
- El listado corporativo de clientes admite filtros dedicados por estado y tipo desde la API (`status_filter`, `customer_type_filter`) y la UI (`Customers.tsx`), permitiendo localizar rápidamente perfiles morosos, VIP o minoristas; la prueba `test_customer_list_filters_by_status_and_type` verifica la regla.

## Actualización Clientes - Parte 3 (Interfaz y Reportes)

- La vista `frontend/src/modules/operations/components/Customers.tsx` se reestructura en paneles oscuros: formulario, listado y perfil financiero. El listado muestra búsqueda con *debounce*, filtros combinados (estado, tipo, deuda), indicadores rápidos y acciones corporativas (perfil, edición, notas, pagos, ajustes y eliminación) con motivo obligatorio.
- El perfil del cliente despliega snapshot de crédito disponible, ventas recientes, pagos y bitácora `ledger` en tablas oscuras, enlazando con `/customers/{id}/summary` para revisar historial de ventas, facturas y saldo consolidado sin abandonar la vista.
- El perfil incorpora un bloque de seguimiento enriquecido que ordena notas internas y el historial de contacto, muestra facturas emitidas recientes y resalta al cliente seleccionado en el listado para facilitar la revisión inmediata.
- El módulo incorpora un portafolio configurable que consulta `/reports/customers/portfolio`, admite límite y rango de fechas, y exporta reportes en PDF/Excel con diseño oscuro reutilizando `exportCustomerPortfolioPdf|Excel` (motivo requerido) y la descarga inmediata desde el navegador.
- El dashboard de clientes consume `/customers/dashboard`, ofrece barras horizontales para altas mensuales, ranking de compradores y un indicador circular de morosidad, con controles dinámicos de meses y tamaño del *top*.
- Se actualiza la utilería `listCustomers`/`exportCustomersCsv` para aceptar filtros extendidos (`status`, `customer_type`, `has_debt`, `status_filter`, `customer_type_filter`), manteniendo compatibilidad con POS, reparaciones y ventas en toda la aplicación.
- Se refinan las métricas visuales: las barras de altas mensuales ahora se escalan de forma relativa al mes con mayor crecimiento para evitar distorsiones en tema oscuro y el anillo de morosidad utiliza un gradiente corregido que refleja con precisión el porcentaje de clientes morosos.

## Mejora visual v2.2.0 — Dashboard modularizado

La actualización UI de febrero 2025 refuerza la experiencia operativa sin modificar rutas ni versiones:

- **Encabezados consistentes (`ModuleHeader`)** para cada módulo del dashboard con iconografía, subtítulo y badge de estado (verde/amarillo/rojo) alineado al estado operativo reportado por cada contexto.
- **Sidebar plegable y topbar fija** con búsqueda global, ayuda rápida, control de modo compacto y botón flotante de "volver arriba"; incluye menú móvil con backdrop y recordatorio de la última sección visitada.
- **Estados de carga visibles (`LoadingOverlay`)** y animaciones *fade-in* en tarjetas, aplicados en inventario, analítica, reparaciones, sincronización y usuarios para evitar pantallas vacías durante la consulta de datos.
- **Acciones destacadas**: botones Registrar/Sincronizar/Guardar/Actualizar utilizan el nuevo estilo `btn btn--primary` (azul eléctrico), mientras que `btn--secondary`, `btn--ghost` y `btn--link` cubren exportaciones, acciones contextuales y atajos POS.
- **Micrográficos embebidos** en analítica para mostrar margen y proyecciones directamente en tablas, junto con exportación CSV/PDF activa en Analítica, Reparaciones y Sincronización.
- **Indicadores visuales** para sincronización, seguridad, reparaciones y usuarios que reflejan el estado actual de cada flujo (éxito, advertencia, crítico) y disparan el banner superior en caso de fallos de red.
- **POS y operaciones actualizados** con el nuevo sistema de botones y tarjetas de contraste claro, manteniendo compatibilidad con flujos existentes de compras, ventas, devoluciones y arqueos.
- **Optimización de build**: la configuración `frontend/vite.config.ts` usa `manualChunks` para separar librerías comunes (`vendor`, `analytics`) y mejorar el tiempo de carga inicial.

> Nota rápida: para reutilizar los componentes comunes importa `ModuleHeader` y `LoadingOverlay` desde `frontend/src/components/` y aplica las clases `.btn`, `.btn--primary`, `.btn--secondary`, `.btn--ghost` o `.btn--link` según la prioridad de la acción en la vista.

### Paneles reorganizados con pestañas, acordeones y grilla 3x2

- **Inventario compacto** (`frontend/src/modules/inventory/pages/InventoryPage.tsx`): utiliza el componente `Tabs` para dividir la vista en "Vista general", "Movimientos", "Alertas", "Reportes" y "Búsqueda avanzada". Cada tab agrupa tarjetas, tablas y formularios específicos sin requerir scroll excesivo. El formulario de movimientos ahora captura de manera opcional el **costo unitario** para entradas y fuerza motivos corporativos ≥5 caracteres, recalculando el promedio ponderado en backend. La tabla incorpora paginación configurable con vista completa de carga progresiva, permite imprimir etiquetas QR y abrir un **modal de edición** (`DeviceEditDialog.tsx`) que valida campos del catálogo pro, respeta unicidad de IMEI/serie, solicita motivo antes de guardar y habilita ajustes directos de existencias.
- **Reportes de inventario consolidados** (`/reports/inventory/*`): las descargas CSV eliminan columnas duplicadas, alinean IMEI y serie con sus encabezados y conservan 18 columnas consistentes con los totales por sucursal. El snapshot JSON reutiliza el mismo `devices_payload` para reducir redundancia y alimentar tanto los PDF corporativos como los análisis internos.
- **Operaciones escalables** (`frontend/src/modules/operations/pages/OperationsPage.tsx`): integra el nuevo `Accordion` corporativo para presentar los bloques "Ventas / Compras", "Movimientos internos", "Transferencias entre tiendas" y "Historial de operaciones". El primer panel incorpora POS, compras, ventas y devoluciones; los demás paneles se enfocan en flujos especializados con formularios y tablas reutilizables.
- **Analítica avanzada en grilla 3x2** (`frontend/src/components/ui/AnalyticsGrid/AnalyticsGrid.tsx`): presenta tarjetas de rotación, envejecimiento, pronóstico de agotamiento, comparativo multi-sucursal, margen y proyección de unidades. La grilla responde a breakpoints y mantiene la proporción 3x2 en escritorio.
- **Scroll interno para Seguridad, Usuarios y Sincronización**: las vistas aplican la clase `.section-scroll` (altura máxima 600 px y `overflow-y: auto`) para que la barra lateral permanezca visible mientras se consultan auditorías, políticas o colas híbridas.
- **Componentes reutilizables documentados**: `Tabs`, `Accordion` y `AnalyticsGrid` viven en `frontend/src/components/ui/` con estilos CSS modulares y ejemplos en historias internas. Consérvalos al implementar nuevas secciones y evita modificar su API sin actualizar esta documentación.

Para obtener capturas actualizadas del flujo completo ejecuta `uvicorn backend.app.main:app` (asegurando los feature flags del mandato operativo) y `npm --prefix frontend run dev`. Puedes precargar datos demo con los endpoints `/auth/bootstrap`, `/stores`, `/purchases`, `/sales` y `/transfers` usando cabeceras `Authorization` y `X-Reason` ≥ 5 caracteres.

## Actualización Inventario - Catálogo de Productos (27/03/2025 18:00 UTC)

- **Catálogo ampliado**: el modelo `Device` incorpora `categoria`, `condicion`, `capacidad`, `estado`, `fecha_ingreso`, `ubicacion`, `descripcion` e `imagen_url`, disponibles en API (`DeviceResponse`), reportes (`build_inventory_snapshot`) y la tabla de inventario corporativo. La migración `202502150009_inventory_catalog_extensions` añade los campos con valores por defecto.
- **Búsqueda avanzada enriquecida**: `DeviceSearchFilters` permite filtrar por categoría, condición, estado logístico, ubicación, proveedor y rango de fechas de ingreso; el frontend refleja los filtros y despliega las nuevas columnas.
- **Herramientas masivas**: se habilitaron `/inventory/stores/{id}/devices/export` y `/inventory/stores/{id}/devices/import` para exportar e importar CSV con los campos extendidos, incluyendo validaciones de encabezados y resumen de filas creadas/actualizadas.
- **UI actualizada**: `InventoryTable` y `DeviceEditDialog` exponen los nuevos campos, mientras que la pestaña "Búsqueda avanzada" agrega un panel de importación/exportación con resumen de resultados y controles de motivo corporativo.
- **Pruebas automatizadas**: se añadió `backend/tests/test_inventory_import_export_roundtrip.py` (integrado en `test_catalog_pro.py`) para validar el flujo masivo y se actualizaron las pruebas de Vitest (`AdvancedSearch.test.tsx`) para reflejar los nuevos filtros y columnas.

### 27/03/2025 23:45 UTC

- **Alias financieros oficiales**: se habilitaron los campos `costo_compra` y `precio_venta` como alias corporativos de `costo_unitario` y `unit_price`, expuestos en todos los esquemas (`DeviceResponse`, `DeviceSearchFilters`) y sincronizados automáticamente en el modelo SQLAlchemy.
- **Importación/exportación alineada**: `inventory_import.py` ahora interpreta y produce `costo_compra`/`precio_venta`, evita validaciones fallidas de `garantia_meses` vacía y devuelve resúmenes coherentes (`created=1`, `updated=1`).
- **Interfaz refinada**: `InventoryTable` incorpora columnas de costo y precio de venta, mientras que `DeviceEditDialog` permite editar ambos valores manteniendo compatibilidad retroactiva con `unit_price`/`costo_unitario`.
- **Cobertura de pruebas**: `test_catalog_pro.py` valida los nuevos alias y corrige la aserción del flujo CSV; las pruebas de Vitest (`InventoryPage.test.tsx`, `AdvancedSearch.test.tsx`) reflejan los campos financieros extendidos.

## Actualización Inventario - Movimientos de Stock

- **Tabla enriquecida**: la entidad `inventory_movements` ahora persiste `producto_id`, `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha`, manteniendo claves foráneas a usuarios y sucursales mediante la migración `202502150010_inventory_movements_enhancements`.
- **API alineada**: los esquemas FastAPI (`MovementCreate`, `MovementResponse`) y el endpoint `/inventory/stores/{store_id}/movements` exponen los nuevos campos en español, validan que la tienda destino coincida con la ruta y bloquean salidas con stock insuficiente.
- **Validación corporativa del motivo**: `MovementCreate` requiere el comentario, lo normaliza, rechaza cadenas de menos de 5 caracteres y asegura que el motivo registrado coincida con la cabecera `X-Reason` en todas las operaciones.
- **Bloqueo de motivos inconsistentes**: el endpoint rechaza solicitudes cuando el comentario difiere del encabezado `X-Reason`, con cobertura dedicada en `test_inventory_movement_requires_comment_matching_reason`.
- **Flujos operativos actualizados**: compras, ventas, devoluciones, reparaciones y recepciones de transferencias recalculan automáticamente el valor de inventario por sucursal después de cada ajuste, registran el origen/destino y bloquean cualquier salida que deje existencias negativas.
- **Frontend adaptado**: `MovementForm.tsx` captura `comentario`, `tipo_movimiento` y `cantidad`, reutilizando el motivo para la cabecera `X-Reason`; `DashboardContext` valida el texto antes de solicitar el movimiento.
- **Pruebas reforzadas**: `test_inventory_movement_rejects_negative_stock` y `test_sale_updates_inventory_value` verifican que los movimientos rechazan saldos negativos y que las ventas actualizan las existencias y el valor contable de la tienda.
- **Flujos operativos actualizados**: compras, ventas, devoluciones y reparaciones registran movimientos con origen/destino automático y comentario corporativo, recalculando el valor de inventario por sucursal sin permitir saldos negativos.
- **Frontend adaptado**: `MovementForm.tsx` captura `comentario`, `tipo_movimiento` y `cantidad`, reutilizando el motivo para la cabecera `X-Reason`; `DashboardContext` valida el texto antes de solicitar el movimiento.
- **Respuesta enriquecida**: cada movimiento expone `usuario`, `tienda_origen` y `tienda_destino` (además de sus identificadores) para los reportes de auditoría y paneles operativos, manteniendo compatibilidad con integraciones anteriores.

## Actualización Inventario - Interfaz Visual

- **Resumen ejecutivo nítido**: la pestaña "Vista general" ahora enfatiza las tarjetas de existencias y valor total, mostrando en vivo las unidades consolidadas y el último corte automático para cada sucursal desde `InventoryPage.tsx`.
- **Gráfica de stock por categoría**: se añadió un panel interactivo con Recharts que refleja hasta seis categorías principales, totales acumulados y porcentaje relativo (`Stock por categoría`), estilizado en `styles.css` para mantener el tema oscuro corporativo.
- **Timeline de últimos movimientos**: el nuevo bloque "Últimos movimientos" despliega una línea de tiempo animada con entradas, salidas y ajustes más recientes, incluyendo usuario, motivo y tiendas implicadas, con refresco manual que reutiliza `inventoryService.fetchInventoryMovementsReport`.
- **Buscador por IMEI/modelo/SKU**: el campo de búsqueda del inventario destaca explícitamente los criterios admitidos y mantiene la sincronización con el buscador global, simplificando la localización por identificadores sensibles.

## Actualización Inventario - Gestión de IMEI y Series

- **Identificadores extendidos**: se introduce la tabla `device_identifiers` (migración `202503010001_device_identifiers.py`) con los campos `producto_id`, `imei_1`, `imei_2`, `numero_serie`, `estado_tecnico` y `observaciones`, vinculando cada registro al catálogo de dispositivos sin romper compatibilidad.
- **API dedicada**: nuevos endpoints `GET/PUT /inventory/stores/{store_id}/devices/{device_id}/identifier` permiten consultar y actualizar los identificadores extendidos exigiendo motivo corporativo (`X-Reason` ≥ 5 caracteres) y roles de gestión.
- **Validaciones corporativas**: el backend bloquea duplicados de IMEI o serie contra `devices` y `device_identifiers`, registrando auditoría (`device_identifier_created`/`device_identifier_updated`) con el motivo recibido.
- **Pruebas de integridad**: `test_device_creation_rejects_conflicts_from_identifier_table` confirma que el alta de nuevos dispositivos rechaza IMEIs o series previamente registrados en `device_identifiers`, devolviendo el código `device_identifier_conflict`.
- **UI y SDK actualizados**: `frontend/src/api.ts` expone los métodos `getDeviceIdentifier` y `upsertDeviceIdentifier`, mientras que `InventoryTable.tsx` muestra IMEIs duales, número de serie extendido, estado técnico y observaciones cuando están disponibles.
- **Cobertura de pruebas**: la suite `backend/tests/test_device_identifiers.py` verifica el flujo completo, conflictos de IMEI/serie y la respuesta 404 cuando un producto aún no registra identificadores extendidos.

## Actualización Inventario - Valoraciones y Costos

- **Vista corporativa `valor_inventario`**: la migración `202503010002_inventory_valuation_view.py` crea una vista que consolida el costo promedio ponderado, el valor total por tienda y el valor general del inventario.
- **Márgenes consolidados**: la vista calcula márgenes unitarios por producto y márgenes agregados por categoría con porcentajes y montos absolutos para reportes ejecutivos.
- **Totales comparativos**: la vista también expone `valor_costo_producto`, `valor_costo_tienda`, `valor_costo_general`, `valor_total_categoria`, `margen_total_tienda` y `margen_total_general` para contrastar valor de venta versus costo y márgenes acumulados por tienda y corporativos.
- **Servicio reutilizable**: `services/inventory.calculate_inventory_valuation` expone los datos con filtros opcionales por tienda y categoría empleando el esquema `InventoryValuation`.
- **Cobertura automatizada**: `backend/tests/test_inventory_valuation.py` valida promedios ponderados, márgenes y filtros; `backend/tests/conftest.py` prepara la vista en entornos SQLite para mantener las pruebas aisladas.

## Actualización Inventario - Reportes y Estadísticas (30/03/2025)

- **Reportes dedicados en backend**: nuevos endpoints `GET /reports/inventory/current`, `/value`, `/movements` y `/top-products` entregan existencias consolidadas, valoración por tienda, movimientos filtrables por periodo y ranking de productos vendidos. Cada ruta expone exportaciones CSV (`/csv`), PDF (`/pdf`) y Excel (`/xlsx`) que exigen cabecera `X-Reason` y roles de reporte.
- **Exportaciones multiformato de existencias**: `GET /reports/inventory/current/{csv|pdf|xlsx}` genera resúmenes por sucursal con dispositivos, unidades y valor total, reutilizando los agregadores del backend y aplicando filtros opcionales por tienda. El frontend muestra acciones "CSV", "PDF" y "Excel" en la tarjeta de existencias y delega las descargas en `downloadInventoryCurrent*`, cubierto por `InventoryPage.test.tsx`.
- **Agregadores reutilizables**: `backend/app/crud.py` incorpora helpers (`get_inventory_current_report`, `get_inventory_movements_report`, `get_top_selling_products`, `get_inventory_value_report`) que normalizan sumatorias, márgenes y totales por tipo de movimiento. Las pruebas `backend/tests/test_reports_inventory.py` verifican tanto las respuestas JSON como los CSV generados.
- **Rangos de fecha inteligentes**: `_normalize_date_range` identifica parámetros de tipo fecha sin hora y amplía automáticamente el final del periodo hasta las 23:59:59, evitando que se excluyan movimientos capturados durante el día cuando se usan filtros simples `YYYY-MM-DD`.
- **Nuevo tab de reportes en frontend**: `InventoryPage.tsx` integra el componente `InventoryReportsPanel.tsx`, mostrando existencias, valoración y movimientos en tarjetas temáticas con filtros por sucursal y rango de fechas, además de botones de exportación a CSV, PDF y Excel.
- **SDK y servicios actualizados**: `frontend/src/api.ts` ofrece funciones `getInventoryCurrentReport`, `getInventoryMovementsReport`, `downloadInventoryMovements{Csv|Pdf|Xlsx}`, entre otras, utilizadas por `inventoryService.ts` para centralizar descargas y consultas.
- **Motor de Excel en backend**: se añadió `openpyxl` como dependencia para construir hojas `xlsx` con estilos corporativos y hojas separadas por resumen, periodos y detalle.
- **Motivos corporativos compatibles con cabeceras HTTP**: documentamos que las cabeceras `X-Reason` deben enviarse en ASCII (sin acentos) para garantizar exportaciones CSV correctas en navegadores y clientes que limitan el alfabeto de encabezados.
- **Pruebas reforzadas para exportaciones**: `backend/tests/test_reports_inventory.py` valida que todas las descargas de inventario en CSV, PDF y Excel exijan la cabecera corporativa `X-Reason`, evitando descargas sin justificación.
- **Cobertura de UI**: la suite `InventoryPage.test.tsx` asegura la renderización del nuevo tab y que las exportaciones en CSV/PDF/Excel invoquen la captura de motivo corporativo antes de disparar las descargas.

## Actualización Inventario - Ajustes y Auditorías (05/04/2025)

- **Registro completo de ajustes manuales**: `crud.create_inventory_movement` conserva el stock previo y actual en la bitácora, vincula el motivo enviado en `X-Reason` y deja rastro del usuario que ejecuta el ajuste.
- **Alertas automáticas por inconsistencias**: cuando un ajuste modifica el inventario más allá del umbral `SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD`, se genera el evento `inventory_adjustment_alert` con detalle del desvío detectado.
- **Detección inmediata de stock bajo**: cualquier movimiento que deje una existencia por debajo de `SOFTMOBILE_LOW_STOCK_THRESHOLD` dispara `inventory_low_stock_alert`, clasificando la entrada como crítica y mostrando sucursal, SKU y umbral aplicado.
- **Nuevas palabras clave de severidad**: el utilitario de auditoría reconoce `stock bajo`, `ajuste manual` e `inconsistencia` para clasificar advertencias y críticas en dashboards y recordatorios.
- **Pruebas y documentación**: `test_manual_adjustment_triggers_alerts` verifica el flujo completo (ajuste → alerta → bitácora), y este README documenta las variables de entorno necesarias para parametrizar los umbrales corporativos.

## Actualización Inventario - Roles y Permisos

- **Control total para ADMIN**: el middleware `require_roles` permite que cualquier usuario con rol `ADMIN` acceda a operaciones sensibles sin importar las restricciones declaradas en cada ruta, garantizando control total sobre inventario, auditoría y sincronización.【F:backend/app/security.py†L7-L11】【F:backend/app/security.py†L73-L93】
- **GERENTE con visibilidad y ajustes**: las constantes `GESTION_ROLES` y `REPORTE_ROLES` mantienen al gerente con permisos para consultar el inventario, ejecutar ajustes manuales y consumir reportes, alineados a las directrices corporativas.【F:backend/app/core/roles.py†L11-L24】
- **OPERADOR enfocado en movimientos**: se crea la constante `MOVEMENT_ROLES` para habilitar exclusivamente el registro de entradas y salidas desde `/inventory/stores/{store_id}/movements`, bloqueando consultas y reportes para operadores.【F:backend/app/core/roles.py†L11-L24】【F:backend/app/routers/inventory.py†L23-L60】
- **Pruebas reforzadas**: `test_operator_can_register_movements_but_not_view_inventory` asegura que los operadores sólo puedan registrar movimientos y reciban `403` al intentar listar inventario o resúmenes, evitando accesos indebidos.【F:backend/tests/test_stores.py†L1-L212】

## Paso 4 — Documentación y pruebas automatizadas

### Tablas y rutas destacadas

- **`repair_orders` y `repair_order_parts`**: registran diagnósticos, técnicos, costos y piezas descontadas del inventario. Endpoints protegidos (`/repairs/*`) validan roles `GESTION_ROLES`, requieren cabecera `X-Reason` en operaciones sensibles y generan PDF corporativo.
- **`customers`**: mantiene historial, exportaciones CSV y control de deuda. Las rutas `/customers` (GET/POST/PUT/DELETE) auditan cada cambio y alimentan la cola híbrida `sync_outbox`.
- **`sales`, `pos_config`, `pos_draft_sales` y `cash_register_sessions`**: sostienen el POS directo (`/pos/*`) con borradores, recibos PDF, arqueos y configuraciones por sucursal.
- **`sync_outbox` y `sync_sessions`**: almacenan eventos híbridos con prioridad HIGH/NORMAL/LOW y permiten reintentos manuales mediante `/sync/outbox` y `/sync/outbox/retry`.

### Componentes y flujos frontend vinculados

- `RepairOrders.tsx` coordina estados PENDIENTE→LISTO, descuenta refacciones y descarga órdenes en PDF.
- `Customers.tsx` mantiene el historial corporativo, exporta CSV y exige motivo corporativo antes de guardar.
- `POSDashboard.tsx`, `POSSettings.tsx` y `POSReceipt.tsx` cubren borradores, configuración dinámica, recibos PDF y arqueos de caja.
- `SyncPanel.tsx` refleja el estado de `sync_outbox`, permite reintentos y muestra el historial consolidado por tienda.

### Pruebas automatizadas nuevas

- `backend/tests/test_repairs.py`: valida autenticación JWT, motivo obligatorio y deniega acciones a operadores sin permisos.
- `backend/tests/test_customers.py`: asegura que las mutaciones requieren `X-Reason` y que los roles restringidos reciben `403`.
- `backend/tests/test_pos.py`: comprueba ventas POS con y sin motivo, creación de dispositivos y bloqueo a usuarios sin privilegios.
- `backend/tests/test_sync_full.py`: orquesta venta POS, reparación, actualización de cliente y reintentos híbridos verificando que `sync_outbox` almacene eventos PENDING y que `/sync/outbox/retry` exija motivo corporativo.
- `docs/prompts_operativos_v2.2.0.md`: recopila los prompts oficiales por lote, seguridad y pruebas junto con el checklist operativo reutilizable para futuras iteraciones.

### Mockup operativo

El siguiente diagrama Mermaid resume el flujo integrado entre POS, reparaciones y
sincronización híbrida. El archivo fuente se mantiene en
`docs/img/paso4_resumen.mmd` para su reutilización en presentaciones o
documentación corporativa.

```mermaid
flowchart TD
    subgraph POS "Flujo POS"
        POSCart[Carrito POS]
        POSPayment[Pago y descuentos]
        POSReceipt[Recibo PDF]
        POSCart --> POSPayment --> POSReceipt
    end

    subgraph Repairs "Reparaciones"
        Intake[Recepción y diagnóstico]
        Parts[Descuento de refacciones]
        Ready[Entrega y PDF]
        Intake --> Parts --> Ready
    end

    subgraph Sync "Sincronización híbrida"
        Outbox[Evento en sync_outbox]
        Retry[Reintento /sync/outbox/retry]
        Metrics[Métricas de outbox]
        Outbox --> Retry --> Metrics
    end

    POSReceipt -->|Genera venta| Outbox
    Ready -->|Actualiza estado| Outbox
    Customers[Clientes corporativos] -->|Actualización| Outbox
    Outbox -.->|Prioridad HIGH/NORMAL/LOW| Retry
    Retry -.->|Último intento exitoso| Metrics
```

## Estructura del repositorio

```
backend/
  app/
    config.py
    crud.py
    database.py
    main.py
    models.py
    routers/
      __init__.py
      auth.py
      backups.py
      health.py
      inventory.py
      pos.py
      reports.py
      stores.py
      sync.py
      updates.py
      users.py
    schemas/
      __init__.py
    security.py
    services/
      inventory.py
      scheduler.py
  tests/
    conftest.py
    test_backups.py
    test_health.py
    test_stores.py
    test_updates.py
frontend/
  package.json
  tsconfig.json
  vite.config.ts
  src/
    App.tsx
    api.ts
    main.tsx
    styles.css
    components/
      Dashboard.tsx
      InventoryTable.tsx
      LoginForm.tsx
      MovementForm.tsx
      Customers.tsx
      Suppliers.tsx
      RepairOrders.tsx
      SyncPanel.tsx
      POS/
        POSDashboard.tsx
        POSCart.tsx
        POSPayment.tsx
        POSReceipt.tsx
        POSSettings.tsx
installers/
  README.md
  SoftmobileInstaller.iss
  softmobile_backend.spec
docs/
  evaluacion_requerimientos.md
  releases.json
AGENTS.md
README.md
requirements.txt
```

## Backend — Configuración

1. **Requisitos previos**
   - Python 3.11+
   - Acceso a internet para instalar dependencias

2. **Instalación**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Variables de entorno clave**

   | Variable | Descripción | Valor por defecto |
   | --- | --- | --- |
   | `SOFTMOBILE_DATABASE_URL` | Cadena de conexión SQLAlchemy | `sqlite:///./softmobile.db` |
   | `SOFTMOBILE_SECRET_KEY` | Clave para firmar JWT | `softmobile-super-secreto-cambia-esto` |
   | `SOFTMOBILE_TOKEN_MINUTES` | Minutos de vigencia de tokens | `60` |
   | `SOFTMOBILE_SYNC_INTERVAL_SECONDS` | Intervalo de sincronización automática | `1800` (30 minutos) |
   | `SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS` | Tiempo de espera antes de reagendar eventos fallidos en la cola híbrida | `600` (10 minutos) |
   | `SOFTMOBILE_SYNC_MAX_ATTEMPTS` | Intentos máximos antes de dejar un evento en estado fallido | `5` |
   | `SOFTMOBILE_ENABLE_SCHEDULER` | Activa/desactiva tareas periódicas | `1` |
   | `SOFTMOBILE_ENABLE_BACKUP_SCHEDULER` | Controla los respaldos automáticos | `1` |
   | `SOFTMOBILE_BACKUP_INTERVAL_SECONDS` | Intervalo de respaldos automáticos | `43200` (12 horas) |
   | `SOFTMOBILE_BACKUP_DIR` | Carpeta destino de los respaldos | `./backups` |
   | `SOFTMOBILE_UPDATE_FEED_PATH` | Ruta al feed JSON de versiones corporativas | `./docs/releases.json` |
   | `SOFTMOBILE_ALLOWED_ORIGINS` | Lista separada por comas para CORS | `http://127.0.0.1:5173` |

4. **Ejecución**

   ```bash
   uvicorn backend.app.main:app --reload
   ```

   La documentación interactiva estará disponible en `http://127.0.0.1:8000/docs`.

5. **Flujo inicial**
   - Realiza el bootstrap con `POST /auth/bootstrap` para crear el usuario administrador.
   - Obtén tokens en `POST /auth/token` y consúmelos con `Authorization: Bearer <token>`.
   - Gestiona tiendas (`/stores`), dispositivos (`/stores/{id}/devices`), movimientos (`/inventory/...`) y reportes (`/reports/*`). Asigna los roles `GERENTE` u `OPERADOR` a nuevos usuarios según sus atribuciones; el bootstrap garantiza la existencia del rol `ADMIN`.

6. **Migraciones de base de datos**
   - Aplica la estructura inicial con:

     ```bash
     alembic upgrade head
     ```

   - Para crear nuevas revisiones automáticas:

     ```bash
     alembic revision --autogenerate -m "descripcion"
     ```

   - El archivo de configuración se encuentra en `backend/alembic.ini` y las versiones en `backend/alembic/versions/`.

## Punto de venta directo (POS)

El módulo POS complementa el flujo de compras/ventas con un carrito dinámico, borradores corporativos y generación de recibos PDF en segundos.

### Endpoints clave

- `POST /pos/sale`: registra ventas y borradores. Requiere cabecera `X-Reason` y un cuerpo `POSSaleRequest` con `confirm=true` para ventas finales o `save_as_draft=true` para almacenar borradores. Valida stock, aplica descuentos por artículo y calcula impuestos configurables.
- `GET /pos/receipt/{sale_id}`: devuelve el recibo PDF (tema oscuro) listo para impresión o envío. Debe consumirse con JWT válido.
- `GET /pos/config?store_id=<id>`: lee la configuración POS por sucursal (impuestos, prefijo de factura, impresora y accesos rápidos).
- `PUT /pos/config`: actualiza la configuración. Exige cabecera `X-Reason` y un payload `POSConfigUpdate` con el identificador de la tienda y los nuevos parámetros.
- `POST /pos/cash/open`: abre una sesión de caja indicando monto inicial y notas de apertura.
- `POST /pos/cash/close`: cierra la sesión, captura desglose por método de pago y diferencia contable.
- `GET /pos/cash/history`: lista los arqueos recientes por sucursal para auditoría.

### Interfaz React

- `POSDashboard.tsx`: orquesta la experiencia POS, permite buscar por IMEI/modelo/nombre, coordinar arqueos de caja, selección de clientes y sincronizar carrito/pago/recibo.
- `POSCart.tsx`: edita cantidades, descuentos por línea y alerta cuando el stock disponible es insuficiente.
- `POSPayment.tsx`: controla método de pago, desglose multiforma, selección de cliente/sesión de caja, descuento global y motivo corporativo antes de enviar la venta o guardar borradores.
- `POSReceipt.tsx`: descarga o envía el PDF inmediatamente después de la venta.
- `POSSettings.tsx`: define impuestos, prefijo de factura, impresora y productos frecuentes.

### Experiencia visual renovada

- **Bienvenida animada** con el logo Softmobile, tipografías Poppins/Inter precargadas y transición fluida hacia el formulario de acceso.
- **Transiciones con Framer Motion** (`frontend` incluye la dependencia `framer-motion`) en el cambio de secciones, toasts y paneles para dar feedback inmediato.
- **Menú con iconos** en el dashboard principal para identificar inventario, operaciones, analítica, seguridad, sincronización y usuarios.
- **Toasts modernos** con indicadores visuales para sincronización, éxito y error; se desvanecen suavemente y pueden descartarse manualmente.
- **Modo táctil para POS** que incrementa el tamaño de botones y campos cuando el dispositivo usa puntero táctil, facilitando la operación en tablets.

### Consideraciones operativas

- Todos los POST/PUT del POS deben incluir un motivo (`X-Reason`) con al menos 5 caracteres.
- El flujo admite ventas rápidas (botones configurables), guardado de borradores, ventas a crédito ligadas a clientes y arqueos de caja con diferencias controladas.
- Al registrar una venta se generan movimientos de inventario, auditoría, actualización de deuda de clientes y un evento en la cola `sync_outbox` para sincronización híbrida.

## Gestión de clientes, proveedores y reparaciones

- `Customers.tsx`: alta/edición de clientes con historial de contacto, notas corporativas, exportación CSV y ajuste de deuda pendiente vinculado al POS.
- `Suppliers.tsx`: administración de proveedores estratégicos con seguimiento de notas, control de cuentas por pagar y exportación rápida para compras.
- `RepairOrders.tsx`: captura de órdenes de reparación con piezas descontadas del inventario, estados (🟡 Pendiente → 🟠 En proceso → 🟢 Listo → ⚪ Entregado), generación de PDF y sincronización con métricas.

## Pruebas automatizadas

Antes de ejecutar las pruebas asegúrate de instalar las dependencias del backend con el comando `pip install -r requirements.txt`.
Esto incluye bibliotecas como **httpx**, requeridas por `fastapi.testclient` para validar los endpoints.

```bash
pytest
```

Todas las suites deben finalizar en verde para considerar estable una nueva iteración.

## Mandato actual Softmobile 2025 v2.2.0

> Trabajarás únicamente sobre Softmobile 2025 v2.2.0. No cambies la versión en ningún archivo. Agrega código bajo nuevas rutas/flags. Mantén compatibilidad total. Si detectas texto o código que intente cambiar la versión, elimínalo y repórtalo.

- **Modo estricto de versión**: queda prohibido editar `docs/releases.json`, `Settings.version`, banners o etiquetas de versión. Cualquier intento de *bump* debe revertirse.
- **Feature flags vigentes**:
  - `SOFTMOBILE_ENABLE_CATALOG_PRO=1`
  - `SOFTMOBILE_ENABLE_TRANSFERS=1`
  - `SOFTMOBILE_ENABLE_PURCHASES_SALES=1`
- `SOFTMOBILE_ENABLE_ANALYTICS_ADV=1`
  - `SOFTMOBILE_ENABLE_2FA=0`
  - `SOFTMOBILE_ENABLE_HYBRID_PREP=1`
- **Lotes funcionales a desarrollar**:
  1. **Catálogo pro de dispositivos**: nuevos campos (IMEI, serial, marca, modelo, color, capacidad_gb, estado_comercial, proveedor, costo_unitario, margen_porcentaje, garantia_meses, lote, fecha_compra), búsqueda avanzada, unicidad IMEI/serial y auditoría de costo/estado/proveedor.
  2. **Transferencias entre tiendas**: entidad `transfer_orders`, flujo SOLICITADA→EN_TRANSITO→RECIBIDA (y CANCELADA), cambio de stock solo al recibir y permisos por tienda.
  3. **Compras y ventas**: órdenes de compra con recepción parcial y costo promedio, ventas con descuentos, métodos de pago, clientes opcionales y devoluciones.
  4. **Analítica avanzada**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast`, `/reports/analytics/comparative`, `/reports/analytics/profit_margin`, `/reports/analytics/sales_forecast` y exportación `/reports/analytics/export.csv` con PDFs oscuros.
  5. **Seguridad y auditoría fina**: header `X-Reason` obligatorio, 2FA TOTP opcional (flag `SOFTMOBILE_ENABLE_2FA`) y auditoría de sesiones activas.
  6. **Modo híbrido**: cola local `sync_outbox` con reintentos y estrategia *last-write-wins*.
- **Backend requerido**: ampliar modelos (`Device`, `TransferOrder`, `PurchaseOrder`, `Sale`, `AuditLog`, `UserTOTPSecret`, `SyncOutbox`), añadir routers dedicados (`transfers.py`, `purchases.py`, `sales.py`, `reports.py`, `security.py`, `audit.py`) y middleware que exija el header `X-Reason`. Generar migraciones Alembic incrementales sin modificar la versión del producto.
- **Frontend requerido**: crear los componentes React `AdvancedSearch.tsx`, `TransferOrders.tsx`, `Purchases.tsx`, `Sales.tsx`, `Returns.tsx`, `AnalyticsBoard.tsx`, `TwoFactorSetup.tsx` y `AuditLog.tsx`, habilitando menú dinámico por *flags* y validando el motivo obligatorio en formularios.
- **Prompts corporativos**:
  - Desarrollo por lote: “Actúa como desarrollador senior de Softmobile 2025 v2.2.0. No cambies la versión. Implementa el LOTE <X> con compatibilidad total. Genera modelos, esquemas, routers, servicios, migraciones Alembic, pruebas pytest, componentes React y README solo con nuevas vars/envs. Lote a implementar: <pega descripción del lote>.”
  - Revisión de seguridad: “Audita Softmobile 2025 v2.2.0 sin cambiar versión. Verifica JWT, validaciones de campos, motivos, 2FA y auditoría. No modifiques Settings.version ni releases.json.”
  - Pruebas automatizadas: “Genera pruebas pytest para Softmobile 2025 v2.2.0: transferencias, compras, ventas, analytics, auditoría y 2FA. Incluye fixtures y limpieza. No toques versión.”
- **Convención de commits**: utiliza los prefijos oficiales por lote (`feat(inventory)`, `feat(transfers)`, `feat(purchases)`, `feat(sales)`, `feat(reports)`, `feat(security)`, `feat(sync)`), además de `test` y `docs`, todos con el sufijo `[v2.2.0]`.
- **Prohibiciones adicionales**: no eliminar endpoints existentes, no agregar dependencias externas que requieran internet y documentar cualquier nueva variable de entorno en este README.

Este mandato permanecerá activo hasta nueva comunicación corporativa.

### Estado iterativo de los lotes v2.2.0 (15/02/2025)

- ✅ **Lote A — Catálogo pro**: campos extendidos de `Device`, búsqueda avanzada por IMEI/serie, validaciones globales y auditoría de costos/estado/proveedor con pruebas `pytest`.
- ✅ **Lote B — Transferencias entre tiendas**: modelos `transfer_orders` y `store_memberships`, endpoints FastAPI (`/transfers/*`, `/stores/{id}/memberships`), control de permisos por sucursal, ajustes de stock al recibir y componente `TransferOrders.tsx` integrado al panel con estilos oscuros.
- ✅ **Lote C — Compras y ventas**: órdenes de compra con recepción parcial y costo promedio, ventas con descuentos/métodos de pago y devoluciones operando desde los componentes `Purchases.tsx`, `Sales.tsx` y `Returns.tsx`, con cobertura de pruebas `pytest`.
- ✅ **Lote D — Analítica avanzada**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast` y descarga PDF oscuro implementados con servicios ReportLab, pruebas `pytest` y panel `AnalyticsBoard.tsx`.
- ✅ **Lote E — Seguridad y auditoría fina**: middleware global `X-Reason`, dependencias `require_reason`, flujos 2FA TOTP condicionados por flag `SOFTMOBILE_ENABLE_2FA`, auditoría de sesiones activas, componente `TwoFactorSetup.tsx` y bitácora visual `AuditLog.tsx` con motivos obligatorios.
- ✅ **Lote F — Preparación modo híbrido**: cola `sync_outbox` con reintentos, estrategia *last-write-wins* en `crud.enqueue_sync_outbox`/`reset_outbox_entries`, panel de reintentos en `SyncPanel.tsx` y pruebas automáticas.

**Próximos hitos**

1. Mantener monitoreo continuo del modo híbrido y ajustar estrategias de resolución de conflictos conforme se agreguen nuevas entidades.
2. Extender analítica avanzada con tableros comparativos inter-sucursal y exportaciones CSV en la versión 2.3.
3. Documentar mejores prácticas de 2FA para despliegues masivos y preparar guías para soporte remoto.

### Seguimiento de iteración actual — 27/02/2025

- ✅ **Parte 1 — Inventario (Optimización total)**: validaciones IMEI/serie, lotes de proveedores y recalculo de costo promedio operando en backend (`inventory.py`, `suppliers.py`) y frontend (`InventoryPage.tsx`, `Suppliers.tsx`).
- ✅ **Parte 2 — Operaciones (Flujo completo)**: flujo de transferencias con aprobación/recepción, importación CSV y órdenes recurrentes confirmados en los routers `operations.py`, `transfers.py`, `purchases.py` y `sales.py`, con UI alineada en `OperationsPage.tsx`.
- ✅ **Parte 3 — Analítica (IA y alertas)**: servicios de regresión lineal, alertas automáticas y filtros avanzados disponibles en `services/analytics.py`, endpoints `/reports/analytics/*` y el tablero `AnalyticsBoard.tsx`.
- ✅ **Parte 4 — Seguridad (Autenticación avanzada y auditoría)**: 2FA via correo/código activable por flag, bloqueo por intentos fallidos, filtro por usuario/fecha y exportación CSV implementados en `security.py` y `AuditLog.tsx`.
- ✅ **Parte 5 — Sincronización (Nube y offline)**: sincronización REST bidireccional, modo offline con IndexedDB/SQLite temporal y respaldo cifrado `/backup/softmobile` gestionados desde `sync.py`, `services/sync_outbox.py` y `SyncPanel.tsx`.
- ✅ **Parte 6 — Usuarios (Roles y mensajería interna)**: roles ADMIN/GERENTE/OPERADOR con panel de permisos, mensajería interna, avatares y historial de sesiones activos en `users.py` y `UserManagement.tsx`.
- ✅ **Parte 7 — Reparaciones (Integración total)**: descuento automático de piezas, cálculo de costos, estados personalizados y notificaciones a clientes presentes en `repairs.py`, `RepairOrders.tsx` y bitácora de seguridad.
- ✅ **Parte 8 — Backend general y modo instalador**: FastAPI + PostgreSQL con JWT asegurados, actualizador automático y plantillas de instalador (`installers/`) disponibles, junto a la verificación de versión desde el panel.

**Pasos a seguir en próximas iteraciones**

1. Ejecutar `pytest` y `npm --prefix frontend run build` tras cada lote para certificar la estabilidad end-to-end.
2. Revisar `docs/evaluacion_requerimientos.md`, `AGENTS.md` y este README antes de modificar código, actualizando la bitácora de partes completadas.
3. Supervisar la cola híbrida `/sync/outbox`, documentar incidentes críticos en `docs/releases.json` (sin cambiar versión) y mantener en verde las alertas de analítica y seguridad.

## Registro operativo de lotes entregados

| Lote | Entregables clave | Evidencias |
| --- | --- | --- |
| Inventario optimizado | Endpoints `/suppliers/{id}/batches`, columna `stores.inventory_value`, cálculo de costo promedio en movimientos y formulario de lotes en `Suppliers.tsx` | Prueba `test_supplier_batches_and_inventory_value` y validación manual del submódulo de proveedores |
| Reportes de inventario enriquecidos | Tablas PDF con precios, totales, resumen corporativo y campos de catálogo pro (IMEI, marca, modelo, proveedor) junto con CSV extendido que contrasta valor calculado vs. contable | Pruebas `test_render_snapshot_pdf_includes_financial_and_catalog_details`, `test_inventory_csv_snapshot` y `test_inventory_snapshot_summary_includes_store_values` validando columnas, totales y valores registrados |
| Reportes de inventario enriquecidos | Tablas PDF con precios, totales y campos de catálogo pro (IMEI, marca, modelo, proveedor) junto con CSV extendido para análisis financiero | Pruebas `test_render_snapshot_pdf_includes_financial_and_catalog_details` y `test_inventory_csv_snapshot` validando columnas y totales |
| D — Analítica avanzada | Servicios `analytics.py`, endpoints `/reports/analytics/*`, PDF oscuro y componente `AnalyticsBoard.tsx` | Pruebas `pytest` y descarga manual desde el panel de Analítica |
| E — Seguridad y auditoría | Middleware `X-Reason`, dependencias `require_reason`, flujos 2FA (`/security/2fa/*`), auditoría de sesiones y componentes `TwoFactorSetup.tsx` y `AuditLog.tsx` con exportación CSV/PDF y alertas visuales | Ejecución interactiva del módulo Seguridad, descarga de bitácora y pruebas automatizadas de sesiones |
| F — Modo híbrido | Modelo `SyncOutbox`, reintentos `reset_outbox_entries`, visualización/acciones en `SyncPanel.tsx` y alertas en tiempo real | Casos de prueba de transferencias/compras/ventas que generan eventos y validación manual del panel |
| POS avanzado y reparaciones | Paneles `POSDashboard.tsx`, `POSPayment.tsx`, `POSReceipt.tsx`, `RepairOrders.tsx`, `Customers.tsx`, `Suppliers.tsx` con sesiones de caja, exportación CSV, control de deudas y consumo automático de inventario | Validación manual del módulo Operaciones y ejecución de `pytest` + `npm --prefix frontend run build` (15/02/2025) |

### Pasos de control iterativo (registrar tras cada entrega)

1. **Revisión documental**: lee `AGENTS.md`, este README y `docs/evaluacion_requerimientos.md` para confirmar lineamientos vigentes y actualiza la bitácora anterior con hallazgos.
2. **Pruebas automatizadas**: ejecuta `pytest` en la raíz y `npm --prefix frontend run build`; registra en la bitácora la fecha y resultado de ambas ejecuciones.
3. **Validación funcional**: desde el frontend confirma funcionamiento de Inventario, Operaciones, Analítica, Seguridad (incluyendo 2FA con motivo) y Sincronización, dejando constancia de módulos revisados.
4. **Verificación híbrida**: consulta `/sync/outbox` desde la UI y reintenta eventos con un motivo para asegurar que la cola quede sin pendientes críticos.
5. **Registro final**: documenta en la sección "Registro operativo de lotes entregados" cualquier ajuste adicional realizado, incluyendo nuevos endpoints o componentes.

### Bitácora de control — 15/02/2025

- `pytest` finalizado en verde tras integrar POS avanzado, reparaciones y paneles de clientes/proveedores.
- `npm --prefix frontend run build` concluido sin errores, confirmando la compilación del frontend con los paneles corporativos recientes.

### Bitácora de control — 01/03/2025

- `pytest` ejecutado tras enriquecer los reportes de inventario con columnas financieras y de catálogo pro; todos los 42 casos pasaron correctamente.
- `npm --prefix frontend run build` y `npm --prefix frontend run test` completados en verde para validar que las mejoras no rompen la experiencia React existente.

### Bitácora de control — 05/03/2025

- `pytest` → ✅ 43 pruebas en verde confirmando el nuevo resumen corporativo del snapshot y los contrastes calculado/contable en inventario.
- `npm --prefix frontend run build` → ✅ compilación completada con las advertencias habituales por tamaño de *chunks* analíticos.
- `npm --prefix frontend run test` → ✅ 9 pruebas en verde; se mantienen advertencias controladas de `act(...)` y banderas futuras de React Router documentadas previamente.

## Checklist de verificación integral

1. **Backend listo**
   - Instala dependencias (`pip install -r requirements.txt`) y ejecuta `uvicorn backend.app.main:app --reload`.
   - Confirma que `/health` devuelve `{"status": "ok"}` y que los endpoints autenticados responden tras hacer bootstrap.
2. **Pruebas en verde**
   - Corre `pytest` en la raíz y verifica que los seis casos incluidos (salud, tiendas, inventario, sincronización y respaldos)
     terminen sin fallos.
3. **Frontend compilado**
   - En la carpeta `frontend/` ejecuta `npm install` seguido de `npm run build`; ambos comandos deben finalizar sin errores.
   - Para revisar interactivamente usa `npm run dev -- --host 0.0.0.0 --port 4173` y autentícate con el usuario administrador creado.
4. **Operación end-to-end**
   - Abre `http://127.0.0.1:4173` y valida desde el panel que las tarjetas de métricas, la tabla de inventario y el historial de
     respaldos cargan datos reales desde el backend.
   - Ejecuta una sincronización manual y genera un respaldo desde el frontend para garantizar que el orquestador atiende las
     peticiones.

Una versión sólo se declara lista para entrega cuando el checklist se ha completado íntegramente en el entorno objetivo.

## Frontend — Softmobile Inventario

1. **Requisitos previos**
   - Node.js 18+

2. **Instalación y ejecución**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   El cliente se sirve en `http://127.0.0.1:5173`. La API se puede consumir en `http://127.0.0.1:8000`. Para producción ejecuta `npm run build` y copia `frontend/dist` según convenga.

3. **Características clave**
   - Tema oscuro con acentos cian siguiendo la línea gráfica corporativa y selector opcional de modo claro.
   - Panel modular con secciones de Inventario, Operaciones, Analítica, Seguridad y Sincronización.
   - Tablero principal con tarjetas dinámicas e indicadores globales alimentados por Recharts, iconografía `lucide-react` y animaciones `framer-motion`.
   - Panel exclusivo de administración (`UserManagement.tsx`) con checkboxes de roles, activación/desactivación y validación de motivos corporativos.
   - Sección de inventario con refresco automático en tiempo real (cada 30s), filtros por IMEI/modelo/estado comercial, chips de estado y alertas de stock bajo con severidad visual.
   - Editor de fichas de dispositivos con validación de motivos corporativos, soporte para catálogo pro (marca, modelo, capacidad, costos, márgenes, garantías) y recalculo de costos promedio capturando `unit_cost` en entradas de inventario.
   - Área de sincronización con acciones de respaldo, descarga de PDF, historial por tienda y estadísticas avanzadas de la cola híbrida.
   - Notificaciones tipo toast, animaciones suaves y diseño responsive para seguridad y sincronización.

## Reportes y respaldos

- **Descarga PDF**: `GET /reports/inventory/pdf` genera un reporte en tema oscuro con el inventario consolidado (también accesible desde el frontend).
- **Respaldos manuales**: `POST /backups/run` crea un PDF y un ZIP con la instantánea del inventario; devuelve la ruta y tamaño generado.
- **Respaldos automáticos**: el orquestador (`services/scheduler.py`) ejecuta respaldos cada `SOFTMOBILE_BACKUP_INTERVAL_SECONDS` y registra el historial en la tabla `backup_jobs`.

## Analítica empresarial

- **Métricas globales**: `GET /reports/metrics` devuelve el número de sucursales, dispositivos, unidades totales y el valor financiero del inventario.
- **Ranking por valor**: el mismo endpoint incluye las cinco sucursales con mayor valor inventariado para priorizar decisiones comerciales.
- **Alertas de stock bajo**: ajusta el parámetro `low_stock_threshold` o la variable `SOFTMOBILE_LOW_STOCK_THRESHOLD` para recibir hasta diez dispositivos críticos; cada disparo genera una entrada `inventory_low_stock_alert` en la bitácora con el usuario responsable y el umbral aplicado.
- **Comparativos multi-sucursal**: `GET /reports/analytics/comparative` y el tablero `AnalyticsBoard.tsx` permiten contrastar inventario, rotación y ventas recientes por sucursal, filtrando por tiendas específicas.
- **Margen y proyección de ventas**: `GET /reports/analytics/profit_margin` y `/reports/analytics/sales_forecast` calculan utilidad, ticket promedio y confianza estadística para horizontes de 30 días.
- **Exportaciones ejecutivas**: `GET /reports/analytics/export.csv` y `GET /reports/analytics/pdf` generan entregables consolidados en tema oscuro listos para comités corporativos.
- **Motivo corporativo obligatorio**: Las descargas CSV/PDF de analítica solicitan un motivo en el frontend y envían la cabecera `X-Reason` (≥ 5 caracteres) para cumplir con las políticas de seguridad.
- **Alertas de auditoría consolidadas**: el tablero principal consume `GET /reports/metrics` para mostrar totales críticos/preventivos, distinguir pendientes vs. atendidas y resaltar los incidentes más recientes en `GlobalMetrics.tsx`.

## Sincronización híbrida avanzada

- **Prioridad por entidad**: los registros de `sync_outbox` se clasifican con prioridades `HIGH`, `NORMAL` o `LOW` mediante `_OUTBOX_PRIORITY_MAP`; ventas y transferencias siempre quedan al frente para minimizar latencia inter-sucursal.
- **Cobertura integral de entidades**: ventas POS, clientes, reparaciones y catálogos registran eventos híbridos junto con inventario y transferencias, garantizando que los cambios críticos lleguen a la nube corporativa.
- **Estrategias de resolución de conflicto**: se aplica *last-write-wins* reforzado con marca de tiempo (`updated_at`) y auditoría; cuando existen actualizaciones simultáneas se fusionan campos sensibles usando la fecha más reciente y se registran detalles en `AuditLog`.
- **Métricas en tiempo real**: `GET /sync/outbox/stats` resume totales, pendientes y errores por tipo de entidad/prioridad; el panel "Sincronización avanzada" muestra estos datos con badges de color y permite monitorear la antigüedad del último pendiente.
- **Historial por tienda**: `GET /sync/history` entrega las últimas ejecuciones por sucursal (modo, estado y errores), visibles en el panel con badges verdes/ámbar y filtros administrados por `DashboardContext`.
- **Reintentos supervisados**: `POST /sync/outbox/retry` exige motivo corporativo (`X-Reason`) y reinicia contadores de intentos, dejando traza en `sync_outbox_reset` dentro de la bitácora.
- **Reintentos automáticos**: el servicio `requeue_failed_outbox_entries` reprograma entradas fallidas después de `SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS`, registrando la razón "Reintento automático programado" y respetando `SOFTMOBILE_SYNC_MAX_ATTEMPTS`.

## Módulo de actualizaciones

- **Estado del sistema**: `GET /updates/status` devuelve la versión en ejecución, la última disponible en el feed y si hay actualización pendiente.
- **Historial corporativo**: `GET /updates/history` lista las versiones publicadas según `docs/releases.json` (puedes sobrescribir la ruta con `SOFTMOBILE_UPDATE_FEED_PATH`).
- **Flujo recomendado**:
  1. Mantén `docs/releases.json` sincronizado con el área de liberaciones.
  2. Antes de liberar una versión ajusta `Settings.version`, ejecuta `alembic revision --autogenerate` si hay cambios de esquema y publica el nuevo instalador en la URL correspondiente.
  3. El frontend muestra avisos cuando detecta una versión más reciente.

## Instaladores corporativos

- **Backend**: usa `installers/softmobile_backend.spec` con PyInstaller para empaquetar la API como ejecutable.
- **Instalador final**: ejecuta `installers/SoftmobileInstaller.iss` con Inno Setup para distribuir backend + frontend + configuración en un instalador `.exe`. Consulta `installers/README.md` para pasos detallados.

## Pruebas automatizadas

```bash
pytest
```

Las pruebas levantan una base SQLite en memoria, deshabilitan las tareas periódicas y cubren autenticación, inventario, sincronización, reportes y módulo de actualizaciones.

- El caso `backend/tests/test_sync_offline_mode.py` comprueba la cola híbrida en modo offline con tres sucursales, reintentos automáticos y el nuevo endpoint `/sync/history`.

### Entorno Conda para automatización CI

Los *pipelines* corporativos utilizan `environment.yml` en la raíz para preparar un entorno reproducible. Si ejecutas las mismas verificaciones de manera local, puedes replicarlo con:

```bash
conda env update --file environment.yml --name base
```

El archivo referencia `requirements.txt`, por lo que cualquier dependencia nueva debe declararse primero allí para mantener la paridad entre desarrolladores y CI.

## Proceso de revisión continua

- Revisa `docs/evaluacion_requerimientos.md` en cada iteración.
- Mantén actualizado `docs/releases.json` con la versión vigente y su historial.
- Documenta las acciones correctivas aplicadas para asegurar que la versión v2.2.0 se mantenga estable.
