# Restauración completa y simulacros

Guía para restaurar Softmobile 2025 v2.2.0 desde respaldos cifrados y para ejecutar simulacros controlados que validen la continuidad operativa.

## Requisitos previos

- Llave o frase de cifrado utilizada en los respaldos (`BACKUP_PASSPHRASE`).
- Acceso al archivo cifrado (`*.sql.enc`) y a su checksum (`*.sha256`).
- Servicios detenidos: `docker compose down` o apagado del servicio FastAPI/worker.
- Herramientas instaladas: `openssl`, `pg_restore`, `psql` y conectividad hacia la base destino.

## Restauración completa

1. **Verificar integridad del respaldo**
   ```bash
   sha256sum -c backups/daily/softmobile_diario_YYYYMMDD_hhmmss.sql.enc.sha256
   ```
2. **Descifrar el SQL** usando la misma passphrase:
   ```bash
   BACKUP_PASSPHRASE="<clave>" \
   openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
     -in backups/daily/softmobile_diario_YYYYMMDD_hhmmss.sql.enc \
     -out /tmp/restauracion.sql
   ```
3. **Restaurar la base** con el script estándar:
   ```bash
   DB_HOST=localhost DB_USER=softmobile DB_NAME=softmobile \
   bash ops/restore.sh /tmp/restauracion.sql
   ```
4. **Aplicar migraciones y validar sincronización**:
   ```bash
   alembic upgrade head
   curl -X POST "https://nodo.local/api/v1/sync/run" \
     -H "Authorization: Bearer <token>" \
     -H "X-Reason: Restauración completa" \
     -H "Content-Type: application/json" \
     -d '{"mode": "hybrid"}'
   ```
5. **Arrancar servicios** (`docker compose up -d`) y monitorear `/sync/overview` hasta ver porcentaje ≥95 %.

## Simulacros trimestrales

1. **Preparación**
   - Copiar el último respaldo cifrado y la llave a un entorno aislado.
   - Definir el motivo corporativo de prueba (`X-Reason`) y usuario responsable.
2. **Ejecución**
   - Restaurar siguiendo los pasos anteriores en la base de pruebas.
   - Registrar resultados en la bitácora (`ops/runbook.md`) incluyendo tiempos de recuperación y errores.
   - Ejecutar `pytest -k backup` y `pytest -k sync_full` para validar integridad.
3. **Cierre**
   - Documentar hallazgos y mejoras pendientes.
   - Rotar llaves si se detectan accesos no autorizados o fugas.

## Replica inicial con sincronización incremental

Para levantar un nodo nuevo alineado con la central:

1. Exporta la base central con `ops/bootstrap_central_replica.sh` usando `CENTRAL_DB_HOST`, `CENTRAL_DB_USER` y credenciales seguras.
2. Permite que el script dispare la primera sincronización incremental (`POST /api/v1/sync/run`) o ejecuta el endpoint manualmente con un token de servicio.
3. Confirma en `/sync/overview` que el backlog pendiente sea menor a 250 eventos antes de abrir el nodo a usuarios finales.
