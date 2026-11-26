"""Esquemas y diagramas generados localmente, sin servicios externos.

Los diagramas se dibujan en texto monoespaciado (cajas, flechas y líneas de
tiempo) a partir del documento maestro, de forma determinista: nunca inventan
contenido. Si un esquema no es posible, se ofrece la tabla equivalente.
"""

import re

_ANCHO_MINIMO = 24
_ANCHO_MAXIMO = 44

_ESQUEMA = "esquema"
_TABLA = "tabla"
_TIMELINE = "timeline"
_LISTA = "lista"

TIPOS = (_ESQUEMA, _TABLA, _TIMELINE, _LISTA)

_FECHA = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)")


class Esquema:
    """Representación textual de un esquema con su tabla equivalente."""

    def __init__(self, titulo: str, filas: list[str], columnas: tuple[str, ...], tipo: str):
        self.titulo = titulo
        self.filas = filas
        self.columnas = columnas
        self.tipo = tipo
        self.especificacion = ""

    @property
    def entradas(self) -> list[tuple[str, str]]:
        """Pares (etiqueta, detalle) de cada caja del esquema."""
        pares = []
        for fila in self.filas:
            etiqueta, separador, detalle = fila.partition("::")
            pares.append((etiqueta.strip(), (detalle if separador else "").strip()))
        return pares

    @property
    def tabla(self) -> list[list[str]]:
        """Tabla equivalente: misma información, formato distinto."""
        cabecera = list(self.columnas)
        filas = []
        for etiqueta, detalle in self.entradas:
            filas.append([etiqueta, detalle])
        return [cabecera, *filas]


def _normalizar_detalle(detalle: str) -> str:
    detalle = re.sub(r"\s+", " ", detalle).strip(" .;")
    if len(detalle) > _ANCHO_MAXIMO:
        corte = detalle.rfind(" ", 0, _ANCHO_MAXIMO)
        detalle = detalle[: corte if corte > 12 else _ANCHO_MAXIMO].rstrip(" ,;") + "…"
    return detalle or "—"


def detectar(especificacion: str) -> Esquema | None:
    """Convierte una especificación de esquema devuelta por la IA en un dibujo.

    Formato aceptado (una línea por nodo): `TIPO: etiqueta :: detalle`, donde
    TIPO es esquema, tabla, timeline o lista. La etiqueta y el detalle salen
    siempre del documento; el dibujo es mecánico.
    """
    lineas = [linea.strip() for linea in especificacion.splitlines() if linea.strip()]
    if not lineas:
        return None

    tipo = None
    for linea in lineas:
        for candidato in TIPOS:
            if linea.lower().startswith(f"{candidato}:"):
                tipo = candidato
                break
        if tipo:
            break

    entradas: list[tuple[str, str]] = []
    for linea in lineas:
        limpio = re.sub(r"^[-*•]\s*", "", linea)
        if limpio == "|":
            continue
        for prefijo in TIPOS:
            if limpio.lower().startswith(f"{prefijo}:"):
                limpio = limpio.split(":", 1)[1].strip()
                break
        if not limpio:
            continue
        etiqueta, separador, detalle = limpio.partition("::")
        etiqueta = _normalizar_detalle(etiqueta)
        if len(etiqueta) > _ANCHO_MINIMO:
            etiqueta = etiqueta[:_ANCHO_MINIMO].rstrip(" ,;") + "…"
        entradas.append((etiqueta, _normalizar_detalle(detalle) if separador else ""))

    if len(entradas) < 2:
        return None

    if tipo is None:
        fechas = [_FECHA.search(etiqueta + " " + detalle) for etiqueta, detalle in entradas]
        tipo = _TIMELINE if all(fechas) else _ESQUEMA

    columnas = {
        _ESQUEMA: ("Bloque", "Idea clave"),
        _TABLA: ("Elemento", "Características"),
        _TIMELINE: ("Momento", "Qué ocurrió"),
        _LISTA: ("Concepto", "Detalle"),
    }[tipo]

    filas = [
        f"{etiqueta}::{detalle}" if detalle else etiqueta
        for etiqueta, detalle in entradas
    ]
    esquema = Esquema(
        titulo="Esquema del repaso",
        filas=filas,
        columnas=columnas,
        tipo=tipo,
    )
    esquema.especificacion = especificacion
    return esquema


def _encajar(texto: str, ancho: int) -> list[str]:
    palabras = texto.split()
    lineas: list[str] = []
    actual = ""
    for palabra in palabras:
        candidato = f"{actual} {palabra}".strip()
        if actual and len(candidato) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = candidato
    if actual:
        lineas.append(actual)
    return lineas


def _caja(etiqueta: str, detalle: str, ancho: int) -> list[str]:
    interior = ancho - 4
    lineas = [etiqueta]
    if detalle:
        lineas.append(f"({detalle})")
    volcadas: list[str] = []
    for linea in lineas:
        volcadas.extend(_encajar(linea, interior))
    cuadro = ["┌" + "─" * (ancho - 2) + "┐"]
    for linea in volcadas:
        cuadro.append("│ " + linea.ljust(interior) + " │")
    cuadro.append("└" + "─" * (ancho - 2) + "┘")
    return cuadro


def dibujar(esquema: Esquema) -> list[str]:
    """Devuelve las líneas monoespaciadas del diagrama."""
    entradas = esquema.entradas
    ancho = min(
        _ANCHO_MAXIMO,
        max(_ANCHO_MINIMO, max(len(e) for e, _ in entradas) + 4),
    )

    if esquema.tipo in ("esquema", "lista"):
        lineas: list[str] = []
        for etiqueta, detalle in entradas:
            lineas.extend(_caja(etiqueta, detalle, ancho))
            lineas.append("".center(ancho, " ") + " │")
            lineas.append("".center(ancho, " ") + " ▼")
        if lineas and lineas[-1].strip() == "▼":
            lineas = lineas[:-2]
        return lineas

    if esquema.tipo == "tabla":
        cabecera = list(esquema.columnas)
        anchos = [max(len(cabecera[0]), *(len(e) for e, _ in entradas)) + 2,
                  max(len(cabecera[1]), *(len(d) for _, d in entradas)) + 2]
        separador = "├" + "─" * anchos[0] + "┼" + "─" * anchos[1] + "┤"
        superior = "┌" + "─" * anchos[0] + "┬" + "─" * anchos[1] + "┐"
        inferior = "└" + "─" * anchos[0] + "┴" + "─" * anchos[1] + "┘"
        lineas = [superior,
                  "│ " + cabecera[0].ljust(anchos[0] - 2) + " │ " + cabecera[1].ljust(anchos[1] - 2) + " │",
                  separador]
        for etiqueta, detalle in entradas:
            lineas.append("│ " + etiqueta.ljust(anchos[0] - 2) + " │ " + detalle.ljust(anchos[1] - 2) + " │")
        lineas.append(inferior)
        return lineas

    lineas = [""] * 0
    eje = "●"
    for indice, (etiqueta, detalle) in enumerate(entradas):
        prefijo = "├─" if indice < len(entradas) - 1 else "└─"
        lineas.append(f"{prefijo} {eje} {etiqueta}")
        if detalle:
            lineas.append(f"{'│' if indice < len(entradas) - 1 else ' '}     {detalle}")
        elif indice < len(entradas) - 1:
            lineas.append("│")
    return lineas
