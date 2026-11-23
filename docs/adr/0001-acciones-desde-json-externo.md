# ADR 0001: Acciones declaradas en JSON externo

- **Estado:** Aceptado y aplicado
- **Fecha:** 2026-11-09 (confinamiento de rutas implementado y verificado el 2026-11-23)

## Contexto

`tareas` necesita automatizar operaciones repetitivas sin convertir cada
acción en un comando hardcodeado de Typer. El proyecto separa la interfaz del
motor y permite declarar las acciones en `acciones.json`, que el cargador
valida antes de que el motor construya sus ejecutores.

La configuración externa también permite que el conjunto de acciones cambie
sin modificar `cli.py`. Las funciones invocables siguen estando limitadas al
registro explícito de `src/tareas/acciones/internas.py`; los comandos externos
se ejecutan sin shell.

## Decisión

El motor leerá las acciones desde un JSON externo validado por
`CargadorAccionesJSON`. `cli.py` construirá dinámicamente los comandos a partir
de esa configuración y delegará la ejecución al `Motor`.

La configuración controla rutas y, en acciones destructivas, podría seleccionar
ficheros fuera del directorio esperado. Para cubrir ese riesgo, la propia
decisión obliga a confinar `borrar` a una raíz autorizada: la acción rechaza
rutas absolutas y cualquier `../` que salga de esa raíz, y conserva simulación y
confirmación. El detalle verificado se describe más abajo en «Confinamiento de
rutas».

## Consecuencias

### Positivas

- Las acciones son extensibles mediante configuración.
- El motor concentra validación, parámetros, simulación y confirmación.
- Typer no duplica la definición de cada acción.
- Las funciones disponibles desde JSON están limitadas por un registro
  explícito.

### Negativas

- Un `acciones.json` no confiable puede declarar comandos externos.
- Toda acción destructiva debe someterse al confinamiento de rutas descrito
  abajo (ya aplicado en `borrar`).
- El esquema de configuración pasa a ser una interfaz que debe mantenerse y
  validarse.

## Confinamiento de rutas (implementado y verificado)

`borrar` opera siempre contra una raíz autorizada: el directorio actual o el que
se indique con `--base RUTA`. La implementación (`src/tareas/acciones/internas.py`)
y la verificación manual del 2026-11-23 confirman que:

- rechaza **todas** las rutas absolutas (`RutaFueraDeBaseError`);
- resuelve la ruta contra la raíz y **rechaza el traversal** `../` que salga de
  ella (mediante `Path.relative_to`);
- rechaza destinos fuera de la raíz autorizada;
- trata las carpetas como caso de error (solo borra ficheros);
- conserva `--dry-run`/`--simular` y la **confirmación interactiva** (o `--si`)
  para toda operación destructiva, de modo que nada se borra sin avisar.

Consecuencia: `borrar` no puede salirse de la raíz autorizada.
