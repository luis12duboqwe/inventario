# Manual rápido de arranque local — Softmobile 2025 v2.2.0

Este manual explica cómo levantar la plataforma completa reutilizando los scripts de conveniencia `scripts/start_backend.sh` y `scripts/start_frontend.sh`. Todos los comandos deben ejecutarse desde la raíz del repositorio y **sin** modificar la versión corporativa v2.2.0.

## 1. Prerrequisitos

- Python 3.11+ disponible en el `PATH` (`python3 -V`).
- Node.js 20+ y npm instalados (`npm -v`).
- (Opcional) Docker si utilizarás `docker compose up` para servicios auxiliares.
- Archivo `.env` en la raíz con las variables obligatorias (`SECRET_KEY`, `SOFTMOBILE_ENABLE_*`, `SOFTMOBILE_API_PREFIX`, etc.).

## 2. Script `scripts/start_backend.sh`

Ejecuta `./scripts/start_backend.sh` para iniciar la API FastAPI con recarga automática. El script realiza lo siguiente:

1. Crea `.venv` si no existe y activa el entorno virtual.
2. Instala/actualiza dependencias cuando cambian `requirements.txt` o `backend/requirements.txt`.
3. Carga automáticamente las variables definidas en `.env`.
4. Corre `alembic upgrade head` (omitible con `SOFTMOBILE_SKIP_MIGRATIONS=1`).
5. Lanza `uvicorn backend.app.main:app` en `0.0.0.0:8000` (configurable).

Variables relevantes:

- `SOFTMOBILE_API_HOST` → host de Uvicorn (por defecto `0.0.0.0`).
- `SOFTMOBILE_API_PORT` → puerto de la API (por defecto `8000`).
- `SOFTMOBILE_UVICORN_APP` → ruta del módulo Uvicorn (`backend.app.main:app`).
- `SOFTMOBILE_SKIP_MIGRATIONS=1` → salta la ejecución de Alembic (solo si ya migraste manualmente).

## 3. Script `scripts/start_frontend.sh`

Ejecuta `./scripts/start_frontend.sh` en otra terminal. El script:

1. Carga `.env` para reutilizar `VITE_*` o `SOFTMOBILE_*` que necesites en el entorno de desarrollo.
2. Valida la instalación de npm y sincroniza dependencias si cambia `package-lock.json`.
3. Corre `npm run dev` sobre `frontend/` en `0.0.0.0:5173` (configurable).

Variables relevantes:

- `SOFTMOBILE_UI_HOST` → host de Vite (`0.0.0.0` por defecto).
- `SOFTMOBILE_UI_PORT` → puerto del frontend (`5173` por defecto).
- Define `VITE_API_BASE_URL` en `.env` o directamente en la terminal si necesitas apuntar a otro backend (`export VITE_API_BASE_URL=http://127.0.0.1:8000`).

## 4. Flujo sugerido tras iniciar ambos servicios

1. Accede a `http://localhost:5173` y usa las credenciales creadas vía `POST /auth/bootstrap` para ingresar.
2. Verifica Inventario, Operaciones, Analítica, Seguridad y Sincronización manteniendo el motivo corporativo `X-Reason` en toda acción sensible.
3. Al terminar, registra los resultados en la bitácora correspondiente (`docs/bitacora_pruebas_YYYY-MM-DD.md`) junto con los comandos ejecutados (`pytest`, `npm run build`, `npm run test`).

## 5. Resolución rápida de problemas

| Síntoma                                                 | Acción sugerida                                                                                                                     |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| El script de backend falla por falta de dependencias    | Ejecuta `rm -rf .venv` y vuelve a correr `./scripts/start_backend.sh` para reinstalar.                                              |
| Migraciones lentas o innecesarias en entornos efímeros  | Exporta `SOFTMOBILE_SKIP_MIGRATIONS=1` solo si sabes que la base ya está al día.                                                    |
| `npm run dev` no detecta cambios de `package-lock.json` | Borra `frontend/.softmobile_frontend.hash` para forzar reinstalación.                                                               |
| El frontend no contacta la API                          | Asegúrate de que `VITE_API_BASE_URL` apunte al backend correcto y que `SOFTMOBILE_API_PORT`/`SOFTMOBILE_UI_PORT` no estén ocupados. |

Con estos scripts podrás replicar rápidamente el entorno local y validar la funcionalidad completa cuando lo necesites.
