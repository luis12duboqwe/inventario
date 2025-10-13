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
    api/
    core/
    db/
    models/
    schemas/
    services/
  tests/
README.md
```

### Backend (`backend/`)
El directorio `backend/` contiene una API inicial basada en **FastAPI** y **SQLAlchemy** que funciona como punto de partida para el módulo Softmobile Central. Incluye:

- Modelos de datos para tiendas (`Store`) y dispositivos (`Device`).
- Servicios de dominio para registrar y consultar sucursales y equipos.
- Endpoints versionados (`/api/v1`) con operaciones CRUD básicas para tiendas y dispositivos.
- Pruebas automatizadas con Pytest utilizando una base de datos temporal en memoria.

## Configuración rápida del backend
1. Crear un entorno virtual e instalar dependencias:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Ejecutar las pruebas automatizadas:
   ```bash
   pytest
   ```
3. Iniciar la API en modo desarrollo:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Revisar la documentación interactiva en `http://127.0.0.1:8000/docs`.

La API utiliza SQLite por defecto (`softmobile.db`). El archivo se genera automáticamente al ejecutar la aplicación. Para entornos más avanzados se recomienda configurar PostgreSQL ajustando la variable de entorno `SOFTMOBILE_SQLITE_DB_FILE` o extendiendo la configuración.

## Flujo de trabajo
1. Cada tienda registra productos y movimientos de inventario.
2. El sistema sincroniza automáticamente la información con la base central cada 30 minutos.
3. Softmobile Central compila los datos para generar reportes globales.
4. Administradores revisan, aprueban y exportan la información consolidada.

## Módulos funcionales previstos
- **Inventario**: gestión, búsqueda y reportes locales.
- **Central**: sincronización y control global de sucursales.
- **Seguridad**: usuarios, permisos y logs de auditoría.
- **Instalación**: creación automática de carpetas, bases de datos y accesos directos.
- **Actualización**: verificación y despliegue de nuevas versiones.

## Requisitos técnicos sugeridos
- **Sistema operativo**: Windows 10/11 (64 bits).
- **Lenguajes**: Python para backend; JavaScript/HTML5 para la interfaz.
- **Librerías**: ReportLab, PyInstaller, SQLite3, Flask o FastAPI.
- **Bases de datos**: SQLite para instalaciones locales y PostgreSQL para el sistema central.
- **Instalador**: Inno Setup Compiler.

## Etapas de desarrollo
1. Diseño y estructura de carpetas (completado con este andamiaje inicial).
2. Construcción de la interfaz visual y módulos base.
3. Implementación de sincronización y logs automáticos.
4. Desarrollo del módulo central con dashboard global.
5. Pruebas, empaquetado y generación de instaladores (.exe).

## Lineamientos de diseño
La interfaz debe mantener un estilo tecnológico con tema oscuro: fondos gris oscuro, acentos azul cian y textos en blanco o gris claro. Se prioriza la limpieza visual, la organización y la facilidad de navegación.

## Próximos pasos sugeridos
- Definir el stack definitivo del frontend (framework, librerías UI, gestor de estado).
- Modelar a detalle la lógica de sincronización entre tiendas y sistema central.
- Incorporar autenticación y autorización basadas en roles.
- Añadir pipelines de CI/CD para pruebas, empaquetado y despliegue.
- Documentar procedimientos de instalación para tiendas y administradores.
