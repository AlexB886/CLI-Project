"""Acciones que ejecutan una orden externa sin pasar por un shell."""

import shlex
import subprocess
from pathlib import Path

from tareas.modelos import Accion, ContextoAccion, ResultadoAccion


def _expandir(argumento: str) -> str:
    if argumento.startswith("~"):
        return str(Path(argumento).expanduser())
    return argumento


class AccionComando:
    """Ejecuta un argv declarado en acciones.json."""

    def __init__(self, accion: Accion) -> None:
        self._accion = accion
        argv = accion.ejecutar
        if not isinstance(argv, tuple) or not argv:
            raise ValueError(f"La acción «{accion.nombre}» no tiene un comando válido.")
        self._argv = tuple(_expandir(argumento) for argumento in argv)

    def previsualizar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Muestra la orden que se ejecutaría, sin lanzarla."""
        return ResultadoAccion(
            codigo=0,
            salida=f"Ejecutaría: {shlex.join(self._argv)}",
        )

    def ejecutar(self, ctx: ContextoAccion) -> ResultadoAccion:
        """Lanza la orden con subprocess y sin shell."""
        try:
            proceso = subprocess.run(
                self._argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            return ResultadoAccion(
                codigo=1,
                error=f"No se encontró la orden «{self._argv[0]}».",
            )
        except OSError as exc:
            return ResultadoAccion(
                codigo=1,
                error=f"No se pudo ejecutar «{self._argv[0]}»: {exc}",
            )

        codigo = proceso.returncode if proceso.returncode >= 0 else 1
        error = proceso.stderr
        if codigo != 0 and not error:
            error = f"La orden terminó con código {codigo}."
        return ResultadoAccion(
            codigo=codigo,
            salida=proceso.stdout,
            error=error,
        )
