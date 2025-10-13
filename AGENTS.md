# Instrucciones para agentes

1. **Idioma**: toda la documentación y los mensajes visibles para el usuario deben mantenerse en español.
2. **Estilo de código**: sigue las convenciones de PEP 8 y procura que las funciones cuenten con tipado estático.
3. **Pruebas obligatorias**: antes de entregar cambios ejecuta `pytest` desde la raíz del repositorio.
4. **Dependencias**: agrega nuevas librerías a `requirements.txt` y documenta su uso en el `README.md` cuando sean necesarias.
5. **Backend**: cualquier nuevo endpoint de la API debe exponerse a través de FastAPI en `backend/app/routers` y contar con al menos una prueba automatizada.
