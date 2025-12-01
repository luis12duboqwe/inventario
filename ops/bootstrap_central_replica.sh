#!/usr/bin/env bash
# // [SYNC-OPS] Replica base central y ejecuta sincronización incremental inicial.
set -euo pipefail

CENTRAL_DB_HOST=${CENTRAL_DB_HOST:-}
CENTRAL_DB_PORT=${CENTRAL_DB_PORT:-5432}
CENTRAL_DB_USER=${CENTRAL_DB_USER:-}
CENTRAL_DB_NAME=${CENTRAL_DB_NAME:-softmobile}
CENTRAL_DB_SSLMODE=${CENTRAL_DB_SSLMODE:-prefer}
CENTRAL_DB_PASSWORD=${CENTRAL_DB_PASSWORD:-${CENTRAL_DB_PASS:-${PGPASSWORD:-}}}

LOCAL_DB_HOST=${LOCAL_DB_HOST:-localhost}
LOCAL_DB_PORT=${LOCAL_DB_PORT:-5432}
LOCAL_DB_USER=${LOCAL_DB_USER:-softmobile}
LOCAL_DB_NAME=${LOCAL_DB_NAME:-softmobile}
LOCAL_DB_PASSWORD=${LOCAL_DB_PASSWORD:-${LOCAL_DB_PASS:-${PGPASSWORD:-}}}

BASE_DIR=${BASE_DIR:-backups/central_seed}
SYNC_API_URL=${SYNC_API_URL:-}
SYNC_TOKEN=${SYNC_TOKEN:-}
SYNC_REASON=${SYNC_REASON:-"Sincronización inicial posterior a replicación"}
SKIP_INCREMENTAL=${SKIP_INCREMENTAL:-0}

if [[ -z ${CENTRAL_DB_HOST} || -z ${CENTRAL_DB_USER} ]]; then
  echo "CENTRAL_DB_HOST y CENTRAL_DB_USER son obligatorios." >&2
  exit 2
fi

mkdir -p "${BASE_DIR}" || true
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_PATH="${BASE_DIR}/central_base_${TIMESTAMP}.dump"

echo "Descargando base central ${CENTRAL_DB_NAME}@${CENTRAL_DB_HOST}:${CENTRAL_DB_PORT} -> ${DUMP_PATH}" >&2
export PGPASSWORD="${CENTRAL_DB_PASSWORD}"
pg_dump --format=custom --no-owner --no-privileges \
  -h "${CENTRAL_DB_HOST}" -p "${CENTRAL_DB_PORT}" -U "${CENTRAL_DB_USER}" \
  "${CENTRAL_DB_NAME}" > "${DUMP_PATH}"
unset PGPASSWORD

echo "Restaurando en base local ${LOCAL_DB_NAME}@${LOCAL_DB_HOST}:${LOCAL_DB_PORT}" >&2
export PGPASSWORD="${LOCAL_DB_PASSWORD}"
pg_restore --clean --if-exists --no-owner --no-privileges \
  -h "${LOCAL_DB_HOST}" -p "${LOCAL_DB_PORT}" -U "${LOCAL_DB_USER}" \
  -d "${LOCAL_DB_NAME}" "${DUMP_PATH}"
unset PGPASSWORD

echo "Replica base cargada. Archivo: ${DUMP_PATH}" >&2

if [[ ${SKIP_INCREMENTAL} -eq 1 ]]; then
  echo "Sincronización incremental omitida por configuración (SKIP_INCREMENTAL=1)." >&2
  exit 0
fi

if [[ -z ${SYNC_API_URL} || -z ${SYNC_TOKEN} ]]; then
  echo "Define SYNC_API_URL y SYNC_TOKEN para disparar la sincronización incremental inicial." >&2
  exit 3
fi

SYNC_ENDPOINT="${SYNC_API_URL%/}/api/v1/sync/run"

echo "Ejecutando sincronización incremental inicial en ${SYNC_ENDPOINT}" >&2
curl -fsSL -X POST "${SYNC_ENDPOINT}" \
  -H "Authorization: Bearer ${SYNC_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Reason: ${SYNC_REASON}" \
  -d '{"mode": "hybrid"}'

