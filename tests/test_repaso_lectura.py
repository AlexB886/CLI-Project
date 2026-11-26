"""Pruebas de la lectura de documentos para repaso-ia (sin IA real)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from tareas.repaso import lectura
from tareas.repaso.lectura import LecturaError, cargar_documentos, extraer_texto


def _simulador_ghostscript(tmp_path: Path) -> str:
    """Crea un falso ejecutable `gs` portable y devuelve su ruta absoluta.

    Imita a `gs -sDEVICE=txtwrite -o SALIDA ENTRADA`: extrae el texto de los
    operadores `BT ... Tj ET` del PDF (con la codificación latin-1 que usa
    Ghostscript), lo escribe en SALIDA y no toca el original. El wrapper embebe
    la ruta absoluta del script, así que funciona aunque el PATH del runner no
    traiga utilidades como `dirname` (Ubuntu/macOS) o en Windows.
    """
    carpeta = tmp_path / "falso-gs"
    carpeta.mkdir()
    guion = carpeta / "gs.py"
    guion.write_text(
        "import re, sys\n"
        "argv = sys.argv[1:]\n"
        'salida = argv[argv.index("-o") + 1]\n'
        "entrada = argv[-1]\n"
        'datos = open(entrada, "rb").read()\n'
        "texto = ' '.join(\n"
        '    m.group(1).decode("latin-1") for m in re.finditer(rb"\\((.*?)\\)\\s*Tj", datos)\n'
        ")\n"
        'open(salida, "w", encoding="utf-8").write(texto + "\\n")\n',
        encoding="utf-8",
    )
    if os.name == "nt":
        simulador = carpeta / "gs.bat"
        simulador.write_text(
            f'@echo off\r\n"{sys.executable}" "{guion}" %*\r\n', encoding="utf-8"
        )
    else:
        simulador = carpeta / "gs"
        simulador.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{guion}" "$@"\n', encoding="utf-8"
        )
        simulador.chmod(0o755)
    return str(simulador)


def _pdf_sencillo(ruta: Path) -> Path:
    """PDF mínimo válido con texto «Hola repaso», para pruebas locales."""
    flujo = b"BT /F1 24 Tf 72 700 Td (Hola repaso) Tj ET"
    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>",
        b"<</Length " + str(len(flujo)).encode() + b">>\nstream\n" + flujo + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Times-Roman>>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    desplazamientos = []
    for numero, cuerpo in enumerate(objetos, start=1):
        desplazamientos.append(len(salida))
        salida += str(numero).encode() + b" 0 obj" + cuerpo + b"endobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 " + str(len(objetos) + 1).encode() + b"\n0000000000 65535 f \n"
    for desplazamiento in desplazamientos:
        salida += b"%010d 00000 n \n" % desplazamiento
    salida += (
        b"trailer<</Size " + str(len(objetos) + 1).encode() + b"/Root 1 0 R>>\nstartxref\n"
        + str(inicio_xref).encode()
        + b"\n%%EOF"
    )
    ruta.write_bytes(bytes(salida))
    return ruta


def test_texto_plan_se_extrae(tmp_path: Path) -> None:
    apuntes = tmp_path / "tema.txt"
    apuntes.write_text("La mitocondria produce energía.", encoding="utf-8")
    assert extraer_texto(apuntes) == "La mitocondria produce energía."


def test_markdown_convierte_encabezados(tmp_path: Path) -> None:
    apuntes = tmp_path / "tema.md"
    apuntes.write_text("# Tema 3\n\nContenido.", encoding="utf-8")
    assert extraer_texto(apuntes) == "Tema 3\n\nContenido."


def test_archivo_inexistente_da_mensaje_humano(tmp_path: Path) -> None:
    with pytest.raises(LecturaError, match="no existe"):
        extraer_texto(tmp_path / "nada.txt")


def test_carpeta_no_es_un_documento(tmp_path: Path) -> None:
    with pytest.raises(LecturaError, match="carpeta"):
        extraer_texto(tmp_path)


def test_extension_no_soportada(tmp_path: Path) -> None:
    broma = tmp_path / "falso.xyz"
    broma.write_bytes(b"\x00\x01")
    with pytest.raises(LecturaError):
        extraer_texto(broma)


def test_pdf_danado_informa_con_claridad(tmp_path: Path) -> None:
    roto = tmp_path / "roto.pdf"
    roto.write_bytes(b"%PDF-1.7\ntacho de bytes")
    with pytest.raises(LecturaError):
        extraer_texto(roto)


def test_docx_valido_se_extrae(tmp_path: Path) -> None:
    docx = tmp_path / "apuntes.docx"
    contenido = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Fotosíntesis</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>dos fases</w:t></w:r></w:p></w:body></w:document>"
    )
    with ZipFile(docx, "w") as paquete:
        paquete.writestr("word/document.xml", contenido)
    assert "Fotosíntesis" in extraer_texto(docx)


def test_odt_valido_se_extrae(tmp_path: Path) -> None:
    odt = tmp_path / "apuntes.odt"
    contenido = (
        '<?xml version="1.0"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        "<office:body><office:text><text:p>Ciclo de Krebs</text:p>"
        "</office:text></office:body></office:document-content>"
    )
    with ZipFile(odt, "w") as paquete:
        paquete.writestr("content.xml", contenido)
    assert "Ciclo de Krebs" in extraer_texto(odt)


def test_vacio_y_danado_informan_sin_romperse(tmp_path: Path) -> None:
    vacio = tmp_path / "vacio.txt"
    vacio.write_text("", encoding="utf-8")
    roto = tmp_path / "roto.odt"
    roto.write_bytes(b"no es un zip")
    informes: list[str] = []
    documentos = cargar_documentos([vacio, roto], informes)
    assert documentos == []
    assert len(informes) == 2
    assert any("no contiene texto" in i for i in informes)
    assert any("ODT" in i or "no es un zip" in i.lower() or "ilegible" in i.lower() for i in informes)


def test_documentos_mixtos_solo_lean_los_buenos(tmp_path: Path) -> None:
    bueno = tmp_path / "bueno.txt"
    bueno.write_text("Contenido útil.", encoding="utf-8")
    malo = tmp_path / "malo.txt"  # no existe
    informes: list[str] = []
    documentos = cargar_documentos([bueno, malo], informes)
    assert [d.origen.name for d in documentos] == ["bueno.txt"]
    assert len(informes) == 1


def test_el_original_nunca_se_modifica(tmp_path: Path) -> None:
    original = tmp_path / "original.txt"
    texto = "Texto que no debe cambiar."
    original.write_text(texto, encoding="utf-8")
    antes = original.read_bytes()
    extraer_texto(original)
    assert original.read_bytes() == antes


def test_pdf_sin_poppler_usa_ghostscript(tmp_path: Path, monkeypatch) -> None:
    """Con LibreOffice y pdftotext ausentes, gs extrae el texto y no toca el PDF.

    El ejecutable Ghostscript se simula con un fixture portable (no requiere gs
    real en el runner). La prueba real de integración es opcional:
    ver test_pdf_integration_ghostscript_real más abajo.
    """
    pdf = _pdf_sencillo(tmp_path / "apuntes con espacios ñ.pdf")
    antes = pdf.read_bytes()

    ruta_simulador = _simulador_ghostscript(tmp_path)
    # Solo `gs` está disponible (sin pdftotext ni LibreOffice) y es el simulador.
    monkeypatch.setattr(lectura.shutil, "which", lambda n: ruta_simulador if n == "gs" else None)
    monkeypatch.setattr(lectura, "_localizar_convertidor", lambda nombres: None)
    texto = extraer_texto(pdf)
    assert "Hola" in texto and "repaso" in texto
    assert pdf.read_bytes() == antes


@pytest.mark.skipif(shutil.which("gs") is None, reason="Ghostscript no está instalado")
def test_pdf_integration_ghostscript_real(tmp_path: Path) -> None:
    """Integración real opcional con gs: se omite si no está instalado."""
    pdf = _pdf_sencillo(tmp_path / "apuntes con espacios ñ.pdf")
    antes = pdf.read_bytes()

    texto = lectura._convertir_pdf_con_ghostscript(pdf)
    assert "Hola" in texto and "repaso" in texto
    assert pdf.read_bytes() == antes


def test_fallbacks_de_pdf_se_prueban_en_orden_y_sin_bucles(tmp_path: Path, monkeypatch) -> None:
    """Cada conversor se intenta una vez; si todos fallan, el mensaje lista las causas."""
    pdf = tmp_path / "sin-herramientas.pdf"
    pdf.write_bytes(b"%PDF-1.7\nbasura\n")

    intentos: list[str] = []

    monkeypatch.setattr(
        lectura.shutil,
        "which",
        lambda n: {
            "pdftotext": "/usr/bin/pdftotext",
            "libreoffice": "/usr/bin/libreoffice",
            "soffice": "/usr/bin/soffice",
            "gs": "/usr/bin/gs",
        }.get(n),
    )

    def falso_run(orden, *a, **k):  # nunca lanza nada: solo cuenta intentos
        intentos.append(str(orden[0]))
        return subprocess.CompletedProcess(orden, 1, "", "sin salida")

    monkeypatch.setattr(lectura.subprocess, "run", falso_run)
    with pytest.raises(LecturaError, match="No se pudo leer"):
        extraer_texto(pdf)
    assert intentos.count("pdftotext") == 1
    assert intentos.count("libreoffice") <= 2
    # Ghostscript se invoca con la ruta resuelta por which (no el literal «gs»):
    # un único intento, contado por la ruta exacta que devolvió el mock.
    assert intentos.count("/usr/bin/gs") == 1
    assert "gs" not in intentos  # nunca se relanza por nombre suelto


def test_sin_ningun_conversor_de_pdf_informa_humanamente(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(lectura.shutil, "which", lambda n: None)
    with pytest.raises(LecturaError, match="hace falta"):
        extraer_texto(pdf)
