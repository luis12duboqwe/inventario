# Registro de mejoras UI y navegación — Softmobile 2025 v2.2.0

## Fecha
- 2025-10-18

## Cambios clave
- Se integró un contenedor de navegación lateral plegable y una barra superior fija con búsqueda global, ayuda rápida, control de tema y modo compacto para alinear la experiencia entre módulos (`frontend/src/modules/dashboard/layout/DashboardLayout.tsx`).
- Se creó el componente `ScrollableTable` con paginación, vista expandida y carga diferida utilizada en inventario, analítica y reparaciones para mantener tablas contenidas y con barras de desplazamiento estilizadas (`frontend/src/components/ScrollableTable.tsx`).
- Se habilitó sincronía con el buscador global dentro de Inventario y Reparaciones para reutilizar filtros y mejorar la continuidad en la navegación.
- Se adaptaron las tablas analíticas a tarjetas responsivas con paginación y gráficas en modo compacto para evitar cortes en dispositivos móviles (`frontend/src/modules/analytics/components/AnalyticsBoard.tsx`).
- Se añadió un botón flotante de "volver arriba", nuevas reglas responsivas y estados compactos en la hoja de estilos principal (`frontend/src/styles.css`).
- Se agregó un control móvil para la sidebar con backdrop animado y cierre por tecla Escape, manteniendo la compatibilidad con el estado colapsado (`frontend/src/modules/dashboard/layout/DashboardLayout.tsx`, `frontend/src/modules/dashboard/components/Sidebar.tsx`, `frontend/src/styles.css`).
- Se optimizó la vista de reparaciones con carga diferida sin solicitudes duplicadas y mensajes de error más amigables (`frontend/src/modules/repairs/components/RepairOrders.tsx`).

## Componentes nuevos
- `frontend/src/modules/dashboard/components/Sidebar.tsx`
- `frontend/src/components/ScrollableTable.tsx`
- `frontend/src/components/CompactModeToggle.tsx`
- `frontend/src/components/BackToTopButton.tsx`

## Componentes actualizados
- `frontend/src/modules/dashboard/layout/DashboardLayout.tsx`
- `frontend/src/modules/dashboard/routes.tsx`
- `frontend/src/components/Dashboard.tsx`
- `frontend/src/App.tsx`
- `frontend/src/modules/inventory/pages/InventoryPage.tsx`
- `frontend/src/modules/inventory/components/InventoryTable.tsx`
- `frontend/src/modules/repairs/components/RepairOrders.tsx`
- `frontend/src/modules/analytics/components/AnalyticsBoard.tsx`
- `frontend/src/modules/dashboard/context/DashboardContext.tsx`
- `frontend/src/styles.css`

## Tiempo estimado de ejecución
- 9 horas hombre (incluye pruebas manuales de navegación y validación visual en pantallas medianas y móviles).
