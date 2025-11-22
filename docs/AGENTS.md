# Bitácora de validaciones de importación

- 2025-02-20 — Registros revisados: 500 · Advertencias registradas: 18.
- 2025-02-20 — Validación avanzada auditada tras suite de 500 filas; sin incidencias críticas, pendiente cubrir estado comercial inválido.
- 2025-10-23 — Se documenta la habilitación de tokens de refresco, recuperación de contraseña y verificación de correo en `/auth`, con limitación de ritmo vía `fastapi-limiter` y dependencias `fakeredis`/`fastapi-limiter` añadidas a los requirements.
- 2025-11-20 — Los módulos legacy en `backend/routes/` se archivaron; toda la funcionalidad vive en `backend/app/routers/*` y las pruebas se ajustaron a `/auth/bootstrap`, `/auth/login`, `/auth/token` y `/auth/verify` como única fuente de verdad.
- 2025-10-23 — Se refuerza la suite `backend/tests/test_routes_bootstrap.py` validando `/auth/refresh`, `/auth/forgot`, `/auth/reset` y `POST /auth/verify` para asegurar que los tokens cambien, las contraseñas se actualicen y los usuarios queden verificados.
- 2025-10-23 — Se registra la paginación de `/stores`, el wrapper ligero (`backend/routes/stores.py`), los nuevos esquemas (`backend/schemas/store.py`) y el endpoint `PUT /stores/{id}` del núcleo con su prueba asociada.
- 2025-11-05 — `backend/core/logging.py` activa un modo de compatibilidad basado en `logging` cuando no está instalada la dependencia `loguru`, manteniendo la salida JSON con contexto.
- 2025-11-05 — `backend/routes/auth.py` permite ejecutar las rutas `/auth/*` sin `fastapi-limiter` ni `fakeredis`, registrando solo una advertencia y desactivando el rate limiting para entornos mínimos.
- 2025-11-06 — Se eliminó del repositorio el artefacto `backend/database/softmobile.db`; la base se genera al vuelo durante el arranque para evitar adjuntar binarios en los PR.

## POS Agent (05/11/2025)

- Se habilitan los modelos ligeros `backend/models/pos.py` (`Sale`, `SaleItem`, `Payment`) para registrar ventas con múltiples métodos de pago (`CASH`, `CARD`, `TRANSFER`).
- El router `backend/routes/pos.py` publica `POST /pos/sales`, `POST /pos/sales/{id}/items`, `POST /pos/sales/{id}/checkout`, `POST /pos/sales/{id}/hold`, `POST /pos/sales/{id}/resume`, `POST /pos/sales/{id}/void` y `GET /pos/receipt/{id}`, manteniendo la compatibilidad con `/pos/sale` (núcleo) para recibos PDF.
- El esquema `backend/schemas/pos.py` describe solicitudes y respuestas; la prueba `backend/tests/test_pos_module.py` valida flujos de hold/resume, multipago y anulaciones.
- Los listados corporativos consumidos por POS (inventario, sucursales, reportes) entregan `Page[...]` según `backend/schemas/common.py`; ajusta clientes o SDK para leer `items`, `total`, `page`, `size`.
- 06/11/2025 — Se refuerza `backend/schemas/common.Page` importando `ceil` para el cálculo de páginas y `backend/core/logging.py` declara explícitamente los contextos utilizados por Loguru, evitando fallos de importación cuando se ejecuta el POS ligero en entornos mínimos.
- 06/11/2025 — Se refuerza `backend/schemas/common.Page` importando `ceil` para el cálculo de páginas y `backend/core/logging.py` declara explícitamente los contextos utilizados por Loguru, evitando fallos de importación cuando se ejecuta el POS ligero en entornos mínimos. `backend/routes/pos.py` desfasó los folios del módulo ligero en `+1,000,000`, consulta primero el recibo PDF del núcleo y sólo devuelve el JSON ligero cuando la venta no existe en la base corporativa, de modo que las pruebas históricas continúan recibiendo `application/pdf`.

## Agentes funcionales — 23/10/2025

### Auth Agent

- **Responsabilidad**: mantener la sesión corporativa usando `services/api/http.ts` (interceptores Axios) y `services/api/auth.ts`.
- **Flujos cubiertos**: bootstrap, login, refresco automático vía `/auth/refresh` y notificación `softmobile:unauthorized` para cerrar sesión en todos los módulos.
- **Integraciones**: `frontend/src/app/App.tsx` opera con `useQuery` y `useMutation` de React Query para sincronizar estado y reducir duplicidad de lógica.

### Store Agent

- **Responsabilidad**: encapsular las llamadas a `/stores` dentro de `services/api/stores.ts`, garantizando tipado consistente y cabecera `Bearer` automática.
- **Integraciones**: módulos de Operaciones, Seguridad y Configuración pueden migrar gradualmente consumiendo los helpers sin tocar la lógica heredada.

### POS Agent

- **Responsabilidad**: centralizar ventas, sesiones de caja y recibos (`/pos/sale`, `/pos/sales/*`) desde `services/api/pos.ts`.
- **Integraciones**: respeta la cabecera `X-Reason`, descarga recibos PDF del núcleo cuando existen y normaliza las respuestas para React Query.

### Export Agent

- **Responsabilidad**: agrupar en `services/api/inventory.ts` las exportaciones CSV/PDF/Excel y los movimientos de inventario.
- **Integraciones**: ofrece un punto único de extensión para nuevos reportes, manteniendo compatibilidad con el SDK legado (`frontend/src/api.ts`).

### Frontend Agent

- **Responsabilidad**: documentar y monitorear la reorganización técnica del cliente React.
- **Alcance**: estructura oficial `frontend/src/{app,shared,services/api,features,pages,widgets,modules}` con componentes reutilizables bajo `shared/components/`.
- **Documentación**: `frontend/README.md` describe el uso de React Query y los interceptores Axios; el registro «frontend agent restructured» deja constancia del mantenimiento sin cambios visuales.
