---
description: Crea una acción nueva en acciones.json siguiendo el esquema de tareas.
agent: build
---

Usa la skill `acciones-json` antes de actuar. Ayuda al usuario a añadir una
acción declarada en `acciones.json`.

Primero pregunta, una pregunta cada vez, estos cuatro datos:

1. `nombre`
2. `descripcion`
3. `tipo`: `funcion` o `comando`
4. `destructiva`: `true` o `false`

Si `$ARGUMENTS` ya contiene alguno de esos datos, úsalo como contexto, pero
confirma igualmente los valores finales antes de editar.

Después:

- Lee `acciones.json` y comprueba que sea válido y que el nombre no esté
  repetido ni reservado.
- Revisa la skill y conserva el formato existente del JSON.
- Para `funcion`, exige que `ejecutar` sea el nombre de una función registrada;
  si falta, pregunta el nombre y no inventes una implementación.
- Para `comando`, pregunta el argv como lista de argumentos y no construyas
  una cadena para shell.
- Pregunta los parámetros adicionales solo si la acción los necesita; usa
  exclusivamente los tipos `texto`, `entero`, `ruta` o `booleano`.
- No añadas el campo `ia`: el cargador v1 actual lo rechaza aunque esté
  documentado como campo previsto.
- Muestra el objeto JSON que vas a insertar y pide confirmación explícita.
- Solo tras la confirmación edita `acciones.json`, sin tocar `motor.py`,
  `cli.py` ni otros ficheros.
- Valida el resultado con `uv run tareas acciones` y reporta el resultado.

No ejecutes acciones nuevas ni hagas commits automáticamente. Si el usuario
no confirma, no edites ningún fichero.
