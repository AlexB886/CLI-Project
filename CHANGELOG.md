# Changelog

Todas las cambios notables de este proyecto se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y el
proyecto se adhiere al [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- **Acción `repaso-ia`**: genera un documento de repaso ODT a partir de uno o
  varios apuntes (`.txt/.md/.rst/.csv`, `.pdf`, `.docx`, `.odt`, `.rtf`,
  `.html`) con portada, resumen por apartados, conceptos clave, explicaciones
  didácticas, tablas comparativas, esquemas dibujados localmente, errores
  frecuentes, repaso final y preguntas de examen. Se abre en LibreOffice
  Writer al terminar. Parámetros: `objetivo`, `salida`, `nombre` y `abrir`.
- Documento largo con síntesis por etapas (fragmentos → maestro coherente) y
  progreso visible por consola.
- Lectura de PDF con tres conversores locales encadenados sin bucles:
  `pdftotext` → LibreOffice → Ghostscript; siempre en directorio temporal y
  sin tocar el original.
- Nuevos módulos en `src/tareas/repaso/`: lectura, fragmentación, esquemas,
  contenidos, ODT y apertura en el escritorio, con dependencias solo de la
  biblioteca estándar.
- Diagnóstico de respuestas inválidas del proveedor: la excepción anota la
  etapa (`fragmento N de M`, `documento final`, extracto de la respuesta) con
  las credenciales saneadas, y la serie de síntesis aborta sin reintentos.
- Simulación (`--dry-run`) propia por acción: `repaso-ia` previsualiza sin
  leer ni escribir, y las acciones sin simulación propia obtienen una
  previsualización neutra.
- Ayuda por acción: `tareas repaso-ia --help` lista los parámetros declarados.
- 54 pruebas nuevas (`tests/test_repaso_*.py`): lectura, fragmentación,
  esquemas, ODT, contenidos, apertura, la acción y un test de integración;
  sin IA real ni LibreOffice real.

### Corregido

- `repaso-ia apuntes.md resumen.txt` ahora entrega dos apuntes en vez de
  interpretar el segundo como objetivo de estudio.
- Los formatos declarados `.ods/.htm/.html/.rtf/.doc` ya producen texto o un
  error humano; antes `extraer_texto` devolvía `None` y rompía la acción.
- La lectura de ODT ya incluye el texto dentro de `text:span`.
- `--base` se aplica también a `repaso-ia` y deja de inyectarse en acciones que
  no declaran ese parámetro.
- `mimetype` se escribe el primero y sin comprimir en los ODT generados.
- Guía manual y README: comandos con rutas relativas y `--base`, tipos válidos
  del JSON y formatos de entrada reales.

## [1.0.0] - 2026-11-23

Primer release estable del CLI `tareas`: motor de acciones configurable desde
JSON, capa de IA conectada al servicio del centro y base de pruebas + CI.

### Añadido

- **Motor de acciones en clases** con responsabilidades separadas: CLI fina
  (`cli.py`), orquestador (`motor.py`), carga y validación (`configuracion.py`),
  modelos (`modelos.py`), resolución de parámetros (`parametros.py`),
  excepciones propias (`errores.py`) y puertos `Protocol` (`puertos.py`).
- **Configuración externa `acciones.json`**: las acciones se declaran sin tocar
  código; el cargador valida el esquema (nombres, tipos, claves desconocidas,
  parámetros, valores por defecto, nombres reservados y duplicados).
- **Registro explícito de funciones** (`registro.py`): el JSON solo puede
  invocar funciones registradas; los comandos externos se ejecutan sin shell.
- **Acciones tradicionales:** `listar`, `validar`, `ver`, `tamano` y `borrar`.
- **Acción destructiva `borrar` con protecciones:** simulación (`--dry-run` /
  `--simular`), confirmación interactiva o `--si`, y **confinamiento a una raíz
  autorizada** (`--base`, por defecto el cwd) que rechaza rutas absolutas y
  traversal `../`.
- **Capa de IA** desacoplada: interfaz `ProveedorIA`, `ProveedorNulo` (modo sin
  IA), fábrica (`fabrica.py`) y `ProveedorCentro` para el servicio Qwen del
  centro con autenticación Bearer, **verificación TLS** (CA vía
  `TAREAS_CA_BUNDLE`, sin desactivar la validación) y reutilización del contexto
  SSL.
- **Clasificación de errores de IA** en errores propios y comprensibles:
  autenticación, tiempo de espera, no disponible y respuesta inválida.
- **Acciones con IA:** `resumir-ia` (resume un fichero de texto) y `tarea-ia`
  (convierte texto libre en una tarea estructurada), ambas con **modo offline**
  cuando no hay clave, red ni CA: informan con claridad y las acciones
  tradicionales siguen disponibles.
- **Comandos de apoyo:** `version`, `acciones`, `ejecutar NOMBRE`, `doctor`
  (diagnóstico de instalación que **nunca** muestra la clave) y `menu`
  (menú numerado interactivo).
- **Sugerencias de acción** ante nombres inexistentes («¿Querías decir …?»).
- **Códigos de salida** coherentes: `0` correcto, `1` fallo al ejecutar, `2`
  uso incorrecto, `3` configuración inválida.
- **Seguridad de secretos:** la clave vive en `.env` (excluido del repositorio);
  `.env.example` documenta la configuración; reglas de permisos en
  `opencode.json` y subagente revisor de solo lectura.
- **Artefactos de IA para el desarrollo:** skill `acciones-json`, comando
  `/nueva-accion` y subagente `revisor-tareas`.
- **Pruebas** con pytest: 145 pruebas que cubren configuración, parámetros,
  motor, acciones internas, comandos personalizados, CLI, proveedor del centro
  (TLS y errores), `tarea-ia`, `doctor` y presentación visual.
- **Dependencias de desarrollo declaradas** (`pytest`, `pytest-cov`) mediante un
  grupo de desarrollo de uv, con `uv.lock` coherente.
- **Integración continua:** job `CI` en GitHub Actions que ejecuta
  `uv sync --frozen` + `uv run pytest -q` en Ubuntu, Windows y macOS.
- **Documentación:** `README.md`, `docs/adr/0001` y `LICENSE` (MIT).

### Cambiado

- Versión del proyecto y del paquete elevada a `1.0.0` (`pyproject.toml` y
  `src/tareas/__init__.py`).
- `README.md`: estado, spec de acciones, proceso de desarrollo (ramas + PR + CI)
  y hoja de ruta actualizados a la realidad entregada.
- `docs/adr/0001`: el confinamiento de rutas de `borrar` se documenta como
  **implementado y verificado**, eliminando la contradicción anterior.

[1.0.0]: https://github.com/AlexB886/CLI-Project/releases/tag/v1.0.0
