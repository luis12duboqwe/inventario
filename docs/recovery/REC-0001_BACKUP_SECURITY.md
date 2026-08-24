# REC-0001 — Contención de seguridad de respaldos

## Alcance

Solo `luis12duboqwe/inventario`.

## Hallazgo

El repositorio público contenía `backups/.backup.key` junto con artefactos de respaldo generados durante ejecución. La llave debe considerarse comprometida aunque se retire del HEAD actual.

No se registra ni reproduce el valor de la llave en este documento.

## Medidas aplicadas

- La llave fue retirada del árbol actual de la rama REC-0001.
- `.gitignore` ahora excluye el directorio runtime `backups/`.
- No se generó ni se añadió una llave nueva al repositorio.

## Comportamiento del servicio

`backend/app/services/encryption.py` usa `_read_or_create_key`: si la ruta configurada no existe, crea el directorio, genera una nueva llave Fernet local y aplica permisos `0600`.

Por ello, una instalación limpia puede generar su propia llave fuera de Git.

## Rotación

Una nueva llave no descifra respaldos creados con la anterior. Si una instalación depende de respaldos reales existentes, antes de rotar se debe:

1. identificar qué respaldos son reales y cuáles son pruebas/desarrollo;
2. conservar fuera de Git cualquier respaldo real que deba preservarse;
3. validar restauración/exportación en un entorno controlado;
4. generar una nueva llave local fuera del repositorio;
5. crear respaldos nuevos con la llave nueva;
6. validar restauración con la llave nueva;
7. retirar la llave anterior de operación.

## Historia Git

Eliminar la llave del HEAD no la elimina de commits anteriores. El saneamiento completo de historia se tratará por separado porque implica reescritura de historia y puede afectar ramas, PRs, tags y clones.

Antes de reescribir historia se debe crear una copia offline, inventariar referencias a conservar y confirmar si los artefactos históricos contienen datos reales o únicamente datos de prueba.

## Artefactos históricos de `backups/`

No se eliminan masivamente en esta primera corrección. Primero se clasificarán como runtime, prueba, fixture necesaria, documentación u obsoleto. Después se retirarán del árbol los que no deban permanecer versionados.

## Criterio de cierre

REC-0001 se podrá cerrar cuando:

- no exista una llave de backup en el HEAD candidato;
- Git evite que nuevos artefactos runtime de backup entren por el flujo normal;
- los artefactos históricos hayan sido clasificados;
- cualquier fixture necesaria esté sanitizada y ubicada explícitamente como fixture de pruebas;
- exista evidencia de generación/restauración con una llave local nueva;
- el riesgo de la historia Git quede resuelto o registrado en una tarea separada con decisión explícita.
