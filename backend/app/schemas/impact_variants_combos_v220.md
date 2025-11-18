# Impacto en esquemas y CRUD — Variantes, combos, DTE, garantías y loyalty (v2.2.0)

## Cambios requeridos en `backend/app/schemas/__init__.py`

1. **Nuevos modelos de variantes**
   - Definir `DeviceVariantAttributeBase`, `DeviceVariantAttributeCreate`, `DeviceVariantAttributeResponse`.
   - Definir `DeviceVariantBase`, `DeviceVariantCreate`, `DeviceVariantUpdate`, `DeviceVariantResponse` con
     `variant_sku`, `barcode`, `attributes: dict[str, str]`, `unit_price_override`, `is_default`, `is_active`.
   - Definir `DeviceVariantValueCreate`/`Response` para la tabla puente.
   - Extender `DeviceBase`/`DeviceResponse` con `catalog_template_id`, `variant_count`, `has_variants`.
   - Actualizar `MovementCreate`, `InventoryReservationCreate` y `SaleItemCreate` para aceptar `variant_id: int | None` y
     validar que solo se envíe cuando `device_id` esté presente.

2. **Modelos para combos**
   - Crear `ComboProductBase`, `ComboProductCreate`, `ComboProductUpdate`, `ComboProductResponse` con campos
     `combo_sku`, `base_price`, `valid_from`, `valid_until`, `is_active`.
   - Crear `ComboItemCreate`/`Update`/`Response` con referencias opcionales a `variant_id`.
   - Crear `SaleComboLinkResponse` y actualizar `SaleResponse`/`SaleDetailResponse` para incluir `combo_summary` y el vínculo
     `combo_id` en cada línea.

3. **Modelos para DTE**
   - Declarar Enum `DTEStatus` (`PENDIENTE`, `EMITIDO`, `RECHAZADO`, `ANULADO`).
   - Crear `DTEDocumentBase`, `DTEDocumentCreate`, `DTEDocumentResponse`, `DTEEventResponse`.
   - Agregar a `SaleResponse` los campos `dte_status` y `dte_reference`.

4. **Garantías**
   - Crear `WarrantyPolicyBase`, `WarrantyPolicyCreate`, `WarrantyPolicyResponse`.
   - Crear `WarrantyAssignmentCreate`, `WarrantyAssignmentResponse` y `WarrantyStatus` Enum.
   - Crear `WarrantyClaimCreate`, `WarrantyClaimUpdate`, `WarrantyClaimResponse`.
   - Añadir `warranty_status` a `SaleItemResponse` y permitir que `SaleItemCreate` reciba `warranty_policy_id` opcional.

5. **Loyalty**
   - Añadir `loyalty_opt_in` a `CustomerResponse` y `CustomerUpdate`.
   - Definir `LoyaltyProgramBase`, `LoyaltyProgramCreate`, `LoyaltyProgramUpdate`, `LoyaltyProgramResponse`.
   - Definir `LoyaltyTierCreate`/`Response`, `LoyaltyMembershipResponse`, `LoyaltyTransactionCreate`/`Response`.
   - Incorporar `loyalty_points_earned` y `loyalty_points_redeemed` a `SaleResponse` y `SaleCreate`/`SaleUpdate`.

6. **Paginación y reportes**
   - Actualizar `InventoryReservationResponse`, `MovementResponse`, `SalesSummaryReport`, `CustomerDashboardMetrics` para
     contemplar columnas derivadas de variantes, combos y loyalty.

## Cambios en `backend/app/crud.py`

1. **Catálogo e inventario**
   - Extender `create_device`, `update_device`, `list_devices`, `get_device_by_sku` para persistir `catalog_template_id` y
     devolver contadores de variantes.
   - Nuevas funciones: `create_device_variant`, `update_device_variant`, `archive_device_variant`,
     `list_device_variants`, `get_device_variant`, `sync_variant_values`.
   - Ajustar `create_inventory_movement` (línea ~6626) y `create_reservation` (línea ~6260) para validar stock a nivel
     variante (`variant_id`) y fallback al SKU base si no se envía.
   - Ajustar `release_reservation`, `renew_reservation`, `convert_reservation_to_sale` para propagar `variant_id`.

2. **Combos**
   - Incorporar funciones `create_combo_product`, `update_combo_product`, `toggle_combo_status`, `list_combos`,
     `attach_combo_to_sale` y `hydrate_combo_summary`.
   - Modificar `create_sale` (línea ~12647) y `create_sale_items` para aceptar combos y distribuir descuentos.
   - Actualizar `recalculate_inventory_after_sale` para descontar inventario de cada `combo_items` asociado.

3. **DTE**
   - Nuevas funciones `register_dte_document`, `update_dte_status`, `list_dte_by_sale`, `log_dte_event`.
   - Extender `create_sale` y `finalize_sale_checkout` para disparar la generación asíncrona del DTE (via servicios) y guardar
     `dte_status`/`dte_reference`.

4. **Garantías**
   - Crear `create_warranty_policy`, `list_warranty_policies`, `assign_warranty_to_sale_item`,
     `update_warranty_claim_status`.
   - Modificar `create_sale` y `register_sale_return` para actualizar `warranty_status` cuando se realice una devolución.

5. **Loyalty**
   - Extender `create_customer` (línea ~3657) y `update_customer` (línea ~3715) para persistir `loyalty_opt_in` y vincular
     membresías.
   - Nuevas funciones `create_loyalty_program`, `update_loyalty_program`, `create_loyalty_membership`,
     `record_loyalty_transaction`, `recalculate_loyalty_balance`.
   - Ajustar `create_sale`, `finalize_sale_checkout`, `process_sale_refund` para emitir movimientos de puntos y validar saldo al
     canjear.

## Endpoints a actualizar o crear

- **Inventario (`backend/app/routers/inventory.py`)**
  - Actualizar `POST /inventory/stores/{store_id}/devices/{device_id}` (alta/actualización) para recibir `catalog_template_id`
    y exponer `has_variants`.
  - Ajustar `POST /inventory/stores/{store_id}/movements` y `/inventory/reservations` para aceptar `variant_id`.
  - Crear subrutas `POST /inventory/devices/{device_id}/variants`, `PATCH /inventory/devices/{device_id}/variants/{variant_id}` y
    `GET /inventory/devices/{device_id}/variants`.

- **Nuevo router `variants.py`**
  - Exponer operaciones especializadas (`/variants/attributes`, `/variants/{variant_id}/values`) para administración avanzada.

- **Nuevo router `combos.py`**
  - CRUD completo de combos (`GET/POST/PATCH /combos`, `POST /combos/{id}/items`).
  - Endpoint `POST /combos/{id}/simulate-pricing` para prorratear descuentos previo a ventas.

- **Ventas (`backend/app/routers/sales.py` y `backend/app/routers/pos.py`)**
  - Permitir `variant_id`, `combo_id`, `warranty_policy_id`, `loyalty_points_to_redeem` en los payloads.
  - Responder con `combo_summary`, `dte_status`, `loyalty_points_earned` y `warranty_status` por línea.
  - Añadir endpoints `POST /sales/{sale_id}/dte/retry`, `GET /sales/{sale_id}/dte` reutilizando el nuevo CRUD.

- **Nuevo router `dte.py`**
  - Publicar `/dte/documents` (listado), `/dte/documents/{id}` (detalle), `/dte/documents/{id}/events` (bitácora).

- **Garantías**
  - Crear `warranties.py` con rutas `/warranties/policies`, `/warranties/assignments`, `/warranties/claims`.
  - Actualizar `backend/app/routers/repairs.py` para relacionar reclamos de garantía con órdenes de reparación existentes.

- **Loyalty**
  - Crear `loyalty.py` con rutas `/loyalty/programs`, `/loyalty/memberships`, `/loyalty/transactions`.
  - Actualizar `backend/app/routers/customers.py` para exponer `loyalty_opt_in`, listado de membresías y puntos acumulados.
  - Ajustar `backend/app/routers/reports.py` y `reports_sales.py` para agregar métricas de puntos ganados/redimidos.

- **Reportes y analítica**
  - Extender `/reports/analytics/*` y `/reports/sales/*` con filtros por `variant_id`, `combo_id` y métricas de loyalty.

## Consideraciones adicionales

- Todos los endpoints nuevos deben respetar `X-Reason` cuando se modifique inventario o saldo de puntos.
- Habilitar *feature flags* independientes (`SOFTMOBILE_ENABLE_VARIANTS`, `SOFTMOBILE_ENABLE_COMBOS`, etc.) para exponer los
  nuevos routers sin afectar clientes actuales.
- Documentar las respuestas actualizadas en `docs/architecture/data_model.md` y agregar pruebas `pytest` que cubran variantes,
  combos, DTE, garantías y loyalty antes de liberar la funcionalidad.
