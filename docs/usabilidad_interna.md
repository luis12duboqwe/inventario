# Pruebas de usabilidad interna — Flujos Operativos

## Alcance
- Facturación (ventas y devoluciones)
- Cierre de caja
- Compras y recepciones

## Participantes
- 3 usuarios internos (operaciones, caja y compras) evaluando en entorno de staging v2.2.0.

## Hallazgos clave
1. **Facturación**: el acceso directo a ventas/devoluciones redujo en ~30% el tiempo de búsqueda; se validó que el motivo corporativo permanece prellenado y editable.
2. **Cierre de caja**: el total automático evitó el doble registro y los usuarios entendieron mejor las diferencias con las ayudas contextuales.
3. **Compras**: los atajos para limpiar filtros y saltar a proveedores disminuyeron errores al cambiar de lote; se sugirió mantener los filtros de historial sincronizados.

## Acciones realizadas
- Se añadieron tarjetas de auditoría con acordeón y tooltips para cada flujo.
- Se fijaron anclas de navegación rápida a formularios y paneles laterales.
- Se documentaron mensajes claros sobre motivo corporativo y cálculo automático de totales.

## Próximos pasos
- Integrar métricas de tiempo por paso en facturación para medir adopción.
- Conectar el cierre de caja con recibo PDF cuando el backend lo expose.
- Monitorear el uso de plantillas de compra para ajustar los textos de ayuda.
