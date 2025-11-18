#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

git config --global --add safe.directory "$(pwd)" >/dev/null 2>&1 || true

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f backend/requirements.txt ]; then
  echo "Instalando dependencias de backend/requirements.txt"
  python -m pip install -r backend/requirements.txt
else
  echo "Aviso: backend/requirements.txt no encontrado, se omitirá (se intentará instalar requirements.txt de la raíz)."
fi

if [ -f requirements.txt ]; then
  echo "Instalando dependencias de requirements.txt (raíz)"
  python -m pip install -r requirements.txt
else
  echo "Aviso: requirements.txt no encontrado en la raíz. Si faltan dependencias, instálelas manualmente."
fi
python -m pip install pytest==8.1.1

deactivate

npm ci --prefix frontend
