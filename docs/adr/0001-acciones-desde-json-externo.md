# ADR 0001: Acciones declaradas en JSON externo

- **Estado:** Propuesto
- **Fecha:** 2026-11-09

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

Esta decisión es consciente de que la configuración controla rutas y, para
acciones destructivas, puede seleccionar ficheros fuera del cwd. En el estado
actual, `borrar` acepta rutas absolutas y rutas con `../`. Por tanto, un usuario
con permisos suficientes podría borrar un fichero fuera de la carpeta que
esperaba operar. Este riesgo no es una inyección de shell, pero sí una falta
de confinamiento de rutas.

## Consecuencias

### Positivas

- Las acciones son extensibles mediante configuración.
- El motor concentra validación, parámetros, simulación y confirmación.
- Typer no duplica la definición de cada acción.
- Las funciones disponibles desde JSON están limitadas por un registro
  explícito.

### Negativas

- Un `acciones.json` no confiable puede declarar comandos externos.
- Las rutas destructivas no tienen todavía una raíz autorizada.
- El esquema de configuración pasa a ser una interfaz que debe mantenerse y
  validarse.

## Mitigación prevista

En el siguiente cambio se confinará `borrar` a una raíz autorizada, elegida
entre el cwd o una opción explícita `--base RUTA`. La validación deberá

- resolver la ruta contra esa raíz;
- rechazar traversal mediante `../`;
- rechazar rutas absolutas que queden fuera de la raíz;
- rechazar rutas de sistema y cualquier destino fuera de la raíz autorizada;
- conservar `--dry-run` y la confirmación para toda operación destructiva.

## Siguiente paso

Preparar y revisar el parche de confinamiento de `borrar`. Este ADR no incluye
ese parche ni cambia el comportamiento actual.
