#!/usr/bin/env bash
# // [PACK32-33-OPS] Restauración desde un respaldo generado con backup.sh.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <archivo.sql> [local|docker]" >&2
  exit 1
fi

INPUT=$1
TARGET=${2:-local}
DB_NAME=${DB_NAME:-softmobile}
DB_USER=${DB_USER:-softmobile}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

if [[ ! -f ${INPUT} ]]; then
  echo "El archivo ${INPUT} no existe" >&2
  exit 2
fi

if [[ ${TARGET} == "docker" ]]; then
  echo "Restaurando respaldo en contenedor docker-compose desde ${INPUT}" >&2
  docker compose exec -T db psql -U "${DB_USER}" "${DB_NAME}" < "${INPUT}"
else
  echo "Restaurando respaldo local hacia ${DB_HOST}:${DB_PORT} desde ${INPUT}" >&2
  psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" < "${INPUT}"
fi

echo "Restauración completada" >&2
