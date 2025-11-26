# Guía de entorno — Softmobile 2025 v2.2.0

Este documento describe cómo preparar, configurar y validar los ambientes de desarrollo y pruebas para Softmobile 2025 v2.2.0. Todo el contenido se mantiene en español conforme a las políticas corporativas.

## Requisitos locales

Instala las siguientes dependencias antes de ejecutar el proyecto:

- **Python 3.11** con `pip` actualizado.
- **Node.js 18 LTS** (incluye `npm`).
- **Redis 7** para el control de rate limiting (`fastapi-limiter`).
- Herramientas opcionales: `make`, `docker` y `docker compose` para flujos automatizados.

Se recomienda crear entornos virtuales con `venv` o `conda` para aislar dependencias.

## Variables de entorno críticas

El backend utiliza `backend/app/config.py` para validar los siguientes valores (todos deben declararse en `.env` o en el entorno del contenedor):

| Variable | Descripción |
| --- | --- |
| `DATABASE_URL` | Cadena de conexión a SQLite o PostgreSQL. Para desarrollo se usa `sqlite:///softmobile.db`. |
| `JWT_SECRET_KEY` | Clave secreta para firmar tokens JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Minutos de vigencia del token de acceso. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Días de vigencia del token de refresco. |
| `SESSION_COOKIE_EXPIRE_MINUTES` | Duración de la sesión web. |
| `CORS_ORIGINS` | Lista separada por comas con los orígenes permitidos. |
| `SOFTMOBILE_LAN_DISCOVERY_ENABLED` | Habilita o deshabilita el endpoint público de descubrimiento LAN. |
| `SOFTMOBILE_LAN_HOST` | IP o hostname anunciado a los terminales LAN (por defecto se detecta automáticamente). |
| `SOFTMOBILE_LAN_PORT` | Puerto anunciado para la API en LAN (por defecto `8000`). |
| `SOFTMOBILE_ENABLE_*` | Flags de funcionalidad (catalog pro, transfers, purchases_sales, analytics_adv, hybrid_prep, 2FA). |
| `REDIS_URL` | Cadena de conexión a Redis utilizada por `fastapi-limiter`. |

### Ejemplo de `.env`

```env
DATABASE_URL=sqlite:///softmobile.db
JWT_SECRET_KEY=softmobile-dev-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14
SESSION_COOKIE_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173
SOFTMOBILE_ENABLE_CATALOG_PRO=1
SOFTMOBILE_ENABLE_TRANSFERS=1
SOFTMOBILE_ENABLE_PURCHASES_SALES=1
SOFTMOBILE_ENABLE_ANALYTICS_ADV=1
SOFTMOBILE_ENABLE_2FA=0
SOFTMOBILE_ENABLE_HYBRID_PREP=1
REDIS_URL=redis://localhost:6379/0
```

### Configuración LAN rápida

Cuando el backend se ejecuta en un servidor LAN y varias terminales deben
conectarse con la IP local, define las siguientes variables:

```env
SOFTMOBILE_LAN_DISCOVERY_ENABLED=1
SOFTMOBILE_LAN_HOST=192.168.0.10
SOFTMOBILE_LAN_PORT=8000
DATABASE_URL=sqlite:////data/softmobile.db  # o postgresql://softmobile:softmobile@192.168.0.10/softmobile
CORS_ORIGINS=["http://192.168.0.10:5173","http://192.168.0.10:8000"]
```

Luego expón el frontend con `npm run dev -- --host 0.0.0.0 --port 5173` y usa el
asistente LAN del frontend para fijar automáticamente la `API_BASE_URL` en cada
terminal.

## Puesta en marcha con Docker

Con Docker instalado ejecuta:

```bash
docker compose up --build
```

El servicio backend se expone en `http://localhost:8000` y el frontend en `http://localhost:5173`. El archivo `docker-compose.yml` monta volúmenes persistentes para la base SQLite (`softmobile-data`) y el cache de Node (`frontend-node-modules`).

### Volúmenes y rutas relevantes

- `/data/softmobile.db`: persistencia de la base de datos local.
- `/app/backend/logs`: registro estructurado del backend.
- `/app/frontend/node_modules`: cache de dependencias para acelerar rebuilds.

## Ejecución manual sin contenedores

1. **Backend**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev -- --host 0.0.0.0 --port 5173
   ```

3. **Redis (opcional)**
   ```bash
   docker run --rm -p 6379:6379 redis:7-alpine
   ```

## Pruebas obligatorias

Desde la raíz ejecuta:

```bash
pytest
npm --prefix frontend run test -- --runInBand
npm --prefix frontend run build
```

Las suites cubren inventario avanzado, sincronización híbrida, POS, reportes PDF y módulos de seguridad/2FA. Cualquier cambio funcional debe dejar estas suites en verde.

## Mantenimiento de entornos

- Regenera el archivo `.env` ante rotación de claves.
- Utiliza `alembic upgrade head` para aplicar migraciones pendientes.
- Limpia caches con `rm -rf backend/.pytest_cache frontend/node_modules/.vite` si detectas estados inconsistentes.
- Ejecuta `npm run lint` en el frontend cuando modifiques componentes React críticos (dashboard, POS, sincronización).

Mantén los `feature flags` alineados al mandato Softmobile 2025 v2.2.0 y evita cambiar textos de versión o banners.
