# CONTEXTO DEL PROYECTO — TAREAS CLI CON IA

**Documento maestro de continuidad**

Última actualización: 17/11/2026  
Repositorio local: `~/CLI`  
Rama de trabajo: `mejoras-ia-cli`  
Objetivo: conseguir el máximo nivel de la rúbrica y desarrollar un CLI original, creativo y de calidad profesional.

---

# 1. OBJETIVO DEL PROYECTO

Estamos desarrollando una herramienta CLI llamada `tareas`, escrita en Python, que permite trabajar con archivos y tareas desde la terminal mediante acciones configuradas externamente en `acciones.json`.

El proyecto utiliza Typer y `uv`, incorpora una capa de inteligencia artificial conectada al servicio local del centro `ia.simarro`, utilizando el modelo Qwen.

No queremos limitarnos a cumplir los requisitos mínimos de la actividad.

Nuestro objetivo es:

- Conseguir el 100 % de cada criterio de la rúbrica.
- Superar las expectativas del profesor.
- Tener una arquitectura limpia, modular y mantenible.
- Garantizar seguridad y protección de secretos.
- Disponer de pruebas automatizadas completas.
- Facilitar la instalación y utilización desde cualquier ordenador compatible.
- Incorporar funcionalidades originales y creativas que diferencien el proyecto.

La prioridad es conseguir primero una base perfectamente funcional y estable. La creatividad se incorporará después.

# 2. RÚBRICA OFICIAL

La evaluación tiene 7 criterios y un total de 100 puntos.

## 2.1 Acciones predefinidas funcionando — 20 puntos

Nivel Excelente:

- 5 o más acciones propias útiles.
- Acciones combinables.
- Salida clara.
- Sin efectos sorpresa.
- Simulación previa o confirmación antes de borrar o sobrescribir.

## 2.2 Configuración externa (`acciones.json`) — 15 puntos

Nivel Excelente:

- Añadir una acción no debe exigir modificar el código.
- Debe existir un ADR que justifique por qué se utiliza configuración externa y no código para definir las acciones.

## 2.3 Capa IA, secretos y modo sin red — 15 puntos

Nivel Excelente:

- Al menos 2 acciones útiles con IA.
- Ninguna clave en el historial de Git.
- Si no hay red, la CLI lo explica y sigue funcionando con las acciones sin IA.

## 2.4 Robustez: excepciones y entradas feas — 15 puntos

Nivel Excelente:

- Excepciones propias, por ejemplo `ConfigError` y `AccionNoValida`.
- Mensajes humanos.
- Ningún traceback ante errores previsibles.
- Aserciones en desarrollo.

## 2.5 Diseño en clases y módulos — 10 puntos

Nivel Excelente:

- Responsabilidades separadas.
- Interfaz, motor, acciones y proveedor IA independientes.
- Visibilidad cuidada.
- Métodos estáticos con sentido cuando corresponda, por ejemplo fábricas desde configuración.

## 2.6 Pruebas y calidad — 15 puntos

Nivel Excelente:

- Pruebas que cubran el camino feliz y al menos 3 casos feos.
- Ejecutadas en GitHub Actions.
- Auditadas y con capacidad de explicar cada aserción.

## 2.7 Instalación, documentación y proceso — 10 puntos

Nivel Excelente:

- Instalación siguiendo el README.
- Release `v1.0` etiquetada con changelog.
- Historial con ramas y PR.
- Proceso de desarrollo legible.

## 2.8 Cuatro requisitos mínimos obligatorios

Si falla uno, el proyecto no se evalúa.

1. Se instala siguiendo el README y la orden de ayuda `--help` funciona.
2. Ninguna clave ni secreto en el repositorio ni en su historial.
3. Al menos 3 acciones propias definidas en `acciones.json` funcionan.
4. Historial Git real con un mínimo de 10 commits con mensajes que expliquen el proceso.

**Importante:** no declarar ningún criterio conseguido sin evidencias verificables.

# 3. TECNOLOGÍAS Y ARQUITECTURA

Tecnologías conocidas:

- Python 3.12 o superior.
- Typer.
- uv.
- Proveedor IA del centro.
- Qwen.
- Pytest.
- JSON para configuración externa.

Estructura conocida:

- `src/tareas/`: código principal.
- `src/tareas/ia/`: capa de inteligencia artificial.
- `src/tareas/acciones/`: acciones internas.
- `tests/`: pruebas automatizadas.
- `acciones.json`: definición externa de acciones.
- `README.md`: documentación.
- `pyproject.toml`: configuración del proyecto.
- `.env.example`: ejemplo de configuración.

La arquitectura debe mantener separadas estas responsabilidades:

- CLI: interfaz y comandos.
- Motor: ejecución y coordinación de acciones.
- Configuración: carga y validación de JSON.
- Acciones: operaciones disponibles.
- Proveedor IA: comunicación con el servicio del centro.

# 4. ESTADO DE GIT Y REGLAS

Rama de trabajo: `mejoras-ia-cli`.

El trabajo debe permanecer en esta rama.

Reglas obligatorias:

- No modificar `main`.
- No hacer commits sin autorización expresa.
- No hacer push sin autorización expresa.
- No hacer merges sin autorización expresa.
- No utilizar OpenCode con `--auto`.
- Revisar los cambios antes de aceptarlos.
- No sobrescribir cambios locales existentes.

Estado conocido antes de la última interrupción:

- Había cambios locales sin commit.
- La rama `mejoras-ia-cli` estaba alineada con el mismo commit base que `main` y `origin/main`.
- Los cambios de trabajo estaban en el árbol local.
- No se habían realizado commits ni push durante las fases descritas.

Archivos locales que deben preservarse:

- `.env`
- `certs/`
- `prueba_resumen.txt`

**PROHIBIDO leer, mostrar, copiar, modificar o divulgar el contenido de `.env`.**

No tocar los certificados locales ni el archivo de prueba salvo autorización expresa.

# 5. CAPA DE INTELIGENCIA ARTIFICIAL

El CLI utiliza el servicio local `ia.simarro` del centro.

Endpoint conocido:

`https://10.100.22.107/llmapi/v1`

Modelo utilizado:

`Qwen38-DualSpark-low`

Acciones IA existentes:

- `resumir-ia`
- `tarea-ia`

El proveedor utiliza autenticación Bearer y soporte para certificados mediante `TAREAS_CA_BUNDLE`.

Se ha trabajado en:

- Reutilización del contexto SSL.
- Verificación TLS.
- Eliminación de comprobaciones redundantes de disponibilidad.
- Tratamiento de errores.
- Documentación de configuración.

## Autenticación del profesor

Una petición HTTPS sin cabecera de autorización devolvió:

`401 Unauthorized`

Esto demuestra que el servidor exige autorización, pero no demuestra que el profesor carezca de acceso institucional.

El profesor es uno de los colaboradores y principales desarrolladores de la IA local del centro.

La autenticación del profesor queda pendiente de comprobar al final con el responsable de `ia.simarro`.

No introducir claves en el código ni distribuir la API Key personal del alumno.

Mientras tanto, desarrollar y probar todo lo que no dependa de esa autorización.

# 6. HISTORIAL DE PRUEBAS

## Resultados anteriores

Antes de ampliar las pruebas existían:

- 9 pruebas superadas.

Primera ampliación:

- 79 pruebas superadas.

Segunda ampliación:

- 83 pruebas superadas.

Se añadieron pruebas para:

- Configuración JSON.
- Validación de parámetros.
- Motor.
- Acciones internas.
- Comandos personalizados.
- CLI.
- Simulación.
- Confirmación y cancelación.
- Modo offline de las acciones IA.

Se utilizaron datos temporales y mocks.

No se llamó a Qwen durante esas pruebas.

## Última fase: tratamiento de fechas y errores

Se crearon dos archivos nuevos:

- `tests/test_tarea_ia.py`
- `tests/test_proveedor_centro_errores.py`

Primera ejecución:

`uv run pytest -q tests/test_tarea_ia.py tests/test_proveedor_centro_errores.py`

Resultado:

- 9 passed.
- 22 failed.

OpenCode detectó un problema conceptual en algunas expectativas de las pruebas.

La separación correcta debe ser:

1. `ProveedorCentro`: comunicación HTTP, autenticación, TLS, timeout y errores del servicio.
2. `generar_texto()`: recibe y devuelve texto generado por el modelo; no debe exigir JSON.
3. `tarea_ia()`: interpreta la respuesta y valida fechas, campos obligatorios, prioridades y estructura de la tarea.

Por tanto, respuestas como `no-json` o `[]` pueden ser texto válido para `generar_texto()`, aunque no representen una tarea válida.

## Última situación conocida

Se pidió a OpenCode corregir exclusivamente las pruebas nuevas, sin modificar producción.

En la última captura:

- Estaba revisando `tests/test_proveedor_centro_errores.py`.
- Estaba revisando `tests/test_tarea_ia.py`.
- Había confirmado la rama `mejoras-ia-cli`.
- OpenCode mostró un mensaje de límite de uso alcanzado.

**No se dispone todavía de un resultado final que confirme si las pruebas se corrigieron.**

No asumir que esa última iteración terminó ni que las pruebas pasan.

El resultado de 83 pruebas corresponde a la fase anterior, no a la suite actual necesariamente.

# 7. PROBLEMAS PENDIENTES

1. Corregir y verificar las pruebas nuevas de `tarea-ia` y del proveedor.
2. Ejecutar la suite completa y recuperar una base estable.
3. Corregir el tratamiento de fechas de `tarea-ia`.
4. Diferenciar errores de autenticación, configuración, conexión, timeout y respuesta inválida.
5. Revisar límites de lectura de archivos y privacidad en `resumir-ia`.
6. Revisar timeout y captura de salida en comandos personalizados.
7. Completar pruebas de regresión.
8. Revisar y actualizar README.
9. Verificar instalación limpia con `uv tool install`.
10. Configurar GitHub Actions.
11. Valorar linter, formatter y cobertura.
12. Crear una matriz definitiva de evidencias de la rúbrica.
13. Diseñar el agente `Profesor Reviewer`.
14. Verificar la autenticación del profesor con Qwen.
15. Preparar release `v1.0`, changelog e historial Git.

# 8. AGENTE FUTURO: PROFESOR REVIEWER

Queremos crear un agente evaluador especializado llamado `Profesor Reviewer`.

Su función será actuar como un evaluador técnico exigente que simule el proceso de instalación y utilización del CLI por parte del profesor.

Responsabilidades:

- Evaluar los siete criterios de la rúbrica.
- Comprobar los cuatro requisitos mínimos.
- Instalar el proyecto desde cero.
- Ejecutar comandos y acciones.
- Comprobar acciones personalizadas desde JSON.
- Comprobar acciones IA cuando exista autorización.
- Buscar errores y casos límite.
- Revisar seguridad y protección de secretos.
- Revisar documentación.
- Comprobar pruebas y CI.
- Emitir una puntuación razonada con evidencias.
- Identificar fallos y mejoras pendientes.

Restricciones:

- Debe ser un agente evaluador de solo lectura.
- No puede modificar código.
- No puede hacer commits ni push.
- No puede aprobar cambios por su cuenta.
- No debe regalar puntuaciones.
- Debe justificar cada valoración con evidencias reproducibles.

# 9. CREATIVIDAD Y ORIGINALIDAD

No queremos un CLI genérico.

Una vez conseguida una base estable, debemos explorar funciones originales y útiles.

Ideas iniciales:

- Planificador inteligente de organización de carpetas.
- Historial local opcional de operaciones.
- Perfiles de acciones según el proyecto.
- Previsualización de operaciones antes de ejecutarlas.
- Sugerencias inteligentes de organización.
- Sistema de acciones combinables.

Cualquier operación que pueda mover, borrar o sobrescribir archivos debe tener protecciones, simulación o confirmación.

Estas ideas son propuestas futuras, no funcionalidades implementadas.

# 10. REGLAS DE TRABAJO CON OPENCODE

Estas reglas son obligatorias en todas las sesiones:

1. Trabajar exclusivamente en `mejoras-ia-cli`.
2. Analizar antes de modificar.
3. Presentar un plan antes de cambios importantes.
4. Trabajar progresivamente.
5. Escribir pruebas antes de cambiar comportamiento cuando sea posible.
6. Ejecutar pruebas después de cada cambio.
7. Detenerse ante errores inesperados.
8. No ocultar fallos eliminando pruebas válidas.
9. No modificar archivos fuera del alcance autorizado.
10. No leer ni modificar `.env`.
11. No tocar `certs/` ni `prueba_resumen.txt`.
12. No introducir secretos en el código ni en Git.
13. No utilizar `--auto`.
14. No hacer commits, merges ni push sin autorización.
15. El alumno revisa los diffs y decide qué cambios acepta.

Utilizar directorios temporales para las pruebas.

No realizar operaciones destructivas sobre carpetas reales.

# 11. FORMA DE TRABAJO ENTRE CHATGPT Y OPENCODE

ChatGPT supervisa el proyecto y ayuda a decidir las siguientes tareas.

OpenCode analiza, programa y ejecuta las pruebas.

Flujo de trabajo:

1. ChatGPT revisa el estado y define el siguiente objetivo.
2. El alumno proporciona a OpenCode las instrucciones aprobadas.
3. OpenCode realiza el trabajo.
4. El alumno comparte aquí el resultado.
5. ChatGPT revisa los cambios y resultados.
6. Se decide si se aprueba la siguiente fase.

No generar nuevos prompts ni autorizar fases adicionales sin revisar primero la respuesta anterior de OpenCode.

# 12. PRÓXIMO PASO EXACTO

Al iniciar una nueva sesión:

1. Leer este documento completo.
2. Comprobar la rama actual y el estado de Git.
3. Revisar los archivos nuevos de pruebas:
   - `tests/test_tarea_ia.py`
   - `tests/test_proveedor_centro_errores.py`
4. Comprobar si OpenCode llegó a terminar la última iteración.
5. No asumir resultados de pruebas anteriores como actuales.
6. No modificar producción todavía.
7. Continuar corrigiendo las expectativas de las pruebas para respetar la separación de responsabilidades.
8. Ejecutar primero las pruebas específicas y después la suite completa si las primeras pasan.
9. Presentar un informe con evidencias y archivos modificados.

**La prioridad inmediata es recuperar una base de pruebas coherente y estable antes de modificar el comportamiento de producción.**

---

# OBJETIVO FINAL

Entregar un CLI que no solo cumpla la rúbrica, sino que destaque por su calidad técnica, seguridad, facilidad de uso, creatividad y originalidad.

No buscamos simplemente que funcione en el ordenador del alumno.

Buscamos que cualquier profesor pueda instalarlo, entenderlo, utilizarlo y comprobar que está bien construido.

**Objetivo: sobresaliente real, demostrado con evidencias.**
