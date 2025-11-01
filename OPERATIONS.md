# Manual operativo — Softmobile 2025 v2.2.0

Este manual resume las tareas diarias, procedimientos de contingencia y métricas clave para operar Softmobile 2025 v2.2.0 en ambientes productivos o preproductivos.

## Checklist diario

1. **Revisión de sincronización híbrida**
   - Consultar `/sync/overview` desde el tablero. El avance debe permanecer ≥95 %.
   - Si la estimación supera 30 min, ejecutar `Forzar envío` en la cola local.
2. **Integridad de inventario**
   - Validar el reporte PDF generado automáticamente (`Inventario actual`).
   - Revisar alertas de stock bajo (`SOFTMOBILE_LOW_STOCK_THRESHOLD`).
3. **POS y ventas**
   - Confirmar que `/pos/sale` emite recibos PDF y que los borradores pendientes se cierran en menos de 15 min.
4. **Backups**
   - Verificar el último respaldo completado en `syncHistory`. Debe existir al menos uno por día hábil.
5. **Seguridad**
   - Revisar `audit_log` para detectar sesiones revocadas o intentos de 2FA fallidos.

## Generación de respaldos manuales

1. Desde el panel de sincronización presiona **Generar respaldo**.
2. Proporciona un motivo corporativo (mínimo 5 caracteres) para registrar la auditoría.
3. Se crea un job en `/backups/jobs` con estado `COMPLETED` y enlace de descarga cifrado.
4. Guarda el artefacto en almacenamiento seguro; los respaldos caducan a los 7 días.

### Restauración controlada

1. Detén la aplicación (`docker compose down`).
2. Sustituye el archivo `softmobile.db` por el respaldo verificado.
3. Ejecuta `alembic upgrade head` para asegurar compatibilidad de migraciones.
4. Levanta servicios (`docker compose up -d`) y ejecuta `pytest -k sync_full` para validar integridad.

## Gestión de incidentes de sincronización

### Duplicados o reintentos excesivos

1. Identifica los eventos en `/sync/outbox/stats` con más de 3 fallos.
2. Usa la acción **Reintentar eventos** desde el tablero para reagendar.
3. Si persisten, revisa la cola local (`hybrid-queue`) y valida claves de idempotencia con `backend/app/utils/idempotency.py`.
4. Documenta el incidente en la bitácora operativa con fecha, módulo afectado y motivo (`X-Reason`).

### Caída de Redis

1. Reinicia el contenedor `redis` y verifica que `fastapi-limiter` reconecte automáticamente.
2. El backend degrada a modo sin rate limiting; monitorea logs (`backend/logs/app.log`) para identificar peticiones sin control.
3. Una vez restablecido, confirma que `/auth/token` vuelve a aplicar límites.

## Flujos POS y caja

- Mantén configurados los accesos rápidos y notificaciones visuales (`POS > Configuración`).
- Los recibos se generan vía `/pos/receipt/{id}`; asegúrate de que los PDF contengan folio, motivo (`X-Reason`) y desglose de pagos.
- Para cierres de caja, valida que las sesiones abiertas no superen 24 h y que la auditoría registre usuario, hora y motivo.

## Despliegues

1. Ejecuta `pytest` y `npm --prefix frontend run test` previo a cualquier despliegue.
2. Genera artefactos: `npm --prefix frontend run build` y empaqueta con `backend/scripts/build_release.py` si se requiere instalador.
3. Actualiza `docs/releases.json` **solo** con notas internas (sin cambiar versión) y registra el ticket en `CHANGELOG.md`.
4. Usa la nomenclatura de commits indicada (`feat(...) [...v2.2.0]`).

## Métricas clave

| Indicador | Umbral | Acción |
| --- | --- | --- |
| Avance híbrido (`overview.percent`) | ≥ 95 % | Reintentar cola si baja del umbral. |
| Eventos pendientes (`overview.remaining.pending`) | < 250 | Escalar si supera el límite. |
| Tiempo estimado (`overview.remaining.estimated_minutes_remaining`) | < 45 min | Revisar conexiones si excede. |
| Ventas POS con motivo | 100 % | Cualquier venta sin `X-Reason` debe rechazarse. |

## Comunicación y auditoría

- Documenta todas las acciones manuales en `ops/runbook.md` o en el sistema de tickets.
- Los motivos corporativos (`X-Reason`) deben estar presentes en cada operación sensible.
- El módulo de auditoría conserva PDF firmados; valida su integridad tras incidentes.

Este manual se actualiza junto con el roadmap Softmobile 2025 v2.2.0. Reporta cualquier desviación al equipo de plataforma.
