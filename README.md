# tareas

Mi herramienta de línea de órdenes para automatizar tareas repetitivas con ficheros.

## Spec (versión 0 · 29/10/2026)
1. **Problema:** cada semana pierdo tiempo ordenando Descargas a mano.
2. **Para quién:** para mí y para mis compañeros de clase.
3. **Cómo se usa:** `tareas ORDEN [CARPETA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes previstas:** `tareas acciones`, `tareas validar`, `tareas ejecutar NOMBRE --simular`.
6. **Mis 3 acciones (borrador):** clasificar por extensión, borrar temporales de +30 días, renombrar fotos por fecha.
7. **Nunca hará:** borrar sin preguntar ni tocar ficheros fuera de la carpeta indicada.
8. **Plataformas:** Linux primero; también Windows y macOS.
9. **Códigos de salida:** 0 bien · 1 fallo al ejecutar · 2 uso incorrecto · 3 configuración inválida.
10. **Instalación:** `uv tool install --editable .`
