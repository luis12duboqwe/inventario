# Manual y guía de arquitectura para módulos costeo, multi-almacén, compras, RMA, integraciones y modo offline

Este documento consolida el diseño de alto nivel, convenciones de docstrings y pasos de despliegue necesarios para operar los módulos estratégicos en Softmobile 2025 v2.2.0. Las secciones se alinean con los lotes vigentes, preservan compatibilidad retroactiva y mantienen el motivo corporativo obligatorio (`X-Reason` ≥5 caracteres).

## Principios comunes

- **Compatibilidad**: ningún flujo existente debe romperse; los nuevos comportamientos se habilitan bajo *feature flags* y rutas dedicadas.
- **Auditoría**: todas las operaciones sensibles registran `AuditLog` y motivo; en modo híbrido los eventos viajan por `sync_outbox` con reintentos automáticos.
- **Validaciones**: IMEI/serial únicos, control de stock real y bloqueo de límites de crédito en compras/ventas asociadas.
- **Observabilidad**: cada módulo expone métricas y logs estructurados con `trace_id`/`user_id` y persiste eventos relevantes en `audit_logs`.
- **Docstrings**: usa formato PEP 257 con tipado estático y referencia explícita a efectos secundarios. Ejemplo para servicios FastAPI:
  ```python
  def calcular_costo_promedio(compra: PurchaseOrder) -> Decimal:
      """Calcula el costo promedio ponderado tras recibir una compra.

      Args:
          compra: Orden de compra con items recibidos.

      Returns:
          Decimal: Nuevo costo promedio a almacenar en `unit_cost`.

      Raises:
          ValueError: Si la compra no tiene items recibidos.
      """
  ```
- **Docstrings en routers**: documenta dependencias y encabezados obligatorios.
  ```python
  @router.post("/purchases/{id}/receive", response_model=PurchaseReceipt)
  async def receive_purchase(id: UUID, payload: ReceivePayload, reason: str = Header(..., alias="X-Reason")):
      """Recibe parcialmente una orden de compra.

      Requiere cabecera corporativa `X-Reason` (≥5 caracteres), valida permisos por sucursal
      y emite eventos de sincronización híbrida cuando la bandera
      `SOFTMOBILE_ENABLE_HYBRID_PREP` está activa.
      """
  ```
  Incluye siempre: propósito, parámetros, encabezados, efectos secundarios (auditoría, eventos híbridos) y códigos de error relevantes.

## Costeo

### Arquitectura
- **Modelo**: Extiende `Device` con `costo_unitario`, `margen_porcentaje` y soporte de lotes/fechas de compra.
- **Servicios**: `services/costing.py` centraliza cálculo de costo promedio, ajustes por devoluciones y valorización de inventario.
- **Endpoints**: `/costing/adjust` y hooks en `/purchases` y `/sales` para recalcular `inventory_value` tras cada movimiento.
- **Datos críticos**: preserva unicidad de IMEI/serial; calcula `inventory_value` en backend y valida coherencia en `/reports/metrics`.

### Docstrings clave
- `def recalcular_costo(device_id: UUID, movimientos: list[Movement]) -> CostingResult:` describe efectos contables y eventos de auditoría.
- `def estimar_margen(unit_cost: Decimal, precio_venta: Decimal) -> Decimal:` documenta redondeos y límites mínimos.

### Pasos de despliegue
1. Aplicar migraciones de costo (`alembic upgrade head`) y revisar índices de unicidad IMEI/serial.
2. Activar `SOFTMOBILE_ENABLE_CATALOG_PRO=1` y validar `/reports/metrics` para confirmar `inventory_value` coherente.
3. Ejecutar `pytest backend/tests/test_costing.py` y pruebas integrales de ventas para asegurar que las devoluciones actualicen costos.
4. Validar logs `audit_logs` y la cola `sync_outbox` para confirmar que los eventos de costeo se replican en modo híbrido.

## Multi-almacén

### Arquitectura
- **Modelo**: `transfer_orders` con estados `SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA`, stock por sucursal y permisos por tienda.
- **Servicios**: `services/transfers.py` gestiona reservas, decrementos/incrementos y reconciliación de inventario.
- **Frontend**: `TransferOrders.tsx` usa acordeones de operaciones con validación visual de estados y motivo obligatorio.

### Docstrings clave
- `def reservar_stock(origen: UUID, items: list[TransferItem]) -> ReservationResult:` explica manejo de backorders y stock negativo.
- `def aplicar_recepcion(transfer_id: UUID, recibido_por: str) -> TransferReceipt:` detalla auditoría y actualización de `inventory_value`.

### Pasos de despliegue
1. Confirmar migración de `transfer_orders` y triggers de auditoría activos.
2. Habilitar `SOFTMOBILE_ENABLE_TRANSFERS=1` y `SOFTMOBILE_ENABLE_HYBRID_PREP=1` para sincronización híbrida.
3. Ejecutar `pytest backend/tests/test_transfers.py` y flujos UI en `frontend/src/modules/operations/components/TransferOrders.tsx`.
4. Revisar que las recepciones incrementen stock y registren `inventory_value` consistente con `/reports/analytics/rotation`.

## Compras

### Arquitectura
- **Modelo**: `PurchaseOrder` con recepción parcial y cálculo de costo promedio por `PurchaseOrderItem`.
- **Servicios**: `services/purchases.py` actualiza inventario, margenes y ledger de proveedores.
- **Endpoints**: `/purchases` y `/purchases/{id}/receive` con validación de cabecera `X-Reason` y control de permisos.

### Docstrings clave
- `def recibir_compra(order_id: UUID, items: list[ReceivedItem]) -> PurchaseReceipt:` documenta reglas de parcialidad y costos.
- `def registrar_factura(order: PurchaseOrder, factura_ref: str) -> None:` indica persistencia y emisión de eventos a `sync_outbox`.

### Pasos de despliegue
1. Migrar tablas de compras y confirmar índices en `supplier_id`.
2. Activar `SOFTMOBILE_ENABLE_PURCHASES_SALES=1` y validar recepción parcial en entorno de staging.
3. Ejecutar `pytest backend/tests/test_purchases.py` y verificar que `inventory_value` coincida con reportes analíticos.
4. Confirmar que los eventos se publiquen en `sync_outbox` y que las reimpresiones PDF mantengan el folio corporativo.

## RMA (Devoluciones y garantías)

### Arquitectura
- **Modelo**: `rma_requests` vinculadas a ventas, con estados `CREADA→EN_REVISION→APROBADA/RECHAZADA→CERRADA`.
- **Servicios**: `services/rma.py` maneja diagnóstico, reintegro de stock y notas de crédito.
- **Integración POS**: Los recibos PDF incorporan folio de RMA y motivo corporativo.

### Docstrings clave
- `def evaluar_rma(rma_id: UUID, diagnostico: str, resultado: RMAOutcome) -> RMAResult:` documenta reintegros y bloqueos de stock.
- `def generar_nota_credito(sale_id: UUID, amount: Decimal) -> CreditNote:` explica balance con ledger de clientes y proveedores.

### Pasos de despliegue
1. Ejecutar migraciones de `rma_requests` y actualizar fixtures de pruebas.
2. Habilitar banderas de compras/ventas y sincronización híbrida para que las devoluciones viajen en `sync_outbox`.
3. Ejecutar `pytest backend/tests/test_rma.py` y validar recibos PDF de `POS` con folios de RMA asociados.
4. Revisar que el ledger de clientes/proveedores refleje las notas de crédito y que el estado de inventario no permita stock negativo.

## Integraciones

### Arquitectura
- **Servicios**: `services/integrations.py` encapsula conectores (ERP, facturación, mensajería) con reintentos y *circuit breaker* ligero.
- **Middleware**: `require_reason` asegura `X-Reason` en cualquier webhook saliente o entrante.
- **Auditoría**: Cada evento genera entrada en `AuditLog` y se replica en `sync_outbox` para resiliencia.

### Docstrings clave
- `def ejecutar_webhook(payload: dict[str, Any], destino: IntegrationTarget) -> IntegrationResult:` incluye tiempos de espera y manejo de errores.
- `def normalizar_respuesta(respuesta: dict[str, Any]) -> dict[str, Any]:` documenta mapeos de campos externos a esquemas internos.

### Pasos de despliegue
1. Configurar credenciales en variables de entorno sin modificar la versión del producto.
2. Registrar endpoints en `backend/app/routers/integrations.py` y documentar payloads en OpenAPI.
3. Ejecutar `pytest backend/tests/test_integrations.py` y pruebas de carga limitada con `fastapi-limiter` habilitado.
4. Activar monitores de `audit_logs` y validar que los conectores registren `trace_id`/`X-Reason` en respuestas exitosas y fallidas.

## Modo offline

### Arquitectura
- **Cola híbrida**: `sync_outbox` almacena eventos con estado y `attempt_count`; `services/scheduler.py` programa reintentos.
- **Reconexión**: `/sync/run`, `/sync/outbox/retry` y `/sync/history` gobiernan reprogramación y trazabilidad.
- **Frontend**: Panel de reintentos en `SyncPanel.tsx` indica alertas visuales en tema oscuro.

### Docstrings clave
- `def requeue_failed_outbox_entries(limit: int = 100) -> int:` describe criterios de reintento y políticas de expiración.
- `def resolver_conflictos(eventos: list[SyncEvent]) -> list[SyncResolution]:` detalla estrategia *last-write-wins* y auditoría.

### Pasos de despliegue
1. Verificar banderas `SOFTMOBILE_ENABLE_HYBRID_PREP=1` y `SOFTMOBILE_ENABLE_TRANSFERS=1` en ambientes híbridos.
2. Asegurar respaldos previos y limpieza de la cola antes de aislar nodos (`GET /sync/outbox/stats`).
3. Ejecutar `pytest backend/tests/test_sync_outbox.py` y simulaciones de desconexión para confirmar reintentos automáticos.
4. Validar que `sync_outbox` limpie eventos procesados y que `sync/history` conserve trazabilidad completa por `trace_id`.

## Checklist final de despliegue

- [ ] Migraciones aplicadas y revisadas (costeo, transferencias, compras, RMA, integraciones, offline).
- [ ] Variables de entorno con *feature flags* activas según el módulo.
- [ ] Docstrings actualizados en servicios y routers para OpenAPI.
- [ ] Pruebas `pytest` y flujos UI ejecutados y documentados.
- [ ] Auditoría y `X-Reason` verificados en endpoints sensibles.
- [ ] `sync_outbox` y reportes analíticos validados tras cada despliegue parcial.
