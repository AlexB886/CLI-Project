"""Pruebas de integración de CLI con acciones.json temporal."""

import json
import sys

from typer.testing import CliRunner

from tareas.cli import crear_app
from tareas.ia.nulo import ProveedorNulo


def escribir_acciones(ruta, acciones):
    ruta.write_text(
        json.dumps({"version": 1, "acciones": acciones}),
        encoding="utf-8",
    )


def test_cli_registra_y_ejecuta_accion_desde_json_temporal(tmp_path, monkeypatch):
    carpeta = tmp_path / "documentos"
    carpeta.mkdir()
    (carpeta / "nota.txt").write_text("nota", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "listar-temporal",
                "descripcion": "Lista una carpeta temporal",
                "tipo": "funcion",
                "ejecutar": "listar",
                "destructiva": False,
                "parametros": {"carpeta": {"tipo": "ruta", "requerido": True}},
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    runner = CliRunner()

    resultado = runner.invoke(crear_app(ruta), ["listar-temporal", str(carpeta)])

    assert resultado.exit_code == 0, resultado.output
    assert "nota.txt" in resultado.output


def test_cli_devuelve_codigo_de_configuracion_invalida(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    ruta.write_text("{json inválido", encoding="utf-8")
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["acciones"])

    assert resultado.exit_code == 3
    assert "JSON inválido" in resultado.output


def test_cli_devuelve_codigo_de_uso_para_accion_desconocida(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(ruta, [])
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["ejecutar", "no-existe"])

    assert resultado.exit_code == 2
    assert "no existe" in resultado.output


def test_cli_simula_borrado_sin_eliminar_fichero(tmp_path, monkeypatch):
    objetivo = tmp_path / "objetivo.txt"
    objetivo.write_text("mantener", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "borrar-temporal",
                "descripcion": "Borra un fichero temporal",
                "tipo": "funcion",
                "ejecutar": "borrar",
                "destructiva": True,
                "parametros": {
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "base": {"tipo": "ruta", "por_defecto": str(tmp_path)},
                },
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(ruta),
        ["borrar-temporal", "objetivo.txt", "--simular"],
    )

    assert resultado.exit_code == 0, resultado.output
    assert "Se borraría" in resultado.output
    assert objetivo.read_text(encoding="utf-8") == "mantener"


def test_cli_cancelar_confirmacion_conserva_fichero_temporal(tmp_path, monkeypatch):
    objetivo = tmp_path / "objetivo.txt"
    objetivo.write_text("mantener", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "borrar-temporal",
                "descripcion": "Borra un fichero temporal",
                "tipo": "funcion",
                "ejecutar": "borrar",
                "destructiva": True,
                "parametros": {
                    "ruta": {"tipo": "ruta", "requerido": True},
                    "base": {"tipo": "ruta", "por_defecto": str(tmp_path)},
                },
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(
        crear_app(ruta),
        ["borrar-temporal", "objetivo.txt"],
        input="n\n",
    )

    assert resultado.exit_code == 1
    assert "cancelada" in resultado.output
    assert objetivo.read_text(encoding="utf-8") == "mantener"


def test_cli_ejecuta_comando_personalizado_de_json_temporal(tmp_path, monkeypatch):
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "comando-temporal",
                "descripcion": "Imprime una marca de prueba",
                "tipo": "comando",
                "ejecutar": [sys.executable, "-c", "print('comando-json-ok')"],
                "destructiva": False,
            }
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)

    resultado = CliRunner().invoke(crear_app(ruta), ["comando-temporal"])

    assert resultado.exit_code == 0, resultado.output
    assert "comando-json-ok" in resultado.output


def test_cli_acciones_ia_indican_modo_offline_sin_red(tmp_path, monkeypatch):
    fichero = tmp_path / "texto.txt"
    fichero.write_text("contenido sintético", encoding="utf-8")
    ruta = tmp_path / "acciones.json"
    escribir_acciones(
        ruta,
        [
            {
                "nombre": "resumir-ia-temporal",
                "descripcion": "Resume con proveedor nulo",
                "tipo": "funcion",
                "ejecutar": "resumir-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"ruta": {"tipo": "ruta", "requerido": True}},
            },
            {
                "nombre": "tarea-ia-temporal",
                "descripcion": "Crea tarea con proveedor nulo",
                "tipo": "funcion",
                "ejecutar": "tarea-ia",
                "destructiva": False,
                "ia": True,
                "parametros": {"texto": {"tipo": "texto", "requerido": True}},
            },
        ],
    )
    monkeypatch.setattr("tareas.motor.crear_proveedor", ProveedorNulo)
    app = crear_app(ruta)
    runner = CliRunner()

    resumen = runner.invoke(app, ["resumir-ia-temporal", str(fichero)])
    tarea = runner.invoke(app, ["tarea-ia-temporal", "preparar exposición"])

    assert resumen.exit_code == 0, resumen.output
    assert tarea.exit_code == 0, tarea.output
    assert "modo offline" in resumen.output
    assert "modo offline" in tarea.output
