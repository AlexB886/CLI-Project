"""Generación de documentos ODT válidos para LibreOffice Writer.

Sin dependencias externas: se escribe el paquete ODF (zip) a mano con estilos
reales: títulos jerárquicos, listas con viñetas, tablas con cabecera sombreada,
márgenes, tipografía legible y una paleta discreta azul/gris.
"""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from tareas.repaso.contenidos import Seccion
from tareas.repaso.esquemas import Esquema

_CELESTE = "DCE6F1"
_GRIS = "F2F2F2"
_AZUL_TITULO = "1F3864"
_AZUL_SUBTITULO = "2F5496"
_BORDE = "B7C3D9"
_TEXTO = "1A1A1A"

_NOMBRES_TIPO = {
    "esquema": "mapa conceptual",
    "tabla": "tabla",
    "timeline": "línea de tiempo",
    "lista": "lista jerárquica",
}

_ANCHO_TABLA_CM = 16.5
_ANCHO_RELATIVO = {"esquema": (30, 70), "lista": (30, 70), "tabla": (30, 70), "timeline": (25, 75)}

_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""


def _styles_xml() -> str:
    """Estilos del documento: página, portada, títulos, listas, tablas y esquema."""
    p = dict(
        celeste=_CELESTE,
        gris=_GRIS,
        azul_t=_AZUL_TITULO,
        azul_s=_AZUL_SUBTITULO,
        borde=_BORDE,
        texto=_TEXTO,
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:mimetype="application/vnd.oasis.opendocument.text">
 <office:font-face-decls>
  <style:font-face style:name="Liberation Serif" svg:font-family="'Liberation Serif', 'Times New Roman', serif"/>
  <style:font-face style:name="DejaVu Sans Mono" svg:font-family="'DejaVu Sans Mono', 'Courier New', monospace" style:font-pitch="fixed"/>
 </office:font-face-decls>
 <office:automatic-styles>
  <style:page-layout style:name="PM1"><style:page-layout-properties fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2.5cm" fo:margin-right="2.5cm" style:writing-mode="lr-tb"/></style:page-layout>
  <style:style style:name="TDX" style:family="table"><style:table-properties style:width="16.5cm" table:align="margins"/></style:style>
  <style:style style:name="TCab" style:family="table-cell"><style:table-cell-properties fo:background-color="#{p['celeste']}" fo:border="0.5pt solid #{p['borde']}" fo:padding="0.1cm"/><style:text-properties fo:font-weight="bold" fo:color="#{p['azul_t']}"/></style:style>
  <style:style style:name="TAlt" style:family="table-cell"><style:table-cell-properties fo:background-color="#{p['gris']}" fo:border="0.5pt solid #C9D2E0" fo:padding="0.1cm"/></style:style>
  <style:style style:name="TNor" style:family="table-cell"><style:table-cell-properties fo:border="0.5pt solid #C9D2E0" fo:padding="0.1cm"/></style:style>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Standard" style:page-layout-name="PM1"/>
 </office:master-styles>
 <office:styles>
  <style:default-style style:family="paragraph"><style:paragraph-properties fo:margin-top="0.12cm" fo:margin-bottom="0.12cm" fo:line-height="115%"/><style:text-properties fo:font-size="11pt" fo:color="#{p['texto']}" style:font-name="Liberation Serif"/></style:default-style>
  <style:style style:name="Heading" style:family="paragraph" style:parent-style-name="Standard" style:next-style-name="Text_20_Body" style:class="text"><style:paragraph-properties fo:margin-top="0.5cm" fo:margin-bottom="0.25cm" fo:keep-with-next="always"/><style:text-properties style:font-name="Liberation Serif" fo:font-style="normal"/></style:style>
  <style:style style:name="Heading_20_1" style:family="paragraph" style:parent-style-name="Heading" style:default-outline-level="1"><style:text-properties fo:font-size="17pt" fo:font-weight="bold" fo:color="#{p['azul_t']}"/></style:style>
  <style:style style:name="Heading_20_2" style:family="paragraph" style:parent-style-name="Heading" style:default-outline-level="2"><style:text-properties fo:font-size="13.5pt" fo:font-weight="bold" fo:color="#{p['azul_s']}"/></style:style>
  <style:style style:name="Heading_20_3" style:family="paragraph" style:parent-style-name="Heading" style:default-outline-level="3"><style:text-properties fo:font-size="12pt" fo:font-weight="bold" fo:color="#{p['azul_s']}" fo:font-style="italic"/></style:style>
  <style:style style:name="Text_20_Body" style:family="paragraph" style:parent-style-name="Standard"><style:paragraph-properties fo:margin-top="0.15cm" fo:margin-bottom="0.15cm"/></style:style>
  <style:style style:name="Portada_20_Titulo" style:family="paragraph" style:parent-style-name="Heading" style:default-outline-level="1"><style:paragraph-properties fo:text-align="center" fo:margin-top="5cm" fo:margin-bottom="0.6cm"/><style:text-properties fo:font-size="28pt" fo:font-weight="bold" fo:color="#{p['azul_t']}" fo:font-style="normal"/></style:style>
  <style:style style:name="Portada_20_Sub" style:family="paragraph" style:parent-style-name="Text_20_Body"><style:paragraph-properties fo:text-align="center" fo:margin-bottom="0.3cm"/><style:text-properties fo:font-size="14pt" fo:color="#{p['azul_s']}" fo:font-style="italic"/></style:style>
  <style:style style:name="Portada_20_Meta" style:family="paragraph" style:parent-style-name="Text_20_Body"><style:paragraph-properties fo:text-align="center"/><style:text-properties fo:font-size="9.5pt" fo:color="#5A5A5A"/></style:style>
  <style:style style:name="Nota" style:family="paragraph" style:parent-style-name="Text_20_Body"><style:text-properties fo:font-size="9pt" fo:color="#5A5A5A" fo:font-style="italic"/></style:style>
   <style:style style:name="Salto_20_pagina" style:family="paragraph" style:parent-style-name="Standard"><style:paragraph-properties fo:break-before="page"/></style:style>
  <style:style style:name="Esquema" style:family="paragraph" style:parent-style-name="Preformatted_20_Text"><style:paragraph-properties fo:background-color="#{p['gris']}" fo:border="0.4pt solid #{p['borde']}" fo:padding="0.18cm" fo:margin-left="0.4cm" fo:margin-right="0.4cm" fo:margin-top="0.25cm" fo:margin-bottom="0.25cm" fo:keep-together="always"/><style:text-properties style:font-name="DejaVu Sans Mono" fo:font-size="8.6pt" fo:color="#{p['texto']}"/></style:style>
  <style:style style:name="L1" style:family="list">
   <text:list-level-style-bullet text:level="1" text:bullet-char="•"><style:list-level-properties text:list-level-position-and-space-mode="label-alignment"><style:list-level-label-alignment text:label-followed-by="listtab" fo:text-indent="-0.7cm" fo:margin-left="0.7cm"/></style:list-level-properties><style:text-properties fo:color="#{p['azul_s']}" fo:font-size="110%"/></text:list-level-style-bullet>
   <text:list-level-style-bullet text:level="2" text:bullet-char="–"><style:list-level-properties text:list-level-position-and-space-mode="label-alignment"><style:list-level-label-alignment text:label-followed-by="listtab" fo:text-indent="-0.6cm" fo:margin-left="1.3cm"/></style:list-level-properties><style:text-properties fo:color="#8496B0"/></text:list-level-style-bullet>
  </style:style>
  <style:style style:name="L2" style:family="list">
   <text:list-level-style-number text:level="1" style:num-suffix="." style:num-format="1"><style:list-level-properties text:list-level-position-and-space-mode="label-alignment"><style:list-level-label-alignment text:label-followed-by="listtab" fo:text-indent="-0.8cm" fo:margin-left="0.8cm"/></style:list-level-properties><style:text-properties fo:color="#{p['azul_s']}" fo:font-weight="bold"/></text:list-level-style-number>
  </style:style>
 </office:styles>
</office:document-styles>"""


def _meta_xml(titulo: str, generado: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"'
        ' office:mimetype="application/vnd.oasis.opendocument.text">'
        "<office:meta>"
        f"<dc:title>{escape(titulo)}</dc:title>"
        "<meta:generator>tareas repaso-ia</meta:generator>"
        f"<dc:date>{escape(generado)}</dc:date>"
        "</office:meta></office:document-meta>"
    )


def _parrafo(texto: str, estilo: str = "Text_20_Body") -> str:
    return f'<text:p text:style-name="{estilo}">{escape(texto)}</text:p>'


def _titulo(texto: str, nivel: int) -> str:
    return (
        f'<text:h text:style-name="Heading_20_{nivel}" text:outline-level="{nivel}">'
        f"{escape(texto)}</text:h>"
    )


def _bullet(texto: str, estilo: str = "L1") -> str:
    return (
        f'<text:list text:style-name="{estilo}"><text:list-item>'
        f"<text:p>{escape(texto)}</text:p>"
        "</text:list-item></text:list>"
    )


def _tabla(filas: list[list[str]], proporcion: tuple[int, ...] | None = None) -> str:
    """Tabla real de Writer con columnas proporcionales al contenido."""
    if not filas:
        return ""
    columnas = max(len(fila) for fila in filas)
    normalizadas = [
        (list(fila) + [""] * (columnas - len(fila)))[:columnas] for fila in filas
    ]
    cabecera = normalizadas[0]
    if proporcion is None:
        pesos = [
            max(10, min(60, max(len(str(celda)) for celda in [fila[i] for fila in normalizadas])))
            for i in range(columnas)
        ]
        suma = sum(pesos) or 1
        proporcion = tuple(max(1, round(peso * 100 / suma)) for peso in pesos)
        proporcion = list(proporcion)
        proporcion[-1] += 100 - sum(proporcion)
        proporcion = tuple(proporcion)
    partes = ['<table:table table:name="TablaRepaso" table:style-name="TDX">']
    for ancho in proporcion:
        cm = _ANCHO_TABLA_CM * ancho / 100
        partes.append(f'<table:table-column table:column-width="{cm:.2f}cm"/>')
    for indice, fila in enumerate(normalizadas):
        partes.append("<table:table-row>")
        for celda, ancho in zip(fila, proporcion):
            estilo = "TCab" if indice == 0 else ("TAlt" if indice % 2 == 0 else "TNor")
            partes.append(
                f'<table:table-cell table:style-name="{estilo}" office:value-type="string">'
                f"<text:p>{escape(str(celda))}</text:p></table:table-cell>"
            )
        partes.append("</table:table-row>")
    partes.append("</table:table>")
    partes.append('<text:p text:style-name="Nota"/>')
    return "".join(partes)


def _es_previada(linea: str) -> bool:
    limpia = linea.lstrip()
    return bool(limpia) and (limpia[:1] in "┌│└├●" or limpia[:2] in ("├─", "└─"))


def _numero(linea: str) -> str:
    return linea[3:].strip() if len(linea) >= 3 and linea[:2] == "1." else linea


def _cuerpo_seccion(seccion: Seccion) -> str:
    partes: list[str] = []
    previo: list[str] = []

    def verter_previo() -> None:
        for linea in previo:
            partes.append(
                f'<text:p text:style-name="Esquema">{escape(linea or " ")}</text:p>'
            )
        previo.clear()

    for cruda in seccion.cuerpo:
        linea = cruda.strip()
        if _es_previada(cruda):
            previo.append(cruda.rstrip())
            continue
        verter_previo()
        if not linea:
            continue
        if linea[:2] in ("- ", "* ", "– "):
            partes.append(_bullet(linea[2:].strip()))
        elif len(linea) >= 3 and linea[0].isdigit() and linea[1] == "." and linea[2] == " ":
            partes.append(_bullet(linea[3:].strip(), "L2"))
        elif linea.endswith(":") and len(linea) < 60:
            partes.append(_titulo(linea.rstrip(":"), 3))
        else:
            partes.append(_parrafo(linea))
    verter_previo()
    return "".join(partes)


def _esquema_como_lista(esquema: Esquema) -> str:
    """Esquema, lista o línea de tiempo como lista jerárquica nativa de Writer.

    Sustituye al diagrama ASCII: la misma información, ordenada, sin cajas
    descolocadas ni duplicados con la tabla equivalente.
    """
    partes: list[str] = []
    for etiqueta, detalle in esquema.entradas:
        texto = f"{etiqueta} — {detalle}" if detalle else etiqueta
        partes.append(_bullet(texto))
    return "".join(partes)


def _seccion_esquemas(esquemas: list[Esquema]) -> str:
    partes: list[str] = []
    for indice, esquema in enumerate(esquemas, start=1):
        partes.append(
            _titulo(f"{indice}. {_NOMBRES_TIPO.get(esquema.tipo, esquema.tipo)}", 2)
        )
        partes.append(_esquema_como_lista(esquema))
    return "".join(partes)


def escribir_odt(
    ruta_destino: Path,
    titulo: str,
    asignatura: str,
    secciones: list[Seccion],
    esquemas: list[Esquema],
    fuentes: list[str],
    generado: str,
) -> None:
    """Escribe el paquete ODT completo (válido para LibreOffice Writer)."""
    cuerpo: list[str] = [
        "<office:body><office:text>",
        _titulo(titulo, 1).replace('Heading_20_1', 'Portada_20_Titulo'),
        _parrafo(asignatura or "Documento de repaso", "Portada_20_Sub"),
        _parrafo(f"Generado con la acción «repaso-ia» de tareas · {generado}", "Portada_20_Meta"),
        _parrafo(
            "Fuentes: " + (", ".join(fuentes) if fuentes else "sin fuentes"),
            "Portada_20_Meta",
        ),
        '<text:p text:style-name="Salto_20_pagina"/>',
    ]

    esquemas_no_tabla = [e for e in esquemas if e.tipo != "tabla"]
    tablas_globales = [e for e in esquemas if e.tipo == "tabla"]

    for seccion in secciones:
        if seccion.titulo == "Esquemas" and seccion.vacia and not esquemas_no_tabla:
            continue
        cuerpo.append(_titulo(seccion.titulo, 1))
        if seccion.titulo == "Tablas comparativas":
            asignadas = list(getattr(seccion, "tablas", []))
            if not asignadas and not any(
                getattr(s, "tablas", []) for s in secciones
            ):
                asignadas = tablas_globales  # compatibilidad: tablas sin sección padre
            for tabla in asignadas:
                cuerpo.append(_tabla(tabla.tabla))
        if seccion.titulo == "Esquemas":
            if not seccion.vacia:
                cuerpo.append(_cuerpo_seccion(seccion))
            cuerpo.append(_seccion_esquemas(esquemas_no_tabla))
            continue
        cuerpo.append(_cuerpo_seccion(seccion))

    cuerpo.append("</office:text></office:body>")

    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
        ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
        ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
        ' xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"'
        ' office:mimetype="application/vnd.oasis.opendocument.text">'
        + "".join(cuerpo)
        + "</office:document-content>"
    )

    with zipfile.ZipFile(ruta_destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        # El estándar ODF exige que `mimetype` sea la primera entrada y esté
        # sin comprimir para que los lectores puedan identificar el documento.
        paquete.writestr(
            "mimetype",
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED,
        )
        paquete.writestr("META-INF/manifest.xml", _MANIFEST)
        paquete.writestr("meta.xml", _meta_xml(titulo, generado))
        paquete.writestr("styles.xml", _styles_xml())
        paquete.writestr("content.xml", content)
