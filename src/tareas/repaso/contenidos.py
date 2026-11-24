"""Normalización del documento maestro de la IA y composición del repaso.

Todo el contenido procede del maestro generado a partir de los apuntes; este
módulo solo reordena, normaliza títulos de sección e inserta los esquemas.
Nunca redacta contenido propio.
"""

import re

from tareas.repaso.esquemas import Esquema, detectar, dibujar

SECCIONES_ESPERADAS = (
    "Introducción",
    "Resumen por apartados",
    "Conceptos clave",
    "Explicaciones didácticas",
    "Tablas comparativas",
    "Esquemas",
    "Errores y confusiones frecuentes",
    "Repaso final de lo imprescindible",
    "Preguntas para el examen",
)

_FALTA_AVISO = "(La IA no generó esta sección a partir de los apuntes.)"
_ESQUEMA_MARCA = re.compile(
    r"^\s*#{0,4}\s*esquema\s*$|^\s*#{1,4}\s*ESQUEMA\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_CLAVES = {
    "Introducción": ("introducc", "presentac", "contexto"),
    "Resumen por apartados": ("resumen", "desarrollo", "apartados", "contenido", "síntesis"),
    "Conceptos clave": ("concept", "definicion", "glosario", "vocabulario", "término"),
    "Explicaciones didácticas": ("explicac", "didáctic", "aclarac"),
    "Tablas comparativas": ("tabla", "comparat"),
    "Esquemas": ("esquema", "diagrama", "mapa"),
    "Errores y confusiones frecuentes": ("error", "confusi", "equivoc"),
    "Repaso final de lo imprescindible": ("imprescind", "esencial", "conclusi", "final"),
    "Preguntas para el examen": ("pregunta", "examen", "cuestion", "autocompro"),
}

_EQUIVALENCIAS = {
    "introduction": "Introducción",
    "summary": "Resumen por apartados",
    "overview": "Resumen por apartados",
    "key concepts": "Conceptos clave",
    "definitions": "Conceptos clave",
    "glossary": "Conceptos clave",
    "explanations": "Explicaciones didácticas",
    "comparison tables": "Tablas comparativas",
    "diagrams": "Esquemas",
    "common mistakes": "Errores y confusiones frecuentes",
    "final review": "Repaso final de lo imprescindible",
    "exam questions": "Preguntas para el examen",
    "questions": "Preguntas para el examen",
}


class Seccion:
    """Sección del repaso con su título canónico y su cuerpo en texto plano."""

    def __init__(self, titulo: str, cuerpo: list[str], subtitulo: bool = False):
        self.titulo = titulo
        self.cuerpo = [linea.rstrip() for linea in cuerpo]
        self.subtitulo = subtitulo

    @property
    def vacia(self) -> bool:
        return not any(linea.strip() for linea in self.cuerpo)


def _es_esquema(linea: str) -> bool:
    return _ESQUEMA_MARCA.match(linea.strip()) is not None


def _limpiar_esquemas(cuerpo: list[str]) -> list[str]:
    """Quita los bloques ESQUEMA del flujo normal: se dibujan aparte."""
    limpio: list[str] = []
    para = False
    for linea in cuerpo:
        if _es_esquema(linea):
            para = True
            continue
        if para:
            if not linea.strip():
                para = False
            continue
        limpio.append(linea)
    while limpio and not limpio[0].strip():
        limpio.pop(0)
    return limpio


def _purgar_esquemas_internos(texto: str) -> str:
    """Borra las líneas de esquema que hayan quedado sueltas dentro de otra sección."""
    salta = False
    lineas: list[str] = []
    for linea in texto.splitlines():
        if _es_esquema(linea):
            salta = True
            continue
        if salta:
            if not linea.strip():
                salta = False
            else:
                continue
        lineas.append(linea)
    return "\n".join(lineas)


def _cortar_en_esquema(texto: str) -> str:
    """Recorta cada sección en su primer bloque ESQUEMA (el resto se dibuja aparte)."""
    partes: list[str] = []
    for bloque in re.split(r"(?=^#{1,3}\s+)", texto, flags=re.MULTILINE):
        lineas = bloque.splitlines()
        for indice, linea in enumerate(lineas):
            if _es_esquema(linea):
                partes.append("\n".join(lineas[:indice]))
                break
        else:
            partes.append(bloque)
    return "\n".join(partes)


def _normalizar_ingles(titulo: str) -> str:
    """Traduce títulos de sección habituales en inglés al catálogo español."""
    return _EQUIVALENCIAS.get(titulo.casefold().strip(" .:"), titulo)


def _detectar_destino(titulo: str) -> str | None:
    bajo = _normalizar_ingles(titulo).casefold()
    for destino, claves in _CLAVES.items():
        if any(clave in bajo for clave in claves):
            return destino
    return None


def detectar_esquemas(maestro: str) -> list[Esquema]:
    """Extrae los bloques marcados con «ESQUEMA» y los convierte en diagramas."""
    esquemas: list[Esquema] = []
    trozos = _ESQUEMA_MARCA.split(maestro)
    for bloque in trozos[1:]:
        lineas: list[str] = []
        for linea in bloque.splitlines():
            if re.match(r"^#{1,3}\s+", linea.strip()):
                break
            if linea.strip():
                lineas.append(linea)
        esquema = detectar("\n".join(lineas))
        if esquema is not None:
            esquemas.append(esquema)
    return esquemas


def construir_documento(maestro: str, esquemas: list[Esquema]) -> list[Seccion]:
    """Reordena el maestro en las secciones fijas del repaso educativo."""
    buckets: dict[str, list[str]] = {titulo: [] for titulo in SECCIONES_ESPERADAS}
    extras: list[Seccion] = []

    for seccion in separar_secciones(_cortar_en_esquema(_purgar_esquemas_internos(maestro))):
        destino = _detectar_destino(seccion.titulo)
        if destino is None:
            extras.append(seccion)
            continue
        cuerpo = _limpiar_esquemas(list(seccion.cuerpo))
        if buckets[destino]:
            cuerpo.insert(0, seccion.titulo)
        buckets[destino].extend(cuerpo)

    resultado: list[Seccion] = []
    for titulo in SECCIONES_ESPERADAS:
        opcionales = titulo in ("Tablas comparativas", "Esquemas")
        cuerpo = buckets[titulo]
        vacia = not any(linea.strip() for linea in cuerpo)

        if titulo == "Esquemas" and bool(esquemas):
            resultado.append(Seccion(titulo, cuerpo))
            continue
        if (opcionales) and vacia:
            continue
        if vacia:
            resultado.append(Seccion(titulo, [_FALTA_AVISO]))
            continue
        resultado.append(Seccion(titulo, cuerpo))

    resultado.extend(extras)
    return resultado


def separar_secciones(maestro: str) -> list[Seccion]:
    """Divide el maestro en secciones: «#» título, «##» subtítulo y «###» tema."""
    secciones: list[Seccion] = []
    titulo: str | None = None
    subtitulo = False
    cuerpo: list[str] = []

    def cerrar() -> None:
        if titulo is not None:
            secciones.append(Seccion(titulo, cuerpo, subtitulo))

    for linea in maestro.splitlines():
        encabezado = re.match(r"^(#{1,3})\s+(.*)$", linea.strip())
        if encabezado:
            nivel = len(encabezado.group(1))
            if nivel <= 2:
                cerrar()
                titulo = encabezado.group(2).strip(" :·-")
                subtitulo = nivel == 2
                cuerpo = []
                continue
            if nivel == 3:
                if titulo is not None:
                    cuerpo.append("")
                    cuerpo.append(encabezado.group(2).strip() + ":")
                continue
        if titulo is None:
            if linea.strip():
                titulo = "Resumen por apartados"
                cuerpo = [linea]
        else:
            cuerpo.append(linea)
    cerrar()
    return secciones
