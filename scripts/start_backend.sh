#!/usr/bin/env bash
# Script de conveniencia para iniciar el backend FastAPI de Softmobile 2025 v2.2.0
# Crea/actualiza el entorno virtual, instala dependencias, ejecuta migraciones
# y levanta Uvicorn con recarga automática para desarrollo local.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$ROOT_DIR/.venv"
REQUIREMENTS_ROOT="$ROOT_DIR/requirements.txt"
REQUIREMENTS_BACKEND="$ROOT_DIR/backend/requirements.txt"
HASH_MARKER="$VENV_PATH/.softmobile_backend.hash"
API_HOST="${SOFTMOBILE_API_HOST:-0.0.0.0}"
API_PORT="${SOFTMOBILE_API_PORT:-8000}"
UVICORN_APP="${SOFTMOBILE_UVICORN_APP:-backend.app.main:app}"

if command -v tput >/dev/null 2>&1; then
  GREEN="$(tput setaf 2)"
  CYAN="$(tput setaf 6)"
  RESET="$(tput sgr0)"
else
  GREEN=""
  CYAN=""
  RESET=""
fi

log() {
  printf '%s[%s]%s %s\n' "$CYAN" "softmobile" "$RESET" "$1"
}

die() {
  printf '%s[%s]%s %s\n' "$(tput setaf 1 2>/dev/null || true)" "error" "$RESET" "$1" >&2
  exit 1
}

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    die "Python 3 no está instalado en el PATH."
  fi
}

create_venv() {
  if [[ ! -d "$VENV_PATH" ]]; then
    log "Creando entorno virtual en .venv"
    "$PYTHON_BIN" -m venv "$VENV_PATH"
  fi
}

activate_venv() {
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
}

requirements_hash() {
  local data=""
  for file in "$REQUIREMENTS_ROOT" "$REQUIREMENTS_BACKEND"; do
    if [[ -f "$file" ]]; then
      data+="$(cat "$file")"
    fi
  done
  printf '%s' "$data" | sha1sum | awk '{print $1}'
}

install_dependencies() {
  local current_hash
  current_hash="$(requirements_hash)"
  if [[ ! -f "$HASH_MARKER" || "$(cat "$HASH_MARKER")" != "$current_hash" ]]; then
    log "Instalando dependencias del backend"
    pip install --upgrade pip >/dev/null
    pip install -r "$REQUIREMENTS_ROOT"
    if [[ -f "$REQUIREMENTS_BACKEND" ]]; then
      pip install -r "$REQUIREMENTS_BACKEND"
    fi
    printf '%s' "$current_hash" >"$HASH_MARKER"
  else
    log "Dependencias del backend al día"
  fi
}

load_dotenv() {
  local dotenv_file="$ROOT_DIR/.env"
  if [[ -f "$dotenv_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$dotenv_file"
    set +a
    log "Variables de entorno cargadas desde .env"
  fi
}

run_migrations() {
  if [[ "${SOFTMOBILE_SKIP_MIGRATIONS:-0}" == "1" ]]; then
    log "Omitiendo migraciones (SOFTMOBILE_SKIP_MIGRATIONS=1)"
    return
  fi
  log "Ejecutando migraciones Alembic"
  (cd "$ROOT_DIR/backend" && alembic upgrade head)
}

start_uvicorn() {
  log "Levantando Uvicorn en ${API_HOST}:${API_PORT}"
  exec "$VENV_PATH/bin/python" -m uvicorn "$UVICORN_APP" \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --reload
}

ensure_python
create_venv
activate_venv
install_dependencies
load_dotenv
run_migrations
start_uvicorn
