# Banderas de funcionalidades Softmobile 2025 v2.2.0

Las siguientes banderas controlan la disponibilidad de módulos clave tanto en el
backend como en el frontend. Todas deben declararse en el entorno del backend
(`SOFTMOBILE_ENABLE_*`) y, cuando aplique, en la capa web usando el prefijo
`VITE_SOFTMOBILE_ENABLE_*` para que la interfaz refleje el estado real.

| Bandera | Valor por defecto | Propósito | Dependencias / Consideraciones |
| --- | --- | --- | --- |
| `SOFTMOBILE_ENABLE_CATALOG_PRO` | `1` | Activa el catálogo avanzado con búsqueda por IMEI, serie y auditoría de cambios sensibles. | Requerido por las capacidades híbridas y por los paquetes de productos (`SOFTMOBILE_ENABLE_BUNDLES`). |
| `SOFTMOBILE_ENABLE_TRANSFERS` | `1` | Permite las transferencias entre sucursales y el flujo SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA. | Depende del catálogo activo para descontar inventario en cada etapa. |
| `SOFTMOBILE_ENABLE_PURCHASES_SALES` | `1` | Habilita compras, ventas, devoluciones y el POS corporativo. | Necesario para emitir DTE y para registrar combos de venta. |
| `SOFTMOBILE_ENABLE_ANALYTICS_ADV` | `1` | Expone reportes avanzados (rotación, aging, proyección de quiebres). | Requiere sincronización híbrida para mantener métricas al día. |
| `SOFTMOBILE_ENABLE_HYBRID_PREP` | `1` | Enciende el modo híbrido y la cola `sync_outbox` con reintentos. | Condición previa para métricas y reportes en tiempo real. |
| `SOFTMOBILE_ENABLE_2FA` | `0` | Permite habilitar TOTP opcional para usuarios corporativos. | Recomendada cuando se activa DTE para reforzar controles. |
| `SOFTMOBILE_ENABLE_PRICE_LISTS` | `0` | Muestra el módulo de listas de precios priorizadas y el router `/pricing`. | Requiere catálogo pro activo y sincronización híbrida. |
| `SOFTMOBILE_ENABLE_BUNDLES` | `0` | Habilita la administración de paquetes/combos de productos asociados al inventario. | Depende de `SOFTMOBILE_ENABLE_CATALOG_PRO` y `SOFTMOBILE_ENABLE_PURCHASES_SALES` para calcular existencias y márgenes. |
| `SOFTMOBILE_ENABLE_DTE` | `0` | Activa la emisión de Documentos Tributarios Electrónicos desde ventas y POS. | Requiere `SOFTMOBILE_ENABLE_PURCHASES_SALES`; se recomienda habilitar `SOFTMOBILE_ENABLE_2FA` para reforzar los flujos fiscales. |

> **Nota:** cuando un flag está deshabilitado en el backend pero habilitado en el
frontend, la API responderá con `404` o `403` según el módulo. Asegúrate de
mantener ambos entornos sincronizados para evitar inconsistencias en la
experiencia del usuario.
