# tareas

CLI para automatizar tareas repetitivas con ficheros desde la terminal.

**Estado:** Semana 1 y 2 cerradas · Capa IA (Semana 3) en desarrollo · v0.1

---

## Spec (versión 1 · 9/11/2026)

1. **Problema:** cada semana pierdo tiempo ordenando Descargas a mano.
2. **Para quién:** para mí y para mis compañeros de clase.
3. **Cómo se usa:** `tareas ORDEN [RUTA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes disponibles:** `listar`, `validar`, `ver`, `tamano`, `borrar`, `acciones`, `ejecutar NOMBRE`, `version`.
6. **Acciones reales (5):** `listar`, `validar`, `ver`, `tamano`, `borrar`.
7. **Nunca hará:** borrar sin preguntar, ni tocar ficheros fuera de la raíz autorizada (confinamiento real, ver Seguridad).
8. **Plataformas:** Linux primero; también Windows y macOS.
9. **Códigos de salida:** `0` bien · `1` fallo al ejecutar · `2` uso incorrecto · `3` configuración inválida.
10. **Instalación:** `uv tool install .` (o `uv run tareas` en desarrollo).

> El Spec v0 (29/10/2026) planteaba 3 acciones de borrador. La v1 refleja lo
> realmente implementado tras el motor y el parche de seguridad.

## Qué es

`tareas` no es un programa con comandos fijos. Es un **motor**: lee la lista de
acciones de un fichero externo (`acciones.json`) y las expone como subcomandos.
El código Python es el músculo; el JSON es la configuración. **Añadir una tarea
nueva no requiere reprogramar el CLI**, solo editar el JSON.

```
acciones.json  →  configuracion.py  →  motor.py  →  Acción
     (config)          (valida)          (motor)     (ejecuta)
```

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias y entornos)

## Instalación

Una sola orden (deja el comando `tareas` disponible en el PATH):

```bash
uv tool install .
```

En modo desarrollo, dentro del repo:

```bash
uv sync
uv run tareas --help
```

## Uso

```bash
tareas --help          # lista todas las acciones
tareas version         # versión del CLI
tareas acciones        # muestra el JSON en crudo
```

### Acciones disponibles

| Acción | Tipo | Descripción |
|---|---|---|
| `listar` | lectura | Lista el contenido de una carpeta en tabla |
| `validar` | lectura | Comprueba que la ruta existe, es fichero y no está vacío |
| `ver` | lectura | Muestra el contenido de un fichero por consola |
| `tamano` | lectura | Calcula el tamaño total de una carpeta (recursivo) |
| `borrar` | **destructiva** | Borra un fichero con simulación y confirmación |

### Ejemplos

```bash
# Validar un fichero (exit 0 si OK, exit 1 si no)
tareas validar src/tareas/__init__.py
# → OK src/tareas/__init__.py

tareas validar noexiste.txt
# → Error: la ruta no existe.   (exit 1)

# Ver el contenido de un fichero
tareas ver notas.txt

# Tamaño de una carpeta
tareas tamano ~/proyectos
# → Ficheros: 12  Carpetas: 3  Tamaño total: 4.2 KB
```

## Códigos de salida

| Código | Significado |
|---|---|
| `0` | Operación correcta |
| `1` | Fallo al ejecutar (ruta inexistente, borrado cancelado…) |
| `2` | Uso incorrecto (acción desconocida, argumentos mal formados) |
| `3` | Configuración inválida (JSON roto o inexistente) |

## Seguridad: sin sorpresas

Las acciones destructivas (`borrar`) **nunca actúan sin avisar**:

```bash
# Simulación: dice qué haría, no borra nada
tareas borrar fichero.txt --dry-run
# → [simular] Se borraría fichero.txt

# Sin --dry-run pregunta antes de borrar
tareas borrar fichero.txt
# → ¿Borrar «fichero.txt»? [y/N]

# Para scripts: --si confirma sin preguntar
tareas borrar fichero.txt --si
```

Además, `borrar` está **confinado a una raíz autorizada** (el directorio actual
o la que pases con `--base`). Rechaza rutas absolutas y cualquier `../` que salga
de esa raíz, para que un borrado no pueda tocar ficheros del sistema ni de fuera
del proyecto. Esta decisión está documentada en
[`docs/adr/0001`](docs/adr/0001-acciones-desde-json-externo.md).

## Cómo añadir una acción

No toques el motor ni `cli.py`. Añade un bloque a `acciones.json` con el esquema
documentado en la skill `.opencode/skills/acciones-json/SKILL.md`. El comando
`/nueva-accion` te guía para hacerlo. Ejemplo:

```json
{
  "nombre": "comprimir",
  "descripcion": "Comprime una carpeta en un .zip",
  "tipo": "sistema",
  "destructiva": false,
  "ia": false
}
```

## Estructura

```
src/tareas/
├── cli.py           # interfaz Typer, solo delega en el motor
├── motor.py         # lee acciones.json y ejecuta
├── puertos.py       # capa de "enchufes" (proveedor IA)
├── modelos.py       # modelos de datos
├── parametros.py    # parseo de argumentos
├── configuracion.py # carga y valida el JSON
├── errores.py       # excepciones propias con mensajes humanos
└── ia/              # proveedor IA (hueco, ProveedorNulo)
docs/adr/            # decisiones de arquitectura
.opencode/           # skill y comando del agente
```

## Artefactos de IA (sesión 2)

- **Skill** `.opencode/skills/acciones-json/SKILL.md`: documenta el esquema del JSON.
- **Comando** `/nueva-accion`: asistente para añadir acciones al JSON.
- **Subagente** `revisor-tareas`: audita el código en solo lectura (edit: deny).
- **ADR 0001**: decisión motor + JSON externo y confinamiento del `borrar`.

## Proceso de desarrollo

Desarrollo en `main` con commits atómicos y descriptivos (uno por paso). Las
decisiones importantes se registran como ADR en `docs/adr/`. Flujo de ramas +
pull requests y release etiquetada previstos para el cierre (ver Roadmap).

## Roadmap

- [ ] Capa IA: acciones `resumir-ia` y `tarea-ia` + modo sin red.
- [ ] Tests del camino feliz + 3 casos feos.
- [ ] GitHub Actions para correr los tests en cada push.
- [ ] Migrar a flujo de ramas + pull requests.
- [ ] Release `v1.0` etiquetada con changelog.

## Licencia

MIT (ver `LICENSE`).
