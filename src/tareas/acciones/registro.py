"""Registro seguro de funciones que pueden invocarse desde acciones.json."""

from collections.abc import Callable

from tareas.acciones.base import AccionFuncion, FuncionAccion
from tareas.acciones.comando import AccionComando
from tareas.errores import ConfigError
from tareas.modelos import Accion, TipoEjecucion
from tareas.puertos import EjecutorAccion


class RegistroAcciones:
    """Asocia nombres de acciones.json con funciones internas."""

    def __init__(self) -> None:
        self._funciones: dict[str, FuncionAccion] = {}

    def registrar(self, nombre: str, funcion: FuncionAccion) -> None:
        """Añade una función al registro."""
        self._funciones[nombre] = funcion

    def obtener(self, nombre: str) -> FuncionAccion:
        """Devuelve una función registrada o lanza ConfigError."""
        try:
            return self._funciones[nombre]
        except KeyError as exc:
            disponibles = ", ".join(sorted(self._funciones)) or "ninguna"
            raise ConfigError(
                f"La función «{nombre}» no está registrada. "
                f"Funciones disponibles: {disponibles}."
            ) from exc

    def construir(self, accion: Accion) -> EjecutorAccion:
        """Convierte una Accion de JSON en un ejecutor concreto."""
        if accion.tipo is TipoEjecucion.FUNCION:
            if not isinstance(accion.ejecutar, str):
                raise ConfigError(
                    f"La acción «{accion.nombre}» debe indicar una función como texto."
                )
            return AccionFuncion(accion, self.obtener(accion.ejecutar))
        if accion.tipo is TipoEjecucion.COMANDO:
            if not isinstance(accion.ejecutar, tuple):
                raise ConfigError(
                    f"La acción «{accion.nombre}» debe indicar un comando como lista."
                )
            return AccionComando(accion)
        raise ConfigError(f"La acción «{accion.nombre}» tiene un tipo desconocido.")


registro = RegistroAcciones()


def registrar(nombre: str) -> Callable[[FuncionAccion], FuncionAccion]:
    """Decorador para registrar una función interna."""

    def decorador(funcion: FuncionAccion) -> FuncionAccion:
        registro.registrar(nombre, funcion)
        return funcion

    return decorador
