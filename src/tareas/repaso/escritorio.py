"""Apertura del repaso en LibreOffice Writer.

Detecta la instalación sin bloquear la terminal: la orden se lanza en segundo
plano y, si Writer no está disponible, se informa de la ruta para abrirlo a mano.
"""

import shutil
import subprocess
from pathlib import Path

PROGRAMAS = ("soffice", "libreoffice")


class EscritorioNoDisponible(Exception):
    """LibreOffice no está instalado o no se pudo lanzar."""


def localizar_writer() -> str | None:
    """Devuelve el ejecutable de LibreOffice o None si no está instalado."""
    return next((shutil.which(p) for p in PROGRAMAS if shutil.which(p)), None)


def abrir_en_writer(ruta: Path) -> str:
    """Abre el documento en LibreOffice Writer sin bloquear la CLI.

    Devuelve el nombre del programa usado. Lanza EscritorioNoDisponible si no
    está instalado o si el arranque falla; nunca deja procesos colgados.
    """
    programa = localizar_writer()
    if programa is None:
        raise EscritorioNoDisponible(
            "LibreOffice no está instalado; abre el documento manualmente."
        )
    try:
        subprocess.Popen(
            [programa, "--writer", str(ruta)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise EscritorioNoDisponible(
            f"No se pudo abrir LibreOffice ({exc}); abre el documento manualmente."
        ) from exc
    return programa
