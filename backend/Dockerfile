# syntax=docker/dockerfile:1
# // [PACK32-33-OPS] Imagen de FastAPI para la bitácora y módulos existentes.
# Multi-stage build optimizado para producción

# Etapa 1: Builder - instala dependencias y prepara el entorno
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Instala dependencias de compilación necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependencias de Python
COPY requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2: Runtime - imagen final ligera
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Crea usuario no-root para mayor seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copia las dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copia solo el código de aplicación necesario
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser fastapi_limiter /app/fastapi_limiter

# Cambia al usuario no-root
USER appuser

# Expone el puerto de la aplicación
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
