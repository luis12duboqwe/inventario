# Respaldo cifrado y recuperación segura

## Cobertura

- **Backups cifrados en origen**: los artefactos PDF/JSON/SQL/configuración y los archivos críticos se cifran con Fernet antes de empaquetarse en el ZIP de respaldo. El servidor descifra automáticamente al descargar/restaurar sin requerir conexión a internet.
- **Llave dedicada sin dependencia externa**: la llave simétrica se almacena en `SOFTMOBILE_BACKUP_ENCRYPTION_KEY_PATH` (predeterminado `backups/.backup.key`) con permisos `0600`. Se genera de forma local si no existe.
- **Tokens sensibles**: los tokens de sesión y recuperación de contraseña se guardan como HMAC-SHA256 (`sha256:<digest>`) derivado de `SECRET_KEY`, evitando exponer valores en texto plano.

## Procedimiento de restauración segura

1. Confirmar que la llave de cifrado está presente y legible por el proceso de aplicación:
   ```bash
   export SOFTMOBILE_BACKUP_ENCRYPTION_KEY_PATH="/ruta/segura/backup.key"
   stat "$SOFTMOBILE_BACKUP_ENCRYPTION_KEY_PATH"
   ```
2. Invocar `POST /backups/{id}/restore` con los componentes requeridos (`database`, `configuration`, `critical_files`). El servicio descifra cada archivo en memoria antes de escribirlo en el destino solicitado.
3. Para inspección manual sin servidor, se puede descifrar un archivo puntual (ej. SQL) ejecutando dentro del entorno de la app:
   ```python
   from pathlib import Path
   from backend.app.services.backups import read_backup_file

   sql_bytes = read_backup_file(Path("./backups/softmobile_respaldo_*.sql"))
   Path("/tmp/restauracion.sql").write_bytes(sql_bytes)
   ```
4. Completar la restauración revisando `logs_sistema` para confirmar la auditoría de la operación.

## Rotación de llaves y continuidad

- Regenerar la llave sólo tras exportar o re-encriptar los respaldos existentes. Para rotar:
  1. Exportar los archivos descifrados con la llave actual (`read_backup_file`).
  2. Mover la llave vieja a un almacén seguro de contingencia.
  3. Eliminar `SOFTMOBILE_BACKUP_ENCRYPTION_KEY_PATH` y reiniciar el servicio para generar una nueva.
  4. Volver a crear los respaldos con la llave fresca y documentar la fecha de rotación.
- Mantén la llave fuera de repositorios y copia de forma segura en bóvedas offline.

## Compatibilidad y pruebas

- Las pruebas `backend/tests/test_backups.py` validan que los archivos almacenados no sean legibles en texto plano y que `read_backup_file` devuelva el contenido descifrado.
- La ruta `/backups/{id}/download` sirve archivos descifrados en memoria, preservando compatibilidad con clientes existentes.
