#!/usr/bin/env bash
# // [BACKUP-OPS] Respaldo diario cifrado y envío a central.
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-backups/daily}
DB_NAME=${DB_NAME:-softmobile}
DB_USER=${DB_USER:-softmobile}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
TARGET=${TARGET:-local}

BACKUP_PASSPHRASE=${BACKUP_PASSPHRASE:-}
CENTRAL_BACKUP_HOST=${CENTRAL_BACKUP_HOST:-}
CENTRAL_BACKUP_USER=${CENTRAL_BACKUP_USER:-}
CENTRAL_BACKUP_PATH=${CENTRAL_BACKUP_PATH:-~/softmobile_backups}
SKIP_UPLOAD=${SKIP_UPLOAD:-0}

if [[ -z ${BACKUP_PASSPHRASE} ]]; then
  echo "BACKUP_PASSPHRASE es obligatorio para cifrar el respaldo." >&2
  exit 2
fi

mkdir -p "${BACKUP_DIR}" || true
STAMP=$(date +%Y%m%d_%H%M%S)
BASENAME="softmobile_diario_${STAMP}"
SQL_PATH="${BACKUP_DIR}/${BASENAME}.sql"
ENC_PATH="${SQL_PATH}.enc"
SUM_PATH="${ENC_PATH}.sha256"

if [[ ${TARGET} == "docker" ]]; then
  echo "Generando respaldo cifrado desde contenedor docker-compose (${SQL_PATH})." >&2
  docker compose exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" > "${SQL_PATH}"
else
  echo "Generando respaldo cifrado local desde ${DB_HOST}:${DB_PORT} (${SQL_PATH})." >&2
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" > "${SQL_PATH}"
fi

echo "Cifrando respaldo con AES-256." >&2
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt \
  -pass env:BACKUP_PASSPHRASE \
  -in "${SQL_PATH}" -out "${ENC_PATH}"

sha256sum "${ENC_PATH}" > "${SUM_PATH}"
rm -f "${SQL_PATH}"

echo "Respaldo cifrado listo en ${ENC_PATH}." >&2

if [[ ${SKIP_UPLOAD} -eq 1 ]]; then
  echo "Envío a central omitido por configuración (SKIP_UPLOAD=1)." >&2
  exit 0
fi

if [[ -z ${CENTRAL_BACKUP_HOST} || -z ${CENTRAL_BACKUP_USER} ]]; then
  echo "CENTRAL_BACKUP_HOST y CENTRAL_BACKUP_USER son obligatorios para el envío." >&2
  exit 3
fi

echo "Enviando respaldo a ${CENTRAL_BACKUP_USER}@${CENTRAL_BACKUP_HOST}:${CENTRAL_BACKUP_PATH}" >&2
scp "${ENC_PATH}" "${SUM_PATH}" "${CENTRAL_BACKUP_USER}@${CENTRAL_BACKUP_HOST}:${CENTRAL_BACKUP_PATH}/"

echo "Respaldo diario cifrado enviado con éxito." >&2
