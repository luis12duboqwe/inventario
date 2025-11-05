# Bitácora de pruebas — 2025-11-04

- Responsable: GitHub Copilot
- Commit/estado: cambios locales (rutas frontend y pruebas actualizadas)

## Resumen

- Backend (pytest): CI configurado en GitHub Actions para instalar requirements y ejecutar `pytest backend/tests`.
- Frontend (build): OK
- Frontend (tests): OK — 18 suites, 58 pruebas aprobadas.

## Detalle de ejecuciones

- npm --prefix frontend run build: OK (previa iteración)
- npm --prefix frontend run test: OK — 18/18 suites, 58/58 tests
- CI: agregado `.github/workflows/ci.yml` para correr pytest (backend) y Vitest + build (frontend) en cada push/PR.
  - Incluye comentario automático en los PR con el estado de ambos jobs.
  - Advertencias esperadas: React Router «future flags», act() en POS (no bloqueante)

## Cambios relevantes en esta iteración

- Alineación de rutas de Dashboard con componentes _Page_ para Inventario y Reparaciones (permiten pruebas con Suspense y loaders controlados por mocks).
- Corrección de prueba `OperationsPage.lazy.test.tsx` para desambiguar el enlace «Caja» cuando «Cajas» también está presente.
- Corrección de prueba `RouteErrorElement.test.tsx` usando `vi.hoisted` para evitar problemas de hoisting al mockear `services/audit`.
- CI agregado y extendido: `.github/workflows/ci.yml` (pytest + Vitest + build + comentario en PR).
- Auto-etiquetado de PRs: `.github/labeler.yml` y workflow `pr-labeler` para asignar etiquetas por rutas.
- Plantilla de PR: `.github/pull_request_template.md` con checklist de v2.2.0.
- CODEOWNERS: `.github/CODEOWNERS` para solicitar revisión por defecto.

## Notas

- Para ejecutar la suite de backend localmente:
  - pip install -r requirements.txt
  - pytest backend/tests -q

## PR relacionado

- Rama: `test/frontend-stabilizacion-v220-2025-11-04`
- Crear PR: https://github.com/luis12duboqwe/inventario/pull/new/test/frontend-stabilizacion-v220-2025-11-04

---

## Ejecución local — 2025-11-04

- Backend (pytest): PASS — 162 tests en ~94s.
  - Nota: se añadió `REFRESH_TOKEN_EXPIRE_DAYS=7` al archivo `.env` local para satisfacer la validación de `Settings` y se inyectó `DATABASE_URL=sqlite:///:memory:` al entorno de ejecución para módulos que no cargan `.env` automáticamente.
- Frontend (build): PASS — Vite 7, build completado en ~19s.
- Frontend (tests): PASS — 18 suites, 58 pruebas. Advertencias esperadas: React Router future flags y `act(...)` en POS (no bloqueantes).

### Servicios levantados — 2025-11-04

- Backend (Uvicorn): RUNNING en 0.0.0.0:8000

  - Variables de entorno usadas en arranque:
    - `DATABASE_URL=sqlite:///./softmobile_dev.db`
    - Flags Softmobile: `SOFTMOBILE_ENABLE_{CATALOG_PRO,TRANSFERS,PURCHASES_SALES,ANALYTICS_ADV,HYBRID_PREP}=1`, `SOFTMOBILE_ENABLE_2FA=0`
    - CORS/JWT/expiraciones provistos por `.env` (CORS como JSON válido)
  - Health check: `GET /docs` → 200 OK

- Frontend (Vite dev): RUNNING en 0.0.0.0:5173 (Local http://localhost:5173/)
  - Health check básico: página de inicio servida correctamente

### Cambios de UI del día

- Sucursales: se añadió modo edición en `StoresPage.tsx` (click en fila → edita; botón “Cancelar edición”), validando motivo corporativo (X-Reason ≥ 5) y refrescando lista global vía `DashboardContext.refreshStores()`.

Comandos ejecutados localmente (resumen):

- Python: `pytest -q` con `DATABASE_URL=sqlite:///:memory:`
- Node: `npm --prefix frontend install`, `npm --prefix frontend run build`, `npm --prefix frontend run test`
