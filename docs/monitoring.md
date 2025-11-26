# Monitoreo y logging corporativo

## Registro estructurado

- El módulo `backend/core/logging.py` inicializa Loguru en modo JSON mediante `setup_logging()`,
  inyectando contexto dinámico (`request_id`, `user_id`, `path`, `latency`) con los helpers
  `bind_context`, `update_context` y `reset_context`.
- Cuando la dependencia `loguru` no está disponible, el modo de compatibilidad activa un logger
  estándar (`logging`) con formateo JSON (`_JsonFormatter`) para mantener la misma estructura y
  evitar pérdidas de información en integraciones SIEM.
- Todo middleware HTTP (`backend/main.py`) agrega `X-Request-ID` a la respuesta y registra
  `request.completed` con latencia, garantizando trazabilidad entre servicios.

## Métricas Prometheus

- El endpoint `GET /monitoring/metrics` (router `backend/app/routers/monitoring.py`) expone todas las
  métricas registradas en `backend/app/telemetry.py` usando el `CollectorRegistry` dedicado.
- Es necesario autenticarse como administradora y conservar la cabecera `Authorization` vigente.
- La respuesta se entrega con `Content-Type: text/plain; version=0.0.4` y cabecera
  `Content-Disposition: inline; filename=metrics.prom`, apta para scrapers Prometheus y servicios
  externos (Grafana Agent, VictoriaMetrics, etc.).
- Se recomienda deshabilitar el cache en los balanceadores externos; el propio endpoint devuelve
  `Cache-Control: no-store` para evitar datos obsoletos.

### Ejemplo de integración

```bash
curl -H "Authorization: Bearer <TOKEN_ADMIN>" \
     https://inventario.softmobile.local/monitoring/metrics \
     -o metrics.prom
```

> **Nota:** si se ejecuta detrás de Prometheus, utilice un `scrape_config` con `bearer_token_file`
> o un `authorization` header estático que contenga el token de servicio generado por Softmobile.

## Validaciones automatizadas

- `backend/tests/test_logging.py` asegura que los logs incluyan el contexto dinámico tanto en modo
  Loguru como en el formateador de compatibilidad.
- `backend/tests/test_system_logs.py` y `backend/tests/test_system_logs_rotation.py` mantienen la
  cobertura sobre filtros de auditoría, rotación y exportación de bitácoras corporativas.
