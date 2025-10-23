# Bitácora de validaciones de importación

- 2025-02-20 — Registros revisados: 500 · Advertencias registradas: 18.
- 2025-02-20 — Validación avanzada auditada tras suite de 500 filas; sin incidencias críticas, pendiente cubrir estado comercial inválido.
- 2025-10-23 — Se documenta la habilitación de tokens de refresco, recuperación de contraseña y verificación de correo en `/auth`, con limitación de ritmo vía `fastapi-limiter` y dependencias `fakeredis`/`fastapi-limiter` añadidas a los requirements.
- 2025-10-23 — Se refuerza la suite `backend/tests/test_routes_bootstrap.py` validando `/auth/refresh`, `/auth/forgot`, `/auth/reset` y `POST /auth/verify` para asegurar que los tokens cambien, las contraseñas se actualicen y los usuarios queden verificados.
- 2025-10-23 — Se registra la paginación de `/stores`, el wrapper ligero (`backend/routes/stores.py`), los nuevos esquemas (`backend/schemas/store.py`) y el endpoint `PUT /stores/{id}` del núcleo con su prueba asociada.
