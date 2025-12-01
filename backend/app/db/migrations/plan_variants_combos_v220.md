# Plan de migraciones Alembic — Extensiones v2.2.0 (variantes, combos, DTE, garantías, loyalty)

## Contexto

- **Head actual**: `202511070003_merge_inventory_reservations_and_user_verification_heads` (carpeta `backend/alembic/versions`).
- **Motor objetivo**: mantener compatibilidad con SQLite y PostgreSQL, siguiendo las reglas de `Base.metadata` vigentes.
- Todas las revisiones nuevas deben ubicarse en `backend/alembic/versions/` con prefijos cronológicos
  `2025MMDDHHMM_*.py` y usar `down_revision = "202511070003_merge_inventory_reservations_and_user_verification_heads"`
  en la primera extensión.

## Secuencia propuesta

1. **2025XXYY0001_catalog_variants.py**
   - **Down revision**: `202511070003_merge_inventory_reservations_and_user_verification_heads`.
   - **Operaciones**:
     - Crear tablas `device_variant_attributes`, `device_variants` y `device_variant_values`.
     - Agregar columna nullable `catalog_template_id` a `devices` (`Integer`, FK opcional a nueva tabla `catalog_templates`
       si se habilita más adelante, por ahora solo índice).
     - Añadir columnas `variant_id` (nullable) a `inventory_movements`, `inventory_reservations` y `detalle_ventas` con
       `ForeignKey('device_variants.id', ondelete='SET NULL')`.
     - Crear índices en `device_variants.variant_sku`, `device_variants.device_id`, `device_variant_values.attribute_id`.
   - **Compatibilidad**: valores por defecto `NULL`; no afecta consultas existentes.

2. **2025XXYY0002_combo_products.py**
   - **Down revision**: `2025XXYY0001_catalog_variants`.
   - **Operaciones**:
     - Crear tabla `combo_products` (FK `store_id` → `sucursales.id_sucursal`).
     - Crear tabla `combo_items` con FK a `combo_products`, `devices` y `device_variants` (`SET NULL`).
     - Crear tabla puente `sale_combo_links` (`sale_id` FK → `ventas.id_venta`).
     - Agregar columna JSON `combo_summary` a `ventas` (usar `sa.JSON().with_variant(sa.JSON, 'sqlite')` para compatibilidad).
     - Agregar columna nullable `combo_id` a `detalle_ventas` con FK a `combo_products` (`SET NULL`).
   - **Compatibilidad**: utilizar valores por defecto `None` y migración de datos vacía.

3. **2025XXYY0003_sales_dte_support.py**
   - **Down revision**: `2025XXYY0002_combo_products`.
   - **Operaciones**:
     - Crear tabla `dte_documents` con FKs a `ventas.id_venta` y `clientes.id_cliente` (`SET NULL`).
     - Crear tabla `dte_events` con FK a `dte_documents.id` y `usuarios.id_usuario` (`SET NULL`).
     - Agregar columnas `dte_status` (`sa.Enum('PENDIENTE','EMITIDO','RECHAZADO','ANULADO', name='dte_status_enum')`) y
       `dte_reference` (`String(80)`, nullable) en `ventas`.
     - Registrar eliminación de `dte_status_enum` en `downgrade` solamente cuando no exista la tabla (manejo seguro para
       SQLite/PostgreSQL).
   - **Compatibilidad**: `dte_status` default `'PENDIENTE'`, se actualiza en procesos posteriores.

4. **2025XXYY0004_warranty_tables.py**
   - **Down revision**: `2025XXYY0003_sales_dte_support`.
   - **Operaciones**:
     - Crear tablas `warranty_policies`, `warranty_assignments` y `warranty_claims`.
     - Vincular `warranty_claims.repair_order_id` a `repair_orders.id` (`SET NULL`).
     - Agregar columna `warranty_status` (Enum `SIN_GARANTIA`, `ACTIVA`, `VENCIDA`, `RECLAMADA`) a `detalle_ventas` con default
       `'SIN_GARANTIA'`.
     - Crear índices en `warranty_assignments.sale_item_id` y `warranty_claims.assignment_id`.
   - **Compatibilidad**: default `'SIN_GARANTIA'` en filas existentes.

5. **2025XXYY0005_loyalty_program.py**
   - **Down revision**: `2025XXYY0004_warranty_tables`.
   - **Operaciones**:
     - Crear tablas `loyalty_programs`, `loyalty_tiers`, `loyalty_memberships` y `loyalty_transactions`.
     - Vincular `loyalty_transactions.sale_id` a `ventas.id_venta` (`SET NULL`) y `registered_by` a `usuarios.id_usuario`.
     - Agregar columnas `loyalty_points_earned` y `loyalty_points_redeemed` (`Numeric(12,2)`, default `0`) a `ventas`.
     - Agregar columna `loyalty_opt_in` (`Boolean`, default `False`) a `clientes`.
     - Crear índices `ix_loyalty_memberships_program_customer` (único) y `ix_loyalty_transactions_sale_id`.
   - **Compatibilidad**: inicializar valores en cero; no modificar registros existentes.

## Notas de implementación

- Cada migración debe actualizar `Enum` con `op.execute("CREATE TYPE ...")` solo en motores PostgreSQL.
  En SQLite se representará como `sa.String` y se documentará el *fallback* en el archivo.
- Incluir pruebas de migración: ejecutar `alembic upgrade <revision>` y `alembic downgrade <down_revision>` en entornos locales
  antes de subir cambios.
- Documentar cada revisión en `CHANGELOG.md` y enlazar este plan en `docs/architecture/data_model.md` para
  mantener trazabilidad.
- Mantener la versión del producto en `v2.2.0`; cualquier bandera de despliegue deberá consultarse en `config.FeatureFlags`.
