#!/usr/bin/env bash
# Script de conveniencia para iniciar el frontend React (Vite) de Softmobile 2025 v2.2.0
# Verifica dependencias, sincroniza variables de entorno y ejecuta `npm run dev`.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOCK_FILE="$FRONTEND_DIR/package-lock.json"
HASH_MARKER="$FRONTEND_DIR/.softmobile_frontend.hash"
DEV_HOST="${SOFTMOBILE_UI_HOST:-0.0.0.0}"
DEV_PORT="${SOFTMOBILE_UI_PORT:-5173}"

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

ensure_node() {
  if ! command -v npm >/dev/null 2>&1; then
    die "npm no está instalado en el PATH."
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

install_dependencies() {
  local current_hash
  if [[ ! -f "$LOCK_FILE" ]]; then
    die "No se encontró package-lock.json; ejecuta npm install manualmente."
  fi
  current_hash="$(sha1sum "$LOCK_FILE" | awk '{print $1}')"
  if [[ ! -d "$FRONTEND_DIR/node_modules" || ! -f "$HASH_MARKER" || "$(cat "$HASH_MARKER")" != "$current_hash" ]]; then
    log "Instalando dependencias del frontend"
    (cd "$FRONTEND_DIR" && npm install)
    printf '%s' "$current_hash" >"$HASH_MARKER"
  else
    log "Dependencias del frontend al día"
  fi
}

start_vite() {
  log "Iniciando frontend en ${DEV_HOST}:${DEV_PORT}"
  cd "$FRONTEND_DIR"
  exec npm run dev -- --host "$DEV_HOST" --port "$DEV_PORT"
}

ensure_node
load_dotenv
install_dependencies
start_vite
