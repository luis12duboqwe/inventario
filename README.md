# Softmobile 2025 v2.2.0

Plataforma empresarial para la gestión centralizada de inventarios, sincronización entre sucursales y control operativo integral de cadenas de tiendas con una experiencia visual moderna en tema oscuro.

## Arquitectura general

Softmobile 2025 se compone de dos módulos cooperantes:

1. **Softmobile Inventario (frontend)**: cliente React + Vite pensado para ejecutarse en cada tienda. Permite registrar movimientos, disparar sincronizaciones, generar respaldos manuales y descargar reportes PDF con un diseño oscuro y acentos cian.
2. **Softmobile Central (backend)**: API FastAPI que consolida catálogos, controla la seguridad, genera reportes, coordina sincronizaciones automáticas/manuales y ejecuta respaldos programados.

La versión v2.2.0 trabaja en modo local (sin nube) pero está preparada para empaquetarse en instaladores Windows y evolucionar a despliegues híbridos.

## Capacidades implementadas

- **API empresarial FastAPI** con modelos SQLAlchemy para tiendas, dispositivos, movimientos, usuarios, roles, sesiones de sincronización, bitácoras y respaldos.
- **Seguridad por roles** con autenticación JWT, alta inicial segura (`/auth/bootstrap`), administración de usuarios y auditoría completa. Los roles corporativos vigentes son `ADMIN`, `GERENTE` y `OPERADOR`.
- **Gestión de inventario** con movimientos de entrada/salida/ajuste, actualización de dispositivos, reportes consolidados por tienda e impresión de etiquetas individuales con QR (generadas en frontend mediante la librería `qrcode`) para cada dispositivo.
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

- **Inventario compacto** (`frontend/src/modules/inventory/pages/InventoryPage.tsx`): utiliza el componente `Tabs` para dividir la vista en "Vista general", "Movimientos", "Alertas" y "Búsqueda avanzada". Cada tab agrupa tarjetas, tablas y formularios específicos sin requerir scroll excesivo. El formulario de movimientos ahora captura de manera opcional el **costo unitario** para entradas y fuerza motivos corporativos ≥5 caracteres, recalculando el promedio ponderado en backend. La tabla incorpora paginación configurable con vista completa de carga progresiva, permite imprimir etiquetas QR y abrir un **modal de edición** (`DeviceEditDialog.tsx`) que valida campos del catálogo pro, respeta unicidad de IMEI/serie, solicita motivo antes de guardar y habilita ajustes directos de existencias.
- **Inventario compacto** (`frontend/src/modules/inventory/pages/InventoryPage.tsx`): utiliza el componente `Tabs` para dividir la vista en "Vista general", "Movimientos", "Alertas" y "Búsqueda avanzada". Cada tab agrupa tarjetas, tablas y formularios específicos sin requerir scroll excesivo. El formulario de movimientos ahora captura de manera opcional el **costo unitario** para entradas y fuerza motivos corporativos ≥5 caracteres, recalculando el promedio ponderado en backend. La tabla permite imprimir etiquetas QR y abrir un **modal de edición** (`DeviceEditDialog.tsx`) que valida campos del catálogo pro, respeta unicidad de IMEI/serie y solicita motivo antes de guardar.
- **Operaciones escalables** (`frontend/src/modules/operations/pages/OperationsPage.tsx`): integra el nuevo `Accordion` corporativo para presentar los bloques "Ventas / Compras", "Movimientos internos", "Transferencias entre tiendas" y "Historial de operaciones". El primer panel incorpora POS, compras, ventas y devoluciones; los demás paneles se enfocan en flujos especializados con formularios y tablas reutilizables.
- **Analítica avanzada en grilla 3x2** (`frontend/src/components/ui/AnalyticsGrid/AnalyticsGrid.tsx`): presenta tarjetas de rotación, envejecimiento, pronóstico de agotamiento, comparativo multi-sucursal, margen y proyección de unidades. La grilla responde a breakpoints y mantiene la proporción 3x2 en escritorio.
- **Scroll interno para Seguridad, Usuarios y Sincronización**: las vistas aplican la clase `.section-scroll` (altura máxima 600 px y `overflow-y: auto`) para que la barra lateral permanezca visible mientras se consultan auditorías, políticas o colas híbridas.
- **Componentes reutilizables documentados**: `Tabs`, `Accordion` y `AnalyticsGrid` viven en `frontend/src/components/ui/` con estilos CSS modulares y ejemplos en historias internas. Consérvalos al implementar nuevas secciones y evita modificar su API sin actualizar esta documentación.

Para obtener capturas actualizadas del flujo completo ejecuta `uvicorn backend.app.main:app` (asegurando los feature flags del mandato operativo) y `npm --prefix frontend run dev`. Puedes precargar datos demo con los endpoints `/auth/bootstrap`, `/stores`, `/purchases`, `/sales` y `/transfers` usando cabeceras `Authorization` y `X-Reason` ≥ 5 caracteres.

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
- **Alertas de stock bajo**: ajusta el parámetro `low_stock_threshold` para recibir hasta diez dispositivos críticos, con precios unitarios y valor actual.
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
