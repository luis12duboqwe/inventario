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
- `bootstrap_central_replica.sh`: descarga un volcado desde la base central (requiere `CENTRAL_DB_HOST` y `CENTRAL_DB_USER`), lo restaura en la base local y dispara la primera sincronización incremental (`POST /api/v1/sync/run`) salvo que se indique `SKIP_INCREMENTAL=1`.
- `daily_encrypted_backup.sh`: genera un respaldo diario cifrado con AES-256, borra el SQL plano y lo envía por `scp` al host central definido. Requiere `BACKUP_PASSPHRASE` y las variables `CENTRAL_BACKUP_HOST`/`CENTRAL_BACKUP_USER` cuando `SKIP_UPLOAD` es `0`.

Ambos scripts respetan `set -euo pipefail` para abortar en caso de error y deben ejecutarse con un usuario que tenga permisos de lectura/escritura sobre los archivos de respaldo.

### Programación recomendada

- **Replica inicial**: ejecutar `ops/bootstrap_central_replica.sh` antes de habilitar un nodo nuevo. Ejemplo:
  ```bash
  CENTRAL_DB_HOST=db-central.corp.local CENTRAL_DB_USER=replicador \
  CENTRAL_DB_PASSWORD="secreto" LOCAL_DB_NAME=softmobile \
  SYNC_API_URL="https://nodo.local/api/v1" SYNC_TOKEN="<jwt>" \
  bash ops/bootstrap_central_replica.sh
  ```
- **Backup diario cifrado** (cron a las 02:00):
  ```cron
  0 2 * * * BACKUP_PASSPHRASE="clave-larga" CENTRAL_BACKUP_HOST=central.corp.local \
  CENTRAL_BACKUP_USER=backup TARGET=docker \
  /opt/softmobile/ops/daily_encrypted_backup.sh >> /var/log/softmobile/backup.log 2>&1
  ```
  Ajusta `TARGET` a `docker` si la base vive en docker-compose y define `CENTRAL_BACKUP_PATH` cuando el destino no sea la carpeta por defecto `~/softmobile_backups`.

## Buenas prácticas

1. Guardar los respaldos en almacenamiento cifrado y con retención mínima de 30 días.
2. Registrar cada ejecución en la bitácora interna indicando motivo y resultado.
3. Validar mensualmente una restauración completa en un entorno aislado.
4. Monitorizar espacio libre en el directorio configurado en `settings.backup_directory`.

