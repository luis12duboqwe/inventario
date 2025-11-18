# Auditoría comparativa inventario vs. "sistema perfecto" — 07/11/2025

> Mandato estricto: v2.2.0. No modificar versión. Mejoras sólo bajo nuevas rutas/flags; compatibilidad retroactiva garantizada.

## 1. Alcance y metodología

Se realizó una revisión multinivel (básico → avanzado) contrastando el sistema actual Softmobile 2025 v2.2.0 contra un modelo de referencia de plataforma de inventario empresarial: catálogo, costos, operaciones (compras/ventas/transferencias/POS), trazabilidad, analítica, seguridad, auditoría, sincronización híbrida, rendimiento, accesibilidad, resiliencia y cumplimiento.

Fuentes: código (`backend/app/routers/*`, `crud.py`, `services/*`), pruebas (`backend/tests/*`, Vitest), documentación (`README.md`, `AGENTS.md`, bitácoras), cambios recientes (CHANGELOG). Se validó estado ejecutando suites backend (194 passed) y frontend (61 passed) antes de la evaluación.

## 2. Matriz de cobertura resumida

| Dominio                                                        | Situación actual | Nivel   | Comentario clave                                                                                  |
| -------------------------------------------------------------- | ---------------- | ------- | ------------------------------------------------------------------------------------------------- |
| Catálogo avanzado (IMEI/Serie, atributos extendidos)           | Implementado     | Fuerte  | Campos ampliados + identificadores duales + vista valoración.                                     |
| Movimientos y valoración costo promedio                        | Implementado     | Fuerte  | Ajustes con auditoría y alertas de umbral. Solo costo promedio.                                   |
| Transferencias multi-sucursal                                  | Implementado     | Fuerte  | Flujo SOLICITADA→EN_TRANSITO→RECIBIDA, exportaciones.                                             |
| Compras (parcial, devoluciones)                                | Implementado     | Fuerte  | Recepción parcial y ajustes de costo. Falta planificación reorden.                                |
| Ventas / POS (multi-pago, recibos, devoluciones)               | Implementado     | Fuerte  | Carrito, holds, multi-pago. Falta reservas futuras/backorder.                                     |
| Clientes (crédito, ledger)                                     | Implementado     | Fuerte  | Límite, bloqueo por crédito, ledger. Falta scoring y segmentación ABC.                            |
| Proveedores (batches, estadísticas)                            | Implementado     | Fuerte  | Batch y métricas básicas. Falta lead time, fill rate, SLA proveedor.                              |
| Reportes Inventario/Analítica                                  | Implementado     | Fuerte  | Rotación, aging, forecast básico. Falta estacionalidad y simulación.                              |
| Auditoría y logs sistema                                       | Implementado     | Fuerte  | Bitácoras + severidad + exportaciones. Falta cadena de custodia/tamper-evidence.                  |
| Seguridad (RBAC, 2FA opcional)                                 | Implementado     | Fuerte  | Roles + matriz permisos + 2FA flag. Falta política complejidad contraseñas/macros IAM (rotación). |
| Sincronización híbrida (outbox + reintentos)                   | Implementado     | Fuerte  | Prioridades + discrepancias. Falta particionamiento y compresión eventos.                         |
| Backups y restore parcial                                      | Implementado     | Fuerte  | ZIP/SQL/JSON. Falta cifrado en reposo y verificación automática.                                  |
| UI/UX (dark theme + lazy + accesibilidad)                      | Implementado     | Fuerte  | Tokens, ARIA, reduced-motion. Falta PWA/offline completo y atajos teclado POS.                    |
| Performance (caché GET, lazy import)                           | Implementado     | Sólido  | TTL, deduplicación. Falta stress/benchmark automático y escalado horizontal guidelines.           |
| Observabilidad (logs + metrics endpoint)                       | Parcial          | Medio   | Métricas básicas. Falta tracing distribuido, SLO y alertas automáticas externas.                  |
| Calidad pruebas (alto coverage funcional)                      | Sólido           | Medio   | Suites integrales. Falta pruebas de carga, propiedad y caos.                                      |
| Cumplimiento (X-Reason, roles)                                 | Parcial          | Medio   | Motivo corporativo. Falta GDPR/PII (anonimización), retención y borrado seguro.                   |
| Gestión avanzada inventario (reservas, kitting, ensamblaje)    | Ausente          | Crítico | No hay BOM, kits, ensamblaje, desensamblaje ni reservas programadas.                              |
| Conteos cíclicos / físicas                                     | Ausente          | Alto    | No existe módulo de sesiones de conteo con reconciliación y aprobación.                           |
| Multi-currency / métodos costo (FIFO/LIFO, estándar)           | Ausente          | Alto    | Solo costo promedio; sin conversión FX ni elección método contable.                               |
| Caducidades / lotes / FEFO                                     | Parcial          | Alto    | Lote presente; no expiración FEFO ni alertas por vencimiento.                                     |
| Calidad / cuarentena / inspección                              | Ausente          | Medio   | Falta estado de calidad (quarantine, rejected) y flujos QC.                                       |
| Gestión de backorders / picking avanzado                       | Ausente          | Medio   | No hay reserva parcial ni estado backorder, no slotting de picking.                               |
| RMA / devoluciones proveedor detalladas                        | Parcial          | Medio   | Devoluciones simples; sin RMA numerado ni condición técnica retorno.                              |
| MDM (unidad de medida jerárquica, conversiones)                | Ausente          | Medio   | Falta catálogo UoM y conversión (caja → unidad).                                                  |
| Integraciones externas (EDI, webhooks)                         | Ausente          | Medio   | No hay webhooks, EDI ni cola estandarizada multi-sistema.                                         |
| Seguridad avanzada (cifrado campos sensibles, rotación llaves) | Ausente          | Alto    | No se indica cifrado en reposo ni rotación automática de claves.                                  |
| Tamper-evidence auditoría (hash encadenado)                    | Ausente          | Medio   | Logs pueden alterarse fuera de DB; falta hashing encadenado.                                      |
| Limpieza/retención datos (archival jobs)                       | Ausente          | Medio   | No hay política de retención automatizada.                                                        |
| Etiquetado fiscal multi-jurisdicción                           | Ausente          | Bajo    | Impuestos simples; sin multi-jurisdicción.                                                        |
| Forecast avanzado (ML estacional, safety stock dinámico)       | Parcial          | Medio   | Stockout forecast básico; falta estacionalidad y ABC automatizado.                                |
| Gestión energética / huella carbono inventario                 | Ausente          | Bajo    | No contemplado (puede ser opcional futuro).                                                       |

## 3. Brechas clasificadas

### Críticas (impactan operaciones core / escalabilidad inmediata)

1. Kitting / BOM / ensamblaje y desensamblaje.
2. Reservas de stock (allocations) y backorders formales.
3. Múltiples métodos de valoración (FIFO/LIFO/Standard) + multi-moneda.
4. Conteos cíclicos y sesiones de inventario estructuradas.

### Altas

5. Caducidades y FEFO automático.
6. Seguridad avanzada: cifrado en reposo y rotación de llaves.
7. Calidad y cuarentena (hold de inspección) con estados técnicos.
8. Lead time proveedor + fill rate + SLA dinámicos.
9. Tamper-evidence de auditoría (hash chain / Merkle).

### Medias

10. RMA proveedor con numeración y workflow (RECEIVED/PENDING/CLOSED).
11. Unidades de medida y conversiones (paquete, caja, unidad, peso).
12. Políticas de retención y archivado (purga segura, pseudonimización).
13. Tracing distribuido (OpenTelemetry) y panel SLO/alertas.
14. Webhooks / integraciones (eventos inventario/ventas) y suscripciones.
15. Multi-jurisdicción fiscal (impuestos compuestos).
16. Forecast avanzado (estacionalidad, safety stock dinámico, clasificación ABC automática).
17. Pruebas de carga, resiliencia (chaos) y property-based.

### Bajas

18. UX offline completo (PWA con cola local extendida a lectura) más atajos teclado POS.
19. Métricas sostenibilidad / huella carbono.
20. Etiquetado GS1 / códigos de barras auto-generados.

## 4. Recomendaciones por prioridad

| Nº  | Acción                                            | Tipo               | Flag sugerido                     | Justificación                                           |
| --- | ------------------------------------------------- | ------------------ | --------------------------------- | ------------------------------------------------------- |
| 1   | Introducir entidad `bom` + `assembly_orders`      | Backend            | SOFTMOBILE_ENABLE_ASSEMBLY        | Permite kits y manufactura ligera; mejora trazabilidad. |
| 2   | Crear `stock_reservations` y estados backorder    | Backend/Frontend   | SOFTMOBILE_ENABLE_RESERVATIONS    | Evita sobreventa y soporta pedidos diferidos.           |
| 3   | Implementar motor de costo FIFO/LIFO opcional     | Servicio/migración | SOFTMOBILE_ENABLE_COST_METHODS    | Flexibilidad contable; cumplimiento normativo.          |
| 4   | Módulo `cycle_counts` con sesiones y aprobación   | Backend/Frontend   | SOFTMOBILE_ENABLE_CYCLE_COUNTS    | Control físico periódico y reducción de desviaciones.   |
| 5   | Añadir expiración (`expiry_date`) y FEFO picking  | Modelo/servicio    | SOFTMOBILE_ENABLE_FEFO            | Reducción de pérdida por caducidad.                     |
| 6   | Cifrado de campos sensibles (PII, tokens)         | Infra/ORM          | SOFTMOBILE_ENABLE_DATA_ENCRYPT    | Refuerza seguridad y cumplimiento.                      |
| 7   | Estados QC (`quarantine`, `inspection_passed`)    | Modelo/flujo       | SOFTMOBILE_ENABLE_QC              | Asegura calidad y evita liberar stock defectuoso.       |
| 8   | Métricas proveedor: lead time promedio, fill rate | CRUD/analytics     | SOFTMOBILE_ENABLE_VENDOR_METRICS  | Optimiza reabastecimiento y negociación.                |
| 9   | Auditoría inmutable: hash encadenado en logs      | Servicio           | SOFTMOBILE_ENABLE_IMMUTABLE_AUDIT | Fortalece evidencia forense.                            |
| 10  | Workflow RMA proveedor con PDF y estados          | Backend/UI         | SOFTMOBILE_ENABLE_RMA             | Formaliza devoluciones y reduce pérdidas.               |
| 11  | Tabla `units_of_measure` + conversiones           | Modelo             | SOFTMOBILE_ENABLE_UOM             | Escala a empaques y peso estándar.                      |
| 12  | Jobs de retención + anonimización PII             | Servicio           | SOFTMOBILE_ENABLE_RETENTION       | Cumplimiento privacidad y reducción de datos antiguos.  |
| 13  | OpenTelemetry + SLO panel (error rate, latency)   | Observabilidad     | SOFTMOBILE_ENABLE_OTEL            | Mejora diagnóstico producción.                          |
| 14  | Webhooks / suscripciones (`/events/*`)            | Integración        | SOFTMOBILE_ENABLE_WEBHOOKS        | Facilita ecosistema externo (ERP, BI).                  |
| 15  | Catálogo impuestos multi-jurisdicción             | Modelo/servicio    | SOFTMOBILE_ENABLE_MULTI_TAX       | Expansión geográfica.                                   |
| 16  | Forecast avanzado (ARIMA/LSTM opcional)           | Servicio/analytics | SOFTMOBILE_ENABLE_ADV_FORECAST    | Optimiza stock y capital inmovilizado.                  |
| 17  | Pruebas carga/chaos (locust + fault injection)    | QA                 | SOFTMOBILE_ENABLE_PERF_TESTS      | Garantiza resiliencia y escalabilidad.                  |
| 18  | PWA offline extendido + atajos POS                | Frontend           | SOFTMOBILE_ENABLE_OFFLINE_UI      | Mejora experiencia y continuidad operativa.             |
| 19  | Huella carbono / métricas sostenibilidad          | Analytics          | SOFTMOBILE_ENABLE_SUSTAINABILITY  | Valor agregado ESG futuro.                              |
| 20  | Generación y validación códigos GS1               | Utilidad           | SOFTMOBILE_ENABLE_BARCODE         | Mejora automatización logística.                        |

## 5. Riesgos si no se abordan

- Sobreventa y pérdidas: ausencia de reservas/backorders.
- Limitaciones contables y auditoría: solo costo promedio sin FIFO/LIFO.
- Incremento de merma: falta FEFO y expiración sistemática.
- Vulnerabilidad legal/compliance: sin retención/anonimización ni cifrado selectivo.
- Falta de escalabilidad operacional: sin cycle counts estructurados la precisión de stock puede degradarse.
- Dificultad de integración externa: carencia de webhooks y UoM convierte integraciones en desarrollos ad hoc.

## 6. Plan de ejecución sugerido (3 fases)

1. Fase Integridad Operativa (Criticos/Altos): BOM/assembly, reservas/backorders, cycle counts, costo FIFO/LIFO, expiraciones FEFO, cifrado básico.
2. Fase Optimización & Calidad: QC/quarantine, vendor metrics avanzadas, RMA workflow, UoM, auditoría inmutable, retención datos.
3. Fase Analítica & Integración: forecast avanzado, OpenTelemetry + SLO, webhooks, multi-tax, PWA offline extendida, sustainability & barcode.

Cada feature con flag propio; mantener v2.2.0 y rutas nuevas evitando romper integraciones existentes.

## 7. Métricas de éxito por bloque

- Ensamblaje/BOM: tiempo medio armado kit, % exactitud componentes vs. teórico.
- Reservas: % ventas con reserva cumplida, reducción cancelaciones por stock.
- Cycle counts: desviación promedio antes/después, tiempo ciclo cierre y aprobación.
- Cost methods: divergencia valor contable vs. promedio; reporte auditoría FIFO/LIFO.
- FEFO: reducción merma por caducidad trimestral.
- Cifrado: porcentaje campos sensibles cifrados; pruebas de rotación llaves exitosas.
- Forecast: reducción stockout y sobrestock (% capital inmovilizado).

## 8. Consideraciones de implementación

- Mantener abstracción de costo: `CostStrategy` interfaz (AVERAGE, FIFO, LIFO, STANDARD) con fallback actual.
- Outbox ampliado: incluir tipo de evento (assembly_created, reservation_allocated) para sincronización distribuida.
- Auditoría inmutable: añadir hash de registro (`prev_hash`, `record_hash`) en `audit_logs` sin romper esquema previo (campos nuevos opcionales).
- Retención: job nocturno que archiva logs > N días en almacenamiento comprimido (sin borrar sin confirmación corporativa) + pseudonimiza PII.
- UoM: árbol de conversión (caja -> unidad) + validación en movimientos, compras y ventas.

## 9. Próximos pasos inmediatos

1. Definir flags y esquemas iniciales (`CostStrategy`, `Reservation`, `BOM`).
2. Esbozar migraciones neutrales (tablas nuevas sin tocar versión).
3. Prototipo cycle counts: `count_sessions`, `count_entries` + estados `OPEN/COUNTING/RECONCILED/CLOSED`.
4. Documento técnico de costo avanzado y plan de pruebas comparativas.

## 10. Cierre

El sistema actual está maduro en operaciones base y capa de seguridad/auditoría. Las brechas críticas se concentran en manufactura ligera (kits/BOM), reservas/backorders, métodos de costo alternativos y procesos avanzados de inventario físico. La hoja de ruta propuesta prioriza impacto operativo y cumplimiento manteniendo compatibilidad con v2.2.0 mediante flags.

---

Generado automáticamente (sesión IA) — Softmobile 2025 v2.2.0 (sin cambios de versión).
