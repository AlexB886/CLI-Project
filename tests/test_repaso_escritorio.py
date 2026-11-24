"""Pruebas de la apertura en LibreOffice (sin abrir Writer de verdad)."""

from pathlib import Path

import pytest

import tareas.repaso.escritorio as escritorio
from tareas.repaso.escritorio import (
    EscritorioNoDisponible,
    abrir_en_writer,
    localizar_writer,
)


def test_sin_libreoffice_instalado_informa_humanamente(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(escritorio.shutil, "which", lambda _: None)
    ruta = tmp_path / "repaso.odt"
    ruta.write_bytes(b"contenido")
    with pytest.raises(EscritorioNoDisponible, match="no está instalado"):
        abrir_en_writer(ruta)


def test_detecta_el_ejecutable_cuando_existe(monkeypatch) -> None:
    rutas = {"soffice": "/usr/bin/soffice", "libreoffice": None}
    monkeypatch.setattr(escritorio.shutil, "which", lambda p: rutas.get(p))
    assert localizar_writer() == "/usr/bin/soffice"


def test_no_bloquea_la_cli_y_lanza_writer_en_segundo_plano(monkeypatch, tmp_path) -> None:
    lanzados: dict = {}

    class ProcesoFalso:
        def __init__(self, orden, **kwargs):
            lanzados["orden"] = orden
            lanzados["kwargs"] = kwargs

    monkeypatch.setattr(escritorio.subprocess, "Popen", ProcesoFalso)
    monkeypatch.setattr(
        escritorio.shutil, "which", lambda p: "/usr/bin/soffice" if p == "soffice" else None
    )
    ruta = tmp_path / "repaso.odt"
    ruta.write_bytes(b"contenido")
    programa = abrir_en_writer(ruta)
    assert programa.endswith("soffice")
    assert lanzados["orden"][0].endswith("soffice") and lanzados["orden"][1] == "--writer"
    assert lanzados["kwargs"]["start_new_session"] is True  # sin colgarse de la CLI


def test_fallo_al_lanzar_se_convierte_en_mensaje_humano(monkeypatch, tmp_path) -> None:
    def explotar(*a, **k):
        raise OSError("sin permisos")

    monkeypatch.setattr(escritorio.subprocess, "Popen", explotar)
    monkeypatch.setattr(escritorio.shutil, "which", lambda p: "/usr/bin/soffice")
    ruta = tmp_path / "repaso.odt"
    ruta.write_bytes(b"x")
    with pytest.raises(EscritorioNoDisponible, match="No se pudo abrir"):
        abrir_en_writer(ruta)
