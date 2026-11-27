# tareas

CLI para automatizar tareas repetitivas con ficheros desde la terminal.

**Estado:** v1.0.0 · motor de acciones configurable, capa IA del centro, +200 pruebas (la cifra exacta evoluciona con cada fase; consulta `uv run pytest tests/`) y CI multi-OS en verde.

---

## Spec (versión 1 · 9/11/2026)

1. **Problema:** cada semana pierdo tiempo ordenando Descargas a mano.
2. **Para quién:** para mí y para mis compañeros de clase.
3. **Cómo se usa:** `tareas ORDEN [RUTA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes disponibles:** `listar`, `validar`, `ver`, `tamano`, `borrar`, `resumir-ia`, `tarea-ia`, `acciones`, `ejecutar NOMBRE`, `doctor`, `menu`, `version`.
6. **Acciones reales:** 5 tradicionales (`listar`, `validar`, `ver`, `tamano`, `borrar`) y 3 con IA (`resumir-ia`, `tarea-ia`, `repaso-ia`).
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

## Uso rápido

Todo se ejecuta con `uv run tareas …` dentro de la carpeta del proyecto (o con
`tareas …` si lo instalaste con `uv tool install .`). La ayuda siempre está a
una orden de distancia:

```bash
uv run tareas --help     # lista todos los comandos
uv run tareas version    # versión instalada
uv run tareas doctor     # comprueba tu configuración (nunca muestra la clave)
uv run tareas acciones   # tabla de acciones declaradas en acciones.json
uv run tareas menu       # menú numerado: elige acción por número
```

### Acciones disponibles

| Acción | ¿Necesita IA? | Descripción |
|---|---|---|
| `listar` | no | Lista el contenido de una carpeta en tabla |
| `validar` | no | Comprueba que la ruta existe, es fichero y no está vacío |
| `ver` | no | Muestra el contenido de un fichero por consola |
| `tamano` | no | Calcula el tamaño total de una carpeta (recursivo y seguro) |
| `borrar` | no | Borra un fichero con simulación y confirmación (destructiva) |
| `resumir-ia` | sí | Resume un fichero de texto en ~3 líneas |
| `tarea-ia` | sí | Convierte texto libre en una tarea estructurada |
| `repaso-ia` | sí | Genera un repaso ODT a partir de tus apuntes |

## Sin IA: el CLI funciona igual

Las cinco acciones tradicionales (`listar`, `validar`, `ver`, `tamano`,
`borrar`), `menu`, `doctor`, `acciones` y `version` **no necesitan red ni
clave**. Si no hay `TAREAS_API_KEY` configurada o el servicio del centro no
responde, las acciones de IA lo dicen en humano —«IA no disponible (modo
offline): sigo con las acciones sin IA»— y terminan con éxito sin tocar nada.
Puedes usar el CLI al 100 % sin IA.

### Ejemplos reales (ejecutados y verificados)

Ejecuta las acciones sobre tus propias carpetas; recuerda que `borrar` exige
rutas relativas dentro de la raíz autorizada:

```bash
uv run tareas listar .                        # también acepta rutas absolutas
uv run tareas validar src/tareas/cli.py       # OK <ruta absoluta>      (exit 0)
uv run tareas validar noexiste.txt            # Error: La ruta … no existe. (exit 1)
uv run tareas ver README.md
uv run tareas tamano src                      # tabla: Ficheros, Carpetas, Tamaño total

# Para simular un borrado (desde la carpeta donde está el fichero):
uv run tareas borrar fichero-viejo.txt --dry-run
# → [simular] Se borraría «…fichero-viejo.txt» (44 B).  No borra nada.
```

## Errores típicos y cómo arreglarlos

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `No existe el fichero de acciones «…»` | No hay `acciones.json` donde toca | Ejecuta desde la raíz del proyecto o pasa `--acciones RUTA` |
| `JSON inválido en «…» línea N, columna N` | El JSON tiene una coma/llave mal | Corrige esa línea; el mensaje indica dónde |
| `La acción «x» no existe. Disponibles: …` | Nombre mal escrito | Usa una de la lista (sugiere la parecida) |
| `La ruta … queda fuera de la raíz autorizada` | `borrar` solo borra dentro de la base | Ajusta la ruta o `--base` |
| `El fichero «…» está vacío` / `no es un fichero de texto` | `validar`/`ver` detectan el problema real | Comprueba la ruta y el formato |
| `La clave de la IA del centro no es válida…` | 401/403 del servicio | Revisa `TAREAS_API_KEY` |
| `La IA del centro agotó el tiempo de espera` | Tarde en responder | Inténtalo de nuevo |

Ningún error muestra un traceback de Python. Ejecuta
[`docs/guia-pruebas-manuales.md`](docs/guia-pruebas-manuales.md) (checklist)
para comprobarlo comando a comando.

## Configurar la IA (opcional)

Las acciones con IA necesitan la clave del servicio del centro. De forma
segura, sin escribir nunca la clave en el repositorio:

```bash
export TAREAS_API_KEY='tu-clave-proporcionada-por-el-centro'
export TAREAS_CA_BUNDLE="/ruta/al/certificado-CA-del-centro.crt"  # si la CA no es pública
```

(o copia `.env.example` como `.env` local: está ignorado por Git; admite tanto
`TAREAS_API_KEY` como `TAREAS_CA_BUNDLE`). Después:

```bash
uv run tareas doctor                          # dice si la clave está configurada
uv run tareas resumir-ia apuntes/tema.txt
uv run tareas tarea-ia "Preparar la exposición del viernes"
uv run tareas repaso-ia apuntes/tema.pdf -p objetivo="examen tipo test"
```

Sin clave, sin red o sin CA reconocida, el CLI **sigue funcionando**: las
acciones de IA avisan en humano y las tradicionales funcionan igual (ver
«Sin IA» más arriba y la sección técnica «Funciones de IA» al final).

## Usar tu propio acciones.json

`acciones.json` (raíz del proyecto) define qué acciones existen; cada una se
convierte en un subcomando. Puedes elegir otro fichero con la opción global
`--acciones`, que va **antes** del comando:

```bash
uv run tareas --acciones mi-config.json acciones
uv run tareas --acciones mi-config.json ejecutar mi-accion
```

`ejecutar NOMBRE` permite lanzar cualquier acción declarada sin registrarla
como subcomando. Para el esquema completo del JSON, ver «Cómo añadir una
acción» (documentación técnica, más abajo).

## Códigos de salida

| Código | Significado |
|---|---|
| `0` | Operación correcta |
| `1` | Fallo al ejecutar (ruta inexistente, borrado cancelado…) |
| `2` | Uso incorrecto (acción desconocida, argumentos mal formados) |
| `3` | Configuración inválida (JSON roto o inexistente) |

## Composición de acciones

No hay un motor de pipelines: las acciones están diseñadas para componerse
desde la shell, una detrás de otra, encadenando con `&&` (sigue solo si la
anterior terminó con código `0`). Los códigos de salida estables hacen que el
flujo sea fiable, y cada acción imprime una salida clara y autónoma.

Ejemplo real ejecutado sobre una carpeta de prueba `apuntes/` (verificado con
`uv run pytest tests/test_cli.py::test_composicion_de_acciones_sobre_una_carpeta_de_prueba`):

```bash
cd /ruta/del/proyecto          # desde aquí vales para todas las órdenes
uv run tareas listar /ruta/a/tus/apuntes        # tabla de contenido
uv run tareas validar /ruta/a/tus/apuntes/tema.txt
uv run tareas ver /ruta/a/tus/apuntes/tema.txt
uv run tareas tamano /ruta/a/tus/apuntes

# Simular un borrado (ruta RELATIVA a la carpeta actual; así lo exige la seguridad):
cd /ruta/a/tus/apuntes
uv run --project /ruta/del/proyecto tareas borrar viejo.txt --dry-run
# → [simular] Se borraría «/ruta/a/tus/apuntes/viejo.txt» (44 B).  No borra nada.
```

Encadenamiento con gestión de errores (la cadena se corta en el primer fallo):

```bash
uv run tareas validar apuntes/tema1.txt && uv run tareas ver apuntes/tema1.txt
uv run tareas validar apuntes/no-existe.txt && echo "no se imprime"
```

Si una acción falla, el error se muestra en un mensaje humano en stderr con su
código (`1`, `2` o `3`) y `&&` evita que el resto del flujo se ejecute sobre un
estado inválido. El borrado real, además, exige confirmación interactiva o
`--si`; sin ella, la cadena se detiene con código `1`.

## Seguridad: sin sorpresas

Las acciones destructivas (`borrar`) **nunca actúan sin avisar**:

```bash
# Simulación: dice qué haría, no borra nada
tareas borrar fichero.txt --dry-run
# → [simular] Se borraría fichero.txt

# Sin --dry-run pregunta antes de borrar
tareas borrar fichero.txt
# → La acción «borrar» es destructiva. ¿Continuar? [y/N]

# Para scripts: --si confirma sin preguntar
tareas borrar fichero.txt --si
```

Además, `borrar` está **confinado a una raíz autorizada** (el directorio actual
o la que pases con `--base`); `repaso-ia` aplica la misma política a sus apuntes
y a la carpeta de salida. `borrar` rechaza rutas absolutas y cualquier `../` que salga
de esa raíz, para que un borrado no pueda tocar ficheros del sistema ni de fuera
del proyecto. La política de confinamiento y los mensajes de seguridad viven en
un módulo propio, `tareas.repaso.seguridad`, reutilizado por `borrar` y
`repaso-ia`. Esta decisión está documentada en
[`docs/adr/0001`](docs/adr/0001-acciones-desde-json-externo.md).

## Cómo añadir una acción

No toques el motor ni `cli.py`. Añade un bloque a `acciones.json` con el esquema
documentado en la skill `.opencode/skills/acciones-json/SKILL.md`. El comando
`/nueva-accion` te guía para hacerlo. Ejemplo:

```json
{
  "nombre": "comprimir",
  "descripcion": "Comprime una carpeta en un .zip",
  "tipo": "comando",
  "ejecutar": ["zip", "-r", "destino.zip", "carpeta"],
  "destructiva": false,
  "ia": false
}
```

Los tipos válidos son `funcion` y `comando`; para `funcion`, `ejecutar` es el
nombre de una función registrada.

## Documentación técnica

Lo que sigue está orientado a quien quiera ampliar o auditar el proyecto;
para usar el CLI basta con la guía rápida de arriba.

## Estructura

```
src/tareas/
├── cli.py           # interfaz Typer, solo delega en el motor
├── motor.py         # lee acciones.json y ejecuta
├── puertos.py       # capa de "enchufes" (proveedor IA)
├── errores.py       # excepciones propias (TareasError, ConfigError, …)
├── modelos.py       # modelos de datos
├── parametros.py    # parseo de argumentos
├── configuracion.py # carga y valida el JSON
├── repaso/          # lectura, síntesis, esquemas, ODT, seguridad y apertura en Writer
└── ia/              # proveedor IA (interfaz, ProveedorNulo, proveedor del centro)
docs/adr/            # decisiones de arquitectura
.opencode/           # skill y comando del agente
```

## Funciones de IA

`resumir-ia` envía el contenido de un fichero de texto al servicio Qwen del
centro, `tarea-ia` convierte una petición en una tarea estructurada y
`repaso-ia` genera un documento ODT a partir de tus apuntes. Para
utilizarlas se necesitan:

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
  las acciones con IA y si la clave o el certificado CA están configurados
  (igual que el proveedor: variables de entorno o `.env` local). No contacta con
  la IA y nunca muestra el valor de la clave.
- `menu` presenta un menú numerado con todas las acciones declaradas y pide los
  parámetros necesarios. Escribe `0` para salir; en una terminal sin entrada
  interactiva termina con un aviso. Las acciones destructivas siguen exigiendo
  confirmación.

```bash
uv run tareas doctor
uv run tareas menu
```

## repaso-ia: apuntes → documento de repaso en LibreOffice

`repaso-ia` convierte uno o varios documentos de apuntes en un **repaso
educativo en formato ODT** (portada, resumen por apartados, conceptos clave,
tablas comparativas, esquemas dibujados localmente, errores frecuentes, repaso
final y preguntas de examen) y lo abre en LibreOffice Writer al terminar.

```bash
uv run tareas repaso-ia tema3.pdf                                  # un PDF
uv run tareas repaso-ia apuntes.md resumen.txt                      # varios
uv run tareas repaso-ia tema.pdf -p objetivo="examen tipo test"     # objetivo
uv run tareas repaso-ia tema.pdf -p salida=repasos -p nombre=final  # destino
uv run tareas repaso-ia tema.pdf -p paralelo=5                        # más concurrencia
uv run tareas repaso-ia tema.pdf --dry-run                          # simular
```

- Formatos leídos: `.txt/.md/.rst/.csv`, `.pdf` (con `pdftotext`, LibreOffice o
  Ghostscript), `.docx/.odt/.ods` (ZIP con XML, se parsean directamente),
  `.htm/.html` (se extrae el texto visible) y `.doc/.rtf` (requieren
  LibreOffice). Varios apuntes se pasan como posicionales:
  `repaso-ia apuntes.md resumen.txt`.
- Los originales **nunca se modifican**; el repaso se escribe junto al primer
  apunte (o en `salida=`). Si el nombre ya existe, se guarda con sufijo `_2`,
  sin sobrescribir.
- Con documentos largos la IA trabaja por etapas: sintetiza fragmentos (hasta 3
  peticiones simultáneas, ajustable con `-p paralelo=N`) y redacta un maestro único.
  En terminal interactiva se muestra una línea de progreso compacta con spinner,
  contador y porcentaje; con salida redirigida, solo las fases y un resumen final.
- Si la IA falla (clave, tiempo de espera o sin conexión) el error se informa
  en humano y no se genera ningún fichero. Si LibreOffice no está instalado,
  se indica la ruta para abrirlo a mano.
- Requiere lo mismo que las demás acciones de IA: `TAREAS_API_KEY` válida y,
  si la CA no es pública, `TAREAS_CA_BUNDLE`.

## Artefactos de IA (sesión 2)

- **Skill** `.opencode/skills/acciones-json/SKILL.md`: documenta el esquema del JSON.
- **Comando** `/nueva-accion`: asistente para añadir acciones al JSON.
- **Subagente** `revisor-tareas`: audita el código en solo lectura (edit: deny).
- **ADR 0001**: decisión motor + JSON externo y confinamiento del `borrar`.

## Probar el CLI a mano

La checklist completa, comando a comando y con los mensajes de error esperados,
está en [`docs/guia-pruebas-manuales.md`](docs/guia-pruebas-manuales.md).

## Pruebas automatizadas

```bash
uv run pytest tests/          # suite completa (el número de pruebas evoluciona; hoy +230)
uv run pytest tests/test_cli.py -q   # solo integración CLI
```

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
- [x] Tests del camino feliz + casos feos (suite en evolución; ver «Pruebas automatizadas»).
- [x] GitHub Actions para correr los tests en cada push (Ubuntu, Windows, macOS).
- [x] Flujo de ramas + pull requests hacia `main`.
- [ ] Release `v1.0.0` etiquetada (versión y `CHANGELOG.md` preparados; **pendiente** de crear el tag y la GitHub Release).

## Licencia

MIT (ver `LICENSE`).
