# Procedimientos de respaldo y restauración

Esta guía describe cómo operar los servicios corporativos de respaldos en Softmobile 2025 v2.2.0.

## API de respaldos

- **Generar respaldo**: `POST /backups/run`.
  - Requiere cabecera `X-Reason` (mínimo 5 caracteres) y rol `ADMIN`.
  - El cuerpo admite `nota` y el conjunto opcional `componentes` (`database`, `configuration`, `critical_files`).
  - El servicio guarda los archivos en `settings.backup_directory` e incorpora la nota, el motivo y el usuario que disparó el respaldo dentro del archivo de metadatos (`*.meta.json`).
- **Historial**: `GET /backups/history` lista los respaldos con tamaño total, componentes y notas.
- **Restaurar**: `POST /backups/{id}/restore` permite escoger componentes, definir un directorio destino y decidir si aplicar el SQL sobre la base activa.
- **Descargas**: `GET /backups/{id}/download?formato={zip|sql|json}` devuelve el artefacto solicitado.

## Contenido del metadato (`*.meta.json`)

Cada respaldo escribe un JSON con la siguiente estructura:

- `timestamp`: marca UTC de generación.
- `mode`: `manual` o `automatico`.
- `notes`: nota libre ingresada en la petición.
- `reason`: motivo recibido vía `X-Reason`.
- `triggered_by_id`: identificador del usuario que ejecutó el respaldo.
- `total_size_bytes`: tamaño total considerando archivos y directorios críticos.
- `components`: lista ordenada de componentes incluidos.
- `files`: rutas absolutas a PDF, JSON, SQL, ZIP, configuración y carpeta de críticos.
- `critical_files`: lista relativa de archivos sensibles copiados.

## Scripts operativos

En `ops/` se incluyen utilidades shell:

- `backup.sh`: ejecuta `pg_dump` contra la base Postgres ya sea en `docker compose` (`TARGET=docker`) o local. Variables principales: `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`.
- `restore.sh`: restaura un archivo SQL generado por `pg_dump` contra la base definida.

Ambos scripts respetan `set -euo pipefail` para abortar en caso de error y deben ejecutarse con un usuario que tenga permisos de lectura/escritura sobre los archivos de respaldo.

## Buenas prácticas

1. Guardar los respaldos en almacenamiento cifrado y con retención mínima de 30 días.
2. Registrar cada ejecución en la bitácora interna indicando motivo y resultado.
3. Validar mensualmente una restauración completa en un entorno aislado.
4. Monitorizar espacio libre en el directorio configurado en `settings.backup_directory`.

