# Integración de lectores RFID y básculas

Esta guía resume las interfaces genéricas para integrar lectores RFID y básculas industriales en el backend, así como los prototipos para asociar EPC y pesos a productos.

## Interfaces disponibles

- `RFIDReaderAdapter`: define `connect`, `disconnect`, `read_single` y `read_batch` para capturar EPC desde cualquier lector RFID compatible.
- `ScaleAdapter`: expone `connect`, `disconnect` y `read_weight` para obtener lecturas normalizadas en kilogramos.
- `ProductInputRepository`: repositorio abstracto encargado de persistir asociaciones EPC⇄producto (`bind_epc`) y capturas de peso (`record_weight`).

Las estructuras de datos incluyen:

- `RFIDTagReading`: lectura individual con EPC, lector y marca de tiempo.
- `RFIDProductLink`: resultado de vincular un EPC a un producto.
- `ScaleReading`: medición de peso con indicador de estabilidad.
- `ProductWeightCapture`: registro de peso ligado a un producto.

## Prototipos de lectura y asociación

Para evitar dependencias directas con SDKs propietarios, el archivo `services/hardware/inputs.py` provee funciones auxiliares que demuestran el flujo mínimo esperado:

```python
from backend.app.services.hardware import (
    capture_and_link_epc,
    capture_weight_for_product,
    RFIDReaderAdapter,
    ScaleAdapter,
    ProductInputRepository,
)

async def asociar_etiqueta(reader: RFIDReaderAdapter, repo: ProductInputRepository, producto_id: str):
    enlace = await capture_and_link_epc(reader, repo, producto_id)
    return enlace  # ``None`` cuando no hay etiquetas cercanas

async def registrar_peso(scale: ScaleAdapter, repo: ProductInputRepository, producto_id: str):
    captura = await capture_weight_for_product(scale, repo, producto_id)
    return captura
```

Cada adaptador debe encargarse de traducir su protocolo de conexión (USB, TCP/IP, Serial) a las llamadas descritas. El repositorio concreto puede persistir en base de datos, colas de sincronización o caché según la arquitectura.

## Requisitos y consideraciones

- Las implementaciones concretas deben manejar la inicialización y cierre de puertos de forma segura antes de realizar lecturas.
- Normaliza los EPC como cadenas y los pesos en kilogramos para mantener consistencia con el resto del inventario.
- Registra la fuente (`reader`/`source`) en cada lectura para facilitar auditoría y trazabilidad de hardware.
- Si un SDK propietario requiere drivers del sistema operativo, documenta el procedimiento de instalación en `installers/` y evita añadir binarios al repositorio.
