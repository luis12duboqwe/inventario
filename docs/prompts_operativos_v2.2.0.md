# Prompts operativos y checklist — Softmobile 2025 v2.2.0

Este documento reúne los prompts de soporte solicitados en el mandato operativo y el checklist reutilizable para validar cada iteración sin cambiar la versión 2.2.0. Úsalo antes de abrir incidencias con IA asistente o ejecutar despliegues.

## 1. Prompts por lote funcional

### Lote A — Catálogo pro de dispositivos
```
Necesito validar el catálogo pro (IMEI, serial, marca, modelo, color, capacidad_gb, estado_comercial, proveedor, costo_unitario, margen_porcentaje, garantia_meses, lote, fecha_compra). Confirma unicidad de IMEI/serial, auditoría de cambios sensibles y búsquedas avanzadas activadas bajo el flag SOFTMOBILE_ENABLE_CATALOG_PRO sin mover la versión 2.2.0.
```

### Lote B — Transferencias entre tiendas
```
Revisa transfer_orders con flujo SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA, permisos por sucursal y descuentos de stock al recibir. Verifica pruebas asociadas y que el flag SOFTMOBILE_ENABLE_TRANSFERS esté activo en v2.2.0.
```

### Lote C — Compras y ventas simples
```
Confirma órdenes de compra con recepción parcial, costo promedio ponderado y ventas con descuento/método de pago. Incluye devoluciones, POS y documentación de motivo X-Reason sin alterar la versión 2.2.0.
```

### Lote D — Analítica y reportes
```
Valida endpoints /reports/analytics/* (rotation, aging, stockout_forecast, comparative, profit_margin, sales_forecast, realtime) y generación de PDF oscuro. Revisa caches y métricas en el dashboard manteniendo la versión 2.2.0.
```

### Lote E — Seguridad y auditoría fina
```
Comprueba middleware X-Reason, 2FA TOTP opcional controlado por SOFTMOBILE_ENABLE_2FA, auditoría de sesiones, recordatorios, acuses y exportaciones CSV/PDF. Confirma cobertura de pruebas y coherencia con README en v2.2.0.
```

### Lote F — Modo híbrido
```
Verifica sync_outbox con prioridades HIGH/NORMAL/LOW, reintentos automáticos, resolución last-write-wins y panel de sincronización actualizado. Documenta incidentes respetando la versión 2.2.0.
```

## 2. Prompts de revisión de seguridad
```
Analiza el módulo Seguridad: políticas de roles, 2FA, auditoría y motivo obligatorio X-Reason. Confirma endpoints /audit/logs, /audit/reminders, /audit/acknowledgements, /reports/audit/pdf y métricas globales con pendientes/atendidas en v2.2.0.
```

```
Evalúa riesgo de exportaciones (CSV/PDF) asegurando cumplimiento de la política X-Reason y ausencia de datos sensibles en respuestas sin autenticación. Mantén la versión 2.2.0.
```

## 3. Prompts de pruebas y calidad
```
Ejecuta pytest desde la raíz y resume resultados, enfocándote en test_audit_filters_and_csv_export, test_inventory_flow y nuevos casos de métricas/auditoría. Indica pasos para obtener un suite en verde manteniendo v2.2.0.
```

```
Corre npm --prefix frontend test y valida componentes AuditLog, GlobalMetrics y POS. Reporta fallas y ajustes necesarios sin alterar la versión.
```

## 4. Checklist rápido por iteración

1. Leer `README.md`, `AGENTS.md`, `docs/evaluacion_requerimientos.md` y `docs/plan_cobertura_v2.2.0.md`.
2. Confirmar que los feature flags permanezcan con los valores del mandato.
3. Ejecutar `pytest` y registrar resultado en `docs/bitacora_pruebas_2025-10-14.md`.
4. Ejecutar `npm --prefix frontend test` y anotar incidencias.
5. Validar en frontend: Inventario (tabs), Operaciones (acordeones), Analítica (grilla 3x2), Seguridad (auditoría completa), Sincronización (`SyncPanel.tsx`).
6. Comprobar que `/sync/outbox` queda sin pendientes críticos y documentar cualquier incidencia.
7. Actualizar README y bitácora operativa con nuevos endpoints, componentes o pruebas agregadas.
8. Verificar que no se haya modificado la versión 2.2.0 en archivos de configuración o documentación.

## 5. Registro de uso

- Marca con fecha y responsable cada vez que se utilicen estos prompts en la bitácora interna.
- Adjunta enlaces a commits o PRs que atiendan hallazgos derivados de las sesiones con IA asistente.

Mantén este documento sincronizado con los cambios del plan de cobertura y revisa que toda interacción externa respete la versión 2.2.0.
