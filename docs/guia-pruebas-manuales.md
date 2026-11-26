Checklist para validar `tareas` a mano, comando a comando. **Nunca uses esta
guía sobre tus documentos personales**: trabaja siempre en una carpeta de
pruebas. Ninguna prueba de esta lista borra ficheros reales (solo `--dry-run`).

## Preparación (bloque A)

```bash
cd /ruta/al/proyecto                # la raíz del repo (donde está acciones.json)
uv sync                             # prepara el entorno
uv run tareas --help                # debe listar los 13 comandos
uv run tareas version               # → tareas 1.0.0
```

Crea la carpeta de pruebas (ej. `P=/tmp/tareas-pruebas`):

```bash
mkdir -p $P/sub
printf 'La fotosíntesis ocurre en los cloroplastos.\n' > $P/apuntes.txt
printf '# Tema 2\n\nLa mitocondria produce energía.\n' > $P/tema2.md
: > $P/vacio.txt
printf 'nota interior\n' > $P/sub/nota.txt
printf 'borrable\n' > $P/borrable.txt
```

## A. Ayuda

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| A1 | `uv run tareas --help` | Tabla con comandos y la opción global `--acciones` | Traceback o lista vacía |
| A2 | `uv run tareas listar --help` | Ayuda del comando con sus parámetros | Traceback |

## B. Información y diagnóstico (sin IA)

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| B1 | `uv run tareas version` | `tareas 1.0.0`, exit 0 | Cualquier error |
| B2 | `uv run tareas doctor` | Tabla: «Configuración Correcta», 8 acciones, «Clave de IA (entorno): configurada/no configurada», y «Conexión: No se comprueba; las acciones sin IA funcionan offline». **Nunca muestra la clave** | exit≠0, clave visible o traceback |
| B3 | `uv run tareas acciones` | Tabla con las 8 acciones del JSON (nombre, tipo, destructiva, IA) | exit≠0 |
| B4 | `uv run tareas menu` | Menú numerado; escribe `1` para ejecutar la primera acción y `0` para salir. Con salida no interactiva: aviso «Entrada no interactiva» y exit 0 | Traceback |

## C. Acciones tradicionales (sin IA)

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| C1 | `uv run tareas listar $P` | Tabla con apuntes.txt, tema2.md, vacio.txt, sub/, borrable.txt; exit 0 | exit≠0 |
| C2 | `uv run tareas validar $P/apuntes.txt` | `OK <ruta>` y exit 0 | exit≠0 |
| C3 | `uv run tareas ver $P/tema2.md` | Contenido del fichero, exit 0 | Contenido vacío |
| C4 | `uv run tareas tamano $P` | Tabla: Ficheros 5, Tamaño total > 0, exit 0 | exit≠0 |
| C5 | `uv run tareas borrar $P/borrable.txt --dry-run` | `[simular] Se borraría «…» (8 B)`, exit 0, **y el fichero sigue existiendo** | El fichero desaparece o exit≠0 |
| C6 | `uv run tareas ejecutar listar $P` (misma acción vía nombre) | Igual que C1 | exit≠0 |

## D. Configuración (`acciones.json`)

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| D1 | `uv run tareas --acciones /ruta/que/no.json acciones` | `Error: No existe el fichero de acciones «…»`, exit 3 | Traceback o exit 0 |
| D2 | `echo '{roto' > $P/roto.json` y `uv run tareas --acciones $P/roto.json acciones` | `Error: JSON inválido en «…», línea 1, columna 2: …`, exit 3 | Traceback |
| D3 | `uv run tareas --no-existe` | Mensaje de uso + tabla roja «No such option», exit 2 | Traceback o exit 1 |

## E. Acciones de IA con proveedor disponible (bloque F si no tienes IA)

Requisitos: `TAREAS_API_KEY` (y `TAREAS_CA_BUNDLE` si la CA no es pública).
Nunca escribas la clave en el repo: usa variables de entorno.

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| E1 | `uv run tareas resumir-ia $P/apuntes.txt` | Resumen de 2–4 líneas, exit 0 | Ver F1 |
| E2 | `uv run tareas tarea-ia "Preparar la exposición del viernes"` | 3 líneas: `Título:` / `Prioridad: Alta\|Media\|Baja` / `Fecha sugerida: AAAA-MM-DD o Sin fecha`, exit 0 | Respuesta sin formato |
| E3 | `uv run tareas repaso-ia $P/apuntes.txt --dry-run` | `[simular] Se generaría «…» … y se abriría en LibreOffice Writer.`, exit 0, no escribe nada | Escribe ficheros |
| E4 | `uv run tareas repaso-ia $P/apuntes.txt -p abrir=false` | Genera `$P/apuntes.odt`, exit 0, abre Writer solo si `abrir=true` y LibreOffice existe | Modifica el original (ver I) |

## F. IA no disponible: modo offline

Con `TAREAS_API_KEY` ausente o red caída (desconecta o usa un endpoint falso):

| # | Comando | Resultado esperado | Incorrecto |
|---|---|---|---|
| F1 | `uv run tareas resumir-ia $P/apuntes.txt` | `IA no disponible (modo offline): sigo con las acciones sin IA`, exit 0 | Traceback o exit≠0 |
| F2 | `uv run tareas tarea-ia "estudiar tema"` | Igual que F1, exit 0 | Traceback |
| F3 | `uv run tareas repaso-ia $P/apuntes.txt -p abrir=false` | Mensaje offline o `Error: …IA del centro…` explicando causa (conexión/clave/timeout), exit 0 u 1 según el caso, sin traceback | Traceback o fichero ODT a medias |
| F4 | `uv run tareas listar $P && uv run tareas validar $P/apuntes.txt` | Siguen funcionando igual que con IA, exit 0 | Dependen de la IA |

## G. Errores intencionados y mensajes humanos

Todos los mensajes van por stderr con prefijo `Error:` y sin traceback.

| # | Comando | Mensaje esperado | Exit |
|---|---|---|---|
| G1 | `uv run tareas validar $P/no-existe.txt` | `Error: La ruta «…» no existe.` | 1 |
| G2 | `uv run tareas validar $P/vacio.txt` | `Error: El fichero «…» está vacío.` | 1 |
| G3 | `uv run tareas listar $P/no-existe` | `Error: «…» no existe o no es una carpeta.` | 1 |
| G4 | `uv run tareas ver $P/vacio.txt` (fichero binario, p. ej. un .pdf) | `Error: «…» no es un fichero de texto (UTF-8).` | 1 |
| G5 | `uv run tareas ejecutar no-existe` | `Error: La acción «no-existe» no existe. Disponibles: … ¿Querías decir …?` | 2 |
| G6 | `uv run tareas listar $P extra` (argumento de más) | Mensaje de uso «Got unexpected extra argument», sin traceback | 2 |
| G7 | `uv run tareas validar -p ruta=$P/apuntes.txt -p ruta=$P/apuntes.txt` | `Error: El parámetro «ruta» se ha indicado dos veces.` | 2 |

## H. Seguridad

| # | Comando | Resultado esperado | Exit |
|---|---|---|---|
| H1 | `uv run tareas borrar $P/borrable.txt </dev/null` (respondes `N` o cancelas) | `Operación cancelada.` y **el fichero sigue existiendo** | 1 |
| H2 | `uv run tareas borrar /etc/passwd` | `Error: No se permiten rutas absolutas para borrar.` | 1 |
| H3 | `uv run tareas borrar $P/../escape.txt --dry-run` | `Error: La ruta … queda fuera de la raíz autorizada …` | 1 |
| H4 | `uv run tareas borrar $P/sub --dry-run` | `Error: «…» es una carpeta. Esta acción solo borra ficheros.` | 1 |

## I. Comprobación final

```bash
ls -la $P                     # borrable.txt debe SEGUIR existiendo (solo dry-run/abort)
cat $P/apuntes.txt            # contenido idéntico al original
git -C /ruta/al/proyecto status --short   # la prueba no ha tocado el repo
```

Resultado global correcto: en ningún paso has visto un traceback de Python;
todos los fallos muestran `Error:` en rojo con explicación en humano.
