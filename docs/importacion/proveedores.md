# Plantillas de importación por proveedor (Inventario inteligente)

Este anexo documenta los formatos oficiales compatibles con la importación inteligente de inventario
(v2.2.0). Cada plantilla está diseñada para que el asistente de la pestaña **Importar** detecte
columnas extendidas (garantía, margen, imagen y descripción) sin requerir reasignaciones manuales.

## MegaSupplier — Catálogo avanzado

- **Formato disponible**: CSV y XLSX.
- **Ubicación para descargas en la aplicación**: `/importacion/plantilla_megasupplier.csv` y un
  enlace dinámico generado por la UI (data URL) para la plantilla XLSX. El contenido base se
  conserva en `frontend/src/assets/importacion/plantilla_megasupplier.xlsx.b64`.
- **Fixtures para pruebas automatizadas**: `backend/tests/fixtures/imports/vendor_layout.csv` y
  `backend/tests/fixtures/imports/vendor_layout.xlsx.b64` (decodificado al vuelo en `pytest`).

### Mapeo de columnas ↔ campos del sistema

| Columna proveedor            | Campo del sistema        |
|-----------------------------|--------------------------|
| `SKU Proveedor`             | `sku`                    |
| `Nombre Catálogo`           | `name`                   |
| `Marca`                     | `marca`                  |
| `Modelo`                    | `modelo`                 |
| `Storage (GB)`              | `capacidad_gb`           |
| `IMEI`                      | `imei`                   |
| `Unidades`                  | `cantidad`               |
| `Precio Publico`            | `precio`                 |
| `Costo Distribuidor`        | `costo`                  |
| `Warranty (months)`         | `garantia_meses`         |
| `Margin %`                  | `margen_porcentaje`      |
| `Image URL`                 | `imagen_url`             |
| `Descripción extendida`     | `descripcion`            |
| `Proveedor`                 | `proveedor`              |
| `Sucursal`                  | `tienda`                 |

### Recomendaciones operativas

1. Ejecuta primero **Analizar estructura**; el asistente marcará la plantilla con estado `ok` y
   precargará los overrides necesarios.
2. Tras aplicar una plantilla, reanaliza el archivo si ya tenías una vista previa abierta para evitar
   incoherencias.
3. Si agregas columnas adicionales (por ejemplo, notas internas), se listarán en las advertencias
   como «columnas sin asignar», sin bloquear la importación.
4. Mantén un margen numérico (sin símbolos) y una garantía en meses para que los campos avanzados se
   sincronicen correctamente en el backend y las auditorías de valuación.

## Próximas plantillas

- **TecnoAliados** (pendiente): incluir lead time (`lead_time_dias`) y semáforos de SLA.
- **Distribuciones Norte** (pendiente): archivo con múltiples hojas (Stock y Backorders).

Añade nuevas entradas siguiendo el mismo formato y recuerda acompañarlas con fixtures dedicados para
las suites de `pytest` y Vitest.
