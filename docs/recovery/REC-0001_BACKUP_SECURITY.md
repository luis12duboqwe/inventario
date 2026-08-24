# REC-0001 — Contención de seguridad de respaldos

## Alcance

Este documento aplica únicamente a `luis12duboqwe/inventario`.

## Incidente identificado

El árbol histórico del repositorio contenía `backups/.backup.key` junto con artefactos de respaldo generados durante ejecución. El repositorio es público, por lo que la llave debe considerarse comprometida aunque se elimine del HEAD actual.

No se registra ni reproduce el valor de la llave en este documento.

## Medidas aplicadas en la rama de recuperación

- `backups/.backup.key` fue retirado del árbol actual.
- `.gitignore` ahora excluye `backups/`, `*.key` y `*.backup.key`.
- No se generó ni se añadió una llave de reemplazo al repositorio.

## Comportamiento verificado del código

`backend/app/services/encryption.py` usa `_read_or_create_key`: si la ruta configurada para la llave no existe, crea el directorio, genera una nueva llave Fernet, la escribe localmente y aplica permisos `0600`.

Por lo tanto, retirar la llave versionada no impide que una instalación limpia genere una llave propia en tiempo de ejecución.

## Consecuencia sobre respaldos históricos

Una nueva llave no puede descifrar respaldos cifrados con la llave anterior. Antes de rotar en una instalación que dependa de respaldos reales existentes se debe:

1. identificar cuáles respaldos son reales y cuáles fueron generados para pruebas/desarrollo;
2. preservar fuera de Git cualquier respaldo real que deba conservarse;
3. validar una restauración o exportación con la llave anterior en un entorno controlado;
4. generar una nueva llave local fuera del repositorio;
5. crear respaldos nuevos con la llave nueva;
6. comprobar restauración con la nueva llave;
7. retirar de operación la llave anterior.

## Historia Git

Eliminar el archivo del HEAD **no elimina su contenido de commits anteriores**. El saneamiento completo del historial debe ejecutarse como una tarea separada porque requiere reescritura de historia y puede afectar ramas, PRs, clones y referencias existentes.

Antes de una reescritura se debe:

- confirmar si los artefactos contienen datos reales o únicamente datos de prueba;
- inventariar ramas/tags que deban conservarse;
- crear una copia offline del repositorio;
- coordinar el force-push y reclonado posterior;
- volver a ejecutar escaneo de secretos sobre toda la historia reescrita.

## Artefactos de `backups/`

Los archivos ya versionados en ese directorio no se borran de forma masiva en esta primera corrección. Se clasificarán antes como:

- runtime/producción;
- datos de prueba;
- fixture necesaria;
- documentación;
- obsoleto.

Solo los runtime/obsoletos serán retirados del árbol después de confirmar que no son dependencias de pruebas.

## Criterio de cierre de REC-0001

REC-0001 puede cerrarse cuando:

- no exista ninguna llave de backup en el HEAD candidato;
- Git impida agregar accidentalmente nuevas llaves/backups runtime;
- los artefactos existentes hayan sido clasificados;
- cualquier fixture necesaria se haya movido a una ubicación explícita de pruebas y sanitizado;
- exista evidencia de generación/restauración con una llave local nueva;
- el riesgo de historia Git haya sido resuelto o registrado como issue separado con decisión explícita.
