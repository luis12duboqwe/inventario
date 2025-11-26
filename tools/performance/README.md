# Pruebas de carga para Softmobile POS (v2.2.0)

Esta carpeta contiene artefactos listos para simular escenarios pico sobre el POS sin romper la compatibilidad de la versión.

## Locust

1. Instala las dependencias de rendimiento (`pip install -r requirements.txt`).
2. Exporta las variables de entorno para apuntar al entorno objetivo:
   - `SOFTMOBILE_API_BASE`: URL base del backend (por defecto `http://localhost:8000`).
   - `SOFTMOBILE_TOKEN`: token `Bearer` para el usuario de pruebas.
   - `SOFTMOBILE_STORE_ID`: identificador de sucursal a usar en las peticiones.
   - `SOFTMOBILE_SESSION_ID` y `SOFTMOBILE_DEVICE_ID`: opcionales para calentar recibos y borradores.
   - `SOFTMOBILE_REASON`: motivo corporativo a enviar en `X-Reason`.
3. Ejecuta Locust desde la raíz del repo:

   ```bash
   locust -f tools/performance/locustfile.py --headless -u 25 -r 5 -t 5m
   ```

Los escenarios incluyen recuperación de sesiones POS, historial paginado, borradores ligeros y encolado de exportes asincrónicos.

## JMeter

1. Abre `tools/performance/jmeter_pos_peak.jmx` en JMeter 5.6+.
2. Ajusta las variables del plan (host, puerto, token, `store_id` y motivo).
3. Lanza el plan con 20 usuarios, ramp-up de 10 segundos y 5 iteraciones por hilo para verificar que los endpoints paginados y de recuperación mantengan la latencia bajo carga.

Las cabeceras `Authorization` y `X-Reason` vienen preconfiguradas en el Header Manager para cumplir con los requisitos de auditoría.
