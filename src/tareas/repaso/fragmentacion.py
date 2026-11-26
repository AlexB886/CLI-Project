"""Fragmentación y síntesis por etapas para documentos largos.

Nunca se envía el texto entero al modelo de una sola vez: se divide en
fragmentos por párrafos, cada fragmento se sintetiza (map) y las síntesis se
integran en un documento maestro coherente (reduce). El mapa puede ejecutarse
con concurrencia limitada (`paralelo`) porque los fragmentos son
independientes; nunca se reenvía un fragmento ya sintetizado.
"""

import re
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from tareas.ia.errores import ErrorProveedorIA

LONGITUD_FRAGMENTO = 12_000
_UMBRAL_ENVIO_DIRECTO = 9_000
_MAXIMO_SINTESIS = 24_000

CONTEXTO_SINTESIS = (
    "Eres un asistente de estudio. Sintetiza fragmentos de apuntes de forma fiel: "
    "conserva datos, cifras, fechas, nombres y definiciones; no inventes nada ni "
    "añadas opiniones. Devuelve solo viñetas en texto plano, sin Markdown."
)

CONTEXTO_MAESTRO = (
    "Eres un profesor que prepara materiales de estudio. Redacta un documento "
    "maestro de repaso, coherente y bien organizado, a partir de las síntesis de "
    "los apuntes del alumno. Conserva todos los datos, cifras, fechas, nombres y "
    "definiciones; no inventes nada. Usa encabezados «#» para secciones generales "
    "y «###» para temas dentro de un apartado; viñetas con «- » para el detalle. "
    "Responde solo en español."
)

_INSTRUCCIONES_MAESTRO = (
    "Organiza el documento con exactamente estas secciones, cada una con su "
    "encabezado «#» en el mismo orden:\n"
    "# Introducción\n"
    "# Resumen por apartados\n(usa «### Título» para cada apartado de los apuntes)\n"
    "# Conceptos clave\n(definiciones breves, una viñeta por concepto)\n"
    "# Explicaciones didácticas\n(comparaciones y ejemplos que faciliten entender)\n"
    "# Errores y confusiones frecuentes\n(ojo con…)\n"
    "# Repaso final de lo imprescindible\n(lo que sí o sí debe quedar)\n"
    "# Preguntas para el examen\n(entre 6 y 10 preguntas para autoevaluarse)\n"
    "Después de cada sección, si los apuntes lo justifican, añade un bloque:\n"
    "## ESQUEMA\nesquema: Idea principal :: por qué importa\nNodo :: detalle\n"
    "(cada línea es un nodo; usa «tabla:» para tablas comparativas, "
    "«timeline: fecha :: suceso» para cronologías y «lista:» para jerarquías). "
    "Incluye como mínimo un bloque ESQUEMA derivado del contenido."
)


class SintesisError(Exception):
    """La IA no pudo sintetizar el material; lleva mensaje humano."""

    def __init__(self, mensaje: str, detalle: str = "") -> None:
        super().__init__(mensaje)
        self.detalle = detalle


def _cortar_palabras(texto: str, maximo: int) -> list[str]:
    bloques: list[str] = []
    actual = ""
    for palabra in texto.split():
        candidato = f"{actual} {palabra}".strip()
        if actual and len(candidato) > maximo:
            bloques.append(actual)
            actual = palabra
        else:
            actual = candidato
    if actual:
        bloques.append(actual)
    return bloques


def _cortar_largo(texto: str, maximo: int) -> list[str]:
    partes: list[str] = []
    actual = ""

    def verter(pieza: str) -> None:
        while len(pieza) > maximo:
            partes.append(pieza[:maximo])
            pieza = pieza[maximo:]
        if pieza:
            partes.append(pieza)

    for linea in texto.splitlines():
        while len(linea) > maximo:
            verter(linea[:maximo])
            linea = linea[maximo:]
        candidato = f"{actual}\n{linea}" if actual else linea
        if actual and len(candidato) > maximo:
            partes.append(actual)
            actual = linea
        else:
            actual = candidato
    if len(actual) > maximo:
        for trozo in _cortar_palabras(actual, maximo):
            verter(trozo)
    elif actual:
        partes.append(actual)
    return partes


def fragmentar(texto: str, maximo: int = LONGITUD_FRAGMENTO) -> list[str]:
    """Divide el texto en fragmentos de como máximo `maximo` caracteres.

    Respeta los párrafos; un párrafo desmesurado se corta por líneas y, si aun
    así no caben, por palabras.
    """
    fragmentos: list[str] = []
    actual = ""
    for parrafo in texto.split("\n\n"):
        limpio = parrafo.strip()
        if not limpio:
            continue
        if len(limpio) > maximo:
            trozos = _cortar_largo(limpio, maximo)
        else:
            trozos = [limpio]
        for trozo in trozos:
            candidato = f"{actual}\n\n{trozo}" if actual else trozo
            if actual and len(candidato) > maximo:
                fragmentos.append(actual)
                actual = trozo
            else:
                actual = candidato
    if actual:
        fragmentos.append(actual)
    return fragmentos


def sintetizar(
    texto: str,
    generar: Callable[[str, str], str],
    objetivo: str = "",
    informar: Callable[[str], None] | None = None,
    progreso=None,
    paralelo: int = 3,
) -> str:
    """Devuelve un documento maestro fiel al material, con síntesis por etapas.

    Textos cortos se pasan directamente; los largos se sintetizan fragmento a
    fragmento (con hasta `paralelo` peticiones simultáneas, siempre en orden
    para la integración) y se integran en un único maestro coherente. El
    progreso se reporta a través de `progreso` (objeto Progreso) si se
    proporciona; `informar` sigue disponible para Avisos sueltos.
    """
    texto = texto.strip()
    if not texto:
        raise SintesisError("Los apuntes no contienen texto que estudiar.")

    nota_objetivo = f" Objetivo de estudio: {objetivo}." if objetivo else ""

    def aviso(mensaje: str) -> None:
        if informar is not None:
            informar(mensaje)
        elif progreso is not None:
            progreso.avanzar()  # el aviso marca una fase superada: avanza el contador

    def maestro_robusto(maestro: str) -> str:
        maestro = maestro.strip()
        if not maestro:
            raise SintesisError(
                "La IA devolvió una respuesta vacía; no se generó ningún documento."
            )
        if not re.search(r"^#{1,3}\s+\S", maestro, flags=re.MULTILINE):
            maestro = "# Resumen por apartados\n\n" + maestro
        return maestro

    def anot_etapa(exc: ErrorProveedorIA, etapa: str) -> ErrorProveedorIA:
        """Anota la etapa del fallo en el error (sin reintentar jamás)."""
        exc.etapa = etapa
        return exc

    if len(texto) <= _UMBRAL_ENVIO_DIRECTO:
        aviso("Analizando los apuntes con la IA…")
        peticion = (
            "Prepara un documento de repaso completo y fiel a partir de estos apuntes."
            f"{nota_objetivo}\n{_INSTRUCCIONES_MAESTRO}\n\n"
            + texto
        )
        try:
            maestro = generar(peticion, CONTEXTO_MAESTRO)
        except ErrorProveedorIA as exc:
            raise anot_etapa(exc, "análisis directo") from exc
        return maestro_robusto(maestro)

    fragmentos = fragmentar(texto)
    paralelo = max(1, min(8, int(paralelo)))

    def sintetizar_fragmento(indice: int, fragmento: str) -> str:
        peticion = (
            f"Sintetiza este fragmento ({indice} de {len(fragmentos)}) de los apuntes, "
            "conservando todos los datos, cifras, fechas y definiciones. "
            "Devuelve solo viñetas:\n\n" + fragmento
        )
        try:
            return generar(peticion, CONTEXTO_SINTESIS)
        except ErrorProveedorIA as exc:
            raise anot_etapa(exc, f"fragmento {indice} de {len(fragmentos)}") from exc

    if progreso is not None:
        progreso.total = len(fragmentos)
        progreso.cambiar_fase("Sintetizando fragmentos")
    else:
        aviso(f"Documento largo: {len(fragmentos)} fragmentos. Sintetizando por etapas…")

    sintesis: list[str] = ["" for _ in fragmentos]
    fallo: ErrorProveedorIA | None = None
    with ThreadPoolExecutor(max_workers=paralelo) as charca:
        pendientes = {
            charca.submit(sintetizar_fragmento, indice, fragmento): indice - 1
            for indice, fragmento in enumerate(fragmentos, start=1)
        }
        from concurrent.futures import as_completed

        for futuro in as_completed(pendientes):
            indice = pendientes[futuro]
            try:
                sintesis[indice] = futuro.result()
            except ErrorProveedorIA as exc:
                fallo = exc
                for resto in pendientes:
                    resto.cancel()
                break
            if progreso is not None:
                progreso.avanzar()
    if fallo is not None:
        if progreso is not None:
            progreso.abortar(str(fallo))
        raise fallo
    if progreso is not None:
        progreso.cerrar()

    def reducir(material: str) -> str:
        peticion_maestro = (
            "Integra estas síntesis de los apuntes en un único documento de repaso "
            "coherente y bien organizado, conservando todos los datos y sin inventar nada."
            f"{nota_objetivo}\n{_INSTRUCCIONES_MAESTRO}\n\n"
            + material
        )
        try:
            return generar(peticion_maestro, CONTEXTO_MAESTRO)
        except ErrorProveedorIA as exc:
            raise anot_etapa(exc, "documento final") from exc

    material = "\n\n".join(sintesis)
    if progreso is not None:
        progreso.cambiar_fase("Integrando el documento de repaso")
    else:
        aviso("Integrando las síntesis en un documento de repaso coherente…")
    maestro = (
        reducir(material)
        if len(material) <= _MAXIMO_SINTESIS
        else _integrar_por_partes(material, reducir, _MAXIMO_SINTESIS)
    )
    return maestro_robusto(maestro)


def _integrar_por_partes(material: str, reducir: Callable[[str], str], limite: int) -> str:
    """Reducción por bloques: ninguna síntesis se pierde ni se trunca.

    Si el conjunto de síntesis excede el contexto del modelo, se divide en
    bloques, cada uno produce un maestro parcial, y esos parciales se vuelven
    a integrar en el documento final.
    """
    bloques: list[str] = []
    actual = ""
    for sintesis in material.split("\n\n"):
        candidato = f"{actual}\n\n{sintesis}" if actual else sintesis
        if len(candidato) > limite and actual:
            bloques.append(actual)
            actual = sintesis
        else:
            actual = candidato
    if actual:
        bloques.append(actual)

    parciales = [reducir(bloque) for bloque in bloques]
    if len(parciales) == 1:
        return parciales[0]
    return reducir(
        "\n\n".join(parciales).replace("\n# ", "\n## ")
    )
