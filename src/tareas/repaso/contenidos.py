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
_MARCA_TIPO = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:esquema|tabla|timeline|lista):",
    re.IGNORECASE,
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
        self.tablas: list = []

    @property
    def vacia(self) -> bool:
        return not any(linea.strip() for linea in self.cuerpo)


def _es_esquema(linea: str) -> bool:
    limpia = re.sub(r"^[-*•]\s*", "", linea.strip())
    return (
        _ESQUEMA_MARCA.match(limpia) is not None
        or bool(_MARCA_TIPO.match(limpia))
    )


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
    """Extrae los bloques de esquema del maestro, con o sin encabezado «ESQUEMA».

    Un bloque es la línea de marca (`ESQUEMA`, o directamente `tabla: …`) más
    sus líneas de nodos, hasta la siguiente línea de encabezado.
    """
    esquemas: list[Esquema] = []
    lineas_maestro = maestro.splitlines()
    indice = 0
    while indice < len(lineas_maestro):
        desnuda = lineas_maestro[indice].strip()
        if _es_esquema(desnuda):
            bloque: list[str] = [desnuda] if _MARCA_TIPO.match(desnuda) else []
            indice += 1
            while indice < len(lineas_maestro):
                siguiente = lineas_maestro[indice].strip()
                if re.match(r"^#{1,3}\s+", siguiente) and not _MARCA_TIPO.match(siguiente):
                    break
                if bloque and _MARCA_TIPO.match(siguiente):
                    break
                if siguiente:
                    bloque.append(siguiente)
                indice += 1
            esquema = detectar("\n".join(bloque))
            if esquema is not None:
                esquemas.append(esquema)
            continue
        indice += 1
    return esquemas


def construir_documento(maestro: str, esquemas: list[Esquema]) -> list[Seccion]:
    """Reordena el maestro en las secciones fijas del repaso educativo."""
    buckets: dict[str, list[str]] = {titulo: [] for titulo in SECCIONES_ESPERADAS}
    extras: list[Seccion] = []

    tablas_por_seccion: dict[str, list] = {}
    para_tablas = [e for e in esquemas if e.tipo == "tabla"]
    for esquema in para_tablas:
        linea_inicial = (esquema.especificacion.splitlines() or [""])[0]
        primera = maestro.find(linea_inicial)
        encabezado = None
        if primera != -1:
            anterior = maestro[:primera]
            marcas = re.findall(r"^#{1,3}\s+(.*)$", anterior, flags=re.MULTILINE)
            if marcas:
                encabezado = type("M", (), {"group": staticmethod(lambda n, m=marcas[-1]: m)})()
        if encabezado:
            destino = _detectar_destino(_normalizar_ingles(encabezado.group(1))) or "Tablas comparativas"
            tablas_por_seccion.setdefault(destino, []).append(esquema)

    for seccion in separar_secciones(_cortar_en_esquema(_purgar_esquemas_internos(maestro))):
        destino = _detectar_destino(seccion.titulo)
        if destino is None:
            extras.append(seccion)
            continue
        seccion.tablas = tablas_por_seccion.get(destino, [])
        cuerpo = _limpiar_esquemas(list(seccion.cuerpo))
        if buckets[destino]:
            cuerpo.insert(0, seccion.titulo)
        buckets[destino].extend(cuerpo)

    resultado: list[Seccion] = []
    pendientes = {k: list(v) for k, v in tablas_por_seccion.items()}
    for titulo in SECCIONES_ESPERADAS:
        opcionales = titulo in ("Tablas comparativas", "Esquemas")
        cuerpo = buckets[titulo]
        tablas_here = pendientes.pop(titulo, [])
        tiene_contenido = bool(cuerpo) or bool(tablas_here)

        if titulo == "Esquemas" and any(e.tipo != "tabla" for e in esquemas):
            seccion = Seccion(titulo, cuerpo)
            resultado.append(seccion)
            continue
        if opcionales and not tiene_contenido:
            continue
        seccion = Seccion(titulo, cuerpo if tiene_contenido else [_FALTA_AVISO])
        seccion.tablas = tablas_here
        resultado.append(seccion)

    sobrantes = [t for colas in pendientes.values() for t in colas]
    if sobrantes:
        colocadas = False
        for seccion in resultado:
            if seccion.titulo == "Tablas comparativas":
                seccion.tablas = [*seccion.tablas, *sobrantes]
                colocadas = True
                break
        if not colocadas:
            seccion = Seccion("Tablas comparativas", [])
            seccion.tablas = sobrantes
            resultado.insert(4, seccion)

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


def esquema_de_bloques(
    maestro: str, titulo_repaso: str, maximo_nodos: int = 5
) -> Esquema | None:
    """Esquema local de seguridad si la IA no devolvió ninguno.

    Usa únicamente los títulos de sección del maestro y su primera frase:
    contenido derivado de los apuntes, nunca inventado.
    """
    bloques = re.findall(r"^#{1,3}\s+(.*)$", maestro, flags=re.MULTILINE)
    cuerpos = re.split(r"^#{1,3}\s+.*$", maestro, flags=re.MULTILINE)[1:]
    omitidas = {"esquema"}
    nodos: list[tuple[str, str]] = []
    for titulo, cuerpo in zip(bloques, cuerpos):
        limpio = titulo.strip(" :·-")
        if limpio.casefold() in omitidas:
            continue
        primera = next((linea.strip() for linea in cuerpo.splitlines() if linea.strip()), "")
        if len(primera) > 90:
            primera = primera[:90].rsplit(" ", 1)[0] + "…"
        nodos.append((limpio, primera))
    if len(nodos) < 2:
        return None
    raiz = (titulo_repaso, "Documento de repaso generado a partir de los apuntes")
    especificacion = "esquema:\n| \n".join(
        [f"{raiz[0]} :: {raiz[1]}"] + [f"{t} :: {d}" if d else t for t, d in nodos[:maximo_nodos]]
    )
    return detectar(especificacion)
