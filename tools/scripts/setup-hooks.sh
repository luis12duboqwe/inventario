#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

git config core.hooksPath .githooks

CONFIGURED_PATH="$(git config core.hooksPath)"
echo "Ruta de hooks configurada en: $CONFIGURED_PATH"
echo "El hook pre-commit ejecutará pytest y Vitest en commits relevantes."
