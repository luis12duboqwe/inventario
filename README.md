# Softmobile 2025 v2.2

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
    __init__.py
    config.py
    crud.py
    database.py
    main.py
    models.py
    schemas.py
    routers/
      __init__.py
      health.py
      stores.py
  tests/
    conftest.py
    test_health.py
    test_stores.py
README.md
requirements.txt
```

### Backend FastAPI (`backend/app`)
El backend implementa un servicio FastAPI que representa el módulo **Softmobile Central**. Sus componentes principales son:

- **`config.py`**: carga valores de configuración (por ejemplo, URL de la base de datos) desde variables de entorno.
- **`database.py`**: inicializa SQLAlchemy, crea el motor correspondiente (SQLite por defecto) y expone la utilidad `get_db` para inyección de dependencias.
- **`models.py`**: define las tablas `stores` y `devices` con restricciones de unicidad y relaciones.
- **`schemas.py`**: valida solicitudes y respuestas mediante Pydantic.
- **`crud.py`**: encapsula la lógica de acceso a datos y manejo de excepciones.
- **`routers/`**: agrupa los endpoints de salud y gestión de sucursales/dispositivos.
- **`main.py`**: crea la instancia de FastAPI, registra los routers y garantiza la creación automática de tablas en el arranque.

### Pruebas (`backend/tests`)
Las pruebas usan `pytest` y `fastapi.testclient` con una base de datos SQLite en memoria para validar los flujos principales:

- Estado de salud (`/health`).
- Creación y listado de sucursales.
- Manejo de errores para sucursales duplicadas o inexistentes.
- Registro y consulta de dispositivos por sucursal, incluyendo conflictos de SKU.

## Requisitos previos
- Python 3.11+
- Pip con acceso a internet para instalar dependencias

## Instalación del entorno
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Ejecución de la API
```bash
uvicorn backend.app.main:app --reload
```
La aplicación estará disponible en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

## Ejecución de pruebas
```bash
pytest
```
Las pruebas se ejecutan con una base de datos efímera en memoria, por lo que no es necesario ningún paso adicional.

## Próximos pasos sugeridos
- Definir el stack definitivo del frontend (framework, librerías UI, gestor de estado).
- Modelar a detalle la lógica de sincronización entre tiendas y sistema central.
- Incorporar autenticación y autorización basadas en roles.
- Añadir pipelines de CI/CD para pruebas, empaquetado y despliegue.
- Documentar procedimientos de instalación para tiendas y administradores.
