"""Presentación visual de la terminal: encabezado, estados, menú y progreso."""

import sys
from collections.abc import Callable

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tareas.modelos import Accion

_ETIQUETAS = {"ok": "OK", "error": "ERROR", "aviso": "AVISO", "info": "INFO"}
_ESTILOS = {"ok": "green", "error": "red", "aviso": "yellow", "info": "cyan"}


def encabezado(
    consola: Console,
    subtitulo: str = "automatiza tareas repetitivas con tus ficheros",
) -> None:
    """Imprime el banner principal del CLI."""
    contenido = Text()
    contenido.append("TAREAS", style="bold cyan")
    contenido.append("\n")
    contenido.append(subtitulo, style="dim")
    consola.print(
        Panel(contenido, border_style="cyan", expand=False, padding=(0, 2))
    )


def estado(consola: Console, mensaje: str, tipo: str = "info") -> None:
    """Imprime un mensaje breve con color según su naturaleza."""
    etiqueta = _ETIQUETAS.get(tipo, "INFO")
    estilo = _ESTILOS.get(tipo, "cyan")
    consola.print(f"[{estilo}]{etiqueta}[/{estilo}] {escape(mensaje)}")


def tabla_menu(acciones: list[Accion]) -> Table:
    """Construye la tabla numerada del menú interactivo."""
    tabla = Table(title="Acciones disponibles", expand=False)
    tabla.add_column("#", justify="right", style="bold cyan")
    tabla.add_column("Acción", style="bold")
    tabla.add_column("Descripción")
    tabla.add_column("IA", justify="center")
    for indice, accion in enumerate(acciones, start=1):
        tabla.add_row(
            str(indice),
            accion.nombre,
            accion.descripcion,
            "sí" if accion.ia else "",
        )
    tabla.add_row("0", "Salir", "Termina el menú", "")
    return tabla


_FASES = ("⣙", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿")


class Progreso:
    """Indicador compacto de una sola línea para operaciones largas.

    En terminal interactiva muestra un spinner de tres puntos, fase, contador
    y porcentaje real sobre una única línea que se actualiza (\\r). Con la
    salida redirigida o sin TTY imprime solo las fases y, al terminar, una
    línea resumen: nunca inunda la consola. `avanzar()` refleja trabajo real
    (una unidad = una tarea completada), nunca inventa porcentaje.
    """

    def __init__(
        self,
        total: int,
        fase_inicial: str,
        imprimir: Callable[[str], None] | None = None,
        es_tty: bool | None = None,
    ) -> None:
        self._total = max(0, int(total))
        self._hecho = 0
        self._fase = fase_inicial
        self._gira = 0
        self._imprimir = imprimir or (lambda texto: print(texto, flush=True))
        self._tty = sys.stdout.isatty() if es_tty is None else es_tty
        self._ultima = ""

    @property
    def hecho(self) -> int:
        return self._hecho

    @property
    def fase(self) -> str:
        return self._fase

    def _dibujar(self, texto: str) -> None:
        if not self._tty:
            return
        if texto != self._ultima:
            sys.stdout.write("\r\033[K" + texto)
            sys.stdout.flush()
            self._ultima = texto

    def cambiar_fase(self, nombre: str) -> None:
        """Cambia de fase; en no-TTY la imprime como línea suelta."""
        self._fase = nombre
        if not self._tty:
            self._imprimir(f"{nombre}…")
        else:
            self._actualiza()

    def avanzar(self, unidades: int = 1) -> None:
        """Registra unidades terminadas y redibuja la línea de progreso."""
        self._hecho = min(self._total, self._hecho + unidades)
        if self._tty:
            self._actualiza()

    def _actualiza(self) -> None:
        if self._total <= 0:
            self._dibujar(f"{self._fase}…")
            return
        simbolo = _FASES[self._gira % len(_FASES)]
        self._gira += 1
        porcentaje = int(self._hecho * 100 / self._total)
        self._dibujar(
            f"{simbolo} {self._fase} · {self._hecho}/{self._total} ({porcentaje}%)"
        )

    def cerrar(self) -> None:
        """Termina la línea: en TTY borra el spinner; en no-TTY, resumen final."""
        if self._tty:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            self._ultima = ""
        else:
            self._imprimir(
                f"{self._fase}: {self._hecho}/{self._total} completado."
            )

    def abortar(self, mensaje: str) -> None:
        """Limpia el spinner y muestra el error (que debe quedar visible)."""
        if self._tty:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            self._ultima = ""
        self._imprimir(f"Interrumpido: {mensaje}")
