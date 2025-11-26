# Impresión de etiquetas (Zebra/Epson)

Las etiquetas de inventario se pueden generar en PDF o enviarse como comandos directos para impresoras Zebra (ZPL) y Epson (ESC/POS). Los tamaños soportados son:

- **38x25 mm (compacto)**: etiquetas breves para móviles o cajas de accesorios.
- **50x30 mm (estándar)**: formato general recomendado para la mayoría de SKU.
- **80x50 mm (ampliado)**: etiquetas con más espacio para identificadores dobles.
- **A7**: vista PDF apaisada para descarga o archivo.

## Conectores

Los conectores siguen la misma estructura que el hardware POS:

- `type`: `usb` o `network`.
- `identifier`: nombre visible de la impresora.
- `path`: ruta del dispositivo USB (cuando aplique).
- `host` y `port`: destino de la impresora de red.

Los trabajos directos incluyen el conector elegido (si existe en la sucursal) para que los bridges locales puedan abrir el puerto correcto.

## Pruebas desde navegador/app local

1. Selecciona el **formato** (PDF/ZPL/ESC/POS) y la **plantilla** en el generador de etiquetas.
2. Para formatos directos, copia el bloque de comandos o usa el botón **“Probar en impresora local”**, que encola el evento `label.print` por WebSocket (`hardware_channels`).
3. Los comandos usan tema oscuro corporativo, QR interno y código de barras del SKU. La vista previa PDF mantiene los mismos datos y respeta el motivo corporativo (`X-Reason`).

> Recuerda validar que el motivo corporativo tenga al menos 5 caracteres y que la sucursal/dispositivo correspondan antes de lanzar la impresión.
