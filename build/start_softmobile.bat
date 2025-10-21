@echo off
:: Creado por Codex el 2025-10-20 para iniciar Softmobile 2025 v2.2.0 en Windows.
setlocal enabledelayedexpansion
set ROOT_DIR=%~dp0
set BACKEND_DIR=%ROOT_DIR%\backend
set FRONTEND_DIR=%ROOT_DIR%\frontend

if exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
    call "%BACKEND_DIR%\venv\Scripts\activate.bat"
)

echo [Softmobile] Arrancando backend en uvicorn...
start "Softmobile Backend" cmd /c "cd /d %BACKEND_DIR% && uvicorn main:app --host 127.0.0.1 --port 8000"

echo [Softmobile] Arrancando frontend (npm run dev)...
start "Softmobile Frontend" cmd /c "cd /d %FRONTEND_DIR% && npm run dev"

echo Softmobile 2025 v2.2.0 iniciado. Cierre esta ventana para finalizar las sesiones.
endlocal
