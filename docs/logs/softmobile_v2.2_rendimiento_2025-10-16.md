# Informe de escenario de rendimiento — 15/10/2025

## Resumen ejecutivo

- **Base de datos utilizada:** `softmobile_performance.db` generada automáticamente con `backend/scripts/performance_dataset.py`.
- **Cobertura de datos:** 500 dispositivos distribuidos en 3 sucursales con 1,000 movimientos de inventario registrados (entradas y salidas balanceadas).
- **Usuarios y permisos:** Alta de 3 cuentas operativas y asignación de membresías corporativas para transferencias.
- **Transacciones clave:** órdenes de compra, ventas con devoluciones, transferencias inter-sucursal, reparaciones registradas y sesiones de sincronización.
- **Respaldo generado:** `/backups/softmobile_respaldo_20251015_013416.zip` con PDF asociado para auditoría.

## Resultados cronometrados por etapa

| Etapa | Tiempo (s) | Detalles destacados |
| --- | --- | --- |
| Bootstrap administrador | 0.31 | ID 1 confirmado. |
| Inicio de sesión | 0.27 | Prefijo de token `eyJhbGciOiJI`. |
| Creación de sucursales | 0.08 | IDs `[1, 2, 3]`.
| Membresías asignadas | 0.05 | Admin vinculado a sucursales `[1, 2, 3]`.
| Altas de usuarios | 0.82 | Nuevos usuarios `[2, 3, 4]`.
| Altas de clientes | 0.30 | 15 clientes con historial y deuda inicial.
| Altas de proveedores | 0.19 | 10 proveedores activos.
| Registro de dispositivos | 8.52 | 500 dispositivos; sucursal 2 y 3 con 125 candidatos a transferencias parciales cada una.
| Movimientos de inventario | 18.07 | 1,000 movimientos totales.
| Órdenes de compra | 0.18 | Órdenes `[1, 2, 3]` recibidas por completo.
| Ventas registradas | 0.20 | Ventas `[1, 2, 3]` con descuentos.
| Devoluciones de venta | 0.10 | 3 devoluciones procesadas. |
| Transferencias | 0.14 | Órdenes `[1, 2]` despachadas y recibidas. |
| Reparaciones | 0.08 | Órdenes `[1, 2, 3]` con piezas descontadas. |
| Sesiones de sincronización | 0.07 | Sesiones `[1, 2, 3, 4]` (3 sucursales + global). |
| Respaldo manual | 0.19 | ZIP y PDF con 61 KB generados. |

> Fuente: ejecución de `PYTHONPATH=. python backend/scripts/performance_dataset.py` (ver bitácora `/tmp/performance_output.txt`).

## Comandos ejecutados

```bash
PYTHONPATH=. python backend/scripts/performance_dataset.py > /tmp/performance_output.txt
```

El script resetea la base de datos de rendimiento, pobla entidades necesarias y genera un respaldo corporativo al cierre.

## Notas operativas

- Los dispositivos con `imei` y `serial` nulos se reservaron para transferencias parciales, evitando bloqueos por unidades únicas.
- El respaldo manual queda disponible en `backups/` para validación y distribución.
- El backend debe arrancar con las variables de entorno habilitando los flags corporativos (`SOFTMOBILE_ENABLE_*`) y apuntando a `softmobile_performance.db` para reproducir los datos capturados.
