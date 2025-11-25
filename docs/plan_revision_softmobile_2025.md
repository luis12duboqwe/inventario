# Revisión de implementación Softmobile 2025 v2.2.0

## Cobertura verificada
- **Unificación parcial de usuarios**: existe migración automática desde la tabla ligera `users` hacia `usuarios`, evitando duplicados y trasladando roles básicos cuando ambas tablas conviven.【F:backend/database/__init__.py†L159-L211】
- **Protección por roles y módulos**: el middleware define prefijos protegidos y mapea cada ruta a un módulo para validar acciones `view/edit/delete` en tiempo de ejecución.【F:backend/app/main.py†L147-L215】
- **Validaciones de stock y transacciones en ventas**: los endpoints de ventas usan transacciones atómicas y devuelven `409` ante stock insuficiente o IMEI ya vendido, manteniendo la consistencia de inventario.【F:backend/app/routers/sales.py†L214-L288】
- **Flujo de transferencias con estados y validaciones de stock/reservas**: las rutas de despacho, recepción y rechazo aplican revisiones de permisos y estados, devolviendo errores coherentes ante insuficiencia de inventario o reservas inválidas.【F:backend/app/routers/transfers.py†L300-L371】

## Brechas y plan de corrección
- **Borrado lógico incompleto en entidades críticas**: los modelos `User` y `Store` sólo manejan banderas de estado y cascadas, sin campos `deleted_at`, lo que expone a eliminaciones físicas de sucursales/usuarios con relaciones activas.【F:backend/app/models/__init__.py†L1019-L1044】【F:backend/app/models/__init__.py†L282-L320】
  - Incorporar campos de borrado lógico (`deleted_at`/`is_active`) en `usuarios` y `sucursales`, ajustar relaciones para evitar cascadas destructivas y actualizar endpoints DELETE a marcados lógicos.
  - Añadir migraciones y pruebas que garanticen la preservación de historiales y rechacen operaciones sobre registros desactivados.
- **Recepción de transferencias ejecutada dos veces**: el endpoint `/transfers/{id}/receive` invoca `crud.receive_transfer_order` antes y dentro del `transactional_session`, lo que puede duplicar descuentos/incrementos de stock o auditorías.【F:backend/app/routers/transfers.py†L327-L353】
  - Reestructurar la función para ejecutar una sola transición dentro de la transacción, reutilizando el resultado para la respuesta y auditoría.
  - Agregar prueba que verifique que las cantidades se actualizan exactamente una vez y que el estado final es consistente.
- **Dependencia residual de la tabla `users`**: el motor sigue esperando la coexistencia de `users` y `usuarios` para migrar registros ligeros, lo que mantiene deuda técnica y riesgo de divergencia de roles.【F:backend/database/__init__.py†L159-L211】
  - Consolidar definitivamente el modelo en `usuarios`, retirando la dependencia de la tabla ligera y sus migraciones implícitas.
  - Ajustar pruebas y endpoints para operar sólo sobre el modelo unificado, documentando el corte y agregando validaciones de integridad previas a la eliminación del legado.
