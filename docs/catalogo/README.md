# Catálogo Pro — Búsqueda avanzada

La versión **Softmobile 2025 v2.2.0** incorpora la búsqueda avanzada del catálogo pro para localizar dispositivos por identificadores únicos y atributos comerciales.

## Filtros disponibles

Los filtros aceptados por `GET /inventory/devices/search` se normalizan automáticamente; basta con enviar cualquiera de los criterios listados:

- `imei` y `serial`: coincidencia exacta.
- `marca`, `modelo`, `color`, `categoria`, `condicion`, `estado`, `ubicacion`, `proveedor`: coincidencia parcial insensible a mayúsculas.
- `capacidad_gb`: valor numérico exacto.
- `fecha_ingreso_desde` y `fecha_ingreso_hasta`: rango de fechas inclusivo (`YYYY-MM-DD`).
- `estado_comercial`: valores permitidos `nuevo`, `A`, `B`, `C`. El servicio acepta mayúsculas/minúsculas y rechaza valores fuera del catálogo.

Para proteger el rendimiento se exige al menos un filtro por solicitud. Cuando `SOFTMOBILE_ENABLE_CATALOG_PRO` está desactivado la ruta responde `404`.

## Auditoría

Cada búsqueda exitosa registra un evento `inventory_catalog_search` en la bitácora:

- **Entidad**: `inventory`.
- **Identificador**: `catalog_search:{user_id|anon}`.
- **Detalle**: filtros aplicados (sin valores vacíos), número de resultados y total paginado.

Además se emite un evento JSON en `softmobile.audit` que incluye los mismos metadatos para correlación externa.

## Referencias

- Backend: `backend/app/services/inventory_search.py` centraliza la consulta y la auditoría.
- Esquema de filtros: `backend/app/schemas/__init__.py` (`DeviceSearchFilters`).
- Frontend: `frontend/src/modules/inventory/components/AdvancedSearch.tsx`.
- Pruebas: `backend/tests/test_inventory_filters.py`, `frontend/src/modules/inventory/components/__tests__/AdvancedSearch.test.tsx`.

## Listas de precios condicionadas

Cuando la variable `SOFTMOBILE_ENABLE_PRICE_LISTS` está activada, el backend publica el router `/price-lists` para definir tarifas preferenciales por sucursal, cliente y periodo de vigencia sin afectar la tabla de dispositivos base. La funcionalidad conserva compatibilidad con el campo `unit_price`/`precio_venta` del catálogo y permite simular la resolución de precios en la interfaz de Inventario.

### Flujo operativo

1. **Creación** — `POST /price-lists` recibe `name`, `currency`, `valid_from`, `valid_until`, banderas `is_active` y los identificadores opcionales de `store_id` y `customer_id` para asignar la lista por sucursal o cliente específico. La respuesta incluye el identificador generado y los criterios de alcance.
2. **Gestión de ítems** — `POST /price-lists/{id}/items` registra precios por `device_id` con prioridad de coincidencia exacta. Cada elemento acepta `price`, `discount_percentage` y límites de vigencia independientes (`valid_from`, `valid_until`). Los conflictos se rechazan con `409`.
3. **Consulta** — `GET /price-lists?include_items=true` lista las tarifas vigentes filtrando por sucursal/cliente/estado. Para obtener un solo registro se usa `GET /price-lists/{id}`.
4. **Resolución** — `GET /price-lists/resolve` aplica la prioridad `cliente → sucursal → global` considerando fechas y vigencia del ítem. Es necesario enviar `device_id` y opcionalmente `store_id`, `customer_id`, `reference_date` y un precio base (`default_price`, `default_currency`) en caso de no encontrar coincidencias.

Todas las operaciones `POST/PUT/PATCH/DELETE` exigen el encabezado corporativo `X-Reason` con al menos 5 caracteres. Las respuestas de lectura devuelven estructuras tipadas según los esquemas `PriceListResponse`, `PriceListItemResponse` y `PriceResolution` en `backend/app/schemas/__init__.py`.

### Integración con la UI

- Frontend: `frontend/src/modules/catalog/components/PriceLists.tsx` habilita la pestaña «Listas de precios» dentro de Inventario y consume las rutas anteriores mediante `frontend/src/modules/catalog/services/priceListsService.ts`.
- Pruebas: `backend/tests/test_price_lists.py`, `backend/tests/test_pricing.py` y `frontend/src/modules/catalog/components/__tests__/PriceLists.test.tsx` validan creación, asignaciones, conflictos y resolución de precios.
