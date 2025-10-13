# Softmobile 2025 v2.2

Sistema empresarial para la gestión centralizada de inventarios, sincronización de sucursales y control operativo integral de cadenas de tiendas.

## Arquitectura general

Softmobile 2025 se compone de dos módulos cooperantes:

1. **Softmobile Inventario**: aplicación local por tienda responsable de capturar movimientos (entradas, salidas y ajustes) y preparar paquetes de sincronización.
2. **Softmobile Central**: servicio FastAPI que consolida catálogos, controla la seguridad, genera reportes y coordina la sincronización automática/manual.

La versión v2.2 trabaja en modo local (sin nube) pero incorpora un plan de expansión futura hacia despliegues híbridos.

## Capacidades implementadas

- **API empresarial FastAPI** con esquemas Pydantic y modelos SQLAlchemy para tiendas, dispositivos, movimientos, usuarios, roles, sesiones de sincronización y bitácoras de auditoría.
- **Seguridad por roles** con autenticación JWT, alta inicial segura (`/auth/bootstrap`), creación y administración de usuarios, y protección granular de endpoints.
- **Gestión de inventario** con movimientos de entrada/salida/ajuste, actualización de dispositivos y reportes consolidados por tienda.
- **Sincronización** automática (intervalo configurable) y manual por sucursal, registrando cada sesión en la base central.
- **Auditoría** con bitácoras consultables (`/reports/audit`) que documentan altas, cambios y sincronizaciones.
- **Pruebas automatizadas** que validan el flujo completo desde el alta del administrador hasta la ejecución de reportes.

## Estructura del repositorio

```
backend/
  __init__.py
  alembic.ini
  app/
    __init__.py
    config.py
    crud.py
    database.py
    main.py
    models.py
    schemas.py
    security.py
    services/
      sync.py
    routers/
      __init__.py
      auth.py
      health.py
      inventory.py
      reports.py
      stores.py
      sync.py
      users.py
  tests/
    conftest.py
    test_health.py
    test_stores.py
docs/
  evaluacion_requerimientos.md
AGENTS.md
README.md
requirements.txt
```

## Configuración

1. **Requisitos previos**
   - Python 3.11+
   - Pip con salida a internet para instalar dependencias

2. **Instalación de dependencias**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

3. **Variables de entorno relevantes**

   | Variable | Descripción | Valor por defecto |
   | --- | --- | --- |
   | `SOFTMOBILE_DATABASE_URL` | Cadena de conexión SQLAlchemy | `sqlite:///./softmobile.db` |
   | `SOFTMOBILE_SECRET_KEY` | Clave usada para firmar JWT | `softmobile-super-secreto-cambia-esto` |
   | `SOFTMOBILE_TOKEN_MINUTES` | Minutos de vigencia de los tokens | `60` |
   | `SOFTMOBILE_SYNC_INTERVAL_SECONDS` | Intervalo de sincronización automática | `1800` (30 minutos) |
   | `SOFTMOBILE_ENABLE_SCHEDULER` | Habilita (1) o deshabilita (0) el planificador | `1` |

   Ajusta estos valores antes de ejecutar la aplicación en entornos productivos.

## Puesta en marcha

1. **Arrancar la API**

   ```bash
   uvicorn backend.app.main:app --reload
   ```

   La documentación interactiva estará disponible en `http://127.0.0.1:8000/docs`.

2. **Alta inicial (bootstrap)**

   El primer usuario debe crearse vía `POST /auth/bootstrap`. Este paso asigna el rol `admin` automáticamente y bloquea futuros bootstraps.

   ```json
   {
     "username": "admin",
     "password": "Cambiar123!",
     "full_name": "Administración General",
     "roles": ["admin"]
   }
   ```

3. **Autenticación**

   Usa `POST /auth/token` (OAuth2 Password) para obtener un token JWT. Inclúyelo en cada petición protegida mediante `Authorization: Bearer <token>`.

4. **Gestión de usuarios y roles**

   - `POST /users`: crear nuevos usuarios (solo administradores).
   - `PUT /users/{id}/roles`: reasignar roles.
   - Roles disponibles iniciales: `admin`, `manager`, `auditor` (pueden ampliarse según necesidades).

5. **Inventario y dispositivos**

   - `POST /stores` crea sucursales (admin/manager).
   - `POST /stores/{id}/devices` registra dispositivos.
   - `PATCH /inventory/stores/{id}/devices/{device_id}` actualiza atributos.
   - `POST /inventory/stores/{id}/movements` registra entradas, salidas o ajustes de stock.
   - `GET /inventory/summary` consolida el inventario por tienda.

6. **Sincronización y reportes**

   - El servicio ejecuta sincronizaciones automáticas según `SOFTMOBILE_SYNC_INTERVAL_SECONDS`.
   - `POST /sync/run` dispara sincronizaciones manuales por tienda.
   - `GET /sync/sessions` lista el historial de sincronizaciones.
   - `GET /reports/audit` consulta la bitácora de auditoría.

## Pruebas automatizadas

```bash
pytest
```

Las pruebas se ejecutan con SQLite en memoria, desactivan el planificador de sincronización y cubren el flujo completo del backend.

## Proceso de revisión continua

1. Tras cada modificación ejecuta `pytest` y revisa `docs/evaluacion_requerimientos.md` para confirmar que el sistema sigue cumpliendo el plan Softmobile 2025 v2.2.
2. Si se detectan brechas, corrige inmediatamente el código, actualiza la documentación y vuelve a repetir el análisis.
3. Mantén este ciclo iterativo hasta que todas las funcionalidades empresariales estén completas y verificadas.

Estas instrucciones también se encuentran en `AGENTS.md` para asegurar que cualquier colaborador repita la evaluación constantemente.
