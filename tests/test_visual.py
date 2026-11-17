"""Pruebas de la interfaz visual adicional del CLI."""

import io
import json
import re

from rich.console import Console
from typer.testing import CliRunner

from tareas.cli import crear_app
from tareas.ia.nulo import ProveedorNulo
from tareas.modelos import Accion, TipoEjecucion
from tareas.visual import encabezado, estado, tabla_menu


def accion(nombre="listar", descripcion="Lista una carpeta", *, ia=False):
    return Accion(
        nombre=nombre,
        descripcion=descripcion,
        tipo=TipoEjecucion.FUNCION,
        ejecutar="listar",
        destructiva=False,
        ia=ia,
    )


def configurar(ruta, acciones):
    ruta.write_text(
        json.dumps({"version": 1, "acciones": acciones}),
        encoding="utf-8",
    )


def test_tabla_menu_numera_acciones_y_ofrece_salida():
    consola = Console(record=True, width=80)

    consola.print(tabla_menu([accion(), accion("tarea-ia", "Crea tarea", ia=True)]))
    texto = consola.export_text()

    assert "1" in texto
    assert "listar" in texto
    assert "tarea-ia" in texto
    assert "Salir" in texto


def test_encabezado_y_estados_respetan_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    buffer = io.StringIO()
    consola = Console(file=buffer, force_terminal=True, width=80)

    encabezado(consola, "prueba")
    estado(consola, "todo correcto", "ok")
    estado(consola, "cuidado", "aviso")
    estado(consola, "fallo", "error")

    salida = buffer.getvalue()
    assert "TAREAS" in salida
    assert "OK" in salida and "AVISO" in salida and "ERROR" in salida
    codigos = set(re.findall(r"\x1b\[([0-9;]*)m", salida))
    assert codigos <= {"0", "1", "2", "22"}


def test_color_aparece_si_la_terminal_lo_permite(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    buffer = io.StringIO()
    consola = Console(file=buffer, force_terminal=True, width=80)

    estado(consola, "todo correcto", "ok")

    assert re.search(r"\x1b\[[0-9;]*(3[0-7]|9[0-7])[0-9;]*m", buffer.getvalue())


def test_cli_menu_ejecuta_accion_elegida_y_sale(tmp_path, monkeypatch):
    carpeta = tmp_path / "docs"
    carpeta.mkdir()
    (carpeta / "nota.txt").write_text("contenido", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    configurar(
        ruta,
        [
            {
                "nombre": "listar",
                "descripcion": "Lista una carpeta",
                "tipo": "funcion",
                "ejecutar": "listar",
                "destructiva": False,
                "parametros": {"carpeta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(ruta), ["menu"], input=f"1\n{carpeta}\n0\n"
    )

    assert resultado.exit_code == 0, resultado.output
    assert "nota.txt" in resultado.output
    assert "Hasta luego" in resultado.output


def test_cli_menu_sale_con_entrada_no_interactiva(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    configurar(
        ruta,
        [
            {
                "nombre": "listar",
                "descripcion": "Lista una carpeta",
                "tipo": "funcion",
                "ejecutar": "listar",
                "destructiva": False,
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["menu"])

    assert resultado.exit_code == 0
    assert "no interactiva" in resultado.output.casefold()


def test_cli_help_y_acciones_muestran_el_encabezado(tmp_path):
    ruta = tmp_path / "acciones.json"
    configurar(ruta, [])
    runner = CliRunner()
    app = crear_app(ruta)

    ayuda = runner.invoke(app, ["--help"])
    acciones = runner.invoke(app, ["acciones"])

    assert ayuda.exit_code == 0
    assert acciones.exit_code == 0
    assert "TAREAS" in ayuda.output
    assert "menu" in ayuda.output
    assert "doctor" in ayuda.output
    assert "TAREAS" in acciones.output
