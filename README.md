# Softmobile 2025 v2.2.0

Plataforma empresarial para la gestión centralizada de inventarios, sincronización entre sucursales y control operativo integral de cadenas de tiendas con una experiencia visual moderna en tema oscuro.

## Arquitectura general

Softmobile 2025 se compone de dos módulos cooperantes:

1. **Softmobile Inventario (frontend)**: cliente React + Vite pensado para ejecutarse en cada tienda. Permite registrar movimientos, disparar sincronizaciones, generar respaldos manuales y descargar reportes PDF con un diseño oscuro y acentos cian.
2. **Softmobile Central (backend)**: API FastAPI que consolida catálogos, controla la seguridad, genera reportes, coordina sincronizaciones automáticas/manuales y ejecuta respaldos programados.

La versión v2.2.0 trabaja en modo local (sin nube) pero está preparada para empaquetarse en instaladores Windows y evolucionar a despliegues híbridos.

### Prefijo de API versionado

El backend publica todas las rutas heredadas sin prefijo para mantener compatibilidad y, adicionalmente, las expone bajo `/api/v2.2.0` como prefijo principal (configurable mediante la variable `SOFTMOBILE_API_PREFIX`). El alias legado `/api/v1` permanece disponible por defecto a través de la configuración `SOFTMOBILE_API_ALIASES`, de modo que las integraciones anteriores continúan funcionando sin cambios.

### Capas del frontend reorganizado

La fase de endurecimiento técnico consolidó la estructura del cliente React en carpetas claramente delimitadas para aislar responsabilidades y facilitar pruebas automatizadas:

- `frontend/src/app/`: arranque de la aplicación, routing y proveedores globales (React Query, theming corporativo).
- `frontend/src/shared/`: componentes reutilizables y utilidades UI compartidas entre módulos, sin alterar el estilo existente.
- `frontend/src/services/api/`: SDK interno basado en Axios con interceptores de autenticación, flujos `/auth/refresh` y módulos por dominio (`auth`, `stores`, `inventory`, `pos`).
- `frontend/src/features/`: espacio reservado para casos de uso compuestos, documentado con _placeholders_ `.gitkeep` para mantener la estructura.
- `frontend/src/pages/`: contenedores por ruta que coordinan widgets y módulos especializados.
- `frontend/src/widgets/`: bloques ligeros reutilizables en dashboards, también preservados mediante `.gitkeep` hasta que se agreguen nuevas implementaciones.
- `frontend/src/modules/`: funcionalidad heredada (Inventario, Operaciones, Analítica, Seguridad, etc.) que se beneficia de la nueva capa de servicios sin modificar el layout visual.

## Hoja de ruta inmediata (Softmobile 2025 v2.2.0)

Para continuar con la evolución ordenada del proyecto, utiliza las siguientes etapas como guía de implementación y verificación. Cada fase consolida capacidades ya previstas en el backend y facilita su validación en el frontend corporativo:

- **Etapa 3 — Autenticación real (SQLite + JWT)**: verifica el modelo de usuarios en `backend/app/models/__init__.py`, los esquemas y CRUD asociados en `backend/app/crud.py` y las utilidades de seguridad (`hash_password`, `create_access_token`, validación TOTP) en `backend/app/security.py`. El router `backend/app/routers/auth.py` expone `POST /auth/bootstrap`, `POST /auth/token`, `POST /auth/session` y `POST /auth/verify`, apoyándose en el middleware de sesiones y en los tokens JWT configurados desde `backend/app/config.py`. La base local se provisiona ejecutando `backend.database.run_migrations()`, que carga `backend/alembic.ini`, actualiza la URL con `SQLALCHEMY_DATABASE_URL` y delega en `alembic upgrade head`; las pruebas unitarias reutilizan la misma utilidad para inicializar instancias efímeras.
- **Etapa 4 — CRUD de inventario**: el router `backend/app/routers/inventory.py` gestiona los dispositivos, existencias y sincronizaciones manuales, mientras que `backend/app/models/__init__.py` define los modelos `Device`, `InventoryMovement` y `DeviceIdentifier` con los campos ampliados del catálogo pro (IMEI, serie, proveedor, valuación). Las pruebas `backend/tests/test_catalog_pro.py`, `backend/tests/test_inventory_valuation.py` y `backend/tests/test_inventory_smart_import.py` aseguran que el flujo de altas, consultas, ediciones, eliminaciones y sincronización cumpla con las reglas corporativas y con el encabezado obligatorio `X-Reason` en operaciones sensibles.
- **Etapa 5 — Sincronización entre tiendas**: la cola híbrida `SyncOutbox` y los endpoints `backend/app/routers/sync.py`/`backend/app/routers/transfers.py` permiten sincronizar inventario y transferencias entre sucursales utilizando reintentos automáticos y resolución _last-write-wins_. Los servicios `backend/app/services/sync.py` y `backend/app/services/sync_conflict_reports.py` controlan las versiones, prioridades y reportes de conflicto, mientras que las suites `backend/tests/test_sync_full.py`, `backend/tests/test_sync_outbox.py` y `backend/tests/test_sync_offline_mode.py` verifican consistencia y reintentos.
- **Etapa 6 — Integración con frontend (Vite + React)**: una vez compilado el frontend (`npm --prefix frontend run build`), la carpeta `frontend/dist` se sirve automáticamente desde `backend/app/main.py`. Los módulos React (`frontend/src/modules/inventory/pages/InventoryPage.tsx`, `frontend/src/modules/dashboard/layout/DashboardLayout.tsx`, entre otros) consumen los endpoints autenticados reutilizando el token JWT o la cookie de sesión. Ejecuta `npm --prefix frontend run test` y `npm --prefix frontend run build` para validar la interfaz antes de desplegar.

> Mantén la versión corporativa **v2.2.0**, respeta los _feature flags_ activos (`SOFTMOBILE_ENABLE_*`) y documenta cualquier ajuste significativo en esta sección para conservar la trazabilidad del roadmap.

## Actualización funcional — POS multipago y observabilidad (05/11/2025)

- 🔁 **Ventas multipago en el POS corporativo**: `backend/models/pos.py` incorpora las entidades `Sale`, `SaleItem` y `Payment` con estados `OPEN/HELD/COMPLETED/VOID` y totales calculados automáticamente. El router `backend/routes/pos.py` publica `POST /pos/sales`, `POST /pos/sales/{id}/items`, `POST /pos/sales/{id}/checkout`, `POST /pos/sales/{id}/hold`, `POST /pos/sales/{id}/resume`, `POST /pos/sales/{id}/void` y `GET /pos/receipt/{id}`, habilitando combinaciones de pago `CASH`, `CARD` y `TRANSFER` sin perder compatibilidad con `/pos/sale` ni con los recibos PDF históricos.
- 📦 **Respuestas API unificadas**: el nuevo módulo `backend/schemas/common.py` define `Page[T]`, `PageParams` y `ErrorResponse`. Los listados de inventario, sucursales, compras y reportes devuelven ahora `Page[...]` con metadatos `total`, `page`, `size`, `pages` y `has_next`, simplificando la paginación en backend, SDK y frontend.
- 🛰️ **Observabilidad con Loguru y jobs asincrónicos**: `backend/core/logging.py` configura Loguru en formato JSON agregando `user_id`, `path`, `latency` y `request_id`. El middleware global en `backend/main.py` asigna `X-Request-ID`, mide latencias y centraliza excepciones con el manejador `INTERNAL_ERROR`. Se suma `backend/routes/jobs.py` con `POST /jobs/export`, que encola exportaciones mediante `BackgroundTasks` o delega en Redis si está disponible.

### API Responses unificadas

- Las rutas de lectura (`/inventory/summary`, `/inventory/devices/incomplete`, `/inventory/devices/search`, `/stores`, `/stores/{id}/devices`, `/stores/{id}/memberships`, `/purchases/vendors`, `/purchases/records`, `/purchases`, `/reports/audit`, `/reports/inventory/supplier-batches`) entregan `Page[...]` con la siguiente estructura:
  ```json
  {
    "items": [...],
    "total": 42,
    "page": 1,
    "size": 20,
    "pages": 3,
    "has_next": true
  }
  ```
- Los errores inesperados responden con `{"code": "INTERNAL_ERROR", "message": "<detalle>"}` gracias al manejador global registrado en `backend/main.py`.
- Para construir respuestas homogéneas desde nuevas rutas reutiliza `Page.from_items(...)` y `ErrorResponse` desde `backend/schemas/common.py`.

### Jobs & Monitoring

- Loguru reemplaza `logging.basicConfig` como logger central. Cada solicitud queda registrada en JSON con `request_id`, `user_id`, `path` y `latency`, lo que facilita la ingestión en soluciones de observabilidad.
- En entornos donde `loguru` no esté disponible, `backend/core/logging.py` activa automáticamente un formateador JSON basado en `logging` para conservar la misma estructura de eventos sin bloquear el arranque.
- El middleware HTTP añade (o reutiliza) el encabezado `X-Request-ID` en todas las respuestas y vincula el contexto de logging por petición.
- Se incorpora el endpoint `POST /jobs/export` que retorna `202 Accepted` y registra el job con el backend `local` (BackgroundTasks) o `redis` si `REDIS_URL` está presente. El archivo `backend/schemas/jobs.py` documenta `ExportJobRequest` y `ExportJobResponse` para futuras extensiones de cola.

## Ajuste de mantenimiento — 06/11/2025

- 🧹 **Limpieza de artefactos generados**: se retira del repositorio el archivo `backend/database/softmobile.db`, que es recreado automáticamente en tiempo de ejecución. Esto evita adjuntar binarios en los PR y mantiene el flujo de empaquetado descrito en la sección «Preparación rápida del entorno base».
- 🔧 **Refuerzos de utilidades compartidas**: `backend/schemas/common.py` normaliza el cálculo de páginas con `ceil` y `backend/core/logging.py` declara explícitamente los contextos (`ContextVar`, `Token`) utilizados por Loguru para garantizar trazabilidad consistente incluso en entornos mínimos.
- 📄 **Compatibilidad de recibos POS**: `backend/routes/pos.py` prioriza los recibos PDF del núcleo, aplica un desfase en los identificadores del módulo ligero (`+1,000,000`) y sólo entrega respuestas JSON cuando la venta no existe en el POS tradicional, evitando colisiones y manteniendo el PDF histórico disponible.

## Limpieza Pydantic v2 — 07/11/2025

Se completó la eliminación de warnings de alias (de 32 → 17 → 0) sin modificar contratos públicos ni la versión corporativa v2.2.0.

### Enfoque técnico

- Sustitución de `validation_alias` / `serialization_alias` por `model_validator(mode="before")` para coalescer aliases de entrada (por ejemplo `device_id`→`producto_id`, `movement_type`→`tipo_movimiento`).
- Uso de `model_serializer` en respuestas complejas (`MovementResponse`, `WMSBinResponse`, POS, seguridad) para mapear atributos internos canónicos (inglés) a claves históricas en español sin romper pruebas ni clientes.
- Conservación de `model_config = ConfigDict(from_attributes=True)` para permitir carga desde modelos SQLAlchemy manteniendo los nombres internos.
- Validadores adicionales (`field_validator`) para normalizar comentarios, cantidades y motivos corporativos (`X-Reason` ≥5 caracteres) evitando excepciones tardías.

### Resultados

- Warnings Pydantic de alias reducidos a cero en la suite (`pytest` 194 tests passed, 0 warnings de alias).
- Restaurados y formalizados esquemas faltantes de seguridad: `TOTPActivateRequest`, `ActiveSessionResponse`, `SessionRevokeRequest` sin alias directos.
- Compatibilidad total: claves de salida en español preservadas; entradas siguen aceptando nombres anteriores mediante coalescencia previa.
- Sin cambios de versión ni edición de `docs/releases.json`/banners conforme al mandato estricto.

### Próximos pasos sugeridos

1. Vigilar nuevas incorporaciones de esquemas para mantener el patrón (validator + serializer) y evitar reintroducir alias directos.
2. Documentar en `AGENTS.md` cualquier nuevo módulo que adopte este enfoque para mantener transparencia en auditorías técnicas.
3. Evaluar migración futura a modelos segregados (input/output) sólo si surge necesidad de desacoplar validaciones avanzadas sin incrementar complejidad.

## Reorganización técnica del frontend — 23/10/2025

- Se normaliza la estructura de `frontend/src/` creando las carpetas `app/`, `shared/`, `services/api/`, `features/`, `pages/` y `widgets/`, manteniendo los módulos existentes dentro de `modules/` y sin alterar el aspecto visual.
- Los componentes reutilizables se concentran en `frontend/src/shared/components/` y se actualizaron las importaciones heredadas para preservar compatibilidad con los módulos existentes.
- `services/api/http.ts` introduce un cliente Axios con interceptores que adjuntan el token corporativo, reintentan `401` mediante `/auth/refresh` y disparan el evento `softmobile:unauthorized` cuando la sesión expira.
- `services/api/auth.ts` centraliza bootstrap, login y cierre de sesión; `services/api/{stores,inventory,pos}.ts` agrupan las llamadas de cada dominio para facilitar mantenibilidad.
- `main.tsx` incorpora `QueryClientProvider` y `App.tsx` adopta `useQuery`/`useMutation` para el flujo de autenticación y bootstrap sin modificar los estilos ni las rutas existentes.
- Se documenta la nueva estructura en `frontend/README.md` para guiar futuras iteraciones manteniendo la versión Softmobile 2025 v2.2.0.

## Preparación rápida del entorno base — 20/10/2025

- ✅ **Backend**: se añadió el archivo `backend/main.py` con FastAPI, CORS abierto para redes locales y montaje automático de `frontend/dist` cuando está disponible. La ruta `/api` devuelve el mensaje corporativo «API online ✅ - Softmobile 2025 v2.2.0». El arranque valida la carpeta `backend/database/softmobile.db` y registra advertencias si faltan directorios de modelos o rutas.
- ✅ **Migraciones automáticas**: la utilidad `backend/database/run_migrations()` resuelve `backend/alembic.ini`, parametriza `SQLALCHEMY_DATABASE_URL` y ejecuta `alembic upgrade head`. `backend/main.py`, `backend/routes/auth.py` y `backend/routes/pos.py` la invocan durante el arranque para evitar dependencias manuales de `Base.metadata.create_all` y asegurar la columna `users.is_verified` en cualquier entorno local.
- ✅ **Variables de entorno**: se generó `.env` en `backend/` con `DATABASE_URL=sqlite:///backend/database/softmobile.db`, `API_PORT=8000` y `DEBUG=True` para alinearse con los empaquetados Windows.
- ✅ **Estructura base**: se normalizaron las carpetas `backend/models`, `backend/routes`, `backend/database` y `backend/logs`, cada una con su `__init__.py` para permitir importaciones explícitas en instaladores.
- ✅ **Logs de instalación**: `backend/logs/setup_report.log` y `backend/logs/verification_status.log` documentan la creación de la estructura y el resultado de las verificaciones del 20/10/2025.
- ✅ **Frontend**: el comando `npm run build` (ejecutado el 20/10/2025) genera `frontend/dist`, permitiendo que el backend sirva los activos compilados cuando está en modo de producción local.
- ✅ **Instaladores Windows**: se agregó `build/start_softmobile.bat` para iniciar backend + frontend y la plantilla `build/SoftmobileInstaller.iss` para empaquetar ambos módulos con Inno Setup.

> Todas las acciones mantienen la versión **Softmobile 2025 v2.2.0** sin cambios y respetan el flujo actual de despliegue híbrido.

## RBAC y permisos modulares — 07/11/2025

El backend aplica autorización en dos capas complementarias:

- Dependencias en router: rutas sensibles usan `require_roles(...)` (p. ej. `/reports/**`, `/security/**`, `/logs/**`, `/monitoring/**`, `/api/audit/ui/**`).
- Middleware global: para cualquier ruta, resuelve el módulo por prefijo (`MODULE_PERMISSION_PREFIXES`) y evalúa permisos por acción (GET→`view`, POST/PUT/PATCH→`edit`, DELETE→`delete`) contra la matriz persistida en `permisos`.

Resumen de matriz por rol (síntesis de `ROLE_MODULE_PERMISSION_MATRIX`):

- ADMIN: `view/edit/delete` en todos los módulos.
- GERENTE: `view/edit` en todos; `delete` prohibido en: `seguridad`, `respaldos`, `usuarios`, `actualizaciones`.
- OPERADOR: `view` en todos; `edit` prohibido en: `seguridad`, `respaldos`, `usuarios`, `actualizaciones`, `auditoria`; `delete` prohibido además en: `reportes`, `sincronizacion`.
- INVITADO: solo `view` en: `inventario`, `reportes`, `clientes`, `proveedores`, `ventas`; sin `edit/delete`.

Prefijos protegidos adicionales (siempre exigen rol):

- `/users` → ADMIN
- `/sync` → ADMIN o GERENTE

Motivo corporativo (X-Reason):

- El middleware exige `X-Reason` (≥5 caracteres) en métodos sensibles (POST/PUT/PATCH/DELETE) y en descargas/exports de `reports`, `purchases`, `sales`, `backups`, `users`, además de lecturas sensibles del POS.

Pruebas añadidas:

- `backend/tests/test_rbac_matrix.py`: valida que `INVITADO` no accede a reportes, `OPERADOR` no exporta auditoría UI, y `GERENTE` no realiza operaciones de borrado en seguridad.

Nota: La matriz se materializa en la tabla `permisos`. Las funciones `ensure_role`/`ensure_role_permissions` inicializan valores por defecto sin sobrescribir flags ya definidos, permitiendo personalización controlada.

## Autenticación JWT con SQLite y bcrypt — 03/03/2026

- ✅ **Dependencias nuevas**: el backend incorpora `passlib[bcrypt]` para el hash de contraseñas, `python-jose[cryptography]` para firmar y validar JWT y `python-multipart` para manejar formularios `application/x-www-form-urlencoded`. Todas se encuentran definidas en `backend/requirements.txt` y se instalan automáticamente al ejecutar `pip install -r backend/requirements.txt`.
- ✅ **Configuración declarativa**: añade `pydantic-settings` para que `backend/main.py` y `backend/app/config.py` carguen variables de entorno de forma tipada y consistente, evitando errores de arranque por configuraciones faltantes. La dependencia ya está listada en `requirements.txt` para instalaciones locales y empaquetados.
- ✅ **Variables de entorno**: añade `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` en `backend/.env`. Genera una clave segura con `python -c "import secrets; print(secrets.token_urlsafe(32))"` y asígnala a `SECRET_KEY` en tu entorno de ejecución (Codespaces/CI). **No** la publiques en commits: utiliza los parámetros de entorno del contenedor o del sistema de integración continua para inyectarla en tiempo de ejecución.
- ✅ **Flujo de endpoints**:
  1. `POST /auth/register` — JSON `{"email": "admin@softmobile", "password": "123456"}`. Responde 200 con el usuario creado y el mensaje «Usuario registrado correctamente.».
  2. `POST /auth/login` — formulario `application/x-www-form-urlencoded` con `username=admin@softmobile&password=123456`. Devuelve `{"access_token": "<jwt>", "token_type": "bearer"}`.
  3. `GET /auth/me` — incluye `Authorization: Bearer <jwt>` para recuperar los datos del usuario autenticado.
- ✅ **Compatibilidad heredada**: se mantiene el soporte para `/auth/token` y `/auth/verify` para los clientes existentes, aprovechando el mismo backend de autenticación basado en JWT.

### Ejemplos rápidos con `curl`

```bash
# Registro
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@softmobile","password":"123456"}'

# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@softmobile&password=123456"

# Verificación del token
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <token_recibido>"
```

> Al ejecutar en Codespaces o en CI agrega `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` como variables de entorno del contenedor para evitar exponer secretos en el repositorio.

## Autenticación avanzada — 23/10/2025

- **Configuración centralizada**: `backend/core/settings.py` define la clase `Settings` con lectura desde `.env`, incorporando `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` y los parámetros SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`) para habilitar notificaciones por correo cuando se configure un servidor corporativo.
- **Tokens tipados**: `backend/core/security.py` emite JWT con el campo `token_type`, permitiendo diferenciar accesos, refrescos, restablecimientos y verificaciones. Los helpers `create_refresh_token`, `decode_token` y `verify_token_expiry` simplifican la validación de cada flujo.
- **Par de tokens y limitación de ritmo**: `/auth/login` y `/auth/token` devuelven ahora `TokenPairResponse` con `access_token` y `refresh_token`. La ruta heredada `/auth/token` queda protegida por `fastapi-limiter` (5 solicitudes por minuto e IP) usando `fakeredis` como almacenamiento embebido.
- En entornos donde `fastapi-limiter` o `fakeredis` no estén disponibles, el backend continúa activo y registra una advertencia, deshabilitando la limitación de ritmo de forma automática.
- **Renovación de sesiones**: el endpoint `POST /auth/refresh` acepta `refresh_token` vigentes, valida que el usuario siga activo y entrega un nuevo par de tokens sin requerir credenciales.
- **Recuperación de contraseña**: `POST /auth/forgot` genera un token temporal `password_reset`, lo envía por correo si existe configuración SMTP y, en entornos de prueba, lo expone en la respuesta. `POST /auth/reset` consume dicho token y actualiza la contraseña con hash bcrypt.
- **Verificación de correo**: `POST /auth/verify` marca `is_verified=True` para el usuario asociado al token `email_verification`. Cada registro (`/auth/register` y `/auth/bootstrap`) devuelve el token de verificación inicial para integraciones automatizadas.
- **Esquemas ampliados**: `backend/schemas/auth.py` incorpora `TokenPairResponse`, `RefreshTokenRequest`, `ForgotPasswordRequest`, `ForgotPasswordResponse`, `ResetPasswordRequest` y `VerifyEmailRequest`, además del nuevo campo `is_verified` dentro de `UserRead` y `RegisterResponse`.
- **Cobertura automatizada**: `backend/tests/test_routes_bootstrap.py` valida el ciclo completo (login, refresh, forgot/reset y verificación) asegurando que los tokens cambien al refrescar, que la contraseña se actualice y que `is_verified` quede en `True` tras consumir `POST /auth/verify`.
- **Dependencias nuevas**: agrega `fastapi-limiter==0.1.6` y `fakeredis==2.32.0` en `requirements.txt` y `backend/requirements.txt`. Si se despliega en producción, reemplaza `fakeredis` por un clúster Redis y ajusta las variables SMTP para notificar a los usuarios.

## API de sucursales con membresías — 23/10/2025

- **Respuesta paginada**: la ruta `GET /stores` ahora entrega `Page[StoreRead]` con parámetros `page` y `size` (máximo 100 registros por página). Cada elemento expone `id`, `name`, `code`, `address`, `status`, `is_active`, `timezone`, `created_at` e `inventory_value`. El backend ligero convierte automáticamente los modelos del núcleo para mantener compatibilidad con Softmobile 2025 v2.2.0.
- **Altas controladas**: `POST /stores` acepta el esquema `StoreCreate` (`name`, `code`, `address`, `is_active`, `timezone`) y delega en `backend/app/routers/stores.py` para preservar validaciones de unicidad (`name`, `code`), generación de códigos `SUC-###` y registro en bitácora corporativa.
- **Edición segura**: `PUT /stores/{id}` consume `StoreUpdate` (campos opcionales) y utiliza `crud.update_store` para auditar cambios y evitar duplicidades de nombre/código. La respuesta incluye los datos unificados del núcleo y el wrapper ligero.
- **Detalle puntual**: `GET /stores/{id}` mantiene la compatibilidad total con el núcleo retornando `StoreRead` ya normalizado, de forma que el backend ligero y los clientes externos obtienen la misma representación.
- **Membresías por sucursal**: `GET /stores/{id}/memberships` entrega `Page[StoreMembershipRead]` con controles de paginación (`page`, `size<=200`). `PUT /stores/{id}/memberships/{user_id}` admite el cuerpo `StoreMembershipUpdate`, valida que los identificadores del cuerpo y la ruta coincidan y delega la persistencia en el núcleo, registrando permisos `can_create_transfer` y `can_receive_transfer`.
- **Compatibilidad extendida**: el wrapper de `backend/routes/stores.py` incluye el router principal (`backend/app/routers/stores`) para conservar rutas avanzadas (`/devices`, transferencias, reportes). Los nuevos esquemas (`backend/schemas/store.py`) encapsulan la conversión y normalización de datos hacia y desde el núcleo.

## Ejecución en GitHub Codespaces

La carpeta `.devcontainer/` incorpora una configuración lista para códigos universales de Codespaces con Python 3.11 y Node.js 20, además de un script de aprovisionamiento que instala automáticamente las dependencias de backend y frontend.

1. Crea un Codespace desde la rama principal del repositorio y espera a que finalice la tarea `postCreate` (instala pip, dependencias de Python y ejecuta `npm ci` en `frontend/`).
2. Activa el entorno virtual con `source .venv/bin/activate` antes de ejecutar comandos de backend.
3. Inicia el backend con `uvicorn backend.main:app --reload --port 8000` y, en otra terminal, ejecuta `npm run dev -- --host --port 5173` dentro de `frontend/` para exponer la interfaz.
4. El archivo `devcontainer.json` reenvía automáticamente los puertos 8000 (API FastAPI) y 5173 (Vite) para que se puedan previsualizar desde la interfaz de Codespaces.
5. Los _feature flags_ corporativos (`SOFTMOBILE_ENABLE_*` y `VITE_SOFTMOBILE_ENABLE_*`) se cargan automáticamente en el contenedor, habilitando catálogo pro, transferencias, compras/ventas, listas de precios, analítica avanzada y modo híbrido sin configuraciones manuales.

> El contenedor marca el repositorio como `safe.directory` de Git durante el _postCreate_ para evitar advertencias al ejecutar comandos como `git status` dentro de Codespaces.

> Nota: si el Codespace se crea nuevamente, el script `.devcontainer/postCreate.sh` regenerará el entorno virtual `.venv` y reinstalará dependencias para garantizar una ejecución limpia.

## Verificación Global - Módulo de Inventario Softmobile 2025 v2.2.0

- **Fecha y hora**: 17/10/2025 05:41 UTC.
- **Resumen**: se ejecutó una validación integral que cubre catálogo de productos, existencias, identificadores IMEI/serie, valoración financiera, ajustes y auditoría, reportes avanzados, permisos RBAC e interfaz visual. No se detectaron defectos funcionales ni inconsistencias de datos.
- **Pruebas ejecutadas**: `pytest`, `npm --prefix frontend run build`, `npm --prefix frontend run test`.

| Área evaluada                  | Estado   | Evidencia clave                                                                                                                                          |
| ------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Catálogo de productos          | Completo | Alta, búsqueda avanzada y auditoría de cambios validados en `backend/tests/test_catalog_pro.py`.                                                         |
| Existencias y movimientos      | Completo | Ajustes, alertas y respuestas enriquecidas verificados en `backend/tests/test_stores.py`.                                                                |
| Gestión de IMEI y series       | Completo | Endpoints de identificadores y bloqueos de duplicados cubiertos por `backend/tests/test_device_identifiers.py`.                                          |
| Valoraciones y costos          | Completo | Cálculos ponderados ejercitados en `backend/tests/test_inventory_valuation.py`.                                                                          |
| Ajustes, auditorías y alertas  | Completo | Alertas críticas/preventivas registradas en `backend/tests/test_stores.py`.                                                                              |
| Reportes y estadísticas        | Completo | Exportaciones CSV/PDF/Excel y agregadores probados en `backend/tests/test_reports_inventory.py`.                                                         |
| Roles y permisos               | Completo | Restricciones por rol y utilidades RBAC validadas en `backend/tests/test_stores.py` y `backend/tests/test_roles.py`.                                     |
| Interfaz visual del inventario | Completo | Composición de pestañas, tablas, reportes y analítica confirmada en `frontend/src/modules/inventory/pages/InventoryPage.tsx` y pruebas Vitest asociadas. |

- **Correcciones aplicadas**: no se requirió modificar código; se aseguraron dependencias de pruebas instaladas (por ejemplo, `openpyxl`) antes de la ejecución de la suite.
- **Recomendaciones**: mantener la ejecución periódica de las suites de backend y frontend, y monitorear advertencias de React/Vitest para futuros refinamientos de pruebas.

## Preparación base para despliegue local — 20/10/2025

- **Backend minimalista de arranque**: se añadió `backend/main.py` con FastAPI, CORS, montaje automático de `frontend/dist` cuando esté disponible y conexión lista para SQLite en `backend/database/softmobile.db`.【F:backend/main.py†L1-L123】
- **Variables corporativas**: `.env` centraliza `DB_PATH`, `API_PORT` y `DEBUG` para reproducir la configuración estándar sin exponer credenciales adicionales.【F:backend/.env†L1-L4】
- **Estructura de módulos iniciales**: los directorios `backend/models`, `backend/routes`, `backend/database` y `backend/logs` incorporan `__init__.py` para facilitar futuras extensiones manteniendo compatibilidad con los paquetes existentes.【F:backend/models/**init**.py†L1-L3】【F:backend/routes/**init**.py†L1-L3】【F:backend/database/**init**.py†L1-L3】【F:backend/logs/**init**.py†L1-L3】
- **Dependencias sincronizadas**: `backend/requirements.txt` conserva la lista oficial de librerías certificadas para Softmobile 2025 v2.2.0, listas para instalar en entornos Windows a través de `start_softmobile.bat`.【F:backend/requirements.txt†L1-L8】【F:build/start_softmobile.bat†L1-L13】
- **Bitácoras de preparación**: `backend/logs/setup_report.log` y `backend/logs/verification_status.log` documentan la inicialización y los chequeos básicos de arranque para auditoría futura.【F:backend/logs/setup_report.log†L1-L5】【F:backend/logs/verification_status.log†L1-L5】
- **Frontend alineado**: se añadió `frontend/src/main.jsx` junto a `vite.config.js` con proxy preconfigurado a `http://127.0.0.1:8000/api`, manteniendo la compilación TypeScript existente y asegurando compatibilidad con empaquetado Windows.【F:frontend/src/main.jsx†L1-L2】【F:frontend/vite.config.js†L1-L25】【F:frontend/vite.config.ts†L1-L23】
- **Empaquetado corporativo**: la carpeta `build/` contiene `start_softmobile.bat` y `SoftmobileInstaller.iss` listos para generar instaladores Windows que integren backend y frontend compilado.【F:build/start_softmobile.bat†L1-L13】【F:build/SoftmobileInstaller.iss†L1-L15】
- **Documentación actualizada**: esta sección resume la preparación para Softmobile 2025 v2.2.0 y debe revisarse antes de crear nuevos instaladores.

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
- **Bitácora de auditoría filtrable** con endpoints `/audit/logs`, `/audit/reminders`, `/audit/acknowledgements` y exportaciones CSV/PDF que respetan el motivo corporativo obligatorio; las pruebas de backend confirman filtros, acuses y descargas correctas.【F:backend/app/routers/audit.py†L19-L140】【F:backend/app/routers/reports.py†L190-L248】【F:backend/tests/test_audit_logs.py†L1-L128】
- **Recordatorios automáticos de seguridad** expuestos en el componente `AuditLog.tsx`, que muestra badges de pendiente/atendida, controles de snooze y descargas enlazadas al SDK corporativo, validados mediante pruebas Vitest.【F:frontend/src/modules/security/components/AuditLog.tsx†L1-L210】【F:frontend/src/modules/security/components/AuditLog.tsx†L520-L706】【F:frontend/src/modules/security/components/**tests**/AuditLog.test.tsx†L1-L242】
- **Acuses manuales de resolución** almacenan notas y responsables, sincronizan métricas de pendientes vs. atendidas y alimentan tableros ejecutivos mediante `compute_inventory_metrics`, cubiertos por pruebas dedicadas.【F:backend/app/crud.py†L4789-L5034】【F:backend/tests/test_audit_logs.py†L55-L128】【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L24-L198】
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

## Importación Inteligente desde Excel – v2.2.0 implementada y verificada

- **Servicio de análisis dinámico**: el backend procesa archivos `.xlsx` o `.csv`, normaliza encabezados (minúsculas, sin tildes ni espacios), detecta IMEI por patrón de 15 dígitos y clasifica tipos de datos (texto, número, fecha, booleano) incluso cuando usan variantes como «sí/no», `true/false` o `1/0`. Los resultados se registran en la nueva tabla `importaciones_temp` junto con advertencias y patrones aprendidos para futuras corridas.【F:backend/app/services/inventory_smart_import.py†L16-L453】【F:backend/app/models/**init**.py†L588-L640】
- **Inserción adaptativa**: cada fila crea o actualiza productos y movimientos en inventario. Si faltan campos críticos, el registro se marca como `completo=False`, se insertan valores `NULL` o "pendiente" y se crean sucursales al vuelo cuando el archivo referencia tiendas inexistentes.【F:backend/app/services/inventory_smart_import.py†L234-L410】
- **Resiliencia de formato**: la lectura soporta `.csv` renombrados como `.xlsx`, detecta encabezados vacíos y continúa la importación incluso cuando el archivo no es un ZIP válido, reduciendo rechazos por errores comunes de los proveedores.【F:backend/app/services/inventory_smart_import.py†L66-L158】
- **API dedicada**: se exponen los endpoints `POST /inventory/import/smart`, `GET /inventory/import/smart/history` y `GET /inventory/devices/incomplete`, todos restringidos a roles de gestión y protegidos por el motivo corporativo `X-Reason` (≥5 caracteres).【F:backend/app/routers/inventory.py†L22-L101】
- **Interfaz React optimizada**: la pestaña «Búsqueda avanzada» incorpora el panel **Importar desde Excel (inteligente)** con barra de progreso, tabla de mapeo de columnas (verde = detectada, ámbar = parcial, rojo = faltante), reasignación manual de encabezados y descarga del resumen en PDF/CSV. El historial muestra fecha, totales y advertencias recientes.【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L135-L1675】
- **Correcciones pendientes centralizadas**: la nueva pestaña «Correcciones pendientes» lista los dispositivos incompletos por tienda, resalta los campos faltantes y permite abrir el diálogo de edición inmediatamente tras la importación.【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L1469-L1649】
- **Estilos corporativos**: los bloques `.smart-import` y `.pending-corrections` mantienen el tema oscuro con bordes cian, notas diferenciadas por severidad y tablas responsivas para análisis desde escritorio o tablet.【F:frontend/src/styles.css†L5814-L6068】
- **Cobertura automática**: nuevas pruebas `pytest` validan overrides, creación de sucursales y respuestas HTTP, mientras que Vitest ejercita el flujo completo (preview → overrides → commit) y la pestaña de correcciones.【F:backend/tests/test_inventory_smart_import.py†L1-L145】【F:frontend/src/modules/inventory/pages/**tests**/InventoryPage.test.tsx†L1-L840】

**Estructura mínima compatible**

| Sucursal       | Dispositivo | Identificador   | Color | Cantidad | Precio | Estado     |
| -------------- | ----------- | --------------- | ----- | -------- | ------ | ---------- |
| Sucursal Norte | Serie X     | 990000000000001 | Negro | 3        | 18999  | Disponible |
| CDMX Centro    | Galaxy A35  | 356789012345678 | Azul  | 2        | 8999   | Revisar    |

> La plataforma aprende nuevos encabezados («Dispositivo», «Identificador», «Revisar») y los asocia a los campos internos (`modelo`, `imei`, `estado`). Las columnas faltantes se marcan como pendientes sin detener la carga.

**Flujo sugerido en el panel de Inventario**

1. Ingresar a **Inventario → Búsqueda avanzada → Importar desde Excel (inteligente)** y seleccionar el archivo (`.xlsx`/`.csv`).
2. Presionar **Analizar estructura**, revisar el mapa de columnas y reasignar manualmente encabezados no reconocidos (select «Automático» → encabezado origen).
3. Resolver advertencias si es necesario; repetir el análisis hasta que todas las columnas clave estén en verde.
4. Ejecutar **Importar desde Excel (inteligente)**. El resumen indica registros procesados, nuevos/actualizados, incompletos, columnas faltantes, tiendas creadas y duración.
5. Consultar **Historial reciente** para validar cada corrida y descargar los reportes en PDF/CSV.
6. Ir a **Correcciones pendientes** para completar fichas con datos incompletos y sincronizar con el inventario corporativo.

**Etiquetas y escaneo en Inventario**

- Desde la tabla principal puedes imprimir etiquetas individuales o por lote; el servicio `backend/app/services/inventory_labels.py` genera PDFs A7 con fondo corporativo, QR interno y código de barras **Code128** del SKU para que los escáneres lean tanto dispositivos nuevos como reposiciones.【F:backend/app/services/inventory_labels.py†L1-L118】
- Las fichas de alta y recepción aceptan lectores en modo teclado: basta con enfocar el campo IMEI/SKU y disparar el lector para que el valor quede registrado en la ficha o en los formularios de recepción parcial. El componente `ScanIMEI` se reutiliza en conteos cíclicos y correcciones para capturar identificadores en serie sin escribir manualmente.【F:frontend/src/modules/inventory/components/cycle-count/ScanIMEI.tsx†L1-L36】
- Cada etiqueta integra simultáneamente QR y Code128; al escanear el QR en bodegas se muestra la ficha del dispositivo (`softmobile://device/<id>`), mientras que el Code128 alimenta directamente los formularios de altas y recepciones al pegar el SKU en el campo activo. Esto evita errores de digitación y mantiene sincronizados los estados de inventario y valuación.

El sistema soporta archivos de más de 1 000 filas, conserva compatibilidad con catálogos previos y registra logs `info`/`warning` por importación para auditoría corporativa.【F:backend/app/crud.py†L10135-L10168】

### Plan activo de finalización v2.2.0

| Paso                                                                                                               | Estado      | Directrices                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Conectar recordatorios, snooze y acuses en Seguridad (`AuditLog.tsx`)                                              | ✅ Listo    | La UI consume los servicios corporativos con motivo obligatorio, badges en vivo y registro de notas.                                       |
| Actualizar el tablero global con métricas de pendientes/atendidas                                                  | ✅ Listo    | `GlobalMetrics.tsx` muestra conteos, último acuse y acceso directo a Seguridad desde el dashboard.                                         |
| Automatizar pruebas de frontend (Vitest/RTL) para recordatorios, acuses y descargas                                | ✅ Completo | Suite Vitest activa (`npm --prefix frontend run test`) validando snooze, motivos obligatorios y descargas con `Blob`.                      |
| Registrar bitácora operativa de corridas (`pytest`, `npm --prefix frontend run build`) y validaciones multiusuario | ✅ Completo | Entradas actualizadas en `docs/bitacora_pruebas_*.md` con ejecuciones recientes de backend/frontend y escenarios simultáneos en Seguridad. |

**Directrices rápidas:**

- Captura siempre un motivo corporativo (`X-Reason` ≥ 5 caracteres) al descargar CSV/PDF o registrar un acuse.
- Repite `pytest` y `npm --prefix frontend run build` antes de fusionar cambios y anota el resultado en la bitácora.
- Mantén sincronizados README, `AGENTS.md` y `docs/evaluacion_requerimientos.md` tras completar cada paso del plan activo.

## Actualización Interfaz - Parte 1 (Coherencia Visual y Componentes Globales)

- **Sistema de diseño unificado**: se introduce `frontend/src/theme/designTokens.ts` con paleta, espaciados, radios y sombras corporativas reutilizables; las hojas de estilo globales adoptan variables `--color-*` para mantener el tema oscuro y los alias heredados funcionan sin romper módulos existentes.【F:frontend/src/theme/designTokens.ts†L1-L47】【F:frontend/src/styles.css†L1-L140】
- **Componentes UI reutilizables**: se agregan `Button`, `TextField`, `PageHeader`, `Modal` y `SidebarMenu` en `frontend/src/components/ui/`, habilitando variantes (primario, ghost, peligro, enlace), tamaños, iconografía y etiquetados accesibles en todos los módulos.【F:frontend/src/components/ui/Button.tsx†L1-L41】【F:frontend/src/components/ui/TextField.tsx†L1-L47】【F:frontend/src/components/ui/PageHeader.tsx†L1-L22】【F:frontend/src/components/ui/Modal.tsx†L1-L116】【F:frontend/src/components/ui/SidebarMenu.tsx†L1-L36】
- **Controles heredados alineados**: los estilos legacy (`.btn`, `.button`, badges, alerts y formularios) adoptan los nuevos tokens de color y espaciado, unificando estados de foco, fondos suaves y bordes corporativos; el botón flotante de retorno ahora reutiliza `Button` con iconografía `ArrowUp` para mantener accesibilidad y consistencia visual.【F:frontend/src/styles.css†L140-L320】【F:frontend/src/styles.css†L2580-L2725】【F:frontend/src/components/BackToTopButton.tsx†L1-L46】
- **Layout corporativo consistente**: el dashboard adopta `PageHeader` y `SidebarMenu` para alinear encabezados, búsquedas, menú hamburguesa y acciones rápidas; `CompactModeToggle` y `WelcomeHero` utilizan los nuevos botones y la búsqueda global comparte estilos en todas las pantallas.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L1-L255】【F:frontend/src/components/CompactModeToggle.tsx†L1-L33】【F:frontend/src/components/WelcomeHero.tsx†L1-L67】
- **Modal y formularios refinados**: `DeviceEditDialog` reusa `Modal` y botones nuevos, bloquea el cierre durante envíos y mantiene el formulario auditable sin duplicar animaciones personalizadas.【F:frontend/src/modules/inventory/components/DeviceEditDialog.tsx†L1-L322】
- **Gráficas y login coherentes**: el login ahora emplea `TextField` y botones unificados; dashboards analíticos (`GlobalMetrics`, `GlobalReportsDashboard`, `InventoryPage`, `Customers`) migran a la paleta corporativa evitando hexadecimales sueltos.【F:frontend/src/components/LoginForm.tsx†L1-L55】【F:frontend/src/modules/dashboard/components/GlobalMetrics.tsx†L1-L243】【F:frontend/src/modules/reports/components/GlobalReportsDashboard.tsx†L1-L348】【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L1-L116】【F:frontend/src/modules/operations/components/Customers.tsx†L1-L1680】
- **Encabezados y filtros armonizados**: `PageHeader` admite iconografía, estado y metadatos reutilizables; `ModuleHeader` lo envuelve para todos los módulos y la hoja de estilos refuerza sus variantes y responsive. El módulo de inventario actualiza los filtros con `TextField`, botones unificados y tooltips basados en tokens para sostener la coherencia visual.【F:frontend/src/components/ui/PageHeader.tsx†L1-L44】【F:frontend/src/components/ModuleHeader.tsx†L1-L53】【F:frontend/src/styles.css†L470-L560】【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L600-L720】
- **Estilos responsivos actualizados**: `frontend/src/styles.css` define nuevas clases (`.app-sidebar`, `.page-header`, `.app-search`, `.ui-modal`, `.ui-button`, `.ui-field`, etc.) y reglas responsivas que mantienen la barra lateral y el encabezado coherentes en escritorios y tablets, preservando compatibilidad con estructuras previas del dashboard.【F:frontend/src/styles.css†L140-L420】【F:frontend/src/styles.css†L360-L460】【F:frontend/src/styles.css†L600-L720】
- **Tokens extendidos y limpieza de hexadecimales**: se añadieron variaciones corporativas (resplandores, resaltados y tintes) en `designTokens.ts` y se depuraron badges, pills, tablas, timeline, transferencias, formularios y recordatorios para que consuman únicamente `var(--color-*)`, evitando valores fijos y asegurando el soporte del tema claro/oscuro.【F:frontend/src/theme/designTokens.ts†L16-L66】【F:frontend/src/styles.css†L200-L420】【F:frontend/src/styles.css†L1680-L4200】

## Actualización Interfaz - Parte 2 (Optimización de Rendimiento y Carga)

- **División de código por módulos pesados**: las rutas del dashboard ahora se cargan con `React.lazy` y límites de suspense dedicados, generando fragmentos independientes para Inventario, Operaciones, Analítica, Reportes, Seguridad, Sincronización, Usuarios y Reparaciones sin alterar la navegación existente.【F:frontend/src/modules/dashboard/routes.tsx†L1-L112】
- **Carga diferida del shell principal**: `App.tsx` retrasa la descarga del módulo `Dashboard` hasta después del ingreso y muestra un loader corporativo reutilizando la superposición oscura para mantener la coherencia visual durante la espera.【F:frontend/src/App.tsx†L1-L205】
- **Contexto memoizado sin renders innecesarios**: `DashboardContext` encapsula callbacks, selectores y valores derivados con `useCallback`/`useMemo`, evitando que todo el árbol se vuelva a renderizar al actualizar métricas, toasts o sincronizaciones de cola.【F:frontend/src/modules/dashboard/context/DashboardContext.tsx†L160-L720】
- **Caché inteligente y deduplicación de peticiones**: el helper `request` memoiza respuestas GET durante 60 segundos, agrupa solicitudes concurrentes para compartir la misma respuesta y limpia tanto caché como promesas en vuelo tras operaciones mutables; las utilidades de reseteo se ejercitan en las nuevas pruebas de Vitest.【F:frontend/src/api.ts†L1586-L1750】【F:frontend/src/api.cache.test.ts†L1-L142】
- **Validación automatizada de memoización**: la suite `api.cache.test.ts` comprueba que las llamadas repetidas reutilicen la caché y que los POST limpien resultados previos, reforzando el umbral de rendimiento solicitado para Softmobile 2025 v2.2.0.【F:frontend/src/api.cache.test.ts†L1-L109】
- **Paneles de Operaciones bajo demanda**: el acordeón de Operaciones encapsula POS, compras, ventas, transferencias e historial dentro de `React.lazy` y `Suspense`, cargando cada sección únicamente al expandirla y reutilizando loaders compactos para mantener la percepción de fluidez.【F:frontend/src/modules/operations/pages/OperationsPage.tsx†L1-L140】
- **Analítica diferida con loaders accesibles**: el tablero analítico se descarga de forma perezosa y muestra un esqueleto corporativo mientras llega el fragmento pesado de gráficas, reduciendo el peso del bundle inicial sin perder contexto para el usuario.【F:frontend/src/modules/analytics/pages/AnalyticsPage.tsx†L1-L80】
- **Reportes ejecutivos perezosos**: la página de reportes globales ahora importa el tablero consolidado mediante `React.lazy` y un loader accesible, con lo que las alertas y exportaciones se descargan sólo al ingresar en la vista especializada.【F:frontend/src/modules/reports/pages/GlobalReportsPage.tsx†L1-L44】
- **Pruebas de rendimiento enfocadas en UI**: se añadieron suites que verifican la carga secuencial del acordeón y que el arranque de la aplicación se mantiene por debajo de los 2 segundos, documentando la ausencia de renders extra en escenarios críticos.【F:frontend/src/modules/operations/pages/OperationsPage.lazy.test.tsx†L1-L88】【F:frontend/src/App.performance.test.tsx†L1-L18】
- **Inventario modular diferido**: `InventoryPage.tsx` aplica `React.lazy` y `Suspense` a la tabla, formularios, búsqueda avanzada y paneles de reportes, además de memoizar tarjetas/resúmenes con `useMemo`/`useCallback` y loaders accesibles para evitar renders innecesarios mientras llegan los fragmentos pesados.【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L1-L1208】
- **Gráfica de categorías desacoplada**: el componente `InventoryCategoryChart.tsx` extrae las dependencias de Recharts en un chunk aislado, reutiliza la paleta corporativa y memoriza la lista para mantener estable la carga diferida del inventario.【F:frontend/src/modules/inventory/components/InventoryCategoryChart.tsx†L1-L71】

## Actualización Interfaz - Parte 3 (Panel, Usabilidad y Accesibilidad)

- **Panel central unificado**: se integra `AdminControlPanel` dentro del dashboard para ofrecer accesos rápidos a cada módulo habilitado, mostrar notificaciones activas y mantener una navegación consistente desde el panel principal.【F:frontend/src/modules/dashboard/components/AdminControlPanel.tsx†L1-L72】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L33-L241】
- **Indicadores operativos accesibles**: `ActionIndicatorBar` resume el estado de guardado, sincronización y alertas con roles `status` y soporte para lectores de pantalla, mejorando la respuesta a eventos críticos en tiempo real.【F:frontend/src/modules/dashboard/components/ActionIndicatorBar.tsx†L1-L118】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L221-L241】
- **Diferenciación visual por rol**: el layout aplica banners y variantes cromáticas específicas para perfiles `ADMIN`, `GERENTE`, `OPERADOR` e invitados, reforzando la orientación contextual sin salir del tema corporativo.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L120-L182】【F:frontend/src/styles.css†L4604-L4703】
- **Contraste y adaptabilidad reforzados**: la hoja de estilos amplía fondos, focos y gradientes para el panel central, asegurando contraste AA en indicadores, badges y tarjetas del centro de control en cualquier rol corporativo.【F:frontend/src/styles.css†L4705-L4956】
- **Centro de notificaciones accesible y atajos inclusivos**: se incorpora `NotificationCenter` con soporte `details/summary`, focos visibles y variantes por rol para listar alertas, errores y avisos de sincronización; los badges del panel añaden estados `warning/danger/info` y el dashboard suma un enlace «Saltar al contenido principal» para navegación por teclado.【F:frontend/src/modules/dashboard/components/NotificationCenter.tsx†L1-L85】【F:frontend/src/modules/dashboard/components/AdminControlPanel.tsx†L1-L129】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L33-L280】【F:frontend/src/styles.css†L180-L213】【F:frontend/src/styles.css†L4829-L5017】
- **Orientación activa y reducción de movimiento**: el centro de control marca el módulo abierto con `aria-current`, agrega mensajes contextuales para lectores de pantalla, refuerza los badges según su estado y respeta `prefers-reduced-motion` para quienes limitan animaciones sin perder contraste corporativo.【F:frontend/src/modules/dashboard/components/AdminControlPanel.tsx†L1-L129】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L33-L280】【F:frontend/src/styles.css†L4746-L5017】

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

## Actualización Sucursales - Parte 2 (Sincronización y Replicación)

- **Sincronización integral de inventario, ventas y compras**: las operaciones críticas (`create_device`, `update_device`, movimientos de inventario, ciclo de ventas POS y flujo completo de compras) generan eventos estructurados en `sync_outbox` con `store_id`, cantidades y costos para cada sucursal, garantizando la réplica prioritaria en entornos distribuidos.【F:backend/app/crud.py†L371-L421】【F:backend/app/crud.py†L5758-L5906】【F:backend/app/crud.py†L7034-L7111】
- **Procesos automáticos y manuales coordinados**: el servicio `run_sync_cycle` marca eventos como `SENT`, reintenta fallidos y registra métricas (`eventos_procesados`, `diferencias_detectadas`) tanto desde el cron interno (`_sync_job`) como al invocar `POST /sync/run`, permitiendo disparos por API, programador o botón en la UI.【F:backend/app/services/sync.py†L151-L209】【F:backend/app/services/scheduler.py†L52-L108】【F:backend/app/routers/sync.py†L18-L80】
- **Operación offline con reintentos híbridos**: `requeue_failed_outbox_entries` reactiva eventos pendientes cuando una tienda estuvo desconectada, y la prueba `backend/tests/test_sync_offline_mode.py` verifica que las entradas regresen a `PENDING` antes de reintentar la sincronización.【F:backend/app/services/sync.py†L19-L55】【F:backend/tests/test_sync_offline_mode.py†L24-L104】
- **Detección y bitácora de discrepancias**: `detect_inventory_discrepancies` compara cantidades por SKU entre sucursales y `log_sync_discrepancies` registra alertas `sync_discrepancy` en `AuditLog` para auditar desviaciones de stock.【F:backend/app/services/sync.py†L58-L137】【F:backend/app/crud.py†L4665-L4684】
- **Auditoría y respaldo corporativo**: `mark_outbox_entries_sent` deja trazas `sync_outbox_sent` por cada evento sincronizado y `services/backups.generate_backup` ofrece exportaciones ZIP/PDF, cubiertas por `backend/tests/test_backups.py`, para respaldar los datos distribuidos.【F:backend/app/crud.py†L4690-L4732】【F:backend/app/services/backups.py†L241-L275】【F:backend/tests/test_backups.py†L24-L78】
- **Cobertura de pruebas integral**: la suite incorpora `backend/tests/test_sync_replication.py` y `backend/tests/test_sync_full.py`, que validan la sincronización de inventario, ventas y compras, el cambio de estado a `SENT` y la generación de discrepancias multi-sucursal.【F:backend/tests/test_sync_replication.py†L34-L129】【F:backend/tests/test_sync_full.py†L23-L121】

## Actualización Sucursales - Parte 3 (Interfaz y Control Central)

- **Dashboard centralizado**: `frontend/src/modules/sync/pages/SyncPage.tsx` incorpora una tarjeta «Dashboard de sincronización» que resume estado actual, última ejecución, sucursales monitorizadas, inventario agregado, cola híbrida y transferencias activas con los registros recientes de `/sync/sessions`.【F:frontend/src/modules/sync/pages/SyncPage.tsx†L56-L184】【F:frontend/src/styles.css†L186-L272】
- **Detalle operativo de sucursales**: se mantiene la tabla «Panorama de sucursales» con estado, última sincronización, transferencias pendientes, conflictos abiertos e inventario para cada tienda, respaldando la supervisión diaria desde `/sync/overview`.【F:frontend/src/modules/sync/pages/SyncPage.tsx†L186-L259】
- **Sistema de transferencias enriquecido**: la sección «Transferencias entre tiendas» ahora muestra el flujo origen→destino con motivo, totales y un cuadro detallado de productos/quantidades gracias a los datos de `/transfers/report`, además de conservar los totales ejecutivos y exportaciones PDF/Excel.【F:frontend/src/modules/sync/pages/SyncPage.tsx†L261-L360】【F:frontend/src/styles.css†L308-L370】
- **Conflictos y reportes corporativos**: se preserva el panel de discrepancias con exportación PDF/Excel y el módulo `SyncPanel` continúa ofreciendo sincronización manual, respaldos y descargas de inventario con motivo corporativo obligatorio.【F:frontend/src/modules/sync/pages/SyncPage.tsx†L362-L515】
- **Consumo optimizado del API de transferencias**: el SDK web ajusta `listTransfers` para solicitar `/transfers?limit=25&store_id=…` evitando redirecciones innecesarias, estandarizando la cabecera de autorización y devolviendo la lista lista para el tablero híbrido.【F:frontend/src/api.ts†L2722-L2729】
- **Documentación actualizada**: este README, `CHANGELOG.md` y `AGENTS.md` registran la fase bajo «Actualización Sucursales - Parte 3 (Interfaz y Control Central)» para preservar la línea de tiempo corporativa.

## Actualización Compras - Parte 3 (Interfaz y Reportes)

- **Formulario de registro directo**: el módulo de Operaciones incorpora un formulario dedicado para capturar compras inmediatas seleccionando proveedor, productos y tasa de impuesto; calcula subtotal/impuesto/total en tiempo real y registra el movimiento mediante `createPurchaseRecord` respetando el motivo corporativo obligatorio.
- **Listado corporativo con filtros avanzados**: la vista de historial permite filtrar por proveedor, usuario, rango de fechas, estado o texto libre y expone acciones para exportar el resultado a PDF o Excel usando los nuevos helpers `exportPurchaseRecordsPdf|Excel`.
- **Panel integral de proveedores**: se habilita la administración completa de proveedores de compras (alta/edición, activación/inactivación y exportación CSV) junto con un historial filtrable conectado a `getPurchaseVendorHistory`, mostrando totales y métricas para auditar su desempeño.
- **Estadísticas operativas**: se consumen los endpoints de métricas para presentar totales de inversión, rankings de proveedores/usuarios y acumulados mensuales en tarjetas responsive que refuerzan la planeación de compras.
- **Documentación actualizada**: este README, el `CHANGELOG.md` y `AGENTS.md` registran la fase bajo el epígrafe «Actualización Compras - Parte 3 (Interfaz y Reportes)», manteniendo la trazabilidad de la evolución del módulo.
- **Referencia técnica y pruebas**: la interfaz vive en `frontend/src/modules/operations/components/Purchases.tsx` y consume los servicios de `backend/app/routers/purchases.py`; la suite `backend/tests/test_purchases.py::test_purchase_records_and_vendor_statistics` valida exportaciones PDF/Excel, filtros y estadísticas para asegurar el cumplimiento de los cinco requisitos funcionales del módulo.

## Actualización Usuarios - Parte 1 (Estructura y Roles Base)

- **Tabla `usuarios` normalizada**: la entidad histórica `users` se renombró a `usuarios` incorporando los campos corporativos `id_usuario`, `correo` (único), `nombre`, `telefono`, `rol`, `sucursal_id`, `estado` y `fecha_creacion`, además de mantener `password_hash` e integraciones existentes. El ORM utiliza alias para conservar compatibilidad con consumidores previos.
- **Migración 202503010008**: la nueva migración renombra columnas e índices, sincroniza `estado` con `is_active`, preserva contraseñas y calcula el rol primario de cada colaborador usando prioridad ADMIN→GERENTE→OPERADOR→INVITADO. La unicidad de correos queda reforzada por un índice exclusivo.
- **Roles base ampliados**: se incorporó el rol `INVITADO` al conjunto predeterminado y la lógica de creación/actualización de usuarios ahora persiste el rol principal en la columna `rol`, manteniendo la tabla relacional `user_roles` para múltiples permisos corporativos.
- **Tabla `permisos` corporativa**: se agregó la entidad opcional `permisos` (`id_permiso`, `rol`, `modulo`, `puede_ver`, `puede_editar`, `puede_borrar`) con clave foránea hacia `roles.name`, unicidad por módulo/rol e índices para consultas rápidas, preservando compatibilidad retroactiva.
- **Cobertura automatizada**: `backend/tests/test_usuarios_schema.py` inspecciona columnas, índices, claves foráneas y la presencia de los roles base (ADMIN, GERENTE, OPERADOR, INVITADO), garantizando la unicidad de correos y la integridad referencial del módulo.
- **Valores predeterminados auditados**: la prueba `backend/tests/test_usuarios_schema.py::test_usuarios_columnas_indices_y_fk` también confirma que `rol` y `estado` conserven los valores por omisión `OPERADOR` y `ACTIVO`, respectivamente, y que el índice `ix_usuarios_correo` mantenga la unicidad sobre la columna `correo`.
- **API y esquemas**: los esquemas Pydantic aceptan alias en español (`correo`, `nombre`, `sucursal_id`) y devuelven metadatos (`fecha_creacion`, `estado`, `rol`, `telefono`) sin romper las pruebas existentes. La documentación se actualizó para reflejar los nuevos campos obligatorios del módulo de seguridad.

## Actualización Usuarios - Parte 2 (Seguridad y Auditoría)

- **Autenticación dual**: `/auth/token` continúa emitiendo JWT y ahora registra sesiones con fecha de expiración; además se estrena `/auth/session`, que crea una sesión segura persistida en base de datos y entrega una cookie HTTPOnly configurable (`SOFTMOBILE_SESSION_COOKIE_*`).
- **Control de intentos y bloqueo automático**: cada credencial inválida incrementa `failed_login_attempts`, persiste la fecha de intento y, al alcanzar `SOFTMOBILE_MAX_FAILED_LOGIN_ATTEMPTS`, fija `locked_until` evitando accesos durante `SOFTMOBILE_ACCOUNT_LOCK_MINUTES`. Los eventos se auditan en `audit_logs` como `auth_login_failed` y `auth_login_success`.
- **Recuperación de contraseña con token temporal**: `/auth/password/request` genera tokens efímeros almacenados en `password_reset_tokens` y `/auth/password/reset` permite reestablecer la clave (hash bcrypt con `salt`), revoca sesiones activas y limpia contadores de bloqueo. En modo pruebas se devuelve el `reset_token` para automatizar flujos.
- **Permisos modulares obligatorios**: el middleware centraliza la validación de permisos por módulo mediante la tabla `permisos` y la nueva matriz `ROLE_MODULE_PERMISSION_MATRIX`. Cada petición determina la acción (`view`, `edit`, `delete`) según el método HTTP y rechaza accesos sin `puede_ver/editar/borrar`, garantizando trazabilidad por rol sin romper compatibilidad.
- **Sesiones auditables**: `active_sessions` incluye `expires_at`, se actualiza `last_used_at` al utilizar cookies o JWT y se registra la revocación automática cuando expiran. Las rutas `/security/sessions` siguen permitiendo listar y revocar sesiones activas con motivo corporativo.
- **Cobertura automatizada**: `backend/tests/test_security.py` incorpora pruebas para bloqueo y restablecimiento de contraseñas, sesión basada en cookies y rechazo de operaciones de edición para roles `INVITADO`, asegurando el cumplimiento de requisitos de seguridad y auditoría en Softmobile 2025 v2.2.0.
- **Verificación 27/10/2025 19:30 UTC** — Se repasó el checklist corporativo de seguridad confirmando: inicio de sesión dual (JWT o cookie segura), hash bcrypt con `salt`, control de sesiones activas, bitácora de auditoría para ventas/compras/inventario, bloqueo tras intentos fallidos, recuperación de contraseña con token temporal y validación de permisos en cada módulo. La suite `pytest` valida los flujos principales (`backend/tests/test_security.py`, `backend/tests/test_sales.py`, `backend/tests/test_purchases.py`).

## Actualización Usuarios - Parte 3 (Interfaz y Panel de Roles)

- **Gestión visual integral**: `frontend/src/modules/users/components/UserManagement.tsx` incorpora un dashboard oscuro con totales de cuentas, actividad reciente, sesiones activas y alertas del módulo, acompañado de filtros combinados y un formulario lateral para altas/ediciones.【F:frontend/src/modules/users/components/UserManagement.tsx†L1-L493】【F:frontend/src/styles.css†L448-L604】
- **Verificación funcional 28/10/2025**: se comprobó que la pantalla de usuarios cubre lista con filtros combinados, creación/edición con formulario lateral, cambio de estado activo/inactivo, asignación de roles y permisos interactivos y exportación PDF/Excel consumiendo los servicios corporativos existentes.【F:frontend/src/modules/users/components/UserManagement.tsx†L452-L1048】【F:frontend/src/api.ts†L1613-L1763】【F:backend/app/routers/users.py†L42-L210】
- **Servicios ampliados de seguridad**: el backend publica `GET /users/dashboard`, `GET /users/export` (PDF/Excel) y la edición de perfiles vía `PUT /users/{id}` junto con el cambio de estado `PATCH /users/{id}`, consumidos por los nuevos clientes de `frontend/src/api.ts` y `frontend/src/modules/users/services/usersService.ts`.
- **Matriz de permisos editable**: `GET /users/permissions` y `PUT /users/roles/{role}/permissions` permiten actualizar privilegios por módulo sin perder compatibilidad, registrando la acción `role_permissions_updated` y manteniendo la persistencia en la tabla `permisos`.
- **Reportes corporativos**: `backend/app/services/user_reports.py` genera directorios PDF/Excel en tema oscuro reutilizando la cabecera `X-Reason`, garantizando descargas auditables para auditorías internas.【F:backend/app/services/user_reports.py†L1-L238】
- **Robustez operativa en la UI**: el panel ahora tolera métricas vacías sin fallar, ordena roles y permisos sin mutar el estado de React y mantiene columnas consistentes en la tabla de usuarios y en la matriz de seguridad.【F:frontend/src/modules/users/components/UserManagement.tsx†L80-L195】【F:frontend/src/modules/users/components/UserManagement.tsx†L833-L1016】
- **Control de cuentas bloqueadas**: se incorporó el filtro «Bloqueados» en listados y exportaciones (`status=locked`), además de indicadores visuales en la tabla de usuarios y totales del dashboard para detectar accesos suspendidos sin afectar compatibilidad previa.【F:frontend/src/modules/users/components/UserManagement.tsx†L138-L210】【F:frontend/src/api.ts†L29-L205】【F:backend/app/routers/users.py†L74-L155】【F:backend/app/crud.py†L1224-L1394】
- **Cobertura dedicada**: `backend/tests/test_users_management.py` valida filtros, exportaciones, actualización de perfiles, edición de permisos, flujo de autenticación posterior al cambio de contraseña y los nuevos controles de motivo obligatorio.【F:backend/tests/test_users_management.py†L1-L234】
- **Motivos obligatorios y bitácora ampliada**: los endpoints `PUT /users/{id}/roles` y `PATCH /users/{id}` ahora exigen `X-Reason`, registran acciones `user_roles_updated`/`user_status_changed` con el motivo en auditoría y cuentan con pruebas que confirman el rechazo cuando falta el encabezado corporativo.【F:backend/app/routers/users.py†L136-L198】【F:backend/app/crud.py†L1289-L1324】【F:backend/tests/test_users_management.py†L173-L234】
- **28/10/2025 09:55 UTC** — Se ajustó `crud.list_users` para aplicar `.unique()` en consultas con `joinedload`, se preservan permisos personalizados en `ensure_role_permissions`, las cuentas inactivas se reactivan al renovar contraseña y las rutas `/users/dashboard` y `/users/export` quedaron antes de `/{user_id}` para evitar respuestas 422. `pytest` se ejecutó completo en esta iteración.【F:backend/app/crud.py†L1236-L1325】【F:backend/app/routers/users.py†L109-L210】【85adf2†L1-L24】

## Actualización Sistema - Parte 1 (Logs y Auditoría General)

- **Tablas dedicadas**: se incorporan `logs_sistema` y `errores_sistema` con índices por usuario, módulo, fecha y nivel para garantizar trazabilidad segura.
- **Severidades alineadas**: los eventos se clasifican automáticamente en `info`, `warning`, `error` y `critical`, integrándose con la bitácora de auditoría existente.
- **Filtros corporativos**: nuevos endpoints `/logs/sistema` y `/logs/errores` permiten filtrar por usuario, módulo y rango de fechas ISO 8601 con acceso restringido a administradores.【F:backend/app/routers/system_logs.py†L1-L67】
- **Registro automático de errores**: middleware central captura fallos críticos del API, preserva stack trace, módulo y dirección IP de origen sin exponer datos sensibles.【F:backend/app/main.py†L56-L123】
- **Cobertura automatizada**: `backend/tests/test_system_logs.py` valida la clasificación `info/warning/error/critical`, los filtros por usuario, módulo (ventas, compras, inventario, ajustes, usuarios) y fechas, además de conservar la IP de origen en los errores corporativos y comprobar que los ajustes se cataloguen bajo `ajustes` gracias al mapeo por prefijos específicos.【F:backend/tests/test_system_logs.py†L1-L150】【F:backend/app/crud.py†L326-L434】
- **Acceso restringido para auditoría**: la prueba `test_system_logs_rejects_non_admin_access` confirma que las rutas `/logs/sistema` exigen autenticación y rol `ADMIN`, devolviendo `401/403` ante peticiones no autorizadas y asegurando que la bitácora se conserve en un canal seguro.【F:backend/tests/test_system_logs.py†L152-L187】【F:backend/app/routers/system_logs.py†L1-L67】
- **Documentación sincronizada**: este README, `CHANGELOG.md` y `AGENTS.md` registran la actualización bajo «Actualización Sistema - Parte 1 (Logs y Auditoría General)» para mantener la trazabilidad operativa.

## Actualización Sistema - Parte 2 (Respaldos y Recuperación)

- **Respaldos manuales y automáticos**: el servicio `services/backups.generate_backup` construye snapshots PDF/JSON/SQL, empaqueta archivos críticos y registra metadatos, rutas y tamaño total en `backup_jobs`, diferenciando entre modos `manual` y `automatico` sin alterar integraciones existentes.【F:backend/app/services/backups.py†L205-L320】【F:backend/app/crud.py†L6575-L6624】
- **Volcado SQL seguro**: `_dump_database_sql` reemplaza `iterdump()` por instrucciones `DELETE/INSERT` que respetan llaves foráneas, normalizan literales (enums, fechas, binarios) y omiten `backup_jobs` para evitar perder el historial de respaldos durante una restauración en caliente.【F:backend/app/services/backups.py†L72-L121】
- **Restauraciones parciales o totales**: `restore_backup` valida que los componentes solicitados existan en el respaldo, permite seleccionar subconjuntos (solo configuración, solo archivos críticos, etc.), definir un destino personalizado y decidir si aplicar el SQL directamente sobre la base activa, registrando cada recuperación en `logs_sistema` sin invalidar el job original.【F:backend/app/services/backups.py†L84-L145】【F:backend/app/services/backups.py†L324-L374】【F:backend/app/routers/backups.py†L42-L60】【F:backend/app/crud.py†L6629-L6645】【F:backend/tests/test_backups.py†L104-L144】
- **API protegida para administradores**: el router `/backups` exige rol `ADMIN`, expone `/run` para ejecuciones manuales, `/history` para consultar el catálogo reciente y `/backups/{id}/restore` para restauraciones controladas con la bandera `aplicar_base_datos`.【F:backend/app/routers/backups.py†L1-L49】
- **Descarga controlada de respaldos**: `GET /backups/{id}/download` habilita exportaciones `.zip`, `.sql` o `.json` para cada respaldo, utiliza el enum `BackupExportFormat` para validar la solicitud, confirma que el archivo exista físicamente y mantiene la restricción al rol `ADMIN`.【F:backend/app/routers/backups.py†L1-L87】【F:backend/app/schemas/**init**.py†L36-L44】【F:backend/tests/test_backups.py†L146-L188】
- **Esquemas consistentes**: `BackupRunRequest`, `BackupRestoreRequest` y `BackupRestoreResponse` describen notas, componentes y destino opcional, mientras que el enum `BackupComponent` queda registrado en el modelo `BackupJob` para mantener la trazabilidad de los archivos generados.【F:backend/app/schemas/**init**.py†L3103-L3159】【F:backend/app/models/**init**.py†L66-L111】【F:backend/app/models/**init**.py†L588-L613】
- **Cobertura automatizada**: `backend/tests/test_backups.py` valida respaldos completos, restauraciones por componente, presencia de archivos críticos, registros en `logs_sistema` y la reautenticación posterior cuando se aplica el SQL sobre la base activa.【F:backend/tests/test_backups.py†L1-L205】
- **Documentación sincronizada**: este README, `CHANGELOG.md` y `AGENTS.md` documentan la fase «Actualización Sistema - Parte 2 (Respaldos y Recuperación)» para preservar la trazabilidad operativa.
- **Verificación 30/10/2025 12:55 UTC**: se confirmó que los respaldos programados y manuales se registran con modo correspondiente, que las exportaciones `.zip`, `.sql` y `.json` permanecen disponibles por respaldo, que la restauración admite seleccionar base de datos, configuraciones o archivos críticos por separado y que cada operación queda asentada en `logs_sistema`, restringiendo las rutas al rol `ADMIN` conforme a las pruebas activas (`test_backups.py`).

## Actualización Sistema - Parte 3 (Reportes y Notificaciones) (31/10/2025 09:40 UTC)

- El router `/reports/global` incorpora los endpoints `overview`, `dashboard` y `export` para consolidar bitácoras, totales por severidad, distribución por módulo y alertas de sincronización crítica; el acceso permanece restringido a `REPORTE_ROLES` y exige motivo corporativo en exportaciones multiformato.【F:backend/app/routers/reports.py†L1-L160】【F:backend/app/crud.py†L360-L760】
- El servicio `services/global_reports.py` genera PDF, Excel y CSV en tema oscuro con tablas de métricas, series de actividad, alertas y detalle de logs/errores reutilizando los colores corporativos para conservar la identidad visual en auditorías ejecutivas.【F:backend/app/services/global_reports.py†L1-L285】
- Se depuró la prueba `test_global_reports.py` para importar únicamente `datetime`, conservando la simulación de fallas de sincronización y asegurando que el módulo registre alertas y totales sin dependencias innecesarias durante las verificaciones automatizadas.【F:backend/tests/test_global_reports.py†L1-L36】
- La prueba `backend/tests/test_global_reports.py` cubre filtros, agregados, alertas por sincronización fallida y las tres exportaciones para garantizar que el backend permanezca íntegro al consumir los nuevos servicios.【F:backend/tests/test_global_reports.py†L1-L138】
- La UI suma el módulo «Reportes globales» con navegación dedicada, filtros por fecha/módulo/severidad, tablero gráfico (línea, barras, pastel), listas de alertas y tablas accesibles de logs/errores mediante el componente `GlobalReportsDashboard`. Las descargas respetan el motivo corporativo y reutilizan la paleta azul/cian.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L1-L140】【F:frontend/src/modules/reports/components/GlobalReportsDashboard.tsx†L1-L324】【F:frontend/src/modules/reports/pages/GlobalReportsPage.tsx†L1-L20】
- El SDK web expone helpers tipados para consultar y exportar el reporte global (`getGlobalReportOverview|Dashboard`, `downloadGlobalReportPdf|Xlsx|Csv`), además de los tipos `GlobalReport*` que normalizan severidades y alertas en la capa cliente.【F:frontend/src/api.ts†L120-L470】【F:frontend/src/api.ts†L3680-L3820】
- La suite de frontend añade `GlobalReportsDashboard.test.tsx` para validar la renderización de métricas y alertas, evitando regresiones al simular respuestas del backend y motivos corporativos automatizados.【F:frontend/src/modules/reports/components/**tests**/GlobalReportsDashboard.test.tsx†L1-L108】

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

- La vista `frontend/src/modules/operations/components/Customers.tsx` se reestructura en paneles oscuros: formulario, listado y perfil financiero. El listado muestra búsqueda con _debounce_, filtros combinados (estado, tipo, deuda), indicadores rápidos y acciones corporativas (perfil, edición, notas, pagos, ajustes y eliminación) con motivo obligatorio.
- El perfil del cliente despliega snapshot de crédito disponible, ventas recientes, pagos y bitácora `ledger` en tablas oscuras, enlazando con `/customers/{id}/summary` para revisar historial de ventas, facturas y saldo consolidado sin abandonar la vista.
- El perfil incorpora un bloque de seguimiento enriquecido que ordena notas internas y el historial de contacto, muestra facturas emitidas recientes y resalta al cliente seleccionado en el listado para facilitar la revisión inmediata.
- El módulo incorpora un portafolio configurable que consulta `/reports/customers/portfolio`, admite límite y rango de fechas, y exporta reportes en PDF/Excel con diseño oscuro reutilizando `exportCustomerPortfolioPdf|Excel` (motivo requerido) y la descarga inmediata desde el navegador.
- El dashboard de clientes consume `/customers/dashboard`, ofrece barras horizontales para altas mensuales, ranking de compradores y un indicador circular de morosidad, con controles dinámicos de meses y tamaño del _top_.
- Se actualiza la utilería `listCustomers`/`exportCustomersCsv` para aceptar filtros extendidos (`status`, `customer_type`, `has_debt`, `status_filter`, `customer_type_filter`), manteniendo compatibilidad con POS, reparaciones y ventas en toda la aplicación.
- Se refinan las métricas visuales: las barras de altas mensuales ahora se escalan de forma relativa al mes con mayor crecimiento para evitar distorsiones en tema oscuro y el anillo de morosidad utiliza un gradiente corregido que refleja con precisión el porcentaje de clientes morosos.

## Mejora visual v2.2.0 — Dashboard modularizado

La actualización UI de febrero 2025 refuerza la experiencia operativa sin modificar rutas ni versiones:

- **Encabezados consistentes (`ModuleHeader`)** para cada módulo del dashboard con iconografía, subtítulo y badge de estado (verde/amarillo/rojo) alineado al estado operativo reportado por cada contexto.
- **Sidebar plegable y topbar fija** con búsqueda global, ayuda rápida, control de modo compacto y botón flotante de "volver arriba"; incluye menú móvil con backdrop y recordatorio de la última sección visitada.
- **Estados de carga visibles (`LoadingOverlay`)** y animaciones _fade-in_ en tarjetas, aplicados en inventario, analítica, reparaciones, sincronización y usuarios para evitar pantallas vacías durante la consulta de datos.
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
- **Clasificación comercial auditada**: el filtro `estado_comercial` acepta `nuevo`, `A`, `B`, `C`, normaliza el valor y rechaza entradas inválidas. Cada búsqueda genera un evento `inventory_catalog_search` con los filtros aplicados y el total de coincidencias, visible en la bitácora y el logger `softmobile.audit`.
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

   | Variable                                 | Descripción                                                             | Valor por defecto                      |
   | ---------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------- |
   | `SOFTMOBILE_DATABASE_URL`                | Cadena de conexión SQLAlchemy                                           | `sqlite:///./softmobile.db`            |
   | `SOFTMOBILE_SECRET_KEY`                  | Clave para firmar JWT                                                   | `softmobile-super-secreto-cambia-esto` |
   | `SOFTMOBILE_TOKEN_MINUTES`               | Minutos de vigencia de tokens                                           | `60`                                   |
   | `SOFTMOBILE_SYNC_INTERVAL_SECONDS`       | Intervalo de sincronización automática                                  | `1800` (30 minutos)                    |
   | `SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS` | Tiempo de espera antes de reagendar eventos fallidos en la cola híbrida | `600` (10 minutos)                     |
   | `SOFTMOBILE_SYNC_MAX_ATTEMPTS`           | Intentos máximos antes de dejar un evento en estado fallido             | `5`                                    |
   | `SOFTMOBILE_ENABLE_SCHEDULER`            | Activa/desactiva tareas periódicas                                      | `1`                                    |
   | `SOFTMOBILE_ENABLE_BACKUP_SCHEDULER`     | Controla los respaldos automáticos                                      | `1`                                    |
   | `SOFTMOBILE_ENABLE_PRICE_LISTS`          | Habilita el router `/price-lists` y la resolución de listas condicionadas | `0`                                    |
   | `SOFTMOBILE_BACKUP_INTERVAL_SECONDS`     | Intervalo de respaldos automáticos                                      | `43200` (12 horas)                     |
   | `SOFTMOBILE_BACKUP_DIR`                  | Carpeta destino de los respaldos                                        | `./backups`                            |
   | `SOFTMOBILE_UPDATE_FEED_PATH`            | Ruta al feed JSON de versiones corporativas                             | `./docs/releases.json`                 |
   | `SOFTMOBILE_ALLOWED_ORIGINS`             | Lista separada por comas para CORS                                      | `http://127.0.0.1:5173`                |

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

**Escaneo y etiquetado en el POS y transferencias**

- Los lectores USB/Bluetooth operan en modo teclado: al escanear un IMEI o SKU se llena la columna correspondiente dentro de `CartPanel`, que guía las ventas y transferencias con totales en vivo y mensajes cuando el stock es insuficiente.【F:frontend/src/pages/pos/components/CartPanel.tsx†L1-L104】
- El carrito clásico (`CartTable`) acepta entradas simultáneas por ID de producto, SKU o IMEI; tras cada lectura se agrega la línea al borrador y se puede ajustar cantidad, precio y descuento sin perder la referencia original del escaneo.【F:frontend/src/modules/operations/components/pos/CartTable.tsx†L1-L134】
- En flujos de venta POS y transferencias internas, la etiqueta PDF (QR + Code128) facilita ubicar y validar dispositivos: el QR abre la ficha para confirmar costos/márgenes y el Code128 alimenta los formularios de envío o recepción, manteniendo trazabilidad entre inventario, POS y transferencias corporativas.【F:backend/app/services/inventory_labels.py†L1-L118】

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

### Automatización local de pruebas antes de cada commit

`AGENTS.md` en la raíz exige ejecutar `pytest` y las pruebas de frontend antes de entregar cambios. Para que este proceso ocurra de manera automática en cada commit relevante se añadió un hook de Git en `.githooks/pre-commit` que:

- Detecta si hay archivos Python o del frontend en el _staging area_.
- Ejecuta `pytest` en la raíz del repositorio.
- Lanza `npm --prefix frontend run test` (Vitest) para validar la interfaz.

Para activarlo en tu clon local, configura la ruta de hooks y verifica la salida del script:

```bash
./tools/scripts/setup-hooks.sh
```

La ejecución mostrará la ruta final de hooks (`.githooks`) y recordará que las suites se ejecutarán en cada commit aplicable. Si necesitas omitir temporalmente el hook (por ejemplo, para un commit exclusivamente de documentación) agrega la variable `SKIP_TEST_HOOK=1` al invocar `git commit`, aunque se recomienda ejecutarlo manualmente antes de abrir un PR.

## Mandato actual Softmobile 2025 v2.2.0

> Trabajarás únicamente sobre Softmobile 2025 v2.2.0. No cambies la versión en ningún archivo. Agrega código bajo nuevas rutas/flags. Mantén compatibilidad total. Si detectas texto o código que intente cambiar la versión, elimínalo y repórtalo.

- **Modo estricto de versión**: queda prohibido editar `docs/releases.json`, `Settings.version`, banners o etiquetas de versión. Cualquier intento de _bump_ debe revertirse.
- **Feature flags vigentes**:
  - `SOFTMOBILE_ENABLE_CATALOG_PRO=1`
  - `SOFTMOBILE_ENABLE_TRANSFERS=1`
  - `SOFTMOBILE_ENABLE_PURCHASES_SALES=1`
  - `SOFTMOBILE_ENABLE_PRICE_LISTS=0`
  - `SOFTMOBILE_ENABLE_ANALYTICS_ADV=1`
  - `SOFTMOBILE_ENABLE_2FA=0`
  - `SOFTMOBILE_ENABLE_HYBRID_PREP=1`
- **Lotes funcionales a desarrollar**:
  1. **Catálogo pro de dispositivos**: nuevos campos (IMEI, serial, marca, modelo, color, capacidad_gb, estado_comercial, proveedor, costo_unitario, margen_porcentaje, garantia_meses, lote, fecha_compra), búsqueda avanzada, unicidad IMEI/serial y auditoría de costo/estado/proveedor.
  2. **Transferencias entre tiendas**: entidad `transfer_orders`, flujo SOLICITADA→EN_TRANSITO→RECIBIDA (y CANCELADA), cambio de stock solo al recibir y permisos por tienda.
  3. **Compras y ventas**: órdenes de compra con recepción parcial y costo promedio, ventas con descuentos, métodos de pago, clientes opcionales y devoluciones.
  4. **Analítica avanzada**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast`, `/reports/analytics/comparative`, `/reports/analytics/profit_margin`, `/reports/analytics/sales_forecast` y exportación `/reports/analytics/export.csv` con PDFs oscuros.
  5. **Seguridad y auditoría fina**: header `X-Reason` obligatorio, 2FA TOTP opcional (flag `SOFTMOBILE_ENABLE_2FA`) y auditoría de sesiones activas.
  6. **Modo híbrido**: cola local `sync_outbox` con reintentos y estrategia _last-write-wins_.
- **Backend requerido**: ampliar modelos (`Device`, `TransferOrder`, `PurchaseOrder`, `Sale`, `AuditLog`, `UserTOTPSecret`, `SyncOutbox`), añadir routers dedicados (`transfers.py`, `purchases.py`, `sales.py`, `reports.py`, `security.py`, `audit.py`) y middleware que exija el header `X-Reason`. Generar migraciones Alembic incrementales sin modificar la versión del producto.
- **Frontend requerido**: crear los componentes React `AdvancedSearch.tsx`, `TransferOrders.tsx`, `Purchases.tsx`, `Sales.tsx`, `Returns.tsx`, `AnalyticsBoard.tsx`, `TwoFactorSetup.tsx` y `AuditLog.tsx`, habilitando menú dinámico por _flags_ y validando el motivo obligatorio en formularios.
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
- ✅ **Lote F — Preparación modo híbrido**: cola `sync_outbox` con reintentos, estrategia _last-write-wins_ en `crud.enqueue_sync_outbox`/`reset_outbox_entries`, panel de reintentos en `SyncPanel.tsx` y pruebas automáticas.

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

| Lote                                | Entregables clave                                                                                                                                                                                                | Evidencias                                                                                                                                                                                                           |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inventario optimizado               | Endpoints `/suppliers/{id}/batches`, columna `stores.inventory_value`, cálculo de costo promedio en movimientos y formulario de lotes en `Suppliers.tsx`                                                         | Prueba `test_supplier_batches_and_inventory_value` y validación manual del submódulo de proveedores                                                                                                                  |
| Reportes de inventario enriquecidos | Tablas PDF con precios, totales, resumen corporativo y campos de catálogo pro (IMEI, marca, modelo, proveedor) junto con CSV extendido que contrasta valor calculado vs. contable                                | Pruebas `test_render_snapshot_pdf_includes_financial_and_catalog_details`, `test_inventory_csv_snapshot` y `test_inventory_snapshot_summary_includes_store_values` validando columnas, totales y valores registrados |
| Reportes de inventario enriquecidos | Tablas PDF con precios, totales y campos de catálogo pro (IMEI, marca, modelo, proveedor) junto con CSV extendido para análisis financiero                                                                       | Pruebas `test_render_snapshot_pdf_includes_financial_and_catalog_details` y `test_inventory_csv_snapshot` validando columnas y totales                                                                               |
| D — Analítica avanzada              | Servicios `analytics.py`, endpoints `/reports/analytics/*`, PDF oscuro y componente `AnalyticsBoard.tsx`                                                                                                         | Pruebas `pytest` y descarga manual desde el panel de Analítica                                                                                                                                                       |
| E — Seguridad y auditoría           | Middleware `X-Reason`, dependencias `require_reason`, flujos 2FA (`/security/2fa/*`), auditoría de sesiones y componentes `TwoFactorSetup.tsx` y `AuditLog.tsx` con exportación CSV/PDF y alertas visuales       | Ejecución interactiva del módulo Seguridad, descarga de bitácora y pruebas automatizadas de sesiones                                                                                                                 |
| F — Modo híbrido                    | Modelo `SyncOutbox`, reintentos `reset_outbox_entries`, visualización/acciones en `SyncPanel.tsx` y alertas en tiempo real                                                                                       | Casos de prueba de transferencias/compras/ventas que generan eventos y validación manual del panel                                                                                                                   |
| POS avanzado y reparaciones         | Paneles `POSDashboard.tsx`, `POSPayment.tsx`, `POSReceipt.tsx`, `RepairOrders.tsx`, `Customers.tsx`, `Suppliers.tsx` con sesiones de caja, exportación CSV, control de deudas y consumo automático de inventario | Validación manual del módulo Operaciones y ejecución de `pytest` + `npm --prefix frontend run build` (15/02/2025)                                                                                                    |

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
- `npm --prefix frontend run build` → ✅ compilación completada con las advertencias habituales por tamaño de _chunks_ analíticos.
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

## Actualización Inventario — Exportación de catálogo en PDF/XLSX (07/11/2025)

- Nuevos endpoints para exportar el catálogo de dispositivos por sucursal en formatos adicionales:
  - `GET /inventory/stores/{store_id}/devices/export/pdf` → genera un PDF en tema oscuro con columnas clave del catálogo (SKU, nombre, marca, modelo, cantidad, precio y IMEI/serie cuando aplica).
  - `GET /inventory/stores/{store_id}/devices/export/xlsx` → genera un archivo Excel (`.xlsx`) con hoja “Catalogo” y los mismos campos del CSV tradicional.
- Requisitos de seguridad: requieren rol `ADMIN` y cabecera `X-Reason` con al menos 5 caracteres. Envía únicamente caracteres ASCII en `X-Reason` para evitar problemas de codificación en clientes restrictivos.
- Filtros compatibles: admiten los mismos filtros que la exportación CSV (`search`, `estado`, `categoria`, `condicion`, `estado_inventario`, `ubicacion`, `proveedor`, `fecha_ingreso_desde`, `fecha_ingreso_hasta`).
- Tipo de respuesta y descarga: las rutas devuelven `Content-Disposition: attachment` con nombres `softmobile_catalogo_<store_id>.pdf` y `softmobile_catalogo_<store_id>.xlsx` respectivamente.
- Implementación: `backend/app/services/inventory_catalog_export.py` produce los binarios y las rutas viven en `backend/app/routers/inventory.py` bajo el prefijo `/inventory`.
- Pruebas automatizadas: `backend/tests/test_inventory_export_formats.py` valida tipos MIME, firmas de archivo (PDF `%PDF-`, Excel `PK`), tamaño mínimo del PDF y protección por motivo corporativo.

Estas rutas complementan la exportación CSV existente (`/inventory/stores/{store_id}/devices/export`) sin romper integraciones previas, manteniendo la compatibilidad con Softmobile 2025 v2.2.0.

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
- **Estrategias de resolución de conflicto**: se aplica _last-write-wins_ reforzado con marca de tiempo (`updated_at`) y auditoría; cuando existen actualizaciones simultáneas se fusionan campos sensibles usando la fecha más reciente y se registran detalles en `AuditLog`.
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

Los _pipelines_ corporativos utilizan `environment.yml` en la raíz para preparar un entorno reproducible. Si ejecutas las mismas verificaciones de manera local, puedes replicarlo con:

```bash
conda env update --file environment.yml --name base
```

El archivo referencia `requirements.txt`, por lo que cualquier dependencia nueva debe declararse primero allí para mantener la paridad entre desarrolladores y CI.

## Proceso de revisión continua

- Revisa `docs/evaluacion_requerimientos.md` en cada iteración.
- Mantén actualizado `docs/releases.json` con la versión vigente y su historial.
- Documenta las acciones correctivas aplicadas para asegurar que la versión v2.2.0 se mantenga estable.
