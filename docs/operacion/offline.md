# Operación en modo offline

Este procedimiento describe cómo operar la plataforma cuando hay desconexiones prolongadas, priorizando la continuidad de ventas y movimientos de inventario sin perder eventos en la cola híbrida (`sync_outbox`).

## Preparación antes de quedar sin conexión

1. Ejecuta una sincronización completa para dejar la cola vacía:
   - `POST /sync/run` por cada sucursal activa.
   - Verifica `GET /sync/outbox/stats` y confirma que no haya entradas pendientes o con conflictos.
2. Habilita las banderas híbridas en el entorno (`SOFTMOBILE_ENABLE_PURCHASES_SALES=1`, `SOFTMOBILE_ENABLE_TRANSFERS=1`, `SOFTMOBILE_ENABLE_HYBRID_PREP=1`).
3. Descarga respaldos recientes (catálogo, clientes y configuraciones POS) y confirma impresoras locales.

## Operación durante la desconexión

1. Registra ventas desde `/sales` o `/pos/sale` asegurando la cabecera `X-Reason` (≥5 caracteres).
2. Cualquier movimiento de inventario (ajustes, reparaciones, devoluciones) quedará en `sync_outbox` con prioridad alta; no borres ni modifiques manualmente las filas.
3. Si un intento de envío falla, se marcará como `FAILED` con el error `offline`; no es necesario reintentar manualmente.
4. Mantén un control local de folios entregados y recibos impresos para conciliar al reconectar.

## Reintentos y reconciliación al recuperar la conexión

1. Los reintentos automáticos se activan con `requeue_failed_outbox_entries`, ya sea vía `POST /sync/outbox/retry` (manual) o por el programador (`services/scheduler.py`).
2. Confirma que los eventos se reprogramaron:
   - `GET /sync/outbox` debe mostrar las entradas en estado `PENDING` y `attempt_count` en `0`.
   - Si alguna sigue fallando, revisa `error_message` y la marca de tiempo `last_attempt_at` para validar el intervalo configurado.
3. Ejecuta `POST /sync/run` por cada sucursal hasta que la cola quede vacía y el historial (`GET /sync/history`) muestre sesiones **exitosas**.
4. Valida que los inventarios y la contabilidad de ventas coincidan con los folios locales; registra cualquier ajuste con motivo corporativo (`X-Reason`).

## Checklist rápido

- [ ] Sincronización previa completada y cola limpia.
- [ ] Banderas híbridas activadas en el entorno.
- [ ] Operaciones registradas con `X-Reason` y recibos locales guardados.
- [ ] Reintentos automáticos confirmados (`attempt_count=0`, estado `PENDING`).
- [ ] Sincronización posterior ejecutada por sucursal y discrepancias resueltas.
