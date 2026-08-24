# Plan Maestro de Recuperación — Softmobile / Inventario

## 0. Identidad inmutable del proyecto

Este plan aplica **únicamente** al repositorio:

- **Repositorio:** `luis12duboqwe/inventario`
- **Producto:** Softmobile 2025 / Inventario de Celulares
- **Rama base auditada:** `main`
- **SHA de inicio de recuperación:** `c67b4b50b98983320ec3cde88f04e1c4b04ed83f`
- **Rama de recuperación:** `recovery/softmobile-stabilization`

### Repositorios explícitamente fuera de alcance

No mezclar, copiar cambios ni asumir equivalencia con:

- `luis12duboqwe/inventario-main` — copia/snapshot histórico del mismo producto.
- `luis12duboqwe/sistema-de-inve-sand` — proyecto distinto.
- Cualquier otro repositorio del usuario.

Si una tarea, issue, PR o agente no puede confirmar que está trabajando en `luis12duboqwe/inventario`, debe detenerse antes de modificar archivos.

---

## 1. Objetivo

Recuperar el sistema existente **sin rehacerlo desde cero**, conservando todo el código útil y convirtiendo el repositorio actual en un producto mantenible, verificable y apto para uso real.

La recuperación prioriza:

1. Seguridad y protección de datos.
2. Instalación y arranque reproducibles.
3. CI confiable.
4. Identificación de funcionalidad real vs. mock/placeholder.
5. Integración frontend ↔ backend.
6. Eliminación progresiva de duplicidad y código legacy.
7. Pruebas de flujos reales de negocio.
8. Limpieza de documentación y artefactos generados.
9. Preparación de despliegue/instalador y operación.

Durante la recuperación se aplica **congelamiento funcional**: no se agregan características nuevas salvo que sean necesarias para completar un flujo ya existente o corregir una deficiencia crítica.

---

## 2. Principios de recuperación

### 2.1 El código ejecutable es la fuente de verdad

La documentación histórica puede contener afirmaciones incorrectas o desactualizadas. Ningún documento que diga “100%”, “completado” o “production ready” sustituye una validación reproducible.

### 2.2 Conservar antes de eliminar

No borrar implementaciones por parecer duplicadas. Primero se debe:

1. identificar consumidores;
2. ejecutar/pruebas correspondientes;
3. elegir implementación canónica;
4. migrar consumidores;
5. eliminar únicamente cuando exista evidencia de que ya no se usa.

### 2.3 Ninguna IA se auto-certifica

Un agente que implementa un cambio no puede declarar el sistema terminado solo por haber completado su tarea. El estado se determina por criterios de salida medibles y pruebas independientes.

### 2.4 Cambios pequeños y reversibles

Cada PR debe resolver una unidad coherente. Evitar PRs masivos que mezclen seguridad, frontend, migraciones, refactors y funciones nuevas.

### 2.5 No trabajar directamente sobre `main`

Toda corrección de recuperación debe partir de una rama y llegar a `main` mediante PR revisable.

---

## 3. Hallazgos críticos iniciales ya confirmados

Estos hallazgos se consideran hechos de partida y deben verificarse nuevamente durante las fases correspondientes.

### REC-CRIT-001 — Manifiesto frontend inválido

`frontend/package.json` contiene dependencias duplicadas/incompatibles y sintaxis JSON inválida. Ejemplos observados:

- React/React DOM con versiones 18 y 19 mezcladas.
- `@vitejs/plugin-react` repetido con versiones diferentes.
- ESLint repetido.
- Recharts repetido.
- Falta de coma en el objeto de dependencias.

`frontend/package-lock.json` refleja el mismo daño.

**Impacto:** instalación/build reproducible del frontend bloqueados.

### REC-CRIT-002 — CI concatenado/inconsistente

`.github/workflows/ci.yml` contiene dos definiciones de workflow pegadas en un mismo archivo, con configuraciones contradictorias (incluyendo versiones diferentes de Node y Actions).

**Impacto:** CI no puede tomarse como evidencia confiable de salud del sistema.

### REC-CRIT-003 — Llave de backup versionada en repositorio público

Existe `backups/.backup.key` dentro del repositorio y además se encuentran artefactos de backup JSON/SQL/PDF y directorios críticos.

La propia documentación del proyecto indica que esa llave debe mantenerse fuera del repositorio.

**Impacto:** la llave debe considerarse comprometida. Se requiere rotación y saneamiento de artefactos.

### REC-HIGH-004 — Funcionalidad frontend parcialmente simulada

Se han confirmado páginas con `TODO(wire)`, placeholders o datos de ejemplo, entre ellas:

- cierre de caja;
- conteo cíclico;
- Kardex / stock ledger;
- ajustes de inventario;
- detalle de órdenes/pagos en ciertas vistas.

**Impacto:** una pantalla visible no equivale a funcionalidad terminada.

### REC-HIGH-005 — `crud_legacy.py` sigue siendo dependencia estructural

Aunque existen módulos CRUD especializados, `backend/app/crud/__init__.py` todavía importa `crud_legacy` mediante wildcard por compatibilidad con routers existentes.

**Impacto:** la migración arquitectónica no está cerrada y existe riesgo de firmas duplicadas/overrides implícitos.

### REC-MED-006 — Documentación contradictoria

Hay documentos que declaran fases 100% terminadas mientras en el mismo árbol existen pendientes explícitos y módulos todavía conectados a legacy.

**Impacto:** el porcentaje de avance no debe derivarse de documentación histórica.

### REC-MED-007 — Debug/ruido en código sensible

Se observaron `print()` de depuración en lógica de autenticación y duplicidad de imports.

**Impacto:** higiene insuficiente y posible exposición de información de sesión en logs de desarrollo/producción.

---

## 4. Clasificación obligatoria de cada módulo

Cada área auditada debe quedar en exactamente uno de estos estados:

- **FUNCIONA:** implementación conectada, probada y sin bloqueo conocido.
- **REPARAR:** existe y está conectada, pero tiene fallos/regresiones/deuda que impiden confiar en ella.
- **TERMINAR:** existe parcialmente, con mocks/placeholders/TODO o integración incompleta.
- **ELIMINAR:** duplicado, obsoleto o no utilizado, con evidencia suficiente para retirarlo.
- **NO EVALUADO:** aún no se dispone de evidencia.

No usar “parece terminado”.

---

## 5. Fases obligatorias

## Fase R0 — Contención y trazabilidad

### Objetivo
Evitar pérdida de información, nuevos daños y mezcla de proyectos.

### Trabajo

- Mantener el SHA inicial documentado.
- Trabajar en `recovery/softmobile-stabilization`.
- Crear tracking de recuperación.
- Identificar secretos/llaves/artefactos generados versionados.
- Definir exclusiones de Git apropiadas.
- Preparar procedimiento de rotación de la llave de backup.
- No borrar historial todavía sin evaluar impacto de datos reales.

### Criterio de salida

- Identidad del repo fijada.
- Rama de recuperación creada.
- Plan maestro versionado.
- Riesgos de secretos clasificados y acciones definidas.

---

## Fase R1 — Baseline reproducible

### Objetivo
Conseguir una instalación limpia y comandos deterministas.

### Backend

- fijar versión soportada de Python;
- revisar `requirements.txt` y duplicidades;
- crear entorno limpio;
- importar `backend.app.main`;
- ejecutar migraciones/base limpia;
- levantar FastAPI;
- comprobar `/health`;
- registrar errores exactos.

### Frontend

- reconstruir `frontend/package.json` sin perder dependencias realmente usadas;
- tomar `inventario-main` únicamente como referencia histórica, nunca como fuente automática de verdad;
- regenerar `package-lock.json` desde el manifiesto válido;
- fijar versión soportada de Node;
- ejecutar install, typecheck, lint, tests y build;
- corregir errores por lotes pequeños.

### CI

- reemplazar el workflow concatenado por un único CI canónico;
- ejecutar backend y frontend de forma equivalente al entorno local;
- no permitir merge si los checks mínimos fallan.

### Criterio de salida

Desde un checkout limpio deben poder ejecutarse instrucciones documentadas que produzcan:

- backend arrancable;
- frontend compilable;
- CI sintácticamente válido;
- comandos de prueba reproducibles.

---

## Fase R2 — Inventario técnico real

### Objetivo
Mapear todo el producto antes de refactorizar en profundidad.

Auditar, como mínimo:

- autenticación y sesiones;
- usuarios, roles y permisos;
- sucursales/almacenes;
- inventario, IMEI/seriales y valuación;
- compras/proveedores;
- ventas/POS;
- caja;
- clientes/cuentas por cobrar/créditos;
- devoluciones;
- garantías;
- reparaciones/RMA;
- transferencias;
- sincronización/offline;
- reportes/analítica;
- backups/restauración;
- importación/exportación;
- DTE/facturación e integraciones externas;
- observabilidad/logs;
- instaladores/despliegue.

Para cada módulo documentar:

- rutas frontend;
- endpoints backend;
- modelos/tablas;
- schemas;
- servicios/CRUD;
- pruebas existentes;
- datos simulados;
- TODO/FIXME/placeholders;
- duplicados/legacy;
- estado FUNCIONA/REPARAR/TERMINAR/ELIMINAR.

### Criterio de salida

Existe una matriz canónica completa y ningún módulo visible queda sin clasificar.

---

## Fase R3 — Arquitectura canónica y reducción de legacy

### Objetivo
Eliminar gradualmente la arquitectura acumulativa producida por iteraciones de agentes.

### Reglas

- elegir una sola implementación canónica por dominio;
- prohibir nuevas funciones en `crud_legacy.py`;
- migrar consumidores antes de eliminar legacy;
- eliminar wildcard imports cuando sea seguro;
- separar dominio/servicios/persistencia donde el beneficio sea claro;
- evitar refactors cosméticos masivos;
- mantener compatibilidad externa solo cuando exista consumidor real.

### Criterio de salida

- imports deterministas;
- duplicados principales retirados;
- legacy reducido a cero o a una lista explícita y justificada;
- pruebas de regresión cubren cada migración.

---

## Fase R4 — Flujos de oro del negocio

### Objetivo
Demostrar que el sistema sirve para operar una tienda real.

### GOLD-01 Compra → inventario → venta

1. Crear/seleccionar sucursal.
2. Crear proveedor.
3. Registrar compra.
4. Ingresar equipo con IMEI/serial.
5. Verificar stock y costo.
6. Vender por POS.
7. Registrar pago.
8. Descontar stock exactamente una vez.
9. Emitir comprobante.
10. Generar auditoría.

### GOLD-02 Venta → devolución/reembolso/crédito

1. Encontrar venta.
2. Registrar devolución válida.
3. Actualizar inventario según estado del equipo.
4. Registrar reembolso/crédito.
5. Mantener trazabilidad financiera.
6. Auditar la operación.

### GOLD-03 Transferencia entre sucursales

1. Crear transferencia A → B.
2. Reservar/sacar stock de A según regla canónica.
3. Marcar EN_TRANSITO.
4. Recibir en B.
5. Evitar duplicación/pérdida de IMEI.
6. Confirmar stock final en ambas tiendas.

### GOLD-04 Caja diaria

1. Abrir caja.
2. Registrar ventas por efectivo/tarjeta/transferencia.
3. Registrar movimientos autorizados.
4. Calcular teórico.
5. Capturar contado.
6. Mostrar diferencia.
7. Cerrar con permisos/auditoría.
8. Generar comprobante/reporte.

### GOLD-05 Backup → restauración

1. Crear datos controlados.
2. Generar backup cifrado.
3. Validar artefacto.
4. Restaurar en entorno limpio.
5. Confirmar integridad funcional y referencial.

### Criterio de salida

Cada GOLD debe tener prueba E2E o de integración reproducible y evidencia de ejecución exitosa.

---

## Fase R5 — Completar UI inconclusa

Con el backend y contratos estabilizados:

- conectar cierre de caja;
- conectar conteo cíclico;
- conectar Kardex;
- conectar ajustes;
- reemplazar datos de ejemplo por servicios reales;
- eliminar botones que solo simulan éxito;
- revisar permisos y mensajes de error;
- asegurar estados loading/empty/error/success.

### Criterio de salida

No quedan rutas de producción con placeholders operativos o datos ficticios salvo modo demo explícito.

---

## Fase R6 — Calidad, seguridad y datos

- escaneo de secretos;
- rotación de llaves comprometidas;
- revisar JWT/cookies/rate limiting;
- revisar autorización por endpoint;
- validar stock negativo y concurrencia;
- validar unicidad IMEI/serial;
- verificar transacciones atómicas;
- revisar migraciones;
- limpiar debug prints;
- revisar dependencias vulnerables;
- proteger backups y datos de clientes;
- pruebas de restauración;
- pruebas de errores y rollback.

### Criterio de salida

No existen hallazgos críticos/altos abiertos que afecten confidencialidad, integridad de inventario, dinero o autenticación.

---

## Fase R7 — Limpieza final del repositorio

Solo después de las fases anteriores:

- retirar código muerto;
- eliminar archivos accidentales/notebooks no requeridos;
- sacar backups generados del control de versiones;
- depurar documentos históricos redundantes;
- consolidar README y manuales canónicos;
- eliminar marcadores PACKxx cuando ya no aporten trazabilidad útil;
- revisar nombres inconsistentes;
- reducir archivos excesivamente grandes cuando tenga beneficio real;
- dejar un árbol comprensible para un nuevo desarrollador.

---

## Fase R8 — Release candidata

### Validación final desde cero

En un entorno limpio:

1. checkout;
2. configuración desde `.env.example`;
3. instalación backend;
4. migraciones;
5. instalación frontend;
6. build;
7. suite backend;
8. suite frontend;
9. E2E GOLD;
10. instalación/arranque en Windows si ese es el objetivo de distribución;
11. backup y restauración;
12. smoke test de operación.

### Definición de “terminado”

El producto solo puede considerarse finalizado si:

- instalación limpia documentada funciona;
- CI está verde sobre el commit candidato;
- no hay secretos/llaves de ejecución en Git;
- no hay rutas productivas con mocks/placeholders operativos;
- flujos GOLD pasan;
- inventario y dinero mantienen integridad ante errores;
- permisos están probados;
- backup/restauración están probados;
- documentación canónica coincide con el código;
- los riesgos restantes son bajos y están documentados.

---

## 6. Protocolo obligatorio para agentes IA

Antes de modificar código, todo agente debe:

1. confirmar repositorio `luis12duboqwe/inventario`;
2. confirmar rama/PR objetivo;
3. leer este plan;
4. localizar tests y consumidores del código a cambiar;
5. describir el fallo concreto que pretende resolver.

Durante el cambio:

- no añadir funciones fuera del alcance;
- no crear una segunda implementación si existe una reparable;
- no introducir mocks en rutas productivas;
- no cambiar versiones masivamente sin justificación;
- no borrar legacy sin migrar consumidores;
- no editar `main` directamente;
- no agregar secretos, bases de datos o backups al repositorio.

Antes de declarar una tarea completada:

- ejecutar pruebas relevantes;
- ejecutar build/typecheck si toca frontend;
- registrar comandos y resultado;
- comprobar diff por cambios accidentales;
- actualizar la matriz de recuperación si cambia el estado de un módulo.

Frases como “100% listo”, “production ready” o “completamente terminado” están prohibidas sin cumplir la Definición de Terminado de este documento.

---

## 7. Orden de ejecución inmediato

1. **REC-0001** Contención de secretos/backups y política `.gitignore`.
2. **REC-0002** Reparar manifiestos frontend y fijar toolchain.
3. **REC-0003** Reconstruir CI canónico.
4. **REC-0004** Obtener baseline backend y suite inicial.
5. **REC-0005** Obtener baseline frontend: typecheck/lint/test/build.
6. **REC-0006** Crear matriz técnica de módulos.
7. **REC-0007+** Trabajar por módulos según criticidad y dependencia.

No saltar a limpieza arquitectónica masiva antes de que R1 sea reproducible.

---

## 8. Medición de progreso

El porcentaje no se calculará por líneas de código ni por cantidad de PRs. Se ponderará por capacidades verificadas:

- R0 Contención y trazabilidad: 5%
- R1 Baseline reproducible: 15%
- R2 Inventario técnico: 10%
- R3 Arquitectura/legacy: 15%
- R4 Flujos GOLD: 25%
- R5 UI completa: 10%
- R6 Calidad/seguridad/datos: 10%
- R7 Limpieza final: 5%
- R8 Release candidata: 5%

Un porcentaje solo aumenta cuando se cumple el criterio de salida de trabajo verificable; no por crear documentación o código sin ejecutar.
