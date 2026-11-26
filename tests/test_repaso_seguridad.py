"""Pruebas del módulo de seguridad: confinamiento y mensajes sin secretos."""

from pathlib import Path

import pytest

from tareas.repaso.seguridad import (
    RutaFueraDeBaseError,
    con_etapa,
    fuera_de_base,
    objetivo_normal,
    ruta_dentro_de_base,
    ruta_salida,
)


def test_fuera_de_base_detecta_escape_y_permite_interior(tmp_path: Path) -> None:
    interior = (tmp_path / "a.txt").resolve()
    exterior = (tmp_path.parent / "otra.txt").resolve()
    assert fuera_de_base(interior, tmp_path) is False
    assert fuera_de_base(exterior, tmp_path) is True


def test_ruta_dentro_de_base_resuelve_relativas(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    resuelta = ruta_dentro_de_base(Path("sub"), tmp_path)
    assert resuelta == (tmp_path / "sub").resolve()


def test_ruta_dentro_de_base_rechaza_escape(tmp_path: Path) -> None:
    with pytest.raises(RutaFueraDeBaseError, match="fuera de la raíz"):
        ruta_dentro_de_base(Path("../escapa.txt"), tmp_path)


def test_ruta_dentro_de_base_absoluta_es_estRICTA_como_el_borrar_original(tmp_path: Path) -> None:
    """Modo `borrar`: una ruta inexistente lanza RutaFueraDeBaseError, sin cambiar códigos."""
    with pytest.raises(RutaFueraDeBaseError):
        ruta_dentro_de_base(Path("no-existe.txt"), tmp_path, absolute=True)
    objetivo = tmp_path / "existe.txt"
    objetivo.write_text("x", encoding="utf-8")
    assert ruta_dentro_de_base(Path("existe.txt"), tmp_path, absolute=True) == objetivo.resolve(strict=True)


def test_ruta_salida_mantiene_mensaje_propio(tmp_path: Path) -> None:
    with pytest.raises(RutaFueraDeBaseError, match="ruta de salida"):
        ruta_salida(Path("../fuera.odt"), tmp_path)


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        ("test", "examen tipo test"),
        ("Tipo Test", "examen tipo test"),
        ("tipo_test", "examen tipo test"),
        ("desarrollo", "examen de desarrollo"),
        ("general", "repaso general"),
        ("", "repaso general"),
        (None, "repaso general"),
        ("otro objetivo propio", "otro objetivo propio"),
    ],
)
def test_objetivo_normal_equivalencias(entrada: str | None, esperada: str) -> None:
    assert objetivo_normal(entrada) == esperada


def test_con_etapa_anade_etapa_sin_exponer_mas():
    class ConEtapa(Exception):
        etapa = "fragmento 2 de 3"

    assert con_etapa("fallo", ConEtapa()) == "fallo (etapa: fragmento 2 de 3)"
    assert con_etapa("fallo", ValueError()) == "fallo"
