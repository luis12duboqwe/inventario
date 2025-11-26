# Manual fiscal — Libro de Ventas y Compras

El módulo fiscal de Softmobile 2025 v2.2.0 permite generar el Libro de Ventas y Compras mensual desde el backend en el endpoint `/reports/fiscal/books`. Este reporte consolida los totales por mes y separa los montos gravados al ISV 15 %, ISV 18 % y operaciones exentas, permitiendo descargar la información en múltiples formatos.

## Parámetros disponibles

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `year` | entero | Sí | Año del periodo a consultar. |
| `month` | entero (1-12) | Sí | Mes del periodo a consultar. |
| `book_type` | `sales` o `purchases` | No (por defecto `sales`) | Indica si se genera el libro de ventas o el libro de compras. |
| `format` | `json`, `pdf`, `xlsx`, `xml` | No (por defecto `json`) | Formato de salida. Para `pdf`, `xlsx` y `xml` es obligatorio incluir la cabecera `X-Reason` con al menos 5 caracteres. |

## Respuesta JSON

Cuando se omite el parámetro `format`, la API responde con la estructura `FiscalBookReport`:

- `generated_at`: marca de tiempo de generación.
- `filters`: parámetros aplicados (año, mes y tipo).
- `totals`: totales por cada tramo de impuesto (base e impuesto para 15 %, 18 % y exentos) y total general.
- `entries`: lista correlativa de registros con fecha, folio, contraparte, detalle y desglose por tasa.

## Descarga de archivos

- **PDF**: resumen ejecutivo más tabla detallada en tema oscuro corporativo.
- **Excel**: hoja “Libro Fiscal” con encabezados estilizados y totales al final.
- **XML**: estructura `LibroFiscal` con nodos de totales y registros individuales.

Recuerda que toda descarga requiere autenticar al usuario con rol **ADMIN** y proporcionar la cabecera `X-Reason` (≥ 5 caracteres) para cumplir con la política corporativa de auditoría.
