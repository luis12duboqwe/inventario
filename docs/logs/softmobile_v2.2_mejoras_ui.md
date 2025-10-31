# Reporte de mejoras UI — Softmobile 2025 v2.2.0

## Resumen de ajustes aplicados
- Se añadieron encabezados consistentes con iconografía y subtítulos descriptivos en cada módulo del dashboard mediante el componente `ModuleHeader`.
- Se incorporó `LoadingOverlay` y animaciones *fade-in* en secciones críticas (inventario, analítica, reparaciones, sincronización y usuarios) para mostrar estados de carga y evitar saltos bruscos.
- Se actualizó la paleta de botones con variantes `btn--primary`, `btn--secondary`, `btn--ghost` y `btn--link`, destacando acciones principales (Registrar, Guardar, Sincronizar) y manteniendo accesibles exportaciones y atajos.
- Se reforzó el contraste de tarjetas secundarias y la retroalimentación visual de estados (verde/amarillo/rojo) en inventario, seguridad, sincronización y reparaciones.
- Se habilitaron exportaciones CSV/PDF activas en Analítica, Reparaciones y Sincronización, junto con micrográficos embebidos y visuales por orden en reparaciones.
- Se corrigió la gestión de usuarios asegurando recuperación desde `/users`, filtros activos y el banner global ante errores de red.
- Se optimizó la compilación de frontend mediante `manualChunks` en `vite.config.ts` para separar dependencias de gran tamaño.

## Archivos modificados
- `frontend/src/components/ModuleHeader.tsx`
- `frontend/src/components/LoadingOverlay.tsx`
- `frontend/src/api.ts`
- `frontend/src/modules/**/*` (páginas y componentes de inventario, operaciones, analítica, seguridad, sincronización, reparaciones y usuarios)
- `frontend/src/modules/dashboard/**/*`
- `frontend/src/styles.css`
- `frontend/vite.config.ts`
- `README.md`

## Tiempo estimado de ejecución
- 6 horas de implementación y pruebas manuales.

> Nota: No se modificó la versión del producto (permanece en v2.2.0) y se respetaron los endpoints existentes.
