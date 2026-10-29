"""Interfaces que conectan el motor con sus adaptadores."""

from pathlib import Path
from typing import Protocol

from tareas.ia.proveedor import ProveedorIA
from tareas.modelos import Accion, ContextoAccion, ResultadoAccion


class CargadorAcciones(Protocol):
    """Lee y valida las acciones declaradas por el usuario."""

    def cargar(self, ruta: Path) -> list[Accion]:
        """Devuelve las acciones o lanza ConfigError."""
        ...


class EjecutorAccion(Protocol):
    """Adaptador que sabe previsualizar y ejecutar una acción."""

    def previsualizar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Describe lo que haría, sin efectos secundarios."""
        ...

    def ejecutar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Ejecuta la acción de verdad."""
        ...


class Confirmador(Protocol):
    """Pregunta al usuario si autoriza una acción destructiva."""

    def __call__(self, accion: Accion) -> bool:
        """Devuelve True si el usuario confirma."""
        ...


__all__ = [
    "CargadorAcciones",
    "EjecutorAccion",
    "Confirmador",
    "ProveedorIA",
]
