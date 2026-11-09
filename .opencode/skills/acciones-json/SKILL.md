---
name: acciones-json
description: Documenta el esquema de acciones.json y cómo añadir acciones nuevas; usar al crear, revisar o modificar acciones del CLI tareas.
---

# Acciones de tareas

Usa esta skill cuando una petición afecte a `acciones.json` o solicite crear
una acción nueva para `tareas`.

## Flujo

La configuración externa sigue este flujo:

```text
acciones.json -> CargadorAccionesJSON -> Motor -> ejecutor de la acción
```

Las acciones de tipo `funcion` solo pueden invocar funciones registradas con
`@registrar("nombre")` en `src/tareas/acciones/internas.py`. Las acciones de
tipo `comando` usan una lista de argumentos y se ejecutan sin shell.

## Esquema de acciones.json

La raíz debe ser un objeto con:

```json
{
  "version": 1,
  "acciones": []
}
```

Cada elemento de `acciones` declara estos campos:

| Campo | Tipo | Obligatorio | Significado |
|---|---|---:|---|
| `nombre` | texto | sí | Identificador en minúsculas; permite números, `-` y `_`. |
| `descripcion` | texto | sí | Explicación no vacía para la ayuda del CLI. |
| `tipo` | `funcion` o `comando` | sí | Selecciona el ejecutor. |
| `ejecutar` | texto o lista de textos | sí | Función registrada si `tipo` es `funcion`; argv completo si es `comando`. Conceptualmente es la ejecución de la acción. |
| `destructiva` | booleano JSON | sí | Si es `true`, exige `--dry-run`, `--si` o confirmación. |
| `ia` | booleano/metadato | no disponible en v1 | Campo previsto para describir su relación con IA, pero el cargador actual no lo acepta. No lo añadas hasta que el esquema y `configuracion.py` lo soporten. |

También puede existir `parametros`, un objeto cuyos parámetros declaran
`tipo`, `requerido`, `por_defecto` y `ayuda`.

El campo real del JSON es `ejecutar`, no `ejecucion`. No inventes alias:
`ejecucion` sería una clave desconocida para el cargador actual.

## Añadir una acción nueva

1. Comprueba que el nombre no esté reservado (`version`, `acciones` o
   `ejecutar`) ni duplicado.
2. Define todos los campos obligatorios y usa booleanos JSON reales para
   `destructiva`, nunca cadenas como `"true"`.
3. Para `tipo: "funcion"`, implementa y registra la función antes de usarla.
4. Para `tipo: "comando"`, declara `ejecutar` como lista, por ejemplo
   `["programa", "--opcion"]`; nunca construyas una cadena para shell.
5. Declara los parámetros con tipos soportados: `texto`, `entero`, `ruta` o
   `booleano`.
6. Valida la configuración ejecutando `uv run tareas acciones` y consulta la
   ayuda con `uv run tareas --help`.
7. Si es destructiva, verifica primero `--dry-run` y no asumas que una ruta
   está confinada a una carpeta: el ADR 0001 documenta esa limitación vigente.

Ejemplo de acción de función:

```json
{
  "nombre": "ejemplo",
  "descripcion": "Ejecuta una acción de ejemplo.",
  "tipo": "funcion",
  "ejecutar": "ejemplo",
  "destructiva": false,
  "parametros": {}
}
```
