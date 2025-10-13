# Instaladores empresariales Softmobile

Este directorio contiene las plantillas para empaquetar la solución completa en Windows 10/11 siguiendo los lineamientos del plan Softmobile 2025 v2.2.

## Backend (PyInstaller)

1. Crea y activa un entorno virtual con las dependencias del backend instaladas.
2. Ejecuta:

   ```bash
   pyinstaller installers/softmobile_backend.spec
   ```

3. El ejecutable se generará en `dist/softmobile_central/`. Incluye los archivos estáticos de la API y puede registrarse como servicio.

## Instalador final (Inno Setup)

1. Ejecuta `ISCC installers/SoftmobileInstaller.iss` desde una máquina Windows con [Inno Setup](https://jrsoftware.org/isinfo.php) instalado.
2. El script empaqueta:
   - El backend compilado (`dist/softmobile_central`).
   - El frontend generado con `npm run build` (carpeta `frontend/dist`).
   - Los archivos de configuración (`config/`, `backups/`).
3. El instalador crea accesos directos para iniciar el servicio central y la aplicación de tienda (modo navegador) y registra la tarea programada para sincronizaciones si se ejecuta con privilegios de administrador.

Ajusta las rutas según los entornos de despliegue y actualiza la versión en ambos archivos cuando se libere un nuevo build.
