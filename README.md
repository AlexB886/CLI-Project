# tareas

CLI para automatizar tareas repetitivas con ficheros desde la terminal.

**Estado:** v1.0.0 · motor de acciones configurable, capa IA del centro, 145 pruebas y CI multi-OS en verde.

---

## Spec (versión 1 · 9/11/2026)

1. **Problema:** cada semana pierdo tiempo ordenando Descargas a mano.
2. **Para quién:** para mí y para mis compañeros de clase.
3. **Cómo se usa:** `tareas ORDEN [RUTA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes disponibles:** `listar`, `validar`, `ver`, `tamano`, `borrar`, `resumir-ia`, `tarea-ia`, `acciones`, `ejecutar NOMBRE`, `doctor`, `menu`, `version`.
6. **Acciones reales:** 5 tradicionales (`listar`, `validar`, `ver`, `tamano`, `borrar`) y 2 con IA (`resumir-ia`, `tarea-ia`).
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

## Funciones de IA

`resumir-ia` envía el contenido de un fichero de texto al servicio Qwen del
centro y `tarea-ia` convierte una petición en una tarea estructurada. Para
utilizarlos se necesitan:

- Acceso de red desde el equipo al endpoint del centro
  `https://10.100.22.107/llmapi/v1` (incluyendo ruta y puerto HTTPS 443).
- Una `TAREAS_API_KEY` válida para el servicio del centro. Puede proporcionarse
  como variable de entorno o en `.env` local; nunca se incluye en Git.
- Si la CA del servicio no está en el almacén de confianza del sistema, una
  copia autorizada del certificado CA del centro y `TAREAS_CA_BUNDLE` apuntando
  a ese fichero. El proveedor verifica TLS en ambos casos; no desactiva la
  validación.

Ejemplo para Linux, desde la raíz del proyecto (usa rutas genéricas):

```bash
export TAREAS_API_KEY='tu-clave-proporcionada-por-el-centro'
export TAREAS_CA_BUNDLE="/ruta/al/certificado-CA-del-centro.crt"
uv run tareas resumir-ia documento.txt
uv run tareas tarea-ia "Preparar la exposición para el viernes"
```

En el equipo del profesor hay que configurar sus propias credenciales y obtener
la CA por un canal autorizado; no se puede asumir que la clave local, la ruta
`certs/` o la conectividad de este ordenador existan allí. Sin API Key, red o
CA reconocida/configurada, Qwen no estará disponible. Las acciones tradicionales
del CLI siguen funcionando sin conexión a Qwen.

## Comandos de apoyo

- `doctor` muestra la versión, el fichero de acciones, el número de acciones,
  las acciones con IA y si la clave o el certificado CA están configurados en
  el entorno. No contacta con la IA y nunca muestra el valor de la clave.
- `menu` presenta un menú numerado con todas las acciones declaradas y pide los
  parámetros necesarios. Escribe `0` para salir; en una terminal sin entrada
  interactiva termina con un aviso. Las acciones destructivas siguen exigiendo
  confirmación.

```bash
uv run tareas doctor
uv run tareas menu
```

## Artefactos de IA (sesión 2)

- **Skill** `.opencode/skills/acciones-json/SKILL.md`: documenta el esquema del JSON.
- **Comando** `/nueva-accion`: asistente para añadir acciones al JSON.
- **Subagente** `revisor-tareas`: audita el código en solo lectura (edit: deny).
- **ADR 0001**: decisión motor + JSON externo y confinamiento del `borrar`.

## Proceso de desarrollo

Desarrollo en ramas de trabajo (p. ej. `mejoras-ia-cli`) con commits atómicos y
descriptivos, integradas en `main` mediante pull request. Cada PR se valida con
**GitHub Actions** (job `CI`: `uv sync --frozen` + `uv run pytest -q` en Ubuntu,
Windows y macOS). Las decisiones importantes se registran como ADR en
`docs/adr/`. Los cambios se preparan y prueban en local (`uv sync` + `uv run
pytest -q`) antes de abrir el PR. El cierre lo marca la release etiquetada
`v1.0.0` con `CHANGELOG.md` (ver Roadmap).

## Roadmap

- [x] Capa IA: acciones `resumir-ia` y `tarea-ia` + modo sin red.
- [x] Tests del camino feliz + casos feos (145 pruebas con pytest).
- [x] GitHub Actions para correr los tests en cada push (Ubuntu, Windows, macOS).
- [x] Flujo de ramas + pull requests hacia `main`.
- [ ] Release `v1.0.0` etiquetada (versión y `CHANGELOG.md` preparados; **pendiente** de crear el tag y la GitHub Release).

## Licencia

MIT (ver `LICENSE`).
