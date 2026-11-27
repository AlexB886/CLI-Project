"""Lectura y extracción de texto de los documentos de entrada.

Este módulo solo lee: nunca modifica ni sobrescribe los ficheros originales.
Las conversiones (PDF, DOCX…) se hacen con herramientas locales invocadas sin
shell, y el contenido del documento de origen nunca se interpola en la orden.
"""

import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

FORMATOS_TEXTO = {".txt", ".text", ".md", ".markdown", ".rst"}
FORMATOS_LECTURA_DIRECTA = FORMATOS_TEXTO | {".csv", ".log"}


class LecturaError(Exception):
    """El documento no se ha podido leer (formato, daño o herramienta ausente)."""


@dataclass(frozen=True)
class Documento:
    """Texto extraído de un fichero de apuntes."""

    origen: Path
    texto: str


def extension_soportada(ruta: Path) -> bool:
    """Indica si la extensión del fichero tiene lector conocido."""
    return ruta.suffix.lower() in SOPORTADAS


SOPORTADAS = FORMATOS_LECTURA_DIRECTA | {".pdf", ".docx", ".doc", ".odt", ".ods", ".rtf", ".htm", ".html"}


def _rastreable(texto: str, origen: Path) -> str:
    """Antepone la fuente para que cada bloque sea rastreable hasta el original."""
    lineas = texto.splitlines()
    if not lineas:
        return f"Fuente: {origen.name}"
    return "\n".join(f"{origen.name} · {linea}" if linea.strip() else linea for linea in lineas)


def _leer_directo(ruta: Path) -> str:
    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LecturaError(
            f"«{ruta.name}» no es un fichero de texto en UTF-8; convierte el documento primero."
        ) from exc
    except OSError as exc:
        raise LecturaError(f"No se pudo leer «{ruta.name}»: {exc}") from exc
    return texto


def _texto_odf(ruta: Path, formato: str = "ODT") -> str:
    """Extrae el texto de un ODT/ODS (zip con content.xml) sin dependencias.

    Se usa `itertext()` para no perder el texto dentro de `text:span` ni el que
    sigue a esos elementos; `nodo.text` por sí solo devolvía solo el primer
    fragmento del párrafo.
    """
    try:
        with zipfile.ZipFile(ruta) as archivo:
            contenido = archivo.read("content.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise LecturaError(f"«{ruta.name}» no es un documento {formato} válido.") from exc

    try:
        raiz = ElementTree.fromstring(contenido)
    except ElementTree.ParseError as exc:
        raise LecturaError(f"«{ruta.name}» tiene un XML interno dañado.") from exc

    partes: list[str] = []
    for nodo in raiz.iter():
        etiqueta = nodo.tag.rsplit("}", 1)[-1]
        if etiqueta in ("p", "h"):
            texto = "".join(nodo.itertext()).strip()
            if texto:
                partes.append(texto)
    return "\n\n".join(partes)


class _LectorHTML(HTMLParser):
    """Recoge el texto visible de un HTML sin añadir dependencias externas."""

    _BLOQUES = {"br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "tr"}
    _OMITIR = {"noscript", "script", "style", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._profundidad = 0
        self.partes: list[str] = []

    def handle_starttag(self, etiqueta: str, atributos: list[tuple[str, str | None]]) -> None:
        if etiqueta in self._OMITIR:
            self._profundidad += 1
        elif etiqueta in self._BLOQUES:
            self.partes.append("\n")

    def handle_endtag(self, etiqueta: str) -> None:
        if etiqueta in self._OMITIR and self._profundidad:
            self._profundidad -= 1
        elif etiqueta in self._BLOQUES:
            self.partes.append("\n")

    def handle_data(self, datos: str) -> None:
        if not self._profundidad:
            self.partes.append(datos)


def _texto_html(ruta: Path) -> str:
    """Extrae el texto de un HTML, descartando scripts y estilos."""
    try:
        crudo = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise LecturaError(f"No se pudo leer «{ruta.name}»: {exc}") from exc

    lector = _LectorHTML()
    lector.feed(crudo)
    lector.close()
    lineas = [" ".join(linea.split()) for linea in "".join(lector.partes).splitlines()]
    return "\n".join(linea for linea in lineas if linea)


def _texto_docx(ruta: Path) -> str:
    """Extrae los párrafos de un DOCX (zip con word/document.xml)."""
    try:
        with zipfile.ZipFile(ruta) as archivo:
            documento = archivo.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise LecturaError(f"«{ruta.name}» no es un documento DOCX válido.") from exc

    try:
        raiz = ElementTree.fromstring(documento)
    except ElementTree.ParseError as exc:
        raise LecturaError(f"«{ruta.name}» tiene un XML interno dañado.") from exc

    parrafos: list[str] = []
    for parrafo in raiz.iter():
        if not parrafo.tag.endswith("}p"):
            continue
        trozos = [nodo.text for nodo in parrafo.iter() if nodo.tag.endswith("}t") and nodo.text]
        texto = "".join(trozos).strip()
        if texto:
            parrafos.append(texto)
    return "\n\n".join(parrafos)


def _localizar_convertidor(candidatos: tuple[str, ...]) -> str | None:
    return next((shutil.which(nombre) for nombre in candidatos if shutil.which(nombre)), None)


def _perfil_alternativo(destino: Path) -> str:
    """Perfil de usuario libreoffice aislado y propio.

    En algunos equipos el perfil por defecto tiene desregistrado el filtro de
    importación de PDF para Writer; con un perfil limpio esa conversión vuelve
    a funcionar y no interfiere con un Writer abierto del usuario.
    """
    perfil = destino / "perfil"
    return f"file://{perfil}"


def _ejecutar_conversion(
    orden: str, filtro: str, ruta: Path, destino: Path, perfil: str | None = None
) -> subprocess.CompletedProcess:
    orden_completa = [orden, "--headless", "--convert-to", filtro, "--outdir", str(destino), str(ruta)]
    if perfil is not None:
        orden_completa.insert(2, f"-env:UserInstallation={perfil}")
    return subprocess.run(
        orden_completa,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=90,
        check=False,
    )


def _conversion_fallo(resultado: subprocess.CompletedProcess | None, ruta: Path, paso: str = "") -> LecturaError:
    if resultado is None:
        return LecturaError(f"La conversión de «{ruta.name}» no produjo texto.")
    salida = ((resultado.stdout or "") + " " + (resultado.stderr or "")).strip()
    detalle = next((l.strip() for l in salida.splitlines() if l.strip()), "")
    if len(detalle) > 160:
        detalle = detalle[:160] + "…"
    sufijo = f" (paso {paso})" if paso else ""
    return LecturaError(
        f"No se pudo convertir «{ruta.name}» a texto{sufijo} ({resultado.returncode}): {detalle}"
    )


def _buscar_generado(destino: Path, sufijo: str) -> Path | None:
    if sufijo == ".txt":
        candidatos = sorted(destino.glob("*.txt"))
    else:
        candidatos = sorted(destino.rglob(f"*{sufijo}"))
    for generado in candidatos:
        if generado.is_file():
            return generado
    return None


def _convertir_a_txt(
    ruta: Path, orden: str, destino: Path, perfil: str | None = None
) -> str:
    """Convierte un documento de Writer a texto con LibreOffice_headless."""
    resultado = _ejecutar_conversion(
        orden, "txt:Text (encoded):UTF8", ruta, destino, perfil=perfil
    )
    if resultado.returncode != 0:
        raise _conversion_fallo(resultado, ruta)
    generado = _buscar_generado(destino, ".txt")
    if generado is None:
        raise _conversion_fallo(resultado, ruta)
    return generado.read_text(encoding="utf-8", errors="replace")


def _convertir_con_filtro(
    ruta: Path,
    filtros: tuple[str, ...],
    requisitos: str = "LibreOffice o pdftotext",
) -> str:
    """Convierte el documento a texto con LibreOffice_headless en un directorio temporal.

    LibreOffice devuelve a veces código 0 aunque el guardado falle, así que el
    criterio de éxito es la presencia del fichero generado; si falta, se
    reproduce el mensaje real del error.
    """
    orden = _localizar_convertidor(filtros)
    if orden is None:
        raise LecturaError(
            f"Para leer «{ruta.name}» hace falta {requisitos} instalados."
        )

    try:
        if ruta.suffix.lower() == ".pdf":
            return _convertir_pdf_con_libreoffice(ruta, orden)
        with tempfile.TemporaryDirectory(prefix="tareas-repaso-") as temporal:
            return _convertir_a_txt(ruta, orden, Path(temporal))
    except subprocess.TimeoutExpired as exc:
        raise LecturaError(f"La conversión de «{ruta.name}» superó 90 s.") from exc


def _convertir_pdf_con_libreoffice(ruta: Path, orden: str) -> str:
    """Convierte un PDF a texto con LibreOffice sin tocar el original.

    Primero intenta la conversión directa (perfil por defecto); si el guardado
    falla, reintenta con un perfil propio dentro del directorio temporal, donde
    el importador de PDF de Writer suele volver a estar disponible. El original
    nunca se modifica.
    """
    with tempfile.TemporaryDirectory(prefix="tareas-repaso-") as temporal:
        destino = Path(temporal)
        try:
            return _convertir_a_txt(ruta, orden, destino)
        except LecturaError:
            perfil = _perfil_alternativo(destino)
            return _convertir_a_txt(ruta, orden, destino, perfil=perfil)


def _quitar_marca_markdown(texto: str) -> str:
    """Convierte encabezados markdown (#, ##…) en líneas de título normales."""
    lineas = []
    for linea in texto.splitlines():
        linea = re.sub(r"^\s{0,3}#{1,6}\s+", "", linea)
        lineas.append(linea)
    return "\n".join(lineas)


def extraer_texto(ruta: Path) -> str:
    """Devuelve el texto del documento o lanza LecturaError con mensaje humano."""
    if not ruta.exists():
        raise LecturaError(f"«{ruta}» no existe.")
    if ruta.is_dir():
        raise LecturaError(f"«{ruta}» es una carpeta, no un documento.")
    if not ruta.is_file():
        raise LecturaError(f"«{ruta}» no es un fichero regular.")

    extension = ruta.suffix.lower()
    if extension not in SOPORTADAS:
        raise LecturaError(
            f"«{ruta.name}» tiene un formato no soportado "
            f"({extension or 'sin extensión'})."
        )
    if extension in FORMATOS_TEXTO:
        return _quitar_marca_markdown(_leer_directo(ruta))
    if extension in FORMATOS_LECTURA_DIRECTA:
        return _leer_directo(ruta)
    if extension == ".odt":
        return _texto_odf(ruta)
    if extension == ".ods":
        return _texto_odf(ruta, "ODS")
    if extension == ".docx":
        return _texto_docx(ruta)
    if extension in (".htm", ".html"):
        return _texto_html(ruta)
    if extension in (".doc", ".rtf"):
        # Formatos binarios o con marcado propio: los convierte LibreOffice,
        # siempre en temporal y sin tocar el original.
        return _convertir_con_filtro(
            ruta, ("libreoffice", "soffice"), requisitos="LibreOffice"
        )
    if extension == ".pdf":
        return _leer_pdf(ruta)
    raise LecturaError(
        f"«{ruta.name}» tiene un formato no soportado ({extension})."
    )


def _leer_pdf(ruta: Path) -> str:
    """Extrae el texto de un PDF con las herramientas locales disponibles.

    Prioridad: pdftotext (poppler), luego LibreOffice headless y, en último
    lugar, Ghostscript. Cada conversor se intenta una sola vez; si uno falla,
    se prueba el siguiente sin bucles. Todos escriben en un directorio
    temporal: el PDF original nunca se modifica.
    """
    intentos: list[tuple[str, Callable[[Path], str]]] = []
    if shutil.which("pdftotext"):
        intentos.append(("pdftotext", _convertir_con_pdfotext))
    orden = _localizar_convertidor(("libreoffice", "soffice"))
    if orden is not None:
        intentos.append(("LibreOffice", lambda r: _convertir_pdf_con_libreoffice(r, orden)))
    ruta_gs = shutil.which("gs")
    if ruta_gs:
        intentos.append(
            ("Ghostscript", lambda r, _gs=ruta_gs: _convertir_pdf_con_ghostscript(r, _gs))
        )

    if not intentos:
        raise LecturaError(
            f"Para leer «{ruta.name}» hace falta pdftotext, LibreOffice o Ghostscript instalados."
        )

    errores: list[str] = []
    for nombre, conversor in intentos:
        try:
            texto = conversor(ruta).strip()
        except (LecturaError, subprocess.TimeoutExpired) as exc:
            errores.append(f"{nombre}: {exc or 'sin texto'}")
            continue
        if texto:
            return texto
        errores.append(f"{nombre}: la conversión no produjo texto legible.")
    raise LecturaError(
        f"No se pudo leer «{ruta.name}» con las herramientas locales. "
        + " | ".join(errores)
    )


def _convertir_pdf_con_ghostscript(ruta: Path, ejecutable: str = "gs") -> str:
    """Convierte el PDF a texto con Ghostscript (fallback local sin permisos).

    `ejecutable` es la ruta resuelta por `shutil.which` en `_leer_pdf`; usarla
    (en lugar del literal «gs») evita relanzar el binario por nombre y permite
    probar el fallback con un simulador portable, sin depender de que `gs`
    esté instalado en el sistema.
    """
    with tempfile.TemporaryDirectory(prefix="tareas-repaso-") as temporal:
        salida = Path(temporal) / "texto.txt"
        try:
            resultado = subprocess.run(
                [
                    ejecutable, "-dBATCH", "-dNOPAUSE", "-q",
                    "-sDEVICE=txtwrite", "-o", str(salida), str(ruta),
                ],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=90,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LecturaError(f"La conversión de «{ruta.name}» superó 90 s.") from exc
        if resultado.returncode != 0 or not salida.is_file():
            detalle = next((l.strip() for l in (resultado.stderr or "").splitlines() if l.strip()), "")
            raise LecturaError(
                f"No se pudo convertir «{ruta.name}» a texto "
                f"({resultado.returncode}): {detalle}"
            )
        return salida.read_text(encoding="utf-8", errors="replace")


def _convertir_con_pdfotext(ruta: Path) -> str:
    """Extrae el texto de un PDF con pdftotext, con errores humanos."""
    with tempfile.TemporaryDirectory(prefix="tareas-repaso-") as temporal:
        salida = Path(temporal) / "texto.txt"
        try:
            resultado = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", str(ruta), str(salida)],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LecturaError(f"La conversión de «{ruta.name}» superó 60 s.") from exc
        if resultado.returncode != 0 or not salida.is_file():
            detalle = next((l.strip() for l in (resultado.stderr or "").splitlines() if l.strip()), "")
            raise LecturaError(
                f"No se pudo convertir «{ruta.name}» a texto ({resultado.returncode}): {detalle}"
            )
        return salida.read_text(encoding="utf-8", errors="replace")


def cargar_documentos(rutas: list[Path], informes: list[str]) -> list[Documento]:
    """Lee todos los documentos; los ilegibles se registran en informes y no abortan."""
    documentos: list[Documento] = []
    for ruta in rutas:
        if not extension_soportada(ruta):
            informes.append(
                f"«{ruta}» tiene un formato no soportado ({ruta.suffix or 'sin extensión'}); se omite."
            )
            continue
        try:
            texto = extraer_texto(ruta).strip()
        except LecturaError as exc:
            informes.append(str(exc))
            continue
        if not texto:
            informes.append(f"«{ruta}» no contiene texto legible; se omite.")
            continue
        documentos.append(Documento(origen=ruta, texto=_rastreable(texto, ruta)))
    return documentos
