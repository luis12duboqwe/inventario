# Plan técnico iterativo — Softmobile 2025 v2.2.0

Este documento resume el estado actual de la plataforma tras la iteración dedicada al módulo de reparaciones y traza los siguientes pasos para completar la hoja de ruta corporativa sin alterar la versión base.

## Tablas SQL incorporadas

- `repair_orders`: registra las órdenes de servicio por sucursal con campos `cliente`, `dispositivo`, `tipo_dano`, `tecnico`, `estado`, `costo`, `piezas_usadas`, `fecha_inicio`, `fecha_entrega`, `notas`, `created_at` y `updated_at`. Cada registro está asociado a una tienda (`store_id`) y admite auditoría completa mediante `AuditLog`.

## Endpoints FastAPI disponibles

| Ruta | Método | Descripción |
| --- | --- | --- |
| `/repairs` | GET | Lista órdenes filtrando por sucursal y estado, solo para roles de reporte. |
| `/repairs` | POST | Crea órdenes de reparación exigiendo cabecera `X-Reason` y permisos de gestión. |
| `/repairs/{id}` | GET | Recupera el detalle de una orden específica. |
| `/repairs/{id}` | PATCH | Actualiza estado, costos, piezas y fechas con motivo corporativo obligatorio. |
| `/repairs/{id}` | DELETE | Cancela/borra la orden con auditoría y motivo. |
| `/repairs/{id}/pdf` | GET | Genera PDF de diagnóstico en tema oscuro usando ReportLab. |

## Sincronización híbrida

- La cola `sync_outbox` ya reconoce la prioridad `repair_order` (nivel NORMAL). Falta extender los disparadores para que cada creación/actualización genere eventos híbridos y aparezcan en el panel "Sincronización avanzada".
- Próximo paso: añadir pruebas de resiliencia con tiendas desconectadas que repliquen órdenes de reparación y validen la resolución *last-write-wins*.

## Frontend planeado

- Crear `RepairOrders.tsx` con tabla filtrable por estado, formulario modal y disparo de PDF.
- Integrar indicadores de estado (🟡 Pendiente, 🟠 En reparación, 🟢 Listo, ⚪ Entregado) y soporte responsive.
- Reutilizar el contexto de motivos (`DashboardContext`) para enviar `X-Reason` en cada acción.

## Roadmap inmediato

1. Implementar los módulos de **Clientes** y **Proveedores** (modelos, CRUD, sincronización y paneles React con exportación CSV).
2. Diseñar el **POS avanzado** con métodos de pago múltiples, control de caja y recibos imprimibles.
3. Construir la **gestión visual de usuarios y permisos**, incluyendo endpoint `/users/permissions` y middleware de autorización granular.
4. Extender la sincronización híbrida para ventas, reparaciones, clientes y proveedores con prioridad y métricas por entidad.
5. Preparar el modo claro opcional para los nuevos módulos manteniendo el tema oscuro corporativo como predeterminado.

## Validaciones y pruebas

- Nuevas pruebas `backend/tests/test_repairs.py` validan el flujo completo (creación, actualización, PDF y eliminaciones) y la obligatoriedad de `X-Reason`.
- Ejecutar `pytest` tras cada iteración para asegurar compatibilidad con lotes previos A–F.

## Bitácora

- **2025-02-15** — Se integró el backend de reparaciones y se documentó el plan pendiente para clientes, proveedores y POS avanzado.
