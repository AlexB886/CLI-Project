# tareas

Mi herramienta de línea de órdenes para automatizar tareas repetitivas con ficheros.

## Spec (versión 0 · 29/10/2026)
1. **Problema:** cada semana pierdo tiempo ordenando Descargas a mano.
2. **Para quién:** para mí y para mis compañeros de clase.
3. **Cómo se usa:** `tareas ORDEN [CARPETA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes disponibles:** `tareas acciones`, `tareas validar`, `tareas ejecutar NOMBRE --simular`.
6. **Mis 3 acciones (borrador):** clasificar por extensión, borrar temporales de +30 días, renombrar fotos por fecha.
7. **Nunca hará:** borrar sin preguntar ni tocar ficheros fuera de la carpeta indicada.
8. **Plataformas:** Linux primero; también Windows y macOS.
9. **Códigos de salida:** 0 bien · 1 fallo al ejecutar · 2 uso incorrecto · 3 configuración inválida.
10. **Instalación:** `uv tool install --editable .`

## Acciones declaradas en `acciones.json`

Las acciones no están hardcodeadas en Typer: se leen de `acciones.json` (raíz del repo). Cada acción declara `nombre`, `descripcion`, `tipo` (`funcion` o `comando`), `ejecutar`, `destructiva` y sus `parametros` opcionales.

```bash
tareas acciones
tareas listar ~/pruebas-tareas
tareas validar README.md
tareas ejecutar listar --param carpeta=~/pruebas-tareas
tareas ejecutar validar --param ruta=README.md
```

- `tareas listar` y `tareas validar` se registran dinámicamente desde el JSON.
- `tareas ejecutar NOMBRE` es la orden genérica para cualquier acción.
- `--dry-run` y `--simular` son sinónimos; en acciones destructivas también se pide confirmación.
- `--si` confirma automáticamente una acción destructiva (útil en scripts).
- `--acciones RUTA` usa otro fichero; es una opción global, va antes del comando.
- Si no se indica ruta, se busca `./acciones.json`, luego la raíz del proyecto (instalación editable) y `~/.config/tareas/acciones.json`.

Las funciones de Python deben estar registradas en `src/tareas/acciones/internas.py` con `@registrar("nombre")`; el motor no importa código arbitrario. Las acciones de tipo `comando` se ejecutan sin shell.
