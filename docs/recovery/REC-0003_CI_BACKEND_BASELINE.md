# REC-0003 / REC-0004 — CI y baseline backend

## Alcance

Solo `luis12duboqwe/inventario`.

## Baseline

La recuperación del CI parte de `main@1abe713164b3c2054bda7149d518139062fac051`, después de cerrar REC-0002.

## CI histórico encontrado

`.github/workflows/ci.yml` contenía dos workflows completos concatenados en un mismo archivo, con decisiones contradictorias:

- Node 20 en una mitad y Node 18 en la otra;
- `npm install --legacy-peer-deps` en una ruta y `npm ci` en otra;
- comandos de pytest distintos;
- nombres y versiones de actions diferentes.

REC-0003 lo reemplaza por un único pipeline canónico con backend y frontend separados.

## Primera ejecución del CI canónico

Entorno backend: Ubuntu GitHub Actions, Python 3.11.16.

Resultados confirmados:

- instalación de `requirements.txt`: **PASS**;
- `python -m compileall -q backend`: **FAIL**;
- importación FastAPI, colección y tests no se ejecutaron porque compileall bloqueó el job.

### Blocker reproducible

`backend/app/crud_legacy.py`, línea 3946:

```text
IndentationError: unexpected indent
```

La función afectada es `resolve_price_for_device`. El archivo actual perdió un bloque de consulta/priorización y dejó un fragmento huérfano antes de `return 3`.

## Recuperación de la implementación

La implementación completa fue localizada en el historial del mismo repositorio, en el antiguo `backend/app/crud.py`. El bloque histórico:

1. construye el filtro de vigencia `valid_from` / `valid_until`;
2. consulta `PriceListItem` unido a `PriceList`;
3. filtra por dispositivo y listas activas;
4. prioriza alcance en este orden:
   - sucursal + cliente;
   - cliente;
   - sucursal;
   - global;
5. mantiene después la comparación de `priority` y `updated_at` que todavía existe en el archivo actual.

La restauración usa esa implementación histórica exacta y no una reescritura inventada.

## Validación requerida después de restaurar

- compileall backend;
- import `backend.app.main`;
- `pytest --collect-only -q backend/tests`;
- smoke HTTP/bootstrap/auth;
- `backend/tests/test_price_lists.py` para confirmar la función restaurada;
- suite backend completa.

## Frontend en el CI canónico

Se mantiene el baseline ya probado en REC-0002:

- Node 20.19;
- lockfile reproducible;
- `npm ci`;
- ESLint;
- Vitest;
- build Vite/PWA.

`typecheck:strict` permanece visible como deuda REC-0005 (#764) y no se oculta desactivando reglas.
