#!/usr/bin/env bash
set -euo pipefail
SRC=${1:?Uso: restore_db.sh <ruta_al_backup>}
cp -f "$SRC" backend/app.db
echo "Restaurado desde $SRC"
