"""Carga segura de la clave de IA y de la CA del centro desde el entorno local.

Las variables `TAREAS_API_KEY` y `TAREAS_CA_BUNDLE` pueden definirse como
variables de entorno o en un `.env` local (ignorado por Git). La variable de
entorno tiene siempre prioridad; el `.env` solo se usa como respaldo. Sin CA
configurada y con un certificado corporativo autofirmado, TLS falla con el
almacén de confianza del sistema: por eso el `.env` también puede aportar la
ruta de la CA (expandida `~`), nunca el propio certificado.
"""

import os
from pathlib import Path


def _variables_env(ruta: Path, nombre: str) -> str | None:
    """Devuelve el valor de `nombre` en el `.env` indicado, o None."""
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        if clave.strip() != nombre:
            continue
        valor = valor.split(" #", 1)[0].strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        return valor or None
    return None


def obtener_clave(ruta_env: Path | None = None) -> str | None:
    """Devuelve la clave del entorno antes de consultar el `.env` local."""
    return obtener_variable("TAREAS_API_KEY", ruta_env)


def obtener_variable(nombre: str, ruta_env: Path | None = None) -> str | None:
    """En variable de entorno > .env local. Nunca registra ni imprime el valor."""
    valor_entorno = os.environ.get(nombre)
    if valor_entorno:
        return valor_entorno
    valor = _variables_env(ruta_env or Path.cwd() / ".env", nombre)
    if valor and nombre == "TAREAS_CA_BUNDLE":
        valor = str(Path(valor).expanduser())
    return valor
