"""Carga segura de la clave de IA desde entorno o .env local."""

import os
from pathlib import Path


def _clave_env(ruta: Path) -> str | None:
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        if nombre.strip() == "TAREAS_API_KEY":
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                valor = valor[1:-1]
            return valor or None
    return None


def obtener_clave(ruta_env: Path | None = None) -> str | None:
    """Devuelve la clave del entorno antes de consultar el .env local."""
    clave_entorno = os.environ.get("TAREAS_API_KEY")
    if clave_entorno:
        return clave_entorno
    return _clave_env(ruta_env or Path.cwd() / ".env")
