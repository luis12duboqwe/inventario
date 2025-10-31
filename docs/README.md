# Documentación complementaria

## Validación Avanzada de Importaciones

El módulo de inventario incorpora una etapa de validación posterior a cada importación inteligente desde Excel. Tras confirmar un lote, el sistema analiza la estructura del archivo, detecta IMEI duplicados, revisa cantidades negativas, evalúa fechas incoherentes y cruza los totales declarados con los saldos reales por sucursal. Todos los hallazgos se almacenan en la tabla `validaciones_importacion` para conservar un historial auditable.

Desde el panel de correcciones pendientes se muestran las incidencias activas, permitiendo editar los campos críticos del dispositivo y marcar cada registro como corregido. El resumen corporativo expone el número de registros revisados, el total de advertencias y errores, los campos faltantes detectados y el tiempo total invertido en el proceso. Además, la API expone reportes en JSON, Excel y PDF para su distribución.

Para cualquier corrección manual se exige un motivo corporativo enviado mediante la cabecera `X-Reason`, manteniendo la trazabilidad operativa conforme al modo estricto v2.2.0.

## Módulo de reparaciones — Pack37

La iteración Pack37 añade un flujo integral de reparaciones que cubre tanto backend como frontend:

- **API FastAPI**: se exponen rutas `POST/GET/PATCH /repairs`, administración de piezas con `POST /repairs/{id}/parts`, eliminación con `DELETE /repairs/{id}/parts/{partId}` y cierre corporativo `POST /repairs/{id}/close` que genera el PDF de la orden. Los estados soportados son `PENDIENTE`, `EN_PROCESO`, `LISTO`, `ENTREGADO` y `CANCELADO`, con alias en inglés para integraciones externas.
- **Inventario y costos**: cada repuesto tomado del stock registra un movimiento `OUT/IN`, recalcula el valor inventario y preserva un `parts_snapshot` auditable. Las compras externas se almacenan con su costo unitario para reflejar el total de la reparación.
- **Frontend React**: la página `/reparaciones` muestra pestañas Pendientes, En proceso, Listas y Entregadas, filtros por fechas/sucursal/estado, exportación CSV y panel lateral para altas. Los modales de repuestos y presupuesto sincronizan la orden, validan motivo corporativo (`X-Reason`) y permiten cerrar con PDF inmediato.
- **Pruebas automatizadas**: `backend/tests/test_repairs.py` cubre el flujo completo (creación, gestión de piezas, cierre y PDF), mientras que la build de Vite garantiza que el tablero React permanezca operativo en tema oscuro.

Toda la documentación, estilos y mensajes se mantienen en español y respetan el modo estricto Softmobile 2025 v2.2.0.
