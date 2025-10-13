# Instrucciones para agentes

1. **Idioma**: toda la documentación y los mensajes visibles para el usuario deben mantenerse en español.
2. **Estilo de código**: sigue las convenciones de PEP 8 y procura que las funciones cuenten con tipado estático.
3. **Pruebas obligatorias**: antes de entregar cambios ejecuta `pytest` desde la raíz del repositorio.
4. **Dependencias**: agrega nuevas librerías a `requirements.txt` y documenta su uso en el `README.md` cuando sean necesarias.
5. **Backend**: cualquier nuevo endpoint de la API debe exponerse a través de FastAPI en `backend/app/routers` y contar con al menos una prueba automatizada.
6. **Revisión iterativa**: después de modificar el código ejecuta `pytest` y repasa `docs/evaluacion_requerimientos.md`; si encuentras brechas con el plan Softmobile 2025 v2.2 corrige y repite el proceso hasta cumplirlo por completo.
7. **Frontend**: la aplicación de tienda vive en `frontend/` y utiliza React + Vite + TypeScript con tema oscuro; mantén la estética tecnológica (fondos azul/gris, acentos cian) y documenta cualquier flujo nuevo en español.
8. **Finalización completa**: cada vez que leas este archivo o el `README.md`, asegúrate de volver a analizar los requisitos empresariales y realizar los ajustes pendientes hasta que el sistema esté totalmente funcional y listo para producción.
9. **Actualizaciones**: mantén el feed `docs/releases.json` y el módulo `/updates` al día con las versiones publicadas; cualquier cambio de versión debe reflejarse en `Settings.version`, documentación y pruebas.
10. **Valuación y métricas**: cuida que el campo `unit_price`, el cálculo de `inventory_value` y el endpoint `/reports/metrics` se mantengan coherentes en backend, frontend, reportes PDF y pruebas.
