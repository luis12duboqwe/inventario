# REC-0002 — Baseline del frontend

## Alcance

Solo `luis12duboqwe/inventario`.

Este documento registra decisiones de recuperación del toolchain. No declara que el frontend esté terminado ni que todas sus pruebas pasen.

## Causa confirmada del daño

El historial del propio repositorio muestra múltiples actualizaciones automáticas de dependencias que se fusionaron sobre un manifiesto que ya había recibido cambios concurrentes.

Hallazgos principales:

- Antes del merge del PR #729, `react` y `react-dom` estaban ambos en 18.3.1.
- PR #729 actualizó `react-dom` 18.3.1 → 19.2.0 y `@types/react-dom` 18.x → 19.2.3 sin actualizar `react`, dejando majors incompatibles.
- PR #727 añadió `@vitejs/plugin-react` 5.1.1 sin sustituir una entrada 4.x ya existente, generando una clave duplicada.
- PR #728 actualizó Recharts 3.4.1 → 3.5.1 de forma independiente.
- PR #730 actualizó ESLint 9.39.0 → 9.39.1.
- Con el paso de más merges, `package.json` y la sección raíz de `package-lock.json` terminaron con claves duplicadas y una coma ausente.

Por tanto, el problema no se corrige revirtiendo el último PR ni copiando `inventario-main`.

## Baseline elegido

Se conserva React 18 porque:

1. es la línea utilizada por el proyecto antes del merge defectuoso;
2. ReactDOM 18.3.1 aparece emparejado correctamente con React 18.3.1 en el lockfile histórico;
3. no existe evidencia de una migración deliberada del código a React 19;
4. la actualización a ReactDOM 19 provino de Dependabot y no incluyó React.

### Runtime directo

- `@tanstack/react-query` 5.45.0
- `axios` 1.13.2
- `framer-motion` 12.23.24
- `lucide-react` 0.344.0
- `qrcode` 1.5.4
- `react` 18.3.1
- `react-dom` 18.3.1
- `react-hook-form` 7.67.0
- `react-is` 18.3.1
- `react-router-dom` 6.23.1
- `recharts` 3.5.1
- `sonner` 2.0.7

### Toolchain directo

- Node >=20.19.0
- Vite 7.1.12
- `@vitejs/plugin-react` 5.1.1
- TypeScript 5.4.0
- Vitest 4.0.6
- `@vitest/coverage-v8` 4.0.14
- ESLint 9.39.1
- Playwright 1.57.0
- `@playwright/test` 1.57.0
- `vite-plugin-pwa` 1.2.0

Las dependencias directas se fijan sin `^` durante la recuperación para evitar que regenerar el lockfile meses después introduzca upgrades silenciosos.

## React Router

El frontend actual utiliza APIs y estructura de React Router v6. La actualización automática a v7 no se adopta dentro de REC-0002. Una migración de router, si se desea posteriormente, debe ser un cambio independiente con pruebas de navegación.

## PWA

`frontend/vite.config.ts` importa `vite-plugin-pwa`, por lo que la dependencia se mantiene explícitamente en `frontend/package.json`. La existencia adicional de un `package.json` raíz con esa dependencia se revisará como deuda de estructura en una tarea posterior; REC-0002 no elimina todavía archivos raíz sin analizar sus consumidores.

## Lockfile

Para evitar partir del archivo corrupto, se recuperó inicialmente el blob del último lockfile coherente anterior a las actualizaciones defectuosas. Sobre esa base, GitHub Actions reconcilia `package-lock.json` usando el manifiesto de recuperación.

El lockfile final solo se acepta si:

- es JSON válido;
- refleja exactamente las dependencias directas del manifiesto;
- resuelve React y ReactDOM al mismo major esperado;
- permite `npm ci` en Node 20.19;
- permite ejecutar typecheck, tests y build sin fallar por instalación.

## Validación pendiente

Después de cerrar la reconciliación del lockfile se ejecutarán como mínimo:

```text
npm ci
npm run typecheck:strict
npm run lint
npm run test
npm run build
```

Los fallos de código descubiertos por esas pruebas no deben ocultarse relajando peer dependencies o desactivando checks; se registrarán y corregirán de forma separada cuando corresponda.
