# Entrada rápida con lector de código

La pantalla de POS incorpora el módulo **Entrada rápida (lector)** para capturar códigos provenientes de escáneres USB/BT sin necesidad de enfocar un campo específico.

## Comportamiento

- El componente `POSQuickScan` escucha ráfagas de teclas con espacios menores a 80 ms. Una vez que recibe `Enter` procesa el buffer capturado.
- Los eventos provenientes de inputs, textareas o elementos con `contentEditable` se ignoran para no interferir con la captura manual.
- Al validar el código se invoca la búsqueda corporativa (`SalesProducts.searchProducts`) filtrando por `sku`/`imei` y se agrega la coincidencia al carrito.
- El estado visual informa éxito, errores de catálogo o la desactivación de la escucha. El panel permite activar/desactivar la captura global y cuenta con un campo para ingresar códigos manualmente como respaldo.

## Integración en la UI

`POSPage` posiciona `POSQuickScan` encima de la barra de búsqueda. Esto permite alternar entre escaneo automático y búsqueda manual sin duplicar componentes.

```tsx
<POSQuickScan onSubmit={handleQuickScan} />
<ProductSearchBar value={q} onChange={setQ} onSearch={handleSearch} />
```

`handleQuickScan` normaliza el código, consulta el catálogo con `pageSize = 1` y agrega el primer resultado al carrito retornando el nombre del producto para el mensaje de confirmación.

## Pruebas

La suite `frontend/src/modules/sales/pages/__tests__/POSPage.test.tsx` simula los eventos de teclado del lector:

1. Mock de `SalesProducts.searchProducts` para devolver un producto cuando la consulta coincide con el código escaneado.
2. Despacho de la secuencia de teclas (`S`, `K`, `U`, `1`, `2`, `3`, `Enter`) directamente sobre `window`.
3. Verificación de que el carrito renderiza el producto y que el estado del lector muestra el mensaje de confirmación.

Ejecuta la prueba con Vitest:

```bash
npm --prefix frontend test -- POSPage
```

> Nota: la captura automática reestablece el estado visual 2.2 s después de cada lectura para mantener feedback constante sin saturar la UI.
