"""Pruebas del generador ODT de repaso-ia: validez y contenido."""

import zipfile
from pathlib import Path
from xml.etree import ElementTree

from tareas.repaso.contenidos import Seccion
from tareas.repaso.esquemas import detectar
from tareas.repaso.odt import escribir_odt

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


def _odt(tmp_path: Path, secciones=None, esquemas=None) -> Path:
    ruta = tmp_path / "repaso.odt"
    escribir_odt(
        ruta,
        "Repaso: La célula",
        "Objetivo: examen tipo test",
        secciones if secciones is not None else [Seccion("Introducción", ["La célula."])],
        esquemas if esquemas is not None else [],
        ["apuntes.txt"],
        "24/11/2026 18:00",
    )
    return ruta


def test_odt_es_un_zip_valido_con_su_mimetype(tmp_path: Path) -> None:
    ruta = _odt(tmp_path)
    with zipfile.ZipFile(ruta) as paquete:
        nombres = paquete.namelist()
        assert "mimetype" in nombres and "content.xml" in nombres
        assert "META-INF/manifest.xml" in nombres
        assert paquete.read("mimetype") == b"application/vnd.oasis.opendocument.text"


def test_mimetype_es_primero_y_no_comprimido(tmp_path: Path) -> None:
    """ODF exige identificar el tipo sin descomprimir el paquete."""
    ruta = _odt(tmp_path)
    with zipfile.ZipFile(ruta) as paquete:
        entrada = paquete.infolist()[0]
        assert entrada.filename == "mimetype"
        assert entrada.compress_type == zipfile.ZIP_STORED


def test_odt_contiene_texto_de_las_secciones(tmp_path: Path) -> None:
    ruta = _odt(tmp_path)
    with zipfile.ZipFile(ruta) as paquete:
        content = paquete.read("content.xml").decode("utf-8")
    assert "Repaso: La célula" in content
    assert "La célula." in content
    assert "apuntes.txt" in content


def test_escapes_inyeccion_de_xml(tmp_path: Path) -> None:
    secciones = [Seccion("Introducción", ["<script>alert(1)</script> & compañía"])]
    ruta = _odt(tmp_path, secciones)
    with zipfile.ZipFile(ruta) as paquete:
        crudo = paquete.read("content.xml").decode("utf-8")
        raiz = ElementTree.fromstring(paquete.read("content.xml"))
    # el XML parsea sin crear un nodo <script> (no rompe el documento)
    assert raiz.find(".//{http://www.w3.org/1999/xhtml}script") is None
    assert "<script>alert" not in crudo  # escapado, nunca literal
    assert "compañía" in "".join(raiz.itertext())


def test_titulos_usan_estilos_reales_de_encabezado(tmp_path: Path) -> None:
    ruta = _odt(tmp_path)
    with zipfile.ZipFile(ruta) as paquete:
        raiz = ElementTree.fromstring(paquete.read("content.xml"))
    encabezados = raiz.findall(".//text:h", _NS)
    assert any(
        e.get("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}outline-level") == "1"
        for e in encabezados
    )


def test_tablas_con_cabecera_sombreada(tmp_path: Path) -> None:
    esquema = detectar("tabla: Reptil :: fría\nAve :: plumas")
    ruta = _odt(tmp_path, [Seccion("Tablas comparativas", [])], [esquema])
    with zipfile.ZipFile(ruta) as paquete:
        content = paquete.read("content.xml").decode("utf-8")
    assert "table:table-row" in content
    assert 'table:style-name="TCab"' in content  # la cabecera usa su estilo
