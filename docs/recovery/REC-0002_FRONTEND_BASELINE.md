# REC-0002 — Baseline del frontend

## Alcance

Solo `luis12duboqwe/inventario`.

Este documento registra la recuperación reproducible del toolchain frontend. No declara que toda la deuda TypeScript del producto esté resuelta; esa deuda queda trazada en REC-0005 (#764).

## Causa confirmada del daño

El historial del propio repositorio muestra múltiples actualizaciones automáticas de dependencias que se fusionaron sobre un manifiesto que ya había recibido cambios concurrentes.

Hallazgos principales:

- Antes del merge del PR #729, `react` y `react-dom` estaban ambos en 18.3.1.
- PR #729 actualizó `react-dom` 18.3.1 → 19.2.0 y `@types/react-dom` 18.x → 19.2.3 sin actualizar `react`, dejando majors incompatibles.
- PR #727 añadió `@vitejs/plugin-react` 5.1.1 sin sustituir una entrada 4.x ya existente, generando una clave duplicada.
- PR #728 actualizó Recharts 3.4.1 → 3.5.1 de forma independiente.
- PR #730 actualizó ESLint 9.39.0 → 9.39.1.
- Con merges posteriores, `package.json` y la sección raíz de `package-lock.json` terminaron con claves duplicadas y una coma ausente.

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
- TypeScript 5.9.3
- Vitest 4.0.14
- `@vitest/coverage-v8` 4.0.14
- ESLint 9.39.1
- Playwright 1.57.0
- `@playwright/test` 1.57.0
- `vite-plugin-pwa` 1.2.0

Las dependencias directas se fijan sin `^` durante la recuperación para evitar upgrades silenciosos al regenerar meses después.

### Transitivas de Motion

`framer-motion` 12.23.24 permitía rangos de dependencias transitivas. Una resolución limpia en 2026 instaló `motion-dom` 12.43.0 / `motion-utils` 12.39.0 y Vitest falló porque el contrato de exports ya no coincidía con la versión histórica de Framer Motion. El último lockfile coherente del propio repositorio usaba:

- `motion-dom` 12.23.23
- `motion-utils` 12.23.6

Por ello se fijan mediante `overrides`. Con ese par los tests vuelven a ejecutar correctamente.

### Nota sobre TypeScript

El manifiesto histórico declaraba `typescript: ^5.4.0`, pero el último `package-lock.json` coherente resolvía realmente **TypeScript 5.9.3**. Fijar literalmente 5.4.0 produjo `ERESOLVE` durante una generación limpia. Se fija 5.9.3 porque es la versión efectivamente registrada en el lock histórico y satisface el peer `>=4.8.4 <6.0.0` de `@typescript-eslint/parser` 8.46.4.

### Nota sobre Vitest

`@vitest/coverage-v8` 4.0.14 exige Vitest 4.0.14 como peer. Mantener Vitest 4.0.6 generaba `ERESOLVE`, por lo que ambos quedan alineados en 4.0.14.

## React Router

El frontend actual utiliza APIs y estructura de React Router v6. La actualización automática a v7 no se adopta dentro de REC-0002. Una migración de router, si se desea posteriormente, debe ser un cambio independiente con pruebas de navegación.

## PWA

`frontend/vite.config.ts` importa `vite-plugin-pwa`, por lo que la dependencia se mantiene explícitamente en `frontend/package.json`. La existencia adicional de un `package.json` raíz con esa dependencia se revisará como deuda de estructura posterior; REC-0002 no elimina archivos raíz sin analizar sus consumidores.

## Correcciones mínimas necesarias para recuperar tests/build

Además del manifiesto se corrigieron blockers reproducibles descubiertos al validar el árbol actual:

- mock duplicado/sintácticamente roto en el test de rutas de Reparaciones;
- imports API incorrectos en `MobileWorkspace`;
- asociaciones label/control que bloqueaban ESLint;
- wrapper de Tooltip marcado como elemento interactivo sin semántica adecuada;
- dependencia dinámica del hook `useHotkeys` estabilizada.

No se ampliaron funcionalidades dentro de REC-0002.

## Lockfile

El lockfile corrupto no se reutiliza como fuente de verdad. Se fijan dependencias directas con evidencia histórica y se genera un `package-lock.json` limpio. El lock resultante congela la resolución transitiva aceptada.

## Evidencia final — 2026-08-24

Validación inmutable sobre el HEAD de recuperación, usando Node 20.19 y sin `--force` ni `legacy-peer-deps`:

- JSON de `package.json` y `package-lock.json`: **PASS**
- lockfile coincide con el manifiesto (`npm install --package-lock-only` sin diff): **PASS**
- `npm ci --ignore-scripts --no-audit --no-fund`: **PASS**
- `npm run lint`: **PASS**, 0 errores; 9 warnings no bloqueantes
- `npm run test`: **PASS**, **28 archivos / 88 tests**
- `npm run build`: **PASS**, Vite 7.1.12; PWA genera service worker y 151 entradas de precache

`npm run typecheck:strict` todavía detecta deuda previa de contratos/tipos en varias áreas. No se desactiva ni se excluyen carpetas: el baseline y los grupos de errores quedaron registrados en #764 (REC-0005), que será el frente específico para dejar ese check verde.

## Resultado REC-0002

El frontend vuelve a ser instalable, testeable y compilable desde un checkout limpio con un manifiesto y lockfile coherentes. La recuperación de dependencias queda cerrada; la deuda de tipado estricto continúa de forma explícita y separada.
