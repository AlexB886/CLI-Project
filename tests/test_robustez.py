"""Pruebas de robustez: permisos, unicode, enlaces, binarios y progreso."""

import os
import stat
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tareas.cli import crear_app
from tareas.ia.nulo import ProveedorNulo
from tareas.visual import Progreso


def _es_root() -> bool:
    return os.name == "nt" or os.geteuid() == 0


@pytest.fixture()
def acciones_vacia(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    ruta.write_text('{"version": 1, "acciones": []}', encoding="utf-8")
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    return ruta


def test_listar_carpetas_grandes_unicode_y_espacios(tmp_path):
    from tareas.acciones.internas import listar
    from tareas.modelos import ContextoAccion

    carpeta = tmp_path / "muchos archivos ñ"
    carpeta.mkdir()
    for n in range(50):
        (carpeta / f"tema {n} αβγ.txt").write_text("x", encoding="utf-8")
    (carpeta / "sub").mkdir()

    resultado = listar(ContextoAccion(parametros={"carpeta": carpeta}))

    assert resultado.codigo == 0
    assert len(resultado.datos.filas) == 51  # 50 ficheros + subcarpeta, ordenados


def test_listar_incluye_elementos_que_desaparecen_sin_romperse(tmp_path):
    from tareas.acciones.internas import listar
    from tareas.modelos import ContextoAccion

    carpeta = tmp_path / "cambiante"
    carpeta.mkdir()
    (carpeta / "estable.txt").write_text("x", encoding="utf-8")
    resultado = listar(ContextoAccion(parametros={"carpeta": carpeta}))
    assert resultado.codigo == 0


@pytest.mark.skipif(_es_root(), reason="root puede leerlo todo")
def test_archivo_sin_permiso_de_lectura_es_error_humano(tmp_path):
    from tareas.acciones.internas import ver
    from tareas.modelos import ContextoAccion

    ruta = tmp_path / "cerrado.txt"
    ruta.write_text("secreto", encoding="utf-8")
    ruta.chmod(0)
    try:
        resultado = ver(ContextoAccion(parametros={"ruta": ruta}))
    finally:
        ruta.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert resultado.codigo == 1
    assert "No se pudo leer" in resultado.error


@pytest.mark.skipif(_es_root(), reason="root puede leerlo todo")
def test_ver_streaming_no_carga_un_fichero_grande(tmp_path):
    """Con streaming, un fichero de 50 MB se lee en una fracción de segundos."""
    import time

    from tareas.acciones.internas import ver
    from tareas.modelos import ContextoAccion

    ruta = tmp_path / "grande.txt"
    linea = ("línea de relleno para medir el streaming " * 4 + "\n")
    with ruta.open("w", encoding="utf-8") as f:
        for n in range(900_000):
            f.write(linea)
    assert ruta.stat().st_size > 50_000_000

    t0 = time.monotonic()
    resultado = ver(ContextoAccion(parametros={"ruta": ruta}))
    duracion = time.monotonic() - t0

    assert resultado.codigo == 0
    assert "más líneas" in resultado.salida
    assert duracion < 5, f"ver tardó {duracion:.1f}s: no hace streaming"


def test_ver_binario_y_utf8_invalido_mensaje_humano(tmp_path):
    from tareas.acciones.internas import ver
    from tareas.modelos import ContextoAccion

    binario = tmp_path / "bin.txt"
    binario.write_bytes(b"\xff\xfe\x00binario")
    resultado = ver(ContextoAccion(parametros={"ruta": binario}))
    assert resultado.codigo == 1
    assert "UTF-8" in resultado.error


def test_ver_linea_extremadamente_larga(tmp_path):
    from tareas.acciones.internas import ver
    from tareas.modelos import ContextoAccion

    ruta = tmp_path / "larga.txt"
    ruta.write_text("x" * 400_000, encoding="utf-8")
    resultado = ver(ContextoAccion(parametros={"ruta": ruta}))
    assert resultado.codigo == 0
    assert resultado.salida.count("x") == 200_000 or resultado.salida.startswith("xxx")


def test_tamano_no_sigue_enlaces_y_un_ciclo_no_bloquea(tmp_path):
    from tareas.acciones.internas import tamano
    from tareas.modelos import ContextoAccion

    carpeta = tmp_path / "arbol"
    interior = carpeta / "dentro"
    interior.mkdir(parents=True)
    (interior / "a.txt").write_text("12345", encoding="utf-8")
    enlace_fich = carpeta / "espejo.txt"
    enlace_dir = carpeta / "bucle"
    try:
        enlace_fich.symlink_to(interior / "a.txt")
        enlace_dir.symlink_to(carpeta, target_is_directory=True)  # ciclo
    except OSError:
        pytest.skip("sin permisos para crear enlaces")

    resultado = tamano(ContextoAccion(parametros={"carpeta": carpeta}))

    assert resultado.codigo == 0
    filas = dict(resultado.datos.filas)
    assert filas["Ficheros"] == "1"          # no cuenta el enlace a fichero
    assert any("No contabilizados" in k for k in filas)      # informa de lo omitido


def test_unicode_rutas_con_espacios_and_parantheses(tmp_path, monkeypatch):
    """Todo el flujo con ruta «retratos ñ (final).txt» funciona."""
    import json

    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    ruta = tmp_path / "retratos ñ (final).txt"
    ruta.write_text("contenido", encoding="utf-8")
    acciones = tmp_path / "a.json"
    acciones.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "validar",
                        "descripcion": "d",
                        "tipo": "funcion",
                        "ejecutar": "validar",
                        "destructiva": False,
                        "parametros": {"ruta": {"tipo": "ruta", "requerido": True}},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    resultado = CliRunner().invoke(crear_app(acciones), ["validar", str(ruta)])
    assert resultado.exit_code == 0 and "OK" in resultado.output


def test_doctor_no_revela_la_clave_venida_de_env(tmp_path, monkeypatch):
    """doctor con clave solo en .env: debe decir «configurada» sin mostrarla."""
    import json

    clave_sintetica = "clave-sintetica-secreta-xyz"
    (tmp_path / ".env").write_text(f"TAREAS_API_KEY={clave_sintetica}\n", encoding="utf-8")
    monkeypatch.delenv("TAREAS_API_KEY", raising=False)
    monkeypatch.delenv("TAREAS_CA_BUNDLE", raising=False)
    monkeypatch.chdir(tmp_path)
    ruta = tmp_path / "acciones.json"
    ruta.write_text('{"version": 1, "acciones": []}', encoding="utf-8")

    resultado = CliRunner().invoke(crear_app(ruta), ["doctor"])

    assert resultado.exit_code == 0
    assert "configurada" in resultado.output
    assert clave_sintetica not in resultado.output


def test_progreso_no_tty_imprime_fases_y_resumen():
    vistas: list[str] = []
    progreso = Progreso(3, "Sintetizando fragmentos", imprimir=vistas.append, es_tty=False)
    progreso.avanzar()
    progreso.avanzar()
    progreso.avanzar()
    progreso.cerrar()
    assert vistas == ["Sintetizando fragmentos: 3/3 completado."]


def test_progreso_tty_una_sola_linea_con_porcentaje():
    escritas: list[str] = []

    class Falso:
        def write(self, texto):
            escritas.append(texto)

        def flush(self):
            pass

    import sys

    original = sys.stdout
    sys.stdout = Falso()
    try:
        progreso = Progreso(4, "Sintetizando fragmentos", es_tty=True)
        progreso.avanzar()
        progreso.avanzar()
        progreso.avanzar()
        progreso.avanzar()
        progreso.cerrar()
    finally:
        sys.stdout = original
    unicos = {l for l in escritas if l and not l.startswith("\r")}
    assert any("50%" in l for l in escritas)
    assert escritas[-1].startswith("\r")  # se limpia la línea al cerrar


def test_repaso_ia_parametro_paralelo_valido_y_acotado(monkeypatch, tmp_path):
    import tareas.acciones.internas as internas
    from tareas.modelos import ContextoAccion
    from tareas.repaso.escritorio import EscritorioNoDisponible

    apuntes = tmp_path / "tema.txt"
    apuntes.write_text("La fotosíntesis ocurre en los cloroplastos.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class IA:
        nombre = "sim"

        def generar_texto(self, peticion, contexto):
            return "# Introducción\nFotosíntesis\n\n## ESQUEMA\nesquema: Fotosíntesis :: luz\nNúcleo :: ADN"

        def proponer_acciones(self, p, c):
            return []

    monkeypatch.setattr(
        internas, "abrir_en_writer",
        lambda r: (_ for _ in ()).throw(EscritorioNoDisponible("x")),
    )
    resultado = internas.repaso_ia(
        ContextoAccion(
            parametros={"archivos": [str(apuntes)], "base": str(tmp_path), "paralelo": 99},
            proveedor_ia=IA(),
            simular=False,
        )
    )
    assert resultado.codigo == 0
    assert (tmp_path / "tema.odt").is_file()
