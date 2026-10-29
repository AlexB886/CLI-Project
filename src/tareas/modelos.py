"""Modelos de dominio del motor de acciones."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TipoEjecucion(str, Enum):
    """Forma en la que se ejecuta una acción."""

    FUNCION = "funcion"
    COMANDO = "comando"


@dataclass(frozen=True)
class Parametro:
    """Parámetro declarado por una acción en acciones.json."""

    nombre: str
    tipo: str = "texto"
    requerido: bool = False
    por_defecto: Any = None
    ayuda: str = ""


@dataclass(frozen=True)
class Accion:
    """Acción leída de acciones.json."""

    nombre: str
    descripcion: str
    tipo: TipoEjecucion
    ejecutar: str | tuple[str, ...]
    destructiva: bool
    parametros: tuple[Parametro, ...] = ()


@dataclass(frozen=True)
class ContextoAccion:
    """Datos que recibe una acción al ejecutarse."""

    parametros: dict[str, Any]
    simular: bool = False


@dataclass(frozen=True)
class TablaContenido:
    """Tabla genérica para que el CLI la pinte con Rich."""

    titulo: str
    columnas: tuple[str, ...]
    filas: tuple[tuple[str, ...], ...]
    alinear_derecha: tuple[int, ...] = ()


@dataclass(frozen=True)
class ResultadoAccion:
    """Resultado de una acción, independiente de la interfaz."""

    codigo: int = 0
    salida: str = ""
    error: str = ""
    datos: Any = None
