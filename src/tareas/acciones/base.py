"""Adaptador de acciones implementadas como funciones de Python."""

from collections.abc import Callable
from dataclasses import replace

from tareas.modelos import Accion, ContextoAccion, ResultadoAccion

FuncionAccion = Callable[[ContextoAccion], ResultadoAccion]


class AccionFuncion:
    """Envuelve una función registrada para que cumpla el puerto de ejecución."""

    def __init__(self, accion: Accion, funcion: FuncionAccion) -> None:
        self._accion = accion
        self._funcion = funcion

    def previsualizar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Ejecuta la función en modo simulación."""
        return self._funcion(replace(ctx, simular=True))

    def ejecutar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Ejecuta la función real."""
        return self._funcion(ctx)
