# Softmobile 2025 v2.2

Plataforma empresarial para la gestión centralizada de inventarios, sincronización entre sucursales y control operativo integral de cadenas de tiendas con experiencia visual moderna de tema oscuro.

## Arquitectura general

Softmobile 2025 se compone de dos módulos cooperantes:

1. **Softmobile Inventario (frontend)**: cliente React + Vite pensado para ejecutarse en cada tienda. Permite registrar movimientos, disparar sincronizaciones, generar respaldos manuales y descargar reportes PDF con un diseño oscuro y acentos cian.
2. **Softmobile Central (backend)**: API FastAPI que consolida catálogos, controla la seguridad, genera reportes, coordina sincronizaciones automáticas/manuales y ejecuta respaldos programados.

La versión v2.2 trabaja en modo local (sin nube) pero está preparada para empaquetarse en instaladores Windows y evolucionar a despliegues híbridos.

## Capacidades implementadas

- **API empresarial FastAPI** con modelos SQLAlchemy para tiendas, dispositivos, movimientos, usuarios, roles, sesiones de sincronización, bitácoras y respaldos.
- **Seguridad por roles** con autenticación JWT, alta inicial segura (`/auth/bootstrap`), administración de usuarios y auditoría completa.
- **Gestión de inventario** con movimientos de entrada/salida/ajuste, actualización de dispositivos y reportes consolidados por tienda.
- **Sincronización programada y bajo demanda** mediante un orquestador asincrónico que ejecuta tareas periódicas configurables.
- **Respaldos empresariales** con generación automática/manual de PDF y archivos comprimidos JSON usando ReportLab; historial consultable vía API.
- **Frontend oscuro moderno** para el módulo de tienda, construido con React + TypeScript, compatible con escritorio y tablet.
- **Instaladores corporativos**: plantilla PyInstaller para el backend y script Inno Setup que empaqueta ambos módulos y crea accesos directos.
- **Pruebas automatizadas** (`pytest`) que validan flujo completo de autenticación, inventario, sincronización y respaldos.

## Estructura del repositorio

```
backend/
  app/
    config.py
    crud.py
    database.py
    main.py
    models.py
    schemas.py
    security.py
    services/
      backups.py
      scheduler.py
    routers/
      __init__.py
      auth.py
      backups.py
      health.py
      inventory.py
      reports.py
      stores.py
      sync.py
      users.py
  tests/
    conftest.py
    test_backups.py
    test_health.py
    test_stores.py
frontend/
  index.html
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
installers/
  README.md
  SoftmobileInstaller.iss
  softmobile_backend.spec
docs/
  evaluacion_requerimientos.md
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
   source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate
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

4. **Ejecución**

   ```bash
   uvicorn backend.app.main:app --reload
   ```

   La documentación interactiva estará disponible en `http://127.0.0.1:8000/docs`.

5. **Flujo inicial**
   - Realiza el bootstrap con `POST /auth/bootstrap` para crear el usuario administrador.
   - Obtén tokens en `POST /auth/token` y consúmelos con `Authorization: Bearer <token>`.
   - Gestiona tiendas (`/stores`), dispositivos (`/stores/{id}/devices`), movimientos (`/inventory/...`) y reportes (`/reports/*`).

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
   - Panel de operaciones para seleccionar sucursales, visualizar inventarios y registrar movimientos.
   - Botones para sincronización manual, generación de respaldos y descarga de reporte PDF.
   - Historial de respaldos y métricas de stock en tiempo real.

## Reportes y respaldos

- **Descarga PDF**: `GET /reports/inventory/pdf` genera un reporte en tema oscuro con el inventario consolidado (también accesible desde el frontend).
- **Respaldos manuales**: `POST /backups/run` crea un PDF y un ZIP con la instantánea del inventario; devuelve la ruta y tamaño generado.
- **Respaldos automáticos**: el orquestador (`services/scheduler.py`) ejecuta respaldos cada `SOFTMOBILE_BACKUP_INTERVAL_SECONDS` y registra el historial en la tabla `backup_jobs`.

## Instaladores corporativos

- **Backend**: usa `installers/softmobile_backend.spec` con PyInstaller para empaquetar la API como ejecutable.
- **Instalador final**: ejecuta `installers/SoftmobileInstaller.iss` con Inno Setup para distribuir backend + frontend + configuración en un instalador `.exe`. Consulta `installers/README.md` para pasos detallados.

## Pruebas automatizadas

```bash
pytest
```

Las pruebas levantan una base SQLite en memoria, deshabilitan las tareas periódicas y cubren autenticación, inventario, sincronización y respaldos.

## Proceso de revisión continua

1. Tras **cada** cambio ejecuta `pytest` y revisa `docs/evaluacion_requerimientos.md`.
2. Si detectas brechas respecto al plan Softmobile 2025 v2.2, corrige el código y repite la evaluación.
3. Mantén este ciclo iterativo hasta que el sistema esté plenamente funcional y listo para despliegue productivo. Estas instrucciones también están en `AGENTS.md` para que ningún colaborador omita la revisión.
Sistema integral para la gestión centralizada de inventarios y control operativo en múltiples tiendas o puntos de venta.

## Resumen general
Softmobile 2025 v2.2 unifica el seguimiento de inventario, sincronización entre sucursales y generación de reportes dentro de una plataforma moderna, rápida y segura. El sistema puede instalarse de forma local y está preparado para evolucionar hacia despliegues en la nube.

## Arquitectura funcional
El sistema se divide en dos módulos principales:

1. **Softmobile Inventario**: aplicación local para cada tienda donde se gestionan entradas, salidas, precios y reportes.
2. **Softmobile Central**: plataforma maestra que consolida la información de todas las tiendas en una base de datos central.

La comunicación entre módulos se realiza mediante sincronizaciones programadas cada 30 minutos y sincronizaciones manuales opcionales. La versión v2.2 contempla conexiones locales con posibilidad de migrar a la nube en iteraciones futuras.

## Objetivos clave
- Administrar inventarios de varias tiendas desde un punto centralizado.
- Ejecutar sincronizaciones automáticas cada 30 minutos y bajo demanda manual.
- Proteger la información mediante controles de acceso y registros de auditoría.
- Entregar una interfaz moderna de tema oscuro con experiencia fluida.
- Facilitar instalaciones locales y futuras opciones de infraestructura en la nube.
- Automatizar reportes y respaldos de información.

## Estructura del repositorio
```
backend/
  app/
    domain.py
    http.py
    main.py
  tests/
README.md
```

### Backend minimalista (`backend/app`)
Para poder ejecutar pruebas en entornos sin conexión a internet ni dependencias externas, el backend incluye:

- **Capa HTTP mínima** (`http.py`): expone una pequeña infraestructura de ruteo y un `TestClient` compatible con Pytest sin requerir FastAPI, con soporte para respuestas estándar 404/405 y la cabecera `Allow` cuando corresponde.
- **Dominio in-memory** (`domain.py`): modelos de tiendas y dispositivos gestionados con estructuras en memoria, reglas de negocio para unicidad y validaciones básicas.
- **Aplicación principal** (`main.py`): define rutas versionadas (`/api/v1`) para operaciones de salud, tiendas y dispositivos reutilizando la capa mínima.

Este andamiaje permite validar la lógica central en entornos offline. Cuando se disponga de dependencias externas se puede reemplazar por una implementación completa en FastAPI/SQLAlchemy manteniendo las mismas reglas de negocio.

### Pruebas (`backend/tests`)
Las pruebas ejercitan los endpoints simulados mediante el `TestClient` propio. Cubren casos positivos y negativos para tiendas y dispositivos, asegurando que los códigos de estado y mensajes de error se mantengan estables.

## Ejecución de pruebas
```
cd backend
pytest
```
Las pruebas no requieren instalación adicional porque toda la lógica depende exclusivamente de la biblioteca estándar de Python.

## Flujo de trabajo funcional
1. Cada tienda registra productos y movimientos de inventario en su instalación local.
2. El sistema sincroniza automáticamente la información con la base central cada 30 minutos.
3. Softmobile Central compila los datos para generar reportes globales.
4. Administradores revisan, aprueban y exportan la información consolidada.

## Módulos previstos
- **Inventario**: gestión, búsqueda y reportes locales.
- **Central**: sincronización y control global de sucursales.
- **Seguridad**: usuarios, permisos y logs de auditoría.
- **Instalación**: creación automática de carpetas, bases de datos y accesos directos.
- **Actualización**: verificación y despliegue de nuevas versiones.

## Requisitos técnicos sugeridos
- **Sistema operativo**: Windows 10/11 (64 bits).
- **Lenguajes**: Python para backend; JavaScript/HTML5 para la interfaz.
- **Librerías futuras**: ReportLab, PyInstaller, SQLite3, framework web (FastAPI, Flask u otro) según disponibilidad del entorno.
- **Bases de datos**: SQLite para instalaciones locales y PostgreSQL para el sistema central.
- **Instalador**: Inno Setup Compiler.

## Próximos pasos sugeridos
- Definir el stack definitivo del frontend (framework, librerías UI, gestor de estado).
- Modelar a detalle la lógica de sincronización entre tiendas y sistema central.
- Incorporar autenticación y autorización basadas en roles.
- Añadir pipelines de CI/CD para pruebas, empaquetado y despliegue.
- Documentar procedimientos de instalación para tiendas y administradores.
