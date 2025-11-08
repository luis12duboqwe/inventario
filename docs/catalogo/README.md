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
