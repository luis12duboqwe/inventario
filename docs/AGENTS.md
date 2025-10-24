# Bitácora de validaciones de importación

- 2025-02-20 — Registros revisados: 500 · Advertencias registradas: 18.
- 2025-02-20 — Validación avanzada auditada tras suite de 500 filas; sin incidencias críticas, pendiente cubrir estado comercial inválido.
- 2025-10-23 — Se documenta la habilitación de tokens de refresco, recuperación de contraseña y verificación de correo en `/auth`, con limitación de ritmo vía `fastapi-limiter` y dependencias `fakeredis`/`fastapi-limiter` añadidas a los requirements.
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

## Agentes funcionales — 23/10/2025

### Auth Agent
- Orquesta el flujo de autenticación en el frontend mediante `services/api/http.ts` y `services/api/auth.ts`, usando Axios con refresco automático de tokens y propagando el evento `softmobile:unauthorized` para cerrar sesión de forma segura.
- `App.tsx` consume `useQuery`/`useMutation` para bootstrap/login manteniendo la compatibilidad con la UI existente y reduciendo código duplicado.

### Store Agent
- Expone accesos tipados a `/stores` y dispositivos por sucursal desde `services/api/stores.ts`, reutilizando el cliente HTTP con cabecera `Bearer` automática.
- Permite que módulos como usuarios y operaciones migren gradualmente a la nueva capa sin reescribir lógica heredada.

### POS Agent
- Reexporta la capa POS desde `services/api/pos.ts`, centralizando ventas, sesiones de caja y descargas de recibos en un único módulo especializado.
- Facilita la adopción de interceptores Axios y mantiene los requerimientos de motivo corporativo (`X-Reason`).

### Export Agent
- `services/api/inventory.ts` concentra las funciones de exportación (CSV/PDF/Excel) y movimientos de inventario, evitando duplicidad de rutas y asegurando la estandarización de respuestas.
- Sirve como punto de extensión para incorporar nuevos reportes sin tocar `frontend/src/api.ts` legado.

### Frontend Agent
- Documenta la reorganización de `frontend/src/` (carpetas `app/`, `shared/`, `services/api/`, `features/`, `pages/`, `widgets/`) y preserva el diseño actual sin cambios visuales.
- `frontend/README.md` actúa como guía operativa para el equipo, describiendo la capa de servicios y el uso de React Query.
- Registro: «frontend agent restructured» deja constancia de la reubicación de componentes en `frontend/src/shared/components/` y de la adopción de React Query para autenticación.
