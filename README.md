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
- **Punto de venta directo (POS)** con carrito multiartículo, control automático de stock, borradores corporativos, recibos PDF en línea y configuración de impuestos/impresora.

## Centro de Control — Mandato de interfaz v2.2.0

El Centro de Control de Softmobile Inventario debe entregarse completo siguiendo el estilo oscuro corporativo (fondos #0D1117 y #161B22, acentos cian #00BFFF), tipografías Inter/Poppins, bordes redondeados de 10px y transiciones `all 0.3s ease`. El siguiente resumen guía las colaboraciones:

| Área | Componentes y archivos clave | Entregables requeridos |
| --- | --- | --- |
| **Visual global** | `frontend/src/styles.css`, `frontend/src/App.tsx`, `frontend/src/components/Toast.tsx`, `frontend/src/components/ModalConfirm.tsx`, `frontend/src/components/FilterSidebar.tsx` | Cuadrícula fluida con CSS Grid para tarjetas, efecto hover con sombra dinámica, animación `.fade-in` global, loader centralizado durante llamadas API, toasts estilo Slack en esquinas inferiores, modal de confirmación previa a acciones sensibles y barra lateral de filtros por tienda/estado. Iconografía con HeroIcons o Lucide. |
| **Analítica y reportes** | `frontend/src/components/AnalyticsBoard.tsx`, `frontend/src/components/ExportPDFButton.tsx`, `frontend/src/components/AnalyticsMiniCards.tsx` (mini tarjetas opcionales) | Indicadores animados (stock, valor, rotación), mini-gráficos con Recharts (barras y circulares), botones "Exportar PDF" y "Ver tendencias" conectados a `/reports/analytics/rotation`, `/reports/analytics/aging` y `/reports/analytics/stockout_forecast`. PDF en tema oscuro con ReportLab desde el backend. |
| **Inventario** | `frontend/src/components/AdvancedSearch.tsx`, `frontend/src/components/DeviceDetailModal.tsx` | Búsqueda por IMEI/nombre/modelo, detalle editable en modal con validaciones de stock y registro en auditoría. |
| **Operaciones** | `frontend/src/components/Purchases.tsx`, `frontend/src/components/Sales.tsx`, `frontend/src/components/Returns.tsx`, `frontend/src/components/TransferOrders.tsx`, `frontend/src/components/POS/*` | Formularios con react-hook-form o yup, badges de estado (SOLICITADA, EN_TRANSITO, RECIBIDA, CANCELADA), motivo obligatorio `X-Reason`, auditoría visible, control de stock en tiempo real, borradores POS, confirmaciones visuales y generación de recibo PDF. |
| **Seguridad** | `frontend/src/components/TwoFactorSetup.tsx`, `frontend/src/components/AuditLog.tsx` | Flujo de 2FA TOTP opcional (activar sólo cuando `SOFTMOBILE_ENABLE_2FA=1`), listado de eventos de auditoría, captura del motivo `X-Reason` antes de ejecutar acciones críticas. |
| **Sincronización híbrida** | `frontend/src/components/SyncQueuePanel.tsx` | Monitor de `sync_outbox` con estado actual, última sincronización, contador de reintentos (ej. "3 operaciones en espera, reintento en 30s") y botón "Forzar sincronización". |
| **Notificaciones y reportes** | `frontend/src/components/Toast.tsx`, `frontend/src/components/POS/POSReceipt.tsx`, `frontend/src/components/ExportPDFButton.tsx` | Sistema de notificaciones global, recibos PDF (logo, tienda, cliente, totales, botones "Imprimir" / "Enviar por correo"), exportación PDF oscura en reportes. |

### Componentes React obligatorios

Todos los siguientes archivos deben existir en `frontend/src/components/` (o la subcarpeta indicada) respetando el estilo anterior:

```
AdvancedSearch.tsx
AnalyticsBoard.tsx
AnalyticsMiniCards.tsx
AuditLog.tsx
DeviceDetailModal.tsx
FilterSidebar.tsx
ModalConfirm.tsx
Purchases.tsx
Returns.tsx
Sales.tsx
SyncQueuePanel.tsx
Toast.tsx
TransferOrders.tsx
TwoFactorSetup.tsx
POS/POSDashboard.tsx
POS/POSCart.tsx
POS/POSPayment.tsx
POS/POSReceipt.tsx
POS/POSSettings.tsx
```

### Integración de backend

- Middleware `X-Reason` obligatorio para ventas, transferencias, auditoría y operaciones sensibles. El frontend debe solicitar y enviar el motivo antes de confirmar.
  - Para automatizaciones (pytest, pipelines CI) el backend inyecta el valor `"Motivo automatizado"` cuando la cabecera no está presente, pero las interfaces humanas **deben** capturar el motivo explícito ≥ 5 caracteres.
- Endpoints habilitados: `/pos/sale`, `/pos/receipt/{id}`, `/pos/config`, `/transfers/*`, `/purchases/*`, `/sales/*`, `/returns/*`, `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast`, `/audit/*`, `/security/*`, `/sync/outbox`.
- Generación de PDFs corporativos con ReportLab y tema oscuro para recibos, analítica y respaldos.

### Prompt corporativo para automatizaciones

Utiliza este mensaje cuando se requiera asistencia de IA en desarrollo:

> "Actúa como desarrollador senior de Softmobile 2025 v2.2.0. No cambies la versión. Implementa los componentes faltantes del frontend según esta guía. Crea los archivos React indicados, con compatibilidad total y estética oscura. Sigue las normas de AGENTS.md y README.md. Mantén compatibilidad con backend FastAPI. Lote activo: interfaz completa del Centro de Control."

### Checklist previo a entrega

1. Tarjetas e indicadores con animaciones suaves y mini-gráficos activos.
2. Formularios de compras, ventas, transferencias y devoluciones con validaciones, auditoría y motivo `X-Reason`.
3. Paneles de analítica avanzada con exportación PDF y botones de tendencias.
4. Flujo de 2FA opcional y auditoría disponible.
5. Monitor de sincronización híbrida con contador de reintentos y botón de forzado.
6. Toasts, loader global, modales de confirmación y filtros avanzados visibles.
7. `pytest` en la raíz sin errores nuevos, `npm run build` en `frontend/` sin *warnings* y `GET /health` respondiendo `{"status": "ok"}`.

### Integración continua corporativa

El flujo de GitHub Actions definido en `.github/workflows/python-package-conda.yml` intenta actualizar el entorno base de Conda con `environment.yml`. Si el archivo estuviera ausente en un *fork* o ejecución aislada, el pipeline realiza una instalación de contingencia con `pip install -r requirements.txt` para impedir fallos por falta de dependencias. Mantén siempre `environment.yml` sincronizado con `requirements.txt` para que la rama principal utilice el entorno corporativo oficial.

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
  4. **Analítica avanzada**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast` con PDFs oscuros.
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
- ⏳ **Lote D — Analítica avanzada**: pendientes endpoints `/reports/analytics/rotation|aging|stockout_forecast` y generación de PDFs oscuros.
- ⏳ **Lote E — Seguridad y auditoría fina**: pendiente middleware global `X-Reason`, 2FA TOTP, auditoría de sesiones activas y revocación, así como componente `TwoFactorSetup.tsx`.
- ⏳ **Lote F — Preparación modo híbrido**: pendiente cola `sync_outbox` con reintentos y estrategia *last-write-wins*.

**Próximos hitos**

1. Activar las medidas de seguridad del Lote E (middleware global `X-Reason`, 2FA TOTP, auditoría de sesiones y componentes `TwoFactorSetup.tsx`/`AuditLog.tsx`) con pruebas asociadas.
2. Implementar el Lote D asegurando endpoints `/reports/analytics/*`, visualizaciones oscuras y exportación PDF con validaciones automatizadas.
3. Finalizar el Lote F con la cola `sync_outbox`, reintentos locales y estrategia *last-write-wins* probada end-to-end.

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
   - Tema oscuro con acentos cian siguiendo la línea gráfica corporativa.
   - Panel modular con secciones de Inventario, Operaciones, Analítica, Seguridad y Sincronización.
   - Sección de inventario con tarjetas de salud, tabla por sucursal, búsqueda avanzada y alertas de stock bajo.
   - Área de sincronización con acciones de respaldo, descarga de PDF e inspección de la cola híbrida.

## Reportes y respaldos

- **Descarga PDF**: `GET /reports/inventory/pdf` genera un reporte en tema oscuro con el inventario consolidado (también accesible desde el frontend).
- **Respaldos manuales**: `POST /backups/run` crea un PDF y un ZIP con la instantánea del inventario; devuelve la ruta y tamaño generado.
- **Respaldos automáticos**: el orquestador (`services/scheduler.py`) ejecuta respaldos cada `SOFTMOBILE_BACKUP_INTERVAL_SECONDS` y registra el historial en la tabla `backup_jobs`.

## Analítica empresarial

- **Métricas globales**: `GET /reports/metrics` devuelve el número de sucursales, dispositivos, unidades totales y el valor financiero del inventario.
- **Ranking por valor**: el mismo endpoint incluye las cinco sucursales con mayor valor inventariado para priorizar decisiones comerciales.
- **Alertas de stock bajo**: ajusta el parámetro `low_stock_threshold` para recibir hasta diez dispositivos críticos, con precios unitarios y valor actual.

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
