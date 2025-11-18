# Notas de Instalación - Softmobile 2025 v2.2.0

## Resolución de Problemas de Módulos Faltantes

### Problema Original
Al intentar ejecutar la aplicación con `python -m uvicorn backend.app.main:app`, se encontraban los siguientes errores:
- `ModuleNotFoundError: No module named 'uvicorn'`
- `ModuleNotFoundError: No module named 'fastapi'`
- `ModuleNotFoundError: No module named 'sqlalchemy'`
- `ModuleNotFoundError: No module named 'pydantic_settings'`

### Solución
Todos los módulos requeridos ya estaban listados correctamente en `requirements.txt`. El problema era que no estaban instalados en el entorno de ejecución.

**Pasos realizados:**
1. Instalación de todas las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Corrección de compatibilidad con pydantic-settings v2.11.0:
   - **Problema**: pydantic-settings v2.11.0 intenta parsear campos `list[str]` como JSON automáticamente antes de ejecutar validadores, lo que causaba un error al intentar parsear strings simples separados por comas.
   - **Solución**: Modificado `backend/app/config.py` para:
     - Cambiar `allowed_origins` de `list[str]` a una estructura de dos campos
     - `allowed_origins_str`: campo `str` que recibe el valor del entorno
     - `allowed_origins`: campo `list[str]` calculado que se puebla en un `model_validator`
     - El validator soporta tanto JSON arrays (retrocompatibilidad) como CSV (formato actual)

### Módulos Instalados
```
fastapi==0.115.0
fastapi-limiter==0.1.6
uvicorn[standard]==0.38.0
sqlalchemy==2.0.34
pydantic==2.12.3
pydantic-settings==2.11.0
httpx==0.27.2
passlib[bcrypt]==1.7.4
bcrypt==5.0.0
python-jose[cryptography]==3.3.0
pyjwt==2.10.1
python-multipart==0.0.9
email-validator==2.3.0
fakeredis==2.32.0
loguru==0.7.2
reportlab==4.1.0
openpyxl==3.1.5
apscheduler==3.11.1
alembic==1.17.1
packaging==25.0
pyotp==2.9.0
prometheus-client==0.23.1
```

### Verificación
Para verificar que todos los módulos están instalados correctamente:

```bash
python3 << 'EOF'
import fastapi
import uvicorn
import sqlalchemy
import pydantic_settings
print("✓ Todos los módulos importados exitosamente")
print(f"FastAPI: {fastapi.__version__}")
print(f"Uvicorn: {uvicorn.__version__}")
print(f"SQLAlchemy: {sqlalchemy.__version__}")
EOF
```

Para verificar que la aplicación FastAPI se puede cargar:

```bash
python3 -c "from backend.app.main import app; print(f'✓ App cargada: {app.title} v{app.version}')"
```

### Archivos de Configuración
La aplicación espera un archivo `.env` en dos ubicaciones:
- `/home/runner/work/inventario/inventario/.env` - para `backend/app/config.py`
- `/home/runner/work/inventario/inventario/backend/.env` - para `backend/database/__init__.py`

Ambos archivos deben contener las mismas variables de entorno (se puede usar una copia del mismo archivo).

Variables requeridas mínimas:
```bash
DATABASE_URL=sqlite:///backend/database/softmobile.db
JWT_SECRET_KEY=dev_change_me
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Ejecutar la Aplicación
```bash
# Desde el directorio raíz del proyecto
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Notas Técnicas

#### Compatibilidad con pydantic-settings v2
La versión 2.x de pydantic-settings cambió el comportamiento de parsing para campos complejos (list, dict), intentando parsearlos como JSON automáticamente. Esto rompió la compatibilidad con la configuración existente que usaba strings CSV simples.

El cambio implementado mantiene la API pública (el campo `allowed_origins` sigue siendo `list[str]`) pero cambia la implementación interna para trabajar alrededor de esta limitación de pydantic-settings.

**Alternativas consideradas:**
1. Downgrade a pydantic-settings <2.6 - Descartado por problemas de red y para mantener versiones actualizadas
2. Cambiar el formato en `.env` a JSON - Descartado para mantener simplicidad de configuración
3. Usar Annotated con BeforeValidator - No funcionó porque pydantic-settings parsea antes del validator
4. Solución implementada: Campo intermedio string con parsing en model_validator ✓

Esta solución mantiene:
- ✓ Retrocompatibilidad con formato CSV actual
- ✓ Compatibilidad con formato JSON (usado en algunos scripts)
- ✓ API pública sin cambios (`settings.allowed_origins` sigue siendo `list[str]`)
- ✓ Sin dependencias adicionales
