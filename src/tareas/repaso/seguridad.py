"""Confinamiento de rutas y mensajes de seguridad compartidos por las acciones.

Este módulo centraliza la política de «no tocar nada fuera de la raíz
autorizada» que comparten `borrar` y `repaso-ia`, y la forma de presentar los
fallos del proveedor IA sin exponer detalles técnicos ni secretos.
"""

from pathlib import Path


class RutaFueraDeBaseError(Exception):
    """La ruta solicitada sale de la raíz autorizada para borrar."""


def fuera_de_base(ruta: Path, base: Path) -> bool:
    """True si la ruta (ya resuelta) escapa de la raíz autorizada."""
    try:
        ruta.relative_to(base)
    except ValueError:
        return True
    return False


def ruta_dentro_de_base(requisitada: Path, base: Path, *, absolute: bool = False) -> Path:
    """Resuelve la ruta dentro de la raíz autorizada o lanza RutaFueraDeBaseError.

    Con `absolute=True` (modo `borrar`) se resuelve con `strict=True`, de forma
    equivalente a `Path.resolve()` en Python 3.10+. El fallo de resolución se
    informa como salida fuera de la raíz, igual que antes de esta extracción.
    """
    ruta = requisitada
    if not ruta.is_absolute():
        ruta = base / ruta
    try:
        ruta = ruta.resolve(strict=absolute)
    except OSError as exc:
        raise RutaFueraDeBaseError(
            f"La ruta «{requisitada}» queda fuera de la raíz autorizada «{base}»."
        ) from exc
    if fuera_de_base(ruta, base):
        raise RutaFueraDeBaseError(
            f"La ruta «{requisitada}» queda fuera de la raíz autorizada «{base}»."
        )
    return ruta


def ruta_salida(requisitada: Path, base: Path) -> Path:
    """Resuelve la salida dentro de la raíz autorizada, con mensaje propio."""
    ruta = requisitada
    if not ruta.is_absolute():
        ruta = base / ruta
    ruta = ruta.resolve()
    if fuera_de_base(ruta, base):
        raise RutaFueraDeBaseError(
            f"La ruta de salida «{requisitada}» queda fuera de la raíz autorizada «{base}»."
        )
    return ruta


def objetivo_normal(objetivo: str | None) -> str:
    """Normaliza el objetivo de estudio a una frase legible y conocida."""
    valor = (objetivo or "").strip().casefold()
    equivalentes = {
        "test": "examen tipo test",
        "tipo test": "examen tipo test",
        "tipo_test": "examen tipo test",
        "desarrollo": "examen de desarrollo",
        "examen desarrollo": "examen de desarrollo",
        "general": "repaso general",
        "": "repaso general",
    }
    return equivalentes.get(valor, objetivo or "repaso general")


def con_etapa(mensaje: str, exc: BaseException) -> str:
    """Añade la etapa del fallo al mensaje humano, sin exponer secretos."""
    etapa = getattr(exc, "etapa", "") or ""
    return f"{mensaje} (etapa: {etapa})" if etapa else mensaje
