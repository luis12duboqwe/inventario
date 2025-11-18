# Importación inteligente y panel global — Softmobile 2025 v2.2.0

## Resumen del flujo

La importación inteligente parte de los archivos enviados desde el panel de inventario
(Excel o CSV). El servicio `process_smart_import` transforma el archivo en un
`ParsedFile`, detecta encabezados con `_analyze_dataset` y confirma la operación con
`_commit_import` cuando el usuario aprueba los cambios. El historial queda disponible
para auditoría junto con las advertencias que consume la pestaña de correcciones.

## Dependencias principales

- **Normalización de columnas**: Los sinónimos viven en `CANONICAL_FIELDS` y se
  complementan con patrones aprendidos vía `crud.get_known_import_column_patterns`.
- **Persistencia transaccional**: `_commit_import` depende de
  `crud.ensure_store_by_name`, `crud.create_device` y `import_validation.build_record`
  para garantizar idempotencia y trazabilidad.
- **Dashboard corporativo**: Los componentes `ActionIndicatorBar`,
  `AdminControlPanel` y `GlobalMetrics` consumen la vista previa y métricas
  publicadas por los servicios de analítica para comunicar estados al equipo
  operativo.

## Puntos de extensión

1. **Nuevos campos canónicos**: Añadir el sinónimo al diccionario
   `CANONICAL_FIELDS` y, si se requiere persistencia, extender el modelo `Device`.
   Las pruebas `test_inventory_smart_import_preview_and_commit` deberán validar el
   nuevo campo.
2. **Validaciones de estado comercial**: `_resolve_estado_comercial` admite reglas
   adicionales antes de construir `estado_comercial`. Documenta las decisiones en
   este archivo y añade aserciones a `test_inventory_smart_import_handles_overrides_and_incomplete_records`.
3. **UI del dashboard**: Para destacar nuevos indicadores basta con extender los
   `modules` o métricas consumidas por `AdminControlPanel` y `GlobalMetrics`. Los
   cambios deben replicarse en los archivos de prueba colocados en
   `frontend/src/modules/dashboard/components/__tests__/`.

## Cobertura de pruebas

- `backend/tests/test_inventory_smart_import.py` comprueba la vista previa, la
  confirmación con overrides, el registro de tiendas nuevas y la exposición de
  registros incompletos.
- `frontend/src/modules/dashboard/components/__tests__/ActionIndicatorBar.test.tsx`
  valida los mensajes hablados y estados visuales para las alertas.
- `frontend/src/modules/dashboard/components/__tests__/AdminControlPanel.test.tsx`
  inspecciona la presentación de módulos, badges y conteos de notificaciones.
- `frontend/src/modules/dashboard/components/__tests__/GlobalMetrics.test.tsx`
  asegura que los estados de carga y datos vacíos sean coherentes con los
  mensajes operativos descritos en esta documentación.
