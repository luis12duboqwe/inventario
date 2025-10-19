# Documentación complementaria

## Validación Avanzada de Importaciones

El módulo de inventario incorpora una etapa de validación posterior a cada importación inteligente desde Excel. Tras confirmar un lote, el sistema analiza la estructura del archivo, detecta IMEI duplicados, revisa cantidades negativas, evalúa fechas incoherentes y cruza los totales declarados con los saldos reales por sucursal. Todos los hallazgos se almacenan en la tabla `validaciones_importacion` para conservar un historial auditable.

Desde el panel de correcciones pendientes se muestran las incidencias activas, permitiendo editar los campos críticos del dispositivo y marcar cada registro como corregido. El resumen corporativo expone el número de registros revisados, el total de advertencias y errores, los campos faltantes detectados y el tiempo total invertido en el proceso. Además, la API expone reportes en JSON, Excel y PDF para su distribución.

Para cualquier corrección manual se exige un motivo corporativo enviado mediante la cabecera `X-Reason`, manteniendo la trazabilidad operativa conforme al modo estricto v2.2.0.
