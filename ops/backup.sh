#!/usr/bin/env bash
# // [PACK32-33-OPS] Script de respaldo para la base Postgres.
set -euo pipefail

TARGET=${1:-local}
OUTPUT=${2:-"backup_$(date +%Y%m%d_%H%M%S).sql"}
DB_NAME=${DB_NAME:-softmobile}
DB_USER=${DB_USER:-softmobile}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

if [[ ${TARGET} == "docker" ]]; then
  echo "Generando respaldo desde contenedor docker-compose en ${OUTPUT}" >&2
  docker compose exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" > "${OUTPUT}"
else
  echo "Generando respaldo local desde ${DB_HOST}:${DB_PORT} en ${OUTPUT}" >&2
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" > "${OUTPUT}"
fi

echo "Respaldo guardado en ${OUTPUT}" >&2
