@echo off
REM Creado por Codex el 2025-10-20
SETLOCAL ENABLEDELAYEDEXPANSION
PUSHD %~dp0\..
IF NOT EXIST backend\.venv (
    python -m venv backend\.venv
)
CALL backend\.venv\Scripts\activate.bat
pip install --upgrade pip >NUL
pip install -r backend\requirements.txt
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
POPD
ENDLOCAL
