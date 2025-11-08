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

## Listas de precios priorizadas (`SOFTMOBILE_ENABLE_PRICE_LISTS`)

Cuando la bandera `SOFTMOBILE_ENABLE_PRICE_LISTS` está activa el backend expone el prefijo `/pricing` con una jerarquía de listas
de precios segmentadas por alcance:

1. **Alcance tienda + cliente**: tiene la mayor prioridad y aplica únicamente cuando coinciden ambos identificadores.
2. **Alcance cliente**: se evalúa después para clientes preferentes sin importar la tienda.
3. **Alcance tienda**: habilita promociones por sucursal.
4. **Alcance global**: se utiliza cuando no hay coincidencias específicas.

### Endpoints

- `GET /pricing/price-lists`: lista las entradas registradas permitiendo filtrar por `store_id`, `customer_id`, incluir/omitir glob
ales e inactivas. Devuelve `404` cuando el flag está deshabilitado.
- `POST /pricing/price-lists`: crea una lista. Exige `X-Reason` (≥ 5 caracteres) y valida que el nombre sea único dentro del mism
o alcance.
- `PUT /pricing/price-lists/{id}` / `DELETE /pricing/price-lists/{id}`: actualiza o elimina la lista respetando auditoría y moti
vo corporativo.
- `POST /pricing/price-lists/{id}/items`: asigna precios específicos por dispositivo. Verifica que el artículo pertenezca a la m
isma sucursal cuando aplica.
- `PUT /pricing/price-lists/{id}/items/{item_id}` / `DELETE ...`: modifican o remueven el precio específico. Siempre requieren `X
-Reason`.
- `GET /pricing/price-evaluation`: evalúa un `device_id` opcionalmente filtrando por `store_id` y `customer_id` mediante parámetros de consulta. Responde con el
 precio ganador, el `price_list_id` y el alcance aplicado.

Todas las operaciones de escritura registran auditoría (`price_list_created`, `price_list_updated`, `price_list_item_created`, et
c.) y preservan la integridad de `Device`: si una lista se elimina las entradas asociadas (`price_list_items`) se borran en cascada.

### Interfaz

- Habilita `VITE_SOFTMOBILE_ENABLE_PRICE_LISTS=1` en el frontend para mostrar la pestaña **Inventario → Listas de precios**.
- La interfaz (`frontend/src/modules/catalog/components/PriceLists.tsx`) permite crear listas, asignar precios y evaluar montos a
ntes de confirmar.
- Al desactivar la bandera, la pestaña se oculta y el backend responde `404`, manteniendo los precios base de los dispositivos.
