# Migraciones de base de datos (Softmobile 2025 v2.2.0)

Softmobile 2025 utiliza Alembic para mantener la estructura de la base de datos sincronizada entre ambientes.

## Ruta oficial

- `backend/alembic/` contiene el entorno configurado y las migraciones versionadas (`versions/*.py`).
- Cada archivo sigue el prefijo `YYYYMMDDHHMM_<descripcion>.py` para conservar el orden cronológico y la trazabilidad de los cambios.
- El archivo `backend/alembic.ini` apunta por defecto a `sqlite:///backend/database/softmobile.db` cuando no se especifica otra cadena de conexión.

## Ejecución

1. Crea el entorno virtual e instala las dependencias del backend (`pip install -r requirements.txt`).
2. Exporta la variable `DATABASE_URL` si deseas utilizar un motor distinto al definido en `.env`.
3. Ejecuta `alembic upgrade head` desde la carpeta `backend/` para aplicar todas las migraciones pendientes.
4. Para generar una nueva migración usa `alembic revision --autogenerate -m "descripcion"` y revisa manualmente los cambios antes de hacer commit.

> Las migraciones deben ser idempotentes: al aplicarse sobre una base actualizada no deben fallar ni alterar datos existentes.

## Integración con las pruebas

- Las suites de `pytest` trabajan sobre un motor SQLite en memoria y crean las tablas con `Base.metadata.create_all` únicamente para los escenarios de prueba.
- Antes de correr pruebas end-to-end con archivos reales, ejecuta `alembic upgrade head` para asegurarte de que la base persistente coincida con la versión publicada.

## Buenas prácticas

- Incluye un registro en `CHANGELOG.md` cada vez que agregues una migración relevante.
- Evita editar migraciones ya publicadas; genera una nueva revisión para cualquier ajuste.
- Acompaña las migraciones con pruebas que cubran los nuevos campos o relaciones para evitar regresiones.
