"""Presentación visual de la terminal: encabezado, estados y menú."""

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
