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
- **Gestión de inventario** con movimientos de entrada/salida/ajuste, actualización de dispositivos y reportes consolidados por tienda.
- **Valuación y métricas financieras** con precios unitarios, ranking de sucursales y alertas de stock bajo expuestos vía `/reports/metrics` y el panel React.
- **Sincronización programada y bajo demanda** mediante un orquestador asincrónico que ejecuta tareas periódicas configurables.
- **Respaldos empresariales** con generación automática/manual de PDF y archivos comprimidos JSON usando ReportLab; historial consultable vía API.
- **Módulo de actualizaciones** que consulta el feed corporativo (`/updates/*`) para verificar versiones publicadas y descargar instaladores.
- **Frontend oscuro moderno** para el módulo de tienda, construido con React + TypeScript, compatible con escritorio y tablet.
- **Instaladores corporativos**: plantilla PyInstaller para el backend y script Inno Setup que empaqueta ambos módulos y crea accesos directos.
- **Pruebas automatizadas** (`pytest`) que validan flujo completo de autenticación, inventario, sincronización y respaldos.
- **Transferencias entre tiendas** protegidas por permisos por sucursal y feature flag, con flujo SOLICITADA → EN_TRANSITO → RECIBIDA/CANCELADA, auditoría en cada transición y componente React dedicado.
- **Compras y ventas operativas** con órdenes de compra parcialmente recibidas, cálculo de costo promedio, ventas con descuento/método de pago y devoluciones auditadas desde la UI (`Purchases.tsx`, `Sales.tsx`, `Returns.tsx`).
- **Órdenes de reparación** con modelo `repair_orders`, flujo de estados PENDIENTE→EN_REPARACION→LISTO→ENTREGADO, control por sucursal, PDF de diagnóstico generado con ReportLab y endpoints REST `/repairs/*` protegidos por `X-Reason` y roles de gestión.
- **Punto de venta directo (POS)** con carrito multiartículo, control automático de stock, borradores corporativos, recibos PDF en línea y configuración de impuestos/impresora.
- **Analítica comparativa multi-sucursal** con endpoints `/reports/analytics/comparative`, `/reports/analytics/profit_margin` y `/reports/analytics/sales_forecast`, exportación CSV consolidada y tablero React con filtros por sucursal.
- **Sincronización híbrida priorizada** mediante `sync_outbox` con niveles HIGH/NORMAL/LOW, estadísticas por entidad y reintentos auditados desde el panel.
- **Experiencia UI responsiva** con toasts contextuales, animaciones suaves y selector de tema claro/oscuro que mantiene el modo oscuro como predeterminado.

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
      repairs.py
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
  plan_v2.2.0.md
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

### Interfaz React

- `POSDashboard.tsx`: orquesta la experiencia POS, permite buscar por IMEI/modelo/nombre, mostrar accesos rápidos y coordinar carrito/pago/recibo.
- `POSCart.tsx`: edita cantidades, descuentos por línea y alerta cuando el stock disponible es insuficiente.
- `POSPayment.tsx`: controla método de pago, descuento global, confirmación visual y motivo corporativo antes de enviar la venta o guardar borradores.
- `POSReceipt.tsx`: descarga o envía el PDF inmediatamente después de la venta.
- `POSSettings.tsx`: define impuestos, prefijo de factura, impresora y productos frecuentes.

### Consideraciones operativas

- Todos los POST/PUT del POS deben incluir un motivo (`X-Reason`) con al menos 5 caracteres.
- El flujo admite ventas rápidas (botones configurables), guardado de borradores y notificaciones visuales de éxito/errores.
- Al registrar una venta se generan movimientos de inventario, auditoría y un evento en la cola `sync_outbox` para sincronización híbrida.

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
- ✅ **Lote D — Analítica avanzada**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast`, `/reports/analytics/comparative`, `/reports/analytics/profit_margin`, `/reports/analytics/sales_forecast`, descarga PDF y exportación CSV oscuras implementadas con servicios ReportLab, pruebas `pytest` y tablero `AnalyticsBoard.tsx` con filtros por sucursal.
- ✅ **Lote E — Seguridad y auditoría fina**: middleware global `X-Reason`, dependencias `require_reason`, flujos 2FA TOTP condicionados por flag `SOFTMOBILE_ENABLE_2FA`, auditoría de sesiones activas con `AuditLog.tsx` (polling y toasts) y componente `TwoFactorSetup.tsx` que exige motivo corporativo en cada acción.
- ✅ **Lote F — Preparación modo híbrido**: cola `sync_outbox` con reintentos, prioridad HIGH/NORMAL/LOW y estrategia *last-write-wins* en `crud.enqueue_sync_outbox`/`reset_outbox_entries`, paneles `SyncPanel.tsx` y "Sincronización avanzada" con métricas y pruebas automáticas.

**Próximos hitos**

1. Mantener monitoreo continuo del modo híbrido, afinando reglas de *merge* temporal y preparando compatibilidad con nuevas entidades planeadas para v2.3.
2. Diseñar módulos adicionales de soporte remoto y control de clientes, incluyendo comparativos regionales en tableros georreferenciados.
3. Profundizar en mejores prácticas de despliegue (Inno Setup) y capacitaciones 2FA para escalamientos masivos.

## Registro operativo de lotes entregados

| Lote | Entregables clave | Evidencias |
| --- | --- | --- |
| Iteración — Reparaciones | Modelo `repair_orders`, esquemas Pydantic, router `/repairs/*`, generación PDF corporativa y pruebas `test_repairs.py` | `pytest` en verde incluyendo el nuevo módulo y verificación manual de PDF |
| D — Analítica avanzada | Servicios `analytics.py`, endpoints `/reports/analytics/*` (incluye comparativos, margen y forecast), PDF/CSV oscuros y componente `AnalyticsBoard.tsx` renovado | Pruebas `pytest` (rotación, envejecimiento, comparativos) y verificación de exportes desde el panel |
| E — Seguridad y auditoría | Middleware `X-Reason`, dependencias `require_reason`, flujos 2FA (`/security/2fa/*`), auditoría de sesiones y componentes `TwoFactorSetup.tsx`/`AuditLog.tsx` con toasts | Ejecución interactiva del módulo Seguridad y pruebas automatizadas de sesiones |
| F — Modo híbrido | Modelo `SyncOutbox`, prioridades HIGH/NORMAL/LOW, reintentos `reset_outbox_entries`, paneles `SyncPanel.tsx` y "Sincronización avanzada" con métricas | Casos de prueba de compras/ventas que generan eventos y validación manual de métricas |
| Operación manual — 2025-10-14 | Alta de sucursales Matriz Centro y Sucursal Norte, registro de dispositivos de catálogo pro y venta de demostración para validar Inventario/Operaciones | Backend y frontend en ejecución con cabeceras `X-Reason`, carga de datos vía script `httpx`, `pytest` en verde y capturas de todos los módulos |

### Pasos de control iterativo (registrar tras cada entrega)

1. **Revisión documental**: lee `AGENTS.md`, este README y `docs/evaluacion_requerimientos.md` para confirmar lineamientos vigentes y actualiza la bitácora anterior con hallazgos.
2. **Pruebas automatizadas**: ejecuta `pytest` en la raíz y `npm --prefix frontend run build`; registra en la bitácora la fecha y resultado de ambas ejecuciones.
3. **Validación funcional**: desde el frontend confirma funcionamiento de Inventario, Operaciones, Analítica, Seguridad (incluyendo 2FA con motivo) y Sincronización, dejando constancia de módulos revisados.
4. **Verificación híbrida**: consulta `/sync/outbox` desde la UI y reintenta eventos con un motivo para asegurar que la cola quede sin pendientes críticos.
5. **Registro final**: documenta en la sección "Registro operativo de lotes entregados" cualquier ajuste adicional realizado, incluyendo nuevos endpoints o componentes.

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
   - Sección de inventario con tarjetas de salud, tabla por sucursal, búsqueda avanzada y alertas de stock bajo.
   - Área de sincronización con acciones de respaldo, descarga de PDF, inspección de la cola híbrida y panel de prioridades.
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

## Sincronización híbrida avanzada

- **Prioridad por entidad**: los registros de `sync_outbox` se clasifican con prioridades `HIGH`, `NORMAL` o `LOW` mediante `_OUTBOX_PRIORITY_MAP`; ventas y transferencias siempre quedan al frente para minimizar latencia inter-sucursal.
- **Estrategias de resolución de conflicto**: se aplica *last-write-wins* reforzado con marca de tiempo (`updated_at`) y auditoría; cuando existen actualizaciones simultáneas se fusionan campos sensibles usando la fecha más reciente y se registran detalles en `AuditLog`.
- **Métricas en tiempo real**: `GET /sync/outbox/stats` resume totales, pendientes y errores por tipo de entidad/prioridad; el panel "Sincronización avanzada" muestra estos datos con badges de color y permite monitorear la antigüedad del último pendiente.
- **Reintentos supervisados**: `POST /sync/outbox/retry` exige motivo corporativo (`X-Reason`) y reinicia contadores de intentos, dejando traza en `sync_outbox_reset` dentro de la bitácora.

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
