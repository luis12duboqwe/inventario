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
    domain.py
    http.py
    main.py
  tests/
README.md
```

### Backend minimalista (`backend/app`)
Para poder ejecutar pruebas en entornos sin conexión a internet ni dependencias externas, el backend incluye:

- **Capa HTTP mínima** (`http.py`): expone una pequeña infraestructura de ruteo y un `TestClient` compatible con Pytest sin requerir FastAPI.
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
