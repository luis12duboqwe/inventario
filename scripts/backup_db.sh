#!/usr/bin/env bash
set -euo pipefail
DATE=$(date +%F_%H%M%S)
OUT=${1:-backups}
mkdir -p "$OUT"
sqlite3 backend/app.db ".backup '$OUT/app_${DATE}.db'"
echo "Backup en $OUT/app_${DATE}.db"
